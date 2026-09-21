"""Servidor IoT FastAPI (Actividad Obligatoria 2).

Un único proceso que concentra los tres protocolos de la actividad:

  * HTTP       POST /telemetria        recepción clásica petición/respuesta
  * WebSocket  WS   /ws                canal bidireccional persistente
  * MQTT       puente hacia broker.hivemq.com: se suscribe al tópico y
                                       reenvía cada mensaje a los WebSocket
  * CoAP       GET  /coap/temp         gateway HTTP → CoAP (coap_server.py)

Arrancar con:  uv run uvicorn lectura:app --port 8000 --reload
"""

import asyncio
import json
import os
import random
from datetime import datetime
from typing import Optional

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ── Configuración ─────────────────────────────────────────────────────────────

MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "fadena/undef/gcourault/telemetria")
COAP_URI    = os.getenv("COAP_URI", "coap://localhost/temp")

# En un broker público el client_id debe ser único: si dos clientes usan el
# mismo identificador, el bróker desconecta al que ya estaba conectado.
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"fastapi-bridge-{random.randint(1000, 9999)}")

app = FastAPI(title="Servidor IoT FastAPI — CoAP / WebSocket / MQTT")

class Lectura(BaseModel):
    sensor_id: str
    valor: float

# ── Estado compartido ─────────────────────────────────────────────────────────

class GestorWebSocket:
    """Mantiene las conexiones WebSocket abiertas y difunde eventos."""

    def __init__(self):
        self.conexiones: list[WebSocket] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def conectar(self, ws: WebSocket):
        await ws.accept()
        self.conexiones.append(ws)
        print(f"[WS] Cliente conectado: {ws.client} (total: {len(self.conexiones)})")

    def desconectar(self, ws: WebSocket):
        if ws in self.conexiones:
            self.conexiones.remove(ws)
        print(f"[WS] Cliente desconectado: {ws.client} (total: {len(self.conexiones)})")

    async def difundir(self, mensaje: dict):
        muertas = []
        for ws in self.conexiones:
            try:
                await ws.send_text(json.dumps(mensaje))
            except Exception:
                muertas.append(ws)
        for ws in muertas:
            self.desconectar(ws)

    def difundir_desde_hilo(self, mensaje: dict):
        """Llamado desde el hilo de paho-mqtt, ajeno al event loop de asyncio."""
        if self.loop and self.conexiones:
            asyncio.run_coroutine_threadsafe(self.difundir(mensaje), self.loop)

gestor = GestorWebSocket()

eventos: list[dict] = []          # últimos eventos de cualquier protocolo
MAX_EVENTOS = 50

def registrar(origen: str, dato: dict):
    evento = {"origen": origen, "recibido": datetime.now().isoformat(), "dato": dato}
    eventos.append(evento)
    if len(eventos) > MAX_EVENTOS:
        eventos.pop(0)
    return evento

# ── Puente MQTT (HiveMQ público) ──────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Conectado a {MQTT_BROKER}:{MQTT_PORT} → {reason_code}")
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT] Suscrito a '{MQTT_TOPIC}'")

def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Desconectado de {MQTT_BROKER}: {reason_code} (paho reintentará)")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] {msg.topic}: {payload}")
    try:
        dato = json.loads(payload)
    except json.JSONDecodeError:
        dato = {"raw": payload}
    evento = registrar("mqtt", dato)
    gestor.difundir_desde_hilo(evento)      # MQTT → WebSocket

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)
mqtt_client.on_connect    = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message    = on_message

@app.on_event("startup")
async def startup_event():
    gestor.loop = asyncio.get_running_loop()
    try:
        mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"[MQTT] Puente iniciado hacia {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT] No se pudo iniciar el puente: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# ── HTTP ──────────────────────────────────────────────────────────────────────

@app.post("/telemetria")
async def recibir_data(data: Lectura):
    print(f"[HTTP] Recibido: {data}")
    evento = registrar("http", data.model_dump())
    await gestor.difundir(evento)
    return {"status": "recibido", "sensor": data.sensor_id, "valor": data.valor}

@app.get("/estado")
async def estado():
    return {
        "mqtt": {"broker": MQTT_BROKER, "puerto": MQTT_PORT, "topic": MQTT_TOPIC,
                 "client_id": MQTT_CLIENT_ID, "conectado": mqtt_client.is_connected()},
        "websocket": {"clientes": len(gestor.conexiones)},
        "coap": {"uri": COAP_URI},
        "eventos": len(eventos),
    }

@app.get("/eventos")
async def listar_eventos():
    return {"total": len(eventos), "eventos": eventos}

# ── Gateway HTTP → CoAP ───────────────────────────────────────────────────────

@app.get("/coap/temp")
async def gateway_coap():
    """Traduce una petición HTTP en una petición CoAP al servidor coap_server.py."""
    try:
        from aiocoap import Context, Message, GET

        contexto = await Context.create_client_context()
        respuesta = await asyncio.wait_for(
            contexto.request(Message(code=GET, uri=COAP_URI)).response, timeout=5
        )
        cuerpo = respuesta.payload.decode()
        await contexto.shutdown()
        try:
            dato = json.loads(cuerpo)
        except json.JSONDecodeError:
            dato = {"raw": cuerpo}
        registrar("coap", dato)
        return {"status": "ok", "codigo_coap": str(respuesta.code), "dato": dato}
    except Exception as e:
        return {"status": "error", "detalle": f"{type(e).__name__}: {e}"}

# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await gestor.conectar(websocket)
    try:
        await websocket.send_text(json.dumps({"origen": "servidor", "mensaje": "conectado"}))
        while True:
            texto = await websocket.receive_text()
            try:
                dato = json.loads(texto)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "JSON inválido"}))
                continue
            print(f"[WS] Recibido: {dato}")
            evento = registrar("websocket", dato)
            await websocket.send_text(json.dumps({"status": "ack", **evento}))
            await gestor.difundir(evento)      # visible también en el panel
    except WebSocketDisconnect:
        gestor.desconectar(websocket)

# ── Panel mínimo para ver los eventos en vivo ─────────────────────────────────

PANEL = """<!doctype html><meta charset="utf-8"><title>Panel IoT</title>
<style>body{font-family:monospace;background:#111;color:#eee;padding:1rem}
li{margin:.2rem 0}.mqtt{color:#6cf}.websocket{color:#fc6}.http{color:#6f6}.coap{color:#f6c}</style>
<h1>Panel IoT en vivo (WebSocket)</h1><ul id=log></ul>
<script>
const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = e => {
  const d = JSON.parse(e.data);
  const li = document.createElement('li');
  li.className = d.origen || '';
  li.textContent = `[${d.origen||'-'}] ${JSON.stringify(d.dato||d)}`;
  document.getElementById('log').prepend(li);
};
</script>"""

@app.get("/", response_class=HTMLResponse)
async def panel():
    return PANEL

if __name__ == "__main__":
    print("Iniciando servidor IoT en http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
