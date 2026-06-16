# Vendored SEO scripts

These files are vendored from the **`anthropic-skills:seo`** Claude skill so the
headless article pipeline (`seo_validator.py`) can run them without depending on
the skill's volatile session install path.

Vendored: `seo_common.py`, `readability.py`, `parse_html.py`,
`answer_block_scanner.py`, `validate_schema.py`, `lib/` (safe_http).

To refresh: re-copy from the installed `seo` skill's `scripts/` directory.
Run deps: beautifulsoup4, lxml, requests.
