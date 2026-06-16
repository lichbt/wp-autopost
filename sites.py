from database import add_site, get_site, list_sites, get_db_connection
from config import get_wp_sites_from_env
from logger import logger

# Default blog template
DEFAULT_TEMPLATE = """<head>
<title>{{meta_title}}</title>
<meta name="description" content="{{meta_description}}">
</head>
<article>
<h1>{{title}}</h1>
<p><strong>TL;DR:</strong> {{tldr}}</p>
<div class="post-content">
{{content}}
</div>
<div class="faq">
<h2>Frequently Asked Questions</h2>
{{faq}}
</div>
{{faq_schema}}
<div class="cta">
<p><a href="{{cta_link}}">{{cta_text}}</a></p>
</div>
</article>"""


def sync_sites_from_env() -> list:
    """
    Sync WordPress sites from environment variables to database.
    
    Reads WP_URL_SITE1, WP_USERNAME_SITE1, WP_PASSWORD_SITE1, etc.
    Creates or updates sites in the database.
    
    Returns:
        List of site IDs
    """
    env_sites = get_wp_sites_from_env()
    
    if not env_sites:
        logger.info("No WordPress sites found in environment variables")
        return []
    
    site_ids = []
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for site_config in env_sites:
        # Check if site already exists by URL
        cursor.execute(
            "SELECT id FROM sites WHERE wp_url = ?",
            (site_config["wp_url"],)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing site
            site_id = existing["id"]
            from database import encrypt_password
            encrypted_pw = encrypt_password(site_config["wp_app_password"])

            cursor.execute("""
                UPDATE sites
                SET name = ?, wp_username = ?, wp_app_password = ?,
                    posts_per_day = ?, gsc_url = ?, ga4_property_id = ?,
                    platform = ?, content_repo_path = ?
                WHERE id = ?
            """, (
                site_config["name"],
                site_config["wp_username"],
                encrypted_pw,
                site_config["posts_per_day"],
                site_config.get("gsc_url", ""),
                site_config.get("ga4_property_id", ""),
                site_config.get("platform", "wordpress"),
                site_config.get("content_repo_path"),
                site_id,
            ))
            conn.commit()  # release the write lock before any add_site() (separate connection)
            logger.info(f"Updated site from env: {site_config['name']} (ID: {site_id})")
        else:
            # Create new site — non-WP sites skip the WP HTML template (assembler bypassed)
            platform = site_config.get("platform", "wordpress")
            site_id = add_site(
                name=site_config["name"],
                wp_url=site_config["wp_url"],
                wp_username=site_config["wp_username"],
                wp_app_password=site_config["wp_app_password"],
                blog_template=DEFAULT_TEMPLATE if platform == "wordpress" else "",
                posts_per_day=site_config["posts_per_day"],
                gsc_url=site_config.get("gsc_url", ""),
                ga4_property_id=site_config.get("ga4_property_id", ""),
                platform=platform,
                content_repo_path=site_config.get("content_repo_path"),
            )
            logger.info(f"Created site from env: {site_config['name']} (ID: {site_id})")
        
        site_ids.append(site_id)
    
    conn.commit()
    conn.close()
    
    return site_ids


def create_site_interactively():
    """Interactive CLI to add a new WordPress site."""
    print("\n=== Add New WordPress Site ===\n")
    
    name = input("Site name (e.g., 'My Blog'): ").strip()
    if not name:
        print("Error: Site name is required")
        return None
    
    wp_url = input("WordPress URL (e.g., https://example.com): ").strip().rstrip("/")
    if not wp_url:
        print("Error: WordPress URL is required")
        return None
    
    wp_username = input("WordPress username: ").strip()
    if not wp_username:
        print("Error: Username is required")
        return None
    
    wp_app_password = input("WordPress Application Password: ").strip()
    if not wp_app_password:
        print("Error: Application password is required")
        return None
    
    # Blog template
    print(f"\nDefault blog template (press Enter to use default):")
    print("---")
    print(DEFAULT_TEMPLATE[:200] + "..." if len(DEFAULT_TEMPLATE) > 200 else DEFAULT_TEMPLATE)
    print("---")
    
    use_default = input("Use default template? (Y/n): ").strip().lower()
    if use_default == "n":
        print("Enter your HTML template (end with empty line):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        blog_template = "\n".join(lines)
    else:
        blog_template = DEFAULT_TEMPLATE
    
    # Category and author
    try:
        default_category = int(input("Default category ID [1]: ").strip() or "1")
    except ValueError:
        default_category = 1
    
    try:
        default_author = int(input("Default author ID [1]: ").strip() or "1")
    except ValueError:
        default_author = 1
    
    try:
        posts_per_day = int(input("Posts per day [2]: ").strip() or "2")
    except ValueError:
        posts_per_day = 2

    gsc_url = input(f"GSC Site URL (e.g. https://example.com/) [optional]: ").strip()
    ga4_property_id = input("GA4 Property ID (numeric, e.g. 123456789) [optional]: ").strip()

    # Add to database
    site_id = add_site(
        name=name,
        wp_url=wp_url,
        wp_username=wp_username,
        wp_app_password=wp_app_password,
        blog_template=blog_template,
        default_category=default_category,
        default_author=default_author,
        posts_per_day=posts_per_day,
        gsc_url=gsc_url,
        ga4_property_id=ga4_property_id,
    )
    
    print(f"\nSite added successfully! ID: {site_id}")
    return site_id


def list_all_sites():
    """Display all configured sites."""
    sites = list_sites()
    
    if not sites:
        print("No sites configured. Use --add-site or add WP_URL_SITE1 to .env")
        return
    
    print("\n=== Configured Sites ===\n")
    print(f"{'ID':<5} {'Name':<20} {'URL':<35} {'P/Day':<7} {'GSC':<5} {'GA4':<5}")
    print("-" * 80)

    for site in sites:
        gsc = "✓" if site.get("gsc_url") else "–"
        ga4 = "✓" if site.get("ga4_property_id") else "–"
        print(
            f"{site['id']:<5} {site['name']:<20} {site['wp_url']:<35} "
            f"{site['posts_per_day']:<7} {gsc:<5} {ga4:<5}"
        )

    print()


def get_site_settings(site_id: int) -> dict:
    """Get full site settings by ID."""
    site = get_site(site_id)
    if not site:
        raise ValueError(f"Site with ID {site_id} not found")
    return site
