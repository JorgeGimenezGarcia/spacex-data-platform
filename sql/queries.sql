-- 1. Maximum number of flights (reuse count) per core
SELECT core_id, MAX(flight) AS max_flights
FROM core_usage
GROUP BY core_id
ORDER BY max_flights DESC
LIMIT 1;

-- 2. Cores reused within 50 days of previous launch
WITH chron AS (
    SELECT
      core_id,
      launch_date,
      LAG(launch_date) OVER (PARTITION BY core_id ORDER BY launch_date) AS prev_date
    FROM core_usage
)
SELECT core_id,
       DATEDIFF(day, prev_date, launch_date) AS days_since_last
FROM chron
WHERE prev_date IS NOT NULL
  AND DATEDIFF(day, prev_date, launch_date) < 50;