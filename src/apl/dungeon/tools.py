"""The only surface an architecture gets. Architectures may import this module."""

from apl.dungeon.env import Episode
from apl.dungeon.results import ToolResult


class AgentTools:
    """The free start-room description plus the four tools; nothing else is public."""

    __slots__ = ("_episode", "start")

    def __init__(self, episode: Episode) -> None:
        self._episode = episode
        self.start = ToolResult.success(episode.describe())

    def look(self) -> ToolResult:
        return self._episode.look()

    def move(self, direction: str) -> ToolResult:
        return self._episode.move(direction)

    def take(self, item: str) -> ToolResult:
        return self._episode.take(item)

    def use(self, item: str, direction: str) -> ToolResult:
        return self._episode.use(item, direction)
