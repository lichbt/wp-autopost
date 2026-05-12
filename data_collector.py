"""
GSC (Google Search Console) and GA4 (Google Analytics 4) data ingestion.

Requires a Google service account JSON with:
  - Search Console API: 'https://www.googleapis.com/auth/webmasters.readonly'
  - Google Analytics Data API: 'https://www.googleapis.com/auth/analytics.readonly'

Set GOOGLE_SERVICE_ACCOUNT_JSON in .env to the path of the key file.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

from config import GOOGLE_SERVICE_ACCOUNT_JSON, GSC_DAYS_LOOKBACK
from database import upsert_gsc_data, upsert_ga4_data, get_site
from logger import logger

_GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
_GA4_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def _get_credentials(scopes: List[str]):
    """Return google-auth Credentials from the service account JSON file."""
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON not set in .env. "
            "Point it to your service account key file."
        )
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_JSON, scopes=scopes
    )


# ── Google Search Console ─────────────────────────────────────────────────────

def fetch_gsc_data(site_id: int, gsc_url: str, days: int = None) -> int:
    """
    Pull query+page data from Search Console for the last N days and store in DB.

    Returns number of rows fetched.
    """
    if days is None:
        days = GSC_DAYS_LOOKBACK

    try:
        from googleapiclient.discovery import build
        credentials = _get_credentials(_GSC_SCOPES)
        service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    except ImportError:
        raise ImportError(
            "google-api-python-client not installed. Run: pip install google-api-python-client"
        )

    end_date = date.today() - timedelta(days=3)  # GSC has ~3 day lag
    start_date = end_date - timedelta(days=days)

    logger.info(f"Fetching GSC data for {gsc_url} ({start_date} → {end_date})")

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
        response = (
            service.searchanalytics()
            .query(siteUrl=gsc_url, body=body)
            .execute()
        )
        batch = response.get("rows", [])
        if not batch:
            break

        for row in batch:
            keys = row.get("keys", ["", ""])
            all_rows.append({
                "query": keys[0] if len(keys) > 0 else "",
                "page": keys[1] if len(keys) > 1 else "",
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": float(row.get("ctr", 0.0)),
                "position": float(row.get("position", 0.0)),
            })

        if len(batch) < row_limit:
            break
        start_row += row_limit

    today_str = date.today().isoformat()
    upsert_gsc_data(site_id, today_str, all_rows)
    logger.info(f"GSC: stored {len(all_rows)} rows for site {site_id}")
    return len(all_rows)


# ── Google Analytics 4 ────────────────────────────────────────────────────────

def fetch_ga4_data(site_id: int, ga4_property_id: str, days: int = 30) -> int:
    """
    Pull page-level session data from GA4 for the last N days and store in DB.

    Returns number of rows fetched.
    """
    if not ga4_property_id:
        logger.warning(f"No GA4 property ID configured for site {site_id}, skipping.")
        return 0

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest,
        )
        from google.oauth2 import service_account
    except ImportError:
        raise ImportError(
            "google-analytics-data not installed. Run: pip install google-analytics-data"
        )

    credentials = _get_credentials(_GA4_SCOPES)
    client = BetaAnalyticsDataClient(credentials=credentials)

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    logger.info(f"Fetching GA4 data for property {ga4_property_id} ({start_date} → {end_date})")

    property_name = f"properties/{ga4_property_id}"
    request = RunReportRequest(
        property=property_name,
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
            "page_path": row.dimension_values[0].value,
            "sessions": int(row.metric_values[0].value or 0),
            "pageviews": int(row.metric_values[1].value or 0),
            "bounce_rate": float(row.metric_values[2].value or 0.0),
            "avg_session_duration": float(row.metric_values[3].value or 0.0),
            "new_users": int(row.metric_values[4].value or 0),
        })

    today_str = date.today().isoformat()
    upsert_ga4_data(site_id, today_str, all_rows)
    logger.info(f"GA4: stored {len(all_rows)} rows for site {site_id}")
    return len(all_rows)


# ── Convenience: fetch both for a site ───────────────────────────────────────

def collect_site_data(site_id: int) -> Dict:
    """
    Fetch fresh GSC + GA4 data for a site and store in DB.
    Safe to call even if Google credentials aren't configured — logs warnings.
    """
    site = get_site(site_id)
    if not site:
        logger.error(f"Site {site_id} not found")
        return {"gsc_rows": 0, "ga4_rows": 0}

    gsc_rows = 0
    ga4_rows = 0

    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        logger.warning(
            "GOOGLE_SERVICE_ACCOUNT_JSON not set — skipping data collection. "
            "The plan generator will work from existing DB data or skip analytics context."
        )
        return {"gsc_rows": 0, "ga4_rows": 0}

    gsc_url = site.get("gsc_url", "")
    if gsc_url:
        try:
            gsc_rows = fetch_gsc_data(site_id, gsc_url)
        except Exception as e:
            logger.warning(f"GSC fetch failed for site {site_id}: {e}")
    else:
        logger.warning(f"No GSC URL configured for site {site_id}")

    ga4_property_id = site.get("ga4_property_id", "")
    if ga4_property_id:
        try:
            ga4_rows = fetch_ga4_data(site_id, ga4_property_id)
        except Exception as e:
            logger.warning(f"GA4 fetch failed for site {site_id}: {e}")
    else:
        logger.warning(f"No GA4 property ID configured for site {site_id}")

    return {"gsc_rows": gsc_rows, "ga4_rows": ga4_rows}
