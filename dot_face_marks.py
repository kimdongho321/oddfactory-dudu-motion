"""도트 단계에서 볼터치 사선(///)과 흰 눈 위 눈꺼풀 선을 직접 그려 넣음(축소로 사라지는 것 방지)."""
import sys, os, numpy as np
from scipy import ndimage as nd
from PIL import Image

def marks(path, lids=True):
    a = np.array(Image.open(path).convert('RGBA')); A = a[..., :3].astype(int); al = a[..., 3] > 0
    r, g, b = A[..., 0], A[..., 1], A[..., 2]; H, W = al.shape
    ys, xs = np.where(al); top, hh = ys.min(), ys.max() - ys.min()
    upper = np.arange(H)[:, None] < top + 0.6 * hh
    # 볼터치: 분홍 덩어리(피부보다 붉은)
    pink = al & upper & (r > 220) & (g > 155) & (g < 200) & (b > 135) & (b < 190) & (r - g > 40) & (r - g < 75)
    lab, n = nd.label(pink); sz = nd.sum(pink, lab, range(1, n + 1))
    _w = al & upper & (A.min(-1) > 220) & (np.abs(r - b) < 25); _wl, _wn = nd.label(_w); _ws = nd.sum(_w, _wl, range(1, _wn + 1))
    _ec = sorted([np.where(_wl == i + 1)[1].mean() for i in np.argsort(-_ws)[:2] if _wn and _ws[i] >= 10])
    for k in [i + 1 for i in np.argsort(-sz)[:3] if sz[i] >= 12]:
        if len(_ec) == 2 and _ec[0] + 3 < np.where(lab == k)[1].mean() < _ec[1] - 3: continue   # 두 눈 사이(입)는 제외
        m = lab == k; my, mx = np.where(m); cy, cx = int(round(my.mean())), int(round(mx.mean()))
        for dx in (-3, 0, 3):   # 짧은 사선 3개(각 3도트)
            for t in range(3):
                y_, x_ = cy - 1 + t, cx + dx + 1 - t
                if 0 <= y_ < H and 0 <= x_ < W and m[y_, x_]: a[y_, x_, :3] = (214, 98, 110)
    if lids:
        white = al & upper & (A.min(-1) > 220) & (np.abs(r - b) < 25)
        lab, n = nd.label(white); sz = nd.sum(white, lab, range(1, n + 1))
        cand = [(i + 1, sz[i], np.where(lab == i + 1)[0].mean(), np.where(lab == i + 1)[1].mean()) for i in np.argsort(-sz)[:6] if sz[i] >= 10]
        eyes = []
        for p_ in cand:
            for q_ in cand:
                if p_[0] < q_[0] and abs(p_[2] - q_[2]) < 6 and 0.6 < p_[1] / q_[1] < 1.6 and 8 < abs(p_[3] - q_[3]) < 60 and not eyes: eyes = [p_[0], q_[0]]
        if len(eyes) == 2:
            for k in eyes:
                ey, ex = np.where(lab == k); y0, x0, x1 = ey.min(), ex.min(), ex.max()
                yl = y0 - 7
                if yl < 1: continue
                for x in range(x0 + 1, x1):
                    if al[yl, x]: a[yl, x, :3] = (52, 34, 32)
                    if al[yl - 1, x] and x0 + 3 <= x <= x1 - 3: a[yl - 1, x, :3] = (52, 34, 32)
                for x, dy in ((x0 - 1, 1), (x1 + 1, 1)):
                    if 0 <= x < W and al[yl + dy, x]: a[yl + dy, x, :3] = (52, 34, 32)
    Image.fromarray(a).save(path)

if __name__ == '__main__':
    for p in sys.argv[1:]: marks(p)
