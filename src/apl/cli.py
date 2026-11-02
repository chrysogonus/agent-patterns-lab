"""The `apl` command line."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from apl.dungeon import LEVELS, generate
from apl.dungeon.frames import Frame, build_frames, parse_route_file
from apl.dungeon.model import Dungeon
from apl.dungeon.render_html import render_html
from apl.dungeon.render_text import render_text
from apl.problems import PROBLEMS

if TYPE_CHECKING:
    from apl.runner.episode import EpisodeResult
    from apl.runner.run import RunOutcome
    from apl.runner.settings import Settings
    from apl.runner.spec import RunSpec


def _frames(dungeon: Dungeon, route: str | None) -> list[Frame] | None:
    if route is None:
        return None
    if route == "solution":
        return build_frames(dungeon, dungeon.solution.actions)
    return parse_route_file(json.loads(Path(route).read_text())).frames(dungeon)


def _show(args: argparse.Namespace) -> int:
    try:
        dungeon = generate(args.level, args.seed)
        frames = _frames(dungeon, args.route)
        if args.html:
            Path(args.html).write_text(render_html(dungeon, frames), encoding="utf-8")
    except (OSError, ValueError) as error:  # JSONDecodeError is a ValueError
        print(f"apl: {error}", file=sys.stderr)
        return 2
    print(render_text(dungeon, frames), end="")
    return 0


def _survey_show(args: argparse.Namespace) -> int:
    from apl.survey import generate as generate_field
    from apl.survey.render_svg import html
    from apl.survey.render_text import render_text as render_field

    try:
        field = generate_field(args.level, args.seed)
        if args.html:
            Path(args.html).write_text(html(field), encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    print(render_field(field, route=args.route == "reference"), end="")
    return 0


def _signal_show(args: argparse.Namespace) -> int:
    from apl.signal_trace import generate as generate_pipe
    from apl.signal_trace.render_svg import html
    from apl.signal_trace.render_text import render_text as render_pipe

    try:
        pipe = generate_pipe(args.level, args.seed)
        if args.html:
            Path(args.html).write_text(html(pipe), encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    print(render_pipe(pipe, route=args.route == "reference"), end="")
    return 0


def _rune_show(args: argparse.Namespace) -> int:
    from apl.rune import generate as generate_floor
    from apl.rune.render_svg import html
    from apl.rune.render_text import render_text as render_floor

    try:
        floor = generate_floor(args.level, args.seed)
        if args.html:
            Path(args.html).write_text(html(floor), encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    print(render_floor(floor, route=args.route == "reference"), end="")
    return 0


def _workshop_show(args: argparse.Namespace) -> int:
    from apl.workshop import generate as generate_workshop
    from apl.workshop.render_svg import html
    from apl.workshop.render_text import render_text as render_workshop

    try:
        workshop = generate_workshop(args.level, args.seed)
        if args.html:
            Path(args.html).write_text(html(workshop), encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    print(render_workshop(workshop, route=args.route == "reference"), end="")
    return 0


def _csv(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _run(args: argparse.Namespace) -> int:
    # LangChain is imported only here, so `apl dungeon show` stays fast.
    from apl.runner import registry
    from apl.runner.settings import load_settings
    from apl.runner.spec import RunSpec, format_plan

    try:
        only = [int(s) for s in _csv(args.only)] if args.only is not None else None
    except ValueError:
        print("apl: --only takes seed numbers, e.g. --only 1000,1004", file=sys.stderr)
        return 2
    try:
        settings = load_settings()
        spec = RunSpec.build(
            _csv(args.arch),
            _csv(args.level),
            args.seeds,
            args.limit,
            only,
            args.repeats,
            problem=args.problem,
        )
    except ValueError as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    written = {name: registry.is_written(name) for name in spec.architectures}
    if not args.execute:
        from apl.runner.run import code_version

        print(format_plan(spec, settings, written, code_version()))
        return 0
    return _execute(spec, settings)


def _progress(i: int, n: int, result: "EpisodeResult") -> None:
    row = result.row
    head = f"[{i}/{n}] {row.arch} {row.level} {row.seed} r{row.repeat}"
    if row.status == "error":
        print(f"{head}  error  {row.error}", flush=True)
        return
    tokens = "?" if row.input_tokens is None else f"{row.input_tokens + (row.output_tokens or 0):,}"
    print(
        f"{head}  {row.end_reason}  steps {row.steps}/{row.budget} (optimal {row.optimal_steps})"
        f"  calls {row.llm_calls}  tokens {tokens}  {row.latency_s:.1f}s",
        flush=True,
    )


def _execute(spec: "RunSpec", settings: "Settings") -> int:
    from apl.runner import registry, run
    from apl.runner.settings import required_key_var
    from apl.runner.vllm import with_server_context

    key_var = required_key_var(settings.model)
    if key_var and not os.environ.get(key_var):
        print(f"apl: {key_var} is not set (needed for {settings.model})", file=sys.stderr)
        return 2
    try:
        plays = {name: registry.load(name) for name in spec.architectures}
        settings = with_server_context(settings)
    except ValueError as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    outcome = run.execute(
        spec,
        settings,
        model_factory=run.default_model_factory,
        architectures=plays,
        on_episode=_progress,
    )
    return _finish(outcome)


def _finish(outcome: "RunOutcome") -> int:
    """The end of `apl run --execute` and `apl continue --execute` (specs/004 contracts/cli.md)."""
    print(outcome.path)
    if outcome.exit_code == 130:
        print("apl: interrupted; finished episodes are kept, the run is marked incomplete")
    elif outcome.exit_code == 3:
        print(
            f"apl: the provider rejected a request, run stopped: {outcome.error}", file=sys.stderr
        )
    elif outcome.exit_code == 4:
        print(f"apl: {outcome.error}. Fix it, then continue the run.", file=sys.stderr)
    if outcome.exit_code:
        print(f"continue with: uv run apl continue {outcome.path} --execute")
        return outcome.exit_code
    return _report([outcome.path])


def _continue(args: argparse.Namespace) -> int:
    from apl.runner import registry, run
    from apl.runner.settings import load_settings, required_key_var
    from apl.runner.spec import format_limits, upper_bounds
    from apl.runner.vllm import with_server_context

    try:
        settings = with_server_context(load_settings())  # the run recorded the server's context
        written = {name: registry.is_written(name) for name in registry.ARCHITECTURES}
        plan = run.plan_continue(
            args.run_dir,
            settings,
            code=run.code_version(),
            versions=run.package_versions(),
            written=written,
        )
    except ValueError as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    if plan.refusals:
        lines = "\n".join(f"  {r}" for r in plan.refusals)
        print(f"apl: cannot continue {plan.record.run_id}:\n{lines}", file=sys.stderr)
        return 2
    if plan.complete:
        print(f"run {plan.record.run_id} is already complete; nothing to play.")
        return 0
    if not args.execute and not plan.left:
        print(
            f"run {plan.record.run_id}: every episode has a row; --execute marks the run complete "
            "and writes report.md."
        )
        return 0
    if not args.execute:
        record = plan.record
        total = len(plan.done) + len(plan.left)
        nxt = plan.left[0]
        rows = [
            ("done", f"{len(plan.done)} of {total} episodes"),
            ("left", str(len(plan.left))),
            ("next", f"{nxt.arch} {nxt.level} {nxt.seed} r{nxt.repeat}"),
            ("model", settings.model),
            ("code", str(record.code.get("commit") or "unknown")[:7]),
        ]
        print(f"Continue run {record.run_id} (dry run, nothing is sent or written)")
        print("\n".join(f"  {k:<15}{v}" for k, v in rows))
        if plan.cut_off:
            print("  a cut-off last row will be removed")
        bounds = upper_bounds(plan.left, settings, plan.record.problem)
        print("\n".join(format_limits(bounds, settings)))
        print("Run with --execute to continue it (a paid provider then costs money).")
        return 0
    key_var = required_key_var(settings.model)
    if key_var and not os.environ.get(key_var):
        print(f"apl: {key_var} is not set (needed for {settings.model})", file=sys.stderr)
        return 2
    plays = {name: registry.load(name) for name in plan.record.architectures}
    outcome = run.continue_run(
        plan,
        settings,
        model_factory=run.default_model_factory,
        architectures=plays,
        on_episode=_progress,
    )
    return _finish(outcome)


def _report(paths: list[Path]) -> int:
    from apl.runner.report import load_run, render

    try:
        report = render([load_run(path) for path in paths])
    except ValueError as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    if len(paths) == 1:
        out = paths[0] / "report.md"
    else:
        out = Path("results") / f"report-{datetime.now():%Y%m%d-%H%M%S}.md"
        out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"(written to {out})")
    return 0


def _serve(args: argparse.Namespace) -> int:
    from apl.runner.settings import load_settings
    from apl.runner.vllm import with_server_context
    from apl.viewer.app import MODELS, Viewer
    from apl.viewer.server import make_server

    try:
        settings = load_settings()
    except ValueError as error:
        print(f"apl: {error}", file=sys.stderr)
        return 2
    try:
        settings = with_server_context(settings)
    except ValueError as error:  # browsing and replay still work; starting an agent will fail
        print(f"apl: warning: {error}", file=sys.stderr)
    # The same .env settings for each model; only the model (and its output default) differs.
    models = {name: load_settings({**os.environ, "APL_MODEL": name}) for name in MODELS}
    viewer = Viewer(settings, execute=args.execute, models=models)
    try:
        server = make_server(viewer, args.port)
    except OSError as error:
        print(f"apl: cannot listen on 127.0.0.1:{args.port}: {error}", file=sys.stderr)
        return 2
    print(
        f"Viewer: http://127.0.0.1:{args.port}/ (model {settings.model}; Ctrl-C to stop)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("apl: stopping; a running episode is stopped and saved", flush=True)
        viewer.shutdown(timeout=settings.timeout_s)
        return 130
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apl")
    commands = parser.add_subparsers(dest="command")
    dungeon = commands.add_parser("dungeon", help="inspect generated dungeons")
    dungeon_commands = dungeon.add_subparsers(dest="dungeon_command")
    show = dungeon_commands.add_parser("show", help="print a dungeon as a text map")
    show.add_argument("--level", required=True, choices=sorted(LEVELS))
    show.add_argument("--seed", required=True, type=int)
    show.add_argument("--route", help='"solution", or a route file (contracts/cli.md)')
    show.add_argument("--html", metavar="OUT", help="also write a picture; animated with --route")
    survey = commands.add_parser("survey", help="inspect generated survey fields")
    survey_commands = survey.add_subparsers(dest="survey_command")
    field_show = survey_commands.add_parser("show", help="print a survey field as a text map")
    field_show.add_argument("--level", required=True, choices=["S1", "S2", "S3"])
    field_show.add_argument("--seed", required=True, type=int)
    field_show.add_argument("--route", choices=["reference"], help="number the reference walk")
    field_show.add_argument("--html", metavar="OUT", help="also write a picture")
    signal = commands.add_parser("signal", help="inspect generated signal trace pipes")
    signal_commands = signal.add_subparsers(dest="signal_command")
    pipe_show = signal_commands.add_parser("show", help="print a pipe as text")
    pipe_show.add_argument("--level", required=True, choices=["T1", "T2", "T3"])
    pipe_show.add_argument("--seed", required=True, type=int)
    pipe_show.add_argument("--route", choices=["reference"], help="list the reference probes")
    pipe_show.add_argument("--html", metavar="OUT", help="also write a picture")
    rune = commands.add_parser("rune", help="inspect generated rune floors")
    rune_commands = rune.add_subparsers(dest="rune_command")
    floor_show = rune_commands.add_parser("show", help="print a rune floor as text")
    floor_show.add_argument("--level", required=True, choices=["R0", "R1", "R2", "R3"])
    floor_show.add_argument("--seed", required=True, type=int)
    floor_show.add_argument("--route", choices=["reference"], help="list the reference path")
    floor_show.add_argument("--html", metavar="OUT", help="also write a picture")
    workshop = commands.add_parser("workshop", help="inspect generated workshops")
    workshop_commands = workshop.add_subparsers(dest="workshop_command")
    tree_show = workshop_commands.add_parser("show", help="print a workshop as text")
    tree_show.add_argument("--level", required=True, choices=["W1", "W2", "W3"])
    tree_show.add_argument("--seed", required=True, type=int)
    tree_show.add_argument("--route", choices=["reference"], help="list the reference plan")
    tree_show.add_argument("--html", metavar="OUT", help="also write a picture")
    run = commands.add_parser("run", help="plan a run, or play it with --execute")
    run.add_argument(
        "--problem", default="dungeon", choices=list(PROBLEMS), help="default: dungeon"
    )
    run.add_argument("--arch", required=True, help="architecture names, comma-separated")
    run.add_argument("--level", required=True, help="the problem's levels, comma-separated, or all")
    run.add_argument("--seeds", required=True, help="the seed set: dev or test")
    run.add_argument("--limit", type=int, help="only the first K seeds of the set")
    run.add_argument("--only", help="only these seeds of the set, comma-separated")
    run.add_argument("--repeats", type=int, default=1, help="repeats per seed (default 1)")
    run.add_argument("--execute", action="store_true", help="actually run: this costs money")
    serve = commands.add_parser("serve", help="open the viewer: watch agents play live")
    serve.add_argument("--port", type=int, default=8765, help="port on 127.0.0.1 (default 8765)")
    serve.add_argument(
        "--execute", action="store_true", help="allow agents with a paid provider: costs money"
    )
    resume = commands.add_parser("continue", help="plan or play the rest of an interrupted run")
    resume.add_argument("run_dir", type=Path, metavar="RUN_DIR")
    resume.add_argument("--execute", action="store_true", help="actually play: this costs money")
    report = commands.add_parser("report", help="build a report from run folders")
    report.add_argument("runs", nargs="+", type=Path, metavar="RUN_DIR")
    args = parser.parse_args(argv)
    if args.command == "dungeon" and args.dungeon_command == "show":
        return _show(args)
    if args.command == "survey" and args.survey_command == "show":
        return _survey_show(args)
    if args.command == "signal" and args.signal_command == "show":
        return _signal_show(args)
    if args.command == "rune" and args.rune_command == "show":
        return _rune_show(args)
    if args.command == "workshop" and args.workshop_command == "show":
        return _workshop_show(args)
    if args.command == "run":
        return _run(args)
    if args.command == "report":
        return _report(args.runs)
    if args.command == "continue":
        return _continue(args)
    if args.command == "serve":
        return _serve(args)
    groups = {
        "dungeon": dungeon, "survey": survey, "signal": signal, "rune": rune, "workshop": workshop,
    }  # fmt: skip
    groups.get(args.command, parser).print_help()
    return 2
