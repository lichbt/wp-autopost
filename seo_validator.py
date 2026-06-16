"""
seo_validator.py — Pre-publish SEO validation gate for generated articles.

Reuses the vendored SEO-skill scripts (seo_scripts/) for structural + GEO/AEO
analysis, adds direct title/meta/keyword/FAQ checks, and produces a 0–100 score
with prioritized findings. Used by the generation pipeline to gate publishing
and drive one automatic revision pass.
"""
import os
import re
import json
import subprocess
import tempfile
from typing import Dict, List, Optional

from config import PROJECT_ROOT
from logger import logger

_SCRIPTS = PROJECT_ROOT / "seo_scripts"
DEFAULT_MIN_SCORE = 70


def _run_script(script: str, args: List[str]) -> Optional[Dict]:
    """Run a vendored seo_scripts/<script> with cwd=seo_scripts so its relative
    imports (lib/, seo_common) resolve. Returns parsed JSON or None."""
    try:
        proc = subprocess.run(
            ["python3", script, *args],
            cwd=str(_SCRIPTS), capture_output=True, text=True, timeout=40,
        )
        out = proc.stdout.strip()
        # strip any leading non-JSON noise (warnings) before the first '{'
        i = out.find("{")
        if i == -1:
            return None
        return json.loads(out[i:])
    except Exception as exc:
        logger.warning(f"[seo] {script} failed: {exc}")
        return None


def _strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def score_html(
    *,
    title: str,
    content_html: str,
    faq_html: str = "",
    meta_description: str = "",
    focus_keyword: str = "",
    min_score: int = DEFAULT_MIN_SCORE,
) -> Dict:
    """Score an article 0–100 against SEO best practices. Returns
    {score, max, passed, findings:[{check, severity, points, detail}], readability}."""
    kw = (focus_keyword or "").strip().lower()
    title_l = (title or "").lower()
    body_text = _strip_tags(content_html)
    first_chunk = " ".join(body_text.split()[:120]).lower()

    # Build a self-contained HTML doc for the structural scripts
    doc = (f"<html><head><title>{title}</title></head><body>"
           f"<h1>{title}</h1>{content_html}{faq_html}</body></html>")
    findings: List[Dict] = []
    score = 0

    def add(ok, pts, check, detail, sev="warn"):
        nonlocal score
        if ok:
            score += pts
        else:
            findings.append({"check": check, "severity": sev, "points": pts, "detail": detail})

    # Run vendored scripts on a temp file
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(doc); tmp = f.name
    try:
        parsed = _run_script("parse_html.py", [tmp, "--json"]) or {}
        answers = _run_script("answer_block_scanner.py", [tmp, "--json"]) or {}
        readability = _run_script("readability.py", [tmp, "--json"]) or {}
    finally:
        try: os.unlink(tmp)
        except Exception: pass

    h1 = parsed.get("h1") or []
    h2 = parsed.get("h2") or []
    word_count = readability.get("word_count") or parsed.get("word_count") or len(body_text.split())

    # ── Checks (total 100) ──
    add(30 <= len(title or "") <= 65, 12, "title_length",
        f"Title is {len(title or '')} chars; aim for 30–65.", "high")
    add(110 <= len(meta_description or "") <= 165, 12, "meta_description_length",
        f"Meta description is {len(meta_description or '')} chars; aim for 110–165.", "high")
    add(bool(kw) and kw in title_l, 12, "keyword_in_title",
        f"Focus keyword {kw!r} not in title.", "high")
    add(bool(kw) and kw in first_chunk, 8, "keyword_early",
        f"Focus keyword {kw!r} not in the first ~120 words.", "med")
    add(len(h1) == 1, 6, "single_h1",
        f"Found {len(h1)} H1 tags; should be exactly 1.", "med")
    add(len(h2) >= 3, 10, "h2_sections",
        f"Only {len(h2)} H2 sections; aim for ≥3.", "med")
    add(word_count >= 800, 18, "word_count",
        f"Word count {word_count}; aim for ≥800.", "high")
    faq_q = (faq_html or "").lower().count("<h3")
    add(faq_q >= 2, 10, "faq_section",
        f"FAQ has {faq_q} questions; include ≥2 for AEO.", "med")
    geo_ok = bool(answers.get("lists") or answers.get("tables")
                  or answers.get("direct_answers") or len(answers.get("questions") or []) >= 2)
    add(geo_ok, 12, "geo_answer_blocks",
        "No lists/tables/direct-answer blocks — weak for AI/answer engines.", "med")

    # Readability is advisory only (technical content often scores 'difficult')
    fre = readability.get("flesch_reading_ease")
    if fre is not None and fre < 30:
        findings.append({"check": "readability", "severity": "low", "points": 0,
                         "detail": f"Flesch reading ease {fre} (very difficult) — consider shorter sentences."})

    passed = score >= min_score
    return {"score": score, "max": 100, "passed": passed,
            "findings": findings, "word_count": word_count,
            "readability": fre}


def _revision_block(validation: Dict) -> str:
    lines = ["", "── SEO REVISION REQUIRED — fix these issues, keep the topic the same ──",
             f"(SEO score was {validation['score']}/100; target ≥ {DEFAULT_MIN_SCORE})"]
    for f in validation["findings"]:
        if f["severity"] in ("high", "med"):
            lines.append(f"- {f['detail']}")
    return "\n".join(lines)


def generate_and_validate(topic: Dict, site: Dict, plan_context: Dict,
                          min_score: int = DEFAULT_MIN_SCORE):
    """Generate content, SEO-score it, and if it fails, regenerate ONCE with the
    findings fed back. Returns (content, validation). validation['passed'] tells
    the caller whether to publish or hold for review."""
    from content_generator import generate_post_content
    from config import DRY_RUN

    content = generate_post_content(topic, site, plan_context)
    if DRY_RUN:
        # DRY_RUN exercises pipeline plumbing with mock content — skip the SEO gate.
        return content, {"score": None, "max": 100, "passed": True, "findings": [], "skipped": True}
    val = _score_content(topic, content, min_score)
    logger.info(f"[seo] '{topic['title'][:50]}' score {val['score']}/100 "
                f"({'PASS' if val['passed'] else 'FAIL'})")
    if val["passed"]:
        return content, val

    # One auto-revision pass with the findings injected as instructions
    logger.info(f"[seo] revising once — issues: "
                + "; ".join(f['check'] for f in val['findings'][:6]))
    topic2 = dict(topic)
    topic2["special_instructions"] = (topic.get("special_instructions") or "") + _revision_block(val)
    content = generate_post_content(topic2, site, plan_context)
    val = _score_content(topic, content, min_score)
    val["revised"] = True
    logger.info(f"[seo] after revision: score {val['score']}/100 "
                f"({'PASS' if val['passed'] else 'FAIL'})")
    return content, val


def _score_content(topic: Dict, content: Dict, min_score: int) -> Dict:
    kw = content.get("focus_keyword") or topic.get("generated_focus_keyword") or ""
    if not kw:
        tk = topic.get("target_keywords")
        if isinstance(tk, list) and tk:
            kw = tk[0]
        elif isinstance(tk, str) and tk:
            kw = tk
    return score_html(
        title=content.get("meta_title") or topic.get("title", ""),
        content_html=content.get("content", ""),
        faq_html=content.get("faq", ""),
        meta_description=content.get("meta_description", ""),
        focus_keyword=kw,
        min_score=min_score,
    )
