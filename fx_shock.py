"""roar 하울링 이펙트: 입 주변에서 부드럽게 빛나는 방사형 빛줄기가 퍼져 나가며 사라짐(사용자 참고 이미지 2026-11-08)"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PEAK = list(range(4, 12))   # 포효하는 프레임
SS = 3                      # 초과 샘플링(부드러운 빛줄기)


def burst(size, center, t, mode, seed=11):
    W, H = size[0] * SS, size[1] * SS
    cx, cy = center[0] * SS, center[1] * SS
    rnd = random.Random(seed)
    layer = Image.new('L', (W, H), 0); d = ImageDraw.Draw(layer)
    r_in = (26 + 70 * t) * SS          # 가운데 빈 구멍이 점점 커짐
    n = 46
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.05, 0.05)
        L = rnd.uniform(18, 46) * (0.7 + 0.9 * t) * SS
        w = rnd.uniform(0.018, 0.04)
        r0 = r_in * rnd.uniform(0.9, 1.15)
        v = int(255 * rnd.uniform(0.55, 1.0))
        p0 = (cx + r0 * math.cos(a - w), cy + r0 * math.sin(a - w))
        p1 = (cx + r0 * math.cos(a + w), cy + r0 * math.sin(a + w))
        p2 = (cx + (r0 + L) * math.cos(a), cy + (r0 + L) * math.sin(a))
        d.polygon([p0, p1, p2], fill=v)
    core = layer.filter(ImageFilter.GaussianBlur(1.2 * SS))
    glow = layer.filter(ImageFilter.GaussianBlur(4 * SS))
    al = np.clip(1.5 * np.array(core).astype(float) + 1.0 * np.array(glow).astype(float), 0, 255)
    al *= (1.0 - 0.75 * max(0.0, t - 0.55) / 0.45)          # 끝에서 서서히 흐려짐
    al = Image.fromarray(al.astype(np.uint8)).resize(size, Image.LANCZOS)
    col = (215, 255, 240) if mode == 'glow' else (110, 140, 185)
    shade = (40, 170, 130) if mode == 'glow' else (70, 90, 130)   # 밝은 배경에서도 보이게 바깥 은은한 테
    out = Image.new('RGBA', size, shade + (0,))
    sh = al.filter(ImageFilter.GaussianBlur(2)).point(lambda v: int(min(255, v * 0.9)))
    out.putalpha(sh)
    top = Image.new('RGBA', size, col + (0,)); top.putalpha(al)
    out.alpha_composite(top)
    return out


def apply(out, FR):
    if 'roar' not in out: return
    for mode in ('normal', 'glow'):
        names = out['roar'].get(mode, [])
        for k, i in enumerate(PEAK):
            if i >= len(names): continue
            fg = Image.open(os.path.join(FR, names[i])).convert('RGBA')
            a = np.array(fg)[..., 3] > 0; ys, xs = np.where(a)
            c = (xs.mean() - 0.04 * (xs.max() - xs.min()), ys.min() + 0.46 * (ys.max() - ys.min()))   # 입 높이
            t = k / (len(PEAK) - 1)
            bg = burst(fg.size, c, t, mode); bg.alpha_composite(fg)
            nm = names[i].replace('.png', '_fx.png'); bg.save(os.path.join(FR, nm)); names[i] = nm


def twice(out):
    """포효를 두 번: 포효 구간(3~11)을 한 번 더 이어 붙임(사용자 요청 2026-11-08)"""
    if 'roar' not in out: return
    o = out['roar']
    for mode in ('normal', 'glow'):
        n = o.get(mode, []); ms = o.get('ms_' + mode, [])
        if len(n) < 12: continue
        o[mode] = n[:12] + n[3:12] + n[12:]
        o['ms_' + mode] = ms[:12] + ms[3:12] + ms[12:]
