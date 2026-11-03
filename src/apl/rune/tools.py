"""The only surface an architecture gets on the rune floor. Architectures may import this.

Besides `apl.kit`, architectures may import only each problem's `tools` and `results` modules
(specs/010 contracts/problems.md).
"""

from apl.rune.env import Episode
from apl.rune.results import ToolResult


class AgentTools:
    """The free floor plus the two tools; nothing else is public."""

    __slots__ = ("_episode", "start")

    def __init__(self, episode: Episode) -> None:
        self._episode = episode
        self.start = ToolResult.success(episode.describe())

    def look(self) -> ToolResult:
        return self._episode.look()

    def move(self, direction: object) -> ToolResult:
        return self._episode.move(direction)
