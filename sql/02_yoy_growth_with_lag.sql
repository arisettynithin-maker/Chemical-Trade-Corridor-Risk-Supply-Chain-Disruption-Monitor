-- Year-on-year trade growth by corridor using LAG window function.
-- This is the first signal we look at in the monthly SIOP review —
-- corridors with 3+ consecutive years of decline get flagged for repositioning.

WITH annual_totals AS (
    SELECT
        country,
        region,
        year,
        SUM(trade_usd) AS trade_usd
    FROM chemical_trade_flows
    JOIN regions USING (country)
    WHERE year >= 2008
    GROUP BY country, region, year
),
with_growth AS (
    SELECT
        country,
        region,
        year,
        trade_usd,
        LAG(trade_usd) OVER (PARTITION BY country ORDER BY year)          AS prev_year_usd,
        LEAD(trade_usd) OVER (PARTITION BY country ORDER BY year)         AS next_year_usd,
        ROUND(
            (trade_usd - LAG(trade_usd) OVER (PARTITION BY country ORDER BY year))
            / NULLIF(LAG(trade_usd) OVER (PARTITION BY country ORDER BY year), 0) * 100
        , 2)                                                               AS yoy_growth_pct
    FROM annual_totals
)
SELECT
    country,
    region,
    year,
    trade_usd,
    yoy_growth_pct,
    CASE
        WHEN yoy_growth_pct >  10 THEN 'Strong Growth'
        WHEN yoy_growth_pct >   0 THEN 'Modest Growth'
        WHEN yoy_growth_pct >  -10 THEN 'Mild Decline'
        ELSE 'Sharp Decline'
    END AS growth_category
FROM with_growth
WHERE yoy_growth_pct IS NOT NULL
ORDER BY country, year;
