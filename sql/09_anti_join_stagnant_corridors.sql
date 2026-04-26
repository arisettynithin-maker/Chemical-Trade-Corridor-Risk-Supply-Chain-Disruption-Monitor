-- Find corridors that have NEVER appeared in the top-quartile growth list.
-- Anti-join via NOT EXISTS — these are perpetually stagnant corridors.
-- Fleet strategy: these should have lower tank allocation than their raw volume suggests.

WITH top_growth AS (
    SELECT DISTINCT country
    FROM (
        SELECT
            country,
            yoy_pct,
            NTILE(4) OVER (PARTITION BY year ORDER BY yoy_pct DESC) AS growth_quartile
        FROM (
            SELECT
                country,
                year,
                ROUND(
                    (trade_usd - LAG(trade_usd) OVER (PARTITION BY country ORDER BY year))
                    / NULLIF(LAG(trade_usd) OVER (PARTITION BY country ORDER BY year), 0) * 100
                , 2) AS yoy_pct,
                trade_usd
            FROM (
                SELECT country, year, SUM(trade_usd) AS trade_usd
                FROM chemical_trade_flows
                GROUP BY country, year
            ) ann
        ) g
        WHERE yoy_pct IS NOT NULL
    ) ranked
    WHERE growth_quartile = 1
)
SELECT
    c.country,
    c.region,
    c.risk_score,
    c.risk_tier,
    c.lpi_overall
FROM corridor_risk_scores c
WHERE c.year = (SELECT MAX(year) FROM corridor_risk_scores)
  AND NOT EXISTS (
      SELECT 1 FROM top_growth tg WHERE tg.country = c.country
  )
ORDER BY c.risk_score DESC;
