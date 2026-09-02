from __future__ import annotations

import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from liquidity_stress.database import build_database
from liquidity_stress.generate import generate_dataset
from liquidity_stress.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


class PipelineIntegrationTests(unittest.TestCase):
    def test_end_to_end_pipeline_and_sql_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            raw = workspace / "raw"
            database = workspace / "liquidity.db"
            output = workspace / "outputs"
            artifacts = workspace / "artifacts"

            generate_dataset(raw, ROOT / "config" / "scenarios.json", seed=42, count=120)
            counts = build_database(raw, database, ROOT / "sql" / "01_schema.sql")
            manifest = run_pipeline(database, output, artifacts)

            self.assertEqual(counts, {"positions": 120, "market_rates": 72, "scenarios": 5})
            self.assertEqual(manifest["cashflow_gap_rows"], 30)
            self.assertTrue((output / "executive_summary.md").exists())
            self.assertTrue((artifacts / "lcr_proxy_by_scenario.svg").exists())
            self.assertTrue((artifacts / "nii_sensitivity_by_scenario.svg").exists())
            self.assertTrue((artifacts / "cumulative_cashflow_gap.svg").exists())

            with (output / "scenario_summary.csv").open(newline="", encoding="utf-8") as handle:
                csv_results = {row["scenario_id"]: row for row in csv.DictReader(handle)}
            connection = sqlite3.connect(database)
            try:
                sql_results = {
                    row[0]: row[1]
                    for row in connection.execute(
                        "SELECT scenario_id, lcr_proxy_pct FROM v_scenario_lcr_proxy"
                    )
                }
                stored_count = connection.execute("SELECT COUNT(*) FROM scenario_summary").fetchone()[0]
                gap_count = connection.execute("SELECT COUNT(*) FROM cashflow_gap").fetchone()[0]
            finally:
                connection.close()

            self.assertEqual(stored_count, 5)
            self.assertEqual(gap_count, 30)
            for scenario_id, sql_ratio in sql_results.items():
                self.assertAlmostEqual(
                    float(csv_results[scenario_id]["lcr_proxy_pct"]), sql_ratio, places=2
                )


if __name__ == "__main__":
    unittest.main()
