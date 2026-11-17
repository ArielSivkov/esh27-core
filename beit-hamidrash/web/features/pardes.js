BHM.register('pardes', async () => {
  const { esc, enc, api, $app } = BHM;
  $app.innerHTML = '<p class="muted">טוען…</p>';
  let d;
  try { d = await api('/api/pardes/gates'); } catch (e) { $app.innerHTML = `<div class="notice">${esc(e.message)}</div>`; return; }
  const site = '/api/pardes/site/index.html';
  $app.innerHTML = `<h2>פרדס רימונים · ל"ב שערים</h2>
    <div class="notice small">${esc(d.note)} תוכן אוטומטי באתר הלימוד הוא כלי עזר ולא פסיקה.</div>
    <p><a href="${site}" target="_blank" rel="noopener"><button>לאתר הלימוד (ל"ב דרכים)</button></a></p>
    <div class="grid">${d.gates.map(g => `<div class="card">
      <b>שער ${esc(g.heb || g.n)}: ${esc(g.title)}</b>
      <div class="small muted">${esc(g.chapters)} פרקים</div>
      <div class="row">
        ${g.refs.length ? `<a href="#/goto/${enc(g.refs[0])}">קריאה בספרייה</a>` : '<span class="muted small">אין טקסט בספרייה</span>'}
        <a href="${site}#/way/${encodeURIComponent(g.n)}" target="_blank" rel="noopener">דרך לימוד ${esc(g.n)}</a>
      </div>
      <div class="small">${g.refs.map((r, i) => `<a class="tag" href="#/goto/${enc(r)}">${esc(i + 1)}</a>`).join(' ')}</div>
    </div>`).join('')}</div>`;
});
