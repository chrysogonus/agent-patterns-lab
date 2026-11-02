"""The only surface an architecture gets on the workshop. Architectures may import this.

Besides `apl.kit`, architectures may import only each problem's `tools` and `results` modules
(specs/011 contracts/problems.md).
"""

from apl.workshop.env import Episode
from apl.workshop.results import ToolResult


class AgentTools:
    """The free start view plus the four tools; nothing else is public."""

    __slots__ = ("_episode", "start")

    def __init__(self, episode: Episode) -> None:
        self._episode = episode
        self.start = ToolResult.success(episode.describe())

    def look(self) -> ToolResult:
        return self._episode.look()

    def inspect(self, item: object) -> ToolResult:
        return self._episode.inspect(item)

    def gather(self, item: object) -> ToolResult:
        return self._episode.gather(item)

    def craft(self, item: object, recipe: object) -> ToolResult:
        return self._episode.craft(item, recipe)
