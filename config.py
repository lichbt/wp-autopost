import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent

# Database & logging
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/blog_automation.db")
DB_FULL_PATH = PROJECT_ROOT / DATABASE_PATH
LOG_FILE = os.getenv("LOG_FILE", "logs/automation.log")
LOG_FULL_PATH = PROJECT_ROOT / LOG_FILE

# ── Claude (sole LLM backend, via the `claude` CLI) ───────────────────────────
# Writing + data-driven audits run through the local `claude` CLI using the
# user's logged-in session — no API key required, no OpenRouter.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_CONTENT_MODEL = os.getenv("CLAUDE_CONTENT_MODEL", "sonnet")
CLAUDE_ANALYSIS_MODEL = os.getenv("CLAUDE_ANALYSIS_MODEL", "sonnet")

import shutil as _shutil
CLAUDE_CLI_AVAILABLE = _shutil.which("claude") is not None

# Dry-run: explicit env var wins; otherwise auto-enable only when we have no way
# to generate (no claude CLI and no Anthropic key).
_dry_run_env = os.getenv("DRY_RUN", "").lower()
if _dry_run_env in ("true", "false"):
    DRY_RUN = _dry_run_env == "true"
else:
    DRY_RUN = not CLAUDE_CLI_AVAILABLE and not ANTHROPIC_API_KEY

# ── Google APIs ───────────────────────────────────────────────────────────────
# Option A (recommended): OAuth — authenticates as your own Google account
GOOGLE_OAUTH_CLIENT = os.getenv("GOOGLE_OAUTH_CLIENT", "credentials/oauth_client.json")
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "credentials/google_token.json")
# Option B: Service account (requires adding email to GSC/GA4 as user — often blocked)
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GSC_DAYS_LOOKBACK = int(os.getenv("GSC_DAYS_LOOKBACK", "90"))

# ── Perplexity (optional – GEO probing) ──────────────────────────────────────
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# ── Pixabay (featured image auto-fetch) ───────────────────────────────────────
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

# ── Encryption ────────────────────────────────────────────────────────────────
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# ── Scheduling defaults ───────────────────────────────────────────────────────
DEFAULT_CHECK_INTERVAL = 3600
DEFAULT_POSTS_PER_DAY = 2
MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]

# ── WordPress defaults ────────────────────────────────────────────────────────
DEFAULT_WP_STATUS = "draft"

# ── Sites directory ───────────────────────────────────────────────────────────
SITES_DIR = PROJECT_ROOT / "sites"


def get_wp_sites_from_env() -> list:
    """Load WordPress site configurations from environment variables."""
    sites = []
    i = 1
    while True:
        url = os.getenv(f"WP_URL_SITE{i}")
        if not url:
            break
        username = os.getenv(f"WP_USERNAME_SITE{i}", "")
        password = os.getenv(f"WP_PASSWORD_SITE{i}", "")
        posts_per_day = int(os.getenv(f"WP_POSTS_PER_DAY_SITE{i}", "2"))
        name = os.getenv(f"WP_NAME_SITE{i}", f"Site {i}")
        gsc_url = os.getenv(f"GSC_SITE_URL_SITE{i}", url.rstrip("/") + "/")
        ga4_property_id = os.getenv(f"GA4_PROPERTY_ID_SITE{i}", "")
        if username and password:
            sites.append({
                "name": name,
                "wp_url": url.rstrip("/"),
                "wp_username": username,
                "wp_app_password": password,
                "posts_per_day": posts_per_day,
                "gsc_url": gsc_url,
                "ga4_property_id": ga4_property_id,
                "env_index": i,
            })
        i += 1
    return sites


def ensure_directories():
    """Create necessary directories if they don't exist."""
    DB_FULL_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_FULL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SITES_DIR.mkdir(parents=True, exist_ok=True)
