-- Self-join to compare each corridor's risk against the same region's average.
-- Helps fleet planners spot outliers: a country with 2x the regional average risk
-- is a candidate for proactive tank repositioning.

WITH regional_avg AS (
    SELECT
        region,
        year,
        AVG(risk_score)   AS region_avg_risk,
        STDDEV(risk_score) AS region_stddev_risk,
        AVG(lpi_overall)  AS region_avg_lpi
    FROM corridor_risk_scores
    GROUP BY region, year
)
SELECT
    c.country,
    c.region,
    c.year,
    c.risk_score                                    AS country_risk,
    ra.region_avg_risk,
    ROUND(c.risk_score - ra.region_avg_risk, 3)     AS deviation_from_region_avg,
    ROUND((c.risk_score - ra.region_avg_risk)
          / NULLIF(ra.region_stddev_risk, 0), 2)    AS z_score,
    CASE
        WHEN c.risk_score > ra.region_avg_risk + ra.region_stddev_risk THEN 'High Outlier'
        WHEN c.risk_score < ra.region_avg_risk - ra.region_stddev_risk THEN 'Low Outlier'
        ELSE 'Within Normal Range'
    END AS outlier_status
FROM corridor_risk_scores c
-- self-join on region + year to pull in regional stats
JOIN regional_avg ra ON c.region = ra.region AND c.year = ra.year
WHERE c.year = (SELECT MAX(year) FROM corridor_risk_scores)
ORDER BY deviation_from_region_avg DESC;
