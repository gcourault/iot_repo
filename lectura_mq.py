"""Suscriptor MQTT local + API FastAPI (Actividad Obligatoria 2).

Se suscribe al tópico publicado por sensor_mq.py en el broker público HiveMQ y
expone lo recibido por HTTP, para confirmar que la publicación viajó a Internet
y volvió.

Variables de entorno: MQTT_BROKER, MQTT_PORT, MQTT_TOPIC (ver sensor_mq.py).
"""

import json
import os
import random
import threading
from typing import Optional

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# ── Modelo ────────────────────────────────────────────────────────────────────

class Lectura(BaseModel):
    # Campos del ESP32 (esp32_mqtt.py)
    temp: Optional[float] = None
    humidity: Optional[float] = None
    client_id: Optional[str] = None
    # Campos de los sensores Python (sensor_mq.py, sensor_mq_pub.py)
    sensor_id: Optional[str] = None
    valor: Optional[float] = None
    timestamp: Optional[str] = None

# ── Configuración ─────────────────────────────────────────────────────────────

BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT   = int(os.getenv("MQTT_PORT", "1883"))
TOPIC  = os.getenv("MQTT_TOPIC", "fadena/undef/gcourault/telemetria")

CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"lectura-mq-{random.randint(1000, 9999)}")

# ── Estado global ─────────────────────────────────────────────────────────────

ultimo_dato: Optional[Lectura] = None
mensajes_recibidos: list = []

# ── Callbacks MQTT ────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Conectado a {BROKER}:{PORT} con código: {reason_code}")
    client.subscribe(TOPIC)
    print(f"Suscrito al tópico: {TOPIC}")

def on_message(client, userdata, msg):
    global ultimo_dato
    payload = msg.payload.decode()
    print(f"[HIVEMQ] Recibido en {msg.topic}: {payload}")
    try:
        ultimo_dato = Lectura(**json.loads(payload))
        mensajes_recibidos.append(ultimo_dato.model_dump())
        if len(mensajes_recibidos) > 10:
            mensajes_recibidos.pop(0)
    except Exception as e:
        print(f"Error procesando mensaje: {e}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    try:
        mqtt_client.connect(BROKER, PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"Error conectando al broker {BROKER}: {e}")

# ── FastAPI ───────────────────────────────────────────────────────────────────

app = FastAPI(title="Lector MQTT (HiveMQ público)")

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=start_mqtt, daemon=True).start()
    print("Cliente MQTT iniciado en segundo plano")

@app.get("/")
async def home():
    return {"message": "Lector MQTT activo", "broker": BROKER, "puerto": PORT, "topic": TOPIC}

@app.get("/telemetria")
async def leer_dato_actual():
    return {"status": "online", "ultimo_dato": ultimo_dato}

@app.get("/telemetria/historial")
async def leer_historial():
    return {"status": "online", "mensajes": mensajes_recibidos}

if __name__ == "__main__":
    print(f"Iniciando lector MQTT en http://localhost:8001 (broker {BROKER}:{PORT}, topic {TOPIC})")
    uvicorn.run(app, host="0.0.0.0", port=8001)
