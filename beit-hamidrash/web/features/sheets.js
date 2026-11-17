(() => {
const B = window.BHM, esc = B.esc, enc = encodeURIComponent;
const $ = (s) => B.$app.querySelector(s);

function itemHTML(it) {
  if (it.type === 'ref') {
    if (!it.ok) return `<div class="post"><b>${esc(it.ref)}</b> <span class="tag x">לא נמצא בספרייה</span></div>`;
    return `<div class="post"><div class="meta"><a href="#/goto/${enc(it.ref)}"><b>${esc(it.ref)}</b></a> · <span class="muted small">${esc(it.version)} · ${esc(it.license)}</span></div><div class="body text" style="white-space:pre-wrap">${esc(it.text)}</div></div>`;
  }
  return `<div class="post"><div class="body" style="white-space:pre-wrap">${esc(it.text)}</div></div>`;
}

async function list() {
  const ss = await B.api('/api/sheets');
  B.$app.innerHTML = `<h1>דפי מקורות</h1><div class="row"><a href="#/sheets/new"><button>דף מקורות חדש</button></a></div>
  <div class="grid">${ss.map(s => `<a class="card" href="#/sheet/${esc(s.id)}"><b>${esc(s.title)}</b><div class="muted small">${esc(s.author_name)} · ${esc(s.ts.slice(0, 10))} · ${s.items} פריטים (${s.refs} מקורות)</div></a>`).join('') || '<p class="muted">עוד לא פורסמו דפי מקורות.</p>'}</div>`;
}

async function view(id) {
  const s = await B.api(`/api/sheets/${enc(id)}`);
  B.$app.innerHTML = `<p class="small"><a href="#/sheets">דפי מקורות</a></p><h1>${esc(s.title)}</h1>
  <p class="muted small">נערך בידי ${esc(s.author_name)} · ${esc(s.ts.slice(0, 10))} · חתום דיגיטלית</p>
  ${s.notes ? `<div class="notice">${esc(s.notes)}</div>` : ''}
  <div class="panel">${s.items.map(itemHTML).join('')}</div>
  <div class="row"><button id="pr" class="ghost">הדפסה</button></div>`;
  $('#pr').onclick = () => window.print();
}

function editor() {
  let items = [];
  const draw = () => {
    $('#its').innerHTML = items.map((it, i) => `<div class="post"><div class="row small"><b>${it.ref ? esc(it.ref) : 'טקסט חופשי'}</b>
      <button class="ghost" data-up="${i}">למעלה</button><button class="ghost" data-dn="${i}">למטה</button><button class="ghost" data-rm="${i}">הסרה</button></div>
      ${it.ref ? '' : `<div class="body" style="white-space:pre-wrap">${esc(it.text)}</div>`}</div>`).join('') || '<p class="muted">הדף ריק.</p>';
    const mv = (i, d) => { const j = i + d; if (j < 0 || j >= items.length) return; [items[i], items[j]] = [items[j], items[i]]; draw(); };
    B.$app.querySelectorAll('[data-up]').forEach(b => b.onclick = () => mv(+b.dataset.up, -1));
    B.$app.querySelectorAll('[data-dn]').forEach(b => b.onclick = () => mv(+b.dataset.dn, 1));
    B.$app.querySelectorAll('[data-rm]').forEach(b => b.onclick = () => { items.splice(+b.dataset.rm, 1); draw(); });
  };
  B.$app.innerHTML = `<p class="small"><a href="#/sheets">דפי מקורות</a></p><h1>דף מקורות חדש</h1>
  <div class="panel"><input id="t" placeholder="כותרת הדף" style="width:100%"><textarea id="n" placeholder="הערות (לא חובה)"></textarea></div>
  <div class="panel"><h3>הוספת מקור</h3><div class="row"><input id="r" placeholder="למשל Genesis 1:1" style="width:min(300px,100%)"><button id="ar">בדיקה והוספה</button></div><div id="rm" class="small"></div>
  <h3>הוספת טקסט חופשי</h3><textarea id="x" placeholder="טקסט"></textarea><div class="row"><button id="ax" class="ghost">הוספה</button></div></div>
  <div class="panel"><h3>פריטי הדף</h3><div id="its"></div></div>
  <div class="row"><button id="pub">פרסום חתום</button><span id="err" class="small"></span></div>`;
  draw();
  $('#ar').onclick = async () => {
    const ref = $('#r').value.trim(); if (!ref) return;
    try {
      const p = await B.api('/api/sheets/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items: [{ ref }] }) });
      if (!p.ok) { $('#rm').innerHTML = `<span class="tag x">${esc(ref)} לא נמצא בספרייה</span>`; return; }
      items.push({ ref }); $('#r').value = ''; $('#rm').innerHTML = `<span class="tag a">נוסף: ${esc(p.items[0].version)}</span>`; draw();
    } catch (e) { $('#rm').textContent = e.message; }
  };
  $('#ax').onclick = () => { const t = $('#x').value.trim(); if (!t) return; items.push({ text: t }); $('#x').value = ''; draw(); };
  $('#pub').onclick = async () => {
    const title = $('#t').value.trim();
    if (!title || !items.length) { $('#err').textContent = 'נדרשים כותרת ולפחות פריט אחד'; return; }
    const body = { title, items }; const notes = $('#n').value.trim(); if (notes) body.notes = notes;
    try { const e = await B.post({ kind: 'sheet', body }); location.hash = `#/sheet/${e.id}`; } catch (e) { $('#err').textContent = e.message; }
  };
}

const page = async (parts) => { try { if (parts[0] === 'sheet') await view(parts[1]); else if (parts[1] === 'new') editor(); else await list(); } catch (e) { B.$app.innerHTML = `<p>שגיאה: ${esc(e.message)}</p>`; } };
B.register('sheets', page);
B.register('sheet', page);
})();
