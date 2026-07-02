from __future__ import annotations

from collections import defaultdict, deque

from .models import Detection


class FallDetector:
    """BBox aspect-ratio based fall detector.

    A fall candidate is raised when a tracked person's bounding box becomes
    horizontally dominant for consecutive frames.
    """

    def __init__(self, ratio_threshold: float = 1.0, min_frames: int = 2) -> None:
        self.ratio_threshold = ratio_threshold
        self.min_frames = min_frames
        self._history: dict[int, deque[bool]] = defaultdict(lambda: deque(maxlen=min_frames))

    def update(self, detections: list[Detection]) -> list[Detection]:
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            width = max(1, x2 - x1)
            height = max(1, y2 - y1)
            is_candidate = width / height >= self.ratio_threshold
            if detection.track_id is None:
                detection.is_fall = is_candidate
                continue
            history = self._history[detection.track_id]
            history.append(is_candidate)
            detection.is_fall = len(history) == self.min_frames and all(history)
        return detections
