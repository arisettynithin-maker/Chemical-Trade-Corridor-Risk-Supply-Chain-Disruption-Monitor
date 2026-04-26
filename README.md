# Tank Corridor Risk Monitor

> 🚀 Live Demo: (https://chemical-trade-corridor-risk-supply-chain-disruption-monitor-3.streamlit.app/)

## The Problem I Noticed

Tank container leasing companies manage assets that physically move around the world. When a trade corridor goes quiet — geopolitics, port disruption, a sudden demand collapse — tanks get stranded. Getting them repositioned costs money, takes weeks, and by the time it's done the corridor has often recovered or the window has closed.

The frustrating thing is that most of the signals for this are visible in advance, in the trade data. Chemical export volumes have their own volatility patterns. Some corridors are structurally stable. Others spike and crash constantly. Layer in the World Bank's Logistics Performance Index and you can start to see, well before a booking gap appears, which corridors are genuinely risky and which are just having an off quarter.

I built this to answer a specific question: **if you had to rank every major chemical trade corridor by how likely it is to cause a fleet positioning problem, what would that list look like?**

<img width="2502" height="1220" alt="image" src="https://github.com/user-attachments/assets/0e101fcc-e168-4660-a5a2-21e24e8027b2" />

<img width="2489" height="1265" alt="image" src="https://github.com/user-attachments/assets/1c4c8da1-9ca3-470b-8b58-056e9e1edbb8" />

<img width="2490" height="1196" alt="image" src="https://github.com/user-attachments/assets/6e023213-1e2c-452d-bfbd-491657db709f" />

<img width="2484" height="1234" alt="image" src="https://github.com/user-attachments/assets/a6347a9f-638d-4a09-b8b5-c169182426e3" />


## My Approach

Data: UN Comtrade bilateral chemical export data (1988–2016, via Kaggle) combined with the World Bank Logistics Performance Index for 150+ countries.

Risk score = 60% trade volatility + 40% logistics risk, both normalised to [0,1]. Volatility is a rolling 3-year standard deviation of year-on-year % change. Logistics risk is the inverse-normalised LPI score — poor infrastructure means positioning errors are harder to recover from.

The Streamlit app then lets fleet planners filter by region, year, and risk tier — and the Disruption Simulator page lets them model what happens to the risk score if a specific corridor loses 30% of its trade volume for 2 years.

## Key Findings

- Around 20–25% of monitored corridors sit in the "High Risk" tier in any given year — more than most operators would expect
- The CIS and Middle East & Africa regions consistently show the widest spread between top and bottom corridors — the average masks a lot of hidden variance
- Strong negative correlation between LPI and risk score (r ≈ -0.4): logistics quality genuinely reduces effective corridor risk, which suggests that depot and forwarder partnerships in weak-infrastructure markets aren't just operational niceness — they're risk management
- A handful of corridors that never appear in the top growth quartile absorb fleet allocation that could be freed up for higher-growth markets

## Business Recommendations

1. Build risk tier into the quarterly SIOP review as a fleet allocation input — not just demand volume
2. Apply a 10–15% buffer for High-risk corridors above base demand forecast
3. Prioritise LPI-improving actions (depot upgrades, forwarder partnerships) on corridors where logistics risk drives the composite score, not volatility — that's the fixable half
4. Automate a 2× rolling-stddev threshold check on monthly trade data so disruptions flag before they hit booking numbers

## How to Run

```bash
pip install -r requirements.txt
python data/ingest.py
streamlit run app/streamlit_app.py
```

First run of `ingest.py` takes ~5 minutes (large Kaggle dataset download). Subsequent runs are instant — outputs are cached in `/data`.

## Tech Stack

- Python, Pandas, NumPy
- Streamlit, Plotly
- Kaggle API (UN Comtrade data)
- World Bank API via `wbgapi`
- SQL (DuckDB-compatible, 11 analytical files)
- Jupyter for EDA

## Data Source

- **UN Comtrade trade statistics** — `kaggle datasets download -d unitednations/global-commodity-trade-statistics`
- **World Bank LPI** — fetched via `wbgapi` from the World Bank public API, no key required
