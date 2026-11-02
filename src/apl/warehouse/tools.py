"""The only surface an architecture gets in the warehouse. Architectures may import this."""

from apl.warehouse.env import Episode
from apl.warehouse.results import ToolResult


class AgentTools:
    """The free start view plus the four tools, per robot; nothing else is public."""

    __slots__ = ("_episode", "start")

    def __init__(self, episode: Episode) -> None:
        self._episode = episode
        self.start = ToolResult.success(episode.start_view())

    def look(self, scout: int = 0) -> ToolResult:
        return self._episode.look(scout=scout)

    def move(self, direction: object, scout: int = 0) -> ToolResult:
        return self._episode.move(direction, scout=scout)

    def pick(self, scout: int = 0) -> ToolResult:
        return self._episode.pick(scout=scout)

    def drop(self, scout: int = 0) -> ToolResult:
        return self._episode.drop(scout=scout)
