"""Shared pytest fixtures for the ROT test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_rot_history_globally(monkeypatch):
    """Ensure no test ever writes to the user's `~/.rot_history`.

    The REPL persists history across sessions by reading/writing
    `~/.rot_history` at startup/exit. Tests that drive `start_repl`
    would otherwise register atexit handlers that scribble test
    inputs into the user's real history file. Setting
    `ROT_HISTORY_FILE` to the empty string makes
    `_install_persistent_history` short-circuit."""
    monkeypatch.setenv("ROT_HISTORY_FILE", "")
