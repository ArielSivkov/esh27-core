(() => {
const B = window.BHM, esc = B.esc, enc = B.enc;
const me = () => document.getElementById('me').value;
const when = (t) => esc((t || '').slice(0, 16).replace('T', ' '));
const card = (i, mode) => {
  const reasons = (i.reports || []).map(r => `<li>${esc(r.reason || '(ללא סיבה)')} <span class="muted small">· ${esc(r.by_name)}</span></li>`).join('');
  const hb = i.hidden_by;
  return `<div class="post" data-id="${esc(i.id)}"><div class="meta"><b>${esc(i.author_name || '')}</b> · ${esc(i.kind || '')} · ${when(i.ts)}${i.ref ? ' · ' + esc(i.ref) : ''}</div>
  ${i.title ? `<h3 style="margin:.2em 0">${esc(i.title)}</h3>` : ''}<div class="body">${esc(i.text)}</div>
  ${mode === 'queue' ? `<div class="small"><span class="tag x">${esc(i.report_count)} דיווחים</span><ul>${reasons}</ul></div>` : `<p class="small muted">הוסתר בידי ${esc(hb.by_name)} · ${when(hb.ts)} · סיבה: ${esc(hb.reason || '(ללא)')}</p>`}
  <div class="row small"><input class="why" placeholder="סיבה" style="width:200px"><button data-act="${mode === 'queue' ? 'hide' : 'unhide'}" data-id="${esc(i.id)}">${mode === 'queue' ? 'הסתרה' : 'ביטול הסתרה'}</button><span class="muted" title="${esc(i.id)}">${esc(i.id.slice(0, 10))}</span></div></div>`;
};
async function queuePage() {
  const [q, h] = await Promise.all([B.api(`/api/moderation/queue?as=${enc(me())}`), B.api(`/api/moderation/hidden?as=${enc(me())}`)]);
  B.$app.innerHTML = `<h1>פיקוח תוכן</h1>
  <div class="notice">הסתרה אינה מחיקה. כל האירועים חתומים ונשמרים בספר ההיסטוריה; הסתרה רק מסירה תוכן מהתצוגה, וניתן לבטלה. רק הסתרה שנחתמה בידי מפקח תוכן מוסמך נספרת${q.is_moderator ? '.' : ' (המשתמש הנבחר אינו מפקח, ולכן הסתרה שלו לא תיכנס לתוקף).'}</div>
  <h2>תור דיווחים (${q.items.length})</h2><div class="panel">${q.items.map(i => card(i, 'queue')).join('') || '<p class="muted">אין דיווחים פתוחים.</p>'}</div>
  <h2>תוכן מוסתר (${h.items.length})</h2><div class="panel">${h.items.map(i => card(i, 'hidden')).join('') || '<p class="muted">אין תוכן מוסתר.</p>'}</div>`;
  B.$app.querySelectorAll('[data-act]').forEach(b => b.onclick = async () => {
    const reason = b.closest('.post').querySelector('.why').value.trim();
    try { await B.post({ kind: b.dataset.act, target: b.dataset.id, body: { reason } }); } catch (e) { alert(e.message); }
    queuePage();
  });
}
async function reportPage(id) {
  B.$app.innerHTML = `<p class="small"><a href="#/moderation">פיקוח תוכן</a></p><h1>דיווח על תוכן</h1>
  <p class="small muted">אירוע: <code>${esc(id)}</code></p>
  <div class="panel"><textarea id="rr" placeholder="מה הבעיה בתוכן?"></textarea><div class="row"><button id="rs">שליחת דיווח חתום</button></div>
  <p class="small muted">הדיווח נבדק בידי מפקח תוכן. הדיווח עצמו אינו מסתיר דבר.</p></div><div id="rm"></div>`;
  B.$app.querySelector('#rs').onclick = async () => {
    const reason = B.$app.querySelector('#rr').value.trim();
    if (!reason) return;
    const out = B.$app.querySelector('#rm');
    try { await B.post({ kind: 'report', target: id, body: { reason } }); out.innerHTML = '<div class="notice">הדיווח נשלח. תודה.</div>'; } catch (e) { out.innerHTML = `<div class="notice">${esc(e.message)}</div>`; }
  };
}
B.register('moderation', async (parts) => { if (parts[1] === 'report') return reportPage(parts[2]); return queuePage(); });
B.register('report', async (parts) => reportPage(parts[1]));
})();
