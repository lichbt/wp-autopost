"""
claude_cli.py — One-shot completions via the local `claude` CLI.
=================================================================
Single LLM backend for content writing and data-driven audits. Shells out to the
`claude` binary in print mode using the user's logged-in session auth — no API
keys, no OpenRouter.

    from claude_cli import claude_complete
    text = claude_complete(user_prompt, system=system_prompt, model="sonnet")

Notes:
- `--system-prompt` fully replaces Claude Code's default agent system prompt, so
  the model behaves as our content writer / analyst rather than a coding agent.
- `--output-format json` returns a single result envelope we parse for `result`.
- The user prompt is fed on stdin to avoid arg-length and shell-escaping limits.
"""

import json
import shutil
import subprocess
from typing import Optional

from logger import logger

# Resolve the binary once; fall back to bare name so PATH is consulted at call time.
CLAUDE_BIN = shutil.which("claude") or "claude"


class ClaudeCLIError(RuntimeError):
    """Raised when the claude CLI is missing, times out, or returns an error."""


def claude_available() -> bool:
    """True if the claude CLI is resolvable on PATH."""
    return shutil.which("claude") is not None


def claude_complete(
    prompt: str,
    system: Optional[str] = None,
    model: str = "sonnet",
    timeout: int = 600,
) -> str:
    """Run a one-shot completion via `claude -p` and return the assistant text.

    Args:
        prompt:  the user message (sent on stdin).
        system:  optional system prompt; replaces the default agent prompt.
        model:   model alias or full name (e.g. "sonnet", "opus", "haiku").
        timeout: seconds before the call is aborted.

    Raises:
        ClaudeCLIError on missing binary, timeout, non-zero exit, empty output,
        or an error envelope.
    """
    cmd = [CLAUDE_BIN, "-p", "--model", model, "--output-format", "json"]
    if system:
        cmd += ["--system-prompt", system]

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ClaudeCLIError(f"claude CLI not found ({CLAUDE_BIN})") from exc
    except subprocess.TimeoutExpired as exc:
        raise ClaudeCLIError(f"claude CLI timed out after {timeout}s") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise ClaudeCLIError(f"claude CLI exited {proc.returncode}: {stderr[:500]}")

    out = (proc.stdout or "").strip()
    if not out:
        raise ClaudeCLIError("claude CLI returned empty output")

    # --output-format json → {"type":"result","subtype":"success",
    #                         "result":"...","is_error":false, ...}
    try:
        envelope = json.loads(out)
    except json.JSONDecodeError:
        # Defensive: if a future CLI emits plain text, use it as-is.
        return out

    if isinstance(envelope, dict):
        if envelope.get("is_error"):
            raise ClaudeCLIError(f"claude CLI error: {str(envelope.get('result', ''))[:300]}")
        result = str(envelope.get("result", "")).strip()
        if not result:
            raise ClaudeCLIError("claude CLI result was empty")
        return result

    return out
