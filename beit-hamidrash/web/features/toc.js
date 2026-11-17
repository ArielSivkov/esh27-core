BHM.register('toc', async () => {
  const { esc, enc, $app } = BHM;
  $app.innerHTML = '<p class="muted">טוען…</p>';
  let d;
  try { d = await BHM.api('/api/toc'); } catch (e) { $app.innerHTML = `<div class="notice">${esc(String(e.message || e))}</div>`; return; }
  const cnt = (n) => n.book ? 1 : n.children.reduce((a, c) => a + cnt(c), 0);
  const node = (n) => n.book
    ? `<div class="row" style="padding:2px 14px"><a href="#/book/${enc(n.book.title)}">${esc(n.book.he_title)}</a> <span class="muted small">${esc(n.book.title)}</span></div>`
    : `<details style="margin:2px 0"><summary><b>${esc(n.he)}</b> <span class="tag">${esc(String(cnt(n)))}</span></summary><div style="margin-inline-start:16px">${n.children.map(node).join('')}</div></details>`;
  $app.innerHTML = `<h1>תוכן עניינים</h1>
    <p class="muted small">${esc(String(d.books))} ספרים · מקור המבנה: ${d.source === 'cache' ? 'ספריא (מטמון)' : 'קטגוריות הספרייה המקומית'}</p>
    ${d.warning ? `<div class="notice">${esc(d.warning)}</div>` : ''}
    <p><button id="toc-ref">רענן מהרשת</button></p>
    <div class="panel">${d.tree.map(node).join('') || '<p class="muted">הספרייה ריקה</p>'}</div>
    <p class="muted small">${esc(d.note)}</p>`;
  document.getElementById('toc-ref').onclick = async () => {
    try { await BHM.api('/api/toc/refresh', { method: 'POST' }); } catch (e) { alert('הרענון נכשל (אין רשת?)'); }
    location.reload();
  };
});
