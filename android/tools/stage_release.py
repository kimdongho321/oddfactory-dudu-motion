"""빌드 때 APK assets/res를 만든다. 원본(../dist, ../runtime, android/runtime, 글꼴)은 읽기만 한다.

assets/
  screen.html, r/overlay.mjs, r/dudu-runtime.mjs   (오버레이 무대 + 공용 동작 로직)
  motions.json, frames/*.png                       (../dist 그대로, motions.json이 참조하는 프레임만)
  fonts/Maplestory-{Bold,Light}.ttf, licenses/maplestory.txt
res/                                              (배송 상자 런처 아이콘)
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
    with Image.open(ANDROID / 'runtime/launcher-box-128.png') as source:
        foreground = source.convert('RGBA')
    assert foreground.size == (128, 128)
    box = foreground.getchannel('A').getbbox()
    assert box and 24 <= box[0] < box[2] <= 104 and 24 <= box[1] < box[3] <= 104

    layer = RES / 'drawable-nodpi/of_box_foreground.png'
    layer.parent.mkdir(parents=True, exist_ok=True)
    foreground.resize((256, 256), Image.Resampling.NEAREST).save(layer)
    adaptive = RES / 'mipmap-anydpi-v26/ic_launcher.xml'
    adaptive.parent.mkdir(parents=True, exist_ok=True)
    adaptive.write_text(
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/of_box_launcher_cream" />\n'
        '    <foreground android:drawable="@drawable/of_box_foreground" />\n'
        '</adaptive-icon>\n', encoding='utf-8',
    )
    colors = RES / 'values/of_box_launcher_colors.xml'
    colors.parent.mkdir(parents=True, exist_ok=True)
    colors.write_text(
        '<resources><color name="of_box_launcher_cream">#FFF6ED</color></resources>\n',
        encoding='utf-8',
    )

    square = Image.new('RGBA', foreground.size, '#FFF6ED')
    square.alpha_composite(foreground)
    for folder, px in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
        out = RES / f'mipmap-{folder}/ic_launcher.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        square.resize((px, px), Image.Resampling.NEAREST).save(out)


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
