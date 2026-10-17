/* =========================================================
   03 - Simple analysis queries (practice / checking results)
   ========================================================= */
USE WeatherDB;
GO

-- 1. How many rows are in each layer?
SELECT 'bronze' AS layer, COUNT(*) AS row_count FROM bronze.weather_raw
UNION ALL SELECT 'silver', COUNT(*) FROM silver.weather_daily
UNION ALL SELECT 'gold',   COUNT(*) FROM gold.fact_daily_weather;

-- 2. Warmest and coldest city on average
SELECT city, avg_temp, record_high, record_low
FROM gold.city_kpis
ORDER BY avg_temp DESC;

-- 3. Top 10 hottest days across all cities
SELECT TOP 10 city, [date], temp_max
FROM gold.fact_daily_weather
ORDER BY temp_max DESC;

-- 4. Wettest month for each city (window function)
WITH ranked AS (
    SELECT city, month_start, total_precip_mm,
           ROW_NUMBER() OVER (PARTITION BY city ORDER BY total_precip_mm DESC) AS rn
    FROM gold.monthly_city_summary
)
SELECT city, month_start, total_precip_mm
FROM ranked
WHERE rn = 1;

-- 5. 7-day moving average temperature (example for one city)
SELECT city, [date], temp_mean,
       AVG(temp_mean) OVER (PARTITION BY city ORDER BY [date]
                            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS temp_ma_7d
FROM gold.fact_daily_weather
WHERE city = 'Baku'
ORDER BY [date];

-- 6. Model quality per city (after notebook 02)
SELECT city,
       COUNT(*)                                 AS predictions,
       ROUND(AVG(ABS(actual - predicted)), 2)   AS mae
FROM gold.ml_predictions
GROUP BY city
ORDER BY mae;

-- 7. Latest model metrics
SELECT * FROM gold.model_metrics ORDER BY trained_at DESC;
