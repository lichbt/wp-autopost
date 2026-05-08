# AI Content Strategy Automation for WordPress

Automated content pipeline that parses strategy documents, generates SEO-optimized blog posts using AI, and publishes to WordPress.

## Features

- **Plan-Agnostic Parsing**: LLM interprets any content strategy document
- **AI Content Generation**: GPT-4o generates TL;DR, body, FAQ, and meta descriptions
- **WordPress Integration**: Publish drafts via REST API with Application Password auth
- **Scheduling**: Daily limits, priority ordering, date-based scheduling
- **Dry-Run Mode**: Test without API keys (returns mock data)
- **Encrypted Storage**: WordPress passwords encrypted with Fernet

## Quick Start

### 1. Install Dependencies

```bash
cd content-automation
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

Required variables:
- `OPENAI_API_KEY` - Your OpenAI API key
- `ENCRYPTION_KEY` - Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### 3. Add a WordPress Site

```bash
python main.py --add-site
```

Follow prompts to enter:
- Site name
- WordPress URL
- Username
- Application Password (generate in WP admin: Users → Profile → Application Passwords)
- Blog template (or use default)
- Category/author IDs
- Posts per day limit

### 4. Import a Content Strategy

```bash
python main.py --site 1 --import-plan sample_strategy.md
```

The LLM will parse your strategy and extract topics with scheduling.

### 5. Run the Pipeline

One cycle:
```bash
python main.py --site 1 --run-once
```

Continuous mode (checks hourly):
```bash
python main.py --site 1 --daemon
```

## Commands

| Command | Description |
|---------|-------------|
| `--add-site` | Add a WordPress site interactively |
| `--list-sites` | List all configured sites |
| `--site ID --import-plan FILE.md` | Import a content strategy |
| `--site ID --run-once` | Run one automation cycle |
| `--site ID --daemon` | Run continuously |
| `--interval SECONDS` | Custom check interval (default: 3600) |

## Dry-Run Mode

When `OPENAI_API_KEY` is not set, the system runs in dry-run mode:
- Plan parsing returns mock topics
- Content generation returns sample content
- WordPress publishing returns mock post ID (9999)

This is useful for testing the pipeline without API costs.

## Project Structure

```
content-automation/
├── main.py                 # CLI entry point
├── config.py               # Environment and constants
├── database.py             # SQLite schema and CRUD
├── sites.py                # Site management
├── plan_parser.py          # LLM plan extraction
├── content_generator.py    # LLM content generation
├── template_assembler.py   # HTML template assembly
├── wp_publisher.py         # WordPress REST API
├── scheduler.py            # Automation cycle
├── logger.py               # Logging setup
├── sample_strategy.md      # Example strategy document
├── requirements.txt
├── .env.example
├── data/                   # SQLite database
├── logs/                   # Log files
└── tests/                  # pytest test suite
```

## Database

SQLite database at `data/blog_automation.db` with tables:
- `sites` - WordPress site configurations
- `plans` - Imported strategy documents
- `topics` - Individual blog posts with status tracking
- `post_log` - Action history

## Testing

```bash
cd content-automation
pytest tests/ -v
```

## Blog Template Placeholders

| Placeholder | Description |
|-------------|-------------|
| `{{title}}` | Post title (HTML escaped) |
| `{{tldr}}` | TL;DR section |
| `{{content}}` | Main body HTML |
| `{{faq}}` | FAQ section |
| `{{meta_description}}` | SEO meta description |
| `{{cta_link}}` | Call-to-action URL |
| `{{cta_text}}` | Call-to-action text |

## Topic Statuses

- `pending` - Awaiting processing
- `content_generated` - Content created, ready to publish
- `draft` - Published as WordPress draft
- `published` - Published publicly
- `failed` - Failed after max retries

## Error Handling

- LLM calls: 3 retries with exponential backoff (10s, 30s, 60s)
- WordPress API: 3 retries, auth errors fail immediately
- Topics marked `failed` after 3 attempts
- All errors logged to `logs/automation.log`
