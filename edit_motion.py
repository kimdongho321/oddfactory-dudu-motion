"""원본 도트를 기준 이미지로 넣고 프레임마다 '이 그림에서 이 부분만 바꿔라' 편집 → 얼굴형·색·도트 유지.
1) python edit_motion.py prompts <mode> <motion...>   : 프레임별 프롬프트 파일 작성
2) (run_edits.sh 로 codex 생성)
3) python edit_motion.py extract <mode> <motion...>   : 원본 캔버스 크기로 맞춘 뒤 2배 도트로 축소·팔레트 고정"""
import os, sys, json
import numpy as np
from PIL import Image
from scipy import ndimage as nd

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)
from extract_own import blockmode, palettize, make_pal, despeckle  # noqa: E402
import skinfix  # noqa: E402

BASE_TXT = ("Edit the attached pixel-art sprite. Keep it the SAME drawing: identical pixel size and pixel grid, identical outline, "
            "identical colors, identical face shape, eyes, hood, stickers, costume and proportions, identical scale; she may move her whole body, change pose, sit, lie down or jump as the change says (a real full-body movement, not only the arms), "
            "but the character design must stay identical. Flat pure magenta #FF00FF background. "
            "FACE SHAPE LOCK: her face keeps exactly the attached face outline and size in every case: same narrow soft chin, same cheek outline and jaw width, same distance between the eyes, same head size; never wider, rounder, flatter or puffier, even when she crouches or leans. HANDS: her hands are plain small human hands with little fingers, NOT animal paws, no paw pads, no claws. LEGS: exactly two legs, short and chubby exactly like the attached sprite, never thin or long, never an extra leg. SKIN LOCK: her face skin stays exactly the pale peach color of the attached sprite, never flushed, reddened or pinker overall; the blush is ONLY the same small soft pink patches as the attached sprite. CHEEK LOCK: the round pink blush patches with tiny freckle dots on BOTH cheeks are always clearly visible exactly like the attached sprite, in every pose and expression. "
            "Pixel art only, no smoothing, no new details, no text, no motion lines, no shake marks, no sparkles or effects floating around her. Change: ")
GLOW_TXT = " Keep the attached dark glow-in-the-dark night palette: only the mint glow parts shine."

EDIR = 'edit2'
SRCDIR = {'normal': 'hand4b', 'glow': 'glow2'}   # 눈꼬리 포인트 추가본 / 새 야광
MOTIONS = json.load(open(os.path.join(R, 'edit_motions.json'), encoding='utf-8'))


def prompts(mode, names):
    d = os.path.join(R, EDIR, mode); os.makedirs(d, exist_ok=True)
    jobs = []
    for m in names:
        for i, fr in enumerate(MOTIONS[m]['frames']):
            ch = fr['p']
            if ch is None: continue          # 원본 그대로 쓰는 프레임
            p = os.path.join(d, f'{m}_{i}.txt')
            open(p, 'w', encoding='utf-8').write(BASE_TXT + ch + (GLOW_TXT if mode == 'glow' else ''))
            refp = os.path.join(d, f'{m}_{i}.ref')
            if fr.get('ref'): open(refp, 'w', encoding='utf-8').write(fr['ref'])
            elif os.path.exists(refp): os.remove(refp)
            jobs.append(f'{mode}/{m}_{i}')
    print('\n'.join(jobs))


def base_canvas(mode):
    im = Image.open(os.path.join(R, 'ref', f'{mode}-clean.png')).convert('RGBA')
    bg = Image.new('RGBA', (im.width + 80, im.height + 80), (255, 0, 255, 255)); bg.alpha_composite(im, (40, 40))
    return bg.convert('RGB')


def cut(rgb):
    a = np.array(rgb).astype(int); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    key = (r > 150) & (b > 150) & (g < 110) & (np.abs(r - b) < 90)
    lab, _ = nd.label(key); edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge)) | ((r > 180) & (b > 160) & (g < 90))
    bg = nd.binary_dilation(bg, iterations=1) & ((g < 140) & (r > 120) & (b > 120) | bg)
    return np.dstack([a, (~bg) * 255]).astype(np.uint8)


def extract(mode, names, dens=2):
    """야광도 일반 프레임을 색만 바꾼 것이라 위치·크기 기준은 항상 일반 원본 캔버스"""
    base = base_canvas('normal'); BW, BH = base.size
    ref_h = np.array(Image.open(os.path.join(R, 'ref', 'normal-clean.png'))).shape[0]
    s = dens * 96 / ref_h
    if mode == 'normal': PAL = make_pal(cut(base), 56)
    else:   # 새 야광(피부 밝게 유지): 야광 프레임 여러 장에서 팔레트 추출
        import glob
        fs = sorted(glob.glob(os.path.join(R, EDIR, 'glow2', '*_[0-9].png')))[::6][:12]
        big = np.concatenate([cut(Image.open(f).convert('RGB').resize((BW, BH)))[::3, ::3].reshape(-1, 4) for f in fs])
        PAL = make_pal(big[None], 56)
    out_dir = os.path.join(R, EDIR, SRCDIR.get(mode, mode), 'frames'); os.makedirs(out_dir, exist_ok=True)
    GREF = (40, 60)
    if mode == 'glow':   # 야광 기준 피부 색차: glow2 idle_0 다리 피부 최빈색
        ia = np.array(Image.open(os.path.join(R, EDIR, 'glow2', 'idle_0.png')).convert('RGB')).astype(int)
        h = ia.shape[0]; low = ia[int(h * .7):int(h * .9)].reshape(-1, 3)
        sk = low[(low[:, 0] > 150) & (low[:, 0] >= low[:, 1]) & (low[:, 0] - low[:, 2] < 90) & (low[:, 0] - low[:, 2] > 10)]
        if len(sk): m_ = np.median(sk, 0); GREF = (int(m_[0] - m_[1]), int(m_[0] - m_[2]))
        print('glow skin ref diff', GREF)
    TGT = skinfix.stats(despeckle(palettize(blockmode(cut(base), s, round(BW * s), round(BH * s)), PAL)))   # 기본 스탠딩 피부·홍조 비율
    for m in names:
        n = len(MOTIONS[m]['frames'])
        keys = [(str(i), MOTIONS[m]['frames'][i]) for i in range(n)] + [(f'x{i}', {'p': 'ib'}) for i in range(n)] + ([('x15s', {'p': 'ib'})] if m == 'headbutt' else []) + ([(f'L{v}', {'p': 'ib'}) for v in ('base', 'suck', 'half', 'closed')] if m == 'blank' else []) + ([(f'E{v}', {'p': 'ib'}) for v in ('base', 'chew1', 'chew2', 'blink')] if m == 'idle' else [])
        for i, fr in keys:
            p = os.path.join(R, EDIR, SRCDIR.get(mode, mode), f'{m}_{i}.png')
            if mode == 'normal' and fr['p'] is None: src = base
            elif not os.path.exists(p): continue
            else: src = Image.open(p).convert('RGB').resize((BW, BH), Image.LANCZOS)
            rgba = cut(src)
            nw, nh = round(BW * s), round(BH * s)
            small = despeckle(palettize(blockmode(rgba, s, nw, nh), PAL))
            if mode == 'normal':
                small = skinfix.fix(small, TGT)
                npth = os.path.join(R, EDIR, 'normal', f'{m}_{i}.png')
                if os.path.exists(p) and os.path.exists(npth):   # 눈꼬리 빨간 포인트: 일반본과 달라진 빨강만 → 도트로
                    A = np.array(src).astype(int); Bn = np.array(Image.open(npth).convert('RGB').resize((BW, BH), Image.LANCZOS)).astype(int)
                    red = (A[..., 0] > 190) & (A[..., 1] < 110) & (A[..., 2] < 110) & (A[..., 0] - A[..., 1] > 100) & (np.abs(A - Bn).sum(-1) > 90)
                    red = nd.binary_opening(red)
                    ys_, xs_ = np.where(red)
                    for yy, xx in set(zip((ys_ * s).astype(int), (xs_ * s).astype(int))):
                        if 0 <= yy < nh and 0 <= xx < nw and small[yy, xx, 3] > 0: small[yy, xx, :3] = (222, 66, 58)
            else: small = skinfix.fix_glow_legs(small, *GREF)
            c = small.copy(); al = c[..., 3] > 0; r_, g_, b_ = (c[..., j].astype(int) for j in range(3))
            edge = al & nd.binary_dilation(~al, iterations=3); mag = edge & (r_ - g_ > 50) & (b_ - g_ > 45) & (np.abs(r_ - b_) < 100); c[mag, 3] = 0
            Image.fromarray(c).save(os.path.join(out_dir, f'{m}_{i}.png'))
        print(m)


if __name__ == '__main__':
    cmd, mode, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    (prompts if cmd == 'prompts' else extract)(mode, names)
