"""Gráficos SVG simples (sem Chart.js / D3)."""

from __future__ import annotations

from typing import Sequence


def svg_bar_chart(
    values: Sequence[float | int | None],
    *,
    width: int = 560,
    height: int = 140,
    color: str = "#0369a1",
    label: str = "",
) -> str:
    nums = [float(v or 0) for v in values]
    n = len(nums)
    if n == 0:
        return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{label}"></svg>'
    peak = max(nums) if max(nums) > 0 else 1.0
    pad_l, pad_r, pad_t, pad_b = 8, 8, 12, 22
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    gap = 2
    bar_w = max(2.0, (inner_w - gap * (n - 1)) / n)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="{_esc(label)}">'
        f'<rect width="{width}" height="{height}" fill="#f8fafc" rx="8"/>'
    ]
    for i, v in enumerate(nums):
        h = (v / peak) * inner_h if peak else 0
        x = pad_l + i * (bar_w + gap)
        y = pad_t + inner_h - h
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'fill="{color}" rx="2">'
            f"<title>{v:g}</title></rect>"
        )
    if label:
        parts.append(
            f'<text x="{pad_l}" y="{height - 6}" fill="#64748b" font-size="11" '
            f'font-family="system-ui,sans-serif">{_esc(label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def svg_line_chart(
    values: Sequence[float | int | None],
    *,
    width: int = 560,
    height: int = 140,
    color: str = "#0f766e",
    label: str = "",
) -> str:
    nums = [float(v) if v is not None else None for v in values]
    usable = [v for v in nums if v is not None]
    if not usable:
        return (
            f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(label)}">'
            f'<rect width="{width}" height="{height}" fill="#f8fafc" rx="8"/>'
            f'<text x="16" y="{height/2:.0f}" fill="#94a3b8" font-size="12">sem dados</text>'
            f"</svg>"
        )
    peak = max(usable) if max(usable) > 0 else 1.0
    pad_l, pad_r, pad_t, pad_b = 8, 8, 12, 22
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    n = len(nums)
    pts: list[str] = []
    for i, v in enumerate(nums):
        if v is None:
            continue
        x = pad_l + (inner_w * i / max(n - 1, 1))
        y = pad_t + inner_h - (v / peak) * inner_h
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="{_esc(label)}">'
        f'<rect width="{width}" height="{height}" fill="#f8fafc" rx="8"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.5" '
        f'points="{polyline}"/>'
        f'<text x="{pad_l}" y="{height - 6}" fill="#64748b" font-size="11" '
        f'font-family="system-ui,sans-serif">{_esc(label)}</text>'
        f"</svg>"
    )


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
