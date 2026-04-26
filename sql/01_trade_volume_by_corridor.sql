-- Top chemical export corridors by trade value
-- Used to understand where the bulk of global tank container demand originates.
-- Running this monthly helps spot if a previously dominant corridor is fading.

SELECT
    country,
    region,
    category,
    year,
    SUM(trade_usd)                                      AS total_trade_usd,
    SUM(weight_kg)                                      AS total_weight_kg,
    ROUND(SUM(trade_usd) / NULLIF(SUM(weight_kg), 0), 4) AS usd_per_kg,
    COUNT(DISTINCT category)                            AS product_categories
FROM chemical_trade_flows
JOIN regions USING (country)
WHERE year >= 2010
GROUP BY country, region, category, year
HAVING SUM(trade_usd) > 1000000   -- exclude noise from tiny flows
ORDER BY year DESC, total_trade_usd DESC;
