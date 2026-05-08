#!/usr/bin/env python3
"""
AI Content Strategy Automation for WordPress
Main entry point with CLI interface
"""

import argparse
import sys
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import ensure_directories, DRY_RUN, DEFAULT_CHECK_INTERVAL
from database import init_db
from logger import logger


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="AI Content Strategy Automation for WordPress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --add-site              Add a new WordPress site interactively
  %(prog)s --sync-env              Sync sites from .env variables
  %(prog)s --list-sites            List all configured sites
  %(prog)s --site 1 --import-plan strategy.md   Import a content plan
  %(prog)s --site 1 --run-once     Run one automation cycle
  %(prog)s --site 1 --daemon       Run continuously (hourly checks)
        """
    )
    
    # Site management
    parser.add_argument("--add-site", action="store_true",
                       help="Add a new WordPress site interactively")
    parser.add_argument("--sync-env", action="store_true",
                       help="Sync WordPress sites from .env variables")
    parser.add_argument("--list-sites", action="store_true",
                       help="List all configured sites")
    parser.add_argument("--list-templates", action="store_true",
                       help="List available blog templates")
    
    # Plan import
    parser.add_argument("--site", type=int, help="Site ID to operate on")
    parser.add_argument("--import-plan", type=str, metavar="FILE",
                       help="Import a content strategy plan (supports .md, .txt, .docx, .pdf)")
    
    # Execution modes
    parser.add_argument("--run-once", action="store_true",
                       help="Run one automation cycle and exit")
    parser.add_argument("--daemon", action="store_true",
                       help="Run continuously with hourly checks")
    parser.add_argument("--interval", type=int, default=DEFAULT_CHECK_INTERVAL,
                       help=f"Check interval in seconds (default: {DEFAULT_CHECK_INTERVAL})")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Log dry-run mode
    if DRY_RUN:
        logger.info("Running in DRY RUN mode (no API keys configured)")
    
    # Auto-sync sites from env on startup
    from sites import sync_sites_from_env
    env_site_ids = sync_sites_from_env()
    if env_site_ids:
        logger.info(f"Synced {len(env_site_ids)} site(s) from environment variables")
    
    # Handle commands
    if args.add_site:
        from sites import create_site_interactively
        create_site_interactively()
        
    elif args.sync_env:
        # Already synced above, just show results
        from sites import list_all_sites
        list_all_sites()
        
    elif args.list_sites:
        from sites import list_all_sites
        list_all_sites()
        
    elif args.list_templates:
        from content_generator import load_template, TEMPLATES_DIR
        print("\n=== Available Blog Templates ===\n")
        if TEMPLATES_DIR.exists():
            for f in sorted(TEMPLATES_DIR.glob("*.md")):
                pillar_name = f.stem.replace("_", " ").title()
                print(f"  {pillar_name:<20} → {f.name}")
        print(f"\nTemplates location: {TEMPLATES_DIR}")
        print("Edit these files to customize how the LLM generates articles.")
        
    elif args.site and args.import_plan:
        from plan_parser import import_plan
        from file_reader import read_plan_file
        
        # Read the plan file (supports .md, .txt, .docx, .pdf)
        plan_path = Path(args.import_plan)
        if not plan_path.exists():
            logger.error(f"Plan file not found: {args.import_plan}")
            sys.exit(1)
        
        try:
            raw_markdown = read_plan_file(args.import_plan)
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)
        
        logger.info(f"Importing plan from {args.import_plan}...")
        plan_id = import_plan(args.site, raw_markdown)
        logger.info(f"Plan imported successfully! Plan ID: {plan_id}")
        
    elif args.site and args.run_once:
        from scheduler import run_automation_cycle
        
        logger.info(f"Running automation cycle for site {args.site}...")
        processed = run_automation_cycle(args.site)
        logger.info(f"Cycle complete. {processed} topics processed.")
        
    elif args.site and args.daemon:
        from scheduler import run_automation_cycle
        
        logger.info(f"Starting daemon mode for site {args.site} (interval: {args.interval}s)")
        
        while True:
            try:
                logger.info("--- Starting automation cycle ---")
                processed = run_automation_cycle(args.site)
                logger.info(f"Cycle complete. {processed} topics processed.")
            except KeyboardInterrupt:
                logger.info("Daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Cycle failed: {e}")
            
            logger.info(f"Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
