(() => {
  const B = window.BHM;
  B.register('parallels', async (parts) => {
    const ref = decodeURIComponent(parts.slice(1).join('/')) || 'Genesis 1:1';
    const m = ref.match(/^(.*\S)\s+(\d+[ab]?):(\d+)$/);
    if (!m) { B.$app.innerHTML = `<div class="notice">רפרנס לא תקין: ${B.esc(ref)}</div>`; return; }
    const [, book, ch, vs] = m;
    let d, cnt;
    try {
      [d, cnt] = await Promise.all([B.api(`/api/parallels?ref=${B.enc(ref)}`), B.api(`/api/parallels/count?chapter=${B.enc(book + ' ' + ch)}`)]);
    } catch (e) { B.$app.innerHTML = `<div class="notice">${B.esc(e.message)}</div>`; return; }
    const verses = Object.keys(cnt.counts);
    const nav = verses.map(k => `<a class="tag${k === vs ? ' b' : ''}" href="#/parallels/${B.enc(book + ' ' + ch + ':' + k)}" title="${B.esc(cnt.commentators[k])} מפרשים">${B.esc(k)} (${B.esc(cnt.counts[k])})</a>`).join(' ');
    const base = d.base ? `<div class="card"><div class="text" lang="he" dir="rtl">${B.esc(d.base.text)}</div>
      <div class="muted small">${B.esc(d.base.version_title)} <span class="tag a">${B.esc(d.base.license)}</span></div></div>` : `<div class="notice">נוסח הפסוק לא נמצא בספרייה.</div>`;
    const cols = d.commentaries.map(c => `<div class="card"><b>${B.esc(c.he_title || c.title)}</b>
      <div class="muted small">${B.esc(c.version_title)} <span class="tag a">${B.esc(c.license)}</span></div>
      ${c.segments.map(s => `<p class="text" dir="rtl" style="margin:.5em 0">${B.esc(s.text)}</p>`).join('')}</div>`).join('');
    B.$app.innerHTML = `<h1>מקראות גדולות · ${B.esc(d.ref)}</h1>
      <div class="row small">${nav}</div>
      ${base}
      <h2>מפרשים (${B.esc(d.commentaries.length)})</h2>
      ${cols ? `<div class="grid">${cols}</div>` : '<div class="muted">אין מפרשים לפסוק זה בספרייה.</div>'}`;
  });
})();
