# Project Backlog & Worklog

A running log of work done, decisions made, and open follow-ups — so we can trace
back *what* changed, *why*, and *where* (commit / PR / external system).

**Legend:** ✅ done · 🔄 in progress · ⏳ open / follow-up · 🧠 decision · ⚠️ needs human/external action

---

## 2026-06-09

- ✅ **Fixed ShaunSocial DB↔live drift.** 5 pending plan topics were already published live under different slugs (dedup missed them): #218→wp#1802, #219→wp#3534 (WoWonder), #220→wp#3536, #221→wp#3252, #226→wp#2393. Marked them `published` + linked. Real queue is now 6 genuinely-new topics (#222 phpSocial, #223 Bettermode/Hivebrite/Disciple, #224 Monetize, #225 Open Source, #227 HumHub, #228 Mobile App). 🧠 Follow-up: productionize a fuzzy plan↔live reconcile so this doesn't recur.

### Image-prompt quality (Nano Banana 2 / Gemini)
- ✅ **New editable guide `data/image_prompt_guide.md`** — there was no md/plugin for image prompts (logic was hardcoded). The guide is tuned for **Nano Banana 2 / Gemini image**: rich natural-language scene descriptions (subject, composition, lighting, lens, palette, mood), `16:9 + negative space for headline`, explicit no-text/logo constraints, topic-type cues, and a worked example.
- ✅ **`image_handler._build_image_prompt` rewritten** to use the guide as the system prompt — drops the old "max 25 words" instruction and the Midjourney-style keyword-soup suffix (`ultra-realistic, 4K…`) on the LLM path (that style hurts Gemini). Falls back to the pillar templates if the guide is missing or the output is too short. 6 tests added (`tests/test_image_prompt.py`).
- 🧠 Note: auto-generation still uses **Pollinations.AI (Flux)**; the improved prompts are what you copy into Nano Banana 2 manually. If wanted, a follow-up could wire auto-gen directly to Gemini image.

### Content production + fact correction
- ✅ **Wrote 2 articles as WordPress drafts** (generated via the `claude` CLI / Sonnet, no OpenRouter):
  - ShaunSocial — *"Best Social Network Software in 2026: Full Comparison (Updated)"* (June plan #1, `best_of`) → draft **#3581**.
  - MooDatingScript — *"What is a Dating Script?"* (pending topic #50, Definition) → draft **#763**; topic #50 marked `draft` in DB.
- ⚠️→✅ **Fixed misleading ShaunSocial pricing fact.** `data/shaunsocial-facts.md` implied native iOS/Android apps were included at the **$149** one-time price. Corrected: **$149 = web platform only**; **$559 one-time = web + native apps** (paid add-on). Updated the pricing table, Mobile App section, differentiators, pricing-comparison note, and content-rule guardrails.
- ✅ **Regenerated the ShaunSocial article** with corrected facts and **updated draft #3581 in place** — verified every pricing mention now separates $149 (web) vs $559 (native apps), incl. an explicit FAQ "Does the $149 license include native apps? No."
- ✅ **`wp_publisher.publish_post(update_post_id=…)`** — new param to update an existing WP post in place (POST to `/posts/{id}`), enabling regeneration without creating duplicate drafts.
- ✅ **Consolidated the duplicate "Best Social Network Software" article.** Discovered the new draft #3581 was a near-duplicate of the existing **live, ranking** post **#2765** (`/best-social-network-softwares-in-2025-comparison/`, ~pos 11, but it had the same misleading $149/native-app pricing live). Per user choice, **rewrote #2765 in place** (same URL, stayed published, category preserved, old version kept in WP revisions) with corrected $149-web / $559-native-app pricing, and **trashed duplicate draft #3581**. Verified live page now states "$149 web license does not include native apps" + "$559 package" throughout. SEO equity preserved; no cannibalization.

- ✅ **Imported the ShaunSocial June 12-article plan into the DB** (was only in `data/shaunsocial-june-plan.html`). Created plan **#10**, topics **#217–#228**; #217 (Best Social Network Software) marked `draft` + linked to WP #3581; #218–#228 pending, scheduled ~3/week (06-11 → 07-04). Verified 0 dedup title collisions with the 88 published, so the scheduler/dedup now track the plan.
- ✅ **Reconciled the MooDatingScript June plan** (`data/moodating-june-plan.html`, 12 articles) against the DB. **11 of 12 already existed** (published/draft/pending) — a blind import would have duplicated them. Added only the **1 genuinely missing** topic: **#229 "Dating Script for Sale: What to Look For & How to Buy Safely"** (buyer_guide, pending, scheduled 06-15).

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

### EPIC 6 — Backlog & worklog convention
- ✅ Created **`BACKLOG.md`** (this file) — running log of work, decisions, follow-ups. `18027f1`
- ✅ Created **`CLAUDE.md`** documenting the convention: *append a dated section here at the end of each work session*, plus project orientation (claude CLI backend; GEO trackers stay on OpenRouter) and git/PR conventions — so future sessions maintain the log automatically.

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
