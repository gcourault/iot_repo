"""Oyente WebSocket del servidor FastAPI (Actividad Obligatoria 2).

Equivalente por consola del panel HTML que sirve lectura.py en «/»: abre una
conexión WebSocket persistente contra /ws y muestra todo lo que el servidor
difunde, venga de HTTP, del puente MQTT (HiveMQ) o de otro cliente WebSocket.

Variables de entorno: WS_URL (default ws://localhost:8000/ws), WS_SECONDS.
"""

import asyncio
import json
import os
from datetime import datetime

import websockets

URL     = os.getenv("WS_URL", "ws://localhost:8000/ws")
SECONDS = float(os.getenv("WS_SECONDS", "0"))

async def conectar(intentos=10, espera=1.0):
    """Reintenta mientras el servidor FastAPI todavía no escucha."""
    for i in range(1, intentos + 1):
        try:
            return await websockets.connect(URL)
        except OSError as e:
            if i == intentos:
                raise
            print(f"  esperando a {URL} ({i}/{intentos}): {e.__class__.__name__}")
            await asyncio.sleep(espera)

async def escuchar():
    async with await conectar() as ws:
        print(f"Conectado a {URL} — esperando eventos difundidos por el servidor")
        inicio = asyncio.get_running_loop().time()
        while True:
            restante = None
            if SECONDS:
                restante = SECONDS - (asyncio.get_running_loop().time() - inicio)
                if restante <= 0:
                    break
            try:
                mensaje = await asyncio.wait_for(ws.recv(), timeout=restante)
            except asyncio.TimeoutError:
                break
            hora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            try:
                d = json.loads(mensaje)
                print(f"[{hora}] origen={d.get('origen','-'):<10} {json.dumps(d.get('dato', d))}")
            except json.JSONDecodeError:
                print(f"[{hora}] {mensaje}")

if __name__ == "__main__":
    try:
        asyncio.run(escuchar())
    except KeyboardInterrupt:
        print("\nOyente detenido")
