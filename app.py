"""Streamlit dashboard for the synthetic treasury stress-testing case study."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"

st.set_page_config(
    page_title="Treasury Liquidity Stress Lab",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp {background: #07111f; color: #e2e8f0;}
      [data-testid="stSidebar"] {background: #0b172a; border-right: 1px solid #24354f;}
      [data-testid="stMetric"] {background: linear-gradient(145deg,#10213a,#0c192c); border: 1px solid #253b59; padding: 16px; border-radius: 12px;}
      [data-testid="stMetricLabel"] {color: #9fb4cf;}
      .eyebrow {color:#38bdf8; letter-spacing:.12em; text-transform:uppercase; font-size:.78rem; font-weight:700;}
      .hero {font-size:2.25rem; font-weight:760; line-height:1.08; margin:.25rem 0 .45rem;}
      .subtle {color:#9fb4cf; max-width:880px;}
      .disclaimer {background:#271d0b; color:#fde68a; border:1px solid #784f13; border-radius:10px; padding:12px 14px; font-size:.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = [
        OUTPUTS / "scenario_summary.csv",
        OUTPUTS / "cashflow_gap.csv",
        OUTPUTS / "portfolio_composition.csv",
        OUTPUTS / "market_rates.csv",
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing generated outputs: {', '.join(missing)}. Run `make all`.")
    return tuple(pd.read_csv(path) for path in required)  # type: ignore[return-value]


def euro_millions(value: float) -> str:
    return f"€{value / 1_000_000:,.1f}m"


try:
    summary, gaps, composition, rates = load_data()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.code("python3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\nmake all\nmake dashboard", language="bash")
    st.stop()

st.sidebar.markdown("### Scenario control")
scenario_names = summary["scenario_name"].tolist()
selected_name = st.sidebar.selectbox("Stress scenario", scenario_names, index=0)
selected = summary.loc[summary["scenario_name"] == selected_name].iloc[0]
selected_id = selected["scenario_id"]
selected_gaps = gaps.loc[gaps["scenario_id"] == selected_id].sort_values("bucket_order")

st.sidebar.markdown("### Analytical lens")
st.sidebar.caption("As of 30 June 2026")
st.sidebar.caption("900 deterministic synthetic positions")
st.sidebar.caption("All amounts translated to EUR")
st.sidebar.markdown("---")
st.sidebar.info("Tip: compare Combined Severe with Rates +200 bps to separate funding risk from earnings sensitivity.")

st.markdown('<div class="eyebrow">Bank treasury analytics portfolio</div>', unsafe_allow_html=True)
st.markdown('<div class="hero">Liquidity & interest-rate stress lab</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtle">An end-to-end analytical workflow linking synthetic balance-sheet positions, transparent stress assumptions, 30-day liquidity coverage, contractual cash-flow gaps, and one-year NII sensitivity.</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("LCR-style proxy", f"{selected['lcr_proxy_pct']:,.1f}%", delta=f"{selected['lcr_proxy_pct'] - 100:,.1f} pp vs reference")
kpi2.metric("Eligible buffer", euro_millions(selected["hqla_eur"]))
kpi3.metric("Net 30d outflows", euro_millions(selected["net_30d_outflows_eur"]))
kpi4.metric("Liquidity surplus", euro_millions(selected["liquidity_surplus_eur"]))
kpi5.metric("Δ one-year NII", euro_millions(selected["delta_nii_eur"]))

tab_overview, tab_gap, tab_nii, tab_portfolio, tab_method = st.tabs(
    ["Executive view", "Cash-flow gap", "NII sensitivity", "Portfolio", "Method & controls"]
)

with tab_overview:
    left, right = st.columns([1.15, 1])
    with left:
        lcr_chart = px.bar(
            summary,
            x="scenario_name",
            y="lcr_proxy_pct",
            color="lcr_proxy_pct",
            color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            labels={"scenario_name": "Scenario", "lcr_proxy_pct": "Coverage proxy (%)"},
            title="Coverage deteriorates as runoff and haircuts intensify",
        )
        lcr_chart.add_hline(y=100, line_dash="dash", line_color="#e2e8f0", annotation_text="Illustrative 100% reference")
        lcr_chart.update_layout(coloraxis_showscale=False, template="plotly_dark", paper_bgcolor="#07111f", plot_bgcolor="#0b172a")
        st.plotly_chart(lcr_chart, use_container_width=True)
    with right:
        waterfall = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "total"],
                x=["Eligible buffer", "Net 30d outflows", "Surplus / shortfall"],
                y=[selected["hqla_eur"] / 1e6, -selected["net_30d_outflows_eur"] / 1e6, selected["liquidity_surplus_eur"] / 1e6],
                connector={"line": {"color": "#64748b"}},
                increasing={"marker": {"color": "#22c55e"}},
                decreasing={"marker": {"color": "#f43f5e"}},
                totals={"marker": {"color": "#38bdf8"}},
            )
        )
        waterfall.update_layout(title=f"{selected_name}: liquidity bridge (€m)", template="plotly_dark", paper_bgcolor="#07111f", plot_bgcolor="#0b172a", showlegend=False)
        st.plotly_chart(waterfall, use_container_width=True)

with tab_gap:
    gap_chart = go.Figure()
    gap_chart.add_bar(x=selected_gaps["time_bucket"], y=selected_gaps["stressed_inflows_eur"] / 1e6, name="Stressed inflows", marker_color="#22c55e")
    gap_chart.add_bar(x=selected_gaps["time_bucket"], y=-selected_gaps["stressed_outflows_eur"] / 1e6, name="Stressed outflows", marker_color="#f43f5e")
    gap_chart.add_scatter(x=selected_gaps["time_bucket"], y=selected_gaps["post_buffer_cumulative_gap_eur"] / 1e6, name="Post-buffer cumulative gap", line={"color": "#38bdf8", "width": 4}, mode="lines+markers")
    gap_chart.add_hline(y=0, line_dash="dash", line_color="#e2e8f0")
    gap_chart.update_layout(barmode="relative", title=f"{selected_name}: stressed liquidity ladder", yaxis_title="€ million", template="plotly_dark", paper_bgcolor="#07111f", plot_bgcolor="#0b172a")
    st.plotly_chart(gap_chart, use_container_width=True)
    st.dataframe(
        selected_gaps[["time_bucket", "stressed_inflows_eur", "stressed_outflows_eur", "net_gap_eur", "post_buffer_cumulative_gap_eur"]].style.format({column: "€{:,.0f}" for column in selected_gaps.columns if column.endswith("_eur")}),
        use_container_width=True,
        hide_index=True,
    )

with tab_nii:
    nii = summary.copy()
    nii["delta_nii_m"] = nii["delta_nii_eur"] / 1e6
    nii_chart = px.bar(
        nii,
        x="scenario_name",
        y="delta_nii_m",
        color="delta_nii_m",
        color_continuous_scale=["#f43f5e", "#64748b", "#22c55e"],
        labels={"scenario_name": "Scenario", "delta_nii_m": "Δ NII (€m)"},
        title="One-year NII change from parallel rate shocks",
    )
    nii_chart.add_hline(y=0, line_color="#e2e8f0")
    nii_chart.update_layout(coloraxis_showscale=False, template="plotly_dark", paper_bgcolor="#07111f", plot_bgcolor="#0b172a")
    st.plotly_chart(nii_chart, use_container_width=True)
    st.caption("Sensitivity uses repricing timing and scenario pass-through betas. It is not a full IRRBB/EVE model.")

with tab_portfolio:
    by_product = composition.groupby(["side", "product"], as_index=False)["principal_eur"].sum()
    by_product["principal_m"] = by_product["principal_eur"] / 1e6
    portfolio_chart = px.bar(
        by_product,
        x="principal_m",
        y="product",
        color="side",
        orientation="h",
        barmode="group",
        color_discrete_map={"Asset": "#38bdf8", "Liability": "#f59e0b"},
        labels={"principal_m": "Principal (€m)", "product": "Product"},
        title="Synthetic balance-sheet composition",
    )
    portfolio_chart.update_layout(template="plotly_dark", paper_bgcolor="#07111f", plot_bgcolor="#0b172a", yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(portfolio_chart, use_container_width=True)
    rate_chart = px.line(rates, x="rate_date", y="rate_pct", color="rate_name", markers=True, title="Illustrative EUR market-rate context", labels={"rate_date": "Date", "rate_pct": "Rate (%)", "rate_name": "Series"})
    rate_chart.update_layout(template="plotly_dark", paper_bgcolor="#07111f", plot_bgcolor="#0b172a")
    st.plotly_chart(rate_chart, use_container_width=True)

with tab_method:
    st.markdown(
        """
        #### Calculation flow

        1. Seeded generator creates position-level assets, liabilities and illustrative market rates.
        2. ETL validates required columns and loads constrained SQLite tables.
        3. Scenario engine stresses liability runoff, asset inflows, liquid-asset haircuts and rates.
        4. The model caps recognised 30-day inflows at 75% of outflows, computes a coverage proxy, buckets cash flows and estimates one-year NII sensitivity.
        5. Tests reconcile component calculations, deterministic generation and SQL/Python coverage results.

        #### Control checks

        - Unique position IDs and positive principal values
        - Allowed side, currency, HQLA and rate-type values
        - Inflow and runoff weights constrained to 0–100%
        - Encumbered assets excluded from the eligible liquidity buffer
        - Recognised inflows capped at 75% of modelled 30-day outflows
        """
    )

st.markdown(
    '<div class="disclaimer"><strong>Educational boundary:</strong> This dashboard is a portfolio demonstration using synthetic data. It is not regulatory LCR, IRRBB, ILAAP, ALM, risk appetite, or financial reporting.</div>',
    unsafe_allow_html=True,
)

