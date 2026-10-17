# 🌤️ Weather End-to-End Project

**API → Python cleaning → SQL Server in Docker (bronze / silver / gold) → SQL → Machine Learning → Streamlit → Power BI**

```
Open-Meteo API ──► bronze.weather_raw ──► silver.weather_daily ──► gold.* tables ──► Streamlit app
   (Python)          (raw data)            (cleaned, Python)       (SQL + ML results)   Power BI
```

## Project structure

```
weather_project/
├── docker-compose.yml           SQL Server 2022 + Streamlit containers
├── Dockerfile                   image for the Streamlit app
├── requirements.txt
├── notebooks/
│   ├── 01_extract_bronze_silver.ipynb   get data → bronze → clean → silver
│   └── 02_gold_ml_analysis.ipynb        gold SQL → analysis → ML → save results
├── sql/
│   ├── 01_setup_database.sql    database + schemas
│   ├── 02_gold_layer.sql        builds the gold tables (run by notebook 02)
│   ├── 03_analysis_queries.sql  practice queries (window functions, CTE, TOP, ...)
│   └── 04_powerbi_reader.sql    optional read-only login for Power BI
├── app/streamlit_app.py         dashboard + prediction page
└── models/                      the trained model is saved here
```

## Tables you get

| Schema | Table | Content |
|---|---|---|
| bronze | `weather_raw` | raw API data + `ingested_at` |
| silver | `weather_daily` | cleaned data + season, temp_range, is_rainy |
| gold | `dim_city` | one row per city |
| gold | `fact_daily_weather` | daily facts (main table for Power BI) |
| gold | `monthly_city_summary` | monthly averages / totals |
| gold | `city_kpis` | record high/low, rainy-day %, … |
| gold | `season_summary` | averages by season |
| gold | `ml_predictions` | model's predictions vs actual on the test period |
| gold | `model_metrics` | MAE / RMSE / R² of every training run |
| gold | `next_day_forecast` | tomorrow's predicted max temp per city |

---

## How to run it

### 0. Install
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows: enable WSL 2)
* Python 3.10+

```bash
cd weather_project
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 1. Start SQL Server in Docker
```bash
docker compose up -d sqlserver
docker ps            # wait until STATUS shows "(healthy)" (~30 s)
```
Login: server `localhost,1433` · user `sa` · password `Weather_Pass123!`

### 2. Run the notebooks (in order)
```bash
jupyter notebook
```
1. `notebooks/01_extract_bronze_silver.ipynb` → *Run All*
2. `notebooks/02_gold_ml_analysis.ipynb` → *Run All*

### 3. Start the Streamlit dashboard
Either locally:
```bash
streamlit run app/streamlit_app.py
```
or in Docker (database + app together):
```bash
docker compose up -d --build
```
Open **http://localhost:8501** — pages: *Overview · City analysis · Model performance · Predict*.

> If the Docker app shows a scikit-learn version warning when loading the model, use the same library versions in both places (`pip install -r requirements.txt`) and run notebook 02 again.

### 4. (Optional) Look at the data with SQL
Connect with **SSMS**, **Azure Data Studio** or the VS Code **mssql** extension to `localhost,1433` (tick *Trust server certificate*) and run `sql/03_analysis_queries.sql`.

---

## 📊 Connect the GOLD layer to Power BI

Power BI Desktop runs on Windows, and SQL Server in Docker is published on port 1433, so Power BI sees it like a normal local SQL Server.

**1 – (Recommended) create a read-only user that can only see gold**
Run `sql/04_powerbi_reader.sql` in SSMS / Azure Data Studio. It creates `powerbi_reader` / `PowerBI_Read123!` with `SELECT` on the `gold` schema only. (You can also just use `sa`.)

**2 – Get Data**
1. Power BI Desktop → **Home → Get data → SQL Server**
2. **Server:** `localhost,1433`  ← note the **comma**, not a colon
3. **Database:** `WeatherDB`
4. **Data connectivity mode:** **Import** (best for this small dataset; choose *DirectQuery* only if you want live data without refresh)
5. OK → choose **Database** (left side, *not* Windows) → user `powerbi_reader`, password `PowerBI_Read123!` → Connect
6. If you see *"The certificate chain was issued by an authority that is not trusted"* → click **OK / Cancel**, then
   **File → Options and settings → Data source settings →** select `localhost,1433;WeatherDB` → **Edit Permissions →** untick **Encrypt connections** → OK, and connect again.

**3 – Select the gold tables**
In the Navigator tick: `gold.dim_city`, `gold.fact_daily_weather`, `gold.monthly_city_summary`, `gold.city_kpis`, `gold.ml_predictions`, `gold.next_day_forecast`, `gold.model_metrics` → **Load**.

**4 – Model view (relationships)**
* `dim_city[city_id]` 1 ──► * `fact_daily_weather[city_id]`
* `dim_city[city]` 1 ──► * `monthly_city_summary[city]`, `city_kpis[city]`, `ml_predictions[city]`, `next_day_forecast[city]`
* Optional: create a date table (*Modeling → New table*):
  ```DAX
  Calendar = CALENDAR(MIN(fact_daily_weather[date]), MAX(fact_daily_weather[date]))
  ```
  and relate `Calendar[Date]` → `fact_daily_weather[date]`.

**5 – A few DAX measures**
```DAX
Avg Temp      = AVERAGE(fact_daily_weather[temp_mean])
Total Rain mm = SUM(fact_daily_weather[precipitation_mm])
Rainy Days    = SUM(fact_daily_weather[is_rainy])
Model MAE     = AVERAGE(ml_predictions[abs_error])
```

**6 – Report ideas**
* Line chart: `month_start` vs `avg_temp`, legend `city`
* Cards: Avg Temp, Total Rain, Model MAE
* Map: `dim_city` latitude / longitude, size = Avg Temp
* Line chart: `ml_predictions[forecast_date]` with `actual` and `predicted`
* Table: `next_day_forecast`
* Slicer: `dim_city[city]`

**7 – Refresh**
After you re-run the notebooks, press **Refresh** in Power BI. (Scheduled refresh in Power BI Service needs an *On-premises data gateway* installed on the PC that runs Docker.)

---

## The ML model in short
* **Goal:** predict tomorrow's maximum temperature.
* **Features:** city, day of year (sin/cos), today's max/min/mean temp, rain, wind, sunshine, yesterday's max temp.
* **Models:** Linear Regression and Random Forest, compared with a naive baseline (*tomorrow = today*).
* **Split:** by time — the last 20 % of dates are the test set.
* The best model (lowest MAE) is retrained on all data and saved to `models/weather_model.joblib`.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Login failed for user 'sa'` | Container still starting — wait for `(healthy)`. If you changed the password after the first start, run `docker compose down -v` and start again. |
| Port 1433 already in use | A local SQL Server is running. Stop it or change the port to `"1434:1433"` and use `localhost,1434`. |
| Mac M1/M2/M3 | Enable *Use Rosetta for x86/amd64 emulation* in Docker Desktop settings. |
| `pymssql` won't install | `pip install --upgrade pip` then retry. |
| Delete everything incl. data | `docker compose down -v` |
