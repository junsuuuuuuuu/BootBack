from __future__ import annotations

import os
from typing import NoReturn


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2  # noqa: E402


def _disable_gui(*_args, **_kwargs) -> NoReturn:
    raise RuntimeError("OpenCV GUI functions are disabled in the Streamlit Cloud headless runtime.")


cv2.imshow = _disable_gui
cv2.waitKey = _disable_gui
cv2.namedWindow = _disable_gui
cv2.destroyAllWindows = _disable_gui
