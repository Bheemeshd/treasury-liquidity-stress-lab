PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    as_of_date TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('Asset', 'Liability')),
    desk TEXT NOT NULL,
    product TEXT NOT NULL,
    counterparty_segment TEXT NOT NULL,
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    principal_eur REAL NOT NULL CHECK (principal_eur > 0),
    contractual_rate_pct REAL NOT NULL,
    rate_type TEXT NOT NULL CHECK (rate_type IN ('Fixed', 'Variable')),
    repricing_days INTEGER NOT NULL CHECK (repricing_days >= 0),
    maturity_days INTEGER NOT NULL CHECK (maturity_days >= 0),
    liquidity_treatment TEXT NOT NULL,
    hqla_level TEXT NOT NULL CHECK (hqla_level IN ('None', 'Level 1', 'Level 2A', 'Level 2B')),
    encumbered INTEGER NOT NULL CHECK (encumbered IN (0, 1)),
    runoff_weight_pct REAL NOT NULL CHECK (runoff_weight_pct BETWEEN 0 AND 100),
    inflow_weight_pct REAL NOT NULL CHECK (inflow_weight_pct BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS market_rates (
    rate_date TEXT NOT NULL,
    rate_name TEXT NOT NULL,
    rate_pct REAL NOT NULL,
    PRIMARY KEY (rate_date, rate_name)
);

CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL UNIQUE,
    severity_rank INTEGER NOT NULL CHECK (severity_rank BETWEEN 1 AND 5),
    retail_runoff_multiplier REAL NOT NULL CHECK (retail_runoff_multiplier >= 0),
    wholesale_runoff_multiplier REAL NOT NULL CHECK (wholesale_runoff_multiplier >= 0),
    asset_inflow_multiplier REAL NOT NULL CHECK (asset_inflow_multiplier BETWEEN 0 AND 1),
    hqla_haircut_addon REAL NOT NULL CHECK (hqla_haircut_addon BETWEEN 0 AND 1),
    rate_shock_bps INTEGER NOT NULL,
    asset_beta REAL NOT NULL CHECK (asset_beta BETWEEN 0 AND 1),
    deposit_beta REAL NOT NULL CHECK (deposit_beta BETWEEN 0 AND 1),
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_summary (
    scenario_id TEXT PRIMARY KEY REFERENCES scenarios(scenario_id),
    scenario_name TEXT NOT NULL,
    hqla_eur REAL NOT NULL,
    gross_30d_outflows_eur REAL NOT NULL,
    raw_30d_inflows_eur REAL NOT NULL,
    capped_30d_inflows_eur REAL NOT NULL,
    net_30d_outflows_eur REAL NOT NULL,
    lcr_proxy_pct REAL NOT NULL,
    liquidity_surplus_eur REAL NOT NULL,
    survival_days_proxy REAL NOT NULL,
    base_annual_nii_eur REAL NOT NULL,
    delta_nii_eur REAL NOT NULL,
    projected_annual_nii_eur REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS cashflow_gap (
    scenario_id TEXT NOT NULL REFERENCES scenarios(scenario_id),
    bucket_order INTEGER NOT NULL,
    time_bucket TEXT NOT NULL,
    stressed_inflows_eur REAL NOT NULL,
    stressed_outflows_eur REAL NOT NULL,
    net_gap_eur REAL NOT NULL,
    cumulative_gap_eur REAL NOT NULL,
    post_buffer_cumulative_gap_eur REAL NOT NULL,
    PRIMARY KEY (scenario_id, bucket_order)
);

CREATE INDEX IF NOT EXISTS idx_positions_side_product ON positions(side, product);
CREATE INDEX IF NOT EXISTS idx_positions_maturity ON positions(maturity_days);
CREATE INDEX IF NOT EXISTS idx_positions_hqla ON positions(hqla_level, encumbered);
CREATE INDEX IF NOT EXISTS idx_cashflow_scenario ON cashflow_gap(scenario_id, bucket_order);

CREATE VIEW IF NOT EXISTS v_balance_sheet_summary AS
SELECT
    side,
    product,
    currency,
    COUNT(*) AS position_count,
    ROUND(SUM(principal_eur), 2) AS principal_eur,
    ROUND(SUM(principal_eur * contractual_rate_pct) / SUM(principal_eur), 4) AS weighted_rate_pct
FROM positions
GROUP BY side, product, currency;

CREATE VIEW IF NOT EXISTS v_30d_liquidity_components AS
SELECT
    s.scenario_id,
    s.scenario_name,
    p.position_id,
    CASE
        WHEN p.side = 'Asset' AND p.encumbered = 0 AND p.hqla_level <> 'None'
        THEN p.principal_eur * MAX(
            0.0,
            CASE p.hqla_level
                WHEN 'Level 1' THEN 1.00
                WHEN 'Level 2A' THEN 0.85
                WHEN 'Level 2B' THEN 0.50
                ELSE 0.00
            END - s.hqla_haircut_addon
        ) ELSE 0.0
    END AS hqla_eur,
    CASE
        WHEN p.side = 'Liability'
         AND (p.liquidity_treatment = 'Non-maturity' OR p.maturity_days <= 30)
        THEN MIN(
            p.principal_eur,
            p.principal_eur * p.runoff_weight_pct / 100.0 *
            CASE WHEN p.counterparty_segment = 'Retail'
                THEN s.retail_runoff_multiplier
                ELSE s.wholesale_runoff_multiplier
            END
        ) ELSE 0.0
    END AS outflow_eur,
    CASE
        WHEN p.side = 'Asset' AND p.hqla_level = 'None' AND p.maturity_days <= 30
        THEN p.principal_eur * p.inflow_weight_pct / 100.0 * s.asset_inflow_multiplier
        ELSE 0.0
    END AS inflow_eur
FROM scenarios s
CROSS JOIN positions p;

CREATE VIEW IF NOT EXISTS v_scenario_lcr_proxy AS
WITH components AS (
    SELECT
        scenario_id,
        scenario_name,
        SUM(hqla_eur) AS hqla_eur,
        SUM(outflow_eur) AS gross_outflows_eur,
        SUM(inflow_eur) AS raw_inflows_eur
    FROM v_30d_liquidity_components
    GROUP BY scenario_id, scenario_name
), capped AS (
    SELECT
        *,
        MIN(raw_inflows_eur, gross_outflows_eur * 0.75) AS capped_inflows_eur
    FROM components
)
SELECT
    scenario_id,
    scenario_name,
    ROUND(hqla_eur, 2) AS hqla_eur,
    ROUND(gross_outflows_eur, 2) AS gross_outflows_eur,
    ROUND(raw_inflows_eur, 2) AS raw_inflows_eur,
    ROUND(capped_inflows_eur, 2) AS capped_inflows_eur,
    ROUND(gross_outflows_eur - capped_inflows_eur, 2) AS net_outflows_eur,
    ROUND(100.0 * hqla_eur / MAX(gross_outflows_eur - capped_inflows_eur, 1.0), 2) AS lcr_proxy_pct
FROM capped;

