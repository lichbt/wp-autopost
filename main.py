#!/usr/bin/env python3
"""
AI Content Strategy Automation for WordPress — v2
Claude-powered pipeline with GSC/GA4 integration, GEO optimization, and interactive plan generation.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import ensure_directories, DRY_RUN, DEFAULT_CHECK_INTERVAL
from database import init_db
from logger import logger


def main():
    parser = argparse.ArgumentParser(
        description="AI Content Automation — Claude + GSC + GA4 + GEO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --add-site                              Add a WordPress site interactively
  %(prog)s --list-sites                            List all configured sites
  %(prog)s --site 1 --generate-plan               Generate plan interactively (Claude + data)
  %(prog)s --site 1 --generate-plan --topics 60   Generate 60-topic plan
  %(prog)s --site 1 --import-plan strategy.md     Import a plan from a file
  %(prog)s --site 1 --fetch-data                  Refresh GSC + GA4 data from APIs
  %(prog)s --site 1 --run-once                    Run one publish cycle
  %(prog)s --site 1 --daemon                      Run continuously (hourly)
  %(prog)s --site 1 --geo-log                     Log a GEO citation sighting
  %(prog)s --site 1 --geo-probe                   Auto-probe Perplexity for citations
  %(prog)s --site 1 --geo-report                  Show GEO citation report
        """,
    )

    # Site management
    parser.add_argument("--add-site", action="store_true", help="Add a WordPress site interactively")
    parser.add_argument("--sync-env", action="store_true", help="Sync WordPress sites from .env variables")
    parser.add_argument("--list-sites", action="store_true", help="List all configured sites")
    parser.add_argument("--list-templates", action="store_true", help="List available blog templates")

    # Site selector
    parser.add_argument("--site", type=int, help="Site ID to operate on")

    # Plan generation & import
    parser.add_argument(
        "--generate-plan", action="store_true",
        help="Launch interactive plan generator (Claude + GSC + GA4 data)",
    )
    parser.add_argument(
        "--topics", type=int, default=30,
        help="Number of topics to generate (default: 30)",
    )
    parser.add_argument(
        "--no-fetch", action="store_true",
        help="Skip refreshing GSC/GA4 data before generating plan",
    )
    parser.add_argument(
        "--import-plan", type=str, metavar="FILE",
        help="Import a content strategy plan (.md, .txt, .docx, .pdf)",
    )

    # Data collection
    parser.add_argument(
        "--fetch-data", action="store_true",
        help="Fetch fresh GSC + GA4 data from Google APIs",
    )

    # Publishing
    parser.add_argument("--run-once", action="store_true", help="Run one automation cycle")
    parser.add_argument("--daemon", action="store_true", help="Run continuously (hourly)")
    parser.add_argument(
        "--interval", type=int, default=DEFAULT_CHECK_INTERVAL,
        help=f"Daemon check interval in seconds (default: {DEFAULT_CHECK_INTERVAL})",
    )

    # GEO monitoring
    parser.add_argument("--geo-log", action="store_true", help="Log a GEO citation sighting interactively")
    parser.add_argument("--geo-probe", action="store_true", help="Auto-probe Perplexity for citations")
    parser.add_argument("--geo-report", action="store_true", help="Show GEO citation stats")

    args = parser.parse_args()

    # Bootstrap
    ensure_directories()
    init_db()
    logger.info("Database initialized")

    if DRY_RUN:
        logger.info("Running in DRY RUN mode (no API keys configured)")

    # Auto-sync sites from .env on every startup
    from sites import sync_sites_from_env
    env_ids = sync_sites_from_env()
    if env_ids:
        logger.info(f"Synced {len(env_ids)} site(s) from environment variables")

    # ── Commands ──────────────────────────────────────────────────────────────

    if args.add_site:
        from sites import create_site_interactively
        create_site_interactively()

    elif args.sync_env:
        from sites import list_all_sites
        list_all_sites()

    elif args.list_sites:
        from sites import list_all_sites
        list_all_sites()

    elif args.list_templates:
        from content_generator import TEMPLATES_DIR
        print("\n=== Blog Templates ===\n")
        if TEMPLATES_DIR.exists():
            for f in sorted(TEMPLATES_DIR.glob("*.md")):
                print(f"  {f.stem:<24} → {f.name}")
        print(f"\nLocation: {TEMPLATES_DIR}\n")

    # ── Site-scoped commands ──────────────────────────────────────────────────

    elif args.site and args.fetch_data:
        from data_collector import collect_site_data
        print(f"Fetching data for site {args.site}...")
        result = collect_site_data(args.site)
        print(f"  GSC rows: {result['gsc_rows']}")
        print(f"  GA4 rows: {result['ga4_rows']}")

    elif args.site and args.generate_plan:
        from site_analyst import generate_plan_interactive
        generate_plan_interactive(
            site_id=args.site,
            num_topics=args.topics,
            fresh_data=not args.no_fetch,
        )

    elif args.site and args.import_plan:
        from plan_parser import import_plan
        from file_reader import read_plan_file
        plan_path = Path(args.import_plan)
        if not plan_path.exists():
            logger.error(f"File not found: {args.import_plan}")
            sys.exit(1)
        try:
            raw_markdown = read_plan_file(args.import_plan)
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)
        logger.info(f"Importing plan from {args.import_plan}...")
        plan_id = import_plan(args.site, raw_markdown)
        logger.info(f"Plan imported — ID: {plan_id}")

    elif args.site and args.run_once:
        from scheduler import run_automation_cycle
        logger.info(f"Running cycle for site {args.site}...")
        processed = run_automation_cycle(args.site)
        logger.info(f"Cycle complete: {processed} topics processed")

    elif args.site and args.daemon:
        from scheduler import run_automation_cycle
        logger.info(f"Daemon started for site {args.site} (interval: {args.interval}s)")
        while True:
            try:
                logger.info("─── Starting cycle ───")
                processed = run_automation_cycle(args.site)
                logger.info(f"Cycle done: {processed} topics processed")
            except KeyboardInterrupt:
                logger.info("Daemon stopped")
                break
            except Exception as e:
                logger.error(f"Cycle failed: {e}")
            logger.info(f"Sleeping {args.interval}s...")
            time.sleep(args.interval)

    elif args.site and args.geo_log:
        from geo_monitor import interactive_log_sighting
        interactive_log_sighting(args.site)

    elif args.site and args.geo_probe:
        from geo_monitor import probe_perplexity
        probe_perplexity(args.site)

    elif args.site and args.geo_report:
        from geo_monitor import print_geo_report
        print_geo_report(args.site)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
