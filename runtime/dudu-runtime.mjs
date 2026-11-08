// 두두 동작 로직(폰 시뮬레이터·안드로이드 앱 공용)
// - 알: 처음엔 떨어져 착지 → 톡 3번(흔들·흔들금·쩌적) → 부화 → idle
// - 자동: idle·blank·sleep·roar 사이마다 walk 1.5초(대각선 랜덤 방향, 화면 전체 돌아다님)
// - walk 중 캐릭터 실제 그림이 화면 끝(벽)에 완전히 닿으면 headbutt(벽 박치기 → 멍 → 일어나기)
// - 톡 1번: pat 1.5초 / 꾹 누른 채 끌기: panic 따라다니기 → 놓으면 넘어짐 / 더블톡: 메뉴(onMenu)
export function createDudu({stage, canvas, base = '', scale = 0.9, onLog = () => {}, onMenu = () => {}}) {
  const ctx = canvas.getContext('2d');
  let M = null, mode = 'normal', sc = scale;
  const cache = {}, boxes = {};
  const img = n => cache[n] || (cache[n] = new Promise(r => { const i = new Image(); i.onload = () => { boxes[n] = bbox(i); r(i); }; i.src = base + 'frames/' + n; }));
  function bbox(im) {   // 그림이 실제로 있는 범위(투명 제외)
    const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0);
    const d = x.getImageData(0, 0, im.width, im.height).data; let l = im.width, t = im.height, r = 0, b = 0;
    for (let y = 0; y < im.height; y++) for (let xx = 0; xx < im.width; xx++) if (d[(y * im.width + xx) * 4 + 3] > 20) { if (xx < l) l = xx; if (xx > r) r = xx; if (y < t) t = y; if (y > b) b = y; }
    return {l, t, r, b};
  }
  const W = () => stage.clientWidth, H = () => stage.clientHeight, CW = () => 306 * sc, CH = () => 281 * sc;
  let x = 0, y = 0, face = 1, cur = null, state = 'egg', taps = 0, schedI = 0, nextAt = 0, walk = null;
  const SCHED = ['idle', 'blank', 'idle', 'sleep', 'idle', 'roar'];
  const list = m => M[m][mode] || M[m].normal, msOf = (m, i) => (M[m]['ms_' + mode] || M[m].ms)[i] || 100;
  function play(m, o = {}) {
    cur = {m, i: o.from ?? 0, to: o.to ?? list(m).length - 1, loopFrom: o.loopFrom, last: performance.now(), until: o.dur ? performance.now() + o.dur : null, onEnd: o.onEnd};
    onLog(m + (o.note ? ' · ' + o.note : ''));
  }
  const end = () => { const f = cur.onEnd; cur.onEnd = null; cur.until = null; if (f) f(); };
  function idle() { state = 'idle'; play('idle', {loopFrom: 0}); nextAt = performance.now() + 1500; }
  function startWalk(then) {
    state = 'walk'; const a = Math.random() * Math.PI * 2, sp = 70 + Math.random() * 40;   // px/초, 대각선 포함 모든 방향
    walk = {vx: Math.cos(a) * sp, vy: Math.sin(a) * sp * 0.8, t: performance.now(), then};
    face = walk.vx >= 0 ? 1 : -1;
    play('walk_grok', {loopFrom: 0, dur: 1500, note: '1.5초 이동', onEnd: () => { walk = null; then(); }});
  }
  function next() {   // 모션 사이마다 walk 1.5초
    const s = SCHED[schedI++ % SCHED.length];
    startWalk(() => {
      if (s === 'idle') return idle();
      state = 'motion'; const once = M[s].play === '1회';
      play(s, {loopFrom: once ? undefined : 0, dur: once ? null : 3000, onEnd: idle});
    });
  }
  function ground() { y = H() - CH() - 30; }
  function hatchStart() {
    x = (W() - CW()) / 2; ground(); face = 1; state = 'egg'; taps = 0; schedI = 0;
    const t0 = M.hatch.taps[0]; play('hatch', {from: 0, to: t0 - 1, loopFrom: t0 - 1, note: '알 — 톡 3번'});
  }
  // 입력
  let pressT = 0, pressTimer = null, dragging = false, lastTap = 0, tapTimer = null;
  const hit = e => { const r = canvas.getBoundingClientRect(); return e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom; };
  stage.addEventListener('pointerdown', e => {
    if (!hit(e) || !M) return; stage.setPointerCapture?.(e.pointerId); pressT = performance.now();
    if (state === 'egg') {
      const tp = M.hatch.taps; taps++;
      if (taps < 3) play('hatch', {from: tp[taps - 1], to: tp[taps] - 1, loopFrom: tp[taps] - 1, note: '톡 ' + taps});
      else { state = 'hatching'; play('hatch', {from: tp[2], note: '톡 3 → 부화', onEnd: idle}); }
      return;
    }
    if (state === 'hatching') return;
    pressTimer = setTimeout(() => { dragging = true; state = 'drag'; walk = null; clearTimeout(tapTimer); play('panic', {from: 2, to: 17, loopFrom: 2, note: '꾹 → 허둥지둥'}); }, 380);
  });
  stage.addEventListener('pointermove', e => {
    if (!dragging) return; const r = stage.getBoundingClientRect();
    x = Math.max(-CW() * .2, Math.min(W() - CW() * .8, e.clientX - r.left - CW() / 2)); y = Math.max(-CH() * .2, Math.min(H() - CH(), e.clientY - r.top - CH() * .45));
  });
  stage.addEventListener('pointerup', e => {
    clearTimeout(pressTimer);
    if (dragging) { dragging = false; state = 'motion'; play('panic', {from: 18, note: '놓음 → 넘어짐', onEnd: idle}); return; }
    if (!M || state === 'egg' || state === 'hatching' || !hit(e) || performance.now() - pressT > 380) return;
    const now = performance.now();
    if (now - lastTap < 320) { clearTimeout(tapTimer); lastTap = 0; onMenu(); return; }   // 더블톡 → 메뉴
    lastTap = now;
    tapTimer = setTimeout(() => { state = 'motion'; walk = null; play('pat', {loopFrom: 5, dur: 1500, note: '톡 → 간지럼', onEnd: idle}); }, 330);
  });
  // 루프
  async function tick(t) {
    if (M && cur) {
      if (state === 'walk' && walk) {
        const dt = (t - walk.t) / 1000; walk.t = t; x += walk.vx * dt; y += walk.vy * dt;
        const bx = boxes[list(cur.m)[cur.i]];
        if (bx) {   // 실제 그림 가장자리가 화면 끝에 닿았나
          const L = x + (face > 0 ? bx.l : 306 - bx.r) * sc, R = x + (face > 0 ? bx.r : 306 - bx.l) * sc, T = y + bx.t * sc, B = y + bx.b * sc;
          if (B > H()) y -= B - H(); if (T < 0) { y -= T; walk.vy = Math.abs(walk.vy); }   // 위·아래는 튕겨서 계속 걷기
          if (B >= H()) walk.vy = -Math.abs(walk.vy);
          if (L <= 0 || R >= W()) {   // 좌우 벽에 완전히 닿음 → 박치기
            x += L <= 0 ? -L : W() - R; face = L <= 0 ? -1 : 1; walk = null; state = 'motion';
            play('headbutt', {from: M.headbutt.hitFrom ?? 0, note: '벽 꽝 → headbutt', onEnd: idle});
          }
        }
      }
      if (cur.until && t >= cur.until) end();
      else if (t - cur.last >= msOf(cur.m, cur.i)) {
        cur.last = t; cur.i++;
        if (cur.i > cur.to) { if (cur.loopFrom !== undefined && (cur.until || cur.onEnd === undefined || cur.onEnd === null)) cur.i = cur.loopFrom; else { cur.i = cur.to; end(); } }
      }
      const n = list(cur.m)[Math.min(cur.i, list(cur.m).length - 1)], im = await img(n);
      ctx.clearRect(0, 0, 306, 281); ctx.imageSmoothingEnabled = false;
      ctx.save(); if (face < 0) { ctx.translate(306, 0); ctx.scale(-1, 1); } ctx.drawImage(im, 0, 0); ctx.restore();
      canvas.style.width = CW() + 'px'; canvas.style.height = CH() + 'px'; canvas.style.left = x + 'px'; canvas.style.top = y + 'px';
    }
    if (state === 'idle' && t >= nextAt) next();
    requestAnimationFrame(tick);
  }
  return {
    async load() { M = await (await fetch(base + 'motions.json', {cache: 'no-store'})).json(); Object.values(M).forEach(m => (m.normal || []).forEach(img)); hatchStart(); requestAnimationFrame(tick); },
    restart: () => hatchStart(),
    setMode(m) { mode = m; Object.values(M).forEach(v => (v[mode] || []).forEach(img)); },
    get mode() { return mode; },
    setScale(s) { sc = s; },
    skipHatch() { x = (W() - CW()) / 2; ground(); idle(); },
  };
}
