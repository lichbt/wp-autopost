"""
keyword_research.py — Live SERP signals via Serper.dev (Tier 3).
================================================================
Adds real-world query discovery to plan generation:
- Related searches + People-Also-Ask  → topics people actually search (long-tail/FAQ).
- AI-Overview presence per query       → flag queries to prioritise GEO formats for.

Serper.dev does NOT return search volume/difficulty (that needs a paid API like
DataForSEO); it returns live SERP structure, which is what we use here.

Degrades gracefully: every entry point returns empty if SERPER_API_KEY is unset,
so plan generation works with or without it. Responses are cached on disk (7 days)
to conserve the free quota (2,500/mo).
"""
import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

from config import PROJECT_ROOT
from logger import logger

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"
_CACHE_DIR = PROJECT_ROOT / "data" / "serper_cache"
_CACHE_TTL = 7 * 24 * 3600  # 7 days


def serper_available() -> bool:
    return bool(SERPER_API_KEY) and SERPER_API_KEY not in ("your_serper_key_here", "")


def _cache_file(query: str) -> Path:
    h = hashlib.sha1(query.lower().strip().encode("utf-8")).hexdigest()[:16]
    return _CACHE_DIR / f"{h}.json"


def serper_search(query: str, gl: str = "us", hl: str = "en", timeout: int = 20) -> Optional[Dict]:
    """One Serper search (cached). Returns the raw JSON, or None if unavailable/error."""
    if not serper_available():
        return None
    cf = _cache_file(query)
    try:
        if cf.exists() and (time.time() - cf.stat().st_mtime) < _CACHE_TTL:
            return json.loads(cf.read_text(encoding="utf-8"))
    except Exception:
        pass
    try:
        resp = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "gl": gl, "hl": hl},
            timeout=timeout,
        )
        if resp.status_code != 200:
            logger.warning(f"[serper] HTTP {resp.status_code} for '{query}'")
            return None
        data = resp.json()
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cf.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass
        return data
    except Exception as exc:
        logger.warning(f"[serper] error for '{query}': {exc}")
        return None


def _extract(data: Dict) -> Dict:
    related = [r.get("query", "").strip() for r in (data.get("relatedSearches") or [])]
    paa = [q.get("question", "").strip() for q in (data.get("peopleAlsoAsk") or [])]
    # AI Overview / answer box presence is a strong GEO signal.
    ai_overview = bool(data.get("aiOverview") or data.get("answerBox"))
    return {
        "related": [q for q in related if q],
        "paa": [q for q in paa if q],
        "ai_overview": ai_overview,
    }


def discover_related_queries(seeds: List[str], max_seeds: int = 8) -> Dict:
    """Aggregate related searches + PAA across seed queries; track which seeds
    trigger an AI Overview. Returns {"related","paa","ai_overview"} (lists)."""
    related, paa, ai_overview = set(), set(), set()
    for q in [s for s in seeds if s][:max_seeds]:
        data = serper_search(q)
        if not data:
            continue
        ex = _extract(data)
        related.update(ex["related"])
        paa.update(ex["paa"])
        if ex["ai_overview"]:
            ai_overview.add(q)
    return {"related": sorted(related), "paa": sorted(paa), "ai_overview": sorted(ai_overview)}


def get_keyword_research_block(seeds: List[str], max_seeds: int = 8) -> str:
    """Prompt-ready block of live SERP query discovery. '' if Serper unavailable
    or nothing found."""
    if not serper_available():
        return ""
    res = discover_related_queries(seeds, max_seeds=max_seeds)
    if not (res["related"] or res["paa"]):
        return ""

    lines = ["KEYWORD RESEARCH (live Google SERP via Serper) — mine these real searches for topics:"]
    if res["related"]:
        lines.append("Related searches:")
        lines += [f"  • {q}" for q in res["related"][:20]]
    if res["paa"]:
        lines.append("People Also Ask (ideal for FAQ sections / long-tail articles):")
        lines += [f"  • {q}" for q in res["paa"][:15]]
    if res["ai_overview"]:
        lines.append("Queries that trigger Google AI Overviews "
                     "(PRIORITISE GEO-optimised formats — direct-answer openers, structured data):")
        lines += [f"  • {q}" for q in res["ai_overview"][:10]]
    return "\n".join(lines)
