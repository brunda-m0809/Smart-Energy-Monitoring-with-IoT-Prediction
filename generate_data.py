import pandas as pd
import numpy as np
import datetime
import os

def generate_sample_data(days=30, output_path='data/training_data.csv'):
    timestamps = pd.date_range(
        start=datetime.datetime.now() - datetime.timedelta(days=days),
        end=datetime.datetime.now(),
        freq='1h'
    )

    data = []
    for ts in timestamps:
        hour = ts.hour
        day = ts.dayofweek

        if 6 <= hour <= 9:
            base = 800
        elif 12 <= hour <= 14:
            base = 600
        elif 18 <= hour <= 22:
            base = 1200
        elif 0 <= hour <= 5:
            base = 200
        else:
            base = 400

        if day >= 5:
            base *= 1.2

        power = base + np.random.normal(0, 50)
        power = max(50, power)

        voltage = 230 + np.random.normal(0, 3)
        current = power / (voltage * 0.85)

        data.append({
            'timestamp': ts,
            'voltage': round(voltage, 1),
            'current': round(current, 3),
            'power': round(power, 1),
            'energy': round(power / 1000, 3)
        })

    df = pd.DataFrame(data)
    os.makedirs('data', exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} records -> {output_path}")
    return df

if __name__ == '__main__':
    generate_sample_data()
