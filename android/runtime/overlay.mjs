// 안드로이드 오버레이 연결부: 화면 전체 투명 무대 + 네이티브 터치 창(두두 그림 위에만) ↔ 공용 동작 로직
import {createDudu} from './dudu-runtime.mjs';
const host = window.AndroidPet, q = new URLSearchParams(location.search);
const defaultScale = 0.4;
const num = (v, d) => { const n = parseFloat(v); return Number.isFinite(n) && n > 0 ? n : d; };
const dudu = createDudu({
  stage: document.getElementById('stage'), canvas: document.getElementById('cv'), base: '',
  scale: num(q.get('scale'), defaultScale),
  onMenu: () => host?.menu(),
  onHatched: () => host?.hatched(),
});
await dudu.load();
if (q.get('hatched') === '1') dudu.skipHatch();
dudu.setMode(q.get('mode') === 'glow' ? 'glow' : 'normal');
addEventListener('resize', () => dudu.fit());
// 그림 범위를 네이티브에 알려 터치 창을 그 위에만 둔다(바뀔 때만)
let last = '';
function report() {
  const b = dudu.bounds(), s = [b.l, b.t, b.r, b.b].map(v => Math.round(v)).join(',') + ',' + innerWidth + ',' + innerHeight;
  if (s !== last) { last = s; host?.bounds(s); }
  requestAnimationFrame(report);
}
requestAnimationFrame(report);
window.Dudu = {
  // 네이티브 터치(화면 픽셀) → CSS 좌표
  pointer(type, x, y, w, h) { dudu.pointer(type, x * innerWidth / w, y * innerHeight / h); },
  setScale(s) { dudu.setScale(num(s, defaultScale)); dudu.fit(); last = ''; },
  setMode(m) { dudu.setMode(m === 'glow' ? 'glow' : 'normal'); },
  restart() { dudu.restart(); },
  fit() { dudu.fit(); last = ''; },
};
host?.ready();
