"""A2's explicit memory on the signal trace: the layout and every probe answer (specs/009 R11).

It reads the result JSON the model also sees, never the environment (Constitution II). `render`
draws no conclusion from the answers; `suspects` (A6 only) applies the probe rule to them, a copy
of the rule in the runner's strategy module, which architectures may not import. Written by the
agent at the experimenter's request.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RunNote:
    feeder: int  # 0 is S
    first: int
    last: int

    def render(self) -> str:
        source = "S" if self.feeder == 0 else str(self.feeder)
        span = str(self.first) if self.first == self.last else f"{self.first}–{self.last}"
        return f"{source} → {span}"


def _runs(layout: Mapping[str, Any]) -> list[RunNote]:
    return [
        RunNote(0 if r["from"] == "S" else int(r["from"]), int(r["first"]), int(r["last"]))
        for r in layout["runs"]
    ]


@dataclass
class ProbeLog:
    segments: int
    runs: list[RunNote]
    answers: list[tuple[int, bool]] = field(default_factory=list)  # in the order given

    @classmethod
    def from_start(cls, start_json: str) -> "ProbeLog":
        data = json.loads(start_json)["data"]
        return cls(int(data["segments"]), _runs(data))

    def apply(self, name: str, args: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        """Update from one call and its result; failed calls change nothing."""
        if not result.get("ok"):
            return
        data = result["data"]
        if name == "probe":
            self.answers.append((int(data["segment"]), bool(data["water"])))
        elif name == "look":
            self.segments, self.runs = int(data["segments"]), _runs(data)

    @property
    def known(self) -> int:
        """Distinct segments probed: A4's measure of progress."""
        return len({k for k, _ in self.answers})

    def render(self) -> str:
        lines = [
            f"Pipe: {self.segments} segments.",
            "Runs: " + "; ".join(r.render() for r in self.runs),
        ]
        if self.answers:
            said = ", ".join(f"{k} {'wet' if water else 'dry'}" for k, water in self.answers)
            lines.append(f"Probes so far ({len(self.answers)}, in order): {said}.")
        else:
            lines.append("Probes so far: none.")
        return "\n".join(lines)

    def upstream(self, segment: int) -> frozenset[int]:
        """The segment and every segment between it and S, from the runs."""
        feeder = self._feeder()
        path = set()
        while segment:
            path.add(segment)
            segment = feeder.get(segment, 0)
        return frozenset(path)

    def suspects(self) -> frozenset[int]:
        """Every segment the answers leave as possibly broken (wet clears k's path from S; dry
        keeps only that path)."""
        left = set(range(1, self.segments + 1))
        for segment, water in self.answers:
            path = self.upstream(segment)
            left = left - path if water else left & path
        return frozenset(left)

    def _feeder(self) -> dict[int, int]:
        feeder = {}
        for run in self.runs:
            feeder[run.first] = run.feeder
            for k in range(run.first + 1, run.last + 1):
                feeder[k] = k - 1
        return feeder
