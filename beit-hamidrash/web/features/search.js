// Full-text search page (#/search). Hebrew, RTL; all text is escaped before insertion.
(function () {
  const { api, esc, enc, he, $app } = window.BHM;
  const hl = s => esc(s).replaceAll('⟦', '<mark>').replaceAll('⟧', '</mark>');
  BHM.register('search', async (parts) => {
    let cats = [];
    try { cats = await api('/api/search/categories'); } catch (e) { cats = []; }
    $app.innerHTML = `<h1>חיפוש בטקסטים</h1>
      <div class="panel"><div class="row">
        <input id="sq" placeholder="חיפוש (ניקוד אינו נדרש)" style="width:min(400px,100%)">
        <select id="sc"><option value="">כל המדורים</option>${cats.map(c => `<option value="${esc(c)}">${esc(he(c))}</option>`).join('')}</select>
        <button id="sg">חיפוש</button></div>
        <div class="muted small">החיפוש מתעלם מניקוד וטעמים. זהו כלי חיפוש בלבד ולא פסק הלכה.</div></div>
      <div id="sr"></div>`;
    const q = $app.querySelector('#sq'), c = $app.querySelector('#sc'), out = $app.querySelector('#sr');
    let offset = 0;
    async function run(more) {
      const term = q.value.trim(); if (term.length < 2) return;
      if (!more) { offset = 0; out.innerHTML = ''; }
      const r = await api(`/api/search/q?q=${enc(term)}&category=${enc(c.value)}&limit=20&offset=${offset}`);
      const old = out.querySelector('.more'); if (old) old.remove();
      if (!more && !r.results.length) { out.innerHTML = '<div class="panel muted">לא נמצא</div>'; return; }
      out.insertAdjacentHTML('beforeend', (more ? '' : `<p class="muted small">${r.mode === 'fts' ? 'אינדקס מלא' : 'סריקה איטית (האינדקס לא נבנה)'}</p>`) +
        r.results.map(x => `<div class="post"><a href="#/goto/${enc(x.ref)}">${esc(x.ref)}</a> <span class="muted small">${esc(x.he_book || x.book)} · ${esc(x.version_title)}</span><div class="body">${hl(x.snippet)}</div></div>`).join(''));
      offset += r.results.length;
      if (r.results.length >= 20) { out.insertAdjacentHTML('beforeend', '<button class="more">עוד תוצאות</button>'); out.querySelector('.more').onclick = () => run(true); }
    }
    $app.querySelector('#sg').onclick = () => run(false);
    q.onkeydown = e => { if (e.key === 'Enter') run(false); };
    if (parts[1]) { q.value = decodeURIComponent(parts[1]); run(false); }
  });
})();
