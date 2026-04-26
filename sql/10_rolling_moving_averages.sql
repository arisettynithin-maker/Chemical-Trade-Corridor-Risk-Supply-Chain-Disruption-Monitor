-- Rolling and moving averages for trade trend smoothing.
-- Raw YoY numbers spike too much to use in SIOP directly —
-- the 3-year MA is what we actually put into the demand planning model.

WITH annual AS (
    SELECT
        country,
        region,
        year,
        SUM(trade_usd) AS trade_usd
    FROM chemical_trade_flows
    JOIN regions USING (country)
    GROUP BY country, region, year
)
SELECT
    country,
    region,
    year,
    trade_usd,

    -- 3-year centred moving average
    ROUND(AVG(trade_usd) OVER (
        PARTITION BY country
        ORDER BY year
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ), 0) AS ma_3yr_centred,

    -- 5-year trailing moving average — what the SIOP model uses
    ROUND(AVG(trade_usd) OVER (
        PARTITION BY country
        ORDER BY year
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ), 0) AS ma_5yr_trailing,

    -- running cumulative total since 2005
    SUM(trade_usd) OVER (
        PARTITION BY country
        ORDER BY year
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total,

    -- deviation from 5yr MA (how far off trend this year is)
    ROUND(
        (trade_usd - AVG(trade_usd) OVER (
            PARTITION BY country
            ORDER BY year
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        )) / NULLIF(AVG(trade_usd) OVER (
            PARTITION BY country
            ORDER BY year
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ), 0) * 100
    , 2) AS pct_deviation_from_5yr_ma

FROM annual
WHERE year >= 2005
ORDER BY country, year;
