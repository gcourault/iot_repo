"""Servidor CoAP (Actividad Obligatoria 2).

Expone el recurso /temp:
  * POST → recibe una lectura de temperatura (lo usa coap_client.py)
  * GET  → devuelve la última lectura (lo usa el gateway HTTP→CoAP de lectura.py)

CoAP corre sobre UDP/5683, sin handshake ni conexión: cada lectura es un único
datagrama de petición y otro de respuesta.
"""

import asyncio
import json
from datetime import datetime

import aiocoap
import aiocoap.resource as resource

ultima_lectura = {"temperature": None, "timestamp": None}

class TemperatureResource(resource.Resource):
    """Recurso CoAP que maneja lecturas de temperatura."""

    async def render_get(self, request):
        payload = json.dumps(ultima_lectura).encode("utf-8")
        print(f"CoAP GET /temp → {ultima_lectura} ({len(payload)} bytes)")
        return aiocoap.Message(payload=payload, code=aiocoap.CONTENT)

    async def render_post(self, request):
        global ultima_lectura
        try:
            payload = json.loads(request.payload.decode("utf-8"))
            temp = payload.get("temperature")
            timestamp = payload.get("timestamp") or datetime.now().isoformat()
            ultima_lectura = {"temperature": temp, "timestamp": timestamp}
            print(f"[{timestamp}] CoAP POST /temp: {temp}°C ({len(request.payload)} bytes)")

            respuesta = json.dumps({"status": "received", "temp": temp}).encode("utf-8")
            return aiocoap.Message(payload=respuesta, code=aiocoap.CHANGED)
        except Exception as e:
            print(f"Error procesando la petición CoAP: {e}")
            return aiocoap.Message(code=aiocoap.BAD_REQUEST)

async def main():
    root = resource.Site()
    root.add_resource(['temp'], TemperatureResource())

    # Se escucha en '::' (doble pila IPv4/IPv6): los clientes resuelven
    # "localhost" primero a ::1, así que atarse solo a 127.0.0.1 hace que las
    # peticiones lleguen a un puerto cerrado y aiocoap devuelva NetworkError.
    print("Iniciando servidor CoAP en [::]:5683 (UDP, IPv4 + IPv6)...")
    await aiocoap.Context.create_server_context(root, bind=('::', 5683))

    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidor CoAP detenido")
