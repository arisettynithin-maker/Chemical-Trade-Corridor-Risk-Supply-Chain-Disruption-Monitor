import os
import sys
import subprocess
import warnings
import pandas as pd
import numpy as np
import requests

warnings.filterwarnings('ignore')

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

CHEM_KEYWORDS = ['chemical', 'organic', 'inorganic', 'pharmaceutical', 'fertilizer', 'plastics']

# rough iso3 -> country name bridge for the trade dataset naming conventions
ISO3_TO_TRADE_NAME = {
    'DEU': 'Germany', 'FRA': 'France', 'NLD': 'Netherlands', 'BEL': 'Belgium',
    'ITA': 'Italy', 'ESP': 'Spain', 'GBR': 'United Kingdom', 'CHE': 'Switzerland',
    'SWE': 'Sweden', 'POL': 'Poland', 'AUT': 'Austria', 'DNK': 'Denmark',
    'FIN': 'Finland', 'CZE': 'Czech Republic', 'HUN': 'Hungary', 'NOR': 'Norway',
    'CHN': 'China', 'JPN': 'Japan', 'KOR': 'Republic of Korea', 'IND': 'India',
    'SGP': 'Singapore', 'TWN': 'Taiwan, Province of China', 'MYS': 'Malaysia',
    'THA': 'Thailand', 'AUS': 'Australia', 'IDN': 'Indonesia', 'HKG': 'China, Hong Kong SAR',
    'USA': 'United States of America', 'CAN': 'Canada', 'BRA': 'Brazil',
    'MEX': 'Mexico', 'ARG': 'Argentina', 'CHL': 'Chile',
    'SAU': 'Saudi Arabia', 'ARE': 'United Arab Emirates', 'ZAF': 'South Africa',
    'ISR': 'Israel', 'RUS': 'Russian Federation', 'UKR': 'Ukraine', 'KAZ': 'Kazakhstan',
    'TUR': 'Turkey', 'EGY': 'Egypt', 'NGA': 'Nigeria', 'PAK': 'Pakistan',
    'PHL': 'Philippines', 'VNM': 'Viet Nam',
}

REGION_MAP = {
    'Germany': 'Europe', 'France': 'Europe', 'Netherlands': 'Europe', 'Belgium': 'Europe',
    'Italy': 'Europe', 'Spain': 'Europe', 'United Kingdom': 'Europe', 'Switzerland': 'Europe',
    'Sweden': 'Europe', 'Poland': 'Europe', 'Austria': 'Europe', 'Denmark': 'Europe',
    'Finland': 'Europe', 'Czech Republic': 'Europe', 'Hungary': 'Europe', 'Norway': 'Europe',
    'China': 'Asia Pacific', 'Japan': 'Asia Pacific', 'Republic of Korea': 'Asia Pacific',
    'India': 'Asia Pacific', 'Singapore': 'Asia Pacific',
    'Taiwan, Province of China': 'Asia Pacific', 'Malaysia': 'Asia Pacific',
    'Thailand': 'Asia Pacific', 'Australia': 'Asia Pacific', 'Indonesia': 'Asia Pacific',
    'China, Hong Kong SAR': 'Asia Pacific',
    'United States of America': 'Americas', 'Canada': 'Americas', 'Brazil': 'Americas',
    'Mexico': 'Americas', 'Argentina': 'Americas', 'Chile': 'Americas',
    'Saudi Arabia': 'Middle East & Africa', 'United Arab Emirates': 'Middle East & Africa',
    'South Africa': 'Middle East & Africa', 'Israel': 'Middle East & Africa',
    'Egypt': 'Middle East & Africa', 'Nigeria': 'Middle East & Africa',
    'Russian Federation': 'CIS', 'Ukraine': 'CIS', 'Kazakhstan': 'CIS',
    'Turkey': 'Middle East & Africa', 'Pakistan': 'Asia Pacific',
    'Philippines': 'Asia Pacific', 'Viet Nam': 'Asia Pacific',
}


def download_trade_data():
    csv_path = os.path.join(DATA_DIR, 'commodity_trade_raw.csv')
    if os.path.exists(csv_path):
        print("Trade data already present, skipping download.")
        return csv_path

    print("Downloading commodity trade dataset from Kaggle...")
    try:
        result = subprocess.run(
            ['kaggle', 'datasets', 'download', '-d', 'unitednations/global-commodity-trade-statistics',
             '-p', DATA_DIR, '--unzip'],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
    except FileNotFoundError:
        print("ERROR: kaggle CLI not found. Run: pip install kaggle")
        print("Then place kaggle.json in ~/.kaggle/ — see https://github.com/Kaggle/kaggle-api")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Kaggle error: {e}")
        sys.exit(1)

    # locate the extracted csv — name varies slightly across kaggle versions
    for fname in os.listdir(DATA_DIR):
        if fname.endswith('.csv') and 'commodity' in fname.lower():
            src = os.path.join(DATA_DIR, fname)
            os.rename(src, csv_path)
            print(f"Renamed {fname} -> commodity_trade_raw.csv")
            return csv_path

    raise FileNotFoundError("Could not find extracted CSV in data/. Check the download manually.")


def process_trade_data(raw_path):
    out_path = os.path.join(DATA_DIR, 'chemical_trade_flows.csv')
    if os.path.exists(out_path):
        print("Processed trade data already exists, skipping.")
        return out_path

    print("Loading raw trade data (large file, ~30s)...")
    df = pd.read_csv(raw_path, dtype={'comm_code': str}, low_memory=False)
    print(f"  Loaded {len(df):,} rows. Columns: {list(df.columns)}")

    # filter to chemical-related categories
    cat_col = 'category' if 'category' in df.columns else 'commodity'
    mask = df[cat_col].str.contains('|'.join(CHEM_KEYWORDS), case=False, na=False)
    chem_df = df[mask].copy()

    # keep exports only to avoid double-counting
    if 'flow' in chem_df.columns:
        chem_df = chem_df[chem_df['flow'].str.lower() == 'export']

    country_col = 'country_or_area' if 'country_or_area' in chem_df.columns else 'country'
    chem_df = chem_df.rename(columns={country_col: 'country'})

    chem_df = chem_df.dropna(subset=['country', 'year', 'trade_usd'])
    chem_df = chem_df[chem_df['trade_usd'] > 0]

    agg = chem_df.groupby(['country', 'year', cat_col]).agg(
        trade_usd=('trade_usd', 'sum'),
        weight_kg=('weight_kg', 'sum') if 'weight_kg' in chem_df.columns else ('trade_usd', 'count')
    ).reset_index()
    agg.rename(columns={cat_col: 'category'}, inplace=True)
    agg['year'] = agg['year'].astype(int)

    agg.to_csv(out_path, index=False)
    print(f"  Saved {len(agg):,} rows -> chemical_trade_flows.csv")
    return out_path


def download_lpi_data():
    out_path = os.path.join(DATA_DIR, 'world_bank_lpi.csv')
    if os.path.exists(out_path):
        print("LPI data already present, skipping.")
        return out_path

    print("Fetching World Bank Logistics Performance Index...")

    indicators = {
        'LP.LPI.OVRL.XQ': 'lpi_overall',
        'LP.LPI.CUST.XQ': 'lpi_customs',
        'LP.LPI.INFR.XQ': 'lpi_infrastructure',
        'LP.LPI.LOGS.XQ': 'lpi_logistics',
        'LP.LPI.TIME.XQ': 'lpi_timeliness',
    }

    try:
        import wbgapi as wb
        frames = []
        for code, col in indicators.items():
            try:
                raw = wb.data.DataFrame(code, economy='all', time=range(2007, 2024))
                raw = raw.reset_index()
                raw.columns = ['country_code'] + [str(c) for c in raw.columns[1:]]
                melted = raw.melt(id_vars='country_code', var_name='year', value_name=col)
                melted['year'] = melted['year'].str.replace('YR', '').astype(int)
                frames.append(melted.set_index(['country_code', 'year']))
            except Exception as e:
                print(f"  Skipping {code}: {e}")

        if not frames:
            raise RuntimeError("wbgapi returned no data")

        lpi_df = pd.concat(frames, axis=1).reset_index()

        # attach country names
        try:
            meta = wb.economy.DataFrame()[['name']].reset_index()
            meta.columns = ['country_code', 'country_name']
            lpi_df = lpi_df.merge(meta, on='country_code', how='left')
        except Exception:
            lpi_df['country_name'] = lpi_df['country_code']

        lpi_df.to_csv(out_path, index=False)
        print(f"  Saved {len(lpi_df):,} LPI rows -> world_bank_lpi.csv")

    except ImportError:
        print("  wbgapi not available, falling back to World Bank REST API...")
        _fetch_lpi_rest(out_path)

    return out_path


def _fetch_lpi_rest(out_path):
    """Fallback: hit the WB REST API directly for overall LPI."""
    url = "https://api.worldbank.org/v2/country/all/indicator/LP.LPI.OVRL.XQ"
    rows, page = [], 1
    while True:
        r = requests.get(url, params={'format': 'json', 'per_page': 1000, 'date': '2007:2023', 'page': page}, timeout=30)
        data = r.json()
        if len(data) < 2 or not data[1]:
            break
        for item in data[1]:
            if item['value'] is not None:
                rows.append({
                    'country_code': item['countryiso3code'],
                    'country_name': item['country']['value'],
                    'year': int(item['date']),
                    'lpi_overall': float(item['value'])
                })
        if page >= data[0]['pages']:
            break
        page += 1

    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"  Saved {len(rows):,} LPI rows (REST fallback)")


def compute_risk_scores():
    out_path = os.path.join(DATA_DIR, 'corridor_risk_scores.csv')
    if os.path.exists(out_path):
        print("Risk scores already computed, skipping.")
        return out_path

    print("Computing corridor risk scores...")

    trade_df = pd.read_csv(os.path.join(DATA_DIR, 'chemical_trade_flows.csv'))
    lpi_df   = pd.read_csv(os.path.join(DATA_DIR, 'world_bank_lpi.csv'))

    # country-year total trade
    cy = trade_df.groupby(['country', 'year'])['trade_usd'].sum().reset_index()
    cy = cy.sort_values(['country', 'year'])

    # year-on-year % change
    cy['trade_yoy_pct'] = cy.groupby('country')['trade_usd'].pct_change() * 100

    # rolling 3-year volatility
    cy['volatility'] = cy.groupby('country')['trade_yoy_pct'].transform(
        lambda x: x.rolling(3, min_periods=2).std()
    )

    # get latest LPI per country name
    name_col = 'country_name' if 'country_name' in lpi_df.columns else 'country_code'
    lpi_latest = (lpi_df.dropna(subset=['lpi_overall'])
                        .sort_values('year')
                        .groupby(name_col)
                        .last()
                        .reset_index()[[name_col, 'lpi_overall']])
    lpi_latest.columns = ['country', 'lpi_overall']

    # also build an iso3-keyed lookup for countries the name merge misses
    iso_lookup = {}
    for iso3, trade_name in ISO3_TO_TRADE_NAME.items():
        matching = lpi_df[lpi_df.get('country_code', pd.Series(dtype=str)) == iso3]
        if not matching.empty and 'lpi_overall' in matching.columns:
            val = matching.dropna(subset=['lpi_overall']).sort_values('year').iloc[-1]['lpi_overall']
            iso_lookup[trade_name] = val

    merged = cy.merge(lpi_latest, on='country', how='left')

    # fill missing LPI via iso3 lookup
    no_lpi = merged['lpi_overall'].isna()
    merged.loc[no_lpi, 'lpi_overall'] = merged.loc[no_lpi, 'country'].map(iso_lookup)

    # normalise volatility (0 = stable, 1 = very volatile)
    v_lo, v_hi = merged['volatility'].quantile(0.05), merged['volatility'].quantile(0.95)
    merged['vol_norm'] = ((merged['volatility'].clip(v_lo, v_hi) - v_lo) / (v_hi - v_lo + 1e-9)).fillna(0.5)

    # LPI risk: inverse-normalised (low LPI -> high risk)
    l_lo = merged['lpi_overall'].quantile(0.05)
    l_hi = merged['lpi_overall'].quantile(0.95)
    merged['lpi_risk'] = (1 - (merged['lpi_overall'].clip(l_lo, l_hi) - l_lo) / (l_hi - l_lo + 1e-9)).fillna(0.5)

    merged['risk_score'] = (0.6 * merged['vol_norm'] + 0.4 * merged['lpi_risk']).round(3)
    merged['risk_tier']  = pd.cut(merged['risk_score'],
                                  bins=[0, 0.33, 0.66, 1.01],
                                  labels=['Low', 'Medium', 'High'],
                                  include_lowest=True)

    merged['region'] = merged['country'].map(REGION_MAP).fillna('Other')

    merged.to_csv(out_path, index=False)
    print(f"  Saved {len(merged):,} rows -> corridor_risk_scores.csv")
    return out_path


if __name__ == '__main__':
    print("=== Tank Corridor Risk Monitor — Data Ingestion ===\n")
    raw   = download_trade_data()
    process_trade_data(raw)
    download_lpi_data()
    compute_risk_scores()
    print("\nAll data ready.")
