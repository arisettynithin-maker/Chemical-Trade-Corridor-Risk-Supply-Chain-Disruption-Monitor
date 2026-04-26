# SQL Files — Tank Corridor Risk Monitor

All queries are written against the schema produced by `data/ingest.py`. The logical tables referenced are:

| Table | Description |
|---|---|
| `chemical_trade_flows` | Annual chemical export volumes by country, year, category |
| `corridor_risk_scores` | Computed risk scores, tiers, and normalised metrics per country-year |
| `lpi_scores` | World Bank Logistics Performance Index by country and year |
| `regions` | Country → region mapping |

---

## Files

| File | Business Question | SQL Concept |
|---|---|---|
| `01_trade_volume_by_corridor.sql` | Which corridors drive the most chemical trade by value and weight? | GROUP BY, HAVING, multi-column aggregation |
| `02_yoy_growth_with_lag.sql` | How is each corridor's trade growing or shrinking year on year? | LAG/LEAD window functions, YoY calculation |
| `03_volatility_scoring.sql` | Which corridors are most unpredictable in their trade volumes? | STDDEV window function, NTILE, rolling 5-year calc |
| `04_corridor_risk_ranking.sql` | How do corridors rank by composite risk in the latest year? | RANK, DENSE_RANK, PERCENT_RANK, CASE |
| `05_multi_cte_risk_pipeline.sql` | Full end-to-end risk score calculation in a single query? | Multi-step CTEs, ROW_NUMBER, normalisation logic |
| `06_regional_rollup.sql` | What is the risk and trade picture at the regional level with subtotals? | ROLLUP, CUBE, COALESCE for NULL labels |
| `07_self_join_corridor_comparison.sql` | Which corridors are outliers vs their own regional average? | Self-join, Z-score calculation, STDDEV |
| `08_correlated_subquery_high_risk.sql` | Which corridors exceed their region's average risk in any given year? | Correlated subquery in WHERE clause |
| `09_anti_join_stagnant_corridors.sql` | Which corridors have never broken into top-quartile growth? | NOT EXISTS anti-join, NTILE inside subquery |
| `10_rolling_moving_averages.sql` | What does the smoothed trade trend look like for each corridor? | Moving average (3yr/5yr), running total, ROWS BETWEEN |
| `11_lpi_trade_funnel.sql` | How does logistics quality relate to actual chemical trade volume? | Multi-table JOIN, EXISTS filter, NTILE tier banding |
