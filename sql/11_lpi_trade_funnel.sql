-- LPI-to-trade funnel: how logistics quality filters down to actual trade outcomes.
-- EXISTS used to only include countries that appear in both datasets.
-- Multi-table join to build the full corridor profile in one query.

WITH lpi_tiers AS (
    SELECT
        country_name AS country,
        year,
        lpi_overall,
        NTILE(3) OVER (PARTITION BY year ORDER BY lpi_overall DESC) AS lpi_tier
        -- tier 1 = best logistics, tier 3 = worst
    FROM lpi_scores
    WHERE year IN (2010, 2012, 2014, 2016, 2018)
),
trade_summary AS (
    SELECT
        country,
        year,
        SUM(trade_usd)  AS total_trade_usd,
        COUNT(DISTINCT category) AS n_chem_categories,
        AVG(trade_usd)  AS avg_category_trade
    FROM chemical_trade_flows
    GROUP BY country, year
)
SELECT
    lt.country,
    r.region,
    lt.year,
    lt.lpi_overall,
    lt.lpi_tier,
    CASE lt.lpi_tier
        WHEN 1 THEN 'Top Logistics'
        WHEN 2 THEN 'Mid Logistics'
        WHEN 3 THEN 'Poor Logistics'
    END AS logistics_band,
    ts.total_trade_usd,
    ts.n_chem_categories,
    ROUND(ts.total_trade_usd / 1e9, 2) AS trade_bn_usd,
    crs.risk_score,
    crs.risk_tier
FROM lpi_tiers lt
JOIN trade_summary ts ON lt.country = ts.country AND lt.year = ts.year
JOIN regions r ON lt.country = r.country
LEFT JOIN corridor_risk_scores crs ON lt.country = crs.country AND lt.year = crs.year
-- only countries with actual trade data — no point showing an LPI score in isolation
WHERE EXISTS (
    SELECT 1 FROM chemical_trade_flows ctf
    WHERE ctf.country = lt.country AND ctf.year = lt.year
)
ORDER BY lt.year, lt.lpi_overall DESC;
