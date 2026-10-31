"""The viewer's request logic as plain functions, testable without sockets (research R1).

Each handler returns `(status, content type, body)`; `server.py` only does the HTTP part.
"""

import json
import re
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from apl.dungeon import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.dungeon.env import Episode, LogEntry
from apl.dungeon.frames import build_frames, snapshot
from apl.dungeon.model import Dungeon
from apl.dungeon.render_html import CELL, MARGIN, svg
from apl.runner import registry
from apl.runner.episode import ModelFactory, PermanentProviderError, play_episode
from apl.runner.registry import Play
from apl.runner.results import write_json
from apl.runner.run import code_version, default_model_factory, package_versions
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.runner.vllm import with_server_context
from apl.viewer.events import EpisodeSession, ViewerCallbacks

Response = tuple[int, str, bytes]
LOCAL_PROVIDERS = ("ollama:", "vllm:")  # no cost, so no --execute needed (research R8)
MODELS = ("vllm:qwen3.5-9b", "openai:gpt-6-luna")  # the page's model switch, besides APL_MODEL
# Checked before any file access, so an id can never point outside results/viewer/.
EPISODE_ID = re.compile(r"\d{8}-\d{6}-[a-z0-9_]+-L[1-3]-\d+(-\d+)?")


def json_response(status: int, data: object) -> Response:
    return status, "application/json", json.dumps(data).encode()


def error(status: int, message: str) -> Response:
    return json_response(status, {"error": message})


@dataclass
class Viewer:
    settings: Settings  # the default model's (APL_MODEL)
    execute: bool = False
    models: Mapping[str, Settings] = field(default_factory=dict)  # the others the page offers
    results_dir: Path = Path("results/viewer")
    model_factory: ModelFactory | None = None  # None: the runner's default factory
    architectures: Mapping[str, Play] | None = None  # None: the registry
    running: EpisodeSession | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def choices(self) -> dict[str, Settings]:
        """The models the page can switch between, the default first."""
        default = self.settings.model
        return {default: self.settings} | {n: s for n, s in self.models.items() if n != default}

    def cannot_run_reason(self, model: str) -> str | None:
        if self.execute or model.startswith(LOCAL_PROVIDERS):
            return None
        return (
            f"{model} is a paid provider; start the viewer with "
            "`apl serve --execute` to run agents with it"
        )

    def architecture_names(self) -> list[str]:
        if self.architectures is not None:
            return sorted(self.architectures)
        return sorted(name for name in registry.ARCHITECTURES if registry.is_written(name))

    def options(self) -> Response:
        reason = self.cannot_run_reason(self.settings.model)
        return json_response(
            200,
            {
                "levels": sorted(LEVELS),
                "dev_seeds": list(DEV_SEEDS),
                "test_seeds": [TEST_SEEDS[0], TEST_SEEDS[-1]],
                "architectures": self.architecture_names(),
                "model": self.settings.model,
                "settings": self.settings.record(),
                "can_run": reason is None,
                "cannot_run_reason": reason,
                "models": [
                    {"name": name, "cannot_run_reason": self.cannot_run_reason(name)}
                    for name in self.choices()
                ],
            },
        )

    def dungeon(self, level: str, seed: str) -> Response:
        found = parse_dungeon(level, seed)
        if not isinstance(found, Dungeon):
            return found
        layout = found.layout
        frames = build_frames(found, found.solution.actions)
        data: dict[str, Any] = {
            "level": level,
            "seed": found.seed,
            "size": layout.size,
            "budget": found.budget,
            "optimal_steps": found.solution.length,
            "start": list(layout.start),
            "exit": list(layout.exit),
            "cell": CELL,
            "margin": MARGIN,
            "svg": svg(layout, animated=True),
            "solution": [f.to_dict() for f in frames],
        }
        return json_response(200, data)

    # ---------- episodes ----------

    def _play(self, arch: str) -> Play:
        return self.architectures[arch] if self.architectures is not None else registry.load(arch)

    def start_episode(self, body: object) -> Response:
        if not isinstance(body, dict):
            return error(400, "the request body must be a JSON object")
        arch, level, seed = body.get("arch"), body.get("level"), body.get("seed")
        model = body.get("model", self.settings.model)
        if not isinstance(arch, str) or arch not in self.architecture_names():
            return error(400, f"unknown or unwritten architecture {arch!r}")
        chosen = self.choices().get(model) if isinstance(model, str) else None
        if chosen is None:
            return error(400, f"unknown model {model!r} (models: {', '.join(self.choices())})")
        if not isinstance(seed, int) or isinstance(seed, bool):
            return error(400, f"seed must be a whole number ≥ 0, got {seed!r}")
        found = parse_dungeon(str(level), str(seed))
        if not isinstance(found, Dungeon):
            return found
        if (reason := self.cannot_run_reason(chosen.model)) is not None:
            return error(403, reason)
        try:
            settings = with_server_context(chosen)
        except ValueError as problem:
            return error(503, str(problem))
        with self._lock:
            if self.running is not None and not self.running.done:
                return json_response(
                    409,
                    {
                        "error": "an episode is already running; stop it or wait",
                        "running": self.running.id,
                    },
                )
            session = self._new_session(arch, str(level), seed)
            self.running = session
        key = EpisodeKey(arch, str(level), seed, 1)
        session.thread = threading.Thread(
            target=self._work, args=(session, key, settings), daemon=True
        )
        session.thread.start()
        return json_response(201, {"id": session.id})

    def _new_session(self, arch: str, level: str, seed: int) -> EpisodeSession:
        base = f"{datetime.now():%Y%m%d-%H%M%S}-{arch}-{level}-{seed}"
        for n in range(1, 1000):
            folder = self.results_dir / (base if n == 1 else f"{base}-{n}")
            try:
                folder.mkdir(parents=True)
                return EpisodeSession(folder.name, folder)
            except FileExistsError:
                continue
        raise RuntimeError(f"no free folder name for {base}")

    def _work(self, session: EpisodeSession, key: EpisodeKey, settings: Settings) -> None:
        started = datetime.now().astimezone().isoformat(timespec="seconds")
        record = settings.record()

        def on_episode(episode: Episode) -> None:
            session.episode = episode
            dungeon = episode.dungeon
            session.emit(
                "start",
                {
                    "arch": key.arch,
                    "level": key.level,
                    "seed": key.seed,
                    "model": settings.model,
                    "settings": record,
                    "budget": dungeon.budget,
                    "optimal_steps": dungeon.solution.length,
                    "frame": snapshot(episode, 0, None, None).to_dict(),
                    "started": started,
                },
            )

            def on_step(entry: LogEntry) -> None:
                frame = snapshot(episode, entry.index + 1, entry.action, entry.result)
                session.emit(
                    "step",
                    {
                        "index": entry.index,
                        "step": entry.step,
                        "call": session.call,
                        "action": entry.action.to_dict(),
                        "result": entry.result.to_dict(),
                        "frame": frame.to_dict(),
                    },
                )

            episode.on_step = on_step
            if session.stop_requested:
                episode.stop()

        row: dict[str, Any] | None = None
        problem: str | None = None
        try:
            result = play_episode(
                key,
                session.id,
                "dev",  # watching is development use; test seeds never get here
                settings,
                self._play(key.arch),
                self.model_factory or default_model_factory,
                callbacks=[ViewerCallbacks(session)],
                on_episode=on_episode,
            )
            row = result.row.to_dict()
            if result.outcome is not None:
                write_json(session.folder / "outcome.json", result.outcome.to_dict())
            if result.row.llm_calls:
                write_json(session.folder / "conversation.json", result.transcript.to_dict())
        except PermanentProviderError as failure:
            problem = f"the provider rejected the request: {failure}"
        except Exception as failure:  # a viewer or runner bug must still end the session
            problem = f"{type(failure).__name__}: {failure}"
        write_json(
            session.folder / "episode.json",
            {
                "row": row,
                "error": problem,
                "arch": key.arch,
                "level": key.level,
                "seed": key.seed,
                "settings": record,
                "code": code_version(),
                "versions": package_versions(),
                "started": started,
                "ended": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
        )
        session.emit("end", {"row": row, "error": problem, "saved": str(session.folder)})

    def stop_episode(self, episode_id: str) -> Response:
        session = self.running
        if session is None or session.id != episode_id or session.done:
            return error(404, f"no running episode {episode_id!r}")
        if not session.stop_requested:
            session.stop_requested = True
            if session.episode is not None:
                session.episode.stop()
            session.emit("stopping", {})
        return json_response(202, {"id": episode_id})

    def session(self, episode_id: str) -> EpisodeSession | None:
        """The running session, or a saved one loaded for replay; None if unknown."""
        if not EPISODE_ID.fullmatch(episode_id):
            return None
        running = self.running
        if running is not None and running.id == episode_id:
            return running
        folder = self.results_dir / episode_id
        if not (folder / "events.jsonl").is_file():
            return None
        return EpisodeSession.load(folder)

    def list_episodes(self) -> Response:
        running = self.running
        entries: list[dict[str, Any]] = []
        if running is not None and not running.done:
            start = running.events[0]["data"] if running.events else {}
            entries.append(
                {
                    "id": running.id,
                    "arch": start.get("arch"),
                    "level": start.get("level"),
                    "seed": start.get("seed"),
                    "model": start.get("model"),
                    "end_reason": None,
                    "steps": None,
                    "optimal_steps": start.get("optimal_steps"),
                    "started": start.get("started"),
                    "running": True,
                }
            )
        listed = {e["id"] for e in entries}  # episode.json is written just before `end`
        for path in sorted(self.results_dir.glob("*/episode.json"), reverse=True):  # newest first
            if not EPISODE_ID.fullmatch(path.parent.name) or path.parent.name in listed:
                continue
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # a damaged folder must not break the list
            row = saved.get("row") or {}
            entries.append(
                {
                    "id": path.parent.name,
                    "arch": saved.get("arch"),
                    "level": saved.get("level"),
                    "seed": saved.get("seed"),
                    "model": (saved.get("settings") or {}).get("model"),
                    "end_reason": "error"
                    if row.get("status", "error") == "error"
                    else row.get("end_reason"),
                    "steps": row.get("steps"),
                    "optimal_steps": row.get("optimal_steps"),
                    "started": saved.get("started"),
                    "running": False,
                }
            )
        return json_response(200, entries)

    def shutdown(self, timeout: float) -> None:
        """Stops a running episode and waits for it to be saved (Ctrl-C in `apl serve`)."""
        session = self.running
        if session is None or session.done:
            return
        self.stop_episode(session.id)
        if session.thread is not None:
            session.thread.join(timeout)


def parse_dungeon(level: str, seed: str) -> Dungeon | Response:
    """The dungeon for a request, or the error response (research R6)."""
    if level not in LEVELS:
        return error(400, f"unknown level {level!r} (levels: {', '.join(sorted(LEVELS))})")
    try:
        number = int(seed)
    except ValueError:
        return error(400, f"seed must be a whole number ≥ 0, got {seed!r}")
    if number in TEST_SEEDS:
        return error(
            403, f"seed {number} is a test seed; test seeds are reserved for reported results"
        )
    try:
        return generate(level, number)
    except ValueError as problem:
        return error(400, str(problem))
