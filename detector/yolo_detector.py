from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np

from .models import Detection


@dataclass
class DetectorStatus:
    engine: str
    ready: bool
    message: str


class YoloPersonDetector:
    """Person detector with an Ultralytics YOLO path and an OpenCV fallback."""

    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.35) -> None:
        self.confidence = confidence
        self.model = None
        self.status = DetectorStatus(
            engine="OpenCV fallback",
            ready=True,
            message="YOLO unavailable, using OpenCV HOG person detector",
        )
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        try:
            from ultralytics import YOLO

            self.model = YOLO(model_name)
            self.status = DetectorStatus(
                engine="Ultralytics YOLO",
                ready=True,
                message=f"{model_name} loaded",
            )
        except Exception as exc:  # pragma: no cover - depends on local model availability
            self.status = DetectorStatus(
                engine="OpenCV fallback",
                ready=True,
                message=f"YOLO unavailable: {exc.__class__.__name__}",
            )

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if self.model is not None:
            return self._detect_yolo(frame)
        return self._detect_hog(frame)

    def _detect_yolo(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.predict(frame, classes=[0], conf=self.confidence, imgsz=320, verbose=False)
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().item())
                detections.append(
                    Detection(
                        bbox=(int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                        confidence=conf,
                    )
                )
        return self._merge_fragmented_people(detections)

    def _detect_hog(self, frame: np.ndarray) -> list[Detection]:
        scale = 416 / max(frame.shape[:2])
        small = cv2.resize(frame, None, fx=scale, fy=scale) if scale < 1 else frame
        rects, weights = self._hog.detectMultiScale(
            small,
            winStride=(12, 12),
            padding=(8, 8),
            scale=1.08,
        )
        detections: list[Detection] = []
        inv = 1 / scale if scale < 1 else 1
        for (x, y, w, h), weight in zip(rects, weights):
            if float(weight) < 0.25:
                continue
            detections.append(
                Detection(
                    bbox=(int(x * inv), int(y * inv), int((x + w) * inv), int((y + h) * inv)),
                    confidence=min(0.99, max(0.25, float(weight))),
                )
            )
        return self._merge_fragmented_people(self._non_max_suppression(detections))

    @staticmethod
    def _non_max_suppression(detections: Iterable[Detection], threshold: float = 0.35) -> list[Detection]:
        detections = list(detections)
        if not detections:
            return []
        boxes = np.array([d.bbox for d in detections])
        scores = np.array([d.confidence for d in detections])
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(),
            scores.tolist(),
            score_threshold=0.1,
            nms_threshold=threshold,
        )
        if len(indices) == 0:
            return []
        flat = np.array(indices).reshape(-1)
        return [detections[int(i)] for i in flat]

    @classmethod
    def _merge_fragmented_people(cls, detections: list[Detection]) -> list[Detection]:
        """Merge person boxes that likely describe one blurred/falling worker."""
        if len(detections) <= 1:
            return detections

        groups: list[list[Detection]] = []
        for detection in sorted(detections, key=lambda d: d.confidence, reverse=True):
            target_group: list[Detection] | None = None
            for group in groups:
                if any(cls._should_merge(detection.bbox, member.bbox) for member in group):
                    target_group = group
                    break
            if target_group is None:
                groups.append([detection])
            else:
                target_group.append(detection)

        merged: list[Detection] = []
        for group in groups:
            if len(group) == 1:
                merged.append(group[0])
                continue
            x1 = min(d.bbox[0] for d in group)
            y1 = min(d.bbox[1] for d in group)
            x2 = max(d.bbox[2] for d in group)
            y2 = max(d.bbox[3] for d in group)
            merged.append(
                Detection(
                    bbox=(x1, y1, x2, y2),
                    confidence=max(d.confidence for d in group),
                )
            )
        return merged

    @classmethod
    def _should_merge(cls, a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
        if cls._iou(a, b) >= 0.05:
            return True
        if cls._intersection_over_min_area(a, b) >= 0.18:
            return True

        ax, ay = cls._centroid(a)
        bx, by = cls._centroid(b)
        distance = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
        max_side = max(cls._box_width(a), cls._box_height(a), cls._box_width(b), cls._box_height(b))
        expanded_overlap = cls._iou(cls._expand(a, 0.22), cls._expand(b, 0.22)) > 0
        return expanded_overlap and distance <= max(70.0, max_side * 0.95)

    @staticmethod
    def _box_width(bbox: tuple[int, int, int, int]) -> int:
        return max(1, bbox[2] - bbox[0])

    @staticmethod
    def _box_height(bbox: tuple[int, int, int, int]) -> int:
        return max(1, bbox[3] - bbox[1])

    @staticmethod
    def _centroid(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @classmethod
    def _expand(cls, bbox: tuple[int, int, int, int], ratio: float) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = bbox
        pad_x = int(cls._box_width(bbox) * ratio)
        pad_y = int(cls._box_height(bbox) * ratio)
        return (x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y)

    @classmethod
    def _intersection_over_min_area(cls, a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if intersection == 0:
            return 0.0
        area_a = cls._box_width(a) * cls._box_height(a)
        area_b = cls._box_width(b) * cls._box_height(b)
        return intersection / min(area_a, area_b)

    @classmethod
    def _iou(cls, a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if intersection == 0:
            return 0.0
        area_a = cls._box_width(a) * cls._box_height(a)
        area_b = cls._box_width(b) * cls._box_height(b)
        return intersection / (area_a + area_b - intersection)
