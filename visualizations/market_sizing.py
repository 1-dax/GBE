#!/usr/bin/env python3
"""
Brazil market sizing — TAM down to R&A's realistic SOM.

Top panel: a narrowing funnel (TAM -> SAM -> addressable import pool).
Bottom panel: the three Year-1 SOM scenarios on their own scale so the small
figures stay legible. TAM is pulled from data/benchmarks.json; the rest are
team estimates defined here.

Usage:
    python visualizations/market_sizing.py
    python visualizations/market_sizing.py --show
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

# --- Shared project palette ------------------------------------------------- #
COLORS = {
    "tam": "#2980B9",        # neutral blue
    "sam": "#2471A3",        # slightly deeper blue
    "addressable": "#1F618D",
    "som_opt": "#27AE60",    # green
    "som_base": "#E67E22",   # amber/orange
    "som_down": "#C0392B",   # red
    "text": "#2C3E50",
}

DATA_PATH = Path(__file__).parent.parent / "data" / "benchmarks.json"
EXPORT_DIR = Path(__file__).parent.parent / "exports"


def load_tam() -> float:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)["brazil_market"]["tam_sports_apparel_2025_usd_m"]


def build_chart(show: bool) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    tam = load_tam()

    # Funnel tiers (top panel): label, value ($M), filter description, color
    funnel = [
        ("TAM", tam, "Total Brazil sports apparel market (IMARC 2025)", COLORS["tam"]),
        ("SAM", 2900, "Segments R&A can manufacture\n(cotton activewear + football shirts + partial technical)", COLORS["sam"]),
        ("Addressable\nimport pool", 870, "SAM portion currently imported (not domestically produced)", COLORS["addressable"]),
    ]

    # SOM scenarios (bottom panel): label, value ($M), description, color
    som = [
        ("Optimistic", 22, "Year 1 · 2–3 Brazilian brands secured", COLORS["som_opt"]),
        ("Base", 12, "Year 1 · Lupo only", COLORS["som_base"]),
        ("Downside", 4, "Year 1 · Brazil validation fails", COLORS["som_down"]),
    ]

    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig = plt.figure(figsize=(11.5, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1.5], hspace=0.35)
    ax_top = fig.add_subplot(gs[0])
    ax_bot = fig.add_subplot(gs[1])

    # ---- Top: funnel as centered horizontal bars -------------------------- #
    max_val = funnel[0][1]
    n = len(funnel)
    for i, (label, value, filt, color) in enumerate(funnel):
        y = n - 1 - i  # top tier highest
        half = (value / max_val) / 2  # half-width in axis units (0..0.5)
        ax_top.barh(y, width=2 * half, left=0.5 - half, height=0.62,
                    color=color, edgecolor="white", linewidth=1.2, zorder=3)
        # Tier label + value inside/over the bar
        ax_top.text(0.5, y + 0.05, f"{label}", ha="center", va="center",
                    color="white", fontsize=12, fontweight="bold", zorder=4)
        ax_top.text(0.5, y - 0.16, f"${value:,.0f}M", ha="center", va="center",
                    color="white", fontsize=11, zorder=4)
        # Filter description to the right
        ax_top.text(1.02, y, filt, ha="left", va="center", fontsize=9.5,
                    color=COLORS["text"])

    ax_top.set_xlim(0, 1.0)
    ax_top.set_ylim(-0.6, n - 0.4)
    ax_top.axis("off")
    ax_top.set_title("Brazil Market Sizing — R&A Addressable Opportunity",
                     fontsize=15, fontweight="bold", loc="left", pad=28)
    ax_top.text(0, 1.06,
                "Source: IMARC Group; Euromonitor; Comex do Brasil; team estimates. June 2026.",
                transform=ax_top.transAxes, fontsize=9.5, color="#666666")

    # Connect the funnel to the SOM panel
    ax_top.annotate("", xy=(0.5, -0.5), xytext=(0.5, 0.0),
                    arrowprops=dict(arrowstyle="-|>", color="#999999", lw=1.4))

    # ---- Bottom: SOM scenarios on their own scale ------------------------- #
    labels = [f"{name}\n${val}M" for name, val, _, _ in som]
    values = [val for _, val, _, _ in som]
    colors = [c for *_, c in som]
    xpos = np.arange(len(som))

    bars = ax_bot.bar(xpos, values, width=0.6, color=colors,
                      edgecolor="white", linewidth=1.0, zorder=3)
    for rect, (_, val, desc, _) in zip(bars, som):
        ax_bot.annotate(f"${val}M", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        textcoords="offset points", xytext=(0, 4), ha="center",
                        va="bottom", fontsize=11, fontweight="bold")
        ax_bot.annotate(desc, (rect.get_x() + rect.get_width() / 2, 0),
                        textcoords="offset points", xytext=(0, -28), ha="center",
                        va="top", fontsize=8.5, color=COLORS["text"])

    ax_bot.set_xticks(xpos)
    ax_bot.set_xticklabels([name for name, *_ in som], fontsize=10, fontweight="bold")
    ax_bot.set_ylim(0, max(values) * 1.25)
    ax_bot.set_ylabel("SOM ($M, Year 1)", fontsize=10)
    ax_bot.set_title("SOM — Year 1 realistic capture (separate scale)",
                     fontsize=11, loc="left", color=COLORS["text"], pad=8)
    ax_bot.spines[["top", "right"]].set_visible(False)
    ax_bot.yaxis.grid(True, color="#E5E5E5", linewidth=0.8, zorder=0)
    ax_bot.set_axisbelow(True)
    ax_bot.tick_params(axis="x", length=0)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    png = EXPORT_DIR / "market_sizing.png"
    pdf = EXPORT_DIR / "market_sizing.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")

    if show:
        plt.show()
    plt.close(fig)

    print("Exported to exports/market_sizing.png and .pdf")


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazil market sizing funnel chart.")
    parser.add_argument("--show", action="store_true", help="Display interactively before saving.")
    args = parser.parse_args()

    if not args.show:
        matplotlib.use("Agg")
    build_chart(show=args.show)


if __name__ == "__main__":
    main()
