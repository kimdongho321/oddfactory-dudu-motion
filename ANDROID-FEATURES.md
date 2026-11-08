# 두두 앱 — 안드로이드 기능 ↔ 모션 연결안 (2026-11-07 초안)

뷰어: `web\` (serve.bat → http://127.0.0.1:8852). 프레임: `web\frames\<normal|glow>_<모션>_*.png`, 순서·시간은 `web\motions.json`.

## 1. 일반 ↔ 야광 전환 (핵심 컨셉: 야광 물약을 먹은 두두)
| 조건 | 결과 | 감지 방법 | 권한 |
|---|---|---|---|
| 시스템 다크모드 켜짐 | 야광 세트로 교체 + `switch` 재생 | `Configuration.uiMode & UI_MODE_NIGHT_MASK`, `onConfigurationChanged` | 없음 |
| 화면 밝기 낮음(예: 30% 이하) | 야광 세트 | `Settings.System.SCREEN_BRIGHTNESS` ContentObserver (자동 밝기면 값만 읽힘) | 없음(읽기) |
| 주변이 어두움 | 야광 세트(선택) | 조도 센서 `TYPE_LIGHT` (lux < 10) | 없음 |
| 밤 시간(사용자 설정) | 야광 세트 | 알람매니저/시계 | 없음 |

## 2. 이벤트 → 모션
| 이벤트 | 모션 | 감지 | 권한 |
|---|---|---|---|
| 평상시 | idle | — | — |
| 잠금 해제 / 화면 켬 | happy | `ACTION_USER_PRESENT`, `ACTION_SCREEN_ON` | 없음 |
| 오늘 첫 잠금 해제 | **sticker(신규)** — 야광 스티커 하나 붙이기(스티커 수집이 두두 취미). 날마다 스티커 개수 증가 → 도감처럼 | 날짜 저장 | 없음 |
| 캐릭터 톡 | pat | 오버레이 터치 | 다른 앱 위에 표시 |
| 캐릭터 길게 누름 | tickle | 오버레이 터치 | 〃 |
| 캐릭터 끌어서 던짐 | panic | 드래그 속도 | 〃 |
| 드래그 중 / 화면 가로질러 이동 | walk | — | 〃 |
| 알림 도착 | roar | `NotificationListenerService.onNotificationPosted` | 알림 접근 허용 |
| 알림 밀어서 지움 | headbutt (→ 뒤로 튕겨 주저앉아 울기) | `onNotificationRemoved` reason=CANCEL | 〃 |
| 충전 시작 | eat (야광 사탕) | `ACTION_POWER_CONNECTED` | 없음 |
| 배터리 15% 이하 | (sad 버튼 숨김 → 연결 모션 결정 필요) | `ACTION_BATTERY_LOW` | 없음 |
| 10분 조작 없음 | blank | 마지막 입력 시각 | 없음 |
| 취침 모드 / 화면 꺼지기 직전 | sleep (엎드려 빼꼼) | 방해금지·취침 모드(`NotificationManager.getCurrentInterruptionFilter`), 화면 꺼짐 | 알림 접근(방해금지 읽기) |
| 다크모드·밝기 전환 | switch (엎드림에서 일어나기) | 위 1번 | — |
| **음악 재생 중** | **dance(신규)** — 공룡 춤 반복 | `AudioManager.isMusicActive()` 폴링 또는 `MediaSessionManager` 활성 세션 | 없음(폴링) / 알림 접근(세션) |
| **스크린샷 찍음** | **pose(신규)** — 플래시에 움찔 → 브이 | Android 14+ `Activity.ScreenCaptureCallback`(자기 앱 화면만) / 미디어 저장소 `Screenshots` 폴더 관찰 | 사진 읽기 권한 필요(폴더 관찰 시) |
| 폰을 흔듦 | panic | 가속도 센서 | 없음 |

## 3. 두두 설정과 어울리는 추가 아이디어 (모션 미제작)
- **손전등 켜짐** → 야광 스티커가 번쩍 (CameraManager.TorchCallback, 권한 없음)
- **걸음 수 목표 달성** → 공룡 포효로 축하 (`TYPE_STEP_COUNTER`, 신체 활동 권한)
- **알람 울림** → 엎드려 자다가 벌떡 (switch 재사용 가능)
- **비 오는 날** → 후드 뒤집어쓰기 (날씨 API, 인터넷 필요)

## 4. 주의
- 알림 접근은 다른 앱 알림 내용까지 읽을 수 있는 권한 → 내용은 저장·전송하지 않는다고 명시 필요.
- 헤드업 알림을 밀어 지운 방향(좌/우)은 API로 구분 불가.
- 다른 앱 위에 표시(오버레이) 권한은 사용자가 설정에서 직접 허용.
