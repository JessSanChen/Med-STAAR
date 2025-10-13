# app.py
from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

# -----------------------------
# Load CSVs once (simple, no caching layer)
# -----------------------------
hist_df = pd.read_csv("volume_forecaster/output/synthetic_data_long.csv")
hist_df["date"] = pd.to_datetime(hist_df["date"])
HIST_FACILITIES = sorted(hist_df["facility"].unique().tolist())

forecast_df = pd.read_csv("volume_forecaster/output/forecast_long.csv")
forecast_df["date"] = pd.to_datetime(forecast_df["date"])
FORECAST_FACILITIES = sorted(forecast_df["facility"].unique().tolist())

# -----------------------------
# Helpers
# -----------------------------
def facility_chart_payload(df: pd.DataFrame, facility: str):
    """
    Build a Chart.js-friendly payload for a single facility from the given DataFrame.
    Dates returned as YYYY-MM-DD (ISO), series for md1/md2/pm (0-filled).
    """
    if not facility:
        return None

    fac_norm = facility.strip().upper()
    sub = df[df["facility"].str.upper() == fac_norm]
    if sub.empty:
        return None

    pivot = (
        sub.pivot_table(index="date", columns="shift", values="volume", aggfunc="sum")
           .reindex(pd.date_range(sub["date"].min(), sub["date"].max(), freq="D"))
           .fillna(0)
           .sort_index()
    )

    for col in ["md1", "md2", "pm"]:
        if col not in pivot.columns:
            pivot[col] = 0.0
    pivot = pivot[["md1", "md2", "pm"]]

    labels = [d.strftime("%Y-%m-%d") for d in pivot.index]
    return {
        "labels": labels,
        "datasets": [
            {"label": "md1", "data": pivot["md1"].astype(float).tolist()},
            {"label": "md2", "data": pivot["md2"].astype(float).tolist()},
            {"label": "pm",  "data": pivot["pm"].astype(float).tolist()},
        ]
    }

def head_payload(full_payload, n=5):
    return {
        "labels": full_payload["labels"][:n],
        "datasets": [
            {"label": ds["label"], "data": ds["data"][:n]}
            for ds in full_payload["datasets"]
        ],
    }

# -----------------------------
# Historical (existing)
# -----------------------------
@app.get("/facilities")
def list_hist_facilities():
    return jsonify({"facilities": HIST_FACILITIES})

@app.get("/chart/<facility>")
def chart_facility(facility):
    payload = facility_chart_payload(hist_df, facility)
    if payload is None:
        return jsonify({"error": f"Unknown facility '{facility}'"}), 404
    return jsonify(payload)

@app.get("/chart/<facility>/head")
def chart_facility_head(facility):
    payload = facility_chart_payload(hist_df, facility)
    if payload is None:
        return jsonify({"error": f"Unknown facility '{facility}'"}), 404
    return jsonify(head_payload(payload, n=5))

# -----------------------------
# Forecast (new)
# -----------------------------
@app.get("/forecast/facilities")
def list_forecast_facilities():
    return jsonify({"facilities": FORECAST_FACILITIES})

@app.get("/forecast/<facility>")
def forecast_facility(facility):
    payload = facility_chart_payload(forecast_df, facility)
    if payload is None:
        return jsonify({"error": f"Unknown facility '{facility}'"}), 404
    return jsonify(payload)

@app.get("/forecast/<facility>/head")
def forecast_facility_head(facility):
    payload = facility_chart_payload(forecast_df, facility)
    if payload is None:
        return jsonify({"error": f"Unknown facility '{facility}'"}), 404
    return jsonify(head_payload(payload, n=5))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
