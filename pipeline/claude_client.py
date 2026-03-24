"""
claude_client.py — Shared Claude caller for Atlas of Culture pipeline.

Uses Claude Code CLI with the OpenClaw API key injected as ANTHROPIC_API_KEY.
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

AUTH_PATH = Path.home() / ".openclaw/agents/main/agent/auth-profiles.json"


def _get_env() -> dict:
    """Build env with Anthropic API key from OpenClaw auth."""
    key = json.loads(AUTH_PATH.read_text())["profiles"]["anthropic:claude"]["token"]
    return {**os.environ, "ANTHROPIC_API_KEY": key}


def ask_claude(prompt: str, max_tokens: int = 4000) -> str:
    """Call Claude via CLI and return response text."""
    result = subprocess.run(
        ["claude", "--print", "--permission-mode", "bypassPermissions"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120,
        env=_get_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error (code {result.returncode}): {result.stderr[:300]}")
    return result.stdout.strip()


def ask_claude_json(prompt: str, max_tokens: int = 4000):
    """Call Claude and parse JSON from the response. Returns dict or list."""
    raw = ask_claude(prompt, max_tokens)
    for pattern in [r'\[.*\]', r'\{.*\}']:
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not parse JSON from response:\n{raw[:400]}")
