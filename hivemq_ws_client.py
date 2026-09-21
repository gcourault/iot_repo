"""Suscriptor MQTT sobre WebSocket contra HiveMQ público.

Réplica por script del cliente web oficial de HiveMQ
(https://www.hivemq.com/demos/websocket-client/): ese cliente es una página
JavaScript que abre un WebSocket contra broker.hivemq.com:8000, path /mqtt, y
habla MQTT dentro de ese WebSocket. Acá se hace exactamente lo mismo con paho
usando transport="websockets", de modo que el tráfico capturado en la red es el
mismo (handshake HTTP Upgrade + tramas WebSocket con paquetes MQTT dentro).

Variables de entorno:
    MQTT_BROKER  (default: broker.hivemq.com)
    WS_PORT      (default: 8000)   8884 para wss (TLS)
    WS_PATH      (default: /mqtt)
    WS_TLS       (default: 0)      1 para usar wss://
    MQTT_TOPIC   (default: fadena/undef/gcourault/telemetria)
    WS_SECONDS   (default: 0 = hasta Ctrl-C)
"""

import json
import os
import random
import ssl
import time
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER  = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT    = int(os.getenv("WS_PORT", "8000"))
PATH    = os.getenv("WS_PATH", "/mqtt")
USE_TLS = os.getenv("WS_TLS", "0") == "1"
TOPIC   = os.getenv("MQTT_TOPIC", "fadena/undef/gcourault/telemetria")
SECONDS = float(os.getenv("WS_SECONDS", "0"))

CLIENT_ID = os.getenv("WS_CLIENT_ID", f"clientId-web-{random.randint(100000, 999999)}")

recibidos = []

def on_connect(client, userdata, flags, reason_code, properties):
    esquema = "wss" if USE_TLS else "ws"
    print(f"✓ Conectado por {esquema}://{BROKER}:{PORT}{PATH} → {reason_code}")
    client.subscribe(TOPIC, qos=0)
    print(f"✓ Subscribe a '{TOPIC}' (equivale al botón Subscribe del cliente web)")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    recibidos.append(payload)
    hora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{hora}] {msg.topic} (qos {msg.qos}, {len(msg.payload)} bytes): {payload}")

def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        transport="websockets",
    )
    client.ws_set_options(path=PATH)
    if USE_TLS:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Conectando como cliente web simulado (client_id={CLIENT_ID})...")
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    inicio = time.time()
    try:
        while SECONDS == 0 or (time.time() - inicio) < SECONDS:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCerrando cliente WebSocket...")
    finally:
        client.loop_stop()
        client.disconnect()
        print(f"Total de mensajes recibidos por WebSocket: {len(recibidos)}")
        if recibidos:
            with open("capturas/act2/hivemq_ws_recibidos.json", "w") as f:
                json.dump(recibidos, f, indent=2)

if __name__ == "__main__":
    main()
