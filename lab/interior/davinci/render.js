const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const DIR = '/home/user/codesandbox-template-nuxt/twin/integration/world';
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.gz': 'application/gzip', '.wasm': 'application/wasm', '.glb': 'model/gltf-binary', '.png': 'image/png', '.webp': 'image/webp', '.ktx2': 'image/ktx2', '.jpg': 'image/jpeg', '.css': 'text/css', '.bin': 'application/octet-stream' };
const picks = JSON.parse(fs.readFileSync('/tmp/claude-0/city/davinci_picks.json'));
const W_ = 480, H_ = 720;
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await (await b.newContext({ viewport: { width: W_, height: H_ }, deviceScaleFactor: 1 })).newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.route('http://w.test/**', r => { const u = new URL(r.request().url()); const f = path.join(DIR, decodeURIComponent(u.pathname));
    if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) return r.fulfill({ status: 404, body: '' });
    r.fulfill({ body: fs.readFileSync(f), contentType: types[path.extname(f)] || 'application/octet-stream' }); });
  await p.route(/^https?:\/\/(?!w\.test)/, r => r.abort());
  await p.addInitScript(() => { const t = setInterval(() => { if (!window.YZW) return; clearInterval(t);
    YZW.register({ id: 'photo-cam', name: 'cam', dept: 'test', order: 99, init() {},
      modes: [{ id: 'photo', name: 'photo', icon: 'x', enter() {}, update(dt, wd) { const P = window.__pose; if (!P) return null; const c = wd.camera; c.position.set(P.x, P.y, P.z);
        c.lookAt(P.x + Math.sin(P.h) * Math.cos(P.p) * 10, P.y + Math.sin(P.p) * 10, P.z - Math.cos(P.h) * Math.cos(P.p) * 10); c.fov = P.fov; c.near = 0.2; c.updateProjectionMatrix();
        if (wd.sky) wd.sky.position.copy(c.position); return { x: P.x, y: P.y - 1.6, z: P.z, speed: 0 }; } }] }); }, 5); });
  await p.goto('http://w.test/index.html?auto&nointro&clean=1&t=12:00&agents=0&nat=0');
  await p.waitForFunction(() => window.YZW && YZW.world.stats.startMs, null, { timeout: 240000 });
  await p.waitForFunction(() => YZW.plugins().every(x => x.state !== 'loading' && x.state !== 'registered'), null, { timeout: 180000 }).catch(() => {});
  const meta = [];
  for (const k of picks) {
    const r = await p.evaluate(async (k) => {
      const W = window.W27, wd = YZW.world; const cam = W.toScene(k.camE, k.camN), tg = W.toScene(k.E, k.N);
      const it = wd.coords.toITM(cam.x, cam.z); YZW.placeAt(it.E, it.N, 0); YZW.setMode('photo');
      const g0 = () => Math.max(0, wd.data.H(cam.x, cam.z));
      const hd = Math.atan2(tg.x - cam.x, -(tg.z - cam.z)), d = Math.hypot(tg.x - cam.x, tg.z - cam.z);
      const pitch = Math.atan2(k.h / 2 - 1.6, d);
      window.__pose = { x: cam.x, y: g0() + 1.6, z: cam.z, h: hd, p: pitch, fov: 70 };
      const f0 = wd.renderer.info.render.frame, t0 = Date.now(); while (wd.renderer.info.render.frame - f0 < 40 && Date.now() - t0 < 90000) await new Promise(r => setTimeout(r, 80));
      window.__pose.y = g0() + 1.6;
      const f1 = wd.renderer.info.render.frame; while (wd.renderer.info.render.frame - f1 < 12 && Date.now() - t0 < 120000) await new Promise(r => setTimeout(r, 80));
      const c = wd.camera, gb = Math.max(0, wd.data.H(tg.x, tg.z)); let xs = [], yt = [], yb = [], behind = 0;
      for (const q of k.poly) { const s = W.toScene(q[0], q[1]);
        for (const [y, arr] of [[gb, yb], [gb + k.h, yt]]) { const v = new THREE.Vector3(s.x, y, s.z).project(c); if (v.z > 1) behind++; xs.push((v.x + 1) / 2 * innerWidth); arr.push((1 - v.y) / 2 * innerHeight); } }
      return { x0: Math.min(...xs), x1: Math.max(...xs), ytop: Math.min(...yt), ybase: Math.max(...yb), behind, d, pitchDeg: pitch * 180 / Math.PI };
    }, k);
    const file = `/tmp/claude-0/davinci/renders/${k.f}_${k.id}.png`; await p.screenshot({ path: file });
    meta.push({ ...k, ...r, file, poly: undefined }); console.log(k.f, k.id, JSON.stringify(r));
  }
  fs.writeFileSync('/tmp/claude-0/davinci/renders/meta.json', JSON.stringify(meta, null, 1));
  console.log('errors', errs.slice(0, 5)); await b.close();
})();
