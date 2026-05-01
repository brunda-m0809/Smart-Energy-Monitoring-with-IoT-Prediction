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

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPICS = ["energy/readings", "energy/alert"]

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT with result code {rc}")
    for topic in MQTT_TOPICS:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())

    if msg.topic == "energy/readings":
        db.insert_reading(data)
        socketio.emit('new_reading', data)

    elif msg.topic == "energy/alert":
        db.insert_alert(data)
        socketio.emit('new_alert', data)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

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
