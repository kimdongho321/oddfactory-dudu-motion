# 두두 도트 모션

트릭컬 두두 도트 모션(일반·야광)과 안드로이드 연계용 데이터.

- `dist/` — 앱에서 쓰는 결과물: `motions.json`(모션별 프레임 순서·시간, 일반/야광) + `frames/`(306×281 PNG)
  - hatch(앱 시작 알 부화, `taps` = 1·2·3번째 터치 구간 시작), idle, pat, roar, headbutt(벽 박치기 → 멍 → 일어나기, `runFrom/runTo/hitFrom`), eat, panic, blank, sleep, switch, walk_grok, getup
- 빌드: `build_web.py`(프레임 조립·야광 변환 `glowmap.py`·이펙트 `fx_shock.py`), `build_v5.py`(새 얼굴형 버전 빌드)
- 편집 도구: `edit_motion.py`, `extract_own.py`, `skinfix.py`, `stamp_eyes.py`, `dot_face_marks.py`
- `android-hatch-20261108/` — 알 부화 안드로이드 시험 앱
- 앱 동작 설계: `ANDROID-FEATURES.md`

## Android에서 사용하기

1. [최신 APK](https://github.com/kimdongho321/oddfactory-dudu-motion/releases/latest)를 설치하고 **실행**을 눌러요.
2. 처음 한 번만 **다른 앱 위에 표시**에서 **두두 키우기**를 허용해요. 접근성 권한이나 PC 연결은 필요 없어요.
3. 1.0.5부터 앱을 열거나 **업데이트 확인**을 누르면 새 버전을 앱에서 받을 수 있어요. 처음 앱 안에서 업데이트할 때는 두두 키우기의 설치를 허용하고, Android 설치창에서 확인해 주세요.
