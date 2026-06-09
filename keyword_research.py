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

# Free, keyless fallback: Google autocomplete/suggest. Used automatically when
# Serper has no key OR its quota is exhausted (Serper then returns an error and
# we fall through per-seed). Gives real query suggestions — no PAA/AI-Overview.
GOOGLE_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
_AC_MODIFIERS = ["", " vs", " best", " alternative", " how to", " free", " review"]


def serper_available() -> bool:
    return bool(SERPER_API_KEY) and SERPER_API_KEY not in ("your_serper_key_here", "")


def _cache_file(key: str) -> Path:
    h = hashlib.sha1(key.lower().strip().encode("utf-8")).hexdigest()[:16]
    return _CACHE_DIR / f"{h}.json"


def _cache_read(key: str):
    cf = _cache_file(key)
    try:
        if cf.exists() and (time.time() - cf.stat().st_mtime) < _CACHE_TTL:
            return json.loads(cf.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _cache_write(key: str, data) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_file(key).write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def serper_search(query: str, gl: str = "us", hl: str = "en", timeout: int = 20) -> Optional[Dict]:
    """One Serper search (cached). Returns raw JSON, or None if unavailable/error
    (incl. quota exhaustion → the caller falls back to autocomplete)."""
    if not serper_available():
        return None
    cached = _cache_read(f"serper:{query}")
    if cached is not None:
        return cached
    try:
        resp = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "gl": gl, "hl": hl},
            timeout=timeout,
        )
        if resp.status_code != 200:
            logger.warning(f"[serper] HTTP {resp.status_code} for '{query}' "
                           "(quota exhausted? → falling back to autocomplete)")
            return None
        data = resp.json()
        _cache_write(f"serper:{query}", data)
        return data
    except Exception as exc:
        logger.warning(f"[serper] error for '{query}': {exc}")
        return None


def google_autocomplete(query: str, hl: str = "en", timeout: int = 10) -> List[str]:
    """Free, keyless Google query suggestions for `query` (cached)."""
    if not query or not query.strip():
        return []
    cached = _cache_read(f"ac:{query}")
    if cached is not None:
        return cached
    try:
        resp = requests.get(
            GOOGLE_SUGGEST_URL,
            params={"client": "firefox", "q": query, "hl": hl},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return []
        data = json.loads(resp.text)  # ["query", ["sugg1", "sugg2", ...]]
        sugg = (data[1] if isinstance(data, list) and len(data) > 1
                and isinstance(data[1], list) else [])
        sugg = [s.strip() for s in sugg if isinstance(s, str) and s.strip()]
        _cache_write(f"ac:{query}", sugg)
        return sugg
    except Exception as exc:
        logger.warning(f"[autocomplete] error for '{query}': {exc}")
        return []


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
    """Aggregate related searches + PAA across seeds, tracking which trigger an
    AI Overview. Uses Serper when available; otherwise (or when a Serper call
    fails / quota is exhausted) falls back per-seed to free Google autocomplete.

    Returns {"related","paa","ai_overview","provider"}.
    """
    related, paa, ai_overview = set(), set(), set()
    used_serper = False
    for q in [s for s in seeds if s][:max_seeds]:
        data = serper_search(q)
        if data:
            used_serper = True
            ex = _extract(data)
            related.update(ex["related"])
            paa.update(ex["paa"])
            if ex["ai_overview"]:
                ai_overview.add(q)
            continue
        # Serper unavailable/failed for this seed → free keyless fallback
        for mod in _AC_MODIFIERS:
            related.update(google_autocomplete(q + mod))
    return {
        "related": sorted(related), "paa": sorted(paa), "ai_overview": sorted(ai_overview),
        "provider": "serper" if used_serper else "autocomplete",
    }


def get_keyword_research_block(seeds: List[str], max_seeds: int = 8) -> str:
    """Prompt-ready block of live query discovery. Works with Serper OR the free
    autocomplete fallback. '' if there are no seeds / nothing found."""
    res = discover_related_queries(seeds, max_seeds=max_seeds)
    if not (res["related"] or res["paa"]):
        return ""

    src = "Serper SERP" if res.get("provider") == "serper" else "Google Autocomplete (free)"
    lines = [f"KEYWORD RESEARCH (live via {src}) — mine these real searches for topics:"]
    if res["related"]:
        lines.append("Related / suggested searches:")
        lines += [f"  • {q}" for q in res["related"][:20]]
    if res["paa"]:
        lines.append("People Also Ask (ideal for FAQ sections / long-tail articles):")
        lines += [f"  • {q}" for q in res["paa"][:15]]
    if res["ai_overview"]:
        lines.append("Queries that trigger Google AI Overviews "
                     "(PRIORITISE GEO-optimised formats — direct-answer openers, structured data):")
        lines += [f"  • {q}" for q in res["ai_overview"][:10]]
    return "\n".join(lines)
