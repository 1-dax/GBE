#!/usr/bin/env python3
"""
Strategic group map — Americas contract sportswear manufacturing.

X axis: geographic proximity to US/Brazil end markets (far -> close).
Y axis: vertical integration / full-package capability (basic cut-and-sew -> full-package Tier-1).

Plots the competitive landscape, draws R&A's Argentina -> Paraguay strategic move,
highlights the Paraguay target state, and shades R&A's target competitive zone.

Usage:
    python visualizations/strategic_group_map.py
    python visualizations/strategic_group_map.py --show
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

EXPORT_DIR = Path(__file__).parent.parent / "exports"

# Named colors mapped to the shared project palette where they correspond.
PALETTE = {
    "red": "#C0392B",
    "green": "#27AE60",
    "gray": "#7F8C8D",
    "blue": "#2980B9",
    "orange": "#E67E22",
    "purple": "#8E44AD",
    "lightblue": "#5DADE2",
}

# name, x, y, color key, note, (label x, label y in DATA coords) — manual placement,
# tuned to avoid overlap; adjustText (if present) nudges from here, kept inside the axes.
POINTS = [
    ("R&A (Argentina — current)", 3, 8, "red", "current position", (2.6, 8.85)),
    ("R&A (Paraguay — target)", 6, 8, "green", "target position", (7.0, 8.55)),
    ("Supertex (Colombia)", 5, 7, "blue", "closest peer", (4.4, 6.35)),
    ("Asian Tier-1 (Eclat, Crystal)", 1, 9, "gray", "scale leaders", (1.6, 9.55)),
    ("CAFTA-DR (Hanesbrands, Gildan)", 7, 5, "orange", "US-access, basics-focused", (7.4, 4.5)),
    ("Brazilian own-brands (T&F, Alto Giro)", 8, 6, "purple", "potential customers", (7.9, 6.7)),
    ("Mexican manufacturers", 7, 6, "lightblue", "Section 301 risk", (5.7, 6.7)),
]

# R&A move endpoints
ARG = (3, 8)
PARAGUAY = (6, 8)


def build_chart(show: bool) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(figsize=(11.5, 8.5))

    # ---- Target competitive zone (shaded) --------------------------------- #
    zone = Rectangle((5, 7), width=3, height=2, facecolor=PALETTE["green"],
                     alpha=0.10, edgecolor=PALETTE["green"], linewidth=1.0,
                     linestyle="--", zorder=0)
    ax.add_patch(zone)
    ax.text(6.5, 8.92, "R&A's target competitive zone", ha="center", va="top",
            fontsize=9.5, fontstyle="italic", color="#1E8449", zorder=1)

    # ---- Points ----------------------------------------------------------- #
    texts = []
    xs, ys = [], []
    for name, x, y, ckey, note, (lx, ly) in POINTS:
        color = PALETTE[ckey]
        ax.scatter(x, y, s=190, color=color, edgecolor="white", linewidth=1.2, zorder=4)
        xs.append(x)
        ys.append(y)
        label = f"{name}\n({note})"
        # Texts live in DATA coords so adjustText can position them and draw clean
        # connectors; without adjustText these manual spots already avoid overlap.
        txt = ax.text(lx, ly, label, ha="center", va="center", fontsize=9,
                      color="#2C3E50", zorder=5, linespacing=1.2)
        texts.append(txt)

    # ---- Highlight the Paraguay target state ------------------------------ #
    ax.scatter(*PARAGUAY, s=950, facecolors="none", edgecolors=PALETTE["green"],
               linewidths=2.4, zorder=3)

    # ---- Strategic-move arrow (dotted) ------------------------------------ #
    ax.annotate("", xy=PARAGUAY, xytext=ARG,
                arrowprops=dict(arrowstyle="-|>", linestyle=":", color="#555555",
                                lw=2.0, shrinkA=10, shrinkB=18))
    mid_x = (ARG[0] + PARAGUAY[0]) / 2
    ax.text(mid_x, ARG[1] + 0.22, "strategic move", ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", color="#555555")

    # ---- Reduce label overlap (adjustText if available) ------------------- #
    try:
        from adjustText import adjust_text
        adjust_text(
            texts, x=xs, y=ys, ax=ax,
            ensure_inside_axes=True,   # never push labels off-canvas
            max_move=18,               # only nudge from the manual placement
            expand=(1.15, 1.3),
            force_text=(0.2, 0.3),
            force_pull=(0.02, 0.02),
            arrowprops=dict(arrowstyle="-", color="#C8C8C8", lw=0.6),
        )
    except Exception:
        pass  # manual placements above are the fallback

    # ---- Axes & framing --------------------------------------------------- #
    ax.set_xlim(0, 10)
    ax.set_ylim(3.5, 10)
    ax.set_xlabel("Geographic proximity to US/Brazil end markets   (far → close)", fontsize=11)
    ax.set_ylabel("Vertical integration / full-package capability   (basic → Tier-1)", fontsize=11)
    ax.set_xticks(range(0, 11, 2))
    ax.set_yticks(range(4, 11, 2))

    ax.set_title("Strategic Group Map — Americas Contract Sportswear Manufacturing",
                 fontsize=14.5, fontweight="bold", loc="left", pad=40)
    ax.text(0, 1.055,
            "Axes: proximity to end markets (x) vs. vertical integration (y). June 2026.",
            transform=ax.transAxes, fontsize=9.5, color="#666666")

    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, color="#EDEDED", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    png = EXPORT_DIR / "strategic_group_map.png"
    pdf = EXPORT_DIR / "strategic_group_map.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")

    if show:
        plt.show()
    plt.close(fig)

    print("Exported to exports/strategic_group_map.png and .pdf")


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategic group map chart.")
    parser.add_argument("--show", action="store_true", help="Display interactively before saving.")
    args = parser.parse_args()

    if not args.show:
        matplotlib.use("Agg")
    build_chart(show=args.show)


if __name__ == "__main__":
    main()
