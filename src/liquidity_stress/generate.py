"""Generate a deterministic, fully synthetic treasury balance-sheet dataset."""

from __future__ import annotations

import argparse
import csv
import json
import random
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any


AS_OF_DATE = "2026-06-30"
DEFAULT_SEED = 20260902


ASSET_TEMPLATES: list[dict[str, Any]] = [
    {
        "product": "Cash & central-bank reserves",
        "desk": "Treasury",
        "counterparty_segment": "Central bank",
        "weight": 0.04,
        "amount": (3_000_000, 18_000_000),
        "maturity": (1, 7),
        "rate": (0.018, 0.030),
        "hqla": [("Level 1", 1.0)],
        "encumbrance_probability": 0.0,
        "inflow_weight": 0.0,
        "rate_type": "Variable",
    },
    {
        "product": "Sovereign bonds",
        "desk": "Liquid Asset Buffer",
        "counterparty_segment": "Sovereign",
        "weight": 0.08,
        "amount": (2_000_000, 14_000_000),
        "maturity": (30, 1_825),
        "rate": (0.018, 0.042),
        "hqla": [("Level 1", 0.85), ("Level 2A", 0.15)],
        "encumbrance_probability": 0.12,
        "inflow_weight": 0.0,
        "rate_type": "Fixed",
    },
    {
        "product": "Covered bonds",
        "desk": "Liquid Asset Buffer",
        "counterparty_segment": "Financial institution",
        "weight": 0.04,
        "amount": (1_000_000, 9_000_000),
        "maturity": (60, 1_460),
        "rate": (0.024, 0.048),
        "hqla": [("Level 2A", 0.8), ("Level 2B", 0.2)],
        "encumbrance_probability": 0.18,
        "inflow_weight": 0.0,
        "rate_type": "Fixed",
    },
    {
        "product": "Interbank placements",
        "desk": "Treasury",
        "counterparty_segment": "Financial institution",
        "weight": 0.08,
        "amount": (1_000_000, 14_000_000),
        "maturity": (1, 180),
        "rate": (0.028, 0.052),
        "hqla": [("None", 1.0)],
        "encumbrance_probability": 0.0,
        "inflow_weight": 0.8,
        "rate_type": "Variable",
    },
    {
        "product": "Retail mortgages",
        "desk": "Retail Banking",
        "counterparty_segment": "Retail",
        "weight": 0.23,
        "amount": (90_000, 850_000),
        "maturity": (365, 9_000),
        "rate": (0.022, 0.061),
        "hqla": [("None", 1.0)],
        "encumbrance_probability": 0.0,
        "inflow_weight": 0.5,
        "rate_type": "Mixed",
    },
    {
        "product": "SME loans",
        "desk": "Commercial Banking",
        "counterparty_segment": "SME",
        "weight": 0.23,
        "amount": (500_000, 10_000_000),
        "maturity": (90, 2_190),
        "rate": (0.032, 0.075),
        "hqla": [("None", 1.0)],
        "encumbrance_probability": 0.0,
        "inflow_weight": 0.5,
        "rate_type": "Mixed",
    },
    {
        "product": "Corporate loans",
        "desk": "Corporate Banking",
        "counterparty_segment": "Corporate",
        "weight": 0.30,
        "amount": (2_000_000, 28_000_000),
        "maturity": (30, 1_825),
        "rate": (0.030, 0.069),
        "hqla": [("None", 1.0)],
        "encumbrance_probability": 0.0,
        "inflow_weight": 0.5,
        "rate_type": "Variable",
    },
]


LIABILITY_TEMPLATES: list[dict[str, Any]] = [
    {
        "product": "Retail current deposits",
        "desk": "Retail Banking",
        "counterparty_segment": "Retail",
        "weight": 0.30,
        "amount": (30_000, 1_200_000),
        "maturity": (1, 1),
        "rate": (0.001, 0.021),
        "runoff_weight": 0.05,
        "treatment": "Non-maturity",
        "rate_type": "Variable",
    },
    {
        "product": "Retail term deposits",
        "desk": "Retail Banking",
        "counterparty_segment": "Retail",
        "weight": 0.17,
        "amount": (50_000, 1_800_000),
        "maturity": (7, 720),
        "rate": (0.012, 0.035),
        "runoff_weight": 1.0,
        "treatment": "Contractual",
        "rate_type": "Fixed",
    },
    {
        "product": "SME operational deposits",
        "desk": "Commercial Banking",
        "counterparty_segment": "SME",
        "weight": 0.13,
        "amount": (100_000, 6_000_000),
        "maturity": (1, 1),
        "rate": (0.002, 0.025),
        "runoff_weight": 0.10,
        "treatment": "Non-maturity",
        "rate_type": "Variable",
    },
    {
        "product": "Corporate deposits",
        "desk": "Corporate Banking",
        "counterparty_segment": "Corporate",
        "weight": 0.14,
        "amount": (500_000, 18_000_000),
        "maturity": (1, 1),
        "rate": (0.005, 0.030),
        "runoff_weight": 0.25,
        "treatment": "Non-maturity",
        "rate_type": "Variable",
    },
    {
        "product": "Wholesale funding",
        "desk": "Treasury",
        "counterparty_segment": "Wholesale",
        "weight": 0.13,
        "amount": (4_000_000, 45_000_000),
        "maturity": (7, 1_095),
        "rate": (0.022, 0.052),
        "runoff_weight": 1.0,
        "treatment": "Contractual",
        "rate_type": "Fixed",
    },
    {
        "product": "Covered bond funding",
        "desk": "Treasury",
        "counterparty_segment": "Wholesale",
        "weight": 0.08,
        "amount": (10_000_000, 70_000_000),
        "maturity": (90, 1_825),
        "rate": (0.020, 0.047),
        "runoff_weight": 1.0,
        "treatment": "Contractual",
        "rate_type": "Fixed",
    },
    {
        "product": "Interbank borrowing",
        "desk": "Treasury",
        "counterparty_segment": "Financial institution",
        "weight": 0.05,
        "amount": (2_000_000, 25_000_000),
        "maturity": (1, 180),
        "rate": (0.026, 0.056),
        "runoff_weight": 1.0,
        "treatment": "Contractual",
        "rate_type": "Variable",
    },
]


def _weighted_choice(rng: random.Random, templates: list[dict[str, Any]]) -> dict[str, Any]:
    return rng.choices(templates, weights=[item["weight"] for item in templates], k=1)[0]


def _hqla_choice(rng: random.Random, options: list[tuple[str, float]]) -> str:
    return rng.choices([item[0] for item in options], weights=[item[1] for item in options], k=1)[0]


def _currency(rng: random.Random) -> str:
    return rng.choices(["EUR", "USD", "GBP", "CHF"], weights=[0.79, 0.11, 0.06, 0.04], k=1)[0]


def _position(
    rng: random.Random,
    index: int,
    side: str,
    template: dict[str, Any],
) -> dict[str, Any]:
    amount = round(rng.uniform(*template["amount"]), 2)
    maturity_days = rng.randint(*template["maturity"])
    rate_type = template["rate_type"]
    if rate_type == "Mixed":
        rate_type = rng.choices(["Fixed", "Variable"], weights=[0.55, 0.45], k=1)[0]
    if rate_type == "Variable":
        repricing_days = rng.choice([1, 30, 90, 180, 365])
    else:
        repricing_days = maturity_days

    if side == "Asset":
        hqla_level = _hqla_choice(rng, template["hqla"])
        encumbered = int(rng.random() < template["encumbrance_probability"])
        runoff_weight = 0.0
        inflow_weight = template["inflow_weight"]
        treatment = "Liquidity buffer" if hqla_level != "None" else "Contractual"
    else:
        hqla_level = "None"
        encumbered = 0
        runoff_weight = template["runoff_weight"]
        inflow_weight = 0.0
        treatment = template["treatment"]

    return {
        "position_id": f"POS-{index:05d}",
        "as_of_date": AS_OF_DATE,
        "side": side,
        "desk": template["desk"],
        "product": template["product"],
        "counterparty_segment": template["counterparty_segment"],
        "currency": _currency(rng),
        "principal_eur": amount,
        "contractual_rate_pct": round(rng.uniform(*template["rate"]) * 100, 4),
        "rate_type": rate_type,
        "repricing_days": repricing_days,
        "maturity_days": maturity_days,
        "liquidity_treatment": treatment,
        "hqla_level": hqla_level,
        "encumbered": encumbered,
        "runoff_weight_pct": round(runoff_weight * 100, 2),
        "inflow_weight_pct": round(inflow_weight * 100, 2),
    }


def generate_positions(seed: int = DEFAULT_SEED, count: int = 900) -> list[dict[str, Any]]:
    """Return deterministic synthetic positions with a 54/46 asset-liability split."""
    if count < 20:
        raise ValueError("count must be at least 20")
    rng = random.Random(seed)
    asset_count = round(count * 0.54)
    rows: list[dict[str, Any]] = []
    for index in range(1, count + 1):
        side = "Asset" if index <= asset_count else "Liability"
        templates = ASSET_TEMPLATES if side == "Asset" else LIABILITY_TEMPLATES
        rows.append(_position(rng, index, side, _weighted_choice(rng, templates)))
    return rows


def generate_market_rates(seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    """Create 24 monthly observations for three illustrative EUR reference rates."""
    rng = random.Random(seed + 17)
    rows: list[dict[str, Any]] = []
    series = {
        "ECB deposit facility": 3.75,
        "EURIBOR 3M": 3.95,
        "EUR swap 2Y": 3.45,
    }
    year, month = 2024, 7
    levels = dict(series)
    for sequence in range(24):
        month_end = date(year, month, monthrange(year, month)[1]).isoformat()
        policy_drift = -0.075 if sequence >= 4 else 0.015
        for rate_name in series:
            noise = rng.uniform(-0.055, 0.055)
            levels[rate_name] = max(0.2, levels[rate_name] + policy_drift + noise)
            rows.append(
                {
                    "rate_date": month_end,
                    "rate_name": rate_name,
                    "rate_pct": round(levels[rate_name], 4),
                }
            )
        month += 1
        if month == 13:
            month = 1
            year += 1
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate_dataset(output_dir: Path, scenario_path: Path, seed: int, count: int) -> None:
    positions = generate_positions(seed=seed, count=count)
    rates = generate_market_rates(seed=seed)
    scenarios = json.loads(scenario_path.read_text(encoding="utf-8"))
    _write_csv(output_dir / "positions.csv", positions)
    _write_csv(output_dir / "market_rates.csv", rates)
    _write_csv(output_dir / "scenarios.csv", scenarios)
    metadata = {
        "dataset_type": "synthetic",
        "seed": seed,
        "as_of_date": AS_OF_DATE,
        "position_count": len(positions),
        "rate_observation_count": len(rates),
        "scenario_count": len(scenarios),
        "contains_real_customer_data": False,
    }
    (output_dir / "generation_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=project_root / "data" / "raw")
    parser.add_argument(
        "--scenario-path", type=Path, default=project_root / "config" / "scenarios.json"
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--positions", type=int, default=900)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_dataset(args.output_dir, args.scenario_path, args.seed, args.positions)
    print(f"Generated {args.positions} synthetic positions in {args.output_dir}")


if __name__ == "__main__":
    main()
