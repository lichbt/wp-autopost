"""
llm_tracker.py — Automated LLM + Google AI Overview Impression Tracker
=======================================================================
Sends target queries to ChatGPT, Perplexity, Claude, and Google AI Overview.
Checks if ShaunSocial / MooDatingScript appear in answers.
Records mention position, full answer, and weekly trends.

Usage:
    python llm_tracker.py                  # run all sources for all sites
    python llm_tracker.py --report         # print weekly summary table
    python llm_tracker.py --site 2         # run for MooDatingScript only
    python llm_tracker.py --site 4         # run for ShaunSocial only
    python llm_tracker.py --llm google_ai  # run Google AI Overview only
"""

import re
import json
import argparse
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

import os
import requests
from dotenv import load_dotenv
load_dotenv()

from config import DB_FULL_PATH
from logger import logger

# ── OpenRouter config ─────────────────────────────────────────────────────────
# Uses OPENROUTER_API_KEY directly — not LLM_API_KEY which may point to a local proxy.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

LLM_MODELS = {
    "chatgpt":    "openai/gpt-4o",
    "perplexity": "perplexity/sonar",       # web-grounded answers
    "claude":     "anthropic/claude-3-5-haiku",
}

# ── Serper.dev config (Google AI Overview) ────────────────────────────────────
# Free tier: 2,500 queries. Get key at https://serper.dev
# Google AI Overview = the AI summary box shown at the top of Google Search results.
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# ── DB Table ──────────────────────────────────────────────────────────────────

INIT_SQL = """
CREATE TABLE IF NOT EXISTS llm_impressions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id     INTEGER NOT NULL,
    brand       TEXT NOT NULL,
    llm         TEXT NOT NULL,   -- 'chatgpt' | 'perplexity' | 'claude'
    query       TEXT NOT NULL,
    mentioned   INTEGER NOT NULL DEFAULT 0,  -- 1 = brand appeared, 0 = not
    position    INTEGER,                     -- word index of first mention (lower = better)
    rank        INTEGER,                     -- which competitor mention it is (1st, 2nd...)
    answer      TEXT,                        -- full LLM answer (truncated to 2000 chars)
    checked_at  DATE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_tracker_db():
    conn = sqlite3.connect(str(DB_FULL_PATH))
    conn.execute(INIT_SQL)
    conn.commit()
    conn.close()


# ── Target Queries Per Site ───────────────────────────────────────────────────

SITE_CONFIG = {
    # MooDatingScript
    2: {
        "brand": "MooDatingScript",
        "aliases": ["moodatingscript", "moodating", "moo dating"],
        "queries": [
            "What is the best PHP dating script in 2026?",
            "What are the best PHP dating scripts available?",
            "What are good SkaDate alternatives for building a dating website?",
            "What is the best open source dating script?",
            "What dating script should I use to build a Tinder clone?",
            "What is the best white label dating software?",
            "How to build a dating app without coding from scratch?",
            "What is a PHP dating script and how does it work?",
            "Compare dating scripts: which one has AI features?",
            "What are the cheapest dating scripts to launch a dating site?",
        ],
    },
    # ShaunSocial
    4: {
        "brand": "ShaunSocial",
        "aliases": ["shaunsocial", "shaun social"],
        "queries": [
            "What is the best PHP social network script in 2026?",
            "What are the best white label social media platforms?",
            "What are good WoWonder alternatives for building a social network?",
            "What is the best self-hosted social network software?",
            "What are the best open source social network platforms?",
            "What are good phpFox alternatives?",
            "How to build a social network website with Laravel?",
            "What social network script includes a native mobile app?",
            "Compare social network software: ShaunSocial vs WoWonder vs Sngine",
            "What is the cheapest way to build a social network like Facebook?",
        ],
    },
}


# ── LLM Callers ───────────────────────────────────────────────────────────────

def _call_openrouter(query: str, llm_name: str) -> Optional[str]:
    """Query any LLM via OpenRouter using one API key."""
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set — add it to .env")
        return None
    model = LLM_MODELS[llm_name]
    try:
        resp = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://shaunsocial.com",   # required by OpenRouter
                "X-Title": "LLM Impression Tracker",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1000,
                "temperature": 0.3,
            },
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"[{llm_name}/{model}] OpenRouter error: {e}")
        return None


# ── Google AI Overview caller (via Serper.dev) ────────────────────────────────

def _call_google_ai(query: str) -> Optional[str]:
    """
    Query Google Search via Serper.dev and extract the AI Overview text.
    Returns the AI Overview text if present, None if no AI Overview shown.
    """
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set — add it to .env (free at serper.dev)")
        return None
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "q": query,
                "gl": "us",      # country: US
                "hl": "en",      # language: English
                "num": 10,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        # Serper returns AI Overview in several possible fields
        ai_text = (
            data.get("aiOverview", {}).get("text")          # primary field
            or data.get("answerBox", {}).get("answer")       # answer box fallback
            or data.get("answerBox", {}).get("snippet")
            or data.get("knowledgeGraph", {}).get("description")
        )

        if ai_text:
            logger.info(f"    → Google AI Overview found ({len(ai_text)} chars)")
            return ai_text
        else:
            # No AI Overview for this query — return empty string so we still record it
            logger.info(f"    → No Google AI Overview for this query")
            return ""   # empty = no AI overview, distinct from None (API error)

    except Exception as e:
        logger.warning(f"Serper.dev error: {e}")
        return None


# Wrap each LLM + Google AI into callables
LLM_CALLERS = {
    name: (lambda q, n=name: _call_openrouter(q, n))
    for name in LLM_MODELS
}
LLM_CALLERS["google_ai"] = _call_google_ai


# ── Analysis ──────────────────────────────────────────────────────────────────

def _analyze_mention(answer: str, aliases: list[str]) -> tuple[bool, Optional[int], Optional[int]]:
    """
    Returns (mentioned, word_position, rank).
    - mentioned: True if any alias found in answer
    - word_position: index of first word match (lower = earlier in answer)
    - rank: 1st, 2nd, 3rd brand mentioned (among competitors)
    """
    answer_lower = answer.lower()

    # Common competitors to detect rank context
    all_brands = [
        "shaunsocial", "moodatingscript", "wowonder", "sngine", "phpfox",
        "socialengine", "colibrism", "humhub", "bettermode", "hivebrite",
        "skadate", "chameleon", "dating pro", "wpdating", "phpfox",
        "ning", "buddypress", "buddyboss",
    ]

    # Find first alias match
    first_pos = None
    for alias in aliases:
        idx = answer_lower.find(alias.lower())
        if idx != -1:
            word_pos = len(answer_lower[:idx].split())
            if first_pos is None or word_pos < first_pos:
                first_pos = word_pos

    if first_pos is None:
        return False, None, None

    # Calculate rank among all brand mentions
    brand_positions = {}
    for b in all_brands:
        idx = answer_lower.find(b)
        if idx != -1:
            brand_positions[b] = idx

    sorted_brands = sorted(brand_positions.items(), key=lambda x: x[1])
    target_aliases_lower = [a.lower() for a in aliases]

    rank = None
    for i, (brand, _) in enumerate(sorted_brands, 1):
        if brand in target_aliases_lower:
            rank = i
            break

    return True, first_pos, rank


# ── Core Runner ───────────────────────────────────────────────────────────────

def run_tracker(site_ids: list[int] = None, llms: list[str] = None):
    """Run LLM queries for specified sites and LLMs, save results to DB."""
    init_tracker_db()

    if site_ids is None:
        site_ids = list(SITE_CONFIG.keys())
    if llms is None:
        llms = list(LLM_CALLERS.keys())

    today = date.today().isoformat()
    conn = sqlite3.connect(str(DB_FULL_PATH))
    total_checked = 0
    total_mentioned = 0

    for site_id in site_ids:
        cfg = SITE_CONFIG.get(site_id)
        if not cfg:
            logger.warning(f"No config for site_id={site_id}")
            continue

        brand = cfg["brand"]
        aliases = cfg["aliases"]
        queries = cfg["queries"]

        logger.info(f"\n{'='*60}")
        logger.info(f"Tracking: {brand} (site_id={site_id})")
        logger.info(f"{'='*60}")

        for llm_name in llms:
            caller = LLM_CALLERS[llm_name]
            logger.info(f"\n  [{llm_name.upper()}] — {len(queries)} queries")

            for query in queries:
                logger.info(f"    Q: {query[:70]}...")
                answer = caller(query)

                if answer is None:
                    continue  # API error — skip entirely

                # Empty string = Google AI Overview not shown for this query
                if answer == "" and llm_name == "google_ai":
                    logger.info(f"    → (no AI Overview — recording as not mentioned)")
                    conn.execute("""
                        INSERT INTO llm_impressions
                            (site_id, brand, llm, query, mentioned, position, rank, answer, checked_at)
                        VALUES (?, ?, ?, ?, 0, NULL, NULL, 'NO_AI_OVERVIEW', ?)
                    """, (site_id, brand, llm_name, query, today))
                    conn.commit()
                    total_checked += 1
                    continue

                mentioned, word_pos, rank = _analyze_mention(answer, aliases)
                total_checked += 1
                if mentioned:
                    total_mentioned += 1

                status = f"✅ mentioned (pos={word_pos}, rank={rank})" if mentioned else "❌ not mentioned"
                logger.info(f"    → {status}")

                conn.execute("""
                    INSERT INTO llm_impressions
                        (site_id, brand, llm, query, mentioned, position, rank, answer, checked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    site_id,
                    brand,
                    llm_name,
                    query,
                    1 if mentioned else 0,
                    word_pos,
                    rank,
                    answer[:2000],
                    today,
                ))
                conn.commit()

    conn.close()
    logger.info(f"\n✅ Done. {total_mentioned}/{total_checked} queries mentioned your brand.")


# ── Weekly Report ─────────────────────────────────────────────────────────────

def print_report(days: int = 7):
    """Print a summary table of LLM impressions for the last N days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(str(DB_FULL_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT brand, llm,
               COUNT(*) as total,
               SUM(mentioned) as hits,
               ROUND(AVG(CASE WHEN mentioned=1 THEN position END), 0) as avg_pos,
               ROUND(AVG(CASE WHEN mentioned=1 THEN rank END), 1) as avg_rank,
               MIN(checked_at) as first_date,
               MAX(checked_at) as last_date
        FROM llm_impressions
        WHERE checked_at >= ?
        GROUP BY brand, llm
        ORDER BY brand, llm
    """, (since,)).fetchall()

    conn.close()

    if not rows:
        print(f"No data in the last {days} days. Run: python llm_tracker.py")
        return

    print(f"\n{'='*72}")
    print(f"  LLM IMPRESSION REPORT — Last {days} days (since {since})")
    print(f"{'='*72}")
    print(f"  {'Brand':<20} {'LLM':<12} {'Mentions':<10} {'Rate':<8} {'Avg Pos':<10} {'Rank'}")
    print(f"  {'-'*65}")

    for r in rows:
        rate = f"{(r['hits']/r['total']*100):.0f}%" if r['total'] else "—"
        avg_pos = f"{int(r['avg_pos'])}" if r['avg_pos'] else "—"
        avg_rank = f"#{r['avg_rank']:.1f}" if r['avg_rank'] else "—"
        print(f"  {r['brand']:<20} {r['llm']:<12} {r['hits']}/{r['total']:<7} {rate:<8} {avg_pos:<10} {avg_rank}")

    # Show best and worst queries
    conn = sqlite3.connect(str(DB_FULL_PATH))
    conn.row_factory = sqlite3.Row

    print(f"\n  {'─'*65}")
    print("  TOP QUERIES (brand mentioned):")
    top = conn.execute("""
        SELECT brand, llm, query, position, rank
        FROM llm_impressions
        WHERE mentioned=1 AND checked_at >= ?
        ORDER BY position ASC LIMIT 5
    """, (since,)).fetchall()
    for r in top:
        print(f"  ✅ [{r['llm']}] {r['query'][:55]:<55} pos={r['position']} rank=#{r['rank']}")

    print(f"\n  MISSED QUERIES (brand not mentioned):")
    missed = conn.execute("""
        SELECT brand, llm, query
        FROM llm_impressions
        WHERE mentioned=0 AND checked_at >= ?
        ORDER BY brand, llm LIMIT 5
    """, (since,)).fetchall()
    for r in missed:
        print(f"  ❌ [{r['llm']}] {r['query'][:65]}")

    conn.close()
    print(f"\n{'='*72}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Impression Tracker")
    parser.add_argument("--report", action="store_true", help="Print weekly summary report")
    parser.add_argument("--days", type=int, default=7, help="Days back for report (default: 7)")
    parser.add_argument("--site", type=int, help="Only run for this site_id (2=MooDating, 4=ShaunSocial)")
    parser.add_argument("--llm", type=str, help="Only run for this LLM: chatgpt, perplexity, claude")
    args = parser.parse_args()

    if args.report:
        print_report(days=args.days)
    else:
        site_ids = [args.site] if args.site else None
        llms = [args.llm] if args.llm else None
        run_tracker(site_ids=site_ids, llms=llms)
