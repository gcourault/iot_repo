"""Gemelo en Python del ESP32 + DHT22 de Wokwi (Actividad Obligatoria 3).

El simulador web de Wokwi saca el tráfico del ESP32 por su propio gateway en
la nube, de modo que en la placa de red de la PC no aparece el MQTT/1883 hacia
HiveMQ sino un túnel cifrado hacia Wokwi. Este script reproduce el mismo
comportamiento que wokwi/sketch.ino (mismos tópicos, mismo payload, mismo
período y keepalive) pero desde la PC, para poder capturarlo con Wireshark en
eno1 y analizar las capas 7, 4, 3 y 2.

Variables de entorno:
    MQTT_BROKER   (default: broker.hivemq.com)
    MQTT_PORT     (default: 1883)
    TOPIC_BASE    (default: fadena/undef/gcourault/esp32/dht22)
    SENSOR_PERIOD (default: 2 segundos)
    SENSOR_COUNT  (default: 0 = infinito)
    KEEPALIVE     (default: 15 segundos, igual que el sketch)
"""

import json
import os
import random
import time
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER     = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT       = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_BASE = os.getenv("TOPIC_BASE", "fadena/undef/gcourault/esp32/dht22")
PERIOD     = float(os.getenv("SENSOR_PERIOD", "2"))
COUNT      = int(os.getenv("SENSOR_COUNT", "0"))
KEEPALIVE  = int(os.getenv("KEEPALIVE", "15"))

TOPIC_TEMP = f"{TOPIC_BASE}/temperatura"
TOPIC_HUM  = f"{TOPIC_BASE}/humedad"
TOPIC_JSON = f"{TOPIC_BASE}/json"

CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"esp32-dht22-twin-{random.randint(1000, 9999)}")


class DHT22Virtual:
    """Paseo aleatorio acotado a los rangos del DHT22 (-40..80 °C, 0..100 %)."""

    def __init__(self, temp=25.4, hum=60.2):
        self.temp = temp
        self.hum = hum

    def leer(self):
        self.temp = min(80.0, max(-40.0, self.temp + random.uniform(-0.3, 0.3)))
        self.hum = min(100.0, max(0.0, self.hum + random.uniform(-0.8, 0.8)))
        # El DHT22 entrega una décima de resolución
        return round(self.temp, 1), round(self.hum, 1)


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"✓ Conectado a MQTT {BROKER}:{PORT} como {CLIENT_ID} → {reason_code}")
    userdata["conectado"] = True


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"✗ Desconectado ({reason_code}) — paho reintenta solo")
    userdata["conectado"] = False


def main():
    estado = {"conectado": False}
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        userdata=estado,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    print(f"Conectando a MQTT {BROKER}:{PORT}...")
    client.connect(BROKER, PORT, keepalive=KEEPALIVE)
    client.loop_start()

    # Publicar antes del CONNACK pierde mensajes (ver Informe 2, §5.1)
    while not estado["conectado"]:
        time.sleep(0.05)

    sensor = DHT22Virtual()
    enviados = 0
    try:
        while COUNT == 0 or enviados < COUNT:
            temp, hum = sensor.leer()
            payload = json.dumps({"temp": temp, "hum": hum})
            client.publish(TOPIC_TEMP, f"{temp:.1f}")
            client.publish(TOPIC_HUM, f"{hum:.1f}")
            client.publish(TOPIC_JSON, payload).wait_for_publish()
            enviados += 1
            hora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{hora}] Publicado #{enviados} {payload}")
            time.sleep(PERIOD)
        # Dejar pasar al menos un keepalive para que aparezca PINGREQ/PINGRESP
        time.sleep(KEEPALIVE + 2)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
        print(f"Fin: {enviados} lecturas publicadas")


if __name__ == "__main__":
    main()
