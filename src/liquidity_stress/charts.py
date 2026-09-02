"""Dependency-free SVG charts for version-controlled analytical artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path
from typing import Any


COLORS = ["#38bdf8", "#22c55e", "#f59e0b", "#a78bfa", "#f43f5e"]


def _svg_start(title: str, width: int = 960, height: int = 540) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text{font-family:Inter,Arial,sans-serif;fill:#dbeafe}.axis{stroke:#64748b;stroke-width:1}.grid{stroke:#334155;stroke-width:1}.small{font-size:12px}.label{font-size:14px}.title{font-size:24px;font-weight:700}.subtitle{font-size:13px;fill:#94a3b8}</style>",
        f'<rect width="{width}" height="{height}" fill="#0f172a" rx="16"/>',
        f'<text x="52" y="44" class="title">{escape(title)}</text>',
        '<text x="52" y="67" class="subtitle">Synthetic portfolio · educational analytics · EUR</text>',
    ]


def _finish(lines: list[str], path: Path) -> None:
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def bar_chart(
    rows: Sequence[dict[str, Any]],
    label_field: str,
    value_field: str,
    title: str,
    path: Path,
    suffix: str = "",
    reference: float | None = None,
) -> None:
    lines = _svg_start(title)
    x0, y0, chart_w, chart_h = 90, 100, 820, 350
    values = [float(row[value_field]) for row in rows]
    min_value = min(0.0, min(values))
    max_value = max(0.0, max(values), reference or 0.0)
    span = max(max_value - min_value, 1.0)
    zero_y = y0 + chart_h * max_value / span
    for tick in range(6):
        value = min_value + span * tick / 5
        y = y0 + chart_h - chart_h * (value - min_value) / span
        lines.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+chart_w}" y2="{y:.1f}" class="grid"/>')
        lines.append(f'<text x="{x0-10}" y="{y+4:.1f}" text-anchor="end" class="small">{value:,.0f}{escape(suffix)}</text>')
    if reference is not None:
        ref_y = y0 + chart_h - chart_h * (reference - min_value) / span
        lines.append(f'<line x1="{x0}" y1="{ref_y:.1f}" x2="{x0+chart_w}" y2="{ref_y:.1f}" stroke="#f8fafc" stroke-dasharray="6 6"/>')
        lines.append(f'<text x="{x0+chart_w}" y="{ref_y-7:.1f}" text-anchor="end" class="small">reference {reference:g}{escape(suffix)}</text>')
    band = chart_w / max(len(rows), 1)
    for index, row in enumerate(rows):
        value = float(row[value_field])
        value_y = y0 + chart_h - chart_h * (value - min_value) / span
        top = min(value_y, zero_y)
        height = max(abs(value_y - zero_y), 1.0)
        x = x0 + band * index + band * 0.16
        width = band * 0.68
        color = COLORS[index % len(COLORS)]
        lines.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{width:.1f}" height="{height:.1f}" rx="5" fill="{color}"/>')
        lines.append(f'<text x="{x+width/2:.1f}" y="{min(top-8, zero_y-8):.1f}" text-anchor="middle" class="small">{value:,.1f}{escape(suffix)}</text>')
        label = str(row[label_field]).replace(" ", "\n", 1)
        first, *rest = label.split("\n", 1)
        lines.append(f'<text x="{x+width/2:.1f}" y="{y0+chart_h+25}" text-anchor="middle" class="small">{escape(first)}</text>')
        if rest:
            lines.append(f'<text x="{x+width/2:.1f}" y="{y0+chart_h+40}" text-anchor="middle" class="small">{escape(rest[0])}</text>')
    lines.append(f'<line x1="{x0}" y1="{zero_y:.1f}" x2="{x0+chart_w}" y2="{zero_y:.1f}" class="axis"/>')
    lines.append('<text x="52" y="510" class="subtitle">Figures are portfolio-model outputs, not regulatory disclosures.</text>')
    _finish(lines, path)


def cumulative_gap_chart(rows: Sequence[dict[str, Any]], path: Path) -> None:
    lines = _svg_start("Post-buffer cumulative cash-flow gap")
    x0, y0, chart_w, chart_h = 90, 100, 820, 350
    scenarios: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        scenarios.setdefault(str(row["scenario_id"]), []).append(row)
    all_values = [float(row["post_buffer_cumulative_gap_eur"]) / 1_000_000 for row in rows]
    min_value, max_value = min(0.0, min(all_values)), max(0.0, max(all_values))
    span = max(max_value - min_value, 1.0)
    for tick in range(6):
        value = min_value + span * tick / 5
        y = y0 + chart_h - chart_h * (value - min_value) / span
        lines.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+chart_w}" y2="{y:.1f}" class="grid"/>')
        lines.append(f'<text x="{x0-10}" y="{y+4:.1f}" text-anchor="end" class="small">€{value:,.0f}m</text>')
    zero_y = y0 + chart_h - chart_h * (0 - min_value) / span
    lines.append(f'<line x1="{x0}" y1="{zero_y:.1f}" x2="{x0+chart_w}" y2="{zero_y:.1f}" stroke="#f8fafc" stroke-dasharray="5 5"/>')
    labels: list[str] = []
    for scenario_index, (scenario_id, scenario_rows) in enumerate(scenarios.items()):
        ordered = sorted(scenario_rows, key=lambda item: int(item["bucket_order"]))
        labels = [str(item["time_bucket"]) for item in ordered]
        points = []
        for index, row in enumerate(ordered):
            x = x0 + chart_w * index / max(len(ordered) - 1, 1)
            value = float(row["post_buffer_cumulative_gap_eur"]) / 1_000_000
            y = y0 + chart_h - chart_h * (value - min_value) / span
            points.append(f"{x:.1f},{y:.1f}")
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{COLORS[scenario_index % len(COLORS)]}"/>')
        lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{COLORS[scenario_index % len(COLORS)]}" stroke-width="3"/>')
        legend_x = 130 + scenario_index * 155
        lines.append(f'<rect x="{legend_x}" y="82" width="12" height="4" fill="{COLORS[scenario_index % len(COLORS)]}"/>')
        lines.append(f'<text x="{legend_x+18}" y="87" class="small">{escape(scenario_id)}</text>')
    for index, label in enumerate(labels):
        x = x0 + chart_w * index / max(len(labels) - 1, 1)
        lines.append(f'<text x="{x:.1f}" y="{y0+chart_h+25}" text-anchor="middle" class="small">{escape(label.replace(" days", "d"))}</text>')
    lines.append('<text x="52" y="510" class="subtitle">Cumulative stressed gap plus scenario-adjusted eligible liquidity buffer.</text>')
    _finish(lines, path)
