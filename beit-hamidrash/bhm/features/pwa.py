"""PWA: manifest, service worker, offline page and icon for installable/offline use."""
from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

WEB = Path(__file__).resolve().parent.parent.parent / "web"


def compute_cache_version(web: Path = WEB) -> str:
    h = hashlib.sha256()
    try:
        for f in sorted(p for p in web.rglob("*") if p.is_file()):
            h.update(f"{f.relative_to(web)}:{f.stat().st_mtime_ns}".encode())
    except OSError:
        pass
    return "bhm-pwa-" + h.hexdigest()[:12]


CACHE_VERSION = compute_cache_version()

ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
    '<rect width="512" height="512" rx="96" fill="#1f3a5f"/>'
    '<path d="M96 144h128c20 0 32 12 32 32v192c0-16-12-28-32-28H96z" fill="#f4e9c8"/>'
    '<path d="M416 144H288c-20 0-32 12-32 32v192c0-16 12-28 32-28h128z" fill="#e6d49a"/>'
    '<rect x="248" y="168" width="16" height="200" fill="#1f3a5f"/></svg>'
)

MANIFEST = {
    "name": "בית המדרש הגדול",
    "short_name": "בית המדרש",
    "description": "ספריית תורה ורשת חברתית חתומה",
    "lang": "he",
    "dir": "rtl",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#1f3a5f",
    "icons": [
        {"src": "/api/pwa/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
        {"src": "/api/pwa/icon.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "maskable"},
    ],
}

OFFLINE_HTML = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>לא מחובר</title>
<style>body{font-family:serif;text-align:center;margin:15vh 1rem;color:#1f3a5f}</style></head>
<body><h1>אין חיבור לרשת</h1><p>בית המדרש הגדול זמין במצב לא מקוון רק לדפים שכבר נטענו.</p>
<p><a href="/">נסה שוב</a></p></body></html>"""

SW_JS = """
const VERSION = '%(v)s';
const STATIC = VERSION + '-static', API = VERSION + '-api';
const PRECACHE = ['/', '/api/pwa/offline'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(STATIC).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(
    ks.filter(k => k.startsWith('bhm-pwa-') && !k.startsWith(VERSION)).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
});
const NEVER = ['/api/moderation/', '/api/admin/', '/api/sources_ai/'];
async function networkFirst(req, name) {
  const c = await caches.open(name);
  try {
    const res = await fetch(req);
    if (res && res.ok) c.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await c.match(req);
    if (hit) return hit;
    return new Response(JSON.stringify({error: 'offline'}),
      {status: 503, headers: {'Content-Type': 'application/json'}});
  }
}
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;           // never cache POST etc.
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === '/api/pwa/sw.js') return;
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(async () =>
      (await caches.match('/')) || (await caches.match('/api/pwa/offline'))));
    return;
  }
  if (NEVER.some(p => url.pathname.startsWith(p))) return;   // never cached
  if (url.pathname.startsWith('/static/')) e.respondWith(networkFirst(req, STATIC));
  else if (url.pathname.startsWith('/api/')) e.respondWith(networkFirst(req, API));
});
""" % {"v": CACHE_VERSION}


def make_router(node) -> APIRouter:
    r = APIRouter(prefix="/api/pwa")

    @r.get("/sw.js")
    def sw():
        return Response(SW_JS, media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

    @r.get("/manifest.json")
    def manifest():
        return JSONResponse(MANIFEST, media_type="application/manifest+json")

    @r.get("/icon.svg")
    def icon():
        return Response(ICON_SVG, media_type="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=86400"})

    @r.get("/offline")
    def offline():
        return Response(OFFLINE_HTML, media_type="text/html; charset=utf-8")

    return r
