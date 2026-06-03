# Research Agent — Brazil Market

AI research analyst for the R&A Indumentaria project. Answers specific questions about
the Brazilian sportswear market using Claude + live web search, and returns a consistent
JSON structure that drops straight into the analysis documents.

## Setup

```bash
pip install -r requirements.txt
# From the repo root, copy .env.example to .env and add your key, or set it directly:
# PowerShell:  $env:ANTHROPIC_API_KEY = "sk-ant-..."
# bash:        export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
python research.py "your question here"     # free-form question
python research.py --preset 3               # run priority question #3
python research.py --batch                  # run all 8 priority questions, save to JSON
python research.py --export brief.md         # export the last result as Word-pasteable markdown
python research.py --interactive             # REPL; follow-ups share conversation context
python research.py --list-presets            # show the 8 priority questions
```

Useful flags:

| Flag | Effect |
|------|--------|
| `--no-cache` | Ignore the local cache and force a fresh search |
| `--json` | Print raw JSON instead of the readable summary |
| `--model ID` | Override the Claude model (default: `claude-sonnet-4-6`) |

You can also chain an export onto a query: `python research.py --preset 2 --export alto_giro.md`.

## Output structure

Every answer is returned as:

```json
{
  "question": "...",
  "answer_summary": "2–3 sentence plain-language answer",
  "key_findings": ["finding 1 with source", "finding 2 with source"],
  "implications_for_ra": "what this means for R&A's Brazil entry decision",
  "confidence": "HIGH / MEDIUM / LOW — with reason",
  "sources": [{"title": "", "url": "", "date": ""}],
  "follow_up_questions": ["...", "..."]
}
```

`--export` turns the last result into markdown with **Finding / Key Facts / Implications
for R&A / Confidence / Sources** sections — clean enough to paste directly into the
professor pre-read or the Brazil market analysis document.

## The 8 priority questions

Run any of them with `--preset N`:

1. Lupo — external sourcing vs. vertical production, annual volume and product mix
2. Alto Giro — revenue, ownership structure, sourcing model
3. Brazil → Paraguay sportswear import volume 2024 by HS code (comexstat.mdic.gov.br; HS 6105, 6112, 6203)
4. Grupo Dass — Paraguay factory timeline and product scope
5. Mercosur certificate of origin process; does cut/sew labor alone meet the 40% regional content threshold
6. Import tariff rates for football shirts (HS 6105) into Brazil from Paraguay under Mercosur
7. Track&Field (TFCO4) — outsource vs. in-house manufacturing
8. Brazilian sportswear brands sourcing from Paraguay / other LatAm countries

## How it works

- **Web search** is enabled on every call (`web_search_20250305`), so answers reflect
  current sources, not training data.
- **Prompt caching** is applied to the large fixed system prompt (project background),
  so repeated calls — e.g. in `--batch` — reuse the cached prefix.
- **Conversation history** is kept within a session in `--interactive` mode, so a
  follow-up like "and what about their export markets?" has the prior answer as context.
- **Local SQLite cache** (`research/.research_data/research_cache.db`) stores results
  keyed by question, so re-asking the same thing doesn't re-run a search. Use `--no-cache`
  to bypass. The cache lives next to the script regardless of where you run it from.
- **Rate limiting**: a 2-second pause between batch searches.

## Data files

Created under `research/.research_data/` (override with the `RESEARCH_DATA_DIR` env var):

- `research_cache.db` — SQLite cache of answered questions
- `last_result.json` — the most recent result (source for `--export`)
- `batch_results.json` — output of the last `--batch` run
