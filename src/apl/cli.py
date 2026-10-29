"""The `apl` command line."""

import argparse
import json
import sys
from pathlib import Path

from apl.dungeon import LEVELS, generate
from apl.dungeon.frames import Frame, build_frames, parse_route_file
from apl.dungeon.model import Dungeon
from apl.dungeon.render_html import render_html
from apl.dungeon.render_text import render_text


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
    args = parser.parse_args(argv)
    if args.command == "dungeon" and args.dungeon_command == "show":
        return _show(args)
    (dungeon if args.command == "dungeon" else parser).print_help()
    return 2
