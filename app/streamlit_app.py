import os
import warnings
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Tank Corridor Risk Monitor",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

RISK_COLOURS = {'High': '#EF4444', 'Medium': '#F59E0B', 'Low': '#22C55E'}
REGION_COLOURS = {
    'Europe': '#3B82F6', 'Asia Pacific': '#8B5CF6', 'Americas': '#10B981',
    'Middle East & Africa': '#F59E0B', 'CIS': '#EF4444', 'Other': '#6B7280',
}


@st.cache_data
def load_data():
    paths = {
        'risk':  os.path.join(DATA_DIR, 'corridor_risk_scores.csv'),
        'trade': os.path.join(DATA_DIR, 'chemical_trade_flows.csv'),
        'lpi':   os.path.join(DATA_DIR, 'world_bank_lpi.csv'),
    }
    missing = [k for k, p in paths.items() if not os.path.exists(p)]
    if missing:
        return None, None, None
    risk_df  = pd.read_csv(paths['risk'])
    trade_df = pd.read_csv(paths['trade'])
    lpi_df   = pd.read_csv(paths['lpi'])
    risk_df['risk_tier'] = risk_df['risk_tier'].astype(str)
    return risk_df, trade_df, lpi_df


def no_data_msg():
    st.error("Data not found. Run `python data/ingest.py` first to fetch and process the datasets.")
    st.code("cd tank-corridor-risk-monitor\npython data/ingest.py", language="bash")
    st.stop()


def fmt_usd(val):
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.1f}M"
    return f"${val:,.0f}"


# ── sidebar ──────────────────────────────────────────────────────────────────

def sidebar(risk_df):
    st.sidebar.image("https://img.icons8.com/fluency/96/test-tube.png", width=60)
    st.sidebar.title("Tank Corridor Risk")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Deep Dive", "Segmentation", "Disruption Simulator"],
        index=0,
    )
    st.sidebar.markdown("---")

    years = sorted(risk_df['year'].dropna().unique().astype(int))
    sel_year = st.sidebar.selectbox("Year", years, index=len(years) - 1)

    regions = ['All'] + sorted(risk_df['region'].dropna().unique())
    sel_region = st.sidebar.selectbox("Region", regions)

    tiers = st.sidebar.multiselect("Risk Tier", ['High', 'Medium', 'Low'], default=['High', 'Medium', 'Low'])

    st.sidebar.markdown("---")
    st.sidebar.caption("Data: UN Comtrade via Kaggle · World Bank LPI")

    return page, sel_year, sel_region, tiers


def apply_filters(risk_df, trade_df, sel_year, sel_region, tiers):
    rf = risk_df[risk_df['year'] == sel_year].copy()
    if sel_region != 'All':
        rf = rf[rf['region'] == sel_region]
    rf = rf[rf['risk_tier'].isin(tiers)]

    tf = trade_df.copy()
    if sel_region != 'All':
        countries_in_region = risk_df[risk_df['region'] == sel_region]['country'].unique()
        tf = tf[tf['country'].isin(countries_in_region)]

    return rf, tf


# ── page 1: overview ──────────────────────────────────────────────────────────

def page_overview(rf, tf, risk_df, sel_year):
    st.title("Overview — Global Corridor Risk")
    st.markdown(f"**{sel_year}** snapshot across {len(rf):,} monitored corridors")

    # KPI row
    col1, col2, col3, col4 = st.columns(4)

    n_high = (rf['risk_tier'] == 'High').sum()
    n_total = len(rf)
    pct_high = round(n_high / n_total * 100, 1) if n_total else 0

    avg_risk = rf['risk_score'].mean()
    prev_year_df = risk_df[risk_df['year'] == sel_year - 1]
    prev_avg = prev_year_df['risk_score'].mean() if not prev_year_df.empty else avg_risk

    top_region = rf.groupby('region')['risk_score'].mean().idxmax() if not rf.empty else "N/A"
    top_trade = fmt_usd(rf['trade_usd'].sum()) if 'trade_usd' in rf.columns else "N/A"

    col1.metric("Corridors Monitored", f"{n_total:,}")
    col2.metric("Avg Risk Score", f"{avg_risk:.3f}", delta=f"{avg_risk - prev_avg:+.3f} vs prior yr",
                delta_color="inverse")
    col3.metric("High Risk Corridors", f"{n_high} ({pct_high}%)")
    col4.metric("Total Chemical Trade", top_trade)

    st.markdown("---")
    left, right = st.columns([3, 2])

    with left:
        # global trade trend — risk_df already has annual trade_usd per country-year
        annual = risk_df.groupby('year')['trade_usd'].sum().reset_index()

        fig = px.area(annual, x='year', y='trade_usd',
                      title="Global Chemical Trade Volume (all years)",
                      labels={'trade_usd': 'Trade USD', 'year': 'Year'},
                      color_discrete_sequence=['#F59E0B'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#E2E8F0', margin=dict(t=40, b=20))
        fig.update_yaxes(tickformat=".2s")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Global export value for organic and inorganic chemicals. Flat or declining years signal reduced tank container demand system-wide.")

    with right:
        # risk tier donut
        tier_counts = rf['risk_tier'].value_counts().reset_index()
        tier_counts.columns = ['risk_tier', 'count']
        fig2 = px.pie(tier_counts, names='risk_tier', values='count', hole=0.55,
                      title=f"Risk Distribution ({sel_year})",
                      color='risk_tier',
                      color_discrete_map=RISK_COLOURS)
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#E2E8F0',
                           margin=dict(t=40, b=20))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Share of corridors by risk tier. A growing 'High' slice signals increasing fleet repositioning pressure.")

    # top 15 riskiest corridors
    top15 = rf.nlargest(15, 'risk_score')[['country', 'region', 'risk_score', 'risk_tier', 'lpi_overall']]
    fig3 = px.bar(top15, x='risk_score', y='country', orientation='h',
                  color='risk_tier', color_discrete_map=RISK_COLOURS,
                  title=f"Top 15 Riskiest Corridors ({sel_year})",
                  labels={'risk_score': 'Risk Score', 'country': ''})
    fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                       font_color='#E2E8F0', yaxis={'categoryorder': 'total ascending'},
                       margin=dict(t=40, b=20))
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Composite risk = 60% trade volatility + 40% logistics risk. Corridors near the top warrant proactive fleet buffer positioning.")

    # download
    csv = rf.to_csv(index=False).encode('utf-8')
    st.download_button("Download Filtered Data (CSV)", csv, f"corridor_risk_{sel_year}.csv", "text/csv")


# ── page 2: deep dive ────────────────────────────────────────────────────────

def page_deep_dive(rf, tf, risk_df, trade_df, sel_year):
    st.title("Deep Dive — Corridor Analysis")

    countries = sorted(rf['country'].unique())
    if not countries:
        st.warning("No countries match current filters.")
        return

    sel_country = st.selectbox("Select Corridor (Country)", countries)

    country_risk = risk_df[risk_df['country'] == sel_country].sort_values('year')
    country_trade = trade_df[trade_df['country'] == sel_country].groupby('year')['trade_usd'].sum().reset_index()

    if country_risk.empty:
        st.warning(f"No risk data for {sel_country}.")
        return

    latest = country_risk[country_risk['year'] == sel_year]
    r_score = latest['risk_score'].values[0] if not latest.empty else None
    r_tier  = latest['risk_tier'].values[0]  if not latest.empty else None

    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Score", f"{r_score:.3f}" if r_score else "N/A")
    col2.metric("Risk Tier", r_tier or "N/A")
    col3.metric(
        "LPI Score",
        f"{latest['lpi_overall'].values[0]:.2f}" if not latest.empty and not pd.isna(latest['lpi_overall'].values[0]) else "N/A",
        help="World Bank Logistics Performance Index (1–5, higher is better)"
    )

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        # trade over time
        merged = country_trade.merge(
            country_risk[['year', 'risk_score', 'risk_tier']], on='year', how='left'
        )
        fig = px.bar(merged, x='year', y='trade_usd',
                     color='risk_tier', color_discrete_map=RISK_COLOURS,
                     title=f"{sel_country} — Chemical Export Value by Year",
                     labels={'trade_usd': 'Export Value (USD)', 'year': 'Year'})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#E2E8F0', margin=dict(t=40, b=20))
        fig.update_yaxes(tickformat=".2s")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Bar colour shows the risk tier assigned in each year. Volatility in bar height directly drives the risk score.")

    with right:
        # risk score over time
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=country_risk['year'], y=country_risk['risk_score'],
            mode='lines+markers', name='Risk Score',
            line=dict(color='#F59E0B', width=2),
            marker=dict(size=7)
        ))
        fig2.add_hline(y=0.66, line_dash='dash', line_color='#EF4444', annotation_text='High threshold')
        fig2.add_hline(y=0.33, line_dash='dash', line_color='#22C55E', annotation_text='Low threshold')
        fig2.update_layout(
            title=f"{sel_country} — Risk Score Trend",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#E2E8F0', margin=dict(t=40, b=20),
            yaxis=dict(range=[0, 1], title='Risk Score'),
            xaxis=dict(title='Year')
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Dashed lines mark tier boundaries. A score crossing 0.66 triggers the 'High Risk' flag in the SIOP review.")

    # risk breakdown
    st.subheader("Risk Component Breakdown")
    if not latest.empty:
        comp_data = pd.DataFrame({
            'Component': ['Trade Volatility (60%)', 'Logistics Risk (40%)'],
            'Score': [
                latest['vol_norm'].values[0] * 0.6,
                latest['lpi_risk'].values[0] * 0.4 if 'lpi_risk' in latest.columns else 0
            ]
        })
        fig3 = px.bar(comp_data, x='Component', y='Score', color='Component',
                      color_discrete_sequence=['#F59E0B', '#3B82F6'],
                      title="What's driving the risk score?")
        fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                           font_color='#E2E8F0', showlegend=False, margin=dict(t=40, b=20))
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("If the amber bar (volatility) dominates, the corridor is structurally unpredictable. If the blue bar (logistics) dominates, the risk is addressable via carrier/depot partnerships.")

    csv = country_risk.to_csv(index=False).encode('utf-8')
    st.download_button(f"Download {sel_country} data (CSV)", csv, f"{sel_country}_risk_history.csv", "text/csv")


# ── page 3: segmentation ─────────────────────────────────────────────────────

def page_segmentation(rf, trade_df, sel_year):
    st.title("Segmentation — Regional & Risk Comparison")

    # region avg risk bars
    region_stats = rf.groupby('region').agg(
        avg_risk=('risk_score', 'mean'),
        n_corridors=('country', 'count'),
        n_high=('risk_tier', lambda x: (x == 'High').sum())
    ).reset_index()
    region_stats['pct_high'] = (region_stats['n_high'] / region_stats['n_corridors'] * 100).round(1)

    left, right = st.columns(2)

    with left:
        fig = px.bar(region_stats.sort_values('avg_risk', ascending=False),
                     x='region', y='avg_risk',
                     color='region', color_discrete_map=REGION_COLOURS,
                     title=f"Average Risk Score by Region ({sel_year})",
                     labels={'avg_risk': 'Avg Risk Score', 'region': ''})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#E2E8F0', showlegend=False, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("High-risk regions need larger strategic tank buffer. This feeds directly into the SIOP fleet positioning inputs.")

    with right:
        fig2 = px.bar(region_stats.sort_values('pct_high', ascending=False),
                      x='region', y='pct_high',
                      color='region', color_discrete_map=REGION_COLOURS,
                      title=f"% of High-Risk Corridors by Region ({sel_year})",
                      labels={'pct_high': '% High Risk', 'region': ''})
        fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                           font_color='#E2E8F0', showlegend=False, margin=dict(t=40, b=20))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Regions with a high % of risky corridors indicate systemic logistics challenges rather than isolated country issues.")

    st.markdown("---")

    # scatter: volatility vs LPI risk
    # rf (corridor_risk_scores) already has trade_usd — no merge needed
    scatter_df = rf.dropna(subset=['vol_norm', 'lpi_risk']).copy()
    scatter_df['trade_usd'] = scatter_df['trade_usd'].fillna(1e8) if 'trade_usd' in scatter_df.columns else 1e8

    fig3 = px.scatter(scatter_df, x='vol_norm', y='lpi_risk',
                      size='trade_usd', color='region',
                      color_discrete_map=REGION_COLOURS,
                      hover_name='country',
                      hover_data={'vol_norm': ':.3f', 'lpi_risk': ':.3f', 'risk_tier': True},
                      title=f"Trade Volatility vs Logistics Risk ({sel_year})",
                      labels={'vol_norm': 'Trade Volatility (normalised)', 'lpi_risk': 'Logistics Risk (normalised)'})
    fig3.add_vline(x=0.5, line_dash='dot', line_color='#6B7280')
    fig3.add_hline(y=0.5, line_dash='dot', line_color='#6B7280')
    fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                       font_color='#E2E8F0', margin=dict(t=40, b=20), height=500)
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Top-right quadrant = high volatility AND poor logistics. These are the corridors where fleet misalignment is most costly and most likely. Bubble size = trade volume.")

    # risk tier stacked bar by region
    tier_region = rf.groupby(['region', 'risk_tier']).size().reset_index(name='count')
    fig4 = px.bar(tier_region, x='region', y='count', color='risk_tier',
                  color_discrete_map=RISK_COLOURS, barmode='stack',
                  title=f"Risk Tier Composition by Region ({sel_year})",
                  labels={'count': 'Number of Corridors', 'region': ''})
    fig4.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                       font_color='#E2E8F0', margin=dict(t=40, b=20))
    st.plotly_chart(fig4, use_container_width=True)
    st.caption("The stacked view reveals not just average risk but the full distribution. A region with many Low corridors but a few High ones may need targeted (not broad) intervention.")

    csv = rf.to_csv(index=False).encode('utf-8')
    st.download_button("Download Segmentation Data (CSV)", csv, f"segmentation_{sel_year}.csv", "text/csv")


# ── page 4: disruption simulator ─────────────────────────────────────────────

def page_simulator(rf, trade_df, risk_df, sel_year):
    st.title("Disruption Simulator — What-If Fleet Planning")
    st.markdown("Model the fleet demand impact of a trade disruption on any corridor.")

    col1, col2 = st.columns([2, 3])

    with col1:
        countries = sorted(rf['country'].dropna().unique())
        if not countries:
            st.warning("No corridors match current filters.")
            return

        sel_corridor = st.selectbox("Affected Corridor", countries)
        shock_pct = st.slider("Trade Volume Shock (%)", min_value=-80, max_value=20, value=-30, step=5,
                              help="Negative = trade contraction, positive = surge")
        duration = st.slider("Duration (years)", min_value=1, max_value=5, value=2)
        lpi_change = st.slider("LPI Score Change", min_value=-1.0, max_value=1.0, value=0.0, step=0.1,
                               help="Simulates logistics improvement or deterioration in the corridor")

    with col2:
        row = rf[rf['country'] == sel_corridor]
        if row.empty:
            st.info(f"Select a corridor to simulate.")
            return

        base_risk = float(row['risk_score'].values[0])
        base_vol  = float(row.get('vol_norm', pd.Series([0.5])).values[0])
        base_lpi  = float(row.get('lpi_risk', pd.Series([0.5])).values[0])

        # crude simulation: shock increases volatility norm proportionally
        shock_factor = abs(shock_pct) / 100
        new_vol  = min(1.0, base_vol + shock_factor * 0.6)
        new_lpi  = max(0.0, min(1.0, base_lpi - lpi_change * 0.2))
        new_risk = round(0.6 * new_vol + 0.4 * new_lpi, 3)
        delta    = round(new_risk - base_risk, 3)

        tier_fn = lambda s: 'High' if s > 0.66 else ('Medium' if s > 0.33 else 'Low')
        new_tier  = tier_fn(new_risk)
        base_tier = tier_fn(base_risk)

        # estimated tank demand impact (rough proxy)
        trade_base = trade_df[(trade_df['country'] == sel_corridor) & (trade_df['year'] == sel_year)]['trade_usd'].sum()
        demand_impact = trade_base * (shock_pct / 100) * 0.0001  # tanks per USD proxy

        m1, m2, m3 = st.columns(3)
        m1.metric("Baseline Risk", f"{base_risk:.3f}", f"{base_tier}")
        m2.metric("Simulated Risk", f"{new_risk:.3f}", f"{delta:+.3f}", delta_color="inverse")
        m3.metric("Tier Change", new_tier, "Upgraded" if new_risk < base_risk else "Downgraded" if new_risk > base_risk else "Unchanged",
                  delta_color="normal" if new_risk < base_risk else "inverse")

        st.markdown("---")

        # projection chart
        years_sim = list(range(sel_year, sel_year + duration + 3))
        risk_traj = [base_risk]
        for i, y in enumerate(years_sim[1:], 1):
            if i <= duration:
                risk_traj.append(new_risk)
            else:
                # gradual normalisation after shock ends
                risk_traj.append(round(new_risk + (base_risk - new_risk) * (i - duration) / 3, 3))

        proj_df = pd.DataFrame({'Year': years_sim, 'Risk Score': risk_traj})
        proj_df['Phase'] = ['Baseline'] + ['Shock Period'] * duration + ['Recovery'] * (len(years_sim) - duration - 1)

        fig = px.line(proj_df, x='Year', y='Risk Score', color='Phase',
                      markers=True, title=f"{sel_corridor} — Risk Score Projection",
                      color_discrete_map={'Baseline': '#22C55E', 'Shock Period': '#EF4444', 'Recovery': '#F59E0B'})
        fig.add_hline(y=0.66, line_dash='dash', line_color='#EF4444', annotation_text='High threshold')
        fig.add_hline(y=0.33, line_dash='dash', line_color='#22C55E', annotation_text='Low threshold')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color='#E2E8F0', yaxis=dict(range=[0, 1]),
                          margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"A {shock_pct}% volume shock lasting {duration} year(s) pushes {sel_corridor} into **{new_tier}** tier. Recovery assumes gradual normalisation over 3 years post-shock.")

    # fleet recommendation
    st.markdown("---")
    st.subheader("Fleet Reallocation Recommendation")
    if new_risk > base_risk:
        st.warning(
            f"**{sel_corridor}** risk increases by **{delta:+.3f}** under this scenario. "
            f"Recommend reducing tank allocation for this corridor by ~{abs(shock_pct)//3}% and "
            f"pre-positioning buffer fleet in adjacent low-risk corridors in {row['region'].values[0]}."
        )
    else:
        st.success(
            f"**{sel_corridor}** risk improves by **{abs(delta):.3f}** under this scenario. "
            f"This corridor can absorb additional tank deployment — consider routing excess fleet here."
        )

    # nearby corridors (same region, lower risk)
    same_region = rf[(rf['region'] == row['region'].values[0]) & (rf['country'] != sel_corridor)]
    absorption = same_region.nsmallest(5, 'risk_score')[['country', 'risk_score', 'risk_tier']]
    if not absorption.empty:
        st.markdown("**Lowest-risk corridors in same region (absorption candidates):**")
        st.dataframe(absorption.reset_index(drop=True), use_container_width=True)

    csv = proj_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Projection Data (CSV)", csv, f"{sel_corridor}_sim_{sel_year}.csv", "text/csv")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    risk_df, trade_df, lpi_df = load_data()
    if risk_df is None:
        no_data_msg()

    page, sel_year, sel_region, tiers = sidebar(risk_df)
    rf, tf = apply_filters(risk_df, trade_df, sel_year, sel_region, tiers)

    if page == "Overview":
        page_overview(rf, tf, risk_df, sel_year)
    elif page == "Deep Dive":
        page_deep_dive(rf, tf, risk_df, trade_df, sel_year)
    elif page == "Segmentation":
        page_segmentation(rf, trade_df, sel_year)
    elif page == "Disruption Simulator":
        page_simulator(rf, trade_df, risk_df, sel_year)


if __name__ == '__main__':
    main()
