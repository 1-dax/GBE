#!/usr/bin/env python3
"""
R&A Indumentaria — Brazil Market Research Agent
================================================

A CLI research analyst for the MBA consulting project advising R&A Indumentaria
(Argentine sportswear contract manufacturer) on relocating production to Paraguay
and entering the Brazilian market.

It answers specific research questions about the Brazilian sportswear market using
Claude + live web search, and returns a consistent JSON structure that can be
dropped straight into the analysis documents.

Usage
-----
  python research.py "your question here"      Run a free-form question
  python research.py --preset 3                Run priority question #3
  python research.py --batch                   Run all 8 priority questions
  python research.py --export brief.md          Export the last result to markdown
  python research.py --interactive             REPL with shared conversation context
  python research.py --list-presets            Show the 8 priority questions

Flags
-----
  --no-cache     Ignore the local cache and force a fresh search
  --model ID     Override the Claude model
  --json         Print raw JSON (default also prints a readable summary)

Environment
-----------
  ANTHROPIC_API_KEY must be set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #

# Project model. Swap here to upgrade, e.g. "claude-opus-4-8".
MODEL = "claude-sonnet-4-6"

# Web search server tool version requested by the brief.
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

MAX_TOKENS = 8000
BATCH_DELAY_SECONDS = 2          # rate-limit cushion between batch searches
MAX_SEARCH_CONTINUATIONS = 6     # safety cap on pause_turn resume loops

DATA_DIR = Path(os.environ.get("RESEARCH_DATA_DIR", Path(__file__).parent / ".research_data"))
DB_PATH = DATA_DIR / "research_cache.db"
LAST_RESULT_PATH = DATA_DIR / "last_result.json"
BATCH_OUTPUT_PATH = DATA_DIR / "batch_results.json"

# --------------------------------------------------------------------------- #
# System prompt (fixed project background — do NOT re-research)               #
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """\
You are a market research analyst supporting a consulting project for R&A Indumentaria, an Argentine sportswear contract manufacturer evaluating entry into the Brazilian market from a Paraguay production base.

Project context (treat this as fixed background knowledge, do not re-research):
- R&A makes football shirts, cotton activewear, and technical sportswear for Nike, Puma, New Balance, The North Face, and Kappa
- They are relocating production to Paraguay under the Maquila Regime (Law 7,547/2025 — 1% tax on local value added, zero import duties on inputs)
- Paraguay already ranks #2 as a source of Brazilian apparel imports behind China (Comex do Brasil 2024)
- Brazilian sportswear market: ~$4.8B in 2025, 4–5% CAGR (IMARC)
- Nike and Adidas hold ~41% combined market share (Euromonitor 2025)
- Target brands for R&A: Lupo (warm lead, cotton-heavy), Alto Giro (women's activewear), LIVE! (athleisure), Track&Field (premium, hardest to crack), Nike/Puma Brazil (existing Tier-1 relationships)
- Key unknown: do Brazilian brands outsource full-package manufacturing at scale, or produce vertically?
- Cotton = 31% of Brazil activewear market (IMARC) — LatAm has input cost advantage here vs. Asia
- Only ~3 factories in Brazil capable of quality technical sportswear for global brands

When answering a research question:
1. Search for current, specific information — not general overviews
2. Prioritize primary sources: B3 filings, Comex do Brasil (comexstat.mdic.gov.br), company investor relations, Brazilian trade press in Portuguese if needed
3. Distinguish clearly between confirmed facts, estimates, and inferences
4. Flag if a finding changes or contradicts the project's working assumptions above
5. Always include the specific source URL and date

Return every answer in this exact JSON structure:
{
  "question": "the question asked",
  "answer_summary": "2–3 sentence plain-language answer",
  "key_findings": ["finding 1 with source", "finding 2 with source"],
  "implications_for_ra": "1–2 sentences on what this means specifically for R&A's Brazil entry decision",
  "confidence": "HIGH / MEDIUM / LOW — with one sentence explaining why",
  "sources": [{"title": "", "url": "", "date": ""}],
  "follow_up_questions": ["question 1", "question 2"]
}

Do not pad the answer. If the information is not findable, say so and explain what source would have it and how to access it.

OUTPUT FORMAT REQUIREMENT: Your final message must be the JSON object and nothing else — no preamble, no explanation, no markdown code fences. Begin your final message with '{' and end it with '}'."""

# --------------------------------------------------------------------------- #
# Priority research questions (presets 1–8)                                   #
# --------------------------------------------------------------------------- #

PRESETS: list[str] = [
    "Does Lupo source apparel externally or produce vertically? What is their annual volume and product mix?",
    "What is Alto Giro's revenue, ownership structure, and sourcing model?",
    "What volume of sportswear did Brazil import from Paraguay in 2024, by HS code? "
    "Target the comexstat.mdic.gov.br database, HS codes 6105, 6112, and 6203.",
    "Is Grupo Dass opening a factory in Paraguay — what is the timeline and product scope?",
    "What is the Mercosur certificate of origin process for sportswear manufactured in Paraguay "
    "entering Brazil, and does cutting/sewing labor alone meet the 40% regional content threshold?",
    "What are current import tariff rates for football shirts (HS 6105) entering Brazil from Paraguay "
    "under Mercosur?",
    "What is Track&Field's (TFCO4) sourcing model — do they outsource manufacturing or produce in-house?",
    "What Brazilian sportswear brands currently source from Paraguay or other LatAm countries?",
]

REQUIRED_KEYS = [
    "question",
    "answer_summary",
    "key_findings",
    "implications_for_ra",
    "confidence",
    "sources",
    "follow_up_questions",
]

# --------------------------------------------------------------------------- #
# Local cache (SQLite, keyed by normalized question)                          #
# --------------------------------------------------------------------------- #


def _normalize(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


class ResultCache:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                question_key TEXT PRIMARY KEY,
                question     TEXT NOT NULL,
                result_json  TEXT NOT NULL,
                created_at   TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def get(self, question: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT result_json FROM results WHERE question_key = ?",
            (_normalize(question),),
        ).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return None
        return None

    def put(self, question: str, result: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO results (question_key, question, result_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(question_key) DO UPDATE SET
                result_json = excluded.result_json,
                created_at  = excluded.created_at
            """,
            (_normalize(question), question, json.dumps(result, ensure_ascii=False),
             datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


# --------------------------------------------------------------------------- #
# The research agent                                                          #
# --------------------------------------------------------------------------- #


class ResearchAgent:
    def __init__(self, model: str = MODEL, cache: ResultCache | None = None):
        self.client = anthropic.Anthropic()
        self.model = model
        self.cache = cache if cache is not None else ResultCache()
        # Conversation history is kept so follow-up questions share context
        # within a single session (used by interactive mode).
        self.messages: list[dict[str, Any]] = []

    # -- public API -------------------------------------------------------- #

    def research(
        self,
        question: str,
        use_cache: bool = True,
        remember: bool = False,
    ) -> dict[str, Any]:
        """Answer one research question, returning the structured result dict.

        remember=True keeps the turn in conversation history so later questions
        in the same session can build on it.
        """
        if use_cache and not remember:
            cached = self.cache.get(question)
            if cached is not None:
                cached["_from_cache"] = True
                _save_last(cached)
                return cached

        result = self._ask(question, remember=remember)
        self.cache.put(question, result)
        _save_last(result)
        return result

    # -- internals --------------------------------------------------------- #

    def _ask(self, question: str, remember: bool) -> dict[str, Any]:
        if remember:
            messages = self.messages
            messages.append({"role": "user", "content": question})
        else:
            messages = [{"role": "user", "content": question}]

        response = self._call_with_search(messages)

        if remember:
            # Preserve the full assistant content (incl. tool blocks) for context.
            messages.append({"role": "assistant", "content": response.content})

        text = _final_text(response)
        result = _parse_result(text, question)

        # Backfill sources from the web_search citations if the model left them sparse.
        if not result.get("sources"):
            result["sources"] = _search_sources(response)

        return result

    def _call_with_search(self, messages: list[dict[str, Any]]):
        """Run the Messages API with web search, resuming through pause_turn."""
        system = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # cache the fixed prefix
            }
        ]

        working = list(messages)
        for _ in range(MAX_SEARCH_CONTINUATIONS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system,
                tools=[WEB_SEARCH_TOOL],
                messages=working,
            )
            if response.stop_reason == "pause_turn":
                # Server-side search loop paused; resend to resume.
                working = working + [{"role": "assistant", "content": response.content}]
                continue
            return response

        # Hit the continuation cap — return whatever we have.
        return response


# --------------------------------------------------------------------------- #
# Response parsing helpers                                                     #
# --------------------------------------------------------------------------- #


def _final_text(response) -> str:
    """Concatenate all text blocks from the final assistant message."""
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()


def _extract_json(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON object from model output."""
    if not text:
        return None
    # Direct parse.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip ```json ... ``` fences.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    # Fall back to the widest {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _parse_result(text: str, question: str) -> dict[str, Any]:
    """Parse model text into the canonical result shape, tolerating failures."""
    data = _extract_json(text)
    if data is None:
        return {
            "question": question,
            "answer_summary": "Could not parse a structured answer from the model.",
            "key_findings": [],
            "implications_for_ra": "",
            "confidence": "LOW — the model did not return valid JSON.",
            "sources": [],
            "follow_up_questions": [],
            "_raw_text": text,
            "_parse_error": True,
        }
    # Ensure every expected key exists.
    for key in REQUIRED_KEYS:
        data.setdefault(key, [] if key in ("key_findings", "sources", "follow_up_questions") else "")
    if not data.get("question"):
        data["question"] = question
    return data


def _search_sources(response) -> list[dict[str, str]]:
    """Collect URLs/titles from web_search_tool_result blocks as a fallback."""
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for block in response.content:
        if getattr(block, "type", None) != "web_search_tool_result":
            continue
        content = getattr(block, "content", None) or []
        for item in content:
            url = getattr(item, "url", None)
            if url and url not in seen:
                seen.add(url)
                sources.append(
                    {
                        "title": getattr(item, "title", "") or "",
                        "url": url,
                        "date": getattr(item, "page_age", "") or "",
                    }
                )
    return sources


# --------------------------------------------------------------------------- #
# Persistence of the "last result" for --export                               #
# --------------------------------------------------------------------------- #


def _save_last(result: dict[str, Any]) -> None:
    LAST_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_last() -> dict[str, Any] | None:
    if LAST_RESULT_PATH.exists():
        try:
            return json.loads(LAST_RESULT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


# --------------------------------------------------------------------------- #
# Rendering                                                                    #
# --------------------------------------------------------------------------- #


def print_result(result: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    tag = "  (from cache)" if result.get("_from_cache") else ""
    line = "=" * 78
    print(f"\n{line}")
    print(f"Q: {result.get('question', '')}{tag}")
    print(line)
    print(f"\n{result.get('answer_summary', '')}\n")

    findings = result.get("key_findings") or []
    if findings:
        print("Key findings:")
        for f in findings:
            print(f"  • {f}")
        print()

    impl = result.get("implications_for_ra")
    if impl:
        print(f"Implications for R&A: {impl}\n")

    print(f"Confidence: {result.get('confidence', '')}\n")

    sources = result.get("sources") or []
    if sources:
        print("Sources:")
        for s in sources:
            title = s.get("title", "") if isinstance(s, dict) else str(s)
            url = s.get("url", "") if isinstance(s, dict) else ""
            date = s.get("date", "") if isinstance(s, dict) else ""
            meta = " — ".join(p for p in (title, url, date) if p)
            print(f"  • {meta}")
        print()

    fups = result.get("follow_up_questions") or []
    if fups:
        print("Follow-up questions:")
        for q in fups:
            print(f"  → {q}")
        print()

    if result.get("_parse_error"):
        print("[note] Could not parse JSON — raw model text saved in the result file.\n")


def to_markdown(result: dict[str, Any]) -> str:
    """Render a result as clean, Word-pasteable markdown for the analysis docs."""
    lines: list[str] = []
    lines.append(f"## {result.get('question', 'Research Question')}")
    lines.append("")

    lines.append("### Finding")
    lines.append(result.get("answer_summary", "").strip() or "_No summary available._")
    lines.append("")

    lines.append("### Key Facts")
    findings = result.get("key_findings") or []
    if findings:
        for f in findings:
            lines.append(f"- {f}")
    else:
        lines.append("- _No specific findings recorded._")
    lines.append("")

    lines.append("### Implications for R&A")
    lines.append(result.get("implications_for_ra", "").strip() or "_None recorded._")
    lines.append("")

    lines.append("### Confidence")
    lines.append(result.get("confidence", "").strip() or "_Not stated._")
    lines.append("")

    lines.append("### Sources")
    sources = result.get("sources") or []
    if sources:
        for s in sources:
            if isinstance(s, dict):
                title = s.get("title", "").strip()
                url = s.get("url", "").strip()
                date = s.get("date", "").strip()
                bits = [b for b in (title or url, url if title else "", date) if b]
                # Avoid duplicating the url when there's no title.
                if title and url:
                    entry = f"{title} — {url}"
                elif url:
                    entry = url
                else:
                    entry = title
                if date:
                    entry += f" ({date})"
                lines.append(f"- {entry}")
            else:
                lines.append(f"- {s}")
    else:
        lines.append("- _No sources recorded._")
    lines.append("")

    fups = result.get("follow_up_questions") or []
    if fups:
        lines.append("### Suggested Follow-Up Questions")
        for q in fups:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Modes                                                                        #
# --------------------------------------------------------------------------- #


def run_batch(agent: ResearchAgent, use_cache: bool, as_json: bool) -> None:
    print(f"Running all {len(PRESETS)} priority questions…\n")
    all_results: list[dict[str, Any]] = []
    for i, question in enumerate(PRESETS, start=1):
        print(f"[{i}/{len(PRESETS)}] {question[:70]}…")
        result = agent.research(question, use_cache=use_cache)
        all_results.append(result)
        print_result(result, as_json=as_json)
        if i < len(PRESETS):
            time.sleep(BATCH_DELAY_SECONDS)

    BATCH_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BATCH_OUTPUT_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": agent.model,
                "results": all_results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved {len(all_results)} results to {BATCH_OUTPUT_PATH}")


def run_interactive(agent: ResearchAgent, use_cache: bool, as_json: bool) -> None:
    print("Interactive research session. Follow-up questions share context.")
    print("Type your question, or 'exit' / 'quit' to leave, 'export <file>' to save the last answer.\n")
    while True:
        try:
            line = input("research> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            break
        if line.lower().startswith("export"):
            parts = line.split(maxsplit=1)
            fname = parts[1].strip() if len(parts) > 1 else "research_export.md"
            do_export(fname)
            continue
        # remember=True so follow-ups in this session have prior context.
        result = agent.research(line, use_cache=use_cache, remember=True)
        print_result(result, as_json=as_json)


def do_export(filename: str | None) -> int:
    result = _load_last()
    if result is None:
        print("No previous result to export. Run a question first.", file=sys.stderr)
        return 1
    out = Path(filename) if filename else Path("research_export.md")
    if out.suffix == "":
        out = out.with_suffix(".md")
    out.write_text(to_markdown(result), encoding="utf-8")
    print(f"Exported last result to {out}")
    return 0


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="research",
        description="Brazil sportswear market research agent for the R&A Indumentaria project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("question", nargs="?", help="A free-form research question.")
    p.add_argument("--preset", type=int, metavar="N", help="Run priority question N (1-8).")
    p.add_argument("--batch", action="store_true", help="Run all 8 priority questions sequentially.")
    p.add_argument(
        "--export",
        nargs="?",
        const="research_export.md",
        metavar="FILE",
        help="Export the last result to a markdown file (default: research_export.md).",
    )
    p.add_argument("--interactive", "-i", action="store_true", help="Start an interactive REPL session.")
    p.add_argument("--list-presets", action="store_true", help="List the 8 priority questions and exit.")
    p.add_argument("--no-cache", action="store_true", help="Ignore the cache; force a fresh search.")
    p.add_argument("--json", action="store_true", help="Print raw JSON instead of the readable summary.")
    p.add_argument("--model", default=MODEL, help=f"Claude model to use (default: {MODEL}).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_presets:
        print("Priority research questions:\n")
        for i, q in enumerate(PRESETS, start=1):
            print(f"  {i}. {q}")
        return 0

    # --export is a local file op and needs no API key.
    if args.export is not None and not (args.question or args.preset or args.batch or args.interactive):
        return do_export(args.export)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2

    use_cache = not args.no_cache
    cache = ResultCache()
    agent = ResearchAgent(model=args.model, cache=cache)

    try:
        if args.batch:
            run_batch(agent, use_cache=use_cache, as_json=args.json)
        elif args.interactive:
            run_interactive(agent, use_cache=use_cache, as_json=args.json)
        elif args.preset is not None:
            if not (1 <= args.preset <= len(PRESETS)):
                print(f"Error: --preset must be between 1 and {len(PRESETS)}.", file=sys.stderr)
                return 2
            result = agent.research(PRESETS[args.preset - 1], use_cache=use_cache)
            print_result(result, as_json=args.json)
        elif args.question:
            result = agent.research(args.question, use_cache=use_cache)
            print_result(result, as_json=args.json)
        else:
            build_parser().print_help()
            return 1

        # Allow --export to chain after a query in the same invocation.
        if args.export is not None and (args.question or args.preset or args.batch):
            do_export(args.export)
    except anthropic.APIError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1
    finally:
        cache.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
