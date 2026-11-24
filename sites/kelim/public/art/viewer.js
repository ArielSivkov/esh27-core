(() => {
  const CDN = 'https://cdn.jsdelivr.net/gh/ArielSivkov/esh27-core@56cff779d4a7f3fdede9d26772f3e6903c7db12b/sites/kelim/art-tiles/';
  const W = 7680, H = 4320;
  const viewer = document.getElementById('viewer'), layer = document.getElementById('layer'), base = document.getElementById('base');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let s = 0.1, tx = 0, ty = 0, sMin = 0.05;
  const sMax = 1.6;

  // full-resolution tiles: 4 columns x 3 rows of 1920x1440, cut with a 2px overlap
  const TW = 1920, TH = 1440, O = 2, tiles = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++) {
    const x0 = Math.max(0, c * TW - O), y0 = Math.max(0, r * TH - O);
    const x1 = Math.min(W, (c + 1) * TW + O), y1 = Math.min(H, (r + 1) * TH + O);
    tiles.push({ r, c, x0, y0, x1, y1, el: null });
  }

  function view() { const b = viewer.getBoundingClientRect(); return { w: b.width, h: b.height }; }
  function clamp() {
    const { w, h } = view();
    s = Math.min(sMax, Math.max(sMin, s));
    const iw = W * s, ih = H * s;
    tx = iw <= w ? (w - iw) / 2 : Math.min(0, Math.max(w - iw, tx));
    ty = ih <= h ? (h - ih) / 2 : Math.min(0, Math.max(h - ih, ty));
  }
  let tileTimer = 0;
  function apply() {
    clamp();
    layer.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
    clearTimeout(tileTimer); tileTimer = setTimeout(loadTiles, 120);
  }
  function loadTiles() {
    const dpr = window.devicePixelRatio || 1;
    if (s * dpr < 0.55) return;            // the 3840 base is sharp enough below this
    const { w, h } = view();
    const vx0 = -tx / s, vy0 = -ty / s, vx1 = (w - tx) / s, vy1 = (h - ty) / s;
    for (const t of tiles) {
      if (t.el || t.x1 < vx0 || t.x0 > vx1 || t.y1 < vy0 || t.y0 > vy1) continue;
      const im = new Image();
      im.alt = ''; im.decoding = 'async';
      Object.assign(im.style, { left: t.x0 + 'px', top: t.y0 + 'px', width: (t.x1 - t.x0) + 'px', height: (t.y1 - t.y0) + 'px', opacity: 0, transition: reduce ? 'none' : 'opacity .35s' });
      im.onload = () => { im.style.opacity = 1; };
      im.src = CDN + `t/${t.r}-${t.c}.jpg`;
      t.el = im; layer.appendChild(im);
    }
  }
  function fitScale(rw, rh, pad = 0.94) { const { w, h } = view(); return Math.min(w / rw, h / rh) * pad; }
  function zoomAt(px, py, ns) { const k = ns / s; tx = px - (px - tx) * k; ty = py - (py - ty) * k; s = ns; apply(); }

  let anim = 0;
  function goTo(x, y, rw, rh) {
    const { w, h } = view();
    const ts = Math.min(sMax, Math.max(sMin, fitScale(rw, rh, x === 0 && rw === W ? 1 : 0.94)));
    const ttx = w / 2 - (x + rw / 2) * ts, tty = h / 2 - (y + rh / 2) * ts;
    cancelAnimationFrame(anim);
    if (reduce) { s = ts; tx = ttx; ty = tty; apply(); return; }
    const s0 = s, x0 = tx, y0 = ty, t0 = performance.now(), D = 650;
    const step = now => {
      const u = Math.min(1, (now - t0) / D), e = u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
      // interpolate scale geometrically so the zoom feels even
      s = s0 * Math.pow(ts / s0, e); tx = x0 + (ttx - x0) * e; ty = y0 + (tty - y0) * e; apply();
      if (u < 1) anim = requestAnimationFrame(step);
    };
    anim = requestAnimationFrame(step);
  }

  function reset() { sMin = fitScale(W, H, 1) * 0.98; goTo(0, 0, W, H); }

  // pointer: drag with one finger, pinch with two
  const pts = new Map(); let last = null, pinch = null, lastTap = 0;
  viewer.addEventListener('pointerdown', e => {
    viewer.setPointerCapture(e.pointerId); pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    cancelAnimationFrame(anim); viewer.classList.add('dragging'); markStop(null);
    if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), s }; }
    last = { x: e.clientX, y: e.clientY };
    const now = performance.now();
    if (e.pointerType !== 'mouse' && pts.size === 1 && now - lastTap < 300) { doubleTap(e.clientX, e.clientY); lastTap = 0; } else lastTap = now;
  });
  viewer.addEventListener('pointermove', e => {
    if (!pts.has(e.pointerId)) return;
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pts.size === 2 && pinch) {
      const [a, b] = [...pts.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      if (last) { tx += mx - last.x; ty += my - last.y; }
      zoomAt(mx, my, pinch.s * d / pinch.d); last = { x: mx, y: my };
    } else if (pts.size === 1 && last) {
      tx += e.clientX - last.x; ty += e.clientY - last.y; last = { x: e.clientX, y: e.clientY }; apply();
    }
  });
  const up = e => {
    pts.delete(e.pointerId);
    if (pts.size < 2) pinch = null;
    if (pts.size === 1) { const [p] = pts.values(); last = { x: p.x, y: p.y }; }
    if (!pts.size) { last = null; viewer.classList.remove('dragging'); }
  };
  viewer.addEventListener('pointerup', up); viewer.addEventListener('pointercancel', up);
  viewer.addEventListener('wheel', e => { e.preventDefault(); markStop(null); zoomAt(e.clientX, e.clientY, s * Math.exp(-e.deltaY * 0.0018)); }, { passive: false });
  viewer.addEventListener('dblclick', e => doubleTap(e.clientX, e.clientY));
  function doubleTap(x, y) {
    const fit = fitScale(W, H, 1);
    if (s > fit * 2.2) { reset(); return; }
    const ns = Math.min(sMax, s * 3.2), { w, h } = view();
    const cx = (x - tx) / s, cy = (y - ty) / s, rw = w / ns, rh = h / ns;
    goTo(cx - rw / 2, cy - rh / 2, rw / 0.94, rh / 0.94);
  }

  const stopBtns = [...document.querySelectorAll('#stops button')];
  function markStop(btn) { stopBtns.forEach(b => b.setAttribute('aria-pressed', b === btn ? 'true' : 'false')); }
  stopBtns.forEach(b => b.addEventListener('click', () => {
    const [x, y, rw, rh] = b.dataset.r.split(',').map(Number); markStop(b);
    if (b.id === 'stop-all') reset(); else goTo(x, y, rw, rh);
  }));

  window.addEventListener('resize', () => { sMin = fitScale(W, H, 1) * 0.98; apply(); });
  function start() {
    sMin = fitScale(W, H, 1) * 0.98; s = fitScale(W, H, 1); apply();
    document.getElementById('load').classList.add('gone');
  }
  base.addEventListener('load', start); base.addEventListener('error', start); base.src = CDN + 'base.jpg';
})();
