# AI CCTV Fall Detection Dashboard

Streamlit 기반 산업현장 AI CCTV 낙상 관제 대시보드입니다.
4개 CCTV 중 1개 이상만 업로드해도 AI 분석을 시작할 수 있습니다.
사람에게 Tracking ID와 Bounding Box를 표시하고, 사람 bbox의 가로가 세로보다 길어지는 상태를 낙상으로 감지합니다.
넘어지는 순간 사람이 여러 박스로 쪼개지는 경우를 줄이기 위해 가까운 person box를 병합하고, tracker가 같은 작업자 ID를 유지하도록 보정합니다.

## 실행

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## 구조

- `app.py`: 단일 Dashboard UI
- `detector/video_processor.py`: 영상 입력, 프레임 처리, 스냅샷/이벤트 클립 저장
- `detector/yolo_detector.py`: YOLO 또는 OpenCV 폴백 사람 탐지
- `detector/tracker.py`: 카메라별 Tracking ID 유지
- `detector/fall_detector.py`: bbox 가로/세로 비율 기반 낙상 감지
- `detector/alert_manager.py`: 낙상 알람과 이벤트 히스토리 관리
- `DESIGN.md`: 대시보드 UI/UX 디자인 시스템 문서

## 성능 설정

앱은 표시 해상도를 640px로 줄이고, YOLO 추론은 12프레임마다 수행합니다.
중간 프레임은 마지막 bbox를 재사용해서 Streamlit 화면 FPS를 높입니다.
더 정확한 박스가 필요하면 `app.py`의 `detection_interval`을 낮추고, 더 빠른 재생이 필요하면 값을 높이면 됩니다.

Ultralytics YOLO가 설치되어 있고 프로젝트 루트의 `yolov8n.pt`를 사용합니다.
모델 파일이 없으면 Ultralytics가 최초 1회 다운로드를 시도합니다. 네트워크가 막힌 환경에서는 `yolov8n.pt`를 프로젝트 루트에 직접 넣어야 합니다.
