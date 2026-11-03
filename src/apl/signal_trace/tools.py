"""The only surface an architecture gets on the signal trace. Architectures may import this.

Besides `apl.kit`, architectures may import only each problem's `tools` and `results` modules
(specs/009 contracts/problems.md).
"""

from apl.signal_trace.env import Episode
from apl.signal_trace.results import ToolResult


class AgentTools:
    """The free layout plus the three tools; nothing else is public."""

    __slots__ = ("_episode", "start")

    def __init__(self, episode: Episode) -> None:
        self._episode = episode
        self.start = ToolResult.success(episode.describe())

    def look(self) -> ToolResult:
        return self._episode.look()

    def probe(self, segment: object) -> ToolResult:
        return self._episode.probe(segment)

    def submit(self, segment: object) -> ToolResult:
        return self._episode.submit(segment)
