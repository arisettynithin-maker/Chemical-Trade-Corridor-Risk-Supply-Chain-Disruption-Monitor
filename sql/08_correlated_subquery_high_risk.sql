-- Find corridors where risk score is above the average for THEIR region and year.
-- Correlated subquery recalculates average per row — slightly slower but
-- avoids the CTE-join pattern when this gets embedded in a larger pipeline.

SELECT
    c.country,
    c.region,
    c.year,
    c.risk_score,
    c.risk_tier,
    c.lpi_overall,
    c.vol_norm,
    -- correlated avg risk for context
    (SELECT ROUND(AVG(c2.risk_score), 3)
     FROM corridor_risk_scores c2
     WHERE c2.region = c.region
       AND c2.year   = c.year)  AS region_year_avg_risk
FROM corridor_risk_scores c
WHERE c.risk_score > (
    SELECT AVG(c2.risk_score)
    FROM corridor_risk_scores c2
    WHERE c2.region = c.region
      AND c2.year   = c.year
)
AND c.year >= 2012
ORDER BY c.year DESC, c.risk_score DESC;
