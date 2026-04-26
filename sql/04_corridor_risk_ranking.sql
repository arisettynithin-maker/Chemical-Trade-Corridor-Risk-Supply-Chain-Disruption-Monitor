-- Rank corridors by composite risk score using RANK and DENSE_RANK.
-- DENSE_RANK used here because ties shouldn't create gaps in the league table —
-- fleet planners get confused when rank 3 jumps to rank 5.

SELECT
    country,
    region,
    year,
    risk_score,
    risk_tier,
    vol_norm,
    lpi_risk,
    RANK()       OVER (PARTITION BY year ORDER BY risk_score DESC)  AS risk_rank,
    DENSE_RANK() OVER (PARTITION BY year ORDER BY risk_score DESC)  AS risk_dense_rank,
    RANK()       OVER (PARTITION BY year, region ORDER BY risk_score DESC) AS risk_rank_within_region,
    PERCENT_RANK() OVER (PARTITION BY year ORDER BY risk_score)     AS risk_percentile,
    CASE risk_tier
        WHEN 'High'   THEN '🔴 High Risk'
        WHEN 'Medium' THEN '🟡 Medium Risk'
        WHEN 'Low'    THEN '🟢 Low Risk'
        ELSE 'Unknown'
    END AS risk_label
FROM corridor_risk_scores
WHERE year = (SELECT MAX(year) FROM corridor_risk_scores)
ORDER BY risk_rank;
