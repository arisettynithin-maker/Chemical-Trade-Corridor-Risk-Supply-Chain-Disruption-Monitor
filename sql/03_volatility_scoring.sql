-- Trade volatility scoring per corridor.
-- High volatility = unpredictable demand = wrong fleet allocation risk.
-- We use rolling 5-year standard deviation of YoY % change as the base signal.

WITH annual AS (
    SELECT
        country,
        year,
        SUM(trade_usd) AS trade_usd
    FROM chemical_trade_flows
    GROUP BY country, year
),
yoy AS (
    SELECT
        country,
        year,
        trade_usd,
        ROUND(
            (trade_usd - LAG(trade_usd) OVER w)
            / NULLIF(LAG(trade_usd) OVER w, 0) * 100
        , 2) AS yoy_pct
    FROM annual
    WINDOW w AS (PARTITION BY country ORDER BY year)
),
volatility_calc AS (
    SELECT
        country,
        year,
        trade_usd,
        yoy_pct,
        -- rolling stddev approximated via variance over a 5-year window
        ROUND(
            STDDEV(yoy_pct) OVER (
                PARTITION BY country
                ORDER BY year
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            )
        , 3) AS rolling_stddev_5yr,
        AVG(yoy_pct) OVER (
            PARTITION BY country
            ORDER BY year
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        )     AS rolling_avg_5yr
    FROM yoy
    WHERE yoy_pct IS NOT NULL
)
SELECT
    country,
    year,
    trade_usd,
    yoy_pct,
    rolling_stddev_5yr  AS volatility_score,
    rolling_avg_5yr     AS avg_growth_5yr,
    NTILE(4) OVER (PARTITION BY year ORDER BY rolling_stddev_5yr) AS volatility_quartile
FROM volatility_calc
WHERE rolling_stddev_5yr IS NOT NULL
ORDER BY year DESC, volatility_score DESC;
