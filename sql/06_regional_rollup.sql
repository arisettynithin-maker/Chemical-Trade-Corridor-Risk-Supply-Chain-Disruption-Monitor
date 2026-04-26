-- Regional trade aggregation using ROLLUP for hierarchical subtotals.
-- Output feeds the regional summary tab in the fleet dashboard.
-- The NULL rows are the subtotals — fleet planning uses those for region-level SIOP inputs.

SELECT
    COALESCE(r.region, 'ALL REGIONS')       AS region,
    COALESCE(c.country, 'ALL COUNTRIES')    AS country,
    COALESCE(CAST(crs.year AS VARCHAR), 'ALL YEARS') AS year,
    ROUND(AVG(crs.risk_score), 3)           AS avg_risk_score,
    ROUND(AVG(crs.lpi_overall), 2)          AS avg_lpi,
    COUNT(DISTINCT c.country)               AS n_countries,
    SUM(at.trade_usd)                       AS total_trade_usd,
    ROUND(AVG(crs.vol_norm), 3)             AS avg_volatility
FROM corridor_risk_scores crs
JOIN regions r USING (country)
JOIN (
    SELECT country, year, SUM(trade_usd) AS trade_usd
    FROM chemical_trade_flows
    GROUP BY country, year
) at ON crs.country = at.country AND crs.year = at.year
-- alias hack to satisfy ROLLUP syntax across dialects
CROSS JOIN (SELECT crs.country AS country FROM corridor_risk_scores crs LIMIT 1) c
GROUP BY ROLLUP(r.region, c.country, CAST(crs.year AS VARCHAR))
ORDER BY region NULLS LAST, country NULLS LAST, year NULLS LAST;

-- Alternative CUBE version for full cross-dimensional breakdown:
-- GROUP BY CUBE(r.region, CAST(crs.year AS VARCHAR))
-- Useful when Finance needs a full region × year matrix for budget planning.
