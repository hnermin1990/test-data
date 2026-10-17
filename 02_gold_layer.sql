/* =========================================================
   02 - Build the GOLD layer from silver.weather_daily
   Notebook 02 runs this file (it splits on GO).
   Run it again any time new data arrives - it rebuilds everything.
   ========================================================= */

USE WeatherDB;
GO

/* ---------- 1. City dimension ---------- */
DROP TABLE IF EXISTS gold.dim_city;
GO
SELECT
    ROW_NUMBER() OVER (ORDER BY city) AS city_id,
    city,
    country,
    MAX(latitude)  AS latitude,
    MAX(longitude) AS longitude
INTO gold.dim_city
FROM silver.weather_daily
GROUP BY city, country;
GO

/* ---------- 2. Daily fact table ---------- */
DROP TABLE IF EXISTS gold.fact_daily_weather;
GO
SELECT
    c.city_id,
    s.city,
    CAST(s.[date] AS DATE)  AS [date],
    s.[year],
    s.[month],
    s.season,
    s.temp_max,
    s.temp_min,
    s.temp_mean,
    s.temp_range,
    s.precipitation_mm,
    s.wind_speed_max_kmh,
    s.sunshine_hours,
    s.is_rainy
INTO gold.fact_daily_weather
FROM silver.weather_daily AS s
JOIN gold.dim_city        AS c ON c.city = s.city;
GO

/* ---------- 3. Monthly summary per city ---------- */
DROP TABLE IF EXISTS gold.monthly_city_summary;
GO
SELECT
    city,
    [year],
    [month],
    DATEFROMPARTS([year], [month], 1)          AS month_start,
    COUNT(*)                                   AS days_count,
    ROUND(AVG(temp_mean), 2)                   AS avg_temp,
    MAX(temp_max)                              AS max_temp,
    MIN(temp_min)                              AS min_temp,
    ROUND(SUM(precipitation_mm), 2)            AS total_precip_mm,
    SUM(CAST(is_rainy AS INT))                 AS rainy_days,
    ROUND(AVG(wind_speed_max_kmh), 2)          AS avg_max_wind_kmh,
    ROUND(SUM(sunshine_hours), 1)              AS total_sunshine_hours
INTO gold.monthly_city_summary
FROM gold.fact_daily_weather
GROUP BY city, [year], [month];
GO

/* ---------- 4. Overall KPIs per city ---------- */
DROP TABLE IF EXISTS gold.city_kpis;
GO
SELECT
    city,
    MIN([date])                                AS first_date,
    MAX([date])                                AS last_date,
    COUNT(*)                                   AS days_count,
    ROUND(AVG(temp_mean), 2)                   AS avg_temp,
    MAX(temp_max)                              AS record_high,
    MIN(temp_min)                              AS record_low,
    ROUND(SUM(precipitation_mm) / NULLIF(COUNT(DISTINCT [year]), 0), 1) AS avg_yearly_precip_mm,
    ROUND(100.0 * SUM(CAST(is_rainy AS INT)) / COUNT(*), 1)            AS rainy_days_pct
INTO gold.city_kpis
FROM gold.fact_daily_weather
GROUP BY city;
GO

/* ---------- 5. Season summary (handy for charts) ---------- */
DROP TABLE IF EXISTS gold.season_summary;
GO
SELECT
    city,
    season,
    ROUND(AVG(temp_mean), 2)        AS avg_temp,
    ROUND(AVG(precipitation_mm), 2) AS avg_daily_precip_mm,
    ROUND(AVG(sunshine_hours), 2)   AS avg_daily_sunshine_hours
INTO gold.season_summary
FROM gold.fact_daily_weather
GROUP BY city, season;
GO
