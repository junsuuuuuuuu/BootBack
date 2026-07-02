from __future__ import annotations

import tempfile
import time
from datetime import datetime
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

from detector.alert_manager import AlertManager
from detector.video_processor import CameraConfig, VideoProcessor
from detector.yolo_detector import YoloPersonDetector


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
CAMERAS = [
    {"camera_id": "CAM1", "zone": "A구역"},
    {"camera_id": "CAM2", "zone": "B구역"},
    {"camera_id": "CAM3", "zone": "C구역"},
    {"camera_id": "CAM4", "zone": "D구역"},
]


st.set_page_config(
    page_title="AI CCTV Safety Control Center",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #0a0d12;
            --surface: #11161e;
            --surface-2: #171d27;
            --surface-3: #202735;
            --line: #2a3342;
            --muted: #8f9bab;
            --text: #f3f6fa;
            --green: #2cc36b;
            --yellow: #f3c74f;
            --red: #e5484d;
            --blue: #4f8cff;
        }
        .stApp {
            background: var(--bg);
            color: var(--text);
            overflow-x: hidden;
        }
        [data-testid="stAppViewContainer"] > .main {
            padding-top: 0;
        }
        header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
        .block-container { padding: 50px 1rem 1.4rem !important; max-width: 100%; }
        .app-top-safe { height: 0; }
        .control-header, .glass-card, .alert-card, .camera-shell, .upload-shell, .ops-panel, .side-panel {
            border: 1px solid var(--line);
            background: var(--surface);
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
        }
        .control-header {
            display: grid;
            grid-template-columns: 1.9fr 0.9fr 0.85fr;
            gap: 12px;
            align-items: center;
            min-height: 96px;
            padding: 18px 20px;
            border-radius: 8px;
            margin: 0 0 12px 0;
            overflow: visible;
            transform: none;
        }
        .system-title {
            display: block;
            font-size: 23px;
            font-weight: 800;
            letter-spacing: 0;
            line-height: 1.45;
            word-break: keep-all;
            white-space: normal;
            overflow: visible;
        }
        .system-sub { color: var(--muted); font-size: 13px; margin-top: 4px; line-height: 1.45; }
        .status-pill {
            display: inline-flex; align-items: center; justify-content: center;
            min-height: 34px; padding: 0 14px; border-radius: 8px;
            font-weight: 800; font-size: 13px; border: 1px solid var(--line);
        }
        .status-normal { color: #c8f5d9; background: rgba(44, 195, 107, 0.14); }
        .status-warning { color: #fff0b3; background: rgba(243, 199, 79, 0.14); }
        .status-emergency { color: #ffd0d2; background: rgba(229, 72, 77, 0.18); box-shadow: inset 0 0 0 1px rgba(229,72,77,.28); }
        .header-metric-label { color: var(--muted); font-size: 12px; }
        .header-metric-value { font-weight: 800; font-size: 15px; margin-top: 4px; }
        .ops-panel, .side-panel {
            border-radius: 8px;
            padding: 14px;
            min-height: 690px;
        }
        .glass-card { border-radius: 8px; padding: 12px; min-height: 86px; background: var(--surface-2); }
        .kpi-label { color: var(--muted); font-size: 13px; }
        .kpi-value { font-size: 27px; line-height: 1.1; font-weight: 850; margin-top: 7px; }
        .kpi-foot { color: #b8c2cf; font-size: 12px; margin-top: 8px; }
        .camera-shell { border-radius: 6px; overflow: hidden; background: #06080c; }
        .camera-title {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 10px; background: #151b25;
            border-bottom: 1px solid var(--line); font-weight: 800;
        }
        .camera-title span:last-child { color: var(--muted); font-size: 12px; }
        .placeholder {
            height: 245px; display: flex; align-items: center; justify-content: center;
            color: #94a3b8; background: #080b10;
            border-top: 1px solid rgba(255,255,255,.04); font-weight: 700;
        }
        .upload-shell { border-radius: 8px; padding: 10px; margin-bottom: 10px; background: var(--surface-2); box-shadow: none; }
        .upload-title { font-size: 13px; font-weight: 800; color: #dce6f3; margin-bottom: 6px; }
        .alert-card {
            border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;
            border-left: 4px solid var(--red);
            background: var(--surface-2);
        }
        .alert-title { font-weight: 850; color: #ffd0d2; font-size: 15px; }
        .alert-meta { color: #c8d1dc; font-size: 13px; line-height: 1.55; margin-top: 6px; }
        .section-title { font-size: 16px; font-weight: 850; margin: 0 0 10px; }
        .panel-title { font-size: 15px; font-weight: 850; margin-bottom: 10px; color: #e6edf6; }
        .panel-divider { height: 1px; background: var(--line); margin: 14px 0; }
        .dashboard-grid {
            display: grid;
            grid-template-columns: minmax(250px, 0.78fr) minmax(620px, 2.25fr) minmax(280px, 0.92fr);
            gap: 12px;
            align-items: start;
        }
        .emergency-banner {
            border: 1px solid rgba(229, 72, 77, 0.45);
            background: #2a1115;
            border-radius: 10px;
            padding: 16px 18px;
            margin: 12px 0;
        }
        .emergency-banner strong { font-size: 24px; }
        .snapshot-img img { border-radius: 8px; border: 1px solid var(--line); }
        div[data-testid="stFileUploader"] section {
            background: #0d1219;
            border: 1px dashed #3a4658;
            border-radius: 8px;
            padding: 10px;
            min-height: 86px;
        }
        div[data-testid="stFileUploader"] section div {
            font-size: 12px;
        }
        div[data-testid="stFileUploader"] button {
            min-height: 34px;
            padding: 0 12px;
        }
        div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
        .stButton > button {
            width: 100%;
            min-height: 46px;
            border-radius: 8px;
            border: 1px solid #5778b8;
            background: #315a9f;
            color: white;
            font-weight: 850;
        }
        .stButton > button:hover { border-color: #7da2e8; background: #3c69b6; color: white; }
        .stDownloadButton > button {
            border-radius: 8px;
            border: 1px solid rgba(44, 195, 107, 0.35);
            background: rgba(44, 195, 107, 0.13);
            color: #dcfce7;
        }
        .login-spacer { height: 12vh; }
        .login-panel-head {
            border: 1px solid var(--line);
            border-bottom: 0;
            background: var(--surface);
            border-radius: 10px 10px 0 0;
            padding: 30px 30px 8px;
        }
        .login-title { font-size: 24px; font-weight: 850; margin-bottom: 6px; color: var(--text); }
        .login-sub { display: none; }
        div[data-testid="stTextInput"] input {
            background: #0d1219;
            border: 1px solid var(--line);
            border-radius: 8px;
            color: var(--text);
        }
        div[data-testid="stForm"] {
            border: 1px solid var(--line);
            border-top: 0;
            border-radius: 0 0 10px 10px;
            background: var(--surface);
            padding: 6px 30px 30px;
            box-shadow: 0 16px 42px rgba(0, 0, 0, 0.28);
        }
        div[data-testid="stForm"] small { display: none; }
        div[data-testid="stFormSubmitButton"] + div { display: none; }
        @media (max-width: 1200px) {
            .control-header {
                grid-template-columns: 1fr 0.75fr;
                row-gap: 14px;
            }
            .system-title { font-size: 21px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    defaults = {
        "alert_manager": AlertManager(),
        "detector": None,
        "uploaded_paths": {},
        "uploaded_names": {},
        "processors": {},
        "authenticated": False,
        "auto_start_after_upload": False,
        "running": False,
        "completed": False,
        "progress": {cam["camera_id"]: 0.0 for cam in CAMERAS},
        "worker_counts": {cam["camera_id"]: 0 for cam in CAMERAS},
        "last_frames": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.authenticated and st.session_state.detector is None:
        st.session_state.detector = YoloPersonDetector()
    if st.session_state.authenticated and Path("yolov8n.pt").exists() and getattr(st.session_state.detector, "model", None) is None:
        st.session_state.detector = YoloPersonDetector()


def save_upload(camera_id: str, uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower()
    path = UPLOAD_DIR / f"{camera_id}_{int(time.time())}{suffix}"
    path.write_bytes(uploaded_file.getbuffer())
    return path


def load_preview_frame(path: Path, max_width: int = 720):
    capture = cv2.VideoCapture(str(path))
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        return None
    height, width = frame.shape[:2]
    if width > max_width:
        scale = max_width / width
        frame = cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)
    return frame


def state_class(state: str) -> str:
    return {
        "NORMAL": "status-normal",
        "WARNING": "status-warning",
        "EMERGENCY": "status-emergency",
    }.get(state, "status-normal")


def render_login() -> None:
    left, center, right = st.columns([1, 1.05, 1])
    with center:
        st.markdown('<div class="login-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="login-panel-head">
                <div class="login-title">작업자 낙상 관제 로그인</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            user_id = st.text_input("아이디", placeholder="아이디 입력")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
            submitted = st.form_submit_button("로그인", use_container_width=True)
        if submitted:
            if user_id.strip().lower() == "admin" and password.strip() == "1234":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")


def render_header() -> None:
    manager: AlertManager = st.session_state.alert_manager
    state = manager.system_state
    st.markdown(
        f"""
        <div id="dashboard-top"></div>
        <div class="app-top-safe"></div>
        <div class="control-header">
            <div>
                <div class="system-title">작업자 안전사고 모니터링 대시보드</div>
                <div class="system-sub">YOLO 기반 산업현장 낙상 안전관제</div>
            </div>
            <div>
                <div class="header-metric-label">현재 시간</div>
                <div class="header-metric-value">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
            </div>
            <div>
                <div class="header-metric-label">시스템 상태</div>
                <div class="status-pill {state_class(state)}">{state}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(columns: int = 4) -> None:
    manager: AlertManager = st.session_state.alert_manager
    total_workers = sum(st.session_state.worker_counts.values())
    cards = [
        ("감시중인 CCTV", "4대", "A/B/C/D 구역 연결 대기"),
        ("탐지중인 작업자 수", f"{total_workers}명", "Tracking ID 기준"),
        ("오늘 낙상 건수", f"{manager.today_count}건", "낙상 이벤트 자동 기록"),
        ("현재 낙상 알람 수", f"{manager.open_high_count}건", "HIGH OPEN 낙상"),
    ]
    if columns == 1:
        for label, value, foot in cards:
            st.markdown(
                f"""
                <div class="glass-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-foot">{foot}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        return

    cols = st.columns(columns)
    for col, (label, value, foot) in zip(cols, cards):
        col.markdown(
            f"""
            <div class="glass-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-foot">{foot}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_uploads() -> None:
    st.markdown('<div class="panel-title">카메라 소스</div>', unsafe_allow_html=True)
    for cam in CAMERAS:
        camera_id = cam["camera_id"]
        st.markdown(
            f'<div class="upload-shell"><div class="upload-title">{cam["zone"]} ({camera_id})</div>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "mp4, avi, mov",
            type=["mp4", "avi", "mov"],
            key=f"upload_{camera_id}",
            label_visibility="collapsed",
            disabled=st.session_state.running,
        )
        if uploaded is not None:
            current_name = st.session_state.uploaded_names.get(camera_id)
            if current_name != uploaded.name:
                saved_path = save_upload(camera_id, uploaded)
                st.session_state.uploaded_paths[camera_id] = saved_path
                st.session_state.uploaded_names[camera_id] = uploaded.name
                preview = load_preview_frame(saved_path)
                if preview is not None:
                    st.session_state.last_frames[camera_id] = preview
            st.caption(f"업로드 완료: {uploaded.name}")
        st.markdown("</div>", unsafe_allow_html=True)


def build_processors() -> dict[str, VideoProcessor]:
    processors: dict[str, VideoProcessor] = {}
    for camera_index, cam in enumerate(CAMERAS):
        camera_id = cam["camera_id"]
        if camera_id not in st.session_state.uploaded_paths:
            continue
        source = st.session_state.uploaded_paths[camera_id]
        processors[camera_id] = VideoProcessor(
            CameraConfig(camera_id=camera_id, zone=cam["zone"], source_path=Path(source)),
            detector=st.session_state.detector,
            alert_manager=st.session_state.alert_manager,
            output_dir=OUTPUT_DIR,
            detection_interval=10,
            max_display_width=384,
            detection_offset=camera_index * 2,
        )
    return processors


def render_progress() -> None:
    if not st.session_state.running and not st.session_state.completed:
        return
    active_camera_ids = list(st.session_state.processors.keys())
    if not active_camera_ids:
        return
    avg = sum(st.session_state.progress[camera_id] for camera_id in active_camera_ids) / len(active_camera_ids)
    st.progress(avg, text=f"AI 분석 진행률 {avg * 100:.0f}%")
    cols = st.columns(len(active_camera_ids))
    for col, camera_id in zip(cols, active_camera_ids):
        value = st.session_state.progress[camera_id]
        col.progress(value, text=f'{camera_id} {value * 100:.0f}%')


def render_emergency_banner() -> None:
    manager: AlertManager = st.session_state.alert_manager
    if manager.system_state != "EMERGENCY" or not manager.events:
        return
    event = manager.events[0]
    st.markdown(
        f"""
        <div class="emergency-banner">
            <strong>🚨 {event.zone} 낙상 발생</strong><br/>
            {event.camera_id} · 작업자 ID : {event.worker_id} ·
            {event.timestamp.strftime("%H:%M:%S")} · {event.event_type} · {event.severity}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_camera_grid(frame_slots=None) -> list:
    st.markdown('<div class="section-title">CCTV 관제 월</div>', unsafe_allow_html=True)
    slots = []
    for row in range(2):
        cols = st.columns(2)
        for idx, col in enumerate(cols):
            cam = CAMERAS[row * 2 + idx]
            camera_id = cam["camera_id"]
            with col:
                st.markdown(
                    f"""
                    <div class="camera-shell">
                        <div class="camera-title"><span>{cam["zone"]} ({camera_id})</span><span>실시간 분석</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                slot = st.empty() if frame_slots is None else frame_slots[row * 2 + idx]
                if camera_id in st.session_state.last_frames:
                    slot.image(st.session_state.last_frames[camera_id], channels="BGR", use_container_width=True)
                else:
                    slot.markdown('<div class="placeholder">영상을 업로드하세요</div>', unsafe_allow_html=True)
                slots.append(slot)
    return slots


def render_alert_panel() -> None:
    st.markdown('<div class="section-title">실시간 알람 패널</div>', unsafe_allow_html=True)
    events = st.session_state.alert_manager.events[:8]
    if not events:
        st.info("현재 발생한 낙상 알람이 없습니다.")
        return
    for event in events:
        st.markdown(
            f"""
            <div class="alert-card">
                <div class="alert-title">🚨 {event.zone} 낙상 발생</div>
                <div class="alert-meta">
                    {event.camera_id}<br/>
                    Worker ID : {event.worker_id}<br/>
                    {event.timestamp.strftime("%H:%M")} · {event.event_type} · {event.severity}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_snapshots() -> None:
    st.markdown('<div class="section-title">최근 저장된 스냅샷</div>', unsafe_allow_html=True)
    snapshots = [event.snapshot_path for event in st.session_state.alert_manager.events if event.snapshot_path]
    if not snapshots:
        st.caption("사고 발생 시 스냅샷이 자동 저장됩니다.")
        return
    cols = st.columns(min(3, len(snapshots)))
    for col, path in zip(cols, snapshots[:3]):
        if path and Path(path).exists():
            col.image(str(path), caption=Path(path).name, use_container_width=True)


def render_event_history() -> None:
    st.markdown('<div class="section-title">Event History Table</div>', unsafe_allow_html=True)
    df = st.session_state.alert_manager.to_dataframe()
    if df.empty:
        df = pd.DataFrame(columns=["시간", "카메라", "Worker ID", "이벤트 종류", "심각도", "상태", "스냅샷", "이벤트 영상"])

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    search = c1.text_input("검색", placeholder="카메라, 구역, 이벤트, Worker ID 검색")
    severity = c2.selectbox("심각도", ["ALL", "HIGH", "MEDIUM", "LOW"])
    status = c3.selectbox("상태", ["ALL", "OPEN", "ACK", "CLOSED"])
    c4.download_button(
        "CSV 다운로드",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"safety_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    filtered = df.copy()
    if search:
        mask = filtered.astype(str).apply(lambda row: row.str.contains(search, case=False, regex=False).any(), axis=1)
        filtered = filtered[mask]
    if severity != "ALL":
        filtered = filtered[filtered["심각도"] == severity]
    if status != "ALL":
        filtered = filtered[filtered["상태"] == status]
    st.dataframe(filtered, use_container_width=True, hide_index=True, height=260)


def begin_analysis() -> None:
    processors = build_processors()
    if not processors:
        return
    st.session_state.processors = processors
    st.session_state.running = True
    st.session_state.completed = False
    st.session_state.progress = {cam["camera_id"]: 0.0 for cam in CAMERAS}


def start_analysis_if_requested() -> None:
    uploaded_count = len(st.session_state.uploaded_paths)
    has_upload = uploaded_count > 0
    st.markdown('<div class="panel-title">분석 제어</div>', unsafe_allow_html=True)
    if st.button("AI 분석 시작", disabled=not has_upload or st.session_state.running):
        begin_analysis()
    st.checkbox(
        "업로드 후 자동 분석",
        key="auto_start_after_upload",
        disabled=st.session_state.running,
    )
    if not has_upload:
        st.caption("CCTV 영상을 업로드하면 분석을 시작할 수 있습니다.")
    elif not st.session_state.running and not st.session_state.completed:
        st.caption(f"{uploaded_count}개 CCTV 준비 완료")
    elif st.session_state.completed:
        st.caption("분석 완료. 이벤트 기록을 확인하세요.")

    if has_upload and st.session_state.auto_start_after_upload and not st.session_state.running and not st.session_state.completed:
        begin_analysis()
        st.rerun()


def run_analysis_loop(frame_slots: list) -> None:
    if not st.session_state.running:
        return

    processors: dict[str, VideoProcessor] = st.session_state.processors
    while st.session_state.running:
        all_finished = True
        for index, cam in enumerate(CAMERAS):
            camera_id = cam["camera_id"]
            if camera_id not in processors:
                continue
            processor = processors[camera_id]
            result = processor.read_next()
            st.session_state.progress[camera_id] = result.progress
            st.session_state.worker_counts[camera_id] = processor.worker_count
            if result.frame is not None:
                st.session_state.last_frames[camera_id] = result.frame
                frame_slots[index].image(result.frame, channels="BGR", use_container_width=True)
            all_finished = all_finished and result.finished

        time.sleep(0.001)
        if all_finished:
            for processor in processors.values():
                processor.release()
            st.session_state.running = False
            st.session_state.completed = True
            st.rerun()


def main() -> None:
    inject_css()
    init_state()
    if not st.session_state.authenticated:
        render_login()
        return
    render_header()
    render_emergency_banner()

    left_col, center_col, right_col = st.columns([0.82, 2.24, 0.92], gap="medium")
    with left_col:
        with st.container(border=True):
            render_kpis(columns=1)
            st.markdown('<div class="panel-divider"></div>', unsafe_allow_html=True)
            render_uploads()
            st.markdown('<div class="panel-divider"></div>', unsafe_allow_html=True)
            start_analysis_if_requested()
    with center_col:
        render_progress()
        frame_slots = render_camera_grid()
    with right_col:
        with st.container(border=True):
            render_alert_panel()
            st.markdown('<div class="panel-divider"></div>', unsafe_allow_html=True)
            render_snapshots()

    render_event_history()
    run_analysis_loop(frame_slots)


if __name__ == "__main__":
    main()
