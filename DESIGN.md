# Worker Fall Monitoring Dashboard Design System

## 1. Visual Theme & Atmosphere

This dashboard monitors worker fall accidents through CCTV footage.
The visual direction follows a Toss-inspired product discipline: clear, calm, approachable, and highly readable.

Unlike a heavy security control room, the interface should feel like a modern operational product:

- Simple Korean labels
- Clear information hierarchy
- Soft surfaces with restrained borders
- Blue for interaction
- Red only for fall/emergency
- No decorative AI visuals
- No unrelated safety topics

The main content is always the CCTV wall. Every panel around it should help the operator upload footage, start analysis, inspect alerts, or review event history.

## 2. Color Palette & Roles

### Core Tokens

- `--bg: #f7f8fa`
  - Page background for a cleaner Toss-like surface

- `--surface: #ffffff`
  - Header, login card, panels, tables

- `--surface-2: #f2f4f6`
  - Subtle section background, upload blocks, disabled surfaces

- `--line: #e5e8eb`
  - Borders and dividers

- `--text: #191f28`
  - Primary headings and important values

- `--muted: #8b95a1`
  - Secondary labels and captions

- `--body: #4e5968`
  - Body text and metadata

### Action & Status

- `--blue: #3182f6`
  - Primary action, focus, selected controls

- `--blue-hover: #2272eb`
  - Button hover/pressed

- `--blue-soft: #e8f3ff`
  - Soft information background

- `--red: #f04452`
  - Fall event, emergency, critical alert

- `--green: #03b26c`
  - Normal state

- `--orange: #fe9800`
  - Warning state

### Rules

- Blue is interaction, not decoration.
- Red is only for fall/emergency.
- Green is only for normal or resolved state.
- Avoid black-heavy cyber dashboards unless footage itself requires dark framing.
- Do not use purple, neon gradients, or glowing effects.

## 3. Typography Rules

### Font Stack

Use a Korean-first system stack similar to Toss:

```css
font-family: "Toss Product Sans", "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

### Type Scale

| Role | Size | Weight | Line Height | Use |
|---|---:|---:|---:|---|
| App title | 24-26px | 700 | 1.35 | Dashboard title |
| Page/section heading | 20-22px | 700 | 1.4 | Major section heading |
| Panel title | 16px | 700 | 1.5 | Panel headings |
| KPI value | 30px | 700 | 1.25 | Numeric status |
| Body | 14-16px | 400 | 1.55 | Descriptions |
| Metadata | 12-13px | 400 | 1.5 | Time, camera, status |
| Button | 15-16px | 600 | 1.2 | Controls |

### Rules

- Use 700 for headings and important numbers.
- Use 600 for controls and emphasis.
- Use 400 for body and helper text.
- Keep letter spacing at `0`.
- Use tabular numerals for counts, timestamps, and progress values.
- Korean text must never clip in cards, buttons, or CCTV overlays.

## 4. Component Stylings

### Login

Purpose: simple authenticated entry for an operator.

Content:

- Title: `작업자 낙상 관제 로그인`
- ID input
- Password input
- Login button

Rules:

- Do not display hardcoded credentials.
- Do not show `Press Enter to submit form`.
- Keep the card as one continuous surface.
- Use a white card on a light gray background.
- Primary login button uses Toss Blue.

### Header

Purpose: show operational context without crowding.

Content:

- `작업자 안전사고 모니터링 대시보드`
- Current time
- System status

Rules:

- Do not expose model name or GPU status.
- Header should be compact.
- Use white surface with light border.
- Status uses semantic colored badge.

### KPI Cards

Content:

- 감시중인 CCTV
- 탐지중인 작업자 수
- 오늘 낙상 건수
- 현재 낙상 알람 수

Style:

- White card
- 16px radius
- Light shadow or 1px border
- Large numeric value
- Muted label

Rules:

- KPI cards should be easy to scan.
- Use clear Korean labels.
- Avoid decorative icons unless they improve recognition.

### Camera Source Upload

Rules:

- Source upload lives in the operations panel.
- Each source block shows zone and camera ID.
- One uploaded camera is enough to start analysis.
- Uploaded frame preview appears in the corresponding CCTV tile.
- Keep upload blocks compact.

### CCTV Wall

Rules:

- CCTV wall is the visual priority.
- Use 2x2 layout for CAM1-CAM4.
- Each tile shows `{구역} ({CAM})`.
- Placeholder: `영상을 업로드하세요`.
- While analyzing, the same tile shows bounding boxes, Worker ID, and fall state.
- Use dark video frame background even in light UI.

### Alert Panel

Rules:

- Alert panel lives on the right side.
- Empty state: `현재 발생한 낙상 알람이 없습니다.`
- Fall alert title: `{구역} 낙상 발생`.
- Critical alert uses red border/background treatment.
- Do not include PPE or unrelated event examples.

### Event History

Columns:

- 시간
- 카메라
- Worker ID
- 이벤트 종류
- 심각도
- 상태
- 스냅샷
- 이벤트 영상

Rules:

- Table should be dense but readable.
- Search, severity filter, status filter, and CSV download must remain visible.
- Use tabular numbers for time and Worker ID.

## 5. Layout Principles

### Primary Layout

Use a clear operational layout:

```text
┌──────────────────────────────────────────────────────────┐
│ Header: title / time / status                            │
├───────────────┬──────────────────────────┬───────────────┤
│ Operations    │ CCTV Wall                 │ Alerts        │
│ KPIs          │ CAM1 CAM2                 │ Alert List    │
│ Upload        │ CAM3 CAM4                 │ Snapshots     │
│ Controls      │                           │               │
├───────────────┴──────────────────────────┴───────────────┤
│ Event History                                             │
└──────────────────────────────────────────────────────────┘
```

### Spacing

- Base unit: 8px
- Component padding: 12-16px
- Panel gap: 12px
- Major section gap: 16-24px
- Avoid large empty top padding.

### Layout Rules

- CCTV wall gets the most width.
- Operations panel should stay compact.
- Alert panel should fit recent alerts without pushing CCTV down.
- Event history sits below the monitoring area.

## 6. Depth & Elevation

Toss-style depth is subtle.

| Level | Treatment | Use |
|---|---|---|
| Base | `#f7f8fa` | Page background |
| Surface | White card with 1px border | Panels and header |
| Raised | White card with `0 2px 8px rgba(0,0,0,0.08)` | KPI and alert cards |
| Critical | Soft red background + red border | Fall/emergency |

Rules:

- Use shadows sparingly.
- Prefer white surfaces and clear spacing.
- No heavy cyberpunk shadows.
- No glassmorphism.
- No decorative gradients.

## 7. Do's and Don'ts

### Do

- Use Toss Blue for primary actions.
- Keep Korean copy short and direct.
- Make CCTV feeds the center of the product.
- Keep fall events visually distinct.
- Use global Worker ID across cameras.
- Use consistent 8/12/16px spacing.
- Keep login simple and private.

### Don't

- Do not display hardcoded login credentials.
- Do not show model/GPU status in the main header.
- Do not use PPE-related copy.
- Do not use emojis in operational alerts.
- Do not over-darken every surface.
- Do not make marketing hero sections.
- Do not let long Korean text clip.

## 8. Responsive Behavior

### Desktop

- Three-column dashboard
- CCTV wall in the center
- Operations left
- Alerts right

### Medium Width

- Header wraps safely.
- CCTV remains first priority.
- Operations and alerts can narrow but must not clip text.

### Small Width

Stack order:

1. Header
2. CCTV Wall
3. Alerts
4. Operations
5. Event History

Rules:

- CCTV tiles become one column.
- Table may scroll horizontally.
- Buttons remain at least 40px tall.

## 9. Agent Prompt Guide

When modifying this project:

- Keep the design Toss-inspired: clear, friendly, minimal, and readable.
- Do not copy fintech wording or money-related UI patterns.
- Preserve the fall-detection domain.
- Keep Streamlit UI in `app.py`.
- Keep detector logic inside `detector/`.
- Explain performance tradeoffs between video resolution, YOLO input size, detection interval, and frame rate.
- Verify code changes with `python -m py_compile`.

