"""Seeded dungeon generator (research R1–R3). Runner side only."""

import random

from apl.dungeon.model import LEVELS, Dungeon, Edge, Layout, Level, Pos
from apl.dungeon.rules import check_level_rules, distances
from apl.dungeon.solver import solve

LABEL_POOL = tuple(f"{c}{d}" for c in "abcdefghjkmnpqrstuvwxyz" for d in "23456789")
COLORS = ("red", "blue", "green", "yellow")
MAX_ATTEMPTS = 1000


def generate(level_name: str, seed: int) -> Dungeon:
    """The dungeon for this level and seed: identical on every run and machine (FR-009)."""
    if level_name not in LEVELS:
        raise ValueError(f"unknown level {level_name!r}; choose one of {', '.join(LEVELS)}")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError(f"seed must be a whole number ≥ 0, got {seed!r}")
    level = LEVELS[level_name]
    # String seeds are hashed with SHA-512, so this is stable across machines.
    rng = random.Random(f"apl:{level.name}:{seed}")
    for _ in range(MAX_ATTEMPTS):
        layout = _attempt(level, rng)
        if layout is None or check_level_rules(layout, level):
            continue
        solution = solve(layout)
        if solution is not None:
            return Dungeon(level, seed, layout, solution)
    raise RuntimeError(f"no valid {level_name} dungeon after {MAX_ATTEMPTS} attempts (seed {seed})")


def _attempt(level: Level, rng: random.Random) -> Layout | None:
    n = level.size
    rooms = [(x, y) for y in range(n) for x in range(n)]

    # 1. Spanning tree: randomized Kruskal over all neighbor pairs.
    pairs = [Edge((x, y), (x + 1, y)) for y in range(n) for x in range(n - 1)]
    pairs += [Edge((x, y), (x, y + 1)) for y in range(n - 1) for x in range(n)]
    rng.shuffle(pairs)
    root = {p: p for p in rooms}

    def find(p: Pos) -> Pos:
        while root[p] != p:
            root[p] = root[root[p]]
            p = root[p]
        return p

    tree: list[Edge] = []
    rest: list[Edge] = []
    for edge in pairs:
        ra, rb = find(edge.a), find(edge.b)
        if ra == rb:
            rest.append(edge)
        else:
            root[ra] = rb
            tree.append(edge)
    tree_doors = frozenset(tree)

    # 2. Start and exit: a random pair at least 2·(N−1) apart in the tree.
    far = [
        (p, q)
        for i, p in enumerate(rooms)
        for q, d in sorted(distances(_grid(n), p, tree_doors).items())
        if rooms.index(q) > i and d >= 2 * (n - 1)
    ]
    start, exit = rng.choice(far)
    if rng.random() < 0.5:
        start, exit = exit, start

    # 3. Locked doors on the tree path from start to exit, in path order.
    path = _tree_path(n, tree_doors, start, exit)
    path_edges = [Edge(a, b) for a, b in zip(path, path[1:], strict=False)]
    lock_idx = sorted(rng.sample(range(len(path_edges)), level.locks))
    lock_edges = [path_edges[i] for i in lock_idx]
    colors = rng.sample(COLORS, level.locks)

    # 4. Extra doors only inside a region, so loops never bypass a lock.
    region: dict[Pos, int] = {}
    for i, start_side in enumerate([start, *(path[k + 1] for k in lock_idx)]):
        for room in distances(_grid(n), start_side, tree_doors - set(lock_edges)):
            region.setdefault(room, i)
    inside = [e for e in rest if region[e.a] == region[e.b]]
    if len(inside) < level.extra_doors:
        return None
    doors = tree_doors | set(rng.sample(inside, level.extra_doors))

    # 5. Keys: in the region in front of their door, off the shortest route to it.
    full = distances(_grid(n), start, doors)
    keys: dict[str, Pos] = {}
    for i, (k, color) in enumerate(zip(lock_idx, colors, strict=True)):
        near = path[k]
        candidates = [
            r
            for r in rooms
            if region[r] == i
            and r != start
            and full[r] + distances(_grid(n), r, doors)[near] != full[near]
        ]
        if not candidates:
            return None
        keys[color] = rng.choice(candidates)

    # 6. Labels: a random draw from the pool, independent of position and layout.
    labels = dict(zip(rooms, rng.sample(LABEL_POOL, n * n), strict=True))
    locks = dict(zip(lock_edges, colors, strict=True))
    return Layout(n, doors, locks, keys, start, exit, labels)


def _grid(n: int) -> Layout:
    """An empty n×n layout, used only for its grid bounds in distance searches."""
    return Layout(n, frozenset(), {}, {}, (0, 0), (0, 0), {})


def _tree_path(n: int, doors: frozenset[Edge], start: Pos, exit: Pos) -> list[Pos]:
    dist = distances(_grid(n), exit, doors)
    path = [start]
    while path[-1] != exit:
        here = path[-1]
        path.append(
            next(
                e.other(here)
                for e in sorted(doors)
                if here in (e.a, e.b) and dist.get(e.other(here)) == dist[here] - 1
            )
        )
    return path
