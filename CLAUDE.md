# CLAUDE.md — project guidance

## Worklog convention (IMPORTANT)
This project keeps a running backlog at **`BACKLOG.md`**.

- **At the end of each work session, append a new dated section** (`## <YYYY-MM-DD>`)
  to `BACKLOG.md` summarizing what changed, decisions made, and open follow-ups.
- Use the existing status markers: ✅ done · 🔄 in progress · ⏳ open/follow-up ·
  🧠 decision · ⚠️ needs human/external action.
- Reference commit hashes and PR numbers so changes can be traced back.
- If a prior open item (⏳/⚠️) was resolved, note it as done in the new section
  rather than editing history.
- Before starting substantial work, skim `BACKLOG.md` for relevant context and
  open items.

## Project orientation
- Python content-automation pipeline for WordPress (SEO/GEO article generation).
- **LLM backend = the local `claude` CLI** via `claude_cli.claude_complete()`
  (logged-in session; no API keys, no OpenRouter) for all writing + audits.
- **Exception:** `llm_tracker.py` and `geo_monitor.py` query *other* engines
  (GPT, Perplexity) for GEO/brand-citation tracking and intentionally use
  OpenRouter — do not migrate them to the claude CLI.
- Tests: `python -m pytest -q`. `tests/conftest.py` forces `DRY_RUN=true` so
  tests never shell out to the real CLI.

## Git/PR conventions
- Don't commit/push to `main` directly; use feature branches + PRs.
- End commit messages with the `Co-Authored-By: Claude ...` trailer.
- Prune feature branches after their PR merges.
