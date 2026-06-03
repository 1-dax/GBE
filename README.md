# R&A Indumentaria — GBE Argentina Research Tools
Georgetown McDonough MBA · Global Business Experience · June 2026

Tools supporting the R&A Indumentaria consulting project: Paraguay manufacturing relocation, Brazil market entry, and US market strategy.

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env` and add your Anthropic API key
3. Install dependencies for the tools you need (each folder has its own requirements.txt)

## Tools

### Research Agent (`research/`)
AI-powered research tool for Brazilian market questions. Uses Claude with web search.

```bash
cd research
pip install -r requirements.txt
python research.py --preset 3
```

See research/README.md for full documentation.

### Visualizations (`visualizations/`)
Chart generators for project presentations and documents.

```bash
cd visualizations
pip install -r requirements.txt
python cost_comparison.py
python market_sizing.py
python strategic_group_map.py
```

All charts export to `exports/`.

### Data (`data/`)
Shared benchmark data used by all tools. Edit `benchmarks.json` when client data arrives — all visualizations pull from this file automatically.

## Team
Gloria Carls · Clark Tutwiler · Dax Deases · Alex Kholb
Client: R&A Indumentaria, Buenos Aires · Contact: Matias Krebs
