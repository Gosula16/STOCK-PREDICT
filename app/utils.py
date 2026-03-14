import os
from datetime import datetime, timedelta

import pandas as pd
import requests


def _get_api_key() -> str | None:
    return os.environ.get("BMRS_API_KEY")


def _bmrs_api_url(dataset: str) -> str:
    # BMRS API base endpoint for dataset streaming.
    # This is based on ELEXON BMRS documentation.
    return f"https://api.bmreports.com/BMRS/{dataset}/v1"


def _parse_datetime(s: str) -> datetime:
    # BMRS timestamps are typically in UTC and formatted like 2024-01-01 00:00:00
    # Accept both with and without timezone information.
    return pd.to_datetime(s, utc=True)


def fetch_bmrs_dataset_csv(dataset: str, from_date: str, to_date: str, extra_params: dict | None = None) -> pd.DataFrame:
    """Fetch BMRS dataset in CSV format and return as a pandas DataFrame.

    Args:
        dataset: Dataset code such as "FUELHH" or "WINDFOR".
        from_date: YYYY-MM-DD
        to_date: YYYY-MM-DD
        extra_params: Additional query params.

    Returns:
        DataFrame with parsed datetimes.

    Note: The BMRS API may require an API key. Set BMRS_API_KEY environment variable.
    """

    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "BMRS_API_KEY environment variable is not set. Please set it to your BMRS API key."
        )

    params = {
        "APIKey": api_key,
        "FromDate": from_date,
        "ToDate": to_date,
        "ServiceType": "csv",
    }
    if extra_params:
        params.update(extra_params)

    url = _bmrs_api_url(dataset)
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    # The BMRS CSV response includes header lines that may start with "#".
    # Let pandas handle the CSV parsing.
    import io

    df = pd.read_csv(io.StringIO(r.text), comment="#")

    # Standardize column names
    df.columns = [c.strip() for c in df.columns]

    return df


def load_actuals_jan2024() -> pd.DataFrame:
    """Load UK wind actual generation for January 2024."""

    df = fetch_bmrs_dataset_csv("FUELHH", "2024-01-01", "2024-01-31", extra_params={"FuelType": "WIND"})

    # Make sure the dataset uses the expected fields
    # The FUELHH dataset has fields like StartTime and Generation.
    # Normalize column names for convenience.
    df = df.rename(columns={
        "StartTime": "startTime",
        "Generation": "generation",
    })

    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df.sort_values("startTime").reset_index(drop=True)
    df = df[["startTime", "generation"]]
    return df


def load_forecasts_jan2024() -> pd.DataFrame:
    """Load UK wind forecast generation for January 2024."""
    df = fetch_bmrs_dataset_csv("WINDFOR", "2024-01-01", "2024-01-31")

    # The dataset uses StartTime and PublishTime.
    df = df.rename(columns={
        "StartTime": "startTime",
        "PublishTime": "publishTime",
        "Generation": "generation",
    })

    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.sort_values(["startTime", "publishTime"]).reset_index(drop=True)

    return df[["startTime", "publishTime", "generation"]]


def build_forecast_series(
    forecasts: pd.DataFrame, horizon_hours: int, start: datetime, end: datetime
) -> pd.DataFrame:
    """For each target time between start and end, pick the latest forecast created at least horizon_hours before."""

    # Filter to requested target window
    mask = (forecasts["startTime"] >= pd.to_datetime(start)) & (forecasts["startTime"] <= pd.to_datetime(end))
    f = forecasts.loc[mask].copy()

    # Compute latest allowed publish time for each target
    f["max_publish"] = f["startTime"] - pd.Timedelta(hours=horizon_hours)

    # We need for each startTime, the forecast with publishTime <= max_publish and highest publishTime.
    # We'll filter and then take the max publishTime.
    f = f[f["publishTime"] <= f["max_publish"]]

    if f.empty:
        return pd.DataFrame(columns=["startTime", "generation"])

    # Keep the latest forecast per startTime
    idx = f.groupby("startTime")["publishTime"].idxmax()
    selected = f.loc[idx, ["startTime", "generation"]].reset_index(drop=True)
    return selected


def align_actuals_and_forecasts(
    actuals: pd.DataFrame, forecasts: pd.DataFrame, horizon_hours: int, start: datetime, end: datetime
) -> pd.DataFrame:
    """Return combined DataFrame containing actual and selected forecast values."""

    # Use target window as provided
    act = actuals[(actuals["startTime"] >= pd.to_datetime(start)) & (actuals["startTime"] <= pd.to_datetime(end))].copy()

    fc = build_forecast_series(forecasts, horizon_hours, start, end)

    merged = pd.merge(act, fc, on="startTime", how="left", suffixes=("_actual", "_forecast"))
    merged = merged.sort_values("startTime").reset_index(drop=True)
    merged = merged.rename(columns={"generation_actual": "actual", "generation_forecast": "forecast"})
    return merged
