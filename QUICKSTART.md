# QUICK-START IMPLEMENTATION GUIDE

## Prerequisites

- Arduino IDE 2.x or PlatformIO
- Python 3.10+
- Node.js 18+ (optional, for dashboard)
- Mosquitto MQTT broker
- Git

---

## Step 1: ESP32 Firmware

### Install Libraries (Arduino IDE)

```
Tools > Manage Libraries > Search & Install:
- PubSubClient (Nick O'Leary)
- Adafruit SSD1306
- Adafruit GFX Library
- ArduinoJson
```

### Main Firmware: `smart_energy_monitor.ino`

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>

// WiFi Credentials
#define WIFI_SSID "Your_WiFi_SSID"
#define WIFI_PASSWORD "Your_WiFi_Password"

// MQTT Configuration
#define MQTT_SERVER "192.168.1.100"
#define MQTT_PORT 1883
#define MQTT_CLIENT "esp32-energy-monitor"

// Pin Definitions
#define CURRENT_PIN 34    // ACS712
#define VOLTAGE_PIN 35    // ZMPT101B
#define RELAY_1 26
#define RELAY_2 27
#define RELAY_3 14
#define RELAY_4 12

// OLED
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

WiFiClient espClient;
PubSubClient mqtt(espClient);

// Calibration values
const float VCC = 3.3;
const float ADC_RESOLUTION = 4095.0;
const float ACS712_SENSITIVITY = 0.066;  // 66mV/A for 30A version
const float ACS712_ZERO = 2048;          // Mid-point of ADC
const float VOLTAGE_RATIO = 230.0 / 1024.0;  // Calibration factor

float voltage = 0, current = 0, power = 0, energy = 0;
unsigned long lastRead = 0;
const int READ_INTERVAL = 2000;  // 2 seconds

// Thresholds
const float POWER_THRESHOLD = 2000;  // Watts
bool relayAutoMode = true;

void setup() {
  Serial.begin(115200);

  // Initialize relays
  pinMode(RELAY_1, OUTPUT);
  pinMode(RELAY_2, OUTPUT);
  pinMode(RELAY_3, OUTPUT);
  pinMode(RELAY_4, OUTPUT);
  digitalWrite(RELAY_1, HIGH);  // Active LOW relays
  digitalWrite(RELAY_2, HIGH);
  digitalWrite(RELAY_3, HIGH);
  digitalWrite(RELAY_4, HIGH);

  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.display();
  delay(1000);
  display.clearDisplay();

  // Connect WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());

  // Setup MQTT
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);

  displayMessage("System Ready", WiFi.localIP().toString().c_str());
}

void loop() {
  // Maintain MQTT connection
  if (!mqtt.connected()) {
    reconnectMQTT();
  }
  mqtt.loop();

  // Read sensors every 2 seconds
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
  // Read current (ACS712)
  int adcCurrent = analogRead(CURRENT_PIN);
  float voltageOut = (adcCurrent / ADC_RESOLUTION) * VCC;
  current = ((voltageOut - (VCC / 2)) / ACS712_SENSITIVITY);
  current = abs(current);  // Absolute value

  // Read voltage (ZMPT101B)
  int adcVoltage = analogRead(VOLTAGE_PIN);
  float voltageOutZMPT = (adcVoltage / ADC_RESOLUTION) * VCC;
  // Convert to AC RMS (simplified - use proper calibration)
  voltage = voltageOutZMPT * VOLTAGE_RATIO * 10;

  // Apply smoothing (moving average)
  static float smoothV = 0, smoothI = 0;
  smoothV = smoothV * 0.7 + voltage * 0.3;
  smoothI = smoothI * 0.7 + current * 0.3;
  voltage = smoothV;
  current = smoothI;
}

void calculateEnergy() {
  float powerFactor = 0.85;  // Assume PF for resistive loads
  power = voltage * current * powerFactor;
  energy += (power / 3600000.0) * READ_INTERVAL;  // kWh
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
    digitalWrite(RELAY_1, HIGH);  // Turn off relay 1
    Serial.println("ALERT: Power threshold exceeded! Relay 1 OFF");

    // Publish alert
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
```

---

## Step 2: MQTT Broker Setup

### Install Mosquitto (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### Test MQTT

```bash
# Subscribe to topic (terminal 1)
mosquitto_sub -t "energy/readings" -v

# Publish test message (terminal 2)
mosquitto_pub -t "energy/readings" -m '{"voltage":230,"current":5,"power":1150}'
```

---

## Step 3: Backend Server (Python Flask)

### Install Dependencies

```bash
pip install flask flask-cors flask-socketio paho-mqtt numpy pandas scikit-learn tensorflow joblib opencv-python face_recognition dlib sqlite3
```

### Project Structure

```
server/
├── app.py
├── models/
│   ├── __init__.py
│   ├── energy_model.py
│   └── face_auth.py
├── database.py
├── mqtt_handler.py
├── templates/
│   ├── index.html
│   └── login.html
└── static/
    ├── css/
    └── js/
```

### Main Server: `server/app.py`

```python
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import json
import sqlite3
import datetime
import threading
from models.energy_model import EnergyPredictor
from models.face_auth import FaceAuthenticator
from database import Database

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

db = Database('energy_monitor.db')
predictor = EnergyPredictor()
face_auth = FaceAuthenticator()

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPICS = ["energy/readings", "energy/alert"]

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT with result code {rc}")
    for topic in MQTT_TOPICS:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())

    if msg.topic == "energy/readings":
        db.insert_reading(data)
        # Broadcast to all connected clients
        socketio.emit('new_reading', data)

    elif msg.topic == "energy/alert":
        db.insert_alert(data)
        socketio.emit('new_alert', data)

# Initialize MQTT
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/api/data/latest')
def get_latest():
    reading = db.get_latest_reading()
    return jsonify(reading)

@app.route('/api/data/history')
def get_history():
    hours = request.args.get('hours', 24, type=int)
    data = db.get_history(hours)
    return jsonify(data)

@app.route('/api/predict')
def get_prediction():
    predictions = predictor.predict_next_24h()
    return jsonify(predictions)

@app.route('/api/auth/face', methods=['POST'])
def authenticate_face():
    if 'image' not in request.files:
        return jsonify({'error': 'No image'}), 400

    image = request.files['image']
    result = face_auth.authenticate(image)

    if result['success']:
        return jsonify({
            'success': True,
            'user': result['user'],
            'token': 'jwt_token_placeholder'
        })
    return jsonify({'success': False, 'message': 'Face not recognized'}), 401

@app.route('/api/auth/register', methods=['POST'])
def register_face():
    name = request.form.get('name')
    image = request.files['image']
    result = face_auth.register(name, image)
    return jsonify(result)

@app.route('/api/relay/control', methods=['POST'])
def control_relay():
    channel = request.json.get('channel')
    state = request.json.get('state')
    mqtt_client.publish(f'energy/relay/{channel}', json.dumps({'state': state}))
    return jsonify({'success': True})

@app.route('/api/alerts')
def get_alerts():
    alerts = db.get_alerts(limit=50)
    return jsonify(alerts)

@app.route('/api/dashboard')
def dashboard_summary():
    latest = db.get_latest_reading()
    today_energy = db.get_today_energy()
    prediction = predictor.predict_next_24h()
    alerts = db.get_unacknowledged_alerts()

    return jsonify({
        'latest': latest,
        'today_energy': today_energy,
        'prediction': prediction,
        'alerts_count': len(alerts)
    })

if __name__ == '__main__':
    db.init_db()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

### Database: `server/database.py`

```python
import sqlite3
import datetime

class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                voltage REAL,
                current REAL,
                power REAL,
                energy REAL,
                power_factor REAL DEFAULT 0.85
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                target_time DATETIME,
                predicted_power REAL,
                actual_power REAL,
                model_version VARCHAR(50)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100),
                face_encoding BLOB,
                role VARCHAR(20) DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                type VARCHAR(50),
                message TEXT,
                acknowledged BOOLEAN DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def insert_reading(self, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO energy_readings (voltage, current, power, energy)
            VALUES (?, ?, ?, ?)
        ''', (data.get('voltage'), data.get('current'),
              data.get('power'), data.get('energy')))
        conn.commit()
        conn.close()

    def get_latest_reading(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM energy_readings ORDER BY timestamp DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_history(self, hours=24):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM energy_readings
            WHERE timestamp > datetime('now', ?)
            ORDER BY timestamp ASC
        ''', (f'-{hours} hours',))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_today_energy(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(energy) - MIN(energy) as today_consumption
            FROM energy_readings
            WHERE date(timestamp) = date('now')
        ''')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def insert_alert(self, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (type, message) VALUES (?, ?)
        ''', (data.get('type', 'unknown'), data.get('message', '')))
        conn.commit()
        conn.close()

    def get_alerts(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_unacknowledged_alerts(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM alerts WHERE acknowledged = 0')
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
```

### ML Model: `server/models/energy_model.py`

```python
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
import datetime

class EnergyPredictor:
    def __init__(self, model_path='models/energy_model.pkl'):
        self.model_path = model_path
        self.model = None
        self.scaler = MinMaxScaler()

        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=15,
                random_state=42
            )

    def create_features(self, df):
        """Create time-based features for prediction"""
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

        # Cyclic encoding for hour
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

        # Lag features
        df['lag_1'] = df['power'].shift(1)
        df['lag_24'] = df['power'].shift(24)

        # Rolling statistics
        df['rolling_mean_6'] = df['power'].rolling(window=6).mean()
        df['rolling_std_6'] = df['power'].rolling(window=6).std()

        return df

    def train(self, data_path='data/training_data.csv'):
        """Train the prediction model"""
        df = pd.read_csv(data_path, parse_dates=['timestamp'])
        df = self.create_features(df)
        df = df.dropna()

        feature_cols = ['hour_sin', 'hour_cos', 'day_of_week', 'is_weekend',
                        'lag_1', 'lag_24', 'rolling_mean_6', 'rolling_std_6']

        X = df[feature_cols]
        y = df['power']

        # Split data
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # Train
        self.model.fit(X_train, y_train)

        # Evaluate
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        y_pred = self.model.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        print(f"MAE: {mae:.2f}W | RMSE: {rmse:.2f}W | R2: {r2:.4f}")

        # Save model
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.model, self.model_path)

        return {'mae': mae, 'rmse': rmse, 'r2': r2}

    def predict_next_24h(self):
        """Predict energy consumption for next 24 hours"""
        if self.model is None:
            return {'error': 'Model not trained'}

        now = datetime.datetime.now()
        predictions = []

        for h in range(1, 25):
            future_time = now + datetime.timedelta(hours=h)

            # Create features for future hour
            hour = future_time.hour
            day_of_week = future_time.weekday()
            is_weekend = 1 if day_of_week >= 5 else 0

            features = np.array([[
                np.sin(2 * np.pi * hour / 24),
                np.cos(2 * np.pi * hour / 24),
                day_of_week,
                is_weekend,
                0,  # lag_1 (placeholder)
                0,  # lag_24 (placeholder)
                0,  # rolling_mean (placeholder)
                0   # rolling_std (placeholder)
            ]])

            pred_power = self.model.predict(features)[0]
            predictions.append({
                'time': future_time.isoformat(),
                'hour': hour,
                'predicted_power': round(pred_power, 2)
            })

        return predictions
```

### Face Authentication: `server/models/face_auth.py`

```python
import cv2
import numpy as np
import face_recognition
import pickle
import os

class FaceAuthenticator:
    def __init__(self, encodings_path='data/face_encodings.pkl'):
        self.encodings_path = encodings_path
        self.known_encodings = {}
        self.known_names = []
        self.threshold = 0.6

        if os.path.exists(encodings_path):
            self.load_encodings()

    def load_encodings(self):
        with open(self.encodings_path, 'rb') as f:
            data = pickle.load(f)
            self.known_encodings = data['encodings']
            self.known_names = data['names']

    def save_encodings(self):
        os.makedirs('data', exist_ok=True)
        with open(self.encodings_path, 'wb') as f:
            pickle.dump({
                'encodings': self.known_encodings,
                'names': self.known_names
            }, f)

    def register(self, name, image_file):
        """Register a new face"""
        img = cv2.imdecode(np.frombuffer(image_file.read(), np.uint8), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        encodings = face_recognition.face_encodings(rgb)

        if len(encodings) == 0:
            return {'success': False, 'message': 'No face detected'}

        encoding = encodings[0]
        self.known_encodings[name] = encoding.tolist()
        self.known_names.append(name)
        self.save_encodings()

        return {'success': True, 'message': f'User {name} registered'}

    def authenticate(self, image_file):
        """Authenticate a face against database"""
        img = cv2.imdecode(np.frombuffer(image_file.read(), np.uint8), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        encodings = face_recognition.face_encodings(rgb)

        if len(encodings) == 0:
            return {'success': False, 'message': 'No face detected'}

        face_encoding = encodings[0]
        best_match = None
        best_distance = float('inf')

        for name, stored_encoding in self.known_encodings.items():
            distance = face_recognition.face_distance(
                [np.array(stored_encoding)], face_encoding
            )[0]

            if distance < best_distance:
                best_distance = distance
                best_match = name

        if best_distance < self.threshold:
            return {
                'success': True,
                'user': best_match,
                'confidence': round((1 - best_distance) * 100, 2)
            }

        return {
            'success': False,
            'message': 'Face not recognized',
            'distance': round(best_distance, 3)
        }
```

---

## Step 4: Dashboard Frontend

### `server/templates/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Energy Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }

        .header {
            background: linear-gradient(135deg, #1e293b, #334155);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #3b82f6;
        }
        .header h1 { font-size: 24px; }
        .status { display: flex; align-items: center; gap: 8px; }
        .status-dot { width: 10px; height: 10px; border-radius: 50%; background: #22c55e; }

        .dashboard {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            padding: 20px;
        }

        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        .card h3 { color: #94a3b8; font-size: 14px; margin-bottom: 10px; }
        .card .value { font-size: 32px; font-weight: bold; }
        .card .unit { font-size: 16px; color: #64748b; }

        .card.voltage .value { color: #f59e0b; }
        .card.current .value { color: #3b82f6; }
        .card.power .value { color: #22c55e; }
        .card.energy .value { color: #a855f7; }

        .chart-container {
            grid-column: span 2;
            min-height: 300px;
        }
        .chart-container.full { grid-column: span 4; }

        .alerts {
            grid-column: span 4;
            max-height: 200px;
            overflow-y: auto;
        }
        .alert-item {
            padding: 10px;
            margin: 5px 0;
            border-radius: 8px;
            background: #334155;
            border-left: 4px solid #ef4444;
        }

        @media (max-width: 768px) {
            .dashboard { grid-template-columns: repeat(2, 1fr); }
            .chart-container, .chart-container.full, .alerts { grid-column: span 2; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Smart Energy Monitoring System</h1>
        <div class="status">
            <div class="status-dot"></div>
            <span>Live</span>
        </div>
    </div>

    <div class="dashboard">
        <div class="card voltage">
            <h3>VOLTAGE</h3>
            <div class="value" id="voltage">0.0</div>
            <div class="unit">Volts (V)</div>
        </div>
        <div class="card current">
            <h3>CURRENT</h3>
            <div class="value" id="current">0.00</div>
            <div class="unit">Amperes (A)</div>
        </div>
        <div class="card power">
            <h3>POWER</h3>
            <div class="value" id="power">0.0</div>
            <div class="unit">Watts (W)</div>
        </div>
        <div class="card energy">
            <h3>ENERGY</h3>
            <div class="value" id="energy">0.000</div>
            <div class="unit">Kilowatt-hours (kWh)</div>
        </div>

        <div class="card chart-container">
            <h3>POWER TREND (24H)</h3>
            <canvas id="powerChart"></canvas>
        </div>
        <div class="card chart-container">
            <h3>PREDICTION vs ACTUAL</h3>
            <canvas id="predictionChart"></canvas>
        </div>

        <div class="card chart-container full">
            <h3>ENERGY CONSUMPTION (7 DAYS)</h3>
            <canvas id="weeklyChart"></canvas>
        </div>

        <div class="card alerts">
            <h3>RECENT ALERTS</h3>
            <div id="alertList"></div>
        </div>
    </div>

    <script>
        const socket = io();

        // Chart initialization
        const powerCtx = document.getElementById('powerChart').getContext('2d');
        const powerChart = new Chart(powerCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Power (W)',
                    data: [],
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#94a3b8' } },
                    y: { ticks: { color: '#94a3b8' } }
                }
            }
        });

        const predCtx = document.getElementById('predictionChart').getContext('2d');
        const predictionChart = new Chart(predCtx, {
            type: 'line',
            data: {
                labels: Array.from({length: 24}, (_, i) => `${i}:00`),
                datasets: [
                    {
                        label: 'Actual',
                        data: [],
                        borderColor: '#3b82f6',
                        tension: 0.4
                    },
                    {
                        label: 'Predicted',
                        data: [],
                        borderColor: '#f59e0b',
                        borderDash: [5, 5],
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: { ticks: { color: '#94a3b8' } },
                    y: { ticks: { color: '#94a3b8' } }
                }
            }
        });

        // WebSocket real-time updates
        socket.on('new_reading', function(data) {
            document.getElementById('voltage').textContent = data.voltage.toFixed(1);
            document.getElementById('current').textContent = data.current.toFixed(2);
            document.getElementById('power').textContent = data.power.toFixed(1);
            document.getElementById('energy').textContent = data.energy.toFixed(3);

            // Update power chart
            const now = new Date().toLocaleTimeString();
            if (powerChart.data.labels.length > 50) {
                powerChart.data.labels.shift();
                powerChart.data.datasets[0].data.shift();
            }
            powerChart.data.labels.push(now);
            powerChart.data.datasets[0].data.push(data.power);
            powerChart.update();
        });

        socket.on('new_alert', function(data) {
            const alertList = document.getElementById('alertList');
            const alert = document.createElement('div');
            alert.className = 'alert-item';
            alert.innerHTML = `<strong>${data.type}</strong>: ${data.message}`;
            alertList.insertBefore(alert, alertList.firstChild);
        });

        // Load initial data
        async function loadHistory() {
            const response = await fetch('/api/data/history?hours=24');
            const data = await response.json();
            if (data.length) {
                powerChart.data.labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
                powerChart.data.datasets[0].data = data.map(d => d.power);
                powerChart.update();
            }
        }

        async function loadPredictions() {
            const response = await fetch('/api/predict');
            const data = await response.json();
            if (data.predictions) {
                predictionChart.data.datasets[1].data =
                    data.predictions.map(p => p.predicted_power);
                predictionChart.update();
            }
        }

        loadHistory();
        loadPredictions();
        setInterval(loadPredictions, 3600000);  // Update predictions every hour
    </script>
</body>
</html>
```

---

## Step 5: Run Everything

### Terminal 1 - MQTT Broker

```bash
mosquitto -c /etc/mosquitto/mosquitto.conf
```

### Terminal 2 - Backend Server

```bash
cd server
python app.py
```

### Terminal 3 - (Optional) Train ML Model

```bash
python -c "
from server.models.energy_model import EnergyPredictor
predictor = EnergyPredictor()
# Generate sample data first, then train
predictor.train('data/training_data.csv')
"
```

### Terminal 4 - ESP32

```
Upload the .ino sketch via Arduino IDE
```

### Access Dashboard

Open browser to: **http://localhost:5000**

---

## Step 6: Face Recognition Setup

### Install face_recognition dependencies

```bash
# Ubuntu/Debian
sudo apt-get install cmake libopenblas-dev liblapack-dev libjpeg-dev

pip install face_recognition dlib
```

### Register a Face

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -F "name=John" \
  -F "image=@/path/to/face_photo.jpg"
```

### Test Authentication

```bash
curl -X POST http://localhost:5000/api/auth/face \
  -F "image=@/path/to/test_photo.jpg"
```

---

## Step 7: Project Directory Structure

```
smart-energy-monitoring/
├── docs/
│   ├── PROJECT_REPORT.md          ← Full project report
│   ├── DIAGRAMS.md                ← All diagrams (Mermaid)
│   └── QUICKSTART.md              ← This file
│
├── firmware/
│   └── smart_energy_monitor/
│       ├── smart_energy_monitor.ino
│       └── platformio.ini
│
├── server/
│   ├── app.py                     ← Flask backend
│   ├── database.py                ← SQLite operations
│   ├── mqtt_handler.py            ← MQTT subscriber
│   ├── models/
│   │   ├── energy_model.py        ← ML prediction
│   │   └── face_auth.py           ← Face recognition
│   ├── templates/
│   │   ├── index.html             ← Dashboard
│   │   └── login.html             ← Face login page
│   └── static/
│       ├── css/style.css
│       └── js/main.js
│
├── data/
│   ├── training_data.csv          ← ML training dataset
│   └── face_encodings.pkl         ← Registered faces
│
├── models/
│   └── energy_model.pkl           ← Trained ML model
│
├── tests/
│   ├── test_sensors.py
│   ├── test_ml_model.py
│   └── test_face_auth.py
│
└── README.md
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ESP32 won't connect to WiFi | Check SSID/password, ensure 2.4GHz network |
| MQTT connection refused | Verify Mosquitto is running: `sudo systemctl status mosquitto` |
| ACS712 reads 0 always | Check wiring, ensure load is connected |
| ZMPT101B inaccurate | Recalibrate with known voltage source |
| Face recognition fails | Ensure good lighting, face is centered |
| ML model not predicting | Check if training data exists, verify features |
| Dashboard not updating | Check WebSocket connection in browser console |
| High prediction error | Collect more training data, tune hyperparameters |

---

## Sample Training Data Generator

```python
import pandas as pd
import numpy as np
import datetime

def generate_sample_data(days=30, output_path='data/training_data.csv'):
    """Generate realistic sample energy data for ML training"""

    timestamps = pd.date_range(
        start=datetime.datetime.now() - datetime.timedelta(days=days),
        end=datetime.datetime.now(),
        freq='1h'
    )

    data = []
    for ts in timestamps:
        hour = ts.hour
        day = ts.dayofweek

        # Base load pattern (typical residential)
        if 6 <= hour <= 9:
            base = 800   # Morning peak
        elif 12 <= hour <= 14:
            base = 600   # Lunch
        elif 18 <= hour <= 22:
            base = 1200  # Evening peak
        elif 0 <= hour <= 5:
            base = 200   # Night minimum
        else:
            base = 400   # Daytime

        # Weekend adjustment
        if day >= 5:
            base *= 1.2

        # Add noise
        power = base + np.random.normal(0, 50)
        power = max(50, power)  # Minimum 50W

        voltage = 230 + np.random.normal(0, 3)
        current = power / (voltage * 0.85)  # Assuming PF=0.85

        data.append({
            'timestamp': ts,
            'voltage': round(voltage, 1),
            'current': round(current, 3),
            'power': round(power, 1),
            'energy': round(power / 1000, 3)
        })

    df = pd.DataFrame(data)
    import os
    os.makedirs('data', exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} records -> {output_path}")
    return df

# Run: python -c "exec(open('generate_data.py').read())"
```
