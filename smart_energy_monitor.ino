#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>

#define WIFI_SSID "Your_WiFi_SSID"
#define WIFI_PASSWORD "Your_WiFi_Password"

#define MQTT_SERVER "192.168.1.100"
#define MQTT_PORT 1883
#define MQTT_CLIENT "esp32-energy-monitor"

#define CURRENT_PIN 34
#define VOLTAGE_PIN 35
#define RELAY_1 26
#define RELAY_2 27
#define RELAY_3 14
#define RELAY_4 12

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

WiFiClient espClient;
PubSubClient mqtt(espClient);

const float VCC = 3.3;
const float ADC_RESOLUTION = 4095.0;
const float ACS712_SENSITIVITY = 0.066;
const float ACS712_ZERO = 2048;
const float VOLTAGE_RATIO = 230.0 / 1024.0;

float voltage = 0, current = 0, power = 0, energy = 0;
float smoothV = 0, smoothI = 0;
unsigned long lastRead = 0;
const int READ_INTERVAL = 2000;

const float POWER_THRESHOLD = 2000;
bool relayAutoMode = true;

void setup() {
  Serial.begin(115200);

  pinMode(RELAY_1, OUTPUT);
  pinMode(RELAY_2, OUTPUT);
  pinMode(RELAY_3, OUTPUT);
  pinMode(RELAY_4, OUTPUT);
  digitalWrite(RELAY_1, HIGH);
  digitalWrite(RELAY_2, HIGH);
  digitalWrite(RELAY_3, HIGH);
  digitalWrite(RELAY_4, HIGH);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.display();
  delay(1000);
  display.clearDisplay();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());

  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);

  displayMessage("System Ready", WiFi.localIP().toString().c_str());
}

void loop() {
  if (!mqtt.connected()) {
    reconnectMQTT();
  }
  mqtt.loop();

  if (millis() - lastRead >= READ_INTERVAL) {
    lastRead = millis();
    readSensors();
    calculateEnergy();
    displayReadings();
    publishData();
    checkThresholds();
  }
}

void readSensors() {
  int adcCurrent = analogRead(CURRENT_PIN);
  float voltageOut = (adcCurrent / ADC_RESOLUTION) * VCC;
  current = ((voltageOut - (VCC / 2)) / ACS712_SENSITIVITY);
  current = abs(current);

  int adcVoltage = analogRead(VOLTAGE_PIN);
  float voltageOutZMPT = (adcVoltage / ADC_RESOLUTION) * VCC;
  voltage = voltageOutZMPT * VOLTAGE_RATIO * 10;

  smoothV = smoothV * 0.7 + voltage * 0.3;
  smoothI = smoothI * 0.7 + current * 0.3;
  voltage = smoothV;
  current = smoothI;
}

void calculateEnergy() {
  float powerFactor = 0.85;
  power = voltage * current * powerFactor;
  energy += (power / 3600000.0) * READ_INTERVAL;
}

void displayReadings() {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.print("V: ");
  display.print(voltage, 1);
  display.println(" V");
  display.print("I: ");
  display.print(current, 2);
  display.println(" A");
  display.print("P: ");
  display.print(power, 1);
  display.println(" W");
  display.print("E: ");
  display.print(energy, 3);
  display.println(" kWh");
  display.display();
}

void publishData() {
  if (mqtt.connected()) {
    StaticJsonDocument<256> doc;
    doc["voltage"] = voltage;
    doc["current"] = current;
    doc["power"] = power;
    doc["energy"] = energy;
    doc["timestamp"] = millis();

    char buffer[256];
    serializeJson(doc, buffer);
    mqtt.publish("energy/readings", buffer);
  }
}

void checkThresholds() {
  if (relayAutoMode && power > POWER_THRESHOLD) {
    digitalWrite(RELAY_1, HIGH);
    Serial.println("ALERT: Power threshold exceeded! Relay 1 OFF");

    StaticJsonDocument<128> alert;
    alert["type"] = "threshold";
    alert["message"] = "Power exceeded threshold";
    alert["power"] = power;
    char buffer[128];
    serializeJson(alert, buffer);
    mqtt.publish("energy/alert", buffer);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  StaticJsonDocument<128> doc;
  deserializeJson(doc, message);

  if (String(topic) == "energy/relay/1") {
    if (doc["state"] == "ON") {
      digitalWrite(RELAY_1, LOW);
    } else {
      digitalWrite(RELAY_1, HIGH);
    }
  }
  if (String(topic) == "energy/relay/auto") {
    relayAutoMode = doc["enabled"];
  }
}

void reconnectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    if (mqtt.connect(MQTT_CLIENT)) {
      Serial.println("connected");
      mqtt.subscribe("energy/relay/1");
      mqtt.subscribe("energy/relay/auto");
    } else {
      Serial.print("failed, rc=");
      Serial.println(mqtt.state());
      delay(5000);
    }
  }
}

void displayMessage(const char* line1, const char* line2) {
  display.clearDisplay();
  display.setCursor(0, 20);
  display.setTextSize(1);
  display.println(line1);
  display.println(line2);
  display.display();
}
