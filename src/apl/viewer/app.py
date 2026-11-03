"""The viewer's request logic as plain functions, testable without sockets (research R1).

Each handler returns `(status, content type, body)`; `server.py` only does the HTTP part.
"""

import json
import re
import threading
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from apl import problems
from apl.dungeon import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.dungeon.frames import build_frames, snapshot
from apl.dungeon.model import Dungeon
from apl.dungeon.render_html import CELL, MARGIN, svg
from apl.rune import Floor
from apl.rune import start_episode as start_rune
from apl.rune.frames import reference_frames as reference_walk
from apl.rune.frames import snapshot as rune_snapshot
from apl.rune.render_svg import svg as floor_svg
from apl.rune.rules import describe as describe_rule
from apl.runner import registry
from apl.runner.episode import ModelFactory, PermanentProviderError, play_episode
from apl.runner.registry import Play
from apl.runner.results import write_json
from apl.runner.run import code_version, default_model_factory, package_versions
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.runner.vllm import with_server_context
from apl.signal_trace import Pipe
from apl.signal_trace import start_episode as start_signal
from apl.signal_trace.frames import reference_frames as reference_probes
from apl.signal_trace.frames import snapshot as signal_snapshot
from apl.signal_trace.render_svg import svg as pipe_svg
from apl.survey import Field
from apl.survey.frames import reference_frames
from apl.survey.frames import snapshot as survey_snapshot
from apl.survey.render_svg import CELL as FIELD_CELL
from apl.survey.render_svg import MARGIN as FIELD_MARGIN
from apl.survey.render_svg import svg as field_svg
from apl.viewer.about import about
from apl.viewer.events import EpisodeSession, ViewerCallbacks
from apl.warehouse import Floor as WarehouseFloor
from apl.warehouse.frames import reference_frames as reference_delivery
from apl.warehouse.frames import snapshot as warehouse_snapshot
from apl.warehouse.render_svg import CELL as HALL_CELL
from apl.warehouse.render_svg import MARGIN as HALL_MARGIN
from apl.warehouse.render_svg import svg as warehouse_svg
from apl.workshop import Workshop
from apl.workshop.frames import reference_frames as reference_plan
from apl.workshop.frames import snapshot as workshop_snapshot
from apl.workshop.render_svg import svg as workshop_svg

Response = tuple[int, str, bytes]
LOCAL_PROVIDERS = ("ollama:", "vllm:")  # no cost, so no --execute needed (research R8)
MODELS = ("vllm:qwen3.5-9b", "openai:gpt-6-luna")  # the page's model switch, besides APL_MODEL
# Checked before any file access, so an id can never point outside results/viewer/.
EPISODE_ID = re.compile(r"\d{8}-\d{6}-[a-z0-9_]+-(?:[LSTWP][1-3]|R[0-3])-\d+(-\d+)?")


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

    def plays(self, name: str, problem: str) -> bool:
        return registry.plays(name, problem)

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
                "problems": {
                    name: {
                        "levels": sorted(p.levels),
                        "dev_seeds": list(p.dev_seeds),
                        "test_seeds": [p.test_seeds[0], p.test_seeds[-1]],
                        "architectures": [
                            a for a in self.architecture_names() if self.plays(a, name)
                        ],
                        # What each architecture defines on this game, for the About card.
                        "about": {
                            a: asdict(card)
                            for a in self.architecture_names()
                            if self.plays(a, name) and (card := about(a, name)) is not None
                        },
                    }
                    for name, p in problems.PROBLEMS.items()
                },
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

    def survey(self, level: str, seed: str) -> Response:
        found = parse_field(level, seed)
        if not isinstance(found, Field):
            return found
        data: dict[str, Any] = {
            "problem": "survey",
            "level": level,
            "seed": found.seed,
            "size": found.size,
            "budget": found.budget,
            "optimal_steps": found.reference_steps,
            "reference_is_optimal": found.reference_is_optimal,
            "true_total": found.true_total,
            "start": list(found.start),
            "cell": FIELD_CELL,
            "margin": FIELD_MARGIN,
            "svg": field_svg(found, animated=True),
            "solution": reference_frames(found),
        }
        return json_response(200, data)

    def signal(self, level: str, seed: str) -> Response:
        """A pipe for the page (specs/009 contracts/viewer.md); test seeds are refused."""
        found = parse_pipe(level, seed)
        if not isinstance(found, Pipe):
            return found
        data: dict[str, Any] = {
            "problem": "signal",
            "level": level,
            "seed": found.seed,
            "segments": found.segments,
            "runs": _runs(found),
            "broken": found.broken,
            "budget": found.budget,
            "optimal_steps": found.reference_steps,
            "reference_is_optimal": found.reference_is_optimal,
            "svg": pipe_svg(found, animated=True),
            "solution": reference_probes(found),
        }
        return json_response(200, data)

    def rune(self, level: str, seed: str) -> Response:
        """A rune floor for the page (specs/010 contracts/viewer.md); test seeds are refused."""
        found = parse_floor(level, seed)
        if not isinstance(found, Floor):
            return found
        view = start_rune(found).describe().to_dict()
        data: dict[str, Any] = {
            "problem": "rune",
            "level": level,
            "seed": found.seed,
            "columns": found.columns,
            "rows": found.rows,
            "start": view["start"],
            "goal": view["goal"],
            "floor": view["floor"],
            "rule": describe_rule(found.rule),
            "budget": found.budget,
            "optimal_steps": found.reference_steps,
            "reference_is_optimal": found.reference_is_optimal,
            "svg": floor_svg(found, animated=True),
            "solution": reference_walk(found),
        }
        return json_response(200, data)

    def workshop(self, level: str, seed: str) -> Response:
        """A workshop for the page (specs/011 contracts/viewer.md); test seeds are refused."""
        found = parse_workshop(level, seed)
        if not isinstance(found, Workshop):
            return found
        data: dict[str, Any] = {
            "problem": "workshop",
            "level": level,
            "seed": found.seed,
            "goal": found.goal,
            "stock": dict(found.stock),
            "scarce": sorted(found.scarce),
            "recipes": {k: [list(r) for r in v] for k, v in found.recipes.items()},
            "reference_choice": dict(found.reference_choice),
            "budget": found.budget,
            "optimal_steps": found.reference_steps,
            "reference_is_optimal": found.reference_is_optimal,
            "svg": workshop_svg(found, animated=True),
            "solution": reference_plan(found),
        }
        return json_response(200, data)

    def warehouse(self, level: str, seed: str) -> Response:
        """A warehouse for the page (specs/012 contracts/viewer.md); test seeds are refused."""
        found = parse_warehouse(level, seed)
        if not isinstance(found, WarehouseFloor):
            return found
        data: dict[str, Any] = {
            "problem": "warehouse",
            "level": level,
            "seed": found.seed,
            "columns": found.columns,
            "rows": found.rows,
            "packages": len(found.packages),
            "budget": found.budget,
            "optimal_steps": found.reference_steps,
            "reference_is_optimal": found.reference_is_optimal,
            "cell": HALL_CELL,
            "margin": HALL_MARGIN,
            "svg": warehouse_svg(found, animated=True),
            "solution": reference_delivery(found),
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
        problem = body.get("problem", problems.DEFAULT)
        if not isinstance(problem, str) or problem not in problems.PROBLEMS:
            names = ", ".join(problems.PROBLEMS)
            return error(400, f"unknown problem {problem!r} (problems: {names})")
        if not isinstance(arch, str) or arch not in self.architecture_names():
            return error(400, f"unknown or unwritten architecture {arch!r}")
        if not self.plays(arch, problem):
            return error(400, registry.refusal(arch, problem))
        chosen = self.choices().get(model) if isinstance(model, str) else None
        if chosen is None:
            return error(400, f"unknown model {model!r} (models: {', '.join(self.choices())})")
        if not isinstance(seed, int) or isinstance(seed, bool):
            return error(400, f"seed must be a whole number ≥ 0, got {seed!r}")
        parsers = {
            "survey": parse_field, "signal": parse_pipe, "rune": parse_floor,
            "workshop": parse_workshop, "warehouse": parse_warehouse,
        }  # fmt: skip
        parse = parsers.get(problem, parse_dungeon)
        world = parse(str(level), str(seed))
        if isinstance(world, tuple):
            return world
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
            target=self._work, args=(session, key, settings, problem), daemon=True
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

    def _work(
        self,
        session: EpisodeSession,
        key: EpisodeKey,
        settings: Settings,
        problem: str = problems.DEFAULT,
    ) -> None:
        started = datetime.now().astimezone().isoformat(timespec="seconds")
        record = settings.record(problem)
        survey = problem == "survey"
        signal = problem == "signal"  # specs/009
        rune = problem == "rune"  # specs/010
        workshop = problem == "workshop"  # specs/011
        warehouse = problem == "warehouse"  # specs/012

        def frame_of(episode: Any, index: int, action: Any, result: Any) -> dict[str, Any]:
            if survey:
                return survey_snapshot(episode, index, action, result)
            if signal:
                return signal_snapshot(episode, index, action, result)
            if rune:
                return rune_snapshot(episode, index, action, result)
            if workshop:
                return workshop_snapshot(episode, index, action, result)
            if warehouse:
                return warehouse_snapshot(episode, index, action, result)
            return snapshot(episode, index, action, result).to_dict()

        def on_episode(episode: Any) -> None:
            session.episode = episode
            if signal:
                world = episode.pipe
            elif rune or warehouse:
                world = episode.floor
            elif workshop:
                world = episode.workshop
            else:
                world = episode.field if survey else episode.dungeon
            session.emit(
                "start",
                {
                    "arch": key.arch,
                    "level": key.level,
                    "seed": key.seed,
                    "model": settings.model,
                    "settings": record,
                    "budget": world.budget,
                    "optimal_steps": problems.get(problem).reference_steps(world),
                    "frame": frame_of(episode, 0, None, None),
                    "started": started,
                    # Survey episodes say so; dungeon events stay as they were (specs/005).
                    **({"problem": problem, "true_total": world.true_total} if survey else {}),
                    **(
                        {"problem": problem, "segments": world.segments, "broken": world.broken}
                        if signal
                        else {}
                    ),
                    **(_rune_start(world) if rune else {}),
                    **(_workshop_start(world) if workshop else {}),
                    **(_warehouse_start(world) if warehouse else {}),
                    # A retrying architecture's cap; other events stay as they were (specs/007).
                    **({"attempts": episode.max_attempts} if episode.max_attempts > 1 else {}),
                },
            )

            def on_step(entry: Any) -> None:
                frame = frame_of(episode, entry.index + 1, entry.action, entry.result)
                session.emit(
                    "step",
                    {
                        "index": entry.index,
                        "step": entry.step,
                        "scout": entry.scout,
                        # The turn that made the call: its scout's latest one, if roles are used.
                        "call": session.latest_call.get(f"scout {entry.scout}", session.call),
                        "action": entry.action.to_dict(),
                        "result": entry.result.to_dict(),
                        "frame": frame,
                    },
                )

            episode.on_step = on_step

            def on_restart() -> None:  # A4's next attempt (specs/007 research R8)
                frame = frame_of(episode, len(episode.log), None, None)
                data = {"attempt": episode.attempt, "of": episode.max_attempts, "frame": frame}
                session.emit("restart", data)

            episode.on_restart = on_restart
            if session.stop_requested:
                episode.stop()

        row: dict[str, Any] | None = None
        trouble: str | None = None
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
                problem=problem,
            )
            row = result.row.to_dict()
            if result.outcome is not None:
                write_json(session.folder / "outcome.json", result.outcome.to_dict())
            if result.row.llm_calls:
                write_json(session.folder / "conversation.json", result.transcript.to_dict())
        except PermanentProviderError as failure:
            trouble = f"the provider rejected the request: {failure}"
        except Exception as failure:  # a viewer or runner bug must still end the session
            trouble = f"{type(failure).__name__}: {failure}"
        write_json(
            session.folder / "episode.json",
            {
                "row": row,
                "error": trouble,
                "arch": key.arch,
                **(
                    {"problem": problem}
                    if survey or signal or rune or workshop or warehouse
                    else {}
                ),
                "level": key.level,
                "seed": key.seed,
                "settings": record,
                "code": code_version(),
                "versions": package_versions(),
                "started": started,
                "ended": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
        )
        session.emit("end", {"row": row, "error": trouble, "saved": str(session.folder)})

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
                    "problem": start.get("problem", problems.DEFAULT),
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
                    "problem": saved.get("problem", problems.DEFAULT),
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


def parse_field(level: str, seed: str) -> Field | Response:
    """The survey field for a request, or the error response; test seeds are refused."""
    found: Field | Response = _parse_world("survey", level, seed)
    return found


def parse_pipe(level: str, seed: str) -> Pipe | Response:
    """The signal-trace pipe for a request, or the error response; test seeds are refused."""
    found: Pipe | Response = _parse_world("signal", level, seed)
    return found


def parse_floor(level: str, seed: str) -> Floor | Response:
    """The rune floor for a request, or the error response; test seeds are refused."""
    found: Floor | Response = _parse_world("rune", level, seed)
    return found


def parse_workshop(level: str, seed: str) -> Workshop | Response:
    """The workshop for a request, or the error response; test seeds are refused."""
    found: Workshop | Response = _parse_world("workshop", level, seed)
    return found


def parse_warehouse(level: str, seed: str) -> WarehouseFloor | Response:
    """The warehouse for a request, or the error response; test seeds are refused."""
    found: WarehouseFloor | Response = _parse_world("warehouse", level, seed)
    return found


def _warehouse_start(floor: WarehouseFloor) -> dict[str, Any]:
    """What a warehouse episode's start event adds (specs/012 contracts/viewer.md)."""
    return {
        "problem": "warehouse",
        "packages": len(floor.packages),
        "columns": floor.columns,
        "rows": floor.rows,
    }


def _workshop_start(workshop: Workshop) -> dict[str, Any]:
    """What a workshop episode's start event adds (specs/011 contracts/viewer.md)."""
    return {
        "problem": "workshop",
        "goal": workshop.goal,
        "stock": dict(workshop.stock),
        "scarce": sorted(workshop.scarce),
    }


def _rune_start(floor: Floor) -> dict[str, Any]:
    """What a rune episode's start event adds (specs/010 contracts/viewer.md)."""
    view = start_rune(floor).describe().to_dict()
    return {
        "problem": "rune",
        "columns": floor.columns,
        "rows": floor.rows,
        "start": view["start"],
        "goal": view["goal"],
    }


def _parse_world(problem: str, level: str, seed: str) -> Any:
    """A problem's world for a request, or the error response (specs/005, specs/009)."""
    chosen = problems.get(problem)
    if level not in chosen.levels:
        return error(400, f"unknown level {level!r} (levels: {', '.join(sorted(chosen.levels))})")
    try:
        number = int(seed)
    except ValueError:
        return error(400, f"seed must be a whole number ≥ 0, got {seed!r}")
    if number in chosen.test_seeds:
        return error(
            403, f"seed {number} is a test seed; test seeds are reserved for reported results"
        )
    return chosen.generate(level, number)


def _runs(pipe: Pipe) -> list[object]:
    """The layout's runs as the agent sees them in its free start view."""
    runs = start_signal(pipe).describe().to_dict()["runs"]
    assert isinstance(runs, list)
    return runs


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
