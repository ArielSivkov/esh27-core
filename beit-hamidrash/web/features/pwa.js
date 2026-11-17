// PWA: manifest link, service worker registration, small install/offline indicator.
(function () {
  if (window.__bhmPwa) return;
  window.__bhmPwa = true;
  if (!document.querySelector('link[rel="manifest"]')) {
    const l = document.createElement('link');
    l.rel = 'manifest'; l.href = '/api/pwa/manifest.json';
    document.head.appendChild(l);
  }
  if (!document.querySelector('meta[name="theme-color"]')) {
    const m = document.createElement('meta');
    m.name = 'theme-color'; m.content = '#1f3a5f';
    document.head.appendChild(m);
  }
  const bar = document.createElement('div');
  bar.setAttribute('dir', 'rtl');
  bar.style.cssText = 'position:fixed;bottom:8px;left:8px;z-index:9999;font-size:12px;display:flex;gap:6px;align-items:center';
  const status = document.createElement('span');
  status.className = 'tag';
  const btn = document.createElement('button');
  btn.textContent = 'התקן אפליקציה';
  btn.style.display = 'none';
  bar.append(status, btn);
  function upd() {
    status.textContent = navigator.onLine ? 'מקוון' : 'לא מקוון - מוצג מהמטמון';
    status.style.opacity = navigator.onLine ? '0.5' : '1';
  }
  upd();
  window.addEventListener('online', upd);
  window.addEventListener('offline', upd);
  let deferred = null;
  window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); deferred = e; btn.style.display = ''; });
  btn.onclick = async () => { if (!deferred) return; deferred.prompt(); await deferred.userChoice; deferred = null; btn.style.display = 'none'; };
  window.addEventListener('appinstalled', () => { btn.style.display = 'none'; });
  document.body.appendChild(bar);
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/api/pwa/sw.js', { scope: '/' }).catch(() => {});
  }
})();
