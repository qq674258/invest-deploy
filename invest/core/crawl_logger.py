from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class CrawlLogEntry:
    ts: str
    level: str  # info | warn | error
    message: str
    progress: float | None = None


EventCallback = Callable[[dict[str, Any]], None]


class CrawlProgressLogger:
    """采集过程结构化日志，可同步写入列表或推送 SSE 事件。"""

    def __init__(self, on_event: EventCallback | None = None) -> None:
        self.entries: list[CrawlLogEntry] = []
        self.on_event = on_event

    def _emit(self, level: str, message: str, progress: float | None = None) -> None:
        entry = CrawlLogEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            progress=progress,
        )
        self.entries.append(entry)
        if self.on_event:
            payload = {"type": "log", **asdict(entry)}
            self.on_event(payload)

    def info(self, message: str, progress: float | None = None) -> None:
        self._emit("info", message, progress)

    def warn(self, message: str, progress: float | None = None) -> None:
        self._emit("warn", message, progress)

    def error(self, message: str, progress: float | None = None) -> None:
        self._emit("error", message, progress)

    def as_list(self) -> list[dict[str, Any]]:
        return [asdict(e) for e in self.entries]
