// כֵּלִים · hero art. Deterministic, no text, numbers only (public layer).
// The night, one line of light with three unlabeled sparks, and seven vessels whose light = share completed.
(() => {
  const VESSELS = [ // rtl order; n = sessions, w = waiting (embers), lit = share completed — snapshot 23.11.2026 22:30
    { n: 43, w: 16, lit: .465 }, { n: 20, w: 6, lit: .5 }, { n: 21, w: 4, lit: .667 }, { n: 25, w: 11, lit: .52 },
    { n: 37, w: 6, lit: .568 }, { n: 27, w: 7, lit: .63 }, { n: 28, w: 4, lit: .321 }];
  const cv = document.getElementById('art'); if (!cv) return;
  const ctx = cv.getContext('2d');
  function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  function draw() {
    const dpr = Math.min(2, window.devicePixelRatio || 1), W = cv.clientWidth, H = cv.clientHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const hz = H * 0.62, r = rng(5787);
    // stars (none near the line of light)
    const kx = W >= 1000 ? W * 0.93 : W * (W < 640 ? 0.86 : 0.82);
    for (let i = 0; i < Math.round(W * H / 2600); i++) {
      const x = r() * W, y = r() * hz * 0.98, m = r();
      if (Math.abs(x - kx) < 40) continue;
      ctx.fillStyle = `rgba(${m > .8 ? '255,236,210' : '200,215,255'},${0.12 + 0.5 * m * m})`;
      ctx.beginPath(); ctx.arc(x, y, 0.4 + 1.1 * m * m, 0, 6.283); ctx.fill();
    }
    // engraved sea hatching
    ctx.strokeStyle = 'rgba(142,155,194,0.07)'; ctx.lineWidth = 1;
    for (let y = hz + 4, s = 3; y < H; y += s, s += 0.35) {
      for (let x = r() * 60; x < W; x += 30 + r() * 90) { ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 8 + r() * 40, y); ctx.stroke(); }
    }
    // the line of light
    const g = ctx.createLinearGradient(0, 0, 0, hz);
    g.addColorStop(0, 'rgba(255,246,224,0.95)'); g.addColorStop(1, 'rgba(255,226,168,0.95)');
    for (const [w, a] of [[46, .05], [16, .12], [5, .35]]) {
      ctx.fillStyle = `rgba(255,200,107,${a})`; ctx.fillRect(kx - w / 2, 0, w, hz);
    }
    ctx.fillStyle = g; ctx.fillRect(kx - 1.25, 0, 2.5, hz);
    // glade on the water
    for (let i = 0; i < 40; i++) {
      const d = r(), y = hz + 3 + d * d * (H - hz) * 0.35, len = 4 + r() * 26 * (1 - d * .5);
      ctx.fillStyle = `rgba(255,214,150,${0.35 * (1 - d)})`; ctx.fillRect(kx - len / 2 + (r() - .5) * 10 * d, y, len, 1);
    }
    // three sparks, graded
    [[.25, 1, 15], [.45, .86, 13], [.65, .74, 12]].forEach(([fy, k, rad]) => {
      const y = hz * fy, gr = ctx.createRadialGradient(kx, y, 0, kx, y, rad * 6);
      gr.addColorStop(0, `rgba(255,253,246,${k})`); gr.addColorStop(.18, `rgba(255,200,107,${.55 * k})`); gr.addColorStop(1, 'rgba(255,200,107,0)');
      ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(kx, y, rad * 6, 0, 6.283); ctx.fill();
      ctx.fillStyle = '#FFFDF6'; ctx.beginPath(); ctx.arc(kx, y, rad * .45, 0, 6.283); ctx.fill();
    });
    // seven vessels in their own band at the bottom; the hero text sits above it
    const band = Math.round(Math.max(72, Math.min(130, H * 0.15)));
    cv.parentElement.style.setProperty('--band', band + 'px');
    const left = W * 0.04, right = W * 0.78, slot = (right - left) / 7, base = H - 10;
    const hmax = band - 30, wmax = Math.min(slot * 0.8, hmax / 1.45);
    ctx.strokeStyle = 'rgba(201,166,107,0.3)'; ctx.beginPath(); ctx.moveTo(left, base + 1); ctx.lineTo(right, base + 1); ctx.stroke();
    VESSELS.forEach((v, i) => {
      const cx = right - slot * (i + .5), w = wmax * Math.sqrt(v.n / 43), h = w * 1.45, top = base - h;
      const P = [[-.36, 0], [-.5, .18], [-.5, .7], [-.3, 1], [.3, 1], [.5, .7], [.5, .18], [.36, 0]].map(([u, t]) => [cx + u * w, top + t * h]);
      const path = () => { ctx.beginPath(); P.forEach(([x, y], j) => j ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); };
      ctx.save(); path(); ctx.clip();
      const ly = base - h * v.lit, lg = ctx.createLinearGradient(0, ly, 0, base);
      lg.addColorStop(0, 'rgba(242,196,109,0.42)'); lg.addColorStop(1, 'rgba(154,107,42,0.16)');
      ctx.fillStyle = lg; ctx.fillRect(cx - w, ly, 2 * w, base - ly);
      ctx.fillStyle = 'rgba(255,230,170,0.7)'; ctx.fillRect(cx - w, ly, 2 * w, 1.5);
      ctx.restore();
      path(); ctx.strokeStyle = 'rgba(201,166,107,0.55)'; ctx.lineWidth = 1; ctx.stroke();
      const er = rng(1000 + i);
      for (let e = 0; e < v.w; e++) { // embers: sessions waiting
        const a = er() * 2 - 1, y = top - 5 - er() * 22 * (1 - a * a * .6);
        ctx.fillStyle = 'rgba(224,112,58,0.75)'; ctx.beginPath(); ctx.arc(cx + a * w * .42, y, 1.5, 0, 6.283); ctx.fill();
      }
    });
  }
  let t = 0; const re = () => { clearTimeout(t); t = setTimeout(draw, 120); };
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw); else draw();
  draw(); window.addEventListener('resize', re);
})();
