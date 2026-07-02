from __future__ import annotations

import os
from typing import NoReturn


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")


class _UnavailableCV2:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def __getattr__(self, name: str) -> NoReturn:
        raise RuntimeError(
            "OpenCV could not be loaded. Streamlit Cloud must run this app with Python 3.11 "
            "and opencv-python-headless installed."
        ) from self.error


try:
    import cv2  # noqa: E402
except Exception as exc:  # pragma: no cover - depends on deployment runtime
    cv2 = _UnavailableCV2(exc)  # type: ignore[assignment]


def _disable_gui(*_args, **_kwargs) -> NoReturn:
    raise RuntimeError("OpenCV GUI functions are disabled in the Streamlit Cloud headless runtime.")


if not isinstance(cv2, _UnavailableCV2):
    cv2.imshow = _disable_gui
    cv2.waitKey = _disable_gui
    cv2.namedWindow = _disable_gui
    cv2.destroyAllWindows = _disable_gui


def is_opencv_available() -> bool:
    return not isinstance(cv2, _UnavailableCV2)


def get_opencv_error() -> str:
    if isinstance(cv2, _UnavailableCV2):
        return f"{cv2.error.__class__.__name__}: {cv2.error}"
    return ""
