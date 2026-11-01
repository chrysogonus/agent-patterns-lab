"""The only surface an architecture gets on the survey field. Architectures may import this."""

from apl.survey.env import Episode
from apl.survey.results import ToolResult


class AgentTools:
    """The free start-cell description plus the three tools, per scout; nothing else is public."""

    __slots__ = ("_episode", "start")

    def __init__(self, episode: Episode) -> None:
        self._episode = episode
        self.start = ToolResult.success(episode.describe())

    def look(self, scout: int = 0) -> ToolResult:
        return self._episode.look(scout=scout)

    def move(self, direction: object, scout: int = 0) -> ToolResult:
        return self._episode.move(direction, scout=scout)

    def submit(self, total: object, scout: int = 0) -> ToolResult:
        return self._episode.submit(total, scout=scout)
