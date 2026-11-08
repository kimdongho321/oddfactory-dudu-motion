"""피부 붉어짐 통일: 기본 스탠딩(idle_0)의 '피부 대비 홍조 면적' 비율을 기준으로,
그보다 넓게 칠해진 홍조를 바깥 테두리부터 한 겹씩 깎아 피부색으로 되돌림(입·혀는 피부와 맞닿지 않아 건드리지 않음)."""
import numpy as np
from scipy import ndimage as nd

SKIN = np.array([252, 231, 215]); LIGHT = [np.array([248, 189, 172]), np.array([228, 169, 152])]
STRONG = [np.array([250, 148, 125]), np.array([230, 134, 114])]


def _is(a, cols): return np.any([np.all(a[..., :3] == c, -1) for c in cols], 0) & (a[..., 3] > 0)


def stats(a):
    sk = _is(a, [SKIN]).sum(); return _is(a, STRONG).sum() / max(1, sk), _is(a, LIGHT).sum() / max(1, sk)


WARM = np.array([250, 218, 196])     # 붉은 기 도는 피부 바탕색(생성 시 얼굴 전체가 이 색으로 칠해지면 붉어 보임)


def fix(a, target, tol=1.15, max_iter=12):
    a = a.copy(); ts, tl = target
    warm = _is(a, [WARM]); skin = _is(a, [SKIN])
    if warm.sum() > 0.25 * max(1, skin.sum()):   # 바탕 피부가 붉은 톤 → 기본 피부색으로
        a[warm, :3] = SKIN
    for _ in range(max_iter):
        s, l = stats(a); changed = False
        skin = _is(a, [SKIN]); light = _is(a, LIGHT); strong = _is(a, STRONG)
        if s > ts * tol:
            edge = strong & nd.binary_dilation(skin | light)
            if edge.any(): a[edge, :3] = LIGHT[0]; changed = True
        if l > tl * tol:
            skin = _is(a, [SKIN]); light = _is(a, LIGHT)
            edge = light & nd.binary_dilation(skin)
            if edge.any(): a[edge, :3] = SKIN; changed = True
        if not changed: break
    return a


def fix_glow_legs(a, ref_rg, ref_rb):
    """야광: 다리·몸 피부(실루엣 아래 45%)가 붉게 뜬 픽셀만 기준 피부의 색차로 되돌림(얼굴 볼터치는 건드리지 않음)"""
    a = a.copy(); al = a[..., 3] > 0
    ys = np.where(al.any(1))[0]
    if not len(ys): return a
    y0 = ys.min() + int((ys.max() - ys.min()) * 0.55)
    r, g, b = (a[..., i].astype(int) for i in range(3))
    sk = al & (r > 120) & (r >= g) & (g >= b - 10) & (r - b < 120) & (r - g > ref_rg + 18)
    sk[:y0] = False
    nr = r[sk]; a[sk, 1] = np.clip(nr - ref_rg, 0, 255); a[sk, 2] = np.clip(nr - ref_rb, 0, 255)
    return a
