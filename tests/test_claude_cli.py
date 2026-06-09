"""
Tests for claude_cli.claude_complete — subprocess is mocked, so these never
invoke the real CLI.
"""
import json
import subprocess
import pytest

import claude_cli
from claude_cli import claude_complete, ClaudeCLIError


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _envelope(result, is_error=False):
    return json.dumps({"type": "result", "subtype": "success",
                       "result": result, "is_error": is_error})


def test_parses_json_envelope(monkeypatch):
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda *a, **k: _Proc(stdout=_envelope("hello world")))
    assert claude_complete("hi") == "hello world"


def test_plain_text_fallback(monkeypatch):
    # If output isn't JSON, return it raw.
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda *a, **k: _Proc(stdout="just text"))
    assert claude_complete("hi") == "just text"


def test_error_envelope_raises(monkeypatch):
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda *a, **k: _Proc(stdout=_envelope("nope", is_error=True)))
    with pytest.raises(ClaudeCLIError):
        claude_complete("hi")


def test_nonzero_exit_raises(monkeypatch):
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda *a, **k: _Proc(returncode=2, stderr="boom"))
    with pytest.raises(ClaudeCLIError):
        claude_complete("hi")


def test_empty_output_raises(monkeypatch):
    monkeypatch.setattr(claude_cli.subprocess, "run", lambda *a, **k: _Proc(stdout="   "))
    with pytest.raises(ClaudeCLIError):
        claude_complete("hi")


def test_empty_result_field_raises(monkeypatch):
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda *a, **k: _Proc(stdout=_envelope("   ")))
    with pytest.raises(ClaudeCLIError):
        claude_complete("hi")


def test_timeout_raises(monkeypatch):
    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)
    monkeypatch.setattr(claude_cli.subprocess, "run", _boom)
    with pytest.raises(ClaudeCLIError):
        claude_complete("hi", timeout=1)


def test_missing_binary_raises(monkeypatch):
    def _boom(*a, **k):
        raise FileNotFoundError()
    monkeypatch.setattr(claude_cli.subprocess, "run", _boom)
    with pytest.raises(ClaudeCLIError):
        claude_complete("hi")


def test_command_includes_model_and_system(monkeypatch):
    captured = {}
    def _capture(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        return _Proc(stdout=_envelope("ok"))
    monkeypatch.setattr(claude_cli.subprocess, "run", _capture)

    claude_complete("USER PROMPT", system="SYS PROMPT", model="opus")

    cmd = captured["cmd"]
    assert "-p" in cmd
    assert "--model" in cmd and "opus" in cmd
    assert "--output-format" in cmd and "json" in cmd
    assert "--system-prompt" in cmd and "SYS PROMPT" in cmd
    assert captured["input"] == "USER PROMPT"   # prompt fed on stdin


def test_no_system_prompt_flag_when_absent(monkeypatch):
    captured = {}
    monkeypatch.setattr(claude_cli.subprocess, "run",
                        lambda cmd, **k: captured.update(cmd=cmd) or _Proc(stdout=_envelope("ok")))
    claude_complete("hi")
    assert "--system-prompt" not in captured["cmd"]
