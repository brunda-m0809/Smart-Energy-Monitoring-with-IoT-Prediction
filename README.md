# Smart Energy Monitoring System with IoT Prediction and Face Recognition

A comprehensive IoT-based energy monitoring system that combines real-time sensor data acquisition, machine learning-based consumption prediction, and face recognition security into a single deployable solution.

## Features

- Real-time voltage, current, power, and energy monitoring
- MQTT-based data transmission with WebSocket dashboard updates
- Machine learning prediction (Random Forest / LSTM) for 24-hour energy forecasting
- Face recognition authentication for secure dashboard access
- Smart alerts for threshold violations via Email/SMS
- Automated relay control based on consumption rules
- Web dashboard with real-time charts and historical data
- Cost-effective design (~$43 total hardware cost)

## System Architecture

```
Sensors (ACS712 + ZMPT101B) --> ESP32 --> MQTT Broker --> Flask Server --> Dashboard
ESP32-CAM --> Face Recognition --> Authentication --> Access Control
Historical Data --> ML Model --> Predictions --> Dashboard
```

## Hardware Requirements

| Component | Quantity | Approx Cost |
|-----------|----------|-------------|
| ESP32 DevKit V1 | 1 | $6 |
| ESP32-CAM | 1 | $10 |
| ACS712 (30A) Current Sensor | 1 | $2.50 |
| ZMPT101B Voltage Sensor | 1 | $4 |
| 4-Channel 5V Relay Module | 1 | $3.50 |
| 0.96" OLED Display (I2C) | 1 | $4 |
| Breadboard + Jumper Wires | 1 set | $5 |
| 5V Power Supply | 1 | $3 |
| Enclosure | 1 | $5 |
| **Total** | | **~$43** |

## Pin Connections

| Component | ESP32 Pin |
|-----------|-----------|
| ACS712 Output | GPIO34 (VP) |
| ZMPT101B Output | GPIO35 (VN) |
| Relay CH1 | GPIO26 |
| Relay CH2 | GPIO27 |
| Relay CH3 | GPIO14 |
| Relay CH4 | GPIO12 |
| OLED SDA | GPIO21 |
| OLED SCL | GPIO22 |

## Project Structure

```
Smart-Energy-Monitoring-with-IoT-Prediction/
├── firmware/
│   └── smart_energy_monitor/
│       └── smart_energy_monitor.ino      # ESP32 firmware
├── server/
│   ├── app.py                             # Flask backend
│   ├── database.py                        # SQLite operations
│   ├── models/
│   │   ├── energy_model.py                # ML prediction
│   │   └── face_auth.py                   # Face recognition
│   ├── templates/
│   │   ├── index.html                     # Dashboard
│   │   └── login.html                     # Face login
│   └── static/
│       ├── css/style.css
│       └── js/dashboard.js
├── data/                                  # Training data & face encodings
├── models/                                # Saved ML models
├── docs/                                  # Project documentation
├── tests/                                 # Unit tests
├── generate_data.py                       # Sample data generator
├── requirements.txt                       # Python dependencies
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install MQTT Broker

**Ubuntu/Debian:**
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

**Windows:** Download from https://mosquitto.org/download/

### 3. Generate Sample Training Data

```bash
python generate_data.py
```

### 4. Train the ML Model

```bash
cd server
python -c "
from models.energy_model import EnergyPredictor
p = EnergyPredictor()
p.train('../data/training_data.csv')
"
```

### 5. Register a Face

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -F "name=YourName" \
  -F "image=@path/to/your/face.jpg"
```

### 6. Run the Server

```bash
cd server
python app.py
```

### 7. Upload ESP32 Firmware

1. Open Arduino IDE
2. Install libraries: PubSubClient, Adafruit SSD1306, Adafruit GFX, ArduinoJson
3. Open `firmware/smart_energy_monitor/smart_energy_monitor.ino`
4. Update WiFi credentials and MQTT server IP
5. Upload to ESP32

### 8. Access Dashboard

Open browser to: **http://localhost:5000**

Login page: **http://localhost:5000/login**

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data/latest` | GET | Latest energy reading |
| `/api/data/history?hours=24` | GET | Historical data |
| `/api/predict` | GET | 24-hour prediction |
| `/api/auth/face` | POST | Face authentication |
| `/api/auth/register` | POST | Register new face |
| `/api/relay/control` | POST | Control relay |
| `/api/alerts` | GET | Alert history |
| `/api/dashboard` | GET | Dashboard summary |

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `energy/readings` | ESP32 --> Server | Sensor data |
| `energy/alert` | ESP32 --> Server | Alert trigger |
| `energy/relay/1` | Server --> ESP32 | Control relay 1 |
| `energy/relay/auto` | Server --> ESP32 | Toggle auto mode |

## Documentation

Full project report, diagrams, and implementation guide are available in the `docs/` folder:

- `docs/PROJECT_REPORT.md` - Complete college project report
- `docs/DIAGRAMS.md` - System architecture, flowcharts, and diagrams (Mermaid)
- `docs/QUICKSTART.md` - Detailed implementation guide with code

## Technologies Used

| Layer | Technology |
|-------|------------|
| Firmware | Arduino (C++) |
| Backend | Python Flask, Flask-SocketIO |
| Database | SQLite |
| ML | scikit-learn, TensorFlow (optional LSTM) |
| Face Recognition | OpenCV, face_recognition, dlib |
| Communication | MQTT (Mosquitto), WebSocket |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Hardware | ESP32, ESP32-CAM, ACS712, ZMPT101B |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ESP32 won't connect to WiFi | Check SSID/password, use 2.4GHz network |
| MQTT connection refused | Verify Mosquitto is running |
| ACS712 reads 0 | Check wiring, ensure load is connected |
| ZMPT101B inaccurate | Recalibrate with known voltage |
| Face recognition fails | Ensure good lighting, face centered |
| ML model not predicting | Run `generate_data.py` first, then train |
| Dashboard not updating | Check WebSocket in browser console |

## License

MIT License

## Contributors

- Brunda M - [brunda-m0809](https://github.com/brunda-m0809)

---

Built for 6th Semester ECE Project | Electronics and Communication Engineering
