import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/blog_automation.db")
DB_FULL_PATH = PROJECT_ROOT / DATABASE_PATH

# Logging configuration
LOG_FILE = os.getenv("LOG_FILE", "logs/automation.log")
LOG_FULL_PATH = PROJECT_ROOT / LOG_FILE

# OpenAI configuration (default)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o"

# OpenRouter configuration (alternative)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Generic LLM configuration (for 9router, OpenRouter, or any OpenAI-compatible provider)
LLM_API_KEY = os.getenv("LLM_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "") or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "") or os.getenv("OPENROUTER_MODEL", "") or os.getenv("OPENAI_MODEL", "gpt-4o")

# Determine which provider to use
USE_OPENROUTER = bool(LLM_API_KEY) and "openrouter" in LLM_BASE_URL

# Encryption key for WP passwords
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# Dry-run mode: auto-enabled when no API keys are configured
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true" or not LLM_API_KEY

# Scheduling defaults
DEFAULT_CHECK_INTERVAL = 3600  # seconds (1 hour)
DEFAULT_POSTS_PER_DAY = 2
MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]  # exponential backoff in seconds

# WordPress defaults
DEFAULT_WP_STATUS = "draft"  # 'draft' or 'publish'


def get_wp_sites_from_env() -> list:
    """
    Load WordPress site configurations from environment variables.
    
    Supports multiple sites: WP_URL_SITE1, WP_URL_SITE2, etc.
    
    Returns:
        List of site config dicts
    """
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
        
        if username and password:
            sites.append({
                "name": name,
                "wp_url": url.rstrip("/"),
                "wp_username": username,
                "wp_app_password": password,
                "posts_per_day": posts_per_day,
                "env_index": i
            })
        
        i += 1
    
    return sites


def ensure_directories():
    """Create necessary directories if they don't exist."""
    DB_FULL_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_FULL_PATH.parent.mkdir(parents=True, exist_ok=True)
