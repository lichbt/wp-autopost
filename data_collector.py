"""
GSC (Google Search Console) and GA4 (Google Analytics 4) data ingestion.

Supports two auth methods (tries OAuth first):

Option A — OAuth 2.0 (recommended):
  1. Create OAuth client ID (Desktop app) in Google Cloud Console
  2. Download JSON → save as credentials/oauth_client.json
  3. Set in .env:
       GOOGLE_OAUTH_CLIENT=credentials/oauth_client.json
       GOOGLE_TOKEN_FILE=credentials/google_token.json
  4. First run opens a browser for one-time login. Token saved for all future runs.

Option B — Service account:
  1. Create service account + JSON key
  2. Add service account email as user in GSC + GA4 (requires property Owner access)
  3. Set in .env:
       GOOGLE_SERVICE_ACCOUNT_JSON=credentials/google-service-account.json
"""

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    GOOGLE_OAUTH_CLIENT, GOOGLE_TOKEN_FILE,
    GOOGLE_SERVICE_ACCOUNT_JSON, GSC_DAYS_LOOKBACK,
)
from database import upsert_gsc_data, upsert_ga4_data, get_site
from logger import logger

_SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]


def _get_credentials():
    """
    Return Google credentials using OAuth (preferred) or service account.

    OAuth: opens browser on first run, saves token to GOOGLE_TOKEN_FILE.
    Subsequent runs use the saved token silently.
    """
    # ── Option A: OAuth 2.0 ───────────────────────────────────────────────────
    oauth_client = Path(GOOGLE_OAUTH_CLIENT)
    token_file = Path(GOOGLE_TOKEN_FILE)

    if oauth_client.exists():
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

            creds = None
            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), _SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    logger.info("Google OAuth token refreshed")
                else:
                    logger.info("Opening browser for Google OAuth login (one-time)...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(oauth_client), _SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth login successful")

                # Save token for next run
                token_file.parent.mkdir(parents=True, exist_ok=True)
                token_file.write_text(creds.to_json())
                logger.info(f"Token saved to {token_file}")

            return creds

        except ImportError:
            raise ImportError(
                "Missing OAuth library. Run: pip install google-auth-oauthlib"
            )

    # ── Option B: Service account ─────────────────────────────────────────────
    if GOOGLE_SERVICE_ACCOUNT_JSON and Path(GOOGLE_SERVICE_ACCOUNT_JSON).exists():
        try:
            from google.oauth2 import service_account
            return service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_JSON, scopes=_SCOPES
            )
        except ImportError:
            raise ImportError(
                "Missing google-auth library. Run: pip install google-auth"
            )

    raise ValueError(
        "No Google credentials found.\n"
        "Option A (recommended): set GOOGLE_OAUTH_CLIENT=credentials/oauth_client.json\n"
        "Option B: set GOOGLE_SERVICE_ACCOUNT_JSON=credentials/google-service-account.json"
    )


# ── Google Search Console ─────────────────────────────────────────────────────

def fetch_gsc_data(site_id: int, gsc_url: str, days: int = None) -> int:
    """Pull query+page data from Search Console and store in DB. Returns row count."""
    if days is None:
        days = GSC_DAYS_LOOKBACK

    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Run: pip install google-api-python-client"
        )

    creds = _get_credentials()
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    end_date = date.today() - timedelta(days=3)  # GSC has ~3 day lag
    start_date = end_date - timedelta(days=days)

    logger.info(f"Fetching GSC: {gsc_url} ({start_date} → {end_date})")

    all_rows: List[Dict] = []
    start_row = 0
    row_limit = 25000

    while True:
        body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["query", "page"],
            "rowLimit": row_limit,
            "startRow": start_row,
        }
        response = service.searchanalytics().query(siteUrl=gsc_url, body=body).execute()
        batch = response.get("rows", [])
        if not batch:
            break

        for row in batch:
            keys = row.get("keys", ["", ""])
            all_rows.append({
                "query":       keys[0] if len(keys) > 0 else "",
                "page":        keys[1] if len(keys) > 1 else "",
                "clicks":      int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr":         float(row.get("ctr", 0.0)),
                "position":    float(row.get("position", 0.0)),
            })

        if len(batch) < row_limit:
            break
        start_row += row_limit

    upsert_gsc_data(site_id, date.today().isoformat(), all_rows)
    logger.info(f"GSC: stored {len(all_rows)} rows for site {site_id}")
    return len(all_rows)


# ── Google Analytics 4 ────────────────────────────────────────────────────────

def fetch_ga4_data(site_id: int, ga4_property_id: str, days: int = 30) -> int:
    """Pull page-level session data from GA4 and store in DB. Returns row count."""
    if not ga4_property_id:
        logger.warning(f"No GA4 property ID for site {site_id}, skipping.")
        return 0

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest,
        )
    except ImportError:
        raise ImportError(
            "Run: pip install google-analytics-data"
        )

    creds = _get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    logger.info(f"Fetching GA4: property {ga4_property_id} ({start_date} → {end_date})")

    request = RunReportRequest(
        property=f"properties/{ga4_property_id}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="newUsers"),
        ],
        date_ranges=[DateRange(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )],
        limit=1000,
    )

    response = client.run_report(request)

    all_rows: List[Dict] = []
    for row in response.rows:
        all_rows.append({
            "page_path":           row.dimension_values[0].value,
            "sessions":            int(row.metric_values[0].value or 0),
            "pageviews":           int(row.metric_values[1].value or 0),
            "bounce_rate":         float(row.metric_values[2].value or 0.0),
            "avg_session_duration":float(row.metric_values[3].value or 0.0),
            "new_users":           int(row.metric_values[4].value or 0),
        })

    upsert_ga4_data(site_id, date.today().isoformat(), all_rows)
    logger.info(f"GA4: stored {len(all_rows)} rows for site {site_id}")
    return len(all_rows)


# ── Convenience ───────────────────────────────────────────────────────────────

def collect_site_data(site_id: int) -> Dict:
    """Fetch fresh GSC + GA4 data for a site. Safe to call without credentials."""
    site = get_site(site_id)
    if not site:
        logger.error(f"Site {site_id} not found")
        return {"gsc_rows": 0, "ga4_rows": 0}

    oauth_exists = Path(GOOGLE_OAUTH_CLIENT).exists()
    sa_exists = bool(GOOGLE_SERVICE_ACCOUNT_JSON) and Path(GOOGLE_SERVICE_ACCOUNT_JSON).exists()

    if not oauth_exists and not sa_exists:
        logger.warning(
            "No Google credentials configured. Skipping data collection.\n"
            "Set GOOGLE_OAUTH_CLIENT or GOOGLE_SERVICE_ACCOUNT_JSON in .env"
        )
        return {"gsc_rows": 0, "ga4_rows": 0}

    gsc_rows, ga4_rows = 0, 0

    gsc_url = site.get("gsc_url", "")
    if gsc_url:
        try:
            gsc_rows = fetch_gsc_data(site_id, gsc_url)
        except Exception as e:
            logger.warning(f"GSC fetch failed: {e}")
    else:
        logger.warning(f"No GSC URL for site {site_id}. Set GSC_SITE_URL_SITE{site_id} in .env")

    ga4_id = site.get("ga4_property_id", "")
    if ga4_id:
        try:
            ga4_rows = fetch_ga4_data(site_id, ga4_id)
        except Exception as e:
            logger.warning(f"GA4 fetch failed: {e}")
    else:
        logger.warning(f"No GA4 property ID for site {site_id}. Set GA4_PROPERTY_ID_SITE{site_id} in .env")

    return {"gsc_rows": gsc_rows, "ga4_rows": ga4_rows}
