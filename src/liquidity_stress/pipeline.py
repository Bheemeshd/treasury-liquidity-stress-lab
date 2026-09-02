"""Run the analytical model, persist outputs, and render portfolio artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from .analysis import build_scenario_results, portfolio_composition
from .charts import bar_chart, cumulative_gap_chart


SUMMARY_FIELDS = [
    "scenario_id",
    "scenario_name",
    "hqla_eur",
    "gross_30d_outflows_eur",
    "raw_30d_inflows_eur",
    "capped_30d_inflows_eur",
    "net_30d_outflows_eur",
    "lcr_proxy_pct",
    "liquidity_surplus_eur",
    "survival_days_proxy",
    "base_annual_nii_eur",
    "delta_nii_eur",
    "projected_annual_nii_eur",
]

GAP_FIELDS = [
    "scenario_id",
    "bucket_order",
    "time_bucket",
    "stressed_inflows_eur",
    "stressed_outflows_eur",
    "net_gap_eur",
    "cumulative_gap_eur",
    "post_buffer_cumulative_gap_eur",
]


def _rows(connection: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    cursor = connection.execute(query)
    return [dict(row) for row in cursor.fetchall()]


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected_fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=selected_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _round_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: round(value, 2) if isinstance(value, float) else value for key, value in row.items()}
        for row in rows
    ]


def _persist_results(
    connection: sqlite3.Connection,
    summaries: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> None:
    with connection:
        connection.execute("DELETE FROM cashflow_gap")
        connection.execute("DELETE FROM scenario_summary")
        connection.executemany(
            f"INSERT INTO scenario_summary ({', '.join(SUMMARY_FIELDS)}) "
            f"VALUES ({', '.join('?' for _ in SUMMARY_FIELDS)})",
            [[row[field] for field in SUMMARY_FIELDS] for row in summaries],
        )
        connection.executemany(
            f"INSERT INTO cashflow_gap ({', '.join(GAP_FIELDS)}) "
            f"VALUES ({', '.join('?' for _ in GAP_FIELDS)})",
            [[row[field] for field in GAP_FIELDS] for row in gaps],
        )


def _executive_summary(summaries: list[dict[str, Any]]) -> str:
    by_id = {row["scenario_id"]: row for row in summaries}
    baseline = by_id["baseline"]
    severe = by_id["combined_severe"]
    worst = min(summaries, key=lambda row: row["lcr_proxy_pct"])
    rate = by_id["rate_up_200bp"]
    direction = "increase" if rate["delta_nii_eur"] >= 0 else "decrease"
    return f"""# Executive analytical summary

**As-of date:** 30 June 2026  
**Dataset:** deterministic synthetic portfolio; no customer or bank data  
**Decision lens:** treasury liquidity resilience and one-year earnings sensitivity

## Headline findings

- The baseline LCR-style proxy is **{baseline['lcr_proxy_pct']:.1f}%**, with **€{baseline['liquidity_surplus_eur']/1_000_000:,.1f}m** of modelled liquidity surplus.
- The lowest coverage result is **{worst['scenario_name']} at {worst['lcr_proxy_pct']:.1f}%**. The model therefore {'falls below' if worst['lcr_proxy_pct'] < 100 else 'remains above'} the illustrative 100% reference line under the most constraining scenario.
- Combined Severe reduces the available liquid-asset buffer to **€{severe['hqla_eur']/1_000_000:,.1f}m** and raises net 30-day outflows to **€{severe['net_30d_outflows_eur']/1_000_000:,.1f}m**.
- A +200 bps parallel shock produces an estimated one-year NII **{direction} of €{abs(rate['delta_nii_eur'])/1_000_000:,.1f}m**, driven by the simplified asset/liability repricing gap and pass-through assumptions.

## Management interpretation

The combined liquidity scenario is the binding case in this synthetic portfolio. A practical treasury response would prioritize diversified term funding, reduction of short-dated wholesale concentration, and maintenance of unencumbered Level 1 assets. NII sensitivity should be interpreted alongside liquidity: faster liability repricing can offset the earnings benefit of asset repricing even when the rate shock is positive.

## Important boundary

This case study is educational analytics, **not regulatory LCR, IRRBB, ILAAP, ALM, or financial reporting**. It deliberately omits jurisdiction-specific classifications, Level 2 caps, secured-funding mechanics, derivative cash flows, FX convertibility constraints, behavioural decay calibration, and supervisory stress requirements.
"""


def run_pipeline(database: Path, output_dir: Path, artifact_dir: Path) -> dict[str, int]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        positions = _rows(connection, "SELECT * FROM positions ORDER BY position_id")
        scenarios = _rows(
            connection, "SELECT * FROM scenarios ORDER BY severity_rank, scenario_name"
        )
        rates = _rows(connection, "SELECT * FROM market_rates ORDER BY rate_date, rate_name")
        if not positions or not scenarios:
            raise ValueError("Database is empty; run the generator and ETL first")
        summaries, gaps = build_scenario_results(positions, scenarios)
        composition = portfolio_composition(positions)
        _persist_results(connection, summaries, gaps)
    finally:
        connection.close()

    rounded_summaries = _round_rows(summaries)
    rounded_gaps = _round_rows(gaps)
    rounded_composition = _round_rows(composition)
    _write_csv(output_dir / "scenario_summary.csv", rounded_summaries, SUMMARY_FIELDS)
    _write_csv(output_dir / "cashflow_gap.csv", rounded_gaps, GAP_FIELDS)
    _write_csv(output_dir / "portfolio_composition.csv", rounded_composition)
    _write_csv(output_dir / "market_rates.csv", rates)
    (output_dir / "executive_summary.md").write_text(
        _executive_summary(summaries), encoding="utf-8"
    )
    manifest = {
        "portfolio_positions": len(positions),
        "scenarios_analyzed": len(scenarios),
        "cashflow_gap_rows": len(gaps),
        "market_rate_observations": len(rates),
        "synthetic_data_only": True,
        "regulatory_reporting": False,
    }
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    lcr_rows = [
        {"scenario_name": row["scenario_name"], "value": row["lcr_proxy_pct"]}
        for row in summaries
    ]
    bar_chart(
        lcr_rows,
        "scenario_name",
        "value",
        "30-day liquidity coverage proxy",
        artifact_dir / "lcr_proxy_by_scenario.svg",
        suffix="%",
        reference=100.0,
    )
    nii_rows = [
        {"scenario_name": row["scenario_name"], "value": row["delta_nii_eur"] / 1_000_000}
        for row in summaries
    ]
    bar_chart(
        nii_rows,
        "scenario_name",
        "value",
        "One-year NII sensitivity",
        artifact_dir / "nii_sensitivity_by_scenario.svg",
        suffix="m",
        reference=0.0,
    )
    cumulative_gap_chart(gaps, artifact_dir / "cumulative_cashflow_gap.svg")
    return manifest


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=project_root / "data" / "processed" / "liquidity_stress.db",
    )
    parser.add_argument("--output-dir", type=Path, default=project_root / "outputs")
    parser.add_argument("--artifact-dir", type=Path, default=project_root / "artifacts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = run_pipeline(args.database, args.output_dir, args.artifact_dir)
    print(f"Analysis complete: {manifest}")


if __name__ == "__main__":
    main()
