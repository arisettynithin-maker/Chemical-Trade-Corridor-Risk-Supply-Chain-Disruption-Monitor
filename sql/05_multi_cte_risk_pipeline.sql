-- Full risk scoring pipeline as a multi-step CTE chain.
-- This is what I'd productionise in the BI layer — each CTE is a testable stage.
-- Lets the fleet team audit exactly where a risk score comes from.

WITH
-- stage 1: clean annual trade per country
annual_trade AS (
    SELECT
        country,
        year,
        SUM(trade_usd)  AS trade_usd,
        SUM(weight_kg)  AS weight_kg,
        COUNT(DISTINCT category) AS n_categories
    FROM chemical_trade_flows
    WHERE trade_usd > 0
    GROUP BY country, year
),

-- stage 2: compute YoY growth
trade_growth AS (
    SELECT
        country,
        year,
        trade_usd,
        weight_kg,
        LAG(trade_usd) OVER (PARTITION BY country ORDER BY year) AS prev_usd,
        ROUND(
            (trade_usd - LAG(trade_usd) OVER (PARTITION BY country ORDER BY year))
            / NULLIF(LAG(trade_usd) OVER (PARTITION BY country ORDER BY year), 0) * 100
        , 2) AS yoy_pct
    FROM annual_trade
),

-- stage 3: rolling 3-year volatility
trade_volatility AS (
    SELECT
        country,
        year,
        trade_usd,
        yoy_pct,
        STDDEV(yoy_pct) OVER (
            PARTITION BY country
            ORDER BY year
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS volatility_3yr
    FROM trade_growth
    WHERE yoy_pct IS NOT NULL
),

-- stage 4: bring in logistics performance
lpi_latest AS (
    SELECT
        country_name AS country,
        lpi_overall,
        lpi_customs,
        lpi_infrastructure,
        lpi_logistics
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (PARTITION BY country_name ORDER BY year DESC) AS rn
        FROM lpi_scores
    ) sub
    WHERE rn = 1
),

-- stage 5: normalise and compute composite score
normalised AS (
    SELECT
        tv.country,
        tv.year,
        tv.trade_usd,
        tv.volatility_3yr,
        l.lpi_overall,
        -- normalise volatility to 0-1 range
        ROUND(
            (tv.volatility_3yr - MIN(tv.volatility_3yr) OVER ())
            / NULLIF(MAX(tv.volatility_3yr) OVER () - MIN(tv.volatility_3yr) OVER (), 0)
        , 4) AS vol_norm,
        -- inverse-normalise LPI (low LPI = high risk)
        ROUND(
            1 - (l.lpi_overall - MIN(l.lpi_overall) OVER ())
            / NULLIF(MAX(l.lpi_overall) OVER () - MIN(l.lpi_overall) OVER (), 0)
        , 4) AS lpi_risk
    FROM trade_volatility tv
    LEFT JOIN lpi_latest l USING (country)
)

SELECT
    country,
    year,
    trade_usd,
    volatility_3yr,
    lpi_overall,
    vol_norm,
    lpi_risk,
    ROUND(0.6 * COALESCE(vol_norm, 0.5) + 0.4 * COALESCE(lpi_risk, 0.5), 3) AS composite_risk_score,
    CASE
        WHEN ROUND(0.6 * COALESCE(vol_norm, 0.5) + 0.4 * COALESCE(lpi_risk, 0.5), 3) > 0.66 THEN 'High'
        WHEN ROUND(0.6 * COALESCE(vol_norm, 0.5) + 0.4 * COALESCE(lpi_risk, 0.5), 3) > 0.33 THEN 'Medium'
        ELSE 'Low'
    END AS risk_tier
FROM normalised
WHERE vol_norm IS NOT NULL
ORDER BY year DESC, composite_risk_score DESC;
