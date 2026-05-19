"""
GEO (Generative Engine Optimization) monitoring.

Two modes:
  1. Manual logging — record when you spot your content cited in an AI answer
  2. Perplexity probe — automatically query Perplexity API and check if your URLs appear

Usage via main.py:
  python main.py --geo-log   --site 1          # interactive log a sighting
  python main.py --geo-probe --site 1          # auto-probe top GSC queries
  python main.py --geo-report --site 1         # show sighting stats
"""

import sys
from collections import Counter
from datetime import date
from typing import Dict, List, Optional

from config import PERPLEXITY_API_KEY, DRY_RUN
from database import (
    get_site, add_geo_sighting, get_geo_sightings, get_geo_stats,
    get_gsc_summary, list_sites,
)
from logger import logger

SOURCES = ["chatgpt", "perplexity", "gemini", "claude", "copilot", "other"]

# ── ANSI helpers ──────────────────────────────────────────────────────────────

def _c(text, code): return f"\033[{code}m{text}\033[0m"
BOLD   = lambda t: _c(t, "1")
GREEN  = lambda t: _c(t, "32")
CYAN   = lambda t: _c(t, "36")
YELLOW = lambda t: _c(t, "33")
DIM    = lambda t: _c(t, "2")
RED    = lambda t: _c(t, "31")


# ── Manual logging ────────────────────────────────────────────────────────────

def interactive_log_sighting(site_id: int):
    """CLI wizard to log a GEO sighting."""
    site = get_site(site_id)
    if not site:
        print(RED(f"Site {site_id} not found."))
        sys.exit(1)

    print(f"\n{BOLD('Log GEO Sighting')} — {CYAN(site['name'])}")
    print("─"*50)
    print(DIM("Press Ctrl+C to cancel.\n"))

    try:
        query = input("Query you searched in the AI tool: ").strip()
        if not query:
            print(RED("Query required."))
            return

        url = input("Your URL that was cited: ").strip()
        if not url:
            print(RED("URL required."))
            return

        print(f"Source: {', '.join(f'{i+1}={s}' for i,s in enumerate(SOURCES))}")
        source_input = input("Source number or name: ").strip().lower()
        if source_input.isdigit() and 1 <= int(source_input) <= len(SOURCES):
            source = SOURCES[int(source_input) - 1]
        elif source_input in SOURCES:
            source = source_input
        else:
            source = "other"

        pillar = input("Content pillar (e.g. vs_comparison, best_of) [optional]: ").strip()
        notes = input("Notes [optional]: ").strip()

        spotted_at = date.today().isoformat()
        sighting_id = add_geo_sighting(
            site_id=site_id,
            query=query,
            url=url,
            source=source,
            spotted_at=spotted_at,
            notes=notes,
            pillar=pillar,
        )
        print(GREEN(f"\n✓ Sighting #{sighting_id} logged."))

    except KeyboardInterrupt:
        print("\nCancelled.")


# ── Perplexity probe ──────────────────────────────────────────────────────────

def _query_perplexity(query: str) -> Optional[str]:
    """Send a query to Perplexity (sonar model) and return the raw text response."""
    if not PERPLEXITY_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai",
        )
        response = client.chat.completions.create(
            model="sonar",
            messages=[
                {
                    "role": "system",
                    "content": "Answer the query concisely and factually. Include URLs of any software you recommend.",
                },
                {"role": "user", "content": query},
            ],
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Perplexity query failed: {e}")
        return None


def probe_perplexity(site_id: int, queries: Optional[List[str]] = None, limit: int = 10):
    """
    Run top GSC queries through Perplexity and check if site URL appears in answers.

    Automatically logs confirmed sightings.
    """
    site = get_site(site_id)
    if not site:
        print(RED(f"Site {site_id} not found."))
        sys.exit(1)

    site_url = site.get("wp_url", "").rstrip("/")
    site_name = site.get("name", f"Site {site_id}")

    if not PERPLEXITY_API_KEY:
        print(YELLOW(
            "PERPLEXITY_API_KEY not set in .env.\n"
            "Add it to enable automatic probing. Get a key at https://www.perplexity.ai/api"
        ))
        return

    # Use provided queries or pull from GSC
    if not queries:
        gsc = get_gsc_summary(site_id)
        top = gsc.get("top_queries", [])
        queries = [r["query"] for r in top[:limit] if r.get("query")]

    if not queries:
        print(YELLOW("No queries available. Run --fetch-data first or provide queries manually."))
        return

    print(f"\n{BOLD('Perplexity GEO Probe')} — {CYAN(site_name)}")
    print(f"Probing {len(queries)} queries...\n")

    citations = 0
    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {query[:60]}", end="", flush=True)

        if DRY_RUN:
            print(f"  {DIM('[DRY RUN]')}")
            continue

        answer = _query_perplexity(query)
        if answer is None:
            print(f"  {YELLOW('API error')}")
            continue

        if site_url in answer:
            print(f"  {GREEN('✓ CITED!')}")
            citations += 1
            add_geo_sighting(
                site_id=site_id,
                query=query,
                url=site_url,
                source="perplexity",
                spotted_at=date.today().isoformat(),
                notes=f"Auto-detected via probe. Answer excerpt: {answer[:200]}",
            )
        else:
            print(f"  {DIM('not cited')}")

    print(f"\n{GREEN(f'Citations found: {citations}/{len(queries)}')}")
    if citations:
        print(DIM("Sightings have been logged to geo_sightings table."))


# ── Report ────────────────────────────────────────────────────────────────────

def print_geo_report(site_id: int):
    """Print a summary of GEO sightings for a site."""
    site = get_site(site_id)
    if not site:
        print(RED(f"Site {site_id} not found."))
        sys.exit(1)

    sightings = get_geo_sightings(site_id)
    stats = get_geo_stats(site_id)

    print(f"\n{BOLD('GEO Report')} — {CYAN(site['name'])}")
    print("─"*50)
    print(f"Total sightings: {BOLD(str(len(sightings)))}")

    if not sightings:
        print(YELLOW("  No sightings logged yet."))
        print(DIM("  Use --geo-log to record manual sightings or --geo-probe to auto-detect."))
        return

    print(f"\n{BOLD('By Source:')}")
    for row in stats.get("by_source", []):
        bar = "█" * row["count"]
        print(f"  {row['source']:<12} {GREEN(bar)} {row['count']}")

    print(f"\n{BOLD('By Content Pillar:')}")
    for row in stats.get("by_pillar", []):
        bar = "█" * row["count"]
        print(f"  {row['pillar']:<20} {GREEN(bar)} {row['count']}")

    print(f"\n{BOLD('Recent Sightings:')}")
    for s in sightings[:10]:
        print(f"  {DIM(s['spotted_at'])}  [{CYAN(s['source'])}]  {s['query'][:50]}")
        print(f"    {DIM(s['url'])}")
        if s.get("notes"):
            print(f"    {DIM(s['notes'][:80])}")

    # GEO insight
    if stats.get("by_pillar"):
        top_pillar = stats["by_pillar"][0]["pillar"]
        print(f"\n{BOLD('Insight:')} Your best-performing GEO pillar is {GREEN(top_pillar)}.")
        print(DIM("  Prioritise more of this pillar type when generating your next plan."))

    print()
