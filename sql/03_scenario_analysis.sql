-- Recruiter demo queries. Run after `make all`:
-- sqlite3 data/processed/liquidity_stress.db < sql/03_scenario_analysis.sql

.headers on
.mode column

SELECT
    scenario_name,
    ROUND(hqla_eur / 1000000.0, 1) AS hqla_m,
    ROUND(net_30d_outflows_eur / 1000000.0, 1) AS net_outflows_m,
    ROUND(lcr_proxy_pct, 1) AS lcr_proxy_pct,
    ROUND(liquidity_surplus_eur / 1000000.0, 1) AS surplus_m,
    ROUND(delta_nii_eur / 1000000.0, 1) AS delta_nii_m
FROM scenario_summary
ORDER BY lcr_proxy_pct;

SELECT
    s.scenario_name,
    g.time_bucket,
    ROUND(g.net_gap_eur / 1000000.0, 1) AS net_gap_m,
    ROUND(g.cumulative_gap_eur / 1000000.0, 1) AS cumulative_gap_m,
    ROUND(g.post_buffer_cumulative_gap_eur / 1000000.0, 1) AS post_buffer_gap_m
FROM cashflow_gap g
JOIN scenarios s USING (scenario_id)
ORDER BY s.severity_rank, g.bucket_order;

SELECT
    side,
    product,
    ROUND(SUM(principal_eur) / 1000000.0, 1) AS exposure_m,
    ROUND(100.0 * SUM(principal_eur) /
        SUM(SUM(principal_eur)) OVER (PARTITION BY side), 1) AS side_share_pct
FROM positions
GROUP BY side, product
ORDER BY side, exposure_m DESC;

