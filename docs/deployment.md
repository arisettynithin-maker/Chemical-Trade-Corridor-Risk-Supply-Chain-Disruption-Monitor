# Deployment — Streamlit Cloud

## Prerequisites

- Python 3.10+
- Kaggle account with API credentials (`~/.kaggle/kaggle.json`)
- Git

## Local Setup

```bash
pip install -r requirements.txt
python data/ingest.py         # fetches and processes data (~5 min first run)
streamlit run app/streamlit_app.py
```

App opens at http://localhost:8501.

## Streamlit Cloud Deployment

1. Push the repo to GitHub (see root README)
2. Go to https://share.streamlit.io → New app
3. Select your repo, branch `main`, file `app/streamlit_app.py`
4. Under **Advanced settings → Secrets**, add Kaggle credentials if re-fetching data in cloud:
   ```toml
   KAGGLE_USERNAME = "your_username"
   KAGGLE_KEY = "your_api_key"
   ```
5. Click **Deploy**

The `/data` folder with processed CSVs must be committed to the repo **before** deploying (the cloud runner won't run `ingest.py` automatically).

## Re-running Ingestion

To refresh data (new LPI vintage, etc.):
```bash
rm data/corridor_risk_scores.csv
python data/ingest.py
```

Only the risk score file is deleted — raw downloads are cached and won't be re-fetched.
