"""Safety net for every test: no network, no real API key, no real `.env` (Constitution VI)."""

import os
import socket
from pathlib import Path

import pytest


def _blocked(*args: object, **kwargs: object) -> None:
    raise RuntimeError("network access is blocked in tests")


@pytest.fixture(autouse=True)
def _no_network_no_secrets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    for name in [n for n in os.environ if n.startswith("APL_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("APL_ENV_FILE", str(tmp_path / "no-such.env"))
