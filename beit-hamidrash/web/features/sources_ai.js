(() => {
  const B = window.BHM, esc = B.esc;
  B.register('sources_ai', async () => {
    B.$app.innerHTML = `<h1>מאתר מקורות</h1>
    <div class="notice">המאתר מחפש מקורות בספרייה בלבד ואינו פוסק הלכה. לשאלה הלכתית יש לפנות לרב או לבית הדין.</div>
    <div class="panel"><div class="row"><input id="saq" style="flex:1" maxlength="500" placeholder="כתבו שאלה או מילות חיפוש…"><button id="sab">חיפוש מקורות</button></div></div>
    <div id="sar"></div>`;
    const run = async () => {
      const q = B.$app.querySelector('#saq').value.trim(), out = B.$app.querySelector('#sar');
      if (q.length < 2) return;
      out.innerHTML = '<p class="muted">מחפש…</p>';
      try {
        const d = await B.api('/api/sources_ai/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q }) });
        let h = '';
        if (d.summary) h += `<div class="panel"><span class="tag x">${esc(d.summary.label)}</span> <span class="muted small">מודל: ${esc(d.summary.model)}</span><div class="body" style="white-space:pre-wrap">${esc(d.summary.text)}</div></div>`;
        if (d.model_error) h += `<div class="notice">${esc(d.model_error)}</div>`;
        h += `<h3>מקורות (${d.sources.length})</h3><div class="panel">${d.sources.map(s => `<div class="post"><a href="#/goto/${B.enc(s.ref)}">${esc(s.ref)}</a> <span class="muted small">${esc(s.version_title)}</span><div class="body">${esc(s.text)}</div></div>`).join('') || '<p class="muted">לא נמצאו מקורות.</p>'}</div>`;
        out.innerHTML = h;
      } catch (e) { out.innerHTML = `<p>שגיאה: ${esc(e.message)}</p>`; }
    };
    B.$app.querySelector('#sab').onclick = run;
    B.$app.querySelector('#saq').onkeydown = (e) => { if (e.key === 'Enter') run(); };
  });
})();
