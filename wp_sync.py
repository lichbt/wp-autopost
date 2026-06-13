"""
wp_sync.py — WordPress ↔ Database Sync
========================================
Fetches all published posts from a WordPress site via REST API and imports
any that are missing from the topics DB as stub records (status='published').

This ensures:
1. Content plan generation (site_analyst.py) sees the full picture and
   doesn't propose articles that already exist on the live site.
2. get_pending_topics() deduplication catches all existing articles,
   preventing the scheduler from re-publishing something already live.

Usage (CLI via main.py):
    python main.py --site 2 --sync-wp
    python main.py --site 4 --sync-wp

Usage (programmatic, e.g. before plan generation):
    from wp_sync import get_wp_post_list
    wp_posts = get_wp_post_list(site)  # [{title, slug}, ...]
"""

import re
import requests
from typing import Dict, List, Optional

from database import (
    get_site,
    get_db_connection,
    get_or_create_import_plan,
    import_wp_post_stub,
    get_all_topic_wp_ids,
    get_all_topic_slugs,
    link_wp_post_by_slug,
    update_topic_status,
)
from logger import logger


# ── Core WP REST API fetch ─────────────────────────────────────────────────────

def fetch_all_wp_posts(site: Dict, per_page: int = 100, statuses: str = "publish") -> List[Dict]:
    """
    Paginate through WP REST API until all matching posts are fetched.

    `statuses` is a comma-separated WP status filter ("publish" by default).
    Pass e.g. "publish,draft,pending,future" to also include unpublished work —
    a draft already covers a topic, so it must count when de-duplicating a plan.
    (Non-published statuses require authenticated edit access; we pass app-password
    auth, and on any permission error we fall back gracefully to whatever returned.)

    Uses X-WP-TotalPages header to stop pagination early.
    Returns a list of dicts: {id, title, slug, link, status}.

    Non-blocking: on any error returns whatever was collected so far (may be []).
    """
    wp_url = site.get("wp_url", "").rstrip("/")
    auth   = (site["wp_username"], site["wp_app_password"])

    all_posts: List[Dict] = []
    page = 1

    while True:
        try:
            resp = requests.get(
                f"{wp_url}/wp-json/wp/v2/posts",
                params={
                    "status":   statuses,
                    "per_page": per_page,
                    "page":     page,
                    "orderby":  "date",
                    "order":    "desc",
                    "_fields":  "id,title,slug,link,status",
                },
                auth=auth,
                timeout=20,
            )

            if resp.status_code == 400 and page > 1:
                # WP returns 400 when page exceeds total — we're done
                break

            if resp.status_code != 200:
                logger.warning(
                    f"[wp_sync] WP API returned {resp.status_code} for site {wp_url} "
                    f"(page {page}) — stopping pagination"
                )
                break

            posts = resp.json()
            if not posts:
                break   # empty page — done

            for p in posts:
                all_posts.append({
                    "id":     p.get("id"),
                    "title":  p.get("title", {}).get("rendered", "").strip(),
                    "slug":   p.get("slug", "").strip(),
                    "link":   p.get("link", ""),
                    "status": p.get("status", "publish"),
                })

            # Check if there are more pages
            total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
            if page >= total_pages:
                break
            page += 1

        except Exception as exc:
            logger.warning(f"[wp_sync] Error fetching page {page}: {exc}")
            break

    logger.info(f"[wp_sync] Fetched {len(all_posts)} posts ({statuses}) from {wp_url}")
    return all_posts


def get_wp_post_list(site: Dict, limit: int = 500) -> List[Dict]:
    """
    Fetch WP posts for plan generation context — title + slug only.
    No DB writes. Shared underlying fetch with sync_wp_to_db.

    Returns [{title, slug}, ...] up to `limit` entries.
    """
    posts = fetch_all_wp_posts(site)
    return [{"title": p["title"], "slug": p["slug"]} for p in posts[:limit]]


# ── Main sync function ─────────────────────────────────────────────────────────

def sync_wp_to_db(site_id: int) -> Dict[str, int]:
    """
    Sync all live WordPress published posts into the topics DB.

    Matching strategy (in order):
      1. Match by wp_post_id — already synced, no action needed.
      2. Match by slug  — topic exists but wp_post_id not linked; link it.
      3. No match       — new stub topic created (status='published').

    Returns stats dict:
      {"total_wp": N, "created": N, "updated": N, "already_synced": N, "errors": N}
    """
    site = get_site(site_id)
    if not site:
        logger.error(f"[wp_sync] Site {site_id} not found")
        return {"total_wp": 0, "created": 0, "updated": 0, "already_synced": 0, "errors": 1}

    # Fetch all live WP posts
    wp_posts = fetch_all_wp_posts(site)
    if not wp_posts:
        logger.warning(f"[wp_sync] No WP posts returned for site {site_id} — check credentials")
        return {"total_wp": 0, "created": 0, "updated": 0, "already_synced": 0, "errors": 0}

    # Load existing DB identifiers for fast lookup
    existing_wp_ids = get_all_topic_wp_ids(site_id)   # set[int]
    existing_slugs  = get_all_topic_slugs(site_id)    # set[str]

    # Get or create the import pseudo-plan (needed for FK constraint)
    plan_id = get_or_create_import_plan(site_id)

    stats = {"total_wp": len(wp_posts), "created": 0, "updated": 0, "already_synced": 0, "errors": 0}

    for post in wp_posts:
        wp_id = post.get("id")
        slug  = post.get("slug", "")
        title = post.get("title", "")

        if not wp_id or not slug:
            stats["errors"] += 1
            continue

        try:
            if wp_id in existing_wp_ids:
                # Already tracked — nothing to do
                stats["already_synced"] += 1

            elif slug in existing_slugs:
                # DB has this slug but missing the wp_post_id — link them
                link_wp_post_by_slug(site_id, slug, wp_id)
                # Update the in-memory set so we don't double-process
                existing_wp_ids.add(wp_id)
                stats["updated"] += 1
                logger.info(f"[wp_sync] Linked wp_post_id={wp_id} → slug='{slug}'")

            else:
                # Completely new to the DB — create stub
                topic_id = import_wp_post_stub(site_id, plan_id, title, slug, wp_id)
                if topic_id:
                    existing_wp_ids.add(wp_id)
                    existing_slugs.add(slug)
                    stats["created"] += 1
                    logger.info(f"[wp_sync] Imported stub: '{title}' (wp_id={wp_id})")

        except Exception as exc:
            logger.warning(f"[wp_sync] Error processing post wp_id={wp_id} '{title}': {exc}")
            stats["errors"] += 1

    logger.info(
        f"[wp_sync] site {site_id} done — "
        f"total={stats['total_wp']} created={stats['created']} "
        f"updated={stats['updated']} already_synced={stats['already_synced']} "
        f"errors={stats['errors']}"
    )
    return stats


# ── Pending ↔ live reconcile ────────────────────────────────────────────────────
# Plan topics often get published under a slug that differs from the planned slug
# (older plan runs, manual edits). Slug/title dedup then misses them and they sit
# "pending", so the scheduler would re-write a duplicate. This reconcile marks a
# pending topic as published+linked when it clearly already exists live.
#
# Precision-first: it AUTO-applies only high-confidence matches (exact slug, or
# near-identical title). Weaker "same distinctive entity, different wording"
# matches are returned as a REVIEW list and NOT applied — silently skipping a
# genuinely-new topic is worse than re-confirming a borderline one.

# Generic words stripped before title comparison so DISTINCTIVE tokens dominate
# (competitor names, specific concepts) rather than boilerplate/domain nouns.
_GENERIC_TITLE_WORDS = {
    # years
    "2023", "2024", "2025", "2026", "2027",
    # articles / prepositions / conjunctions / question words
    "the", "a", "an", "to", "for", "of", "and", "or", "in", "on", "is", "are",
    "with", "your", "you", "it", "its", "that", "this", "how", "what", "which",
    "why", "when", "who", "vs", "versus", "from", "as", "at", "by", "be",
    # SEO-generic
    "best", "top", "guide", "complete", "full", "ultimate", "comparison",
    "compared", "compare", "updated", "update", "ranked", "review", "reviewed",
    "options", "option", "right", "choose", "choosing", "explained", "everything",
    "need", "know", "step", "steps", "tips", "ways", "things",
    # domain-generic nouns (both niches) — keep the distinctive entity, drop these
    "social", "network", "networking", "dating", "online", "platform", "platforms",
    "software", "app", "apps", "application", "script", "scripts", "website",
    "websites", "web", "site", "sites", "system", "solution", "tool", "tools",
    "cms", "media", "php",
}


def _title_tokens(text: str, extra_stop: set) -> set:
    toks = re.split(r"[^a-z0-9]+", (text or "").lower())
    stop = _GENERIC_TITLE_WORDS | extra_stop
    return {t for t in toks if len(t) > 2 and t not in stop}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _norm_slug(slug: str) -> str:
    return (slug or "").strip("/").lower()


def _get_pending_topics_min(site_id: int) -> List[Dict]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, title, slug FROM topics WHERE site_id = ? AND status = 'pending'",
        (site_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def reconcile_pending_against_live(
    site_id: int,
    apply: bool = True,
    auto_threshold: float = 0.8,
    review_threshold: float = 0.5,
) -> Dict:
    """Mark pending topics that already exist live as published + linked.

    AUTO (applied when apply=True): exact slug match, or normalized-title
    Jaccard >= auto_threshold. REVIEW (never auto-applied): Jaccard in
    [review_threshold, auto_threshold) — surfaced for a human to confirm.

    Returns {"checked": n, "published": [...], "review": [...]}.
    """
    site = get_site(site_id)
    if not site:
        return {"checked": 0, "published": [], "review": [], "error": "site not found"}

    live = fetch_all_wp_posts(site)
    if not live:
        return {"checked": 0, "published": [], "review": []}

    # Brand tokens (e.g. "shaunsocial", "moodatingscript") count as generic here.
    brand_stop = _title_tokens(site.get("name", ""), set()) | _title_tokens(
        (site.get("wp_url", "").split("//")[-1].split("/")[0]).replace(".", " "), set()
    )

    live_idx = [
        {"id": L["id"], "slug": _norm_slug(L.get("slug")),
         "title": L.get("title", ""), "tok": _title_tokens(L.get("title", ""), brand_stop)}
        for L in live
    ]
    live_by_slug = {l["slug"]: l for l in live_idx if l["slug"]}

    pending = _get_pending_topics_min(site_id)
    published, review = [], []

    for p in pending:
        p_tok = _title_tokens(p["title"], brand_stop)
        p_slug = _norm_slug(p.get("slug"))

        match, score, reason = None, 0.0, ""
        # 1. exact slug match → definitive
        if p_slug and p_slug in live_by_slug:
            match, score, reason = live_by_slug[p_slug], 1.0, "slug"
        else:
            # 2. best title similarity
            for l in live_idx:
                s = _jaccard(p_tok, l["tok"])
                if s > score:
                    match, score, reason = l, s, "title"

        if not match:
            continue
        entry = {"topic_id": p["id"], "topic_title": p["title"],
                 "wp_post_id": match["id"], "live_title": match["title"],
                 "live_slug": match["slug"], "score": round(score, 2), "via": reason}

        if reason == "slug" or score >= auto_threshold:
            if apply:
                update_topic_status(p["id"], "published",
                                    wp_post_id=match["id"], slug=match["slug"])
            published.append(entry)
            logger.info(f"[reconcile] {p['id']} '{p['title'][:40]}' → live wp#{match['id']} "
                        f"(score {entry['score']}, via {reason}) — marked published")
        elif score >= review_threshold:
            review.append(entry)
            logger.warning(f"[reconcile] REVIEW: topic {p['id']} '{p['title'][:40]}' may match "
                           f"live wp#{match['id']} '{match['title'][:40]}' (score {entry['score']}) "
                           f"— NOT auto-applied")

    logger.info(f"[reconcile] site {site_id}: checked {len(pending)} pending, "
                f"published {len(published)}, review {len(review)}")
    return {"checked": len(pending), "published": published, "review": review}


# ── Plan dedup-check (proposed topics vs existing DB + live) ─────────────────────
# Runs when a plan is proposed/imported: blocks topics that duplicate something
# already in the DB (any status) or live. High-precision (slug-exact, near-identical
# title, or near-total token overlap) so it won't wrongly drop genuinely-new topics.
# Keeps domain nouns (so "launch a dating site" overlaps) but the high thresholds
# prevent "X vs Y" articles from colliding with "X vs Z".

# Generic words only (NOT domain nouns) + light stemming so wording variants match.
_DEDUP_STOP = {
    "2023", "2024", "2025", "2026", "2027",
    "the", "a", "an", "to", "for", "of", "and", "or", "in", "on", "is", "are", "with",
    "your", "you", "it", "its", "how", "what", "which", "why", "when", "who", "vs",
    "versus", "from", "as", "at", "by", "be", "that", "this",
    "best", "top", "guide", "complete", "full", "ultimate", "comparison", "compared",
    "compare", "updated", "update", "ranked", "review", "reviewed", "options", "option",
    "right", "choose", "choosing", "explained", "step", "steps", "ways", "tips", "should",
}
_STEM_SUFFIXES = ("ization", "isation", "ations", "ation", "izes", "ize", "ise",
                  "ings", "ing", "ers", "ies", "es", "ed", "s")


def _stem(w: str) -> str:
    for suf in _STEM_SUFFIXES:
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[:-len(suf)]
    return w


def _dedup_tokens(text: str) -> set:
    toks = re.split(r"[^a-z0-9]+", (text or "").lower())
    return {_stem(t) for t in toks if len(t) > 2 and t not in _DEDUP_STOP}


def _overlap(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _get_existing_topic_titles(site_id: int) -> List[Dict]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT title, COALESCE(slug,'') slug, status FROM topics WHERE site_id = ?",
        (site_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_plan_duplicates(site_id: int, proposed: List, include_live: bool = True,
                         jaccard_thr: float = 0.7, overlap_thr: float = 0.85) -> Dict:
    """Split proposed topics into unique vs duplicate (of existing DB topics / live posts).

    A proposed topic is a duplicate when: its slug exactly matches an existing one,
    OR its title token-Jaccard ≥ jaccard_thr, OR token-overlap ≥ overlap_thr with any
    existing title.

    `proposed` items may be dicts (with 'title'/'slug') or plain strings.
    Returns {"unique": [...original items...], "duplicates": [{title, match, source, score, via}]}.
    """
    existing: List[Dict] = []
    for t in _get_existing_topic_titles(site_id):
        existing.append({"title": t["title"], "slug": _norm_slug(t["slug"]),
                         "source": f"db:{t['status']}", "tok": _dedup_tokens(t["title"])})
    if include_live:
        try:
            site = get_site(site_id)
            # Include unpublished work — a draft/pending/scheduled post already
            # covers a topic, so it must count as an existing candidate.
            live = fetch_all_wp_posts(site, statuses="publish,draft,pending,future") if site else []
            for L in live:
                st = L.get("status", "publish")
                existing.append({"title": L.get("title", ""), "slug": _norm_slug(L.get("slug", "")),
                                 "source": "live" if st == "publish" else f"live:{st}",
                                 "tok": _dedup_tokens(L.get("title", ""))})
        except Exception as exc:
            logger.warning(f"[dedup] live fetch skipped: {exc}")
    by_slug = {e["slug"]: e for e in existing if e["slug"]}

    unique, duplicates = [], []
    for p in proposed:
        title = (p.get("title", "") if isinstance(p, dict) else str(p)) or ""
        pslug = _norm_slug(p.get("slug", "") if isinstance(p, dict) else "")
        ptok = _dedup_tokens(title)

        match, score, via = None, 0.0, ""
        if pslug and pslug in by_slug:
            match, score, via = by_slug[pslug], 1.0, "slug"
        else:
            for e in existing:
                j, o = _jaccard(ptok, e["tok"]), _overlap(ptok, e["tok"])
                if (j >= jaccard_thr or o >= overlap_thr) and max(j, o) > score:
                    match, score, via = e, max(j, o), ("jaccard" if j >= o else "overlap")

        if match:
            duplicates.append({"title": title, "match": match["title"],
                               "source": match["source"], "score": round(score, 2), "via": via})
            logger.info(f"[dedup] DROP '{title[:48]}' — dup of '{match['title'][:48]}' "
                        f"({match['source']}, {via} {round(score,2)})")
        else:
            unique.append(p)

    if duplicates:
        logger.info(f"[dedup] site {site_id}: {len(duplicates)} of {len(proposed)} proposed "
                    f"topics were duplicates of existing/live content")
    return {"unique": unique, "duplicates": duplicates}
