"""새 방식(v5) 웹 빌드: edit2/v5src 소스로 잠시 바꿔 build_web 실행 → web_v5 로 복사 → 원래 웹·소스 복구.
원래 웹(web/, 8852)은 절대 바뀌지 않게 함."""
import os, sys, shutil, subprocess, glob
R = os.path.dirname(os.path.abspath(__file__)); os.chdir(R)
E2 = 'edit2'; V = os.path.join(E2, 'v5src'); T = os.path.join(E2, '_swap_tmp')
CI_STRIPS = sorted(glob.glob(os.path.join(V, 'strips', '*.png')))
pairs = [(os.path.join(V, 'frames'), os.path.join(E2, 'hand4b', 'frames')),
         (os.path.join(V, 'patloop'), os.path.join(E2, 'patloop')),
         (os.path.join(V, 'grokwalk'), os.path.join(E2, 'grokwalk'))]
shutil.rmtree(T, ignore_errors=True); os.makedirs(T)
# 원래 것 보관
shutil.copytree('web/frames', os.path.join(T, 'web_frames')); shutil.copy('web/motions.json', os.path.join(T, 'motions.json'))
for i, (s, d) in enumerate(pairs):
    shutil.copytree(d, os.path.join(T, f'd{i}'))
for f in CI_STRIPS:
    shutil.copy(os.path.join('web', 'codex-v3', 'assets', os.path.basename(f)), os.path.join(T, os.path.basename(f)))
try:
    for s, d in pairs:
        for f in glob.glob(os.path.join(s, '*.png')): shutil.copy(f, os.path.join(d, os.path.basename(f)))
    for f in CI_STRIPS: shutil.copy(f, os.path.join('web', 'codex-v3', 'assets', os.path.basename(f)))
    r = subprocess.run([sys.executable, 'build_web.py'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(r.stdout[-300:], r.stderr[-800:])
    shutil.rmtree('web_v5/frames', ignore_errors=True); shutil.copytree('web/frames', 'web_v5/frames'); shutil.copy('web/motions.json', 'web_v5/motions.json')
    shutil.copy('web/index.html', 'web_v5/index.html')
finally:
    shutil.rmtree('web/frames'); shutil.copytree(os.path.join(T, 'web_frames'), 'web/frames'); shutil.copy(os.path.join(T, 'motions.json'), 'web/motions.json')
    for i, (s, d) in enumerate(pairs):
        shutil.rmtree(d); shutil.copytree(os.path.join(T, f'd{i}'), d)
    for f in CI_STRIPS: shutil.copy(os.path.join(T, os.path.basename(f)), os.path.join('web', 'codex-v3', 'assets', os.path.basename(f)))
    shutil.rmtree(T, ignore_errors=True)
print('v5 built')
