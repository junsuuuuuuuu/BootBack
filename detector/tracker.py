from __future__ import annotations

from dataclasses import dataclass

from .models import Detection


@dataclass
class Track:
    track_id: int
    centroid: tuple[float, float]
    bbox: tuple[int, int, int, int]
    missed_frames: int = 0


class CentroidTracker:
    """Small per-camera centroid tracker for stable worker IDs."""

    def __init__(self, max_distance: float = 180.0, max_missed_frames: int = 30) -> None:
        self.max_distance = max_distance
        self.max_missed_frames = max_missed_frames
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    @property
    def active_count(self) -> int:
        return len(self._tracks)

    def update(self, detections: list[Detection]) -> list[Detection]:
        for track in self._tracks.values():
            track.missed_frames += 1

        assigned_tracks: set[int] = set()
        for detection in detections:
            centroid = self._centroid(detection.bbox)
            best_id: int | None = None
            best_score = -1.0
            for track_id, track in self._tracks.items():
                if track_id in assigned_tracks:
                    continue
                distance = ((centroid[0] - track.centroid[0]) ** 2 + (centroid[1] - track.centroid[1]) ** 2) ** 0.5
                adaptive_distance = max(self.max_distance, self._diagonal(track.bbox) * 0.9)
                iou = self._iou(detection.bbox, track.bbox)
                distance_score = max(0.0, 1.0 - distance / adaptive_distance)
                score = max(iou * 1.4, distance_score)
                if (iou > 0.03 or distance < adaptive_distance) and score > best_score:
                    best_id = track_id
                    best_score = score

            if best_id is None:
                best_id = self._next_id
                self._next_id += 1
                self._tracks[best_id] = Track(track_id=best_id, centroid=centroid, bbox=detection.bbox)
            else:
                self._tracks[best_id].centroid = centroid
                self._tracks[best_id].bbox = detection.bbox
                self._tracks[best_id].missed_frames = 0

            detection.track_id = best_id
            assigned_tracks.add(best_id)

        stale_ids = [
            track_id
            for track_id, track in self._tracks.items()
            if track.missed_frames > self.max_missed_frames
        ]
        for track_id in stale_ids:
            del self._tracks[track_id]

        return detections

    @staticmethod
    def _centroid(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @staticmethod
    def _diagonal(bbox: tuple[int, int, int, int]) -> float:
        x1, y1, x2, y2 = bbox
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    @staticmethod
    def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        intersection = iw * ih
        if intersection == 0:
            return 0.0
        area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
        area_b = max(1, (bx2 - bx1) * (by2 - by1))
        return intersection / (area_a + area_b - intersection)
