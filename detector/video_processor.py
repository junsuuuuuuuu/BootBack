from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .alert_manager import AlertManager
from .fall_detector import FallDetector
from .models import Detection, SafetyEvent
from .tracker import CentroidTracker
from .yolo_detector import YoloPersonDetector


@lru_cache(maxsize=8)
def _load_font(size: int) -> ImageFont.ImageFont:
    font_candidates = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/malgunbd.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for font_path in font_candidates:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def _draw_korean_text(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
) -> np.ndarray:
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    draw.text(position, text, font=_load_font(size), fill=color)
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


@dataclass
class CameraConfig:
    camera_id: str
    zone: str
    source_path: Path


@dataclass
class FrameResult:
    camera_id: str
    zone: str
    frame: np.ndarray | None
    progress: float
    detections: list[Detection] = field(default_factory=list)
    events: list[SafetyEvent] = field(default_factory=list)
    finished: bool = False


class VideoProcessor:
    def __init__(
        self,
        config: CameraConfig,
        detector: YoloPersonDetector,
        alert_manager: AlertManager,
        output_dir: Path,
        detection_interval: int = 5,
        max_display_width: int = 960,
        detection_offset: int = 0,
    ) -> None:
        self.config = config
        self.detector = detector
        self.alert_manager = alert_manager
        self.output_dir = output_dir
        self.tracker = CentroidTracker()
        self.fall_detector = FallDetector()
        self.capture = cv2.VideoCapture(str(config.source_path))
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 20.0)
        self.frame_index = 0
        self.recent_frames: deque[np.ndarray] = deque(maxlen=max(8, int(self.fps * 2)))
        self._recorded_event_workers: set[int] = set()
        self.detection_interval = max(1, detection_interval)
        self.max_display_width = max_display_width
        self.detection_offset = detection_offset % self.detection_interval
        self._last_detections: list[Detection] = []
        self._missed_detection_cycles = 0
        self.max_detection_hold_cycles = 3

    @property
    def worker_count(self) -> int:
        return self.tracker.active_count

    @property
    def is_opened(self) -> bool:
        return self.capture.isOpened()

    def read_next(self) -> FrameResult:
        ok, frame = self.capture.read()
        if not ok or frame is None:
            return FrameResult(
                camera_id=self.config.camera_id,
                zone=self.config.zone,
                frame=None,
                progress=1.0,
                finished=True,
            )

        self.frame_index += 1
        frame = self._resize_for_processing(frame)
        should_detect = self.frame_index == 1 or (self.frame_index + self.detection_offset) % self.detection_interval == 0
        if should_detect:
            raw_detections = self.detector.detect(frame)
            if raw_detections:
                detections = self.tracker.update(raw_detections)
                self._assign_global_worker_ids(detections)
                detections = self.fall_detector.update(detections)
                self._last_detections = detections
                self._missed_detection_cycles = 0
            else:
                self.tracker.update([])
                self._missed_detection_cycles += 1
                detections = self._last_detections if self._missed_detection_cycles <= self.max_detection_hold_cycles else []
        else:
            detections = self._last_detections
        events = self._handle_events(frame, detections)
        annotated = self._draw_overlay(frame, detections)
        self.recent_frames.append(annotated.copy())
        progress = self.frame_index / self.total_frames if self.total_frames else 0
        return FrameResult(
            camera_id=self.config.camera_id,
            zone=self.config.zone,
            frame=annotated,
            progress=min(1.0, progress),
            detections=detections,
            events=events,
        )

    def _resize_for_processing(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        if width <= self.max_display_width:
            return frame
        scale = self.max_display_width / width
        return cv2.resize(frame, (self.max_display_width, int(height * scale)), interpolation=cv2.INTER_AREA)

    def release(self) -> None:
        self.capture.release()

    def _assign_global_worker_ids(self, detections: list[Detection]) -> None:
        for detection in detections:
            if detection.track_id is None:
                continue
            detection.global_id = self.alert_manager.get_global_worker_id(
                self.config.camera_id,
                detection.track_id,
            )

    def _handle_events(self, frame: np.ndarray, detections: list[Detection]) -> list[SafetyEvent]:
        events: list[SafetyEvent] = []
        for detection in detections:
            if not detection.is_fall or detection.track_id is None:
                continue
            worker_id = detection.global_id or detection.track_id
            if worker_id in self._recorded_event_workers:
                continue
            snapshot = self._save_snapshot(frame, detection)
            video_path = self._save_event_clip()
            event = self.alert_manager.add_event(
                camera_id=self.config.camera_id,
                zone=self.config.zone,
                worker_id=worker_id,
                event_type="낙상 감지",
                severity="HIGH",
                snapshot_path=snapshot,
                video_path=video_path,
            )
            self._recorded_event_workers.add(worker_id)
            if event is not None:
                events.append(event)
        return events

    def _save_snapshot(self, frame: np.ndarray, detection: Detection) -> Path:
        snapshot_dir = self.output_dir / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        worker_id = detection.global_id or detection.track_id
        path = snapshot_dir / f"{self.config.camera_id}_worker{worker_id}_{ts}.jpg"
        annotated = self._draw_overlay(frame.copy(), [detection])
        cv2.imwrite(str(path), annotated)
        return path

    def _save_event_clip(self) -> Path | None:
        if not self.recent_frames:
            return None
        video_dir = self.output_dir / "event_videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = video_dir / f"{self.config.camera_id}_event_{ts}.mp4"
        h, w = self.recent_frames[0].shape[:2]
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            max(8.0, min(30.0, self.fps)),
            (w, h),
        )
        for frame in self.recent_frames:
            writer.write(frame)
        writer.release()
        return path

    def _draw_overlay(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 42), (15, 18, 24), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
        frame = _draw_korean_text(
            frame,
            f"{self.config.zone} | {self.config.camera_id} | AI LIVE",
            (14, 9),
            24,
            (235, 235, 235),
        )

        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            color = (30, 45, 235) if detection.is_fall else (80, 220, 120)
            worker_id = detection.global_id or detection.track_id or "-"
            label = f"ID {worker_id} {detection.confidence:.2f}"
            if detection.is_fall:
                label = f"FALL | {label}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            cv2.rectangle(frame, (x1, max(0, y1 - 28)), (min(frame.shape[1], x1 + 180), y1), color, -1)
            cv2.putText(
                frame,
                label,
                (x1 + 6, max(18, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return frame
