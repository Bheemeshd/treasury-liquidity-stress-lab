-- Each query should return zero rows (or zero in the aggregate) after ETL.

SELECT 'duplicate_position_id' AS check_name, position_id, COUNT(*) AS issue_count
FROM positions
GROUP BY position_id
HAVING COUNT(*) > 1;

SELECT 'non_positive_principal' AS check_name, position_id, principal_eur
FROM positions
WHERE principal_eur <= 0 OR principal_eur IS NULL;

SELECT 'invalid_liquidity_weight' AS check_name, position_id, runoff_weight_pct
FROM positions
WHERE runoff_weight_pct NOT BETWEEN 0 AND 100
   OR inflow_weight_pct NOT BETWEEN 0 AND 100;

SELECT 'asset_with_runoff' AS check_name, position_id, runoff_weight_pct
FROM positions
WHERE side = 'Asset' AND runoff_weight_pct <> 0;

SELECT 'liability_with_hqla' AS check_name, position_id, hqla_level
FROM positions
WHERE side = 'Liability' AND hqla_level <> 'None';

SELECT 'row_counts' AS check_name,
       (SELECT COUNT(*) FROM positions) AS positions,
       (SELECT COUNT(*) FROM scenarios) AS scenarios,
       (SELECT COUNT(*) FROM market_rates) AS market_rates;

