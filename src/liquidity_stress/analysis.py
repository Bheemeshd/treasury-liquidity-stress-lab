"""Transparent liquidity-gap, LCR-style proxy, and NII sensitivity calculations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


HQLA_FACTORS = {"Level 1": 1.00, "Level 2A": 0.85, "Level 2B": 0.50, "None": 0.0}
BUCKETS = [
    (1, "0-7 days", 0, 7),
    (2, "8-30 days", 8, 30),
    (3, "31-90 days", 31, 90),
    (4, "91-180 days", 91, 180),
    (5, "181-365 days", 181, 365),
    (6, ">365 days", 366, 1_000_000),
]


def _number(row: Mapping[str, Any], field: str) -> float:
    return float(row[field])


def _runoff_multiplier(position: Mapping[str, Any], scenario: Mapping[str, Any]) -> float:
    if position["counterparty_segment"] == "Retail":
        return _number(scenario, "retail_runoff_multiplier")
    return _number(scenario, "wholesale_runoff_multiplier")


def position_hqla(position: Mapping[str, Any], scenario: Mapping[str, Any]) -> float:
    if (
        position["side"] != "Asset"
        or int(position["encumbered"]) == 1
        or position["hqla_level"] == "None"
    ):
        return 0.0
    base_factor = HQLA_FACTORS[str(position["hqla_level"])]
    adjusted_factor = max(0.0, base_factor - _number(scenario, "hqla_haircut_addon"))
    return _number(position, "principal_eur") * adjusted_factor


def position_30d_outflow(position: Mapping[str, Any], scenario: Mapping[str, Any]) -> float:
    if position["side"] != "Liability":
        return 0.0
    if position["liquidity_treatment"] != "Non-maturity" and int(position["maturity_days"]) > 30:
        return 0.0
    principal = _number(position, "principal_eur")
    stressed_weight = (
        _number(position, "runoff_weight_pct") / 100.0
        * _runoff_multiplier(position, scenario)
    )
    return principal * min(1.0, stressed_weight)


def position_30d_inflow(position: Mapping[str, Any], scenario: Mapping[str, Any]) -> float:
    if (
        position["side"] != "Asset"
        or position["hqla_level"] != "None"
        or int(position["maturity_days"]) > 30
    ):
        return 0.0
    return (
        _number(position, "principal_eur")
        * _number(position, "inflow_weight_pct")
        / 100.0
        * _number(scenario, "asset_inflow_multiplier")
    )


def calculate_nii_sensitivity(
    positions: Sequence[Mapping[str, Any]], scenario: Mapping[str, Any]
) -> dict[str, float]:
    """Estimate one-year NII impact using repricing timing and scenario pass-through betas."""
    base_nii = 0.0
    delta_nii = 0.0
    shock = _number(scenario, "rate_shock_bps") / 10_000.0
    for position in positions:
        principal = _number(position, "principal_eur")
        rate = _number(position, "contractual_rate_pct") / 100.0
        sign = 1.0 if position["side"] == "Asset" else -1.0
        base_nii += sign * principal * rate
        repricing_days = int(position["repricing_days"])
        exposure_fraction = max(0.0, (365.0 - repricing_days) / 365.0)
        beta_field = "asset_beta" if position["side"] == "Asset" else "deposit_beta"
        delta_nii += sign * principal * shock * _number(scenario, beta_field) * exposure_fraction
    return {
        "base_annual_nii_eur": base_nii,
        "delta_nii_eur": delta_nii,
        "projected_annual_nii_eur": base_nii + delta_nii,
    }


def calculate_lcr_proxy(
    positions: Sequence[Mapping[str, Any]], scenario: Mapping[str, Any]
) -> dict[str, float]:
    """Calculate a simplified 30-day liquidity coverage proxy.

    This intentionally mirrors the high-level structure of LCR but is not a regulatory
    calculation: the synthetic data and simplified assumptions omit many rule nuances.
    """
    hqla = sum(position_hqla(item, scenario) for item in positions)
    outflows = sum(position_30d_outflow(item, scenario) for item in positions)
    raw_inflows = sum(position_30d_inflow(item, scenario) for item in positions)
    capped_inflows = min(raw_inflows, outflows * 0.75)
    net_outflows = max(outflows - capped_inflows, 1.0)
    ratio = 100.0 * hqla / net_outflows
    return {
        "hqla_eur": hqla,
        "gross_30d_outflows_eur": outflows,
        "raw_30d_inflows_eur": raw_inflows,
        "capped_30d_inflows_eur": capped_inflows,
        "net_30d_outflows_eur": net_outflows,
        "lcr_proxy_pct": ratio,
        "liquidity_surplus_eur": hqla - net_outflows,
        "survival_days_proxy": min(365.0, 30.0 * hqla / net_outflows),
    }


def _bucket_for(maturity_days: int) -> tuple[int, str]:
    for order, label, lower, upper in BUCKETS:
        if lower <= maturity_days <= upper:
            return order, label
    raise ValueError(f"maturity_days outside supported range: {maturity_days}")


def calculate_cashflow_gaps(
    positions: Sequence[Mapping[str, Any]], scenario: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Aggregate stressed principal cash flows into standard treasury time buckets."""
    buckets: dict[int, dict[str, float]] = {
        order: {"inflows": 0.0, "outflows": 0.0} for order, _, _, _ in BUCKETS
    }
    for position in positions:
        maturity_days = int(position["maturity_days"])
        order, _ = _bucket_for(maturity_days)
        principal = _number(position, "principal_eur")
        if position["side"] == "Asset":
            if position["hqla_level"] == "None":
                buckets[order]["inflows"] += (
                    principal
                    * _number(position, "inflow_weight_pct")
                    / 100.0
                    * _number(scenario, "asset_inflow_multiplier")
                )
        else:
            stressed_weight = min(
                1.0,
                _number(position, "runoff_weight_pct")
                / 100.0
                * _runoff_multiplier(position, scenario),
            )
            buckets[order]["outflows"] += principal * stressed_weight

    hqla = sum(position_hqla(item, scenario) for item in positions)
    cumulative_gap = 0.0
    rows: list[dict[str, Any]] = []
    for order, label, _, _ in BUCKETS:
        inflows = buckets[order]["inflows"]
        outflows = buckets[order]["outflows"]
        net_gap = inflows - outflows
        cumulative_gap += net_gap
        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "bucket_order": order,
                "time_bucket": label,
                "stressed_inflows_eur": inflows,
                "stressed_outflows_eur": outflows,
                "net_gap_eur": net_gap,
                "cumulative_gap_eur": cumulative_gap,
                "post_buffer_cumulative_gap_eur": cumulative_gap + hqla,
            }
        )
    return rows


def build_scenario_results(
    positions: Sequence[Mapping[str, Any]], scenarios: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for scenario in scenarios:
        summary: dict[str, Any] = {
            "scenario_id": scenario["scenario_id"],
            "scenario_name": scenario["scenario_name"],
        }
        summary.update(calculate_lcr_proxy(positions, scenario))
        summary.update(calculate_nii_sensitivity(positions, scenario))
        summaries.append(summary)
        gaps.extend(calculate_cashflow_gaps(positions, scenario))
    return summaries, gaps


def portfolio_composition(positions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: {"position_count": 0.0, "principal_eur": 0.0, "weighted_rate": 0.0}
    )
    side_totals: dict[str, float] = defaultdict(float)
    for position in positions:
        key = (str(position["side"]), str(position["product"]), str(position["currency"]))
        principal = _number(position, "principal_eur")
        totals[key]["position_count"] += 1
        totals[key]["principal_eur"] += principal
        totals[key]["weighted_rate"] += principal * _number(position, "contractual_rate_pct")
        side_totals[str(position["side"])] += principal

    rows: list[dict[str, Any]] = []
    for (side, product, currency), values in sorted(totals.items()):
        rows.append(
            {
                "side": side,
                "product": product,
                "currency": currency,
                "position_count": int(values["position_count"]),
                "principal_eur": values["principal_eur"],
                "side_share_pct": 100.0 * values["principal_eur"] / side_totals[side],
                "weighted_rate_pct": values["weighted_rate"] / values["principal_eur"],
            }
        )
    return rows
