from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .models import SafetyEvent


class AlertManager:
    def __init__(self) -> None:
        self.events: list[SafetyEvent] = []
        self._open_event_keys: set[tuple[str, int, str]] = set()
        self._external_event_ids: set[str] = set()
        self._worker_id_map: dict[tuple[str, int], int] = {}
        self._next_worker_id = 1

    def get_global_worker_id(self, camera_id: str, local_track_id: int) -> int:
        key = (camera_id, local_track_id)
        if key not in self._worker_id_map:
            self._worker_id_map[key] = self._next_worker_id
            self._next_worker_id += 1
        return self._worker_id_map[key]

    def add_event(
        self,
        camera_id: str,
        zone: str,
        worker_id: int,
        event_type: str,
        severity: str,
        snapshot_path: Path | None = None,
        video_path: Path | None = None,
    ) -> SafetyEvent | None:
        key = (camera_id, worker_id, event_type)
        if key in self._open_event_keys:
            return None

        event = SafetyEvent(
            event_id=uuid4().hex[:10].upper(),
            timestamp=datetime.now(),
            camera_id=camera_id,
            zone=zone,
            worker_id=worker_id,
            event_type=event_type,
            severity=severity,  # type: ignore[arg-type]
            snapshot_path=snapshot_path,
            video_path=video_path,
        )
        self.events.insert(0, event)
        self._open_event_keys.add(key)
        return event

    def add_external_event(self, payload: dict) -> SafetyEvent | None:
        event_id = str(payload.get("event_id") or uuid4().hex[:10].upper())
        if event_id in self._external_event_ids:
            return None

        timestamp = self._parse_timestamp(str(payload.get("created_at") or ""))
        worker_id = int(payload.get("worker_id") or 0)
        event = SafetyEvent(
            event_id=event_id,
            timestamp=timestamp,
            camera_id=str(payload.get("camera_id") or ""),
            zone=str(payload.get("zone") or ""),
            worker_id=worker_id,
            event_type=str(payload.get("event_type") or payload.get("message") or "외부 낙상 알림"),
            severity=str(payload.get("severity") or "HIGH"),  # type: ignore[arg-type]
            status=str(payload.get("status") or "OPEN"),  # type: ignore[arg-type]
            metadata={
                "source": str(payload.get("source") or "external"),
                "message": str(payload.get("message") or ""),
            },
        )
        self.events.insert(0, event)
        self._external_event_ids.add(event_id)
        self._open_event_keys.add((event.camera_id, event.worker_id, event.event_type))
        return event

    def has_open_event_for_camera(self, camera_id: str) -> bool:
        return any(event.camera_id == camera_id and event.status == "OPEN" for event in self.events)

    @property
    def open_high_count(self) -> int:
        return sum(1 for event in self.events if event.status == "OPEN" and event.severity == "HIGH")

    @property
    def today_count(self) -> int:
        today = datetime.now().date()
        return sum(1 for event in self.events if event.timestamp.date() == today)

    @property
    def system_state(self) -> str:
        if any(event.status == "OPEN" and event.severity == "HIGH" for event in self.events):
            return "EMERGENCY"
        if any(event.status == "OPEN" and event.severity == "MEDIUM" for event in self.events):
            return "WARNING"
        return "NORMAL"

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        if not value:
            return datetime.now()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return datetime.now()

    def to_dataframe(self) -> pd.DataFrame:
        rows = [
            {
                "시간": event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "카메라": f"{event.zone} ({event.camera_id})",
                "Worker ID": event.worker_id,
                "이벤트 종류": event.event_type,
                "심각도": event.severity,
                "상태": event.status,
                "스냅샷": str(event.snapshot_path or ""),
                "이벤트 영상": str(event.video_path or ""),
            }
            for event in self.events
        ]
        return pd.DataFrame(rows)
