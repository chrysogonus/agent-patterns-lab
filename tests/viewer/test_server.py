"""One real HTTP round trip over loopback (research R1); everything else tests app functions."""

import http.client
import json
import socket
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from apl.runner.settings import Settings
from apl.viewer.app import Viewer
from apl.viewer.server import make_server
from tests.runner import loop_arch
from tests.runner.scripted import scripted_factory, text_answer

# Taken before conftest blocks them; the fixture lets only 127.0.0.1 through.
_create_connection = socket.create_connection
_connect = socket.socket.connect


def _check(address: object) -> None:
    if not (isinstance(address, tuple) and address[0] == "127.0.0.1"):
        raise RuntimeError("network access is blocked in tests")


def _loopback_create(address: tuple[str, int], *args: object, **kwargs: object) -> socket.socket:
    _check(address)
    return _create_connection(address, *args, **kwargs)  # type: ignore[arg-type]


def _loopback_connect(self: socket.socket, address: object) -> None:
    _check(address)
    _connect(self, address)  # type: ignore[arg-type]


@pytest.fixture
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[int, Viewer]]:
    monkeypatch.setattr(socket, "create_connection", _loopback_create)
    monkeypatch.setattr(socket.socket, "connect", _loopback_connect)
    viewer = Viewer(
        Settings(model="ollama:qwen3:8b"),  # local, and no vLLM lookup over the network
        results_dir=tmp_path / "viewer",
        model_factory=scripted_factory(text_answer()),
        architectures={"loop": loop_arch.play},
    )
    httpd = make_server(viewer, 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1], viewer
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(port: int, path: str) -> tuple[int, str, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.getheader("Content-Type") or "", response.read()
    finally:
        connection.close()


def test_page_options_and_dungeon(server: tuple[int, Viewer]) -> None:
    port, _ = server
    status, content_type, body = _get(port, "/")
    assert status == 200 and content_type.startswith("text/html") and b"Agent Viewer" in body
    status, content_type, body = _get(port, "/api/options")
    assert status == 200 and json.loads(body)["architectures"] == ["loop"]
    status, _, body = _get(port, "/api/dungeon?level=L1&seed=1000")
    assert status == 200 and json.loads(body)["seed"] == 1000
    status, _, body = _get(port, "/api/dungeon?level=L1&seed=2005")
    assert status == 403 and "test seed" in json.loads(body)["error"]
    assert _get(port, "/nope")[0] == 404


def test_server_listens_on_loopback_only(server: tuple[int, Viewer]) -> None:
    viewer = server[1]
    httpd = make_server(viewer, 0)
    try:
        assert httpd.server_address[0] == "127.0.0.1"
    finally:
        httpd.server_close()


def test_episode_over_http_with_server_sent_events(server: tuple[int, Viewer]) -> None:
    port, _ = server
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = json.dumps({"arch": "loop", "level": "L1", "seed": 1000})
    connection.request("POST", "/api/episodes", body, {"Content-Type": "application/json"})
    response = connection.getresponse()
    assert response.status == 201
    episode_id = json.loads(response.read())["id"]
    connection.close()
    status, content_type, stream = _get(port, f"/api/episodes/{episode_id}/events")
    assert status == 200 and content_type == "text/event-stream"
    text = stream.decode()
    assert text.startswith("id: 0\nevent: start\ndata: {")
    assert "event: thinking" in text and "event: turn" in text and text.rstrip().endswith("}")
    assert "\nevent: end\n" in text
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request("GET", f"/api/episodes/{episode_id}/events", headers={"Last-Event-ID": "1"})
    resumed = connection.getresponse().read().decode()
    assert resumed.startswith("id: 2\n")  # a reconnecting page gets only what it missed
    connection.close()
    assert _get(port, "/api/episodes/..%2F..%2Fetc/events")[0] == 404
