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

## Web app for the team (`streamlit_app.py`)

The research agent is also available as a shared web app — teammates open a URL, pick a
priority question (or ask their own), and get the structured answer with sources plus a
markdown download. No terminal needed.

**Run locally:**

```bash
pip install -r requirements.txt
# provide your key one of two ways:
#   export ANTHROPIC_API_KEY=sk-ant-...        (PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-...")
#   or create .streamlit/secrets.toml with:  ANTHROPIC_API_KEY = "sk-ant-..."
streamlit run streamlit_app.py
```

**Deploy on Streamlit Community Cloud (free, shareable URL):**

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. New app → repo `1-dax/GBE`, branch `main`, main file `streamlit_app.py`.
3. In **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Deploy. Share the URL with the team.

> The hosted app uses **one** API key (your spend covers everyone's searches). The
> SQLite cache is shared per running container, so repeated questions are instant.

## Team
Gloria Carls · Clark Tutwiler · Dax Deases · Alex Kholb
Client: R&A Indumentaria, Buenos Aires · Contact: Matias Krebs
