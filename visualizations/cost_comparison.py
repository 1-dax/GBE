#!/usr/bin/env python3
"""
Unit production cost comparison — football shirt by geography.

Grouped bar chart: unit cost per geography plus the cost gap vs. the Asia benchmark.
Pulls figures from data/benchmarks.json so every tool shares one source of truth.

Usage:
    python visualizations/cost_comparison.py
    python visualizations/cost_comparison.py --show
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

# --- Shared project palette ------------------------------------------------- #
COLORS = {
    "argentina": "#C0392B",  # problem (red)
    "paraguay": "#27AE60",   # target (green)
    "asia": "#7F8C8D",       # competitor benchmark (gray)
    "other": "#2980B9",      # neutral (blue)
    "gap": "#E67E22",        # cost gap vs. Asia (orange)
}

DATA_PATH = Path(__file__).parent.parent / "data" / "benchmarks.json"
EXPORT_DIR = Path(__file__).parent.parent / "exports"


def load_costs() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)["unit_costs"]["football_shirt"]


def build_chart(show: bool) -> None:
    import matplotlib.pyplot as plt  # imported after the backend is chosen
    import numpy as np

    costs = load_costs()

    # Order: problem -> target -> benchmark -> alternative
    labels = ["Argentina\n(current base)", "Paraguay\n(Maquila target)",
              "Asia benchmark\n(China/Vietnam)", "CAFTA-DR\n(Honduras/El Salvador)"]
    keys = ["argentina", "paraguay", "asia", "cafta_dr"]
    values = [costs[k] for k in keys]
    bar_colors = [COLORS["argentina"], COLORS["paraguay"], COLORS["asia"], COLORS["other"]]

    asia_price = costs["asia"]
    gaps = [round(v - asia_price, 2) for v in values]  # cost gap vs. Asia benchmark

    x = np.arange(len(labels))
    width = 0.38

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#444444"})
    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Series 1: unit cost (colored per geography)
    bars_cost = ax.bar(x - width / 2, values, width, color=bar_colors,
                       edgecolor="white", linewidth=0.6, label="Unit cost (USD)", zorder=3)
    # Series 2: cost gap vs. Asia benchmark
    bars_gap = ax.bar(x + width / 2, gaps, width, color=COLORS["gap"], alpha=0.85,
                      edgecolor="white", linewidth=0.6,
                      label="Cost gap vs. Asia benchmark", zorder=3)

    # Asia benchmark reference line
    ax.axhline(asia_price, linestyle="--", color=COLORS["asia"], linewidth=1.4, zorder=2)
    ax.text(len(labels) - 0.5, asia_price + 0.25, f"Asia benchmark  ${asia_price:.2f}",
            ha="right", va="bottom", color=COLORS["asia"], fontsize=9, fontstyle="italic")

    # Value labels
    for rect, val in zip(bars_cost, values):
        ax.annotate(f"${val:.2f}", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    textcoords="offset points", xytext=(0, 4), ha="center", va="bottom",
                    fontsize=10, fontweight="bold")
    for rect, val in zip(bars_gap, gaps):
        label = "—" if val == 0 else f"+${val:.2f}"
        ax.annotate(label, (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    textcoords="offset points", xytext=(0, 4), ha="center", va="bottom",
                    fontsize=9, color=COLORS["gap"])

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("USD per unit", fontsize=11)
    ax.set_ylim(0, max(values) * 1.18)

    # Titles
    ax.set_title("Unit Production Cost — Football Shirt by Geography",
                 fontsize=15, fontweight="bold", pad=26, loc="left")
    ax.text(0, 1.045, "Source: R&A Indumentaria client data; industry benchmarks. June 2026.",
            transform=ax.transAxes, fontsize=9.5, color="#666666")

    # Minimal, deck-ready styling
    ax.legend(frameon=False, fontsize=9.5, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, color="#E5E5E5", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    png = EXPORT_DIR / "cost_comparison.png"
    pdf = EXPORT_DIR / "cost_comparison.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")

    if show:
        plt.show()
    plt.close(fig)

    print("Exported to exports/cost_comparison.png and .pdf")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unit production cost comparison chart.")
    parser.add_argument("--show", action="store_true", help="Display interactively before saving.")
    args = parser.parse_args()

    # Choose the backend before pyplot is first imported (inside build_chart).
    if not args.show:
        matplotlib.use("Agg")
    build_chart(show=args.show)


if __name__ == "__main__":
    main()
