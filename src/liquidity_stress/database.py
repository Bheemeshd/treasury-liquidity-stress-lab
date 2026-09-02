"""Load generated CSV inputs into a constrained SQLite analytical store."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Iterable


POSITION_FIELDS = [
    "position_id",
    "as_of_date",
    "side",
    "desk",
    "product",
    "counterparty_segment",
    "currency",
    "principal_eur",
    "contractual_rate_pct",
    "rate_type",
    "repricing_days",
    "maturity_days",
    "liquidity_treatment",
    "hqla_level",
    "encumbered",
    "runoff_weight_pct",
    "inflow_weight_pct",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _assert_columns(rows: list[dict[str, str]], required: Iterable[str], name: str) -> None:
    if not rows:
        raise ValueError(f"{name} is empty")
    missing = set(required) - set(rows[0])
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def build_database(input_dir: Path, database_path: Path, schema_path: Path) -> dict[str, int]:
    """Create or replace the database contents and return loaded row counts."""
    positions = _read_csv(input_dir / "positions.csv")
    rates = _read_csv(input_dir / "market_rates.csv")
    scenarios = _read_csv(input_dir / "scenarios.csv")
    _assert_columns(positions, POSITION_FIELDS, "positions.csv")
    _assert_columns(rates, ["rate_date", "rate_name", "rate_pct"], "market_rates.csv")
    _assert_columns(
        scenarios,
        [
            "scenario_id",
            "scenario_name",
            "severity_rank",
            "retail_runoff_multiplier",
            "wholesale_runoff_multiplier",
            "asset_inflow_multiplier",
            "hqla_haircut_addon",
            "rate_shock_bps",
            "asset_beta",
            "deposit_beta",
            "description",
        ],
        "scenarios.csv",
    )

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        with connection:
            connection.execute("DELETE FROM cashflow_gap")
            connection.execute("DELETE FROM scenario_summary")
            connection.execute("DELETE FROM positions")
            connection.execute("DELETE FROM market_rates")
            connection.execute("DELETE FROM scenarios")
            connection.executemany(
                f"INSERT INTO positions ({', '.join(POSITION_FIELDS)}) "
                f"VALUES ({', '.join('?' for _ in POSITION_FIELDS)})",
                [[row[field] for field in POSITION_FIELDS] for row in positions],
            )
            rate_fields = ["rate_date", "rate_name", "rate_pct"]
            connection.executemany(
                "INSERT INTO market_rates (rate_date, rate_name, rate_pct) VALUES (?, ?, ?)",
                [[row[field] for field in rate_fields] for row in rates],
            )
            scenario_fields = list(scenarios[0])
            connection.executemany(
                f"INSERT INTO scenarios ({', '.join(scenario_fields)}) "
                f"VALUES ({', '.join('?' for _ in scenario_fields)})",
                [[row[field] for field in scenario_fields] for row in scenarios],
            )
        connection.execute("PRAGMA optimize")
    finally:
        connection.close()
    return {"positions": len(positions), "market_rates": len(rates), "scenarios": len(scenarios)}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=project_root / "data" / "raw")
    parser.add_argument(
        "--database",
        type=Path,
        default=project_root / "data" / "processed" / "liquidity_stress.db",
    )
    parser.add_argument(
        "--schema", type=Path, default=project_root / "sql" / "01_schema.sql"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = build_database(args.input_dir, args.database, args.schema)
    print(f"Loaded SQLite database at {args.database}: {counts}")


if __name__ == "__main__":
    main()
