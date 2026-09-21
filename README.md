# IoT Dispositivos

Este proyecto simula un sistema IoT simple con diferentes protocolos de comunicación: HTTP, MQTT, WebSocket y CoAP.

## 🚀 Inicio Rápido

### Linux / macOS

```bash
git clone <url-del-repo>
cd iot_repo
chmod +x setup.sh
./setup.sh
```

### Windows

```powershell
git clone <url-del-repo>
cd iot_repo
powershell -ExecutionPolicy Bypass -File setup.ps1
```

**¡Listo!** Después de ejecutar estos comandos, todo está configurado y funcionando.

Probá el primer ejemplo:

**Linux/macOS:**
```bash
# Terminal 1
uv run python lectura_mq.py

# Terminal 2 (en otra terminal)
uv run python sensor_mq.py
```

**Windows (PowerShell):**
```powershell
# Terminal 1
uv run python lectura_mq.py

# Terminal 2 (en otra terminal)
uv run python sensor_mq.py
```

Abrí http://localhost:8001/telemetria en tu navegador para ver los datos en tiempo real.

---

## Tabla de Contenidos

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración Inicial](#configuración-inicial)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Ejecución](#ejecución)
- [Captura con Wireshark](#captura-con-wireshark)
- [Troubleshooting](#troubleshooting)

## Requisitos

### Todos los Sistemas Operativos

- **Python 3.12+** - [Descargar](https://www.python.org/downloads/)
- **uv** (gestor de paquetes Python) - Se instala automáticamente con `setup.sh` / `setup.ps1`
- **Git** - Para clonar el repositorio

### Solo para MQTT con TLS (sensor_er/lectura_er)

- **Linux/macOS:** Mosquitto (se instala automáticamente con `setup.sh`)
- **Windows:** Mosquitto - [Descargar instalador](https://mosquitto.org/download/)

**Nota para Windows:** Los scripts MQTT básicos (`sensor_mq`/`lectura_mq`) funcionan sin Mosquitto usando brokers públicos. Solo necesitás Mosquitto si querés usar `sensor_er`/`lectura_er` con TLS local.

## Instalación

### Instalación Automática (Recomendado)

```bash
git clone <url-del-repo>
cd iot_repo
chmod +x setup.sh
./setup.sh
```

El script `setup.sh` hace todo automáticamente:
- ✓ Verifica Python 3.12+
- ✓ Instala `uv` si no está
- ✓ Instala dependencias Python
- ✓ Instala Mosquitto
- ✓ Genera certificados TLS
- ✓ Configura Mosquitto

**¡Listo!** Después de ejecutar `setup.sh`, todos los scripts están listos para usar.

### Instalación Manual (Opcional)

Si preferís instalar paso a paso:

#### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd iot_repo
```

#### 2. Instalar dependencias Python

```bash
uv sync
```

Esto crea un entorno virtual en `.venv/` e instala todas las dependencias del proyecto.

#### 3. Instalar Mosquitto (solo para MQTT con TLS)

Requerido únicamente para `sensor_er.py` y `lectura_er.py`.

```bash
sudo apt update && sudo apt install -y mosquitto mosquitto-clients openssl
```

#### 4. Configurar Mosquitto con TLS

```bash
chmod +x setup_mosquitto_tls.sh
./setup_mosquitto_tls.sh
```

## Configuración Inicial

**Si usaste `setup.sh` (Linux/macOS) o `setup.ps1` (Windows), esta sección ya está completa. Podés saltar a [Ejecución](#ejecución).**

### Configurar Mosquitto con TLS (solo si instalaste manualmente)

**Linux/macOS:**

Este paso es necesario **solo para `sensor_er` y `lectura_er`**. Los demás scripts MQTT usan brokers públicos y no requieren configuración.

```bash
chmod +x setup_mosquitto_tls.sh
./setup_mosquitto_tls.sh
```

**Windows:**

En Windows, los scripts `sensor_er` y `lectura_er` requieren configuración manual de Mosquitto con TLS. Recomendamos usar los scripts MQTT básicos (`sensor_mq`/`lectura_mq`) que funcionan sin configuración adicional.

Si necesitás usar TLS local en Windows:
1. Instalá [Mosquitto para Windows](https://mosquitto.org/download/)
2. Usá WSL (Windows Subsystem for Linux) o Git Bash para ejecutar `setup_mosquitto_tls.sh`
3. O seguí la [guía oficial de Mosquitto TLS](https://mosquitto.org/man/mosquitto-tls-7.html)

**¿Qué hace este script?**
- Genera certificados SSL autofirmados en `~/.mosquitto/certs/`
- Crea un archivo de configuración en `~/.mosquitto/mosquitto.conf`
- Configura Mosquitto para escuchar en puerto 8883 con TLS

**Nota:** `sensor_er.py` levanta Mosquitto automáticamente usando esta configuración. No es necesario iniciar Mosquitto manualmente.

## Arquitectura del Sistema

El proyecto contiene múltiples pares de scripts sensor/lector para demostrar diferentes protocolos:

| Protocolo | Sensor | Lector | Broker/Servidor | Puerto |
|-----------|--------|--------|-----------------|--------|
| **HTTP** | `sensor.py` | `lectura.py` | FastAPI local | 8000 |
| **MQTT básico** | `sensor_mq.py` | `lectura_mq.py` | `broker.hivemq.com` (público) | 1883 |
| **MQTT sobre WebSocket** | `sensor_mq.py` | `hivemq_ws_client.py` | `broker.hivemq.com` (público) | 8000 |
| **MQTT + errores** | `sensor_er.py` | `lectura_er.py` | Mosquitto local TLS | 8883 |
| **WebSocket** | `ws_client.py` | `ws_server.py` o `lectura.py` | WebSocket local | 8000 |
| **CoAP** | `coap_client.py` | `coap_server.py` | CoAP local | 5683 (UDP) |
| **ESP32 (Wokwi)** | `esp32_mqtt.py` | N/A | mqtt-dashboard.com | 1883 |

### Flujo de Datos

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Sensor    │ ──────> │ Broker/Server│ ──────> │   Lector    │
│  (publica)  │         │   (rutea)    │         │ (suscribe)  │
└─────────────┘         └──────────────┘         └─────────────┘
```

## Ejecución

El sistema contiene varios ejemplos de comunicación IoT. Cada protocolo requiere ejecutar los scripts en **terminales separadas** y en el orden indicado.

---

### HTTP (Simulación básica)

Estos scripts simulan comunicación HTTP entre un sensor y un servidor de lectura.

**1. Primero - Servidor (Lectura):**
```bash
uv run uvicorn lectura:app --port 8000 --reload
```

**2. Después - Cliente (Sensor):**
```bash
uv run python sensor.py
```

---

### MQTT (Message Queue Telemetry Transport)

Estos scripts publican contra el **bróker público `broker.hivemq.com:1883`** (Actividad
Obligatoria 2): el tráfico sale a Internet y es visible en la interfaz de red (`eno1`/`wlan0`) de
Wireshark, no en `lo`. No hace falta Mosquitto.

El bróker, el puerto y el tópico se configuran por variables de entorno, así que los mismos scripts
sirven para un bróker local (Actividad 1):

| Variable | Valor por defecto |
|---|---|
| `MQTT_BROKER` | `broker.hivemq.com` |
| `MQTT_PORT` | `1883` |
| `MQTT_TOPIC` | `fadena/undef/gcourault/telemetria` |
| `SENSOR_COUNT` | `0` (publicar indefinidamente) |
| `SENSOR_PERIOD` | `2` segundos |

```bash
# Contra un Mosquitto local, como en la Actividad 1
MQTT_BROKER=localhost uv run python sensor_mq.py
```

**1. Primero - Suscriptor (Lectura):**
```bash
uv run python lectura_mq.py
```
Servidor en http://localhost:8001 con endpoints:
- `/telemetria` - Último dato recibido
- `/telemetria/historial` - Últimos 10 mensajes

**2. Después - Publicador (Sensor):**
```bash
uv run python sensor_mq.py
```

Verás en consola:
```
✓ CONNACK de broker.hivemq.com:1883 → Success (session_present=False)
  (CONNACK recibido en 0.46 s)
[001] Publicado en fadena/undef/gcourault/telemetria (81 bytes): {"sensor_id": "S-001", "valor": 27.64, ...}
```

**3. Suscripción desde Internet (equivalente al cliente web de HiveMQ):**
```bash
uv run python hivemq_ws_client.py
```
Abre un WebSocket contra `ws://broker.hivemq.com:8000/mqtt` con subprotocolo `mqtt`, igual que hace
la página <https://www.hivemq.com/demos/websocket-client/>. Para usar la página en lugar del script,
configurá host `broker.hivemq.com`, puerto `8000`, path `/mqtt` y suscribite al mismo tópico.

---

### Servidor IoT unificado (`lectura.py`)

`lectura.py` concentra los tres protocolos de la Actividad 2 en un solo proceso:

```bash
uv run uvicorn lectura:app --port 8000 --reload
```

| Endpoint | Protocolo | Qué hace |
|---|---|---|
| `POST /telemetria` | HTTP | recibe una lectura |
| `WS /ws` | WebSocket | canal bidireccional; difunde **todos** los eventos |
| `GET /coap/temp` | HTTP → CoAP | gateway hacia `coap_server.py` |
| `GET /` | HTTP | panel en vivo por WebSocket |
| `GET /estado`, `GET /eventos` | HTTP | estado y últimos 50 eventos |

Además se suscribe al tópico MQTT en HiveMQ y reenvía por WebSocket lo que llega desde Internet.
Para ver esa cadena completa:

```bash
uv run python ws_listener.py      # oyente del panel, en otra terminal
uv run python sensor_mq.py        # publica hacia HiveMQ, en una tercera
```

---

### MQTT con Simulación de Errores

Estos scripts demuestran MQTT con lógica de reintentos y simulación de errores de red/hardware, publicando **simultáneamente en dos brokers con TLS**:
- **Broker local:** `localhost:8883` (Mosquitto TLS) → tráfico visible en interfaz `lo` de Wireshark
- **Broker remoto:** `broker.hivemq.com:8883` (TLS) → tráfico visible en interfaz de red (`wlan0`/`eth0`)

Usa certificados autofirmados para el broker local y certificados del sistema para el remoto.

> Requiere ejecutar `./setup_mosquitto_tls.sh` una vez antes del primer uso (ver sección de instalación arriba).
> Iniciá siempre `sensor_er.py` antes que `lectura_er.py`.

**1. Primero - Publicador (levanta Mosquitto y publica datos):**
```bash
uv run python sensor_er.py
```

Verás en consola:
```
[LOCAL] Publicado exitosamente: {"sensor_id": "SENSOR_ER_01", ...}
[REMOTO] Publicado exitosamente: {"sensor_id": "SENSOR_ER_01", ...}
```

**2. Después - Suscriptor (Lectura):**
```bash
uv run python lectura_er.py
```

El servidor estará en http://localhost:8002 con endpoints:
- `/telemetria` - Último dato recibido
- `/telemetria/historial` - Últimos 10 mensajes

---

### WebSocket

Estos scripts demuestran comunicación bidireccional en tiempo real mediante WebSocket.

**1. Primero - Servidor:**
```bash
uv run python ws_server.py
```

**2. Después - Cliente:**
```bash
uv run python ws_client.py
```

---

### CoAP (Constrained Application Protocol)

Estos scripts demuestran el protocolo CoAP diseñado para dispositivos IoT con recursos limitados.

**1. Primero - Servidor:**
```bash
uv run python coap_server.py
```

**2. Después - Cliente:**
```bash
uv run python coap_client.py
```

---

### ESP32 con Wokwi

El script `esp32_mqtt.py` corre en el simulador [Wokwi](https://wokwi.com) sobre un ESP32 con sensor DHT22. Publica datos de temperatura y humedad en el broker **mqtt-dashboard.com:1883**, tópico `fadena/test`.

**Nota:** El ESP32 usa un broker remoto público (`mqtt-dashboard.com`), no el Mosquitto local. Para ver sus datos necesitarías cambiar `lectura_mq.py` temporalmente al broker remoto o usar el cliente web de MQTT.

---

### MQTT con HiveMQ (Broker Público)

El script `sensor_mq_pub.py` publica datos al broker público HiveMQ. Para leer los mensajes, debes usar el cliente web de HiveMQ para suscribirte al tópico correspondiente.

**Publicador:**
```bash
uv run python sensor_mq_pub.py
```

**Lector:** Usa el [cliente web de HiveMQ](https://www.hivemq.com/demos/websocket-client/) para suscribirte y leer los mensajes del tópico.

---

## Captura con Wireshark

Para analizar el tráfico de cada protocolo, abre Wireshark en la interfaz `lo` (loopback) para comunicación local o `any` para capturar todo el tráfico.

### Filtros por Protocolo

| Protocolo | Filtro Wireshark | Puerto |
|-----------|------------------|--------|
| **HTTP** (lectura + sensor) | `tcp.port == 8000` | 8000 |
| **MQTT básico** (lectura_mq + sensor_mq) | `tcp.port == 1883` | 1883 (local Y remoto) |
| **MQTT con errores** (lectura_er + sensor_er) | `tcp.port == 8883` | 8883 (local TLS Y remoto TLS) |
| **WebSocket** (ws_server + ws_client) | `websocket` o `tcp.port == 8000` | 8000 |
| **CoAP** (coap_server + coap_client) | `coap` o `udp.port == 5683` | 5683 |

### Instrucciones de Captura

1. **Abrir Wireshark** y seleccionar la interfaz:
   - `lo` o `Loopback` para tráfico local (localhost)
   - `any` para capturar todo el tráfico

2. **Aplicar el filtro** correspondiente en la barra de filtros

3. **Iniciar captura** (botón azul o Ctrl+E)

4. **Ejecutar los scripts** cliente-servidor en terminales separadas

5. **Detener captura** y analizar los paquetes

### Ejemplo: Capturar WebSocket

```bash
# En Wireshark: filtro "tcp.port == 8000"
# Terminal 1:
uv run python ws_server.py
# Terminal 2:
uv run python ws_client.py
```

### Ejemplo: Capturar CoAP (UDP)

```bash
# En Wireshark: filtro "coap" o "udp.port == 5683"
# Terminal 1:
uv run python coap_server.py
# Terminal 2:
uv run python coap_client.py
```

---

## Troubleshooting

### Error: "Mosquitto no levantó a tiempo"

**Causa:** El puerto 1883 ya está ocupado por otra instancia de Mosquitto.

**Solución:**
```bash
sudo systemctl stop mosquitto
sudo systemctl disable mosquitto  # Para que no arranque automáticamente
```

Luego volvé a ejecutar `sensor_er.py`.

### Error: "Connection refused" en puerto 8883

**Causa:** No se ejecutó `setup_mosquitto_tls.sh` o los certificados no se generaron correctamente.

**Solución:**
```bash
./setup_mosquitto_tls.sh
```

Verificá que los certificados existen:
```bash
ls -la ~/.mosquitto/certs/
```

Deberías ver: `ca.crt`, `ca.key`, `server.crt`, `server.key`

### Error: "The client is not currently connected"

**Causa:** El broker MQTT no está disponible o la conexión TLS falló.

**Solución para MQTT local (sensor_er/lectura_er):**
1. Verificá que Mosquitto esté instalado: `which mosquitto`
2. Probá iniciar Mosquitto manualmente: `mosquitto -c ~/.mosquitto/mosquitto.conf -v`
3. Si da error de puerto ocupado, seguí los pasos de "Mosquitto no levantó a tiempo"

**Solución para MQTT remoto (sensor_mq/lectura_mq):**
1. Verificá conectividad: `ping mqtt-dashboard.com`
2. Verificá que el puerto 1883 no esté bloqueado por firewall

### lectura_mq no recibe datos del ESP32

**Causa:** El broker o tópico no coinciden.

**Solución:**
- Verificá que `esp32_mqtt.py` use `MQTT_BROKER = "mqtt-dashboard.com"` y `TOPIC_PUB = "fadena/test"`
- Verificá que `lectura_mq.py` use el mismo broker y tópico
- Ambos archivos ya están configurados correctamente por defecto

### Wireshark no captura tráfico MQTT

**Causa:** Filtro incorrecto o interfaz incorrecta.

**Solución:**
- Para tráfico local (Mosquitto): Capturá en interfaz `lo` (Loopback)
- Para tráfico remoto (mqtt-dashboard.com): Capturá en interfaz de red activa (ej: `wlan0`, `eth0`)
- Usá filtro `tcp.port == 1883` o `tcp.port == 8883` según el caso

### Error: "Address already in use" al iniciar servidor

**Causa:** El puerto ya está ocupado por otra aplicación.

**Solución:**
```bash
# Ver qué proceso usa el puerto (ejemplo: 8000)
sudo lsof -i :8000

# Matar el proceso si es necesario
kill -9 <PID>
```

---

## Recursos Adicionales

- [Documentación de MQTT](https://mqtt.org/)
- [Documentación de CoAP](https://coap.technology/)
- [Wokwi ESP32 Simulator](https://wokwi.com)
- [Wireshark User Guide](https://www.wireshark.org/docs/wsug_html_chunked/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## Licencia

Este proyecto es material educativo para el curso de IoT.
