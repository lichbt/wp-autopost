import os
import sys
import json
import sqlite3
import pytest
from pathlib import Path
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables before importing config
os.environ["DATABASE_PATH"] = ":memory:"  # Use in-memory DB for tests
os.environ["DRY_RUN"] = "true"  # Never shell out to the real claude CLI in tests
os.environ["OPENAI_API_KEY"] = ""
os.environ["ENCRYPTION_KEY"] = "OxcT9c_vLCJZFkSz6Ke_53sxqO2S3AwMDHpP7xzCRwE="

from database import init_db, get_db_connection, add_site, add_plan, add_topics_bulk, reset_memory_db


@pytest.fixture
def db_conn():
    """Create a fresh in-memory database for each test."""
    # Reset the memory connection to get a clean database
    reset_memory_db()
    
    # Initialize schema
    init_db()
    
    conn = get_db_connection()
    yield conn
    # Don't close - let reset_memory_db handle it


@pytest.fixture
def sample_site(db_conn):
    """Create a sample site for testing."""
    cursor = db_conn.cursor()
    
    # Insert site with encrypted password
    from database import encrypt_password
    encrypted_pw = encrypt_password("test-password")
    
    cursor.execute("""
        INSERT INTO sites (name, wp_url, wp_username, wp_app_password, blog_template,
                          default_category, default_author, posts_per_day)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Test Site",
        "https://test.example.com",
        "admin",
        encrypted_pw,
        "<article><h1>{{title}}</h1>{{content}}</article>",
        1,
        1,
        2
    ))
    
    site_id = cursor.lastrowid
    db_conn.commit()
    
    return site_id


@pytest.fixture
def sample_plan(db_conn, sample_site):
    """Create a sample plan with topics for testing."""
    cursor = db_conn.cursor()
    
    raw_markdown = """# Content Strategy
    
## Phase 1 Topics
- Best Dating Apps
- How to Create a Dating App
"""
    
    extracted_json = json.dumps({
        "topics": [
            {
                "title": "Best Dating Apps in 2026",
                "pillar": "Comparisons",
                "priority": "high",
                "intent": "commercial",
                "target_keywords": ["best dating apps", "dating app comparison"],
                "internal_links": ["https://example.com/features"],
                "special_instructions": "Include comparison table",
                "scheduled_date": date.today().isoformat()
            },
            {
                "title": "How to Create a Dating App",
                "pillar": "How-To",
                "priority": "medium",
                "intent": "informational",
                "target_keywords": ["create dating app", "build dating app"],
                "internal_links": ["https://example.com/demo"],
                "special_instructions": None,
                "scheduled_date": (date.today() + timedelta(days=7)).isoformat()
            }
        ],
        "global": {
            "default_pillar_template_hints": {
                "Comparisons": "Use comparison tables",
                "How-To": "Numbered steps"
            },
            "posts_per_month": 8,
            "overall_strategy_goal": "Test goal"
        }
    })
    
    # Insert plan
    cursor.execute("""
        INSERT INTO plans (site_id, raw_markdown, extracted_json)
        VALUES (?, ?, ?)
    """, (sample_site, raw_markdown, extracted_json))
    
    plan_id = cursor.lastrowid
    db_conn.commit()
    
    # Add topics
    topics_data = [
        {
            "title": "Best Dating Apps in 2026",
            "slug": "best-dating-apps-2026",
            "pillar": "Comparisons",
            "priority": "high",
            "intent": "commercial",
            "target_keywords": ["best dating apps", "dating app comparison"],
            "internal_links": ["https://example.com/features"],
            "special_instructions": "Include comparison table",
            "scheduled_date": date.today().isoformat()
        },
        {
            "title": "How to Create a Dating App",
            "slug": "how-to-create-dating-app",
            "pillar": "How-To",
            "priority": "medium",
            "intent": "informational",
            "target_keywords": ["create dating app", "build dating app"],
            "internal_links": ["https://example.com/demo"],
            "special_instructions": None,
            "scheduled_date": (date.today() + timedelta(days=7)).isoformat()
        }
    ]
    
    add_topics_bulk(sample_site, plan_id, topics_data)
    
    return plan_id


@pytest.fixture
def sample_topics(sample_plan):
    """Get the sample topics data."""
    from database import get_topics_by_plan
    return get_topics_by_plan(sample_plan)


@pytest.fixture
def mock_openai_response(mocker):
    """Mock OpenAI API responses."""
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "topics": [
            {
                "title": "Test Topic",
                "pillar": "How-To",
                "priority": "medium",
                "intent": "informational",
                "target_keywords": ["test keyword"],
                "internal_links": [],
                "special_instructions": None,
                "scheduled_date": None
            }
        ],
        "global": {
            "default_pillar_template_hints": {"How-To": "Steps"},
            "posts_per_month": 8,
            "overall_strategy_goal": "Test"
        }
    })
    
    return mock_response
