import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import datetime

class TestEnergyPredictor(unittest.TestCase):
    def setUp(self):
        from server.models.energy_model import EnergyPredictor
        self.predictor = EnergyPredictor()

    def test_create_features(self):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=48, freq='1h'),
            'power': np.random.uniform(100, 1000, 48)
        })
        result = self.predictor.create_features(df.copy())

        self.assertIn('hour', result.columns)
        self.assertIn('hour_sin', result.columns)
        self.assertIn('hour_cos', result.columns)
        self.assertIn('lag_1', result.columns)
        self.assertIn('lag_24', result.columns)
        self.assertIn('rolling_mean_6', result.columns)

    def test_predict_returns_24_hours(self):
        predictions = self.predictor.predict_next_24h()
        self.assertIsInstance(predictions, list)
        self.assertEqual(len(predictions), 24)

    def test_predict_each_has_power(self):
        predictions = self.predictor.predict_next_24h()
        for pred in predictions:
            self.assertIn('predicted_power', pred)
            self.assertIn('hour', pred)
            self.assertIn('time', pred)

class TestDatabase(unittest.TestCase):
    def setUp(self):
        from server.database import Database
        self.db = Database(':memory:')
        self.db.init_db()

    def test_insert_and_get_latest(self):
        self.db.insert_reading({
            'voltage': 230.5,
            'current': 4.2,
            'power': 820.0,
            'energy': 1.5
        })
        latest = self.db.get_latest_reading()
        self.assertIsNotNone(latest)
        self.assertEqual(latest['voltage'], 230.5)
        self.assertEqual(latest['power'], 820.0)

    def test_insert_alert(self):
        self.db.insert_alert({
            'type': 'threshold',
            'message': 'Power exceeded 2000W'
        })
        alerts = self.db.get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], 'threshold')

    def test_get_history_returns_data(self):
        self.db.insert_reading({
            'voltage': 230.0,
            'current': 5.0,
            'power': 980.0,
            'energy': 0.5
        })
        history = self.db.get_history(hours=24)
        self.assertGreater(len(history), 0)

class TestSampleDataGenerator(unittest.TestCase):
    def test_generate_creates_csv(self):
        import os
        from generate_data import generate_sample_data

        test_path = 'data/test_sample.csv'
        df = generate_sample_data(days=7, output_path=test_path)

        self.assertTrue(os.path.exists(test_path))
        self.assertEqual(len(df), 7 * 24)
        self.assertIn('timestamp', df.columns)
        self.assertIn('power', df.columns)
        self.assertIn('voltage', df.columns)

        os.remove(test_path)

if __name__ == '__main__':
    unittest.main()
