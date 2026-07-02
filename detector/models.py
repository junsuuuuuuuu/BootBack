from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


Severity = Literal["LOW", "MEDIUM", "HIGH"]
EventStatus = Literal["OPEN", "ACK", "CLOSED"]


@dataclass
class Detection:
    bbox: tuple[int, int, int, int]
    confidence: float
    class_name: str = "person"
    track_id: int | None = None
    global_id: int | None = None
    is_fall: bool = False


@dataclass
class SafetyEvent:
    event_id: str
    timestamp: datetime
    camera_id: str
    zone: str
    worker_id: int
    event_type: str
    severity: Severity
    status: EventStatus = "OPEN"
    snapshot_path: Path | None = None
    video_path: Path | None = None
    metadata: dict[str, str] = field(default_factory=dict)
