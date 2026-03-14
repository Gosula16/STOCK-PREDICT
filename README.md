# Wind Forecast Monitoring Challenge

This repository contains a demo **Wind Power Forecast Monitoring** application and an accompanying **Jupyter notebook** for analyzing forecast errors and actual generation data for January 2024.

## Contents

- `app/` - Streamlit-based web app that visualizes actual vs forecast wind generation and supports configurable forecast horizon.
- `notebooks/analysis.ipynb` - Notebook exploring forecast error characteristics and recommending reliable MW capacity from wind.
- `.gitignore` - Excludes environment files and artifacts.

## Running the App (Local)

### 1) Setup

1. Create a Python virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r app/requirements.txt
```

### 2) Run

```powershell
cd app
streamlit run app.py
```

Then open the URL shown in the terminal (usually http://localhost:8501).

## Data Source

This app fetches data from the ELEXON BMRS API:

- Actual generation: `FUELHH` dataset (filter `fuelType=WIND`)
- Forecasts: `WINDFOR` dataset

> **Note:** The BMRS API may require an API key. The app is configured to read `BMRS_API_KEY` from environment variables.

## Deployment

### Heroku (example)

1. Create a new Heroku app.
2. Set environment variables:
   - `BMRS_API_KEY` (if required)
3. Push the repository.

### Vercel

A pure Python Streamlit app is not directly supported on Vercel, but can be deployed via platforms supporting Python web apps (Heroku, Render, Streamlit Cloud).

## Notebook

The notebook in `notebooks/analysis.ipynb`:

- Downloads January 2024 actual and forecast data.
- Computes forecast error metrics (MAE, RMSE, quantiles).
- Explores error variation with forecast horizon and time of day.
- Provides a recommendation for reliable MW capacity based on historical percentiles.

## Notes

- This project was bootstrapped as a technical challenge submission.
- The notebook is self-contained and uses `requests` to fetch data.

---
