# Data dictionary

All monetary fields use **EUR equivalent**. Dates are ISO `YYYY-MM-DD`. Percent fields are stored as percentage points (for example, `5.0` means 5%). The dataset is entirely synthetic.

## `positions`

Grain: one synthetic balance-sheet position as of 30 June 2026.

| Field | Type | Definition / accepted values |
|---|---|---|
| `position_id` | text, PK | Synthetic identifier such as `POS-00001` |
| `as_of_date` | date text | Reporting snapshot date |
| `side` | text | `Asset` or `Liability` |
| `desk` | text | Illustrative business owner: Treasury, Retail Banking, Commercial Banking, Corporate Banking, or Liquid Asset Buffer |
| `product` | text | Instrument/product family used for aggregation |
| `counterparty_segment` | text | Behavioural segment used to select retail vs wholesale stress multipliers |
| `currency` | text | Original position currency (`EUR`, `USD`, `GBP`, `CHF`); principal is already translated to EUR |
| `principal_eur` | real | Positive EUR-equivalent principal |
| `contractual_rate_pct` | real | Annual nominal rate in percentage points |
| `rate_type` | text | `Fixed` or `Variable` |
| `repricing_days` | integer | Days until next modelled rate reset; fixed-rate positions use contractual maturity |
| `maturity_days` | integer | Days until contractual/modelled maturity |
| `liquidity_treatment` | text | `Non-maturity`, `Contractual`, or `Liquidity buffer` |
| `hqla_level` | text | Simplified `None`, `Level 1`, `Level 2A`, or `Level 2B` classification |
| `encumbered` | integer | `1` excludes an otherwise eligible asset from the liquidity buffer; `0` is available |
| `runoff_weight_pct` | real | Baseline modelled liability outflow weight, 0–100 |
| `inflow_weight_pct` | real | Baseline recognised asset inflow weight, 0–100 |

## `scenarios`

Grain: one controlled stress scenario.

| Field | Type | Definition |
|---|---|---|
| `scenario_id` | text, PK | Stable machine identifier |
| `scenario_name` | text | Dashboard label |
| `severity_rank` | integer | Display order from 1 (baseline) to 4 (most severe in this case) |
| `retail_runoff_multiplier` | real | Multiplier applied to positions in the Retail segment |
| `wholesale_runoff_multiplier` | real | Multiplier applied to all non-Retail liability segments |
| `asset_inflow_multiplier` | real | Fraction of baseline inflows recognised under stress |
| `hqla_haircut_addon` | real | Decimal haircut added to the simplified HQLA factor |
| `rate_shock_bps` | integer | Parallel interest-rate shock in basis points |
| `asset_beta` | real | Fraction of the rate shock passed through to repricing assets |
| `deposit_beta` | real | Fraction of the rate shock passed through to repricing liabilities |
| `description` | text | Plain-language stress narrative |

## `market_rates`

Grain: one illustrative market-rate series per month-end.

| Field | Type | Definition |
|---|---|---|
| `rate_date` | date text, PK part | Month-end observation date |
| `rate_name` | text, PK part | ECB deposit facility, EURIBOR 3M, or EUR swap 2Y |
| `rate_pct` | real | Synthetic/illustrative percentage rate; not sourced market data |

## `scenario_summary`

Grain: one calculated result per scenario.

| Field | Definition |
|---|---|
| `hqla_eur` | Scenario-adjusted unencumbered liquid-asset buffer |
| `gross_30d_outflows_eur` | Modelled liability outflows within 30 days |
| `raw_30d_inflows_eur` | Stressed contractual asset inflows before the cap |
| `capped_30d_inflows_eur` | Recognised inflows, limited to 75% of outflows |
| `net_30d_outflows_eur` | Gross outflows less recognised inflows |
| `lcr_proxy_pct` | Eligible buffer divided by net outflows × 100 |
| `liquidity_surplus_eur` | Eligible buffer less net outflows; negative means shortfall |
| `survival_days_proxy` | `30 × buffer / net outflows`, capped at 365 days for display |
| `base_annual_nii_eur` | Static-balance interest income less expense before the scenario shock |
| `delta_nii_eur` | One-year NII change from repricing timing, shock, and betas |
| `projected_annual_nii_eur` | Base annual NII plus scenario NII change |

## `cashflow_gap`

Grain: one scenario and one time bucket.

| Field | Definition |
|---|---|
| `bucket_order` | Numeric display order, 1–6 |
| `time_bucket` | `0–7`, `8–30`, `31–90`, `91–180`, `181–365`, or `>365 days` |
| `stressed_inflows_eur` | Inflow-weighted asset principal in the tenor |
| `stressed_outflows_eur` | Runoff-weighted liability principal in the tenor |
| `net_gap_eur` | Inflows less outflows |
| `cumulative_gap_eur` | Running sum of net gap without the liquid-asset buffer |
| `post_buffer_cumulative_gap_eur` | Cumulative gap plus scenario-adjusted eligible buffer |

## Files outside SQLite

| File | Purpose |
|---|---|
| `data/raw/generation_metadata.json` | Seed, as-of date, row counts, and explicit `contains_real_customer_data: false` lineage |
| `outputs/portfolio_composition.csv` | Product/currency aggregation for dashboard and exploratory analysis |
| `outputs/analysis_manifest.json` | Output row counts and model-boundary flags |
| `outputs/executive_summary.md` | Auto-generated decision summary tied to current model results |

