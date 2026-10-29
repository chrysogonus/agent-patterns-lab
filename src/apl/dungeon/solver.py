"""Breadth-first solver over (room, keys taken, doors opened). Runner side only."""

from collections import deque

from apl.dungeon.model import Action, Direction, Layout, Pos, Solution, key_name

State = tuple[Pos, int, int]  # room, bitmask of keys taken, bitmask of locked doors opened


def solve(layout: Layout) -> Solution | None:
    """Return a shortest solution, or None if the exit cannot be reached."""
    colors = sorted(layout.keys)
    color_bit = {c: 1 << i for i, c in enumerate(colors)}
    door_bit = {e: 1 << i for i, e in enumerate(sorted(layout.locks))}

    def successors(state: State) -> list[tuple[State, Action]]:
        room, held, opened = state
        out: list[tuple[State, Action]] = []
        for color in colors:
            if layout.keys[color] == room and not held & color_bit[color]:
                out.append(
                    ((room, held | color_bit[color], opened), Action("take", (key_name(color),)))
                )
        for direction in Direction:
            edge = layout.door(room, direction)
            if edge in door_bit and not opened & door_bit[edge]:
                color = layout.locks[edge]
                if held & color_bit[color]:
                    action = Action("use", (key_name(color), str(direction)))
                    out.append(((room, held, opened | door_bit[edge]), action))
        for direction in Direction:
            edge = layout.door(room, direction)
            if edge is not None and (edge not in door_bit or opened & door_bit[edge]):
                out.append(((edge.other(room), held, opened), Action("move", (str(direction),))))
        return out

    start: State = (layout.start, 0, 0)
    parent: dict[State, tuple[State, Action] | None] = {start: None}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        if state[0] == layout.exit:
            actions: list[Action] = []
            step = parent[state]
            while step is not None:
                state, action = step
                actions.append(action)
                step = parent[state]
            return Solution(tuple(reversed(actions)))
        for nxt, action in successors(state):
            if nxt not in parent:
                parent[nxt] = (state, action)
                queue.append(nxt)
    return None
