"""Generate sample CSV data for the app to use when BMRS_API_KEY is not available."""

from datetime import datetime, timedelta
import math
import os

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Generate actual generation samples for January 2024 at 30-minute intervals.
start = datetime(2024, 1, 1)
end = datetime(2024, 1, 31, 23, 30)

rows = []
current = start
while current <= end:
    # Simulate wind generation with a daily cycle + randomness.
    hours = current.hour + current.minute / 60.0
    base = 2000 + 1200 * math.sin((hours / 24.0) * 2 * math.pi)
    noise = 200 * math.sin((current.timetuple().tm_yday / 365.0) * 2 * math.pi)  # seasonal
    value = max(0, base + noise + (100 * (0.5 - math.sin(current.timestamp() / 3600))))
    rows.append({"StartTime": current.strftime("%Y-%m-%d %H:%M:%S"), "Generation": round(value, 1)})
    current += timedelta(minutes=30)

actual_df = pd.DataFrame(rows)
actual_df.to_csv(os.path.join(DATA_DIR, "sample_actuals.csv"), index=False)

# Generate forecasts by shifting random hours earlier and adding a small bias.
# For each target time, create forecasts published 1h, 4h, 12h, 24h before.
forecast_rows = []
for _, row in actual_df.iterrows():
    start_time = datetime.strptime(row["StartTime"], "%Y-%m-%d %H:%M:%S")
    actual_gen = float(row["Generation"])
    for horizon in [1, 4, 12, 24]:
        publish_time = start_time - timedelta(hours=horizon)
        # Use actual value plus a horizon-dependent noise
        forecast_value = actual_gen + (horizon * 5) * (0.5 - math.sin(publish_time.timestamp() / 3600))
        forecast_rows.append({
            "StartTime": row["StartTime"],
            "PublishTime": publish_time.strftime("%Y-%m-%d %H:%M:%S"),
            "Generation": round(max(0, forecast_value), 1),
        })

forecast_df = pd.DataFrame(forecast_rows)
forecast_df.to_csv(os.path.join(DATA_DIR, "sample_forecasts.csv"), index=False)

print(f"Generated sample data in {DATA_DIR}")
