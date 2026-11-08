"""빌드 때 APK assets/res를 만든다. 원본(../dist, ../runtime, android/runtime, 글꼴)은 읽기만 한다.

assets/
  screen.html, r/overlay.mjs, r/dudu-runtime.mjs   (오버레이 무대 + 공용 동작 로직)
  motions.json, frames/*.png                       (../dist 그대로, motions.json이 참조하는 프레임만)
  fonts/Maplestory-{Bold,Light}.ttf, licenses/maplestory.txt
res/mipmap-*/ic_launcher.png                       (idle 첫 프레임에서 잘라 만든 런처 아이콘)
"""
from pathlib import Path
import json, shutil, subprocess

ANDROID = Path(__file__).resolve().parents[1]
PROJECT = ANDROID.parent
BUILD = ANDROID / 'app/build/generated'
ASSETS = BUILD / 'runtimeAssets'
RES = BUILD / 'runtimeRes'
FONTS = PROJECT / 'android-hatch-20261108/assets'


def copy(src: Path, rel: str):
    dst = ASSETS / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def icon():
    from PIL import Image
    im = Image.open(PROJECT / 'dist/frames/normal_idle_idle_Ebase.png').convert('RGBA')
    l, t, r, b = im.getchannel('A').point(lambda a: 255 if a > 20 else 0).getbbox()
    crop = im.crop((l, t, r, b))
    side = max(crop.size) + 8
    square = Image.new('RGBA', (side, side), (248, 243, 232, 255))
    square.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    for folder, px in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
        out = RES / f'mipmap-{folder}/ic_launcher.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        square.resize((px, px), Image.NEAREST).save(out)


def build():
    for d in (ASSETS, RES):
        assert d.resolve().is_relative_to((ANDROID / 'app/build').resolve())
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    motions = json.loads((PROJECT / 'dist/motions.json').read_text(encoding='utf-8'))
    frames = sorted({f for m in motions.values() for mode in ('normal', 'glow') for f in m.get(mode, [])})
    need = ['hatch', 'idle', 'pat', 'roar', 'headbutt', 'panic', 'blank', 'sleep', 'walk_grok']
    missing_motion = [m for m in need if m not in motions]
    assert not missing_motion, missing_motion
    assert 'taps' in motions['hatch'] and len(motions['hatch']['taps']) >= 3
    missing = [f for f in frames if not (PROJECT / 'dist/frames' / f).is_file()]
    assert not missing, missing[:10]
    copy(PROJECT / 'dist/motions.json', 'motions.json')
    for f in frames:
        copy(PROJECT / 'dist/frames' / f, 'frames/' + f)
    copy(ANDROID / 'runtime/screen.html', 'screen.html')
    copy(ANDROID / 'runtime/overlay.mjs', 'r/overlay.mjs')
    copy(PROJECT / 'runtime/dudu-runtime.mjs', 'r/dudu-runtime.mjs')
    copy(FONTS / 'maple-bold.ttf', 'fonts/Maplestory-Bold.ttf')
    copy(FONTS / 'maple-light.ttf', 'fonts/Maplestory-Light.ttf')
    copy(FONTS / 'Maplestory-LICENSE.txt', 'licenses/maplestory.txt')
    if shutil.which('node'):
        for m in ('r/overlay.mjs', 'r/dudu-runtime.mjs'):
            subprocess.run(['node', '--check', str(ASSETS / m)], check=True, capture_output=True)
    icon()
    print(json.dumps({'frames': len(frames), 'motions': len(motions), 'assets': str(ASSETS)}))


if __name__ == '__main__':
    build()
