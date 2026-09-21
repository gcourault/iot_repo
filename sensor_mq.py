"""Publicador MQTT hacia el broker público HiveMQ (Actividad Obligatoria 2).

En la Actividad 1 este script publicaba en paralelo contra Mosquitto local y
mqtt-dashboard.com. Ahora el destino por defecto es el broker público
broker.hivemq.com, de modo que los mensajes salen a Internet y pueden verse
desde el cliente web de HiveMQ.

Configuración por variables de entorno:
    MQTT_BROKER   (default: broker.hivemq.com)
    MQTT_PORT     (default: 1883)
    MQTT_TOPIC    (default: fadena/undef/gcourault/telemetria)
    MQTT_QOS      (default: 0)
    SENSOR_PERIOD (default: 2 segundos)
    SENSOR_COUNT  (default: 0 = infinito)
"""

import json
import os
import random
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

# ── Configuración ─────────────────────────────────────────────────────────────

BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT   = int(os.getenv("MQTT_PORT", "1883"))
TOPIC  = os.getenv("MQTT_TOPIC", "fadena/undef/gcourault/telemetria")
QOS    = int(os.getenv("MQTT_QOS", "0"))
PERIOD = float(os.getenv("SENSOR_PERIOD", "2"))
COUNT  = int(os.getenv("SENSOR_COUNT", "0"))

CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"sensor-mq-{random.randint(1000, 9999)}")

# ── Sensor virtual ────────────────────────────────────────────────────────────

class SensorVirtual:
    def __init__(self, id, tipo):
        self.id   = id
        self.tipo = tipo

    def leer_valor(self):
        if self.tipo == "temperatura":
            return round(random.uniform(18, 30), 2)
        return random.randint(0, 100)

# ── Callbacks ─────────────────────────────────────────────────────────────────

# El CONNACK del broker público puede tardar varios segundos. Publicar antes de
# recibirlo es una violación del protocolo (el servidor debe procesar el CONNECT
# primero) y el broker puede descartar esos mensajes, así que se espera aquí.
conectado = threading.Event()

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"✓ CONNACK de {BROKER}:{PORT} → {reason_code} (session_present={flags.session_present})")
    if reason_code == 0:
        conectado.set()

def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"⚠ Desconectado de {BROKER}: {reason_code}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    sensor = SensorVirtual("S-001", "temperatura")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect

    print(f"Conectando a broker público {BROKER}:{PORT} (client_id={CLIENT_ID})...")
    t0 = time.time()
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    if not conectado.wait(timeout=20):
        print("ERROR: el broker no respondió con CONNACK en 20 s")
        client.loop_stop()
        return
    print(f"  (CONNACK recibido en {time.time() - t0:.2f} s)")

    print(f"Publicando en el tópico '{TOPIC}' con QoS {QOS} cada {PERIOD}s")
    print("Suscribite al mismo tópico desde el cliente web de HiveMQ para ver los mensajes.")

    enviados = 0
    try:
        while COUNT == 0 or enviados < COUNT:
            datos = {
                "sensor_id": sensor.id,
                "valor": sensor.leer_valor(),
                "timestamp": datetime.now().isoformat(),
            }
            payload = json.dumps(datos)

            info = client.publish(TOPIC, payload, qos=QOS)
            info.wait_for_publish()
            enviados += 1
            print(f"[{enviados:03d}] Publicado en {TOPIC} ({len(payload)} bytes): {payload}")

            time.sleep(PERIOD)
    except KeyboardInterrupt:
        print("\nDeteniendo sensor...")
    finally:
        # Margen para que el broker curse el último PUBLISH antes del DISCONNECT.
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        print(f"Total publicado: {enviados} mensajes")

if __name__ == "__main__":
    main()
