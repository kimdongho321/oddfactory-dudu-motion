"""sprite-gen 추출이 분홍(혀·목도리·볼)을 주황으로 바꿔버려서 직접 추출.
raw(마젠타 배경) → 배경과 이어진 마젠타만 제거(안쪽 분홍은 보존) → 8칸 분리 → master 높이로 원래 픽셀 크기 축소 → 발 기준 정렬
사용: python extract_own.py normal glow"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as nd

R = os.path.dirname(os.path.abspath(__file__))
SCALE = {'normal': 0.345, 'glow': 0.421}
DENS = 2   # 원본 도트보다 2배 촘촘한 픽셀(360p 느낌 개선). 1이면 원본 픽셀 크기


def make_pal(master, n=56):
    import cv2
    px = master[master[..., 3] > 128][:, :3].astype(np.float32)
    _, _, c = cv2.kmeans(px, n, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, .5), 4, cv2.KMEANS_PP_CENTERS)
    return c.astype(np.int32)


def blockmode(rgba, s, nw, nh):
    """블록마다 가장 많은 색(양자화 후 최빈값) — 가운데 한 점만 찍으면 경계에서 뭉개진 색이 나옴"""
    out = np.zeros((nh, nw, 4), np.uint8); bw = 1 / s
    q = (rgba[..., :3] // 8).astype(np.int32); key = q[..., 0] * 4096 + q[..., 1] * 64 + q[..., 2]
    for y in range(nh):
        y0, y1 = int(y * bw), max(int(y * bw) + 1, int((y + 1) * bw))
        for x in range(nw):
            x0, x1 = int(x * bw), max(int(x * bw) + 1, int((x + 1) * bw))
            al = rgba[y0:y1, x0:x1, 3] > 128
            if al.mean() < 0.5: continue
            kk = key[y0:y1, x0:x1][al]; vals, cnt = np.unique(kk, return_counts=True); best = vals[cnt.argmax()]
            sel = (key[y0:y1, x0:x1] == best) & al
            out[y, x, :3] = rgba[y0:y1, x0:x1, :3][sel].mean(0); out[y, x, 3] = 255
    return out


def despeckle(img, passes=2):
    """주변 8칸과 모두 다른 외톨이 점(지지직)을 주변 다수색으로 — 도트 노이즈 제거"""
    out = img.copy()
    for _ in range(passes):
        a = out.astype(np.int32); key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]; key[a[..., 3] == 0] = -1
        H, W = key.shape; P = np.pad(key, 1, constant_values=-1)
        nb = np.stack([P[1 + dy:H + 1 + dy, 1 + dx:W + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], -1)
        same = (nb == key[..., None]).sum(-1)
        ys, xs = np.where((same == 0) & (key >= 0))
        for y, x in zip(ys, xs):
            v, c = np.unique(nb[y, x], return_counts=True)
            if c.max() >= 4:
                b = v[c.argmax()]
                if b < 0: out[y, x, 3] = 0
                else: out[y, x, :3] = [(b >> 16) & 255, (b >> 8) & 255, b & 255]
    return out


def palettize(img, pal):
    """Lab 거리로 가장 가까운 원본 색 — RGB 거리는 어두운 갈색 피부를 홍조 빨강으로 잘못 붙임"""
    import cv2
    al = img[..., 3] > 0
    lab = cv2.cvtColor(np.ascontiguousarray(img[..., :3]), cv2.COLOR_RGB2LAB).astype(np.int32)
    plab = cv2.cvtColor(pal.astype(np.uint8)[None], cv2.COLOR_RGB2LAB)[0].astype(np.int32)
    d = ((lab[..., None, :] - plab[None, None]) ** 2).sum(-1); idx = d.argmin(-1)
    out = img.copy(); out[..., :3] = np.where(al[..., None], pal[idx], 0).astype(np.uint8); return out


def run(k, state='idle'):
    d = os.path.join(R, k)
    a = np.array(Image.open(os.path.join(d, 'run', 'raw', f'{state}.png.raw.png')).convert('RGB')).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    key = (r > 150) & (b > 150) & (g < 110) & (np.abs(r - b) < 90)          # 마젠타 계열
    lab, _ = nd.label(key)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge))
    bg |= (r > 180) & (b > 160) & (g < 90)   # 실루엣 안에 갇힌 배경 구멍(순수 마젠타)도 배경
    bg = nd.binary_dilation(bg, iterations=1) & ((g < 140) & (r > 120) & (b > 120) | bg)   # 경계 1px 번짐까지
    fg = ~bg
    H, W = fg.shape; cw = W / 8
    m = np.array(Image.open(os.path.join(d, 'master.png')).convert('RGBA'))
    PAL = make_pal(m)
    if k.startswith('glow'):   # 야광: 원본 팔레트가 어두운 피부를 홍조색으로 붙여서, 생성본 자체 색(48색)으로 팔레트
        inner = nd.binary_erosion(fg, iterations=3)   # 배경 번짐(마젠타)이 팔레트에 섞이지 않게 안쪽만
        PAL = make_pal(np.dstack([a, inner * 255]).astype(np.uint8)[::2, ::2], 48)
    mal = m[..., 3] > 128; mys, mxs = np.where(mal); mh = mys.max() - mys.min() + 1
    CW, CH = DENS * (m.shape[1] + 40), DENS * (m.shape[0] + 30)   # 점프·박치기 여유
    out = []
    for i in range(8):
        x0, x1 = int(i * cw), int((i + 1) * cw)
        f = fg[:, x0:x1]; lab2, n = nd.label(f); sz = nd.sum(f, lab2, range(1, n + 1))
        keep = np.isin(lab2, 1 + np.where(sz > 0.02 * sz.max())[0])
        ys, xs = np.where(keep); y0, y1, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rgba = np.dstack([a[:, x0:x1], keep * 255]).astype(np.uint8)[y0:y1, xa:xb]
        if i == 0:   # 1번 장(기본 자세) 키를 원본 높이에 맞춘 배율을 8장 모두에 적용
            s0 = DENS * mh / (y1 - y0)
        s = s0
        nw, nh = max(1, round(rgba.shape[1] * s)), max(1, round(rgba.shape[0] * s))
        small = blockmode(rgba, s, nw, nh)
        small = palettize(small, PAL)
        small = despeckle(small)
        cell = np.zeros((CH, CW, 4), np.uint8)
        al = small[..., 3] > 0; sy, sx = np.where(al); bot = sy.max()
        fx = sx[sy >= bot - 3].mean()
        CW_, CH_ = CW, CH
        oy = CH - 4 - bot; ox = int(round(CW / 2 - fx + (mxs[mys >= mys.max() - 3].mean() - m.shape[1] / 2)))
        ys2, xs2 = np.where(al)
        ty, tx = ys2 + oy, xs2 + ox; ok = (ty >= 0) & (ty < CH) & (tx >= 0) & (tx < CW)
        cell[ty[ok], tx[ok]] = small[ys2[ok], xs2[ok]]
        out.append(Image.fromarray(cell))
    os.makedirs(os.path.join(d, 'own'), exist_ok=True)
    for i, c in enumerate(out):
        c = np.array(c); al = c[..., 3] > 0; r_, g_, b_ = (c[..., j].astype(int) for j in range(3))
        for _ in range(2):   # 마젠타 테두리 찌꺼기 제거
            edge = al & nd.binary_dilation(~al, iterations=3); mag = edge & (r_ - g_ > 50) & (b_ - g_ > 45) & (np.abs(r_ - b_) < 100); c[mag, 3] = 0; al = c[..., 3] > 0
        Image.fromarray(c).save(os.path.join(d, 'own', f'{state}_{i}.png'))
    print(k, 'scale', round(s0, 3), 'cell', CW, CH)


if __name__ == '__main__':
    k = sys.argv[1]
    for st in sys.argv[2:] or ['idle']:
        run(k, st)
