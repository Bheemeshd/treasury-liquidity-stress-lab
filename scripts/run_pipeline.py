"""One-command orchestration for generation, ETL, analysis, and artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from liquidity_stress.database import build_database  # noqa: E402
from liquidity_stress.generate import DEFAULT_SEED, generate_dataset  # noqa: E402
from liquidity_stress.pipeline import run_pipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--positions", type=int, default=900)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = ROOT / "data" / "raw"
    database = ROOT / "data" / "processed" / "liquidity_stress.db"
    generate_dataset(raw_dir, ROOT / "config" / "scenarios.json", args.seed, args.positions)
    counts = build_database(raw_dir, database, ROOT / "sql" / "01_schema.sql")
    manifest = run_pipeline(database, ROOT / "outputs", ROOT / "artifacts")
    print(f"Pipeline complete. Loaded {counts}; analyzed {manifest}.")


if __name__ == "__main__":
    main()

