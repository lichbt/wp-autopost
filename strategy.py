#!/usr/bin/env python3
"""
strategy.py — Article Scoring & Strategy Memo CLI
==================================================
Score published articles using GSC/GA4 data and generate
LLM-written weekly strategy memos.

Usage:
    python strategy.py --site 2 --score              # score all articles
    python strategy.py --site 2 --report             # print top/bottom performers
    python strategy.py --site 2 --memo               # generate strategy memo
    python strategy.py --site 2 --score --report     # score then show report
    python strategy.py --site 2 --score --memo --out memos/weekly_2026-06-08.md
    python strategy.py --site 4 --score --report     # ShaunSocial
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import ensure_directories
from database import init_db, get_site
from logger import logger


def _print_report(performers: dict):
    """Pretty-print the top/bottom performers table."""
    print(f"\n{'='*72}")
    print(f"  {'Score':>6}  {'Tier':<16}  {'Pillar':<20}  {'Persona':<20}  Title")
    print(f"  {'-'*68}")

    print("\n  ── TOP PERFORMERS ──")
    for t in performers["top"]:
        score   = f"{t['performance_score']:.1f}" if t.get("performance_score") is not None else "  —  "
        tier    = t.get("score_tier", "—")
        pillar  = (t.get("pillar") or "—")[:19]
        persona = (t.get("writing_persona") or "—")[:19]
        title   = t.get("title", "")[:38]
        print(f"  {score:>6}  {tier:<16}  {pillar:<20}  {persona:<20}  {title}")

    print("\n  ── BOTTOM PERFORMERS ──")
    for t in performers["bottom"]:
        score   = f"{t['performance_score']:.1f}" if t.get("performance_score") is not None else "  —  "
        tier    = t.get("score_tier", "—")
        pillar  = (t.get("pillar") or "—")[:19]
        persona = (t.get("writing_persona") or "—")[:19]
        title   = t.get("title", "")[:38]
        print(f"  {score:>6}  {tier:<16}  {pillar:<20}  {persona:<20}  {title}")

    print(f"{'='*72}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Content strategy scoring and weekly memo generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python strategy.py --site 2 --score --report
  python strategy.py --site 4 --score
  python strategy.py --site 2 --memo --out memos/weekly_$(date +%Y%m%d).md
  python strategy.py --site 2 --score --memo
        """,
    )
    parser.add_argument("--site",   type=int, required=True,
                        help="Site ID (2=MooDatingScript, 4=ShaunSocial)")
    parser.add_argument("--score",  action="store_true",
                        help="Score all published/draft topics using GSC data")
    parser.add_argument("--report", action="store_true",
                        help="Print top and bottom performers table")
    parser.add_argument("--memo",   action="store_true",
                        help="Generate weekly strategy memo via the claude CLI")
    parser.add_argument("--personas", action="store_true",
                        help="Show per-persona average score + sample count (the persona feedback loop)")
    parser.add_argument("--suggest-templates", action="store_true",
                        help="Propose NEW content templates from performance data (saved to templates/proposed/ for review)")
    parser.add_argument("--max-proposals", type=int, default=3,
                        help="Max template proposals to generate (default: 3)")
    parser.add_argument("--days",   type=int, default=60,
                        help="GSC lookback window in days (default: 60)")
    parser.add_argument("--out",    type=str, default="",
                        help="Save memo to this file path (optional)")
    parser.add_argument("--top",    type=int, default=5,
                        help="Number of top/bottom articles to show in report (default: 5)")
    args = parser.parse_args()

    ensure_directories()
    init_db()

    site = get_site(args.site)
    if not site:
        print(f"Error: Site {args.site} not found in database.")
        sys.exit(1)

    site_name = site.get("name", f"site {args.site}")
    print(f"\nSite: {site_name} (id={args.site})")

    from content_strategist import (
        score_all_topics,
        get_top_and_bottom_performers,
        generate_strategy_memo,
        get_persona_performance,
        suggest_templates,
    )

    if not (args.score or args.report or args.memo or args.personas or args.suggest_templates):
        parser.print_help()
        sys.exit(0)

    # ── Score ──────────────────────────────────────────────────────────────────
    if args.score:
        print(f"\nScoring articles (last {args.days} days of GSC data)...")
        stats = score_all_topics(args.site, days=args.days)
        print(
            f"  Scored:       {stats.get('scored', 0)}\n"
            f"  No GSC data:  {stats.get('no_data', 0)}\n"
            f"  top_performer {stats.get('top_performer', 0)}\n"
            f"  rising        {stats.get('rising', 0)}\n"
            f"  stalled       {stats.get('stalled', 0)}\n"
            f"  declining     {stats.get('declining', 0)}"
        )

    # ── Report ─────────────────────────────────────────────────────────────────
    if args.report:
        performers = get_top_and_bottom_performers(args.site, n=args.top)
        if not performers["top"] and not performers["bottom"]:
            print("\nNo scored articles found. Run --score first.")
        else:
            _print_report(performers)

    # ── Memo ───────────────────────────────────────────────────────────────────
    if args.memo:
        print("\nGenerating strategy memo...")
        try:
            memo = generate_strategy_memo(args.site)
            print(f"\n{'='*72}")
            print(memo)
            print(f"{'='*72}\n")

            if args.out:
                out_path = Path(args.out)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(memo, encoding="utf-8")
                print(f"Memo saved → {out_path}")

        except RuntimeError as exc:
            print(f"\nError: {exc}")
            sys.exit(1)

    # ── Persona performance ──────────────────────────────────────────────────────
    if args.personas:
        perf = get_persona_performance(args.site)
        if not perf:
            print("\nNo scored articles with a persona yet. Run --score first "
                  "(selection uses round-robin rotation until then).")
        else:
            ranked = sorted(perf.items(), key=lambda kv: kv[1]["avg_score"], reverse=True)
            print(f"\n  {'Persona':<22} {'Avg score':>10} {'Articles':>9}")
            print(f"  {'-'*42}")
            for name, s in ranked:
                print(f"  {name:<22} {s['avg_score']:>10.1f} {s['count']:>9}")
            print("\n  (Selection exploits the top personas and explores under-sampled ones.)")

    # ── Suggest templates ────────────────────────────────────────────────────────
    if args.suggest_templates:
        print("\nAnalysIng performance data to propose new content templates...")
        try:
            result = suggest_templates(args.site, max_proposals=args.max_proposals)
        except RuntimeError as exc:
            print(f"\nError: {exc}")
            sys.exit(1)

        if result.get("skipped"):
            print(f"  {result['skipped']}")
        elif not result["proposals"]:
            print("  No new templates proposed.")
        else:
            print(f"\n  {len(result['proposals'])} template(s) proposed → {result['saved_to']}")
            print("  (Review each, then move it up into templates/ to activate.)\n")
            for p in result["proposals"]:
                print(f"  • {p['name']}")
                print(f"      when:  {p['when_to_use']}")
                print(f"      why:   {p['rationale']}")
                print(f"      file:  {p['path']}\n")


if __name__ == "__main__":
    main()
