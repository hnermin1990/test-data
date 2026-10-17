"""
Weather Dashboard - reads the GOLD layer from SQL Server and serves the ML model.

Run locally :  streamlit run app/streamlit_app.py
Run in Docker: docker compose up -d --build   ->  http://localhost:8501
"""
import os
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤️", layout="wide")

# ---------------------------------------------------------------- config
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1433"))
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Weather_Pass123!")
DB_NAME = os.getenv("DB_NAME", "WeatherDB")
MODEL_PATH = Path(os.getenv("MODEL_PATH", Path(__file__).resolve().parent.parent / "models" / "weather_model.joblib"))


@st.cache_resource
def get_engine():
    url = URL.create("mssql+pymssql", username=DB_USER, password=DB_PASSWORD,
                     host=DB_SERVER, port=DB_PORT, database=DB_NAME)
    return create_engine(url)


@st.cache_data(ttl=600)
def query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine())


@st.cache_resource
def load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def build_features(city, day, t_max, t_min, t_mean, rain, wind, sun, t_max_prev):
    """Same features as notebook 02 -> must stay in sync."""
    doy = pd.Timestamp(day).dayofyear
    return pd.DataFrame([{
        "city": city,
        "doy_sin": np.sin(2 * np.pi * doy / 365.25),
        "doy_cos": np.cos(2 * np.pi * doy / 365.25),
        "temp_max": t_max, "temp_min": t_min, "temp_mean": t_mean,
        "precipitation_mm": rain, "wind_speed_max_kmh": wind,
        "sunshine_hours": sun, "temp_max_prev_day": t_max_prev,
    }])


# ---------------------------------------------------------------- load data
try:
    fact = query("SELECT * FROM gold.fact_daily_weather")
    fact["date"] = pd.to_datetime(fact["date"])
    kpis = query("SELECT * FROM gold.city_kpis")
    monthly = query("SELECT * FROM gold.monthly_city_summary")
    monthly["month_start"] = pd.to_datetime(monthly["month_start"])
except Exception as e:
    st.error("Could not read the gold tables. Is SQL Server running and did you run both notebooks?")
    st.exception(e)
    st.stop()

bundle = load_model()
cities = sorted(fact["city"].unique())

# ---------------------------------------------------------------- sidebar
st.sidebar.title("🌤️ Weather Project")
page = st.sidebar.radio("Page", ["Overview", "City analysis", "Model performance", "Predict"])
st.sidebar.caption(f"Data: {fact['date'].min():%Y-%m-%d} → {fact['date'].max():%Y-%m-%d}")
if bundle:
    st.sidebar.caption(f"Model: {bundle['model_name']} (trained {bundle['trained_at']})")

# ---------------------------------------------------------------- pages
if page == "Overview":
    st.title("Weather overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cities", len(cities))
    c2.metric("Days of data", f"{fact['date'].nunique():,}")
    c3.metric("Record high", f"{kpis['record_high'].max():.1f} °C",
              kpis.loc[kpis['record_high'].idxmax(), "city"], delta_color="off")
    c4.metric("Record low", f"{kpis['record_low'].min():.1f} °C",
              kpis.loc[kpis['record_low'].idxmin(), "city"], delta_color="off")

    st.plotly_chart(px.line(monthly.sort_values("month_start"), x="month_start", y="avg_temp",
                            color="city", title="Average monthly temperature (°C)",
                            labels={"month_start": "", "avg_temp": "°C"}), width="stretch")

    st.subheader("City KPIs (gold.city_kpis)")
    st.dataframe(kpis.sort_values("avg_temp", ascending=False), hide_index=True, width="stretch")

elif page == "City analysis":
    city = st.selectbox("City", cities)
    d = fact[fact["city"] == city].sort_values("date")
    start, end = st.slider("Period", d["date"].min().date(), d["date"].max().date(),
                           (d["date"].max().date() - timedelta(days=365), d["date"].max().date()))
    d = d[(d["date"].dt.date >= start) & (d["date"].dt.date <= end)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Average temp", f"{d['temp_mean'].mean():.1f} °C")
    c2.metric("Total rain", f"{d['precipitation_mm'].sum():.0f} mm")
    c3.metric("Rainy days", int(d["is_rainy"].sum()))

    st.plotly_chart(px.line(d, x="date", y=["temp_max", "temp_mean", "temp_min"],
                            title=f"{city} — daily temperature (°C)", labels={"value": "°C", "date": ""}),
                    width="stretch")
    m = monthly[monthly["city"] == city].sort_values("month_start")
    col1, col2 = st.columns(2)
    col1.plotly_chart(px.bar(m, x="month_start", y="total_precip_mm", title="Monthly rain (mm)",
                             labels={"month_start": ""}), width="stretch")
    col2.plotly_chart(px.bar(m, x="month_start", y="total_sunshine_hours", title="Monthly sunshine (hours)",
                             labels={"month_start": ""}), width="stretch")

elif page == "Model performance":
    st.title("Model performance")
    try:
        metrics = query("SELECT * FROM gold.model_metrics")
        preds = query("SELECT * FROM gold.ml_predictions")
    except Exception:
        st.warning("No model results yet — run notebook 02 first.")
        st.stop()

    last = metrics[metrics["trained_at"] == metrics["trained_at"].max()]
    st.subheader("Latest training run (test period)")
    st.dataframe(last[["model_name", "MAE", "RMSE", "R2", "is_best"]].sort_values("MAE"),
                 hide_index=True, width="stretch")
    st.caption("MAE = average error in °C. The model should beat the baseline 'tomorrow = today'.")

    preds["forecast_date"] = pd.to_datetime(preds["forecast_date"])
    city = st.selectbox("City", sorted(preds["city"].unique()))
    p = preds[preds["city"] == city].sort_values("forecast_date")
    st.plotly_chart(px.line(p, x="forecast_date", y=["actual", "predicted"],
                            title=f"{city}: actual vs predicted next-day max temp",
                            labels={"value": "°C", "forecast_date": ""}), width="stretch")
    col1, col2 = st.columns(2)
    col1.plotly_chart(px.scatter(p, x="actual", y="predicted", opacity=.6, title="Predicted vs actual"),
                      width="stretch")
    col2.plotly_chart(px.histogram(p, x="error", nbins=40, title="Error distribution (°C)"),
                      width="stretch")

else:  # Predict
    st.title("Predict tomorrow's max temperature")
    if bundle is None:
        st.warning(f"Model file not found at {MODEL_PATH}. Run notebook 02 first.")
        st.stop()

    try:
        fc = query("SELECT * FROM gold.next_day_forecast")
        st.subheader("Latest saved forecast (gold.next_day_forecast)")
        st.dataframe(fc, hide_index=True, width="stretch")
    except Exception:
        pass

    st.subheader("Try your own values")
    city = st.selectbox("City", bundle["cities"])
    last = fact[fact["city"] == city].sort_values("date").tail(2)   # pre-fill with latest real data
    today_row, prev_row = last.iloc[-1], last.iloc[0]

    with st.form("predict"):
        day = st.date_input("Today's date", value=today_row["date"].date())
        c1, c2, c3 = st.columns(3)
        t_max = c1.number_input("Max temp today (°C)", value=float(today_row["temp_max"]), step=0.5)
        t_min = c2.number_input("Min temp today (°C)", value=float(today_row["temp_min"]), step=0.5)
        t_mean = c3.number_input("Mean temp today (°C)", value=float(today_row["temp_mean"]), step=0.5)
        c4, c5, c6 = st.columns(3)
        rain = c4.number_input("Rain today (mm)", min_value=0.0, value=float(today_row["precipitation_mm"]), step=0.5)
        wind = c5.number_input("Max wind today (km/h)", min_value=0.0, value=float(today_row["wind_speed_max_kmh"]), step=1.0)
        sun = c6.number_input("Sunshine today (hours)", min_value=0.0, max_value=24.0,
                              value=float(today_row["sunshine_hours"]), step=0.5)
        t_prev = st.number_input("Max temp yesterday (°C)", value=float(prev_row["temp_max"]), step=0.5)
        submitted = st.form_submit_button("Predict")

    if submitted:
        X = build_features(city, day, t_max, t_min, t_mean, rain, wind, sun, t_prev)
        pred = float(bundle["model"].predict(X[bundle["features"]])[0])
        mae = bundle["metrics"].get("MAE", 0)
        st.success(f"Predicted max temperature in **{city}** on **{day + timedelta(days=1)}**: "
                   f"**{pred:.1f} °C**  (typical error ± {mae:.1f} °C)")
