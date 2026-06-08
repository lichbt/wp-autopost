# Project Backlog & Worklog

A running log of work done, decisions made, and open follow-ups — so we can trace
back *what* changed, *why*, and *where* (commit / PR / external system).

**Legend:** ✅ done · 🔄 in progress · ⏳ open / follow-up · 🧠 decision · ⚠️ needs human/external action

---

## 2026-06-08

### EPIC 1 — Google Ads conversion tracking audit & fixes
External system: Google Ads account **880-552-2615** (shared: ShaunSocial + MooDatingScript), GTM, GA4. Changes made via web UI (Chrome), not code.

- ✅ **Diagnosed ShaunSocial purchase tracking broken end-to-end.** Root cause: GA4 `purchase` event *was* firing with real revenue (**$1,427 / 5 purchases in 28d**) but was **not marked as a Key Event** in the GA4 ShaunSocial property (`G-RLVDJC6SKC`) → couldn't export to Google Ads → Ads purchase conversion stuck at 0.
- ✅ **Fix:** marked `purchase` as a **Key Event** in GA4 (ShaunSocial). *(GA4 UI change.)*
- ✅ Verified GTM container `GTM-5TVR86VD` v45 "Fix purchase event tracking" is live; GTM4WP pushes GA4-format ecommerce (`view_item`, `purchase`); GA4↔Ads link active.
- ✅ **MooDatingScript:** applied same Key-Event fix to `purchase` in GA4 (`G-04T0BPG6X6`). GTM (`GTM-KF2KGF6`) tracking is correctly wired (Loves Data `{{Event}}` ecommerce tag, trigger regex includes `purchase`). GA4 shows **"No stream data detected"** → no recorded sales in 28d.
- ✅ **Removed 3 dead MooDatingScript conversion actions** (all Inactive, 0 conv, website-tag type): `moodatingscript - Purchase`, `- Add to Cart`, `- Begin Checkout`.
- ✅ **Removed dead `ShaunSocial (web) Order_Received`** conversion (key event that never fires — site sends `purchase`, not `Order_Received`).
- ✅ **Demoted `fantasyengine (web) chat_started`** Primary → Secondary (was polluting Smart Bidding for the other products).
- 📉 Account conversion actions: **18 → 14**.

**⏳ Open / follow-up (EPIC 1):**
- ⏳ **Promote `ShaunSocial (web) purchase` Secondary → Primary + include in account goals** once data lands in Ads (~24–48h after the Key-Event change). Do *after* confirming Ads shows the conversion.
- ⚠️ **MooDatingScript: zero recorded sales** — confirm whether sales actually happen on the WooCommerce checkout, or the checkout uses an off-site gateway that skips the `/order-received/` thank-you page (which would prevent the `purchase` event firing). Fix would be a gateway that returns on-site, or server-side Measurement Protocol.
- ⚠️ **Vietnam tax code missing** — persistent "Fix it" banner in the Ads account; needs the business tax details (user action).

---

### EPIC 2 — Test suite health + repo hygiene
Branch: committed to `main` baseline (pre-existing uncommitted work from a prior session was committed here too).

- ✅ Fixed 2 failing tests — `_get_mock_content()` now returns `meta_title`/`focus_keyword`/`slug` to match the real LLM contract (tests had asserted non-existent `seo_title`/`schema_type` content keys). `382fa23`–`fceb5c9`
- ✅ Added unit tests: content-strategist scoring/tiers, persona rotation, `wp_sync` 3-way match.
- ✅ **.gitignore cleanup** — untracked `data/blog_automation.db`, `logs/automation.log`, and a stray `:memory:` file; added ignore rules. `382fa23`
- ✅ Committed prior-session content-intelligence modules (`content_strategist`, `wp_sync`, `llm_tracker`, `strategy`, persona rotation) as structured commits. `8556da7`

---

### EPIC 3 — LLM-driven content templates  · PR #1 (merged → `4adc774`)
- ✅ **Phase 1 — robust template resolution + bug fix.** New `resolve_template_name(pillar, override)`: direct `{slug}.md` → alias map → fuzzy → default; auto-discovers templates on disk. Fixed real bug where `best_of`/`buyer_guide`/`setup_tutorial`/`use_case` fell back to `how_to` and `feature_explainer` mis-mapped to `definition`. `58773ae`
- ✅ **Phase 2 — planner suggests a template per topic.** `recommended_template` chosen by search intent, flows planner → DB → generation; falls back to pillar default. `b041457`
- ✅ **Phase 3 — data-driven template proposals.** `suggest_templates()` analyses top scorers + pillar perf + existing library → proposes new templates to `templates/proposed/` (human-review; inactive until moved up). CLI: `strategy.py --suggest-templates`. `b4a3096`
- ✅ **Controlled-extension tweak** — template is now the *recommended* structure the LLM adapts per topic, keeping mandatory AEO blocks (TL;DR, FAQ, headings). `4b3c61e`

---

### EPIC 4 — Performance-weighted, template-aware persona selection  · PR #2 (merged → `1d2ce03`)
- ✅ Replaced blind `topic_id % 6` rotation with **deterministic epsilon-greedy** on recorded article scores. `23628a2`
- ✅ Made it **template-aware** — tiered: per-template performance → global performance → cold-start template→persona affinity (e.g. `vs_comparison`→`data_analyst`, `how_to`→`educator`) → rotation. `3e605e5`
- ✅ `strategy.py --personas` shows per-persona avg score + counts.

---

### EPIC 5 — Claude CLI as the sole LLM backend (drop OpenRouter)  · PR #3 (OPEN)
Branch `feature/claude-cli-backend`, commit `8446919`.

- ✅ **New `claude_cli.py`** — `claude_complete(prompt, system, model)` wraps `claude -p --output-format json`; prompt on stdin; `--system-prompt` overrides default agent behaviour. Uses the logged-in `claude` session — **no API key, no OpenRouter**.
- ✅ Migrated to the CLI: `content_generator` (writing), `content_strategist` (strategy memo + template audit), `plan_parser`, `site_analyst` (also drops Anthropic API-key dep), `image_handler`.
- ✅ Config: removed `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL`/`OPENAI_API_KEY`; `DRY_RUN` now keys off `CLAUDE_CLI_AVAILABLE`; models via `CLAUDE_CONTENT_MODEL`/`CLAUDE_ANALYSIS_MODEL` (default `sonnet`).
- ✅ Verified with a live call against the real binary (returned expected output).
- 🧠 **Kept on OpenRouter intentionally:** `llm_tracker` + `geo_monitor` — they query *other* engines (GPT, Perplexity) for GEO/brand-citation tracking; not our writing/audit.

**⏳ Open / follow-up (EPIC 5):**
- ⏳ **Review + merge PR #3** (https://github.com/lichbt/wp-autopost/pull/3).
- ⚠️ **Headless auth:** cron/daemon runs need the `claude` CLI to stay logged in on the host — that session replaces the API key.
- ⏳ Add `README` / `.env.example` note: Claude-CLI setup; `OPENROUTER_API_KEY` now only needed for GEO tracking (`llm_tracker`/`geo_monitor`).

---

## Cross-cutting open items
- ⏳ **Serper.dev API key** (from a prior session) — sign up (free, 2,500/mo), set `SERPER_API_KEY` in `.env`, then test `llm_tracker.py --llm google_ai` (Google AI Overview tracking).
- ⏳ **WordPress ↔ DB sync** bootstrap — run `python main.py --site N --sync-wp` per site so plan generation/dedup see live posts (modules shipped in EPIC 2; one-time run still needed if not done).

---

## Key decisions & rationale (🧠)
- **Templates = hybrid, not free-form.** Keep the fixed template library as the AEO/GEO backbone (schema/FAQ/TL;DR consistency + measurability); add intelligent *selection* and *bounded adaptation* + data-driven *proposals*. Full per-article free-form was rejected (loses schema consistency + testability).
- **Persona bandit is deterministic (no RNG).** Reproducible and testable; exploration guaranteed via "every Nth topic" rather than randomness.
- **Template proposals are human-reviewed.** Written to `templates/proposed/` and never auto-activated (`available_template_stems()` globs only the top level).
- **Hard replace OpenRouter** (not a configurable backend) for the content pipeline, per request.
- **GEO trackers stay on OpenRouter by design** — their job is to query competing engines.
- **Branch hygiene:** consolidated feature branches to `main` via PRs (#1, #2) before the CLI swap; pruned merged branches.

## Reference — commits / PRs
| Item | Ref |
|---|---|
| gitignore + runtime untrack | `382fa23` |
| content-intelligence modules | `8556da7` |
| test fixes + new tests | `fceb5c9` |
| ad-hoc publish/report scripts | `09e24a3` |
| Templates Phase 1–3 + tweak | `58773ae`, `b041457`, `b4a3096`, `4b3c61e` |
| Persona weighting + template-aware | `23628a2`, `3e605e5` |
| PR #1 merge (templates) | `4adc774` |
| PR #2 merge (persona) | `1d2ce03` |
| Claude CLI backend | `8446919` (PR #3, open) |
