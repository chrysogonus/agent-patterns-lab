"""The only surface an architecture gets. Architectures may import this module."""

from apl.dungeon.env import Episode
from apl.dungeon.results import ToolResult


class AgentTools:
    """The free start-room description plus the four tools, per scout; nothing else is public."""

    __slots__ = ("_episode", "start")

    def __init__(self, episode: Episode) -> None:
        self._episode = episode
        self.start = ToolResult.success(episode.describe())

    def look(self, scout: int = 0) -> ToolResult:
        return self._episode.look(scout=scout)

    def move(self, direction: str, scout: int = 0) -> ToolResult:
        return self._episode.move(direction, scout=scout)

    def take(self, item: str, scout: int = 0) -> ToolResult:
        return self._episode.take(item, scout=scout)

    def use(self, item: str, direction: str, scout: int = 0) -> ToolResult:
        return self._episode.use(item, direction, scout=scout)
