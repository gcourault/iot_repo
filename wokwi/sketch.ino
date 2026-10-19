// Actividad Obligatoria III — ESP32 + DHT22 publicando por MQTT en HiveMQ público
// Pegar en un proyecto Wokwi "ESP32 DevKit v1" junto con diagram.json y libraries.txt.

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// Red simulada de Wokwi (abierta, sin contraseña)
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASS = "";

// Bróker MQTT público, sin cifrado
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;

// Tópicos: el bróker es compartido, por eso se antepone un prefijo propio
#define TOPIC_BASE "fadena/undef/gcourault/esp32/dht22"
const char* TOPIC_TEMP = TOPIC_BASE "/temperatura";
const char* TOPIC_HUM  = TOPIC_BASE "/humedad";
const char* TOPIC_JSON = TOPIC_BASE "/json";

#define DHT_PIN  15
#define DHT_TYPE DHT22
const unsigned long PERIODO_MS = 2000;

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
unsigned long ultimaLectura = 0;

void conectarWiFi() {
  Serial.print("Conectando a WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS, 6);  // canal 6 acelera la conexión en Wokwi
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println(" conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void conectarMQTT() {
  while (!mqtt.connected()) {
    // Client ID único: el bróker público desconecta IDs repetidos
    String clientId = "esp32-dht22-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print("Conectando a MQTT ");
    Serial.print(MQTT_BROKER);
    Serial.print(" como ");
    Serial.print(clientId);
    Serial.print("... ");
    if (mqtt.connect(clientId.c_str())) {
      Serial.println("conectado");
    } else {
      Serial.print("falló, rc=");
      Serial.print(mqtt.state());
      Serial.println(" — reintento en 2 s");
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  conectarWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setKeepAlive(15);  // PINGREQ/PINGRESP visibles en la captura
}

void loop() {
  if (!mqtt.connected()) conectarMQTT();
  mqtt.loop();

  unsigned long ahora = millis();
  if (ahora - ultimaLectura < PERIODO_MS) return;
  ultimaLectura = ahora;

  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  if (isnan(temp) || isnan(hum)) {
    Serial.println("Error leyendo el DHT22");
    return;
  }

  char t[8], h[8], json[48];
  snprintf(t, sizeof(t), "%.1f", temp);
  snprintf(h, sizeof(h), "%.1f", hum);
  snprintf(json, sizeof(json), "{\"temp\": %.1f, \"hum\": %.1f}", temp, hum);

  mqtt.publish(TOPIC_TEMP, t);
  mqtt.publish(TOPIC_HUM, h);
  mqtt.publish(TOPIC_JSON, json);

  Serial.print("Publicado ");
  Serial.println(json);
}
