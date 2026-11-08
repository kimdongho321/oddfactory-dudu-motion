// 안드로이드 오버레이 연결부: 월드 좌표로 그리는 무대 + 두두 주변의 네이티브 창 ↔ 공용 동작 로직
import {createDudu} from './dudu-runtime.mjs';
const host = window.AndroidPet, q = new URLSearchParams(location.search);
const defaultScale = 0.39;
const num = (v, d) => { const n = parseFloat(v); return Number.isFinite(n) && n > 0 ? n : d; };
let last = "";
const dudu = createDudu({
  stage: document.getElementById('stage'), canvas: document.getElementById('cv'), base: '',
  scale: num(q.get('scale'), defaultScale),
  onMenu: () => host?.menu(),
  onPaint({l, t, r, b}) {
    const bounds = [Math.floor(l), Math.floor(t), Math.ceil(r), Math.ceil(b), innerWidth, innerHeight].join(',');
    if (bounds === last) return;
    last = bounds;
    host?.bounds(bounds);
  },
});
await dudu.load();
dudu.setMode(q.get('mode') === 'glow' ? 'glow' : 'normal');
addEventListener('resize', () => dudu.fit());
window.Dudu = {
  // 네이티브 터치(화면 픽셀) → CSS 좌표
  pointer(type, x, y, w, h) { dudu.pointer(type, x * innerWidth / w, y * innerHeight / h); },
  setScale(s) { dudu.setScale(num(s, defaultScale)); dudu.fit(); last = ''; },
  setMode(m) { dudu.setMode(m === 'glow' ? 'glow' : 'normal'); },
  restart() { dudu.restart(); last = ''; },
  fit() { dudu.fit(); last = ''; },
};
host?.ready();
