from __future__ import annotations

import unittest

from liquidity_stress.analysis import (
    calculate_cashflow_gaps,
    calculate_lcr_proxy,
    calculate_nii_sensitivity,
    position_hqla,
)


SCENARIO = {
    "scenario_id": "test",
    "scenario_name": "Test",
    "retail_runoff_multiplier": 1.0,
    "wholesale_runoff_multiplier": 1.0,
    "asset_inflow_multiplier": 1.0,
    "hqla_haircut_addon": 0.0,
    "rate_shock_bps": 100,
    "asset_beta": 0.8,
    "deposit_beta": 0.4,
}


def position(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "position_id": "P1",
        "side": "Asset",
        "principal_eur": 100.0,
        "contractual_rate_pct": 4.0,
        "rate_type": "Variable",
        "repricing_days": 30,
        "maturity_days": 10,
        "liquidity_treatment": "Contractual",
        "hqla_level": "None",
        "encumbered": 0,
        "runoff_weight_pct": 0.0,
        "inflow_weight_pct": 50.0,
        "counterparty_segment": "Corporate",
    }
    row.update(overrides)
    return row


class AnalysisTests(unittest.TestCase):
    def test_inflow_cap_is_75_percent_of_outflows(self) -> None:
        rows = [
            position(principal_eur=1_000.0, inflow_weight_pct=100.0),
            position(
                position_id="P2",
                side="Liability",
                principal_eur=100.0,
                contractual_rate_pct=1.0,
                liquidity_treatment="Non-maturity",
                hqla_level="None",
                runoff_weight_pct=100.0,
                inflow_weight_pct=0.0,
                counterparty_segment="Retail",
            ),
        ]
        result = calculate_lcr_proxy(rows, SCENARIO)
        self.assertEqual(result["gross_30d_outflows_eur"], 100.0)
        self.assertEqual(result["raw_30d_inflows_eur"], 1_000.0)
        self.assertEqual(result["capped_30d_inflows_eur"], 75.0)
        self.assertEqual(result["net_30d_outflows_eur"], 25.0)

    def test_encumbered_hqla_is_excluded(self) -> None:
        eligible = position(hqla_level="Level 1", encumbered=0)
        encumbered = position(hqla_level="Level 1", encumbered=1)
        self.assertEqual(position_hqla(eligible, SCENARIO), 100.0)
        self.assertEqual(position_hqla(encumbered, SCENARIO), 0.0)

    def test_additional_haircut_reduces_hqla(self) -> None:
        scenario = dict(SCENARIO, hqla_haircut_addon=0.10)
        result = position_hqla(position(principal_eur=100.0, hqla_level="Level 2A"), scenario)
        self.assertAlmostEqual(result, 75.0)

    def test_positive_rate_shock_benefits_asset_sensitive_gap(self) -> None:
        rows = [
            position(principal_eur=1_000.0, repricing_days=30),
            position(
                position_id="P2",
                side="Liability",
                principal_eur=500.0,
                contractual_rate_pct=2.0,
                repricing_days=30,
                liquidity_treatment="Non-maturity",
                runoff_weight_pct=5.0,
                inflow_weight_pct=0.0,
                counterparty_segment="Retail",
            ),
        ]
        result = calculate_nii_sensitivity(rows, SCENARIO)
        self.assertGreater(result["delta_nii_eur"], 0.0)
        self.assertAlmostEqual(
            result["projected_annual_nii_eur"],
            result["base_annual_nii_eur"] + result["delta_nii_eur"],
        )

    def test_cashflow_gap_reconciles_by_bucket(self) -> None:
        rows = [
            position(principal_eur=100.0, maturity_days=10, inflow_weight_pct=50.0),
            position(
                position_id="P2",
                side="Liability",
                principal_eur=80.0,
                maturity_days=10,
                liquidity_treatment="Contractual",
                runoff_weight_pct=100.0,
                inflow_weight_pct=0.0,
            ),
        ]
        gaps = calculate_cashflow_gaps(rows, SCENARIO)
        bucket = gaps[1]
        self.assertEqual(bucket["time_bucket"], "8-30 days")
        self.assertEqual(bucket["stressed_inflows_eur"], 50.0)
        self.assertEqual(bucket["stressed_outflows_eur"], 80.0)
        self.assertEqual(bucket["net_gap_eur"], -30.0)


if __name__ == "__main__":
    unittest.main()

