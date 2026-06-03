"""
Streamlit web app for the R&A Indumentaria Brazil market research agent.

Wraps the existing research/research.py logic in a shared web UI so teammates can
type a question (or pick a priority preset), get the structured answer with sources,
and download it as Word-pasteable markdown.

Run locally:   streamlit run streamlit_app.py
Deploy:        Streamlit Community Cloud -> repo 1-dax/GBE, main file streamlit_app.py,
               add secret ANTHROPIC_API_KEY in the app settings.
"""

from __future__ import annotations

import importlib.util
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

# --------------------------------------------------------------------------- #
# Load the research module from research/research.py (single source of truth)  #
# --------------------------------------------------------------------------- #

_RESEARCH_PATH = Path(__file__).parent / "research" / "research.py"
_spec = importlib.util.spec_from_file_location("research_agent", _RESEARCH_PATH)
research = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(research)

# --------------------------------------------------------------------------- #
# API key: prefer the environment, fall back to Streamlit secrets (on Cloud)   #
# --------------------------------------------------------------------------- #


def resolve_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")  # type: ignore[attr-defined]
    except Exception:
        key = None
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key  # the Anthropic SDK reads this
    return key


# --------------------------------------------------------------------------- #
# Page                                                                         #
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="R&A Brazil Market Research", page_icon="🇧🇷", layout="wide")

st.title("R&A Indumentaria — Brazil Market Research")
st.caption(
    "Georgetown McDonough MBA · GBE Argentina · Claude + live web search. "
    "Answers are returned in a consistent structure for the analysis docs."
)

api_key = resolve_api_key()

with st.sidebar:
    st.subheader("About")
    st.markdown(
        "Each query runs a live web search and can take **30–90 seconds**. "
        "Results are cached, so re-asking the same question is instant."
    )
    st.markdown("Repo: [1-dax/GBE](https://github.com/1-dax/GBE)")
    if not api_key:
        st.error(
            "No API key found. Set `ANTHROPIC_API_KEY` as an environment variable "
            "(local) or in the app's **Secrets** (Streamlit Cloud)."
        )
    else:
        st.success("API key loaded.")
    no_cache = st.checkbox("Bypass cache (force fresh search)", value=False)


# --------------------------------------------------------------------------- #
# Question input                                                               #
# --------------------------------------------------------------------------- #

mode = st.radio("Question source", ["Pick a priority question", "Ask your own"], horizontal=True)

if mode == "Pick a priority question":
    idx = st.selectbox(
        "Priority research questions",
        options=range(len(research.PRESETS)),
        format_func=lambda i: f"{i + 1}. {research.PRESETS[i]}",
    )
    question = research.PRESETS[idx]
else:
    question = st.text_area(
        "Your research question",
        placeholder="e.g. What is LIVE!'s manufacturing footprint and do they outsource?",
        height=100,
    )

run = st.button("🔎 Run research", type="primary", disabled=not api_key)


# --------------------------------------------------------------------------- #
# Rendering                                                                    #
# --------------------------------------------------------------------------- #


def render(result: dict) -> None:
    if result.get("_from_cache"):
        st.caption("⚡ Served from cache")

    if result.get("_parse_error"):
        st.warning("The model did not return clean JSON for this question. Raw text below.")
        st.text(result.get("_raw_text", ""))
        return

    st.subheader("Answer")
    st.write(result.get("answer_summary", ""))

    findings = result.get("key_findings") or []
    if findings:
        st.markdown("**Key findings**")
        for f in findings:
            st.markdown(f"- {f}")

    impl = result.get("implications_for_ra")
    if impl:
        st.markdown("**Implications for R&A**")
        st.info(impl)

    conf = (result.get("confidence") or "").strip()
    if conf:
        st.markdown("**Confidence**")
        upper = conf.upper()
        if upper.startswith("HIGH"):
            st.success(conf)
        elif upper.startswith("MEDIUM"):
            st.warning(conf)
        else:
            st.error(conf)

    sources = result.get("sources") or []
    if sources:
        st.markdown("**Sources**")
        for s in sources:
            if isinstance(s, dict):
                title = s.get("title") or s.get("url") or "source"
                url = s.get("url") or ""
                date = f" ({s['date']})" if s.get("date") else ""
                if url:
                    st.markdown(f"- [{title}]({url}){date}")
                else:
                    st.markdown(f"- {title}{date}")
            else:
                st.markdown(f"- {s}")

    fups = result.get("follow_up_questions") or []
    if fups:
        st.markdown("**Suggested follow-up questions**")
        for q in fups:
            st.markdown(f"- {q}")

    # Downloads
    md = research.to_markdown(result)
    slug = "".join(c if c.isalnum() else "_" for c in result.get("question", "result"))[:50]
    st.download_button("⬇️ Download as markdown", md, file_name=f"{slug}.md", mime="text/markdown")

    with st.expander("Raw JSON"):
        st.json({k: v for k, v in result.items() if not k.startswith("_")})


# --------------------------------------------------------------------------- #
# Run                                                                          #
# --------------------------------------------------------------------------- #

if run:
    if not question or not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            with st.spinner("Searching primary sources… this can take 30–90 seconds."):
                # Fresh agent per run keeps the SQLite connection on this thread.
                agent = research.ResearchAgent()
                result = agent.research(question, use_cache=not no_cache)
            render(result)
        except research.anthropic.APIError as e:  # type: ignore[attr-defined]
            st.error(f"API error: {e}")
        except Exception as e:  # noqa: BLE001  surface anything else to the user
            st.error(f"Something went wrong: {e}")
