"""야광 = 일반 도트 프레임의 색을 규칙으로 바꿈(AI 재생성 없음 → 전 프레임 통일, 엉뚱한 야광 점 없음).
- 피부·볼터치·머리·원피스·목도리: 어둡게(사용자 지정 2번 사진 톤)
- 망토(채도 높은 연두): 거의 검은 초록
- 망토 발톱 방울·머리핀(하늘색): 민트 발광
- 주황/노랑: 망토에 붙은 것 중 바깥(투명)에 닿는 것=등뼈 → 민트 발광, 망토 안쪽=스티커 → 연두 발광, 피부에 닿는 것=눈 → 금색 유지
- 눈꼬리 빨간 포인트: 빨강 유지"""
import numpy as np
from scipy import ndimage as nd

MINT_L, MINT_D = np.array([120, 255, 205]), np.array([40, 205, 150])
LIME_L, LIME_D = np.array([215, 255, 110]), np.array([130, 200, 40])


def classify(a):
    r, g, b = (a[..., i].astype(int) for i in range(3)); al = a[..., 3] > 0
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); sat = mx - mn; lum = (r + g + b) / 3
    C = {}
    C['outline'] = al & (lum < 60)
    C['accent'] = al & (r > 190) & (g < 110) & (b < 110) & (r - g > 100)
    C['blue'] = al & (b > r + 8) & (b >= g - 12) & (lum > 90) & ~C['outline']
    C['orange'] = al & (r > 170) & (r > g + 25) & (g > b + 30) & (g > 95) & ~C['accent']
    C['cloak'] = al & (g > r) & (g > b + 45) & (sat > 70) & ~C['outline']
    C['hair'] = al & (g >= r - 5) & (g > b) & (sat <= 70) & (lum > 70) & ~((r >= g) & (r - b > 12)) & ~C['cloak'] & ~C['blue'] & ~C['outline']   # 따뜻한 기(r>=g, r>b)는 피부
    C['white'] = al & (lum > 235) & (sat < 20)
    C['warm'] = al & (r >= g) & (r > b) & ~C['accent'] & ~C['orange'] & ~C['white'] & ~C['outline']
    return C, lum


def _round(m):
    ys, xs = np.where(m); h = np.ptp(ys) + 1; w = np.ptp(xs) + 1
    return 0.45 < w / h < 3.6 and m.sum() > 0.45 * w * h   # 반쯤 감은 눈은 납작함   # 눈은 동그랗게 꽉 찬 덩어리

def to_glow(a):
    out = a.copy(); C, lum = classify(a); al = a[..., 3] > 0
    # 원피스의 푸르스름한 흰 음영(발톱 아님): 안쪽에 있고 흰색에 둘러싸인 하늘색 덩어리 → 원피스 흰색으로 취급
    _out3 = nd.binary_dilation(~al, iterations=3); _bl0, _bn0 = nd.label(C['blue'])
    _rb, _gb, _bb = (a[..., i].astype(int) for i in range(3)); _lb = (_rb + _gb + _bb) / 3
    for k in range(1, _bn0 + 1):
        m = _bl0 == k
        ring = nd.binary_dilation(m, iterations=2) & ~m & al
        whn = (ring & (C['white'] | (_lb > 225))).sum() / max(1, ring.sum())
        _clk = (ring & (C['cloak'] | C['outline'])).sum() / max(1, ring.sum())
        _hrn = (ring & C['hair']).sum() / max(1, ring.sum())
        if whn > 0.55 and _clk < 0.2 and _hrn < 0.25 and not (m & _out3).any() and _lb[m].mean() > 160:   # 머리카락 그늘은 원피스로 보지 않음   # 발톱(망토·테두리에 닿음)은 제외
            C['blue'] &= ~m; C['white'] |= m
    f = a[..., :3].astype(float)
    def put(m, col): out[m, :3] = np.clip(col, 0, 255).astype(np.uint8)
    # 기본: 전체 어둡게 + 푸른 기
    put(al, f[al] * 0.38 + np.array([4, 10, 14]))
    put(C['outline'], f[C['outline']] * 0.6)
    put(C['warm'], f[C['warm']] * np.array([0.58, 0.40, 0.40]))                      # 피부·볼·목도리: 어두운 분홍빛 갈색
    put(C['hair'], (lum[C['hair']][:, None] / 255.0) * np.array([78, 102, 84]) + np.array([8, 12, 9]))   # 머리: 밝기만 따르고 색조 고정(회녹색)
    put(C['white'], f[C['white']] * np.array([0.42, 0.46, 0.48]))                     # 원피스: 어두운 회색
    _cream = C['white'] & ((a[..., 0].astype(int) - a[..., 2].astype(int)) > 12)   # 노르스름한 아주 밝은 피부(다리) → 피부색
    put(_cream, f[_cream] * np.array([0.58, 0.40, 0.40]))
    put(C['cloak'], f[C['cloak']] * np.array([0.22, 0.27, 0.15]))                     # 망토: 어두운 올리브(공식 야광 일러스트 톤)
    put(C['accent'], f[C['accent']] * np.array([0.85, 0.6, 0.6]))                     # 눈꼬리 빨강
    # 발광: 하늘색(발톱 방울·머리핀)
    bl = C['blue']; t = ((lum[bl] - lum[bl].min()) / max(1, np.ptp(lum[bl])))[:, None] if bl.any() else 0
    if bl.any(): put(bl, MINT_D + (MINT_L - MINT_D) * t)
    # 눈물·눈 속 하늘색(얼굴 위 작은 덩어리)은 발광 아님 → 원래 색 그대로(조금 어둡게)
    facezone = nd.binary_dilation(C['warm'] | C['white'], iterations=3)
    bll, bln = nd.label(bl)
    for k in range(1, bln + 1):
        m = bll == k
        ring = nd.binary_dilation(m, iterations=2) & ~m & al
        if m.sum() < 80 and (ring & C['cloak']).sum() < 0.15 * ring.sum() and (ring & facezone).sum() > 0.5 * ring.sum():
            put(m, f[m] * 0.85)
    # 피부(다리 등)에 둘러싸인 푸른 그늘은 발광 아님 → 피부색
    for k in range(1, bln + 1):
        m = bll == k
        ring = nd.binary_dilation(m, iterations=2) & ~m & al
        if (ring & C['warm']).sum() > 0.4 * ring.sum() and (ring & C['cloak']).sum() < 0.1 * ring.sum() and m.sum() < 80 and not (m & nd.binary_dilation(~al, iterations=3)).any():   # 발톱(가장자리)은 제외
            put(m, f[m] * np.array([0.58, 0.40, 0.40])); bl = bl & ~m
    # 머리카락 속 푸른 하이라이트·그늘(머리에 둘러싸인 작은 덩어리)은 발광 아님 → 머리색
    hairz = nd.binary_dilation(C['hair'], iterations=1)
    for k in range(1, bln + 1):
        m = bll == k
        ring = nd.binary_dilation(m, iterations=2) & ~m & al
        _ay2 = np.where(al.any(1))[0]
        if m.sum() < 3000 and np.where(m)[0].mean() < _ay2.min() + 0.45 * (_ay2.max() - _ay2.min()) and (ring & hairz).sum() > 0.45 * ring.sum() and (ring & C['cloak']).sum() < 0.25 * ring.sum() and not (m & nd.binary_dilation(~al, iterations=3)).any():   # 머리는 위쪽에만(아래 발톱은 제외)
            put(m, (lum[m][:, None] / 255.0) * np.array([78, 102, 84]) + np.array([8, 12, 9])); bl = bl & ~m
    # 방울 안의 흰 하이라이트·푸른 그림자(작은 덩어리, 하늘색에 닿음) → 발광
    rr, gg, bb2 = (a[..., i].astype(int) for i in range(3))
    cand = al & ~C['outline'] & ~bl & (((lum > 200) & (np.abs(rr - bb2) < 20)) | ((bb2 > rr + 8) & (lum > 45)))
    cl, cn = nd.label(cand); bln = nd.binary_dilation(bl, iterations=1)
    for k in range(1, cn + 1):
        m = cl == k
        if m.sum() < 90 and (m & bln).any(): put(m, MINT_L if lum[m].mean() > 150 else MINT_D)
    # 주황 덩어리 문맥 판정
    # 후드 뿔(맨 위 가운데 큰 주황 덩어리)은 항상 민트 발광
    _hl, _hn = nd.label(C['orange'], structure=np.ones((3, 3))); _ays = np.where(al.any(1))[0]; _axs = np.where(al.any(0))[0]
    _ht, _hh = _ays.min(), max(1, _ays.max() - _ays.min()); _hx0, _hw = _axs.min(), max(1, _axs.max() - _axs.min())
    _horn = np.zeros_like(al)
    for k in range(1, _hn + 1):
        m = _hl == k; yy_, xx_ = np.where(m)
        _tout = (m & nd.binary_dilation(~al, iterations=3)).any()
        if (m.sum() >= 50 and (yy_.min() - _ht) / _hh < 0.14 and 0.3 < (xx_.mean() - _hx0) / _hw < 0.75) or (m.sum() >= 60 and _tout and (yy_.min() - _ht) / _hh < 0.2): _horn |= m   # 누운 자세 뿔·등뼈도
    C['orange'] = C['orange'] & ~_horn
    if _horn.any():
        _lk = lum[_horn]; put(_horn, MINT_D + (MINT_L - MINT_D) * ((_lk - _lk.min()) / max(1, np.ptp(_lk)))[:, None])
    lab, n = nd.label(C['orange'], structure=np.ones((3, 3)))
    face = nd.binary_dilation(C['warm'] & ~C['white'], iterations=5)
    # 흰 눈(blank 등): 얼굴 안쪽의 작은 흰 덩어리는 흰색 유지
    _cands = []; _iris = []
    _w0, _wn0 = nd.label(C['warm']); _fb0 = (0, -999, 0, -999)
    if _wn0:
        _fz0 = nd.sum(C['warm'], _w0, range(1, _wn0 + 1)); _fy0, _fx0 = np.where(_w0 == 1 + int(np.argmax(_fz0))); _fb0 = (_fy0.min(), _fy0.max(), _fx0.min(), _fx0.max())
    EYEW = np.zeros(al.shape, bool); r_, g_, b_ = (a[..., i].astype(int) for i in range(3))
    wl0, wn0 = nd.label(C['white'] | (al & (lum > 225) & ((np.maximum(np.maximum(a[..., 0].astype(int), a[..., 1].astype(int)), a[..., 2].astype(int)) - np.minimum(np.minimum(a[..., 0].astype(int), a[..., 1].astype(int)), a[..., 2].astype(int))) < 25)))
    for k in range(1, wn0 + 1):
        m = wl0 == k
        if not (15 <= m.sum() <= 700): continue
        _ay = np.where(al.any(1))[0]
        pass   # 위치 제한 대신 두 눈 짝 판정 사용
        mf = nd.binary_fill_holes(m) & al
        ring = nd.binary_dilation(mf, iterations=2) & ~mf & al
        face_ring = (ring & (C['warm'] | C['outline'] | C['accent'])).sum() / max(1, ring.sum())
        if 20 <= m.sum() <= 300 and (ring & C['cloak']).sum() < 0.1 * ring.sum() and (ring & C['hair']).sum() < 0.3 * ring.sum() and (ring & C['outline']).sum() > 0.3 * ring.sum() and _round(mf) and (a[m][:, 0].astype(int) - a[m][:, 2].astype(int)).mean() < 12:   # 눈은 검은 테두리로 둘러싸임
            _yy, _xx = np.where(m)
            if _fb0[0] - 6 <= _yy.mean() <= _fb0[1] + 6 and _fb0[2] - 6 <= _xx.mean() <= _fb0[3] + 6:   # 눈은 얼굴(가장 큰 피부) 안에만
                _cands.append((mf, m.sum(), _yy.mean(), _xx.mean()))
    # 눈은 두 개가 나란히(비슷한 크기·높이) 있을 때만 흰 눈으로 인정
    for i_, (mf, sz_, cy_, cx_) in enumerate(_cands):
        if any(j_ != i_ and abs(cy2 - cy_) < 14 and 12 < abs(cx2 - cx_) < 100 and 0.28 < sz2 / sz_ < 3.6 for j_, (_, sz2, cy2, cx2) in enumerate(_cands)):
            inner = mf & ~C['outline']
            out[inner, :3] = np.clip(np.maximum(f[inner], 205) * 0.93, 0, 255).astype(np.uint8)
            EYEW |= mf
    # 얼굴 피부 위 흰 하이라이트(피부에 둘러싸인 흰 덩어리, 눈 제외) → 피부색
    _ay0 = np.where(al.any(1))[0]; ytop0, yh0 = _ay0.min(), _ay0.max() - _ay0.min()
    wl, wn = nd.label(C['white'] & ~EYEW)
    for k in range(1, wn + 1):
        m = wl == k
        ring = nd.binary_dilation(m, iterations=2) & ~m & al
        upper = np.where(m)[0].mean() < ytop0 + 0.55 * yh0
        if (ring & C['warm']).sum() > 0.55 * ring.sum() or (upper and (ring & C['warm']).sum() > 0.25 * ring.sum() and (ring & C['cloak']).sum() < 0.2 * ring.sum()):
            put(m, f[m] * np.array([0.58, 0.40, 0.40]) * 0.92)
        elif upper and (ring & C['hair']).sum() > 0.3 * ring.sum():   # 머리카락 하이라이트 → 머리색
            put(m, (lum[m][:, None] / 255.0) * np.array([78, 102, 84]) + np.array([8, 12, 9]))
        elif upper and m.sum() < 60 and (ring & C['cloak']).sum() < 0.3 * ring.sum():   # 얼굴 옆 작은 흰 점 → 피부
            put(m, f[m] * np.array([0.58, 0.40, 0.40]) * 0.92)
    skin_near = face
    empty_near = nd.binary_dilation(~al, iterations=3)
    ays = np.where(al.any(1))[0]; ytop, yh = ays.min(), ays.max() - ays.min()
    _wl, _wn = nd.label(C['warm'])   # 얼굴 = 가장 큰 피부 덩어리 중 위쪽
    _fbox = (0, -999, 0, -999)
    if _wn:
        _fz = nd.sum(C['warm'], _wl, range(1, _wn + 1)); _fy, _fx = np.where(_wl == 1 + int(np.argmax(_fz)))
        _fbox = (_fy.min(), _fy.max(), _fx.min(), _fx.max())
    for k in range(1, n + 1):
        m = lab == k
        cy = np.where(m)[0].mean()
        ring = nd.binary_dilation(m, iterations=3) & ~m & al
        cloak_frac = (ring & C['cloak']).sum() / max(1, ring.sum())
        _cy, _cx = np.where(m); _inface = _fbox[0] - 4 <= _cy.mean() <= _fbox[1] + 4 and _fbox[2] - 4 <= _cx.mean() <= _fbox[3] + 4
        if _inface and m.sum() < 160 and cloak_frac < 0.25 and (ring & (C['warm'] | C['outline'] | C['hair'])).sum() > 0.5 * ring.sum() and (nd.binary_dilation(m, iterations=6) & C['warm']).sum() > 0.6 * m.sum():   # 눈(홍채)
            _yy, _xx = np.where(m); _iris.append((m, m.sum(), _yy.mean(), _xx.mean())); continue
        if (ring & C['warm']).sum() > 0.45 * ring.sum() and cloak_frac < 0.05 and (ring & (lum > 200)).sum() < 0.15 * ring.sum() and not _inface:   # 피부에 둘러싸인 주황(다리 반창고 얼룩 등) → 어두운 피부톤
            put(m, f[m] * np.array([0.58, 0.40, 0.40])); continue
        if m.sum() < 45 and (nd.binary_dilation(m, iterations=2) & C['warm']).any():   # 피부 위 작은 주황(볼 주근깨·입 안) → 어두운 피부톤
            put(m, f[m] * np.array([0.58, 0.40, 0.40])); continue
        axs = np.where(al.any(0))[0]; upright = (axs.max() - axs.min()) < 1.4 * yh
        if upright and cy < ytop + 0.33 * yh and not (m & empty_near).any() and m.sum() < 120:   # 후드 귀 안쪽: 주황 유지
            put(m, f[m] * 0.7); continue
        redbow = al & (a[..., 0] > 150) & (a[..., 1] < 100) & (a[..., 2] < 100)
        _my, _mx = np.where(m)
        _touch = (nd.binary_dilation(m, iterations=4) & (C['warm'] | redbow)).sum() > 8   # 스티커는 흰 테두리라 피부·리본에 안 닿음
        if _touch and m.sum() >= 40 and not (m & empty_near).any() and _fbox[1] - 6 <= _my.mean() <= _fbox[1] + 0.22 * yh and _fbox[2] - 10 <= _mx.mean() <= _fbox[3] + 10:   # 얼굴 바로 아래 주황 = 목도리
            put(m, f[m] * np.array([0.58, 0.40, 0.40])); continue
        if (cloak_frac < 0.3 and (ring & C['warm']).sum() > 0.2 * ring.sum() and (ring & (lum > 200)).sum() < 0.25 * ring.sum() and not (m & empty_near).any()) or (m.sum() >= 80 and (nd.binary_dilation(m, iterations=3) & redbow).sum() > 5):   # 목도리(주황 망토): 피부·리본에 닿음 → 어둡게
            put(m, f[m] * np.array([0.58, 0.40, 0.40])); continue
        lk = lum[m]; tt = ((lk - lk.min()) / max(1, np.ptp(lk)))[:, None]
        if (m & empty_near).any(): put(m, MINT_D + (MINT_L - MINT_D) * tt)        # 등뼈(바깥에 닿음)
        else:
            put(m, LIME_D + (LIME_L - LIME_D) * tt)                                     # 스티커
            ring = nd.binary_dilation(m, iterations=3) & (lum > 200) & al & ~C['outline']   # 스티커 흰 테두리 → 연두 발광
            put(ring, LIME_L)
    # 입 안 빨강(얼굴 아래쪽의 빨간 덩어리) → 어둡게. 눈꼬리 포인트(위쪽)는 유지
    _al, _an = nd.label(C['accent'])
    for k in range(1, _an + 1):
        m = _al == k; _ya, _xa = np.where(m)
        if ((a[m][:, 0] == 222) & (a[m][:, 1] == 66)).mean() > 0.5:   # 지정색 빨강: 눈꼬리 포인트만 유지, 입·리본에 묻은 건 어둡게
            _fw = max(1, _fbox[3] - _fbox[2]); _fh = max(1, _fbox[1] - _fbox[0])
            _rx = (_xa.mean() - _fbox[2]) / _fw; _ry = (_ya.mean() - _fbox[0]) / _fh
            eyept = _fbox[0] - 4 <= _ya.mean() <= _fbox[1] - 3 and -0.1 <= _rx <= 1.1 and (_ry < 0.5 or _rx < 0.33 or _rx > 0.67) and m.sum() < 45
            if not eyept: put(m, f[m] * np.array([0.5, 0.28, 0.28]))
            continue
        _fw = _fbox[3] - _fbox[2]
        if _fbox[2] + 0.25 * _fw <= _xa.mean() <= _fbox[3] - 0.25 * _fw and _ya.mean() - _fbox[0] > 0.6 * _fw and _ya.mean() < _fbox[1] - 2 and (nd.binary_dilation(m, iterations=3) & ~m & (C['warm'] | C['outline'])).sum() > 0.7 * (nd.binary_dilation(m, iterations=3) & ~m).sum() and not (nd.binary_dilation(m, iterations=3) & C['cloak']).any():   # 입은 피부·선으로 둘러싸임(리본은 아님)
            put(m, f[m] * np.array([0.55, 0.32, 0.32]))
    # 홍채는 두 개가 나란히 있을 때만 주황 유지, 나머지(입 안·목도리 조각)는 어두운 피부톤
    _pairs = [(abs(c1[2] - c2[2]), (c1[2] + c2[2]) / 2, i1, i2) for i1, c1 in enumerate(_iris) for i2, c2 in enumerate(_iris)
              if i1 < i2 and abs(c1[2] - c2[2]) < 10 and 20 < abs(c1[3] - c2[3]) < 100 and 0.28 < c1[1] / c2[1] < 3.6]
    _eyey = min(_pairs)[1] if _pairs else None; _eyeset = {min(_pairs)[2], min(_pairs)[3]} if _pairs else set()
    for i_, (m, sz_, cy_, cx_) in enumerate(_iris):
        if _eyey is not None and i_ not in _eyeset and cy_ > _eyey + 5:   # 두 눈보다 아래 = 입 → 어둡게
            put(m, f[m] * np.array([0.58, 0.40, 0.40])); continue
        pair = any(j_ != i_ and abs(cy2 - cy_) < 10 and 20 < abs(cx2 - cx_) < 100 and 0.28 < sz2 / sz_ < 3.6 for j_, (_, sz2, cy2, cx2) in enumerate(_iris))
        lower_exists = any(cy2 > cy_ + 8 for _, _, cy2, _ in _iris)   # 아래에 다른 후보(입)가 있으면 이건 눈
        upper_face = lower_exists or (cy_ - _fbox[0]) < 0.5 * (_fbox[3] - _fbox[2])   # 혼자면 얼굴 윗선에서 가까우면 눈, 멀면 입
        put(m, f[m] * 0.85 if (pair or upper_face) else f[m] * np.array([0.58, 0.40, 0.40]))
    # 공식 야광처럼: 망토·후드 바깥 테두리선이 민트로 빛남
    edge1 = al & nd.binary_dilation(~al, iterations=1)                       # 실루엣 맨 바깥 1px
    edge2 = al & nd.binary_dilation(edge1, iterations=1) & ~edge1
    o_l = out[..., :3].astype(int).mean(-1)
    _hairside = nd.binary_dilation(C['hair'] | C['warm'], iterations=3) & ~nd.binary_dilation(C['cloak'] | C['blue'], iterations=3)   # 머리카락·피부 가장자리는 발광 안 함(망토 테두리만)
    # 겉테두리: 맨 바깥 1px 한 줄만, 망토·후드·발톱·꼬리 쪽만 발광(머리카락·피부 쪽은 제외). 안쪽 2번째 줄은 칠하지 않음(끊겨 보임)
    _ins = al & ~edge1 & ~C['outline']
    _cl = nd.binary_dilation(_ins & (C['cloak'] | C['blue'] | C['orange'] | C['white']), iterations=3)
    _hs = nd.binary_dilation(_ins & (C['hair'] | C['warm']), iterations=3)
    _sk = nd.binary_dilation(_ins & C['warm'], iterations=2) & ~_cl   # 얼굴·다리 피부 가장자리만 제외(머리카락 가장자리는 발광)
    _ok = edge1 & ~_sk
    _ok = nd.binary_closing(_ok, structure=np.ones((3, 3))) & edge1   # 1~2px 끊김 메우기
    _ok2 = nd.binary_dilation(_ok, structure=np.ones((3, 3))) & al & nd.binary_dilation(~al, iterations=2) & ~_sk   # 2px 두께
    put(_ok2, MINT_D + (MINT_L - MINT_D) * 0.7)
    # 원피스: 흰 천 안의 푸른 역W 선을 찾고, 선으로 갈라진 흰 조각 중 선보다 아래쪽 조각만 발광
    W_ = C['white'] & ~EYEW & ~_cream
    _r, _g, _b = (a[..., i].astype(int) for i in range(3))
    blue_line = al & ~C['white'] & ~C['cloak'] & (_b > _r + 14) & (_b >= _g) & (lum > 50) & (lum < 140)   # 역W 선: 진한 청회색
    zz = blue_line & nd.binary_dilation(W_, iterations=2)
    zl, zn = nd.label(zz, structure=np.ones((3, 3)))
    keepz = np.zeros_like(zz)
    for q in range(1, zn + 1):
        mq = zl == q; yq, xq = np.where(mq)
        if np.ptp(xq) >= 6 or mq.sum() >= 12: keepz |= mq   # 가는 선(지그재그) 조각
    zz = keepz
    if zz.any():
        wl_, wn_ = nd.label(W_)
        zd = nd.binary_dilation(zz, iterations=2)
        below = np.zeros_like(W_)
        for q in range(1, wn_ + 1):
            mq = wl_ == q
            if mq.sum() < 6: continue
            touch = mq & zd
            if not touch.any(): continue
            zy, zx = np.where(nd.binary_dilation(mq, iterations=2) & zz)
            if len(zy) == 0: continue
            cols = {}
            for y_, x_ in zip(zy, zx): cols.setdefault(x_, []).append(y_)
            xk = np.array(sorted(cols)); yk = np.array([np.mean(cols[x_]) for x_ in xk])
            my, mx = np.where(mq)
            if np.ptp(xk) < 4:   # 선이 짧으면 덩어리 단위로 판정
                if my.mean() > yk.mean() + 1: below |= mq
                continue
            ly = np.interp(mx, xk, yk)
            sel = my > ly + 0.5
            below[my[sel], mx[sel]] = True
        put(below, MINT_D + (MINT_L - MINT_D) * 0.5)
        put(zz, MINT_D * 0.75)
    out = _cleanup(out, a, C, EYEW)
    out = grey_sweep(out, EYEW)
    return out


def _cleanup(out, a, C, EYEW=None):
    """야광 변환 뒤 남는 하얀 점·발광부 회색 구멍 정리"""
    al = out[..., 3] > 0; o = out[..., :3].astype(int)
    lum_o = o.mean(-1); sat_o = o.max(-1) - o.min(-1)
    glow = al & (o[..., 1] > 170) & (o[..., 1] > o[..., 0] + 40)              # 민트·연두 발광
    # 발광 덩어리 안의 구멍(회색·어두운 점) 채우기
    gf = nd.binary_closing(glow, structure=np.ones((3, 3)), iterations=1) & al & ~glow & ~C['outline']
    if gf.any():
        idx = nd.distance_transform_edt(~glow, return_distances=False, return_indices=True)
        out[gf, :3] = out[idx[0][gf], idx[1][gf], :3]
    # 밝은 무채색 점(하이라이트가 남은 것): 눈 흰자 아닌 작은 덩어리 → 주변 색
    o = out[..., :3].astype(int); lum_o = o.mean(-1); sat_o = o.max(-1) - o.min(-1)
    spot = al & (lum_o > 140) & (sat_o < 45)
    if EYEW is not None: spot &= ~EYEW
    lab, n = nd.label(spot)
    keep = np.zeros_like(spot)
    for k in range(1, n + 1):
        m = lab == k
        if m.sum() >= 200: keep |= m
    small = spot & ~keep
    near_glow = small & nd.binary_dilation(glow, iterations=2)
    out[near_glow, :3] = MINT_L.astype(np.uint8); small &= ~near_glow
    if small.any():
        idx = nd.distance_transform_edt(small | ~al, return_distances=False, return_indices=True)
        out[small, :3] = out[idx[0][small], idx[1][small], :3]
    return out


def grey_sweep(out, EYEW):
    """마지막 정리: 흰색·회색(무채색) 작은 덩어리 → 가장 가까운 유채색 픽셀 색.
    남기는 것: 흰 눈동자(blank, 30px 이상 덩어리) / 원피스 같은 큰 면(350px 이상)"""
    al = out[..., 3] > 0; o = out[..., :3].astype(int)
    lum = o.mean(-1); sat = o.max(-1) - o.min(-1)
    grey = al & (sat < 30) & (lum > 70)
    lab, n = nd.label(grey); sz = nd.sum(grey, lab, range(1, n + 1))
    big = np.isin(lab, 1 + np.where(sz > 350)[0])
    eye_ids = [i + 1 for i in range(n) if sz[i] >= 30 and (EYEW & (lab == i + 1)).sum() > 0.5 * sz[i]]
    keep = big | np.isin(lab, eye_ids)
    g = grey & ~keep
    if g.any():
        src = al & ~grey & (lum > 25)
        idx = nd.distance_transform_edt(~src, return_distances=False, return_indices=True)
        out[g, :3] = out[idx[0][g], idx[1][g], :3]
    return out
