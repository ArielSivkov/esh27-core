(() => {
'use strict';
const $app = document.getElementById('app');
const $me = document.getElementById('me');
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const api = async (p, opt) => { const r = await fetch(p, opt); if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText); return r.json(); };
const post = (body) => api('/api/events', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user: $me.value, ...body }) });
const enc = encodeURIComponent;
const CAT = { Tanakh: 'תנ"ך', Mishnah: 'משנה', Talmud: 'תלמוד', Tosefta: 'תוספתא', Midrash: 'מדרש', Halakhah: 'הלכה', Kabbalah: 'קבלה', Liturgy: 'תפילה', 'Jewish Thought': 'מחשבה', Chasidut: 'חסידות', Musar: 'מוסר', Responsa: 'שו"ת', 'Second Temple': 'בית שני', Reference: 'עזר', Torah: 'תורה', Prophets: 'נביאים', Writings: 'כתובים', Commentary: 'מפרשים' };
const he = (c) => CAT[c] || c;
const TIER = { certain: ['a', 'נחלת הכלל'], conditional: ['b', 'מותר בייחוס'] };
let META = null, books = null;

function postHTML(e, opts = {}) {
  const roles = e.author_roles.map(r => `<span class="tag b">${esc(META.roles[r] || r)}</span>`).join('');
  return `<div class="post" data-id="${e.id}"><div class="meta"><b>${esc(e.author_name)}</b> ${roles} · ${esc(e.ts.slice(0, 16).replace('T', ' '))}${e.ref ? ` · <a href="#/goto/${enc(e.ref)}">${esc(e.ref)}</a>` : ''}</div>
  ${e.body.title ? `<h3 style="margin:.2em 0">${esc(e.body.title)}</h3>` : ''}<div class="body">${esc(e.body.text)}</div>
  <div class="row small"><button class="ghost" data-endorse="${e.id}">הסכמה (${e.endorsements}${e.scholar_endorsements ? `, מהן ${e.scholar_endorsements} של ת"ח` : ''})</button>${opts.reply !== false ? `<button class="ghost" data-thread="${e.id}">תגובות</button>` : ''}<span class="muted" title="${esc(e.id)}">חתום · ${esc(e.id.slice(0, 10))}</span></div><div class="thread"></div></div>`;
}
function wirePosts(root, reload) {
  root.querySelectorAll('[data-endorse]').forEach(b => b.onclick = async () => { await post({ kind: 'endorse', target: b.dataset.endorse, body: {} }); reload(); });
  root.querySelectorAll('[data-thread]').forEach(b => b.onclick = async () => {
    const box = b.closest('.post').querySelector('.thread');
    const show = async () => {
      const rs = await api(`/api/thread/${b.dataset.thread}`);
      box.innerHTML = `<div style="margin-inline-start:18px">${rs.map(r => postHTML(r, { reply: false })).join('')}<textarea placeholder="תגובה"></textarea><button>הוסף תגובה</button></div>`;
      wirePosts(box, show);
      box.querySelector('button:last-child').onclick = async () => { const t = box.querySelector('textarea').value.trim(); if (t) { await post({ kind: 'reply', target: b.dataset.thread, body: { text: t } }); show(); } };
    };
    show();
  });
}

async function pageHome() {
  const [lg, feed] = await Promise.all([api('/api/legal'), api('/api/feed?limit=8')]);
  $app.innerHTML = `<h1>בית המדרש הגדול</h1>
  <p>ספרייה תורנית מלאה ורשת לימוד: כל אחד יכול לכתוב פירוש על כל פסוק ומשנה, להעלות מאמר ולתת הסכמה. כל פעולה חתומה דיגיטלית וניתנת להעברה בין מחשבים ברשת סגורה או בדיסק און קי.</p>
  <div class="kpis"><div class="kpi"><b>${lg.versions.toLocaleString('he')}</b>גרסאות ספרים</div><div class="kpi"><b>${lg.segments.toLocaleString('he')}</b>קטעי טקסט</div><div class="kpi"><b>${(lg.counts.rejected || 0).toLocaleString('he')}</b>נדחו במחלקה המשפטית</div></div>
  <h2>ספרים ראשונים</h2><div class="grid"><a class="card" href="#/book/Genesis"><b>ספר התורה</b><div class="muted small">בראשית · שמות · ויקרא · במדבר · דברים</div></a><a class="card" href="#/book/Sefer%20Yetzirah"><b>ספר יצירה</b><div class="muted small">דפוס ורשה תרמ"ד ומפרשיו</div></a><a class="card" href="#/library"><b>כל הספרייה</b><div class="muted small">לפי מדורים</div></a></div>
  <h2>חדש בבית המדרש</h2><div class="panel">${feed.map(e => postHTML(e)).join('') || '<p class="muted">עוד לא נכתבו פירושים.</p>'}</div>`;
  wirePosts($app, pageHome);
}

async function pageLibrary(cat) {
  books = books || await api('/api/books');
  if (!cat) {
    const cnt = {}; books.forEach(b => { const c = b.categories[0] || 'אחר'; cnt[c] = (cnt[c] || 0) + 1; });
    $app.innerHTML = `<h1>הספרייה</h1><div class="row"><input id="q" placeholder="חיפוש בטקסטים" style="width:min(400px,100%)"><button id="qs">חיפוש</button></div><div id="qr"></div>
    <div class="grid">${Object.entries(cnt).map(([c, n]) => `<a class="card" href="#/library/${enc(c)}"><b>${esc(he(c))}</b><div class="muted small">${n} ספרים</div></a>`).join('')}</div>`;
    $app.querySelector('#qs').onclick = async () => {
      const q = $app.querySelector('#q').value.trim(); if (q.length < 2) return;
      const rs = await api(`/api/search?q=${enc(q)}`);
      $app.querySelector('#qr').innerHTML = `<div class="panel">${rs.map(r => `<div class="post"><a href="#/goto/${enc(r.ref)}">${esc(r.ref)}</a> <span class="muted small">${esc(r.version_title)}</span><div class="body">${esc(r.text).replaceAll(esc(q), `<mark>${esc(q)}</mark>`)}</div></div>`).join('') || 'לא נמצא'}</div>`;
    };
    return;
  }
  const list = books.filter(b => b.categories[0] === cat);
  const groups = {}; list.forEach(b => { const g = b.categories.slice(1, 3).map(he).join(' › ') || he(cat); (groups[g] = groups[g] || []).push(b); });
  $app.innerHTML = `<p class="small"><a href="#/library">הספרייה</a> › ${esc(he(cat))}</p><h1>${esc(he(cat))}</h1>${Object.entries(groups).map(([g, bs]) => `<h3>${esc(g)}</h3><div class="grid">${bs.map(b => `<a class="card" href="#/book/${enc(b.title)}"><b>${esc(b.he_title || b.title)}</b><div class="muted small">${esc(b.title)} · ${b.versions} גרסאות</div></a>`).join('')}</div>`).join('')}`;
}

async function pageBook(title) {
  const vs = await api(`/api/versions/${enc(title)}`);
  if (!vs.length) { $app.innerHTML = '<p>הספר לא נמצא בספרייה.</p>'; return; }
  const v = vs[0];
  const chs = await api(`/api/chapters?version_id=${v.id}`);
  location.hash = `#/read/${v.id}/${enc(chs[0])}`;
}

async function pageRead(vid, ref, seg) {
  const [chs, segs] = await Promise.all([api(`/api/chapters?version_id=${vid}`), api(`/api/text?version_id=${vid}&ref=${enc(ref)}`)]);
  books = books || await api('/api/books');
  const title = ref.replace(/ [\d:]+$/, '');
  const vs = await api(`/api/versions/${enc(title)}`);
  const v = vs.find(x => x.id === +vid) || vs[0];
  const bk = books.find(b => b.title === title) || {};
  const comm = await api(`/api/commentary?ref=${enc(ref)}`);
  const cnt = {}; comm.forEach(c => { cnt[c.ref] = (cnt[c.ref] || 0) + 1; });
  const [tc, tl] = TIER[v.tier] || ['x', v.tier];
  $app.innerHTML = `<p class="small"><a href="#/library/${enc((bk.categories || [])[0] || '')}">${esc(he((bk.categories || [])[0] || ''))}</a> › ${esc(bk.he_title || title)}</p>
  <h1>${esc(bk.he_title || title)} <span class="muted" style="font-size:1rem">${esc(ref)}</span></h1>
  <div class="row"><select id="ver">${vs.map(x => `<option value="${x.id}" ${x.id === v.id ? 'selected' : ''}>${esc(x.version_title)}</option>`).join('')}</select>
  <span class="tag ${tc}">${tl} · ${esc(v.license)}</span>${v.version_source ? `<a class="small" href="${esc(v.version_source)}" target="_blank" rel="noopener">מקור</a>` : ''}</div>
  ${v.obligations.length ? `<p class="small muted">${v.obligations.map(esc).join(' · ')}</p>` : ''}
  <div class="chs">${chs.length > 1 ? chs.map(c => `<a href="#/read/${vid}/${enc(c)}" class="${c === ref ? 'on' : ''}">${esc(c.split(' ').pop())}</a>`).join('') : ''}</div>
  <div class="reader"><div class="panel text">${segs.map(s => `<span class="seg ${s.ref === seg ? 'on' : ''}" data-ref="${esc(s.ref)}"><sup>${esc(s.ref.split(':').pop())}</sup>${esc(s.text)}${cnt[s.ref] ? `<span class="cnt">${cnt[s.ref]}</span>` : ''}</span> `).join('')}</div>
  <div class="side panel" id="side"><p class="muted">לחצו על פסוק כדי לראות את הפירושים עליו ולכתוב פירוש משלכם.</p></div></div>`;
  $app.querySelector('#ver').onchange = async (e) => { const c2 = await api(`/api/chapters?version_id=${e.target.value}`); location.hash = `#/read/${e.target.value}/${enc(c2.includes(ref) ? ref : c2[0])}`; };
  const openSeg = async (r) => {
    $app.querySelectorAll('.seg').forEach(s => s.classList.toggle('on', s.dataset.ref === r));
    const cs = (await api(`/api/commentary?ref=${enc(r)}`)).filter(c => c.ref === r);
    const side = $app.querySelector('#side');
    side.innerHTML = `<h3>${esc(r)}</h3>${cs.map(c => postHTML(c)).join('') || '<p class="muted">אין עדיין פירושים על קטע זה.</p>'}
      <h3>פירוש חדש</h3><textarea id="ct" placeholder="כתבו את פירושכם…"></textarea><div class="row"><button id="cs">פרסום חתום</button><span class="small muted">בשם ${esc($me.selectedOptions[0]?.text || '')}</span></div>`;
    wirePosts(side, () => openSeg(r));
    side.querySelector('#cs').onclick = async () => { const t = side.querySelector('#ct').value.trim(); if (!t) return; try { await post({ kind: 'commentary', ref: r, body: { text: t } }); openSeg(r); } catch (e) { alert(e.message); } };
  };
  $app.querySelectorAll('.seg').forEach(s => s.onclick = () => openSeg(s.dataset.ref));
  if (seg) openSeg(seg);
}

async function gotoRef(ref) {
  const title = ref.replace(/ [\d:]+$/, '');
  const vs = await api(`/api/versions/${enc(title)}`);
  if (!vs.length) { $app.innerHTML = `<p>${esc(ref)} לא נמצא בספרייה.</p>`; return; }
  const ch = ref.includes(':') ? ref.slice(0, ref.lastIndexOf(':')) : ref;
  location.hash = `#/read/${vs[0].id}/${enc(ch)}/${enc(ref)}`;
}

async function pageFeed() {
  const feed = await api('/api/feed?limit=100');
  $app.innerHTML = `<h1>בית המדרש</h1><div class="panel"><h3>מאמר חדש</h3><input id="at" placeholder="כותרת" style="width:100%"><textarea id="ab" placeholder="תוכן המאמר. מקורות אפשר לכתוב כמו Genesis 1:1"></textarea><div class="row"><button id="as">פרסום חתום</button></div></div><div class="panel">${feed.map(e => postHTML(e)).join('') || '<p class="muted">אין עדיין פרסומים.</p>'}</div>`;
  wirePosts($app, pageFeed);
  $app.querySelector('#as').onclick = async () => { const t = $app.querySelector('#at').value.trim(), b = $app.querySelector('#ab').value.trim(); if (!t || !b) return; try { await post({ kind: 'article', body: { title: t, text: b } }); pageFeed(); } catch (e) { alert(e.message); } };
}

const STATUS = { draft: 'טיוטה', in_review: 'בעיון', approved: 'אושר בחתימת דיין', rejected: 'נדחה' };
async function pageBeitDin(id) {
  if (id) {
    const d = await api(`/api/drafts/${id}`);
    const b = d.draft.body;
    $app.innerHTML = `<p class="small"><a href="#/beitdin">בית הדין</a></p><h1>${esc(b.question)}</h1>
    <p><span class="tag ${d.status === 'approved' ? 'a' : d.status === 'rejected' ? 'x' : 'b'}">${STATUS[d.status]}</span> נכתב בידי ${esc(d.author_name)} · ${d.approvals}/${d.required} חתימות</p>
    ${d.notices.map(n => `<div class="notice">${esc(n)}</div>`).join('')}
    <div class="panel"><h3>תשובה (טיוטה)</h3><div class="text" style="font-size:1.1rem;white-space:pre-wrap">${esc(b.answer)}</div><h3>מקורות</h3><ul>${b.sources.map(s => `<li><a href="#/goto/${enc(s)}">${esc(s)}</a></li>`).join('')}</ul></div>
    <div class="panel"><h3>הערות עיון</h3>${d.reviews.map(r => `<div class="post"><div class="meta">${esc(r.by)} · ${esc(r.ts)}</div><div class="body">${esc(r.note)}</div></div>`).join('') || '<p class="muted">אין</p>'}
    <h3>חתימות דיינים</h3>${d.signatures.map(s => `<div class="post"><div class="meta">${esc(s.by)} · ${s.decision === 'approved' ? 'מאשר' : 'דוחה'} · ${esc(s.ts)}</div><div class="body">${esc(s.note)}</div></div>`).join('') || '<p class="muted">אין</p>'}
    ${d.ignored_signatures.length ? `<p class="small muted">${d.ignored_signatures.length} חתימות של מי שאינו דיין מוסמך לא נספרו.</p>` : ''}</div>
    <div class="panel"><textarea id="rn" placeholder="הערה"></textarea><div class="row"><button id="rv" class="ghost">הוספת הערת עיון</button><button id="ap">חתימה: מאשר</button><button id="rj" class="ghost">חתימה: דוחה</button><span class="small muted">החתימה נספרת רק אם הכותב מונה לדיין</span></div></div>`;
    const note = () => $app.querySelector('#rn').value.trim();
    $app.querySelector('#rv').onclick = async () => { if (note()) { await post({ kind: 'psak_review', target: id, body: { note: note() } }); pageBeitDin(id); } };
    $app.querySelector('#ap').onclick = async () => { await post({ kind: 'psak_sign', target: id, body: { decision: 'approved', note: note() } }); pageBeitDin(id); };
    $app.querySelector('#rj').onclick = async () => { await post({ kind: 'psak_sign', target: id, body: { decision: 'rejected', note: note() } }); pageBeitDin(id); };
    return;
  }
  const ds = await api('/api/drafts');
  $app.innerHTML = `<h1>בית הדין: טיוטות לפסקי הלכה</h1><div class="notice">${esc(META.draft_notice)}</div>
  <div class="panel"><h3>טיוטה חדשה</h3><input id="q" placeholder="השאלה" style="width:100%"><textarea id="a" placeholder="התשובה המוצעת"></textarea><input id="s" placeholder="מקורות, מופרדים בפסיק (חובה). למשל: Genesis 1:1" style="width:100%"><div class="row"><label><input type="checkbox" id="ai"> נכתב בסיוע מודל ממוחשב</label><button id="go">הגשה לעיון</button></div></div>
  <div class="panel">${ds.map(d => `<div class="post"><a href="#/beitdin/${d.id}"><b>${esc(d.draft.body.question)}</b></a> <span class="tag">${STATUS[d.status]}</span>${d.draft.body.ai_generated ? '<span class="tag x">בסיוע מודל</span>' : ''}<div class="meta">${esc(d.author_name)} · ${esc(d.draft.ts.slice(0, 10))}</div></div>`).join('') || '<p class="muted">אין טיוטות.</p>'}</div>`;
  $app.querySelector('#go').onclick = async () => {
    const sources = $app.querySelector('#s').value.split(',').map(x => x.trim()).filter(Boolean);
    try { const e = await post({ kind: 'psak_draft', body: { question: $app.querySelector('#q').value.trim(), answer: $app.querySelector('#a').value.trim(), sources, ai_generated: $app.querySelector('#ai').checked } }); location.hash = `#/beitdin/${e.id}`; } catch (e) { alert(e.message); }
  };
}

async function pageLegal() {
  const lg = await api('/api/legal');
  $app.innerHTML = `<h1>המחלקה המשפטית</h1><p>כל גרסה שנכנסת לספרייה עוברת שער רישוי. גרסה בלי רישיון ידוע, עם רישיון לא-מסחרי, או יצירה מודרנית שסומנה "נחלת הכלל", לא נכנסת ונרשמת כאן לבדיקה.</p>
  <div class="kpis"><div class="kpi"><b>${lg.counts.certain || 0}</b>נחלת הכלל / CC0</div><div class="kpi"><b>${lg.counts.conditional || 0}</b>מותר בייחוס</div><div class="kpi"><b>${lg.counts.rejected || 0}</b>נדחו</div></div>
  <h2>סיבות דחייה</h2><table>${lg.reasons.map(r => `<tr><td>${esc(r.reason)}</td><td>${r.n}</td></tr>`).join('')}</table>
  <h2>ייחוס נדרש (רישיונות CC-BY)</h2><table><tr><th>ספר</th><th>גרסה</th><th>רישיון</th><th>מקור</th></tr>${lg.attribution.map(a => `<tr><td>${esc(a.title)}</td><td>${esc(a.version_title)}</td><td>${esc(a.license)}</td><td>${a.version_source ? `<a href="${esc(a.version_source)}" target="_blank" rel="noopener">קישור</a>` : ''}</td></tr>`).join('')}</table>
  <h2>דוגמת נדחים</h2><table><tr><th>ספר</th><th>גרסה</th><th>רישיון</th><th>סיבה</th></tr>${lg.rejected_sample.map(a => `<tr><td>${esc(a.title)}</td><td>${esc(a.version_title)}</td><td>${esc(a.license)}</td><td>${esc(a.reason)}</td></tr>`).join('')}</table>`;
}

async function route() {
  const parts = location.hash.slice(2).split('/').map(decodeURIComponent);
  document.querySelectorAll('.top nav a').forEach(a => a.classList.toggle('on', a.getAttribute('href').slice(2) === parts[0]));
  try {
    if (!parts[0]) await pageHome();
    else if (parts[0] === 'library') await pageLibrary(parts[1]);
    else if (parts[0] === 'book') await pageBook(parts[1]);
    else if (parts[0] === 'read') await pageRead(parts[1], parts[2], parts[3]);
    else if (parts[0] === 'goto') await gotoRef(parts[1]);
    else if (parts[0] === 'feed') await pageFeed();
    else if (parts[0] === 'beitdin') await pageBeitDin(parts[1]);
    else if (parts[0] === 'legal') await pageLegal();
    window.scrollTo(0, 0);
  } catch (e) { $app.innerHTML = `<p>שגיאה: ${esc(e.message)}</p>`; }
}

(async () => {
  META = await api('/api/meta');
  const us = await api('/api/users');
  $me.innerHTML = us.map(u => `<option value="${esc(u.user)}">${esc(u.name)}${u.roles.length ? ' (' + u.roles.map(r => META.roles[r] || r).join(', ') + ')' : ''}</option>`).join('');
  const firstUser = us.find(u => u.user !== 'authority'); if (firstUser) $me.value = firstUser.user;
  try { const saved = localStorage.getItem('bhm-me'); if (saved && us.some(u => u.user === saved)) $me.value = saved; } catch { }
  $me.onchange = () => { try { localStorage.setItem('bhm-me', $me.value); } catch { } route(); };
  window.addEventListener('hashchange', route);
  route();
})();
})();
