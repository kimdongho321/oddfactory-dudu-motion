"""edit2/<mode>/frames → web/frames + motions.json + gif.
- 키프레임 사이에 중간 프레임 x<i> 삽입, 시간은 반씩
- headbutt: 0~5(돌진·충돌) → x5s(전환) → sad 1~7(주저앉아 울기)  (사용자 요청 2026-11-07: 넘어지는 부분을 sad로 교체, sad 버튼은 숨김)
- 엎드린 프레임(sleep 4~, switch 0~2)은 바닥선(아래끝)과 가로 위치를 한 장 기준으로 고정 → 위아래 흔들림 제거"""
import os, json, shutil
import numpy as np
from PIL import Image
import glowmap

R = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(R, 'edit_motions.json'), encoding='utf-8'))
WEB = os.path.join(R, 'web'); FR = os.path.join(WEB, 'frames')
shutil.rmtree(FR, ignore_errors=True); os.makedirs(FR, exist_ok=True)
PX, PT = 40, 60
HIDE = {'sad', 'tickle', 'happy', 'walk'}   # tickle: Codex 간지럼(pat 자리)과 겹쳐 숨김
PIN = {'sleep': lambda k: (k.lstrip('x').isdigit() and int(k.lstrip('x')) >= 4), 'switch': lambda k: k in ('0', 'x0', '1', 'x1')}


def seq_of(m, v, src):
    F = v['frames']; n = len(F); seq = []
    for i in range(n):
        seq.append((m, str(i), F[i].get('dx', 0), F[i].get('dy', 0), v['ms'][i]))
        j = (i + 1) % n
        if i == n - 1 and 'loop_from' in v: j = v['loop_from']
        if os.path.exists(os.path.join(src, f'{m}_x{i}.png')) and not (j == 0 and v['play'] == '1회'):
            seq[-1] = seq[-1][:4] + (max(40, v['ms'][i] // 2),)
            seq.append((m, f'x{i}', (F[i].get('dx', 0) + F[j].get('dx', 0)) // 2, (F[i].get('dy', 0) + F[j].get('dy', 0)) // 2, max(40, v['ms'][i] // 2)))
    return seq


def bbox(path):
    a = np.array(Image.open(path))[..., 3] > 0; ys, xs = np.where(a); return xs.min(), xs.max(), ys.max()


from scipy import ndimage as nd


def fit_to(a, ref):
    """a를 ref 실루엣에 맞춤(이동 ±10px, 크기 0.9~1.1) — 같은 자세 프레임끼리 크기·위치 흔들림 제거"""
    ra = ref[..., 3] > 0; best = (-1, a)
    H, W = ra.shape
    for sc in (1.0,):   # 크기 변경 없음(확대·축소하면 도트가 뭉개짐) — 위치만 맞춤
        im = Image.fromarray(a); im = im.resize((round(im.width * sc), round(im.height * sc)), Image.NEAREST)
        b = np.zeros_like(a); bb = np.array(im); h, w = bb.shape[:2]
        oy, ox = (H - h) // 2, (W - w) // 2
        ys, xs = slice(max(0, oy), min(H, oy + h)), slice(max(0, ox), min(W, ox + w))
        b[ys, xs] = bb[max(0, -oy):max(0, -oy) + (ys.stop - ys.start), max(0, -ox):max(0, -ox) + (xs.stop - xs.start)]
        ba = b[..., 3] > 0
        for dy in range(-10, 11, 2):
            for dx in range(-10, 11, 2):
                m = np.roll(np.roll(ba, dy, 0), dx, 1); iou = (m & ra).sum() / max(1, (m | ra).sum())
                if iou > best[0]: best = (iou, np.roll(np.roll(b, dy, 0), dx, 1), sc, dy, dx)
    iou, b, sc, dy, dx = best
    for ddy in (-1, 0, 1):
        for ddx in (-1, 0, 1):
            m = np.roll(np.roll(b[..., 3] > 0, ddy, 0), ddx, 1); i2 = (m & ra).sum() / max(1, (m | ra).sum())
            if i2 > iou: iou, b = i2, np.roll(np.roll(b, ddy, 0), ddx, 1)
    return b


def eye_band(ref):
    """ref에서 흰 눈동자 위치 → 눈 띠 영역(눈썹 아래~코 위)"""
    r, g, b = (ref[..., i].astype(int) for i in range(3)); al = ref[..., 3] > 0
    w = al & (r > 235) & (g > 235) & (b > 235)
    ays = np.where(al.any(1))[0]; w[ays.min() + int((ays.max() - ays.min()) * 0.5):] = False   # 원피스 흰색 제외(위쪽 절반만)
    lab, n = nd.label(w); sz = nd.sum(w, lab, range(1, n + 1))
    cand = [i + 1 for i in np.argsort(sz)[::-1] if 15 < sz[i] < 500][:2]
    m = np.isin(lab, cand); ys, xs = np.where(m)
    return max(0, ys.min() - 6), ys.max() + 3, max(0, xs.min() - 4), xs.max() + 5


ALIGN = {}   # (motion) -> (ref key, keys to align, eye-only keys)
ALIGN['headbutt'] = ('12', {'12', '13', '14', '15', '16', '17', '18'}, set())   # 눈 바꿔끼우기 안 함(원래 그림 그대로, 위치만 고정)
ALIGN['blank'] = ('5', {str(i) for i in range(5, 13)} | {f'x{i}' for i in range(5, 13)}, set())

out = {}
for mode in ['normal', 'glow']:
    src = os.path.join(R, 'edit2', 'hand4b', 'frames')   # 야광도 일반 프레임에서 규칙 변환(glowmap)
    for m, v in M.items():
        if m in HIDE: continue
        seq = seq_of(m, v, src)
        if m == 'headbutt':
            keep = ['0', 'x0', '1', 'x1', '2', 'x2', '3', 'x3', '4', 'x4', '5', 'x5', '6', 'x6', '7']
            hb = [x for x in seq if x[1] in keep]
            D = lambda k, t: ('headbutt', k, -8, 0, t)
            blink = [D('16', 35), D('13', 35), D('17', 35), D('14', 70), D('17', 35), D('13', 35), D('16', 35)]
            daze = [D('12', 420)] + blink + [D('12', 500)]   # 마지막 두 장 삭제(사용자 요청)
            sad = [x for x in seq_of('sad', M['sad'], src) if x[1] not in ('0', 'x0', '1', 'x1', 'x7')]
            seq = hb + daze   # 울기 제거(사용자 요청 2026-11-08)
        if m == 'idle':   # eat2 자세로 오물오물(사용자 요청 2026-11-08)
            E = lambda v, t, dy=0: ('idle', 'E' + v, 0, dy, t)
            seq = [E('base', 500), E('chew1', 140), E('chew2', 140), E('chew1', 140), E('chew2', 140), E('base', 700), E('blink', 90), E('base', 600), E('chew1', 140), E('chew2', 140), E('chew1', 140), E('base', 800)]
        if m == 'blank':   # 손가락 빠는 반복: 같은 그림 1장에서 눈·입만 바꾼 4장으로(얼굴형 통일)
            cut = [k for k, x in enumerate(seq) if x[1] == '5'][0]
            L = lambda v, t: ('blank', 'L' + v, 0, 0, t)
            seq = [x for x in seq[:cut] if x[1] in ('0', 'x0', '1', 'x1', '3')]   # 손 올리는 중간장(손가락 깨짐) 제외
            seq = seq + [L('base', 500), L('suck', 220), L('base', 260), L('suck', 220), L('base', 420), L('half', 70), L('closed', 100), L('half', 70)]
        ref = None; names, ms = [], []
        for mm, key, dx, dy, t in seq:
            p = os.path.join(src, f'{mm}_{key}.png')
            if not os.path.exists(p): continue
            im = Image.open(p)
            if mm == 'sad':   # 울 때는 눈꼬리 빨간 포인트 없음(사용자 요청 2026-11-08) → 주변 피부색으로
                _a = np.array(im.convert('RGBA')); _rd = (_a[..., 0] == 222) & (_a[..., 1] == 66) & (_a[..., 2] == 58)
                if _rd.any():
                    _ok = (_a[..., 3] > 0) & ~_rd & (_a[..., 0] > 200) & (_a[..., 1] > 150)
                    _ix = nd.distance_transform_edt(~_ok, return_distances=False, return_indices=True)
                    _a[_rd] = _a[_ix[0][_rd], _ix[1][_rd]]; im = Image.fromarray(_a)
            if mm in ALIGN and key in ALIGN[mm][1]:
                refk, _, eyes = ALIGN[mm]
                ref = np.array(Image.open(os.path.join(src, f'{mm}_{refk}.png')).convert('RGBA'))
                a = fit_to(np.array(im.convert('RGBA')), ref)
                if key in eyes:   # 눈만 바뀌는 깜빡임: 기준 프레임에 눈 띠만 교체 → 몸 위치·크기 완전 고정
                    y0, y1, x0, x1 = eye_band(ref); c = ref.copy()
                    def eyepix(x):
                        q = x[..., :3].astype(int); lm = q.mean(-1)
                        return (lm < 90) | ((lm > 225) & (q.max(-1) - q.min(-1) < 25))   # 눈 윤곽(어두움)·흰자
                    band = np.zeros(ref.shape[:2], bool); band[y0:y1, x0:x1] = True
                    mk = band & (eyepix(a) | eyepix(ref)) & (a[..., 3] > 0)
                    skin = ref[y0:y1, x0:x1][~eyepix(ref[y0:y1, x0:x1]) & (ref[y0:y1, x0:x1, 3] > 0)]
                    skin_col = np.median(skin[:, :3], 0).astype(np.uint8) if len(skin) else None
                    fillsk = mk & ~eyepix(a)                     # ref엔 눈인데 a엔 피부 → 기준 피부색으로
                    c[mk] = a[mk]
                    if skin_col is not None: c[fillsk, :3] = skin_col
                    a = c
                im = Image.fromarray(a)
            if mode == 'glow': im = Image.fromarray(glowmap.to_glow(np.array(im.convert('RGBA'))))
            W, H = im.size
            if m in PIN and PIN[m](key):
                x0, x1, bot = bbox(p)
                if ref is None: ref = (x0, bot)
                dx, dy = ref[0] - x0, ref[1] - bot
            c = Image.new('RGBA', (W + 2 * PX, H + PT), (0, 0, 0, 0)); c.alpha_composite(im, (PX + dx, PT + dy))
            nm = f'{mode}_{m}_{mm}_{key}.png'; c.save(os.path.join(FR, nm)); names.append(nm); ms.append(t)
        o = out.setdefault(m, {'label': v['label'], 'play': v['play']}); o[mode] = names; o['ms_' + mode] = ms
        if m == 'blank':
            o['loopFrom'] = [k for k, nm in enumerate(names) if nm.endswith('_Lbase.png')][0]; o['loopTo'] = len(names) - 1
        elif 'loop_from' in v:
            lf = f"_{v['loop_from']}.png"; hits = [k for k, nm in enumerate(names) if nm.endswith(lf)]
            if hits: o['loopFrom'] = hits[0]; o['loopTo'] = len(names) - 1
# Codex가 만든 알림 포효·간지럼을 roar·pat 자리에 사용 (사용자 요청 2026-11-07)
CI = json.load(open(os.path.join(R, 'codex_import.json'), encoding='utf-8'))
for slot, cid, label in [('roar', 'roar', '알림 도착 (알림 포효 · Codex)'), ('pat', 'tickle', '캐릭터 톡 터치 (간지럼 · Codex)')]:
    c = CI[cid]; n = len(c['times']); o = {'label': label, 'play': out[slot]['play']}
    for mode, var in [('normal', c['variant']), ('glow', c['variant'])]:
        strip = Image.open(os.path.join(WEB, 'codex-v3', 'assets', f'{cid}-new-{var}-strip.png'))
        names = []
        for i in range(n):
            f = strip.crop((i * 306, 0, (i + 1) * 306, 271))
            if mode == 'glow': f = Image.fromarray(glowmap.to_glow(np.array(f.convert('RGBA'))))
            cv = Image.new('RGBA', (306, 281), (0, 0, 0, 0)); cv.alpha_composite(f, (0, 10))
            nm = f'{mode}_{slot}_codex_{i}.png'; cv.save(os.path.join(FR, nm)); names.append(nm)
        o[mode] = names; o['ms_' + mode] = c['times']
    if slot == 'pat':   # Codex 0~4(눕기) → 우리 다리 자전거 4장 반복 (사용자 영상처럼 양다리 교대)
        for mode in ('normal', 'glow'):
            names = o[mode][:5]; ms = o['ms_' + mode][:5]
            for i in range(4):
                im = Image.open(os.path.join(R, 'edit2', 'patloop', f'p{i}.png')).convert('RGBA')
                if mode == 'glow': im = Image.fromarray(glowmap.to_glow(np.array(im)))
                cv = Image.new('RGBA', (306, 281), (0, 0, 0, 0)); cv.alpha_composite(im, (0, 10))
                nm = f'{mode}_pat_loop_{i}.png'; cv.save(os.path.join(FR, nm)); names.append(nm); ms.append(110)
            o[mode] = names; o['ms_' + mode] = ms
        o['loopFrom'], o['loopTo'] = 5, 8; o['play'] = '1회 후 반복'
    out[slot] = o
# 비교용: Grok 걷기 영상 한 주기를 도트로 변환한 걷기(하체가 실제로 교대)
_hp = np.array(Image.open(os.path.join(R, 'edit2', 'hand4b', 'frames', 'eat_0.png')).convert('RGBA')).astype(int)
_hm = (_hp[..., 3] > 0) & (_hp[..., 1] > _hp[..., 0] + 4) & (_hp[..., 1] > _hp[..., 2] + 10) & (_hp[..., 1] > 110)
HAIRPAL = np.unique(_hp[_hm][:, :3], axis=0)
_hs = _hp[_hm][:, :3]; HAIRSORT = _hs[np.argsort(_hs.mean(1))]
o = {'label': '이동 (Grok 영상 걷기 · 비교용)', 'play': '반복'}
gfs = sorted([f for f in os.listdir(os.path.join(R, 'edit2', 'grokwalk')) if f.endswith('.png')], key=lambda x: int(x[1:-4]))
for mode in ('normal', 'glow'):
    names = []
    for f in gfs:
        im = Image.open(os.path.join(R, 'edit2', 'grokwalk', f)).convert('RGBA'); im = im.crop(im.getbbox())
        ga = np.array(im).astype(float); r_, g_, b_ = ga[..., 0], ga[..., 1], ga[..., 2]
        sk = (ga[..., 3] > 0) & (r_ > 170) & (r_ >= g_) & (g_ >= b_ - 5) & (r_ - b_ > 15) & (r_ - b_ < 90) & (g_ > 120)
        if sk.sum() > 50:   # 피부 밝기 통일(기본 스탠딩 피부색 기준)
            gain = np.array([252, 231, 215]) / ga[sk][:, :3].mean(0)
            ga[sk, :3] = np.clip(ga[sk, :3] * np.clip(gain, 0.85, 1.3), 0, 255); im = Image.fromarray(ga.astype(np.uint8))
        ga = np.array(im).astype(int); hm = (ga[..., 3] > 0) & (ga[..., 1] > ga[..., 0] + 2) & (ga[..., 1] > ga[..., 2] + 8) & (ga[..., 1] > 110)   # 머리(연두) → 다른 모션 머리 팔레트로
        if hm.any():
            lm = ga[hm][:, :3].mean(1); q = np.argsort(np.argsort(lm)) / max(1, len(lm) - 1)   # 밝기 순위를 다른 모션 머리 밝기 분포에 맞춤
            ga[hm, :3] = HAIRSORT[np.clip((q * (len(HAIRSORT) - 1)).round().astype(int), 0, len(HAIRSORT) - 1)]; im = Image.fromarray(ga.astype(np.uint8))
        if mode == 'glow': im = Image.fromarray(glowmap.to_glow(np.array(im)))
        cv = Image.new('RGBA', (306, 281), (0, 0, 0, 0)); cv.alpha_composite(im, ((306 - im.width) // 2, 281 - 15 - im.height))
        nm = f'{mode}_walkgrok_{f}'; cv.save(os.path.join(FR, nm)); names.append(nm)
    o[mode] = names; o['ms_' + mode] = [83] * len(names)
o['label'] = '이동 (Grok 영상 걷기)'
out['walk_grok'] = o
import fx_shock; fx_shock.apply(out, FR); fx_shock.twice(out)   # roar 쇼크웨이브·두 번
for o in out.values(): o['ms'] = o['ms_normal']
out['headbutt']['label'] = '알림 밀어서 지움 (박치기 → 멍)'
_gsrc = os.path.join(R, 'edit2', 'hand4b', 'frames')
if os.path.exists(os.path.join(_gsrc, 'getup_1.png')):   # 멍한 뒤 다시 일어나기(새 방식에만 있음)
    o = {'label': '다시 일어나기 (headbutt 뒤)', 'play': '1회'}
    seqg = [(0, 300), ('m', 200), (1, 220), (2, 260), (3, 360), (4, 300)]
    for mode in ('normal', 'glow'):
        names = []
        for k, t in seqg:
            im = Image.open(os.path.join(_gsrc, f'getup_{k}.png')).convert('RGBA')
            _s0 = np.array(Image.open(os.path.join(_gsrc, 'headbutt_12.png')).convert('RGBA'))[..., 3] > 0
            _w0 = np.array(Image.open(os.path.join(FR, [n for n in out['headbutt']['normal'] if n.endswith('headbutt_12.png')][0])).convert('RGBA'))[..., 3] > 0
            _oy = np.where(_w0)[0].max() - np.where(_s0)[0].max(); _ox = np.where(_w0)[1].min() - np.where(_s0)[1].min()
            cv = Image.new('RGBA', (306, 281), (0, 0, 0, 0)); cv.alpha_composite(im, (int(_ox), int(_oy))); im = cv   # headbutt와 같은 캔버스·위치
            if mode == 'glow': im = Image.fromarray(glowmap.to_glow(np.array(im)))
            nm = f'{mode}_getup_{k}.png'; im.save(os.path.join(FR, nm)); names.append(nm)
        o[mode] = names; o['ms_' + mode] = [t for _, t in seqg]
    o['ms'] = o['ms_normal']; out['getup'] = o
    for mode in ('normal', 'glow'):   # headbutt 멍 → 다시 일어나기로 이어짐(사용자 요청)
        out['headbutt'][mode] = out['headbutt'][mode] + o[mode][1:]
        out['headbutt']['ms_' + mode] = out['headbutt']['ms_' + mode] + o['ms_' + mode][1:]
    out['headbutt']['label'] = '알림 밀어서 지움 (박치기 → 멍 → 다시 일어나기)'
    if 'walk_grok' in out:   # 달리는 부분(5~9)을 walk_grok 다리 교대로 교체(사용자 요청)
        for mode in ('normal', 'glow'):
            n = out['headbutt'][mode]; t = out['headbutt']['ms_' + mode]; w = out['walk_grok'][mode]
            out['headbutt'][mode] = n[:4] + w + w + n[10:]
            out['headbutt']['ms_' + mode] = t[:4] + [55] * (2 * len(w)) + t[10:]
        out['headbutt']['runFrom'] = 4; out['headbutt']['runTo'] = 4 + len(out['walk_grok']['normal']) - 1; out['headbutt']['hitFrom'] = 4 + 2 * len(out['walk_grok']['normal'])
if os.path.exists(os.path.join(_gsrc, 'hatch_egg.png')):   # 앱 시작: 알 → 톡톡(최대 3번) 흔들림·금 → 팔다리 쏙 → 팡 → 스탠딩
    import math
    o = {'label': '앱 시작 (알 부화 · 톡톡 3번)', 'play': '1회'}
    def rot(im, deg):
        a = np.array(im)[..., 3] > 0; ys, xs = np.where(a); cx, by = (xs.min() + xs.max()) / 2, ys.max()
        return im.rotate(deg, resample=Image.NEAREST, center=(cx, by))
    def wob(k, amp): return [(k, d, 70) for d in (amp, -amp, amp * 0.6, -amp * 0.6, 0)]
    seqh = [('egg', 0, 900)] + wob('egg', 8) + [('egg', 0, 600)] + wob('crack1', 10) + [('crack1', 0, 600)] + wob('crack2', 13) + [('crack2', 0, 250), ('out1', 0, 650), ('burst', 0, 380), ('idle', 0, 600)]
    for mode in ('normal', 'glow'):
        names = []
        for i, (k, d, t) in enumerate(seqh):
            p_ = os.path.join(_gsrc, 'getup_4.png' if k == 'idle' else f'hatch_{k}.png')
            im = Image.open(p_).convert('RGBA')
            if d: im = rot(im, d)
            _shp = os.path.join(_gsrc, 'hatch_shadow.png')
            if k in ('egg', 'crack1', 'crack2') and os.path.exists(_shp):   # 그림자는 고정, 알만 흔들림
                bgs = Image.open(_shp).convert('RGBA'); bgs.alpha_composite(im); im = bgs
            cv = Image.new('RGBA', (306, 281), (0, 0, 0, 0)); cv.alpha_composite(im, (int(_ox), int(_oy))); im = cv
            if mode == 'glow': im = Image.fromarray(glowmap.to_glow(np.array(im)))
            nm = f'{mode}_hatch_{i}.png'; im.save(os.path.join(FR, nm)); names.append(nm)
        o[mode] = names; o['ms_' + mode] = [t for _, _, t in seqh]
    o['ms'] = o['ms_normal']; o['taps'] = [1, 7, 13]   # 톡 누르면 재생할 구간 시작(1·2·3번째 터치)
    out = {'hatch': o, **out}
json.dump(out, open(os.path.join(WEB, 'motions.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
G = os.path.join(R, 'gif'); shutil.rmtree(G, ignore_errors=True); os.makedirs(G, exist_ok=True)
for m, v in out.items():
    for mode, bg in [('normal', (250, 246, 240, 255)), ('glow', (22, 24, 30, 255))]:
        fr = []
        for nm in v.get(mode, []):
            im = Image.open(os.path.join(FR, nm)); b = Image.new('RGBA', im.size, bg); b.alpha_composite(im)
            fr.append(b.convert('RGB').resize((im.width * 2, im.height * 2), Image.NEAREST))
        if fr: fr[0].save(os.path.join(G, f'{mode}_{m}.gif'), save_all=True, append_images=fr[1:], duration=v['ms_' + mode], loop=0)
print('ok', {m: (len(v.get('normal', [])), len(v.get('glow', []))) for m, v in out.items()})
