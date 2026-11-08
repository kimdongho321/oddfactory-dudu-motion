"""blank 흰 눈(떠 있는 눈꺼풀 포함)을 도트 단계에서 그대로 옮겨 찍음 → 눈꺼풀 모양 통일. 볼터치 사선 3개는 양쪽 볼에."""
import sys, numpy as np
from scipy import ndimage as nd
from PIL import Image
SKIN = None

def eyes(a):
    A = a[..., :3].astype(int); al = a[..., 3] > 0; r, b = A[..., 0], A[..., 2]
    ys, xs = np.where(al); up = np.arange(a.shape[0])[:, None] < ys.min() + 0.6 * (ys.max() - ys.min())
    w = al & up & (A.min(-1) > 220) & (np.abs(r - b) < 25); lab, n = nd.label(w); sz = nd.sum(w, lab, range(1, n + 1))
    c = [(i + 1, sz[i], *np.argwhere(lab == i + 1).mean(0)) for i in range(n) if sz[i] >= 20]
    best = None
    for p in c:
        for q in c:
            if p[0] < q[0] and abs(p[2] - q[2]) < 6 and 0.6 < p[1] / q[1] < 1.6 and 10 < abs(p[3] - q[3]) < 70:
                s = p[1] + q[1]
                if best is None or s > best[0]: best = (s, p, q)
    if not best: return []
    out = []
    for p in sorted(best[1:], key=lambda t: t[3]):
        yy, xx = np.where(lab == p[0]); out.append((yy.min(), yy.max(), xx.min(), xx.max()))
    return out

def stamps(src):
    a = np.array(Image.open(src).convert('RGBA')); E = eyes(a); res = []
    for (y0, y1, x0, x1) in E:
        Y0, Y1, X0, X1 = y0 - 8, y1 + 1, x0 - 2, x1 + 3
        box = a[Y0:Y1 + 1, X0:X1 + 1].copy(); A = box[..., :3].astype(int)
        keep = (A.mean(-1) < 110) | ((A.min(-1) > 220))   # 선·흰자만
        res.append((box, keep, (y0 - Y0, y1 - Y0, x0 - X0, x1 - X0)))
    return res

def apply(path, S, FIX=None):
    a = np.array(Image.open(path).convert('RGBA')); E = eyes(a)
    if len(E) != 2: return False
    A = a[..., :3].astype(int)
    for (y0, y1, x0, x1), (box, keep, (sy0, sy1, sx0, sx1)) in zip(E, S):
        tw, th = x1 - x0 + 1, y1 - y0 + 1; sw, sh = sx1 - sx0 + 1, sy1 - sy0 + 1
        fx, fy = (FIX, FIX) if FIX else (tw / sw, th / sh)
        bh, bw = box.shape[:2]; nh, nw = max(1, round(bh * fy)), max(1, round(bw * fx))
        B = np.array(Image.fromarray(box).resize((nw, nh), Image.NEAREST)); K = np.array(Image.fromarray(keep.astype(np.uint8) * 255).resize((nw, nh), Image.NEAREST)) > 0
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        oy, ox = int(round(cy - (sy0 + sy1) / 2 * fy)), int(round(cx - (sx0 + sx1) / 2 * fx))
        # 기존 눈·속눈썹 지우기(피부색), 볼터치·눈물은 유지
        reg = np.zeros(a.shape[:2], bool); reg[max(0, oy):oy + nh, max(0, ox):ox + nw] = True
        old = reg & ((A.mean(-1) < 110) | (A.min(-1) > 220))
        skin = np.median(A[reg & (A[..., 0] > 235) & (A[..., 1] > 200) & (A[..., 2] > 180)], 0) if (reg & (A[..., 0] > 235) & (A[..., 1] > 200)).any() else np.array([252, 231, 215])
        a[old, :3] = skin
        for yy in range(nh):
            for xx in range(nw):
                Y, X = oy + yy, ox + xx
                if 0 <= Y < a.shape[0] and 0 <= X < a.shape[1] and K[yy, xx] and a[Y, X, 3] > 0: a[Y, X, :3] = B[yy, xx, :3]
    Image.fromarray(a).save(path); return True

def hatch(path):
    a = np.array(Image.open(path).convert('RGBA')); A = a[..., :3].astype(int); al = a[..., 3] > 0; r, g, b = A[..., 0], A[..., 1], A[..., 2]
    E = eyes(a)
    H, W = al.shape
    pink = al & (r > 215) & (g > 140) & (g < 205) & (b > 125) & (b < 195) & (r - g > 35) & (r - g < 85)
    if len(E) != 2:   # 눈 감은 장면: 위쪽 큰 분홍 덩어리 두 개
        ys, xs = np.where(al); up = np.arange(H)[:, None] < ys.min() + 0.6 * (ys.max() - ys.min())
        pl, pn = nd.label(pink & up); ps = nd.sum(pink & up, pl, range(1, pn + 1))
        E = []
        for i in np.argsort(-ps)[:2]:
            if ps[i] < 10: continue
            yy, xx = np.where(pl == i + 1); E.append((yy.min() - 6, yy.min(), xx.min() + 4, xx.max() - 4))
        E = sorted(E, key=lambda e: e[2])
        if len(E) != 2: return
    for i, (y0, y1, x0, x1) in enumerate(E):
        reg = np.zeros((H, W), bool); cx = (x0 + x1) // 2
        if i == 0: reg[y1 - 2:y1 + 16, max(0, x0 - 16):cx + 2] = True
        else: reg[y1 - 2:y1 + 16, cx - 2:min(W, x1 + 16)] = True
        m = pink & reg
        if m.sum() < 6: continue
        my, mx = np.where(m); cy_, cx_ = int(round(my.mean())), int(round(mx.mean()))
        for dx in (-3, 0, 3):
            for t in range(3):
                y_, x_ = cy_ - 1 + t, cx_ + dx + 1 - t
                if 0 <= y_ < H and 0 <= x_ < W and al[y_, x_] and A[y_, x_].mean() > 150: a[y_, x_, :3] = (214, 98, 110)
    Image.fromarray(a).save(path)

if __name__ == '__main__':
    S = stamps(sys.argv[1]); sw = np.mean([k[2][3] - k[2][2] + 1 for k in S])
    ws = []
    for p in sys.argv[2:]:
        E = eyes(np.array(Image.open(p).convert('RGBA')))
        if len(E) == 2: ws += [e[3] - e[2] + 1 for e in E]
    FIX = float(np.median(ws)) / sw; print('fixed scale', FIX)
    for p in sys.argv[2:]:
        ok = apply(p, S, FIX); hatch(p); print(p, ok)
