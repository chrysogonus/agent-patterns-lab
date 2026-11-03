"""The HTTP part of the viewer: routing and streaming, bound to 127.0.0.1 only (research R1)."""

import importlib.resources
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from apl.viewer.app import Response, Viewer, error

PAGE = (importlib.resources.files("apl.viewer") / "assets" / "index.html").read_bytes()
EVENTS = re.compile(r"/api/episodes/([^/]+)/events")
STOP = re.compile(r"/api/episodes/([^/]+)/stop")
MAX_BODY = 4096


class Handler(BaseHTTPRequestHandler):
    viewer: Viewer  # set on the subclass made by make_server

    def do_GET(self) -> None:  # noqa: N802 (the http.server naming)
        url = urlsplit(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/":
            self._send((200, "text/html; charset=utf-8", PAGE))
        elif url.path == "/api/options":
            self._send(self.viewer.options())
        elif url.path == "/api/dungeon":
            self._send(self.viewer.dungeon(query.get("level", ""), query.get("seed", "")))
        elif url.path == "/api/survey":
            self._send(self.viewer.survey(query.get("level", ""), query.get("seed", "")))
        elif url.path == "/api/signal":
            self._send(self.viewer.signal(query.get("level", ""), query.get("seed", "")))
        elif url.path == "/api/rune":
            self._send(self.viewer.rune(query.get("level", ""), query.get("seed", "")))
        elif url.path == "/api/workshop":
            self._send(self.viewer.workshop(query.get("level", ""), query.get("seed", "")))
        elif url.path == "/api/warehouse":
            self._send(self.viewer.warehouse(query.get("level", ""), query.get("seed", "")))
        elif url.path == "/api/episodes":
            self._send(self.viewer.list_episodes())
        elif match := EVENTS.fullmatch(url.path):
            self._events(unquote(match.group(1)))
        else:
            self._send(error(404, f"no such page: {url.path}"))

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(error(413, "request body too large"))
            return
        raw = self.rfile.read(length)
        if path == "/api/episodes":
            try:
                body = json.loads(raw or b"null")
            except ValueError:
                self._send(error(400, "the request body must be JSON"))
                return
            self._send(self.viewer.start_episode(body))
        elif match := STOP.fullmatch(path):
            self._send(self.viewer.stop_episode(unquote(match.group(1))))
        else:
            self._send(error(404, f"no such endpoint: {path}"))

    def _events(self, episode_id: str) -> None:
        """Server-Sent Events: everything so far, then live; resumes after Last-Event-ID."""
        session = self.viewer.session(episode_id)
        if session is None:
            self._send(error(404, f"no episode {episode_id!r}"))
            return
        last = self.headers.get("Last-Event-ID", "")
        start = int(last) + 1 if last.isdigit() else 0
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            for item in session.stream(start):
                if item is None:
                    self.wfile.write(b": keepalive\n\n")  # also notices a closed page
                else:
                    index, event = item
                    data = json.dumps(event["data"])
                    self.wfile.write(
                        f"id: {index}\nevent: {event['type']}\ndata: {data}\n\n".encode()
                    )
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the page went away; the episode carries on

    def _send(self, response: Response) -> None:
        status, content_type, body = response
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass  # one line per request would drown the terminal


def make_server(viewer: Viewer, port: int) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"viewer": viewer})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    return server
