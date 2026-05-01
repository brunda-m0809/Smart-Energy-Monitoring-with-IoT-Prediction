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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                action VARCHAR(50),
                success BOOLEAN,
                ip_address VARCHAR(45)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relay_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel INTEGER,
                state BOOLEAN,
                last_changed DATETIME DEFAULT CURRENT_TIMESTAMP,
                triggered_by VARCHAR(50)
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

    def log_access(self, user_id, action, success, ip_address='unknown'):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO access_logs (user_id, action, success, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (user_id, action, success, ip_address))
        conn.commit()
        conn.close()
