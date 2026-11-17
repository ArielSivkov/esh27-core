(() => {
'use strict';
const B = window.BHM;
const esc = B.esc, enc = B.enc;
const fmt = (ts) => esc(String(ts || '').slice(0, 16).replace('T', ' '));

// Render text as paragraphs; detected refs (offsets into the full text) become links
// with a hover/title snippet. Every piece of user text goes through BHM.esc().
function renderBody(text, refs) {
  let out = '', pos = 0, ri = 0;
  const paras = [];
  text.replace(/[^\n]+/g, (m, off) => { paras.push([off, m]); return m; });
  for (const [off, p] of paras) {
    let html = '', cur = 0;
    while (ri < refs.length && refs[ri].start < off) ri++;
    for (let k = ri; k < refs.length && refs[k].start < off + p.length; k++) {
      const r = refs[k];
      if (r.end > off + p.length) continue;
      const s = r.start - off, e = r.end - off;
      if (s < cur) continue;
      html += esc(p.slice(cur, s));
      html += `<a href="#/goto/${enc(r.ref)}" title="${esc(r.snippet)}" class="aref">${esc(p.slice(s, e))}</a>`;
      cur = e;
    }
    html += esc(p.slice(cur));
    out += `<p style="margin:.6em 0">${html}</p>`;
  }
  return out || '<p class="muted">(ריק)</p>';
}

async function currentUser() {
  const me = document.getElementById('me');
  const us = await B.api('/api/users');
  return us.find(u => u.user === (me && me.value)) || null;
}

async function pageList() {
  const list = await B.api('/api/articles?limit=200');
  B.$app.innerHTML = `<h1>מאמרים</h1>
  <p class="muted small">מאמרים חתומים של חברי בית המדרש. כתיבת מאמר חדש: <a href="#/feed">בית המדרש</a>.</p>
  <div class="panel">${list.map(a => `<div class="post"><a href="#/article/${esc(a.id)}"><b>${esc(a.title)}</b></a>
    <div class="meta small muted">${esc(a.author_name)} · ${fmt(a.ts)}${a.edited ? ` · נערך ${fmt(a.updated)}` : ''}</div>
    <div class="body">${esc(a.snippet)}</div></div>`).join('') || '<p class="muted">עוד לא נכתבו מאמרים.</p>'}</div>`;
}

async function pageArticle(id) {
  const a = await B.api(`/api/articles/${enc(id)}`);
  const me = await currentUser();
  const mine = !!me && me.pubkey === a.author;
  const roles = a.author_roles.map(r => `<span class="tag b">${esc(B.META.roles[r] || r)}</span>`).join('');
  const seen = new Set();
  const srcs = a.refs.filter(r => !seen.has(r.ref) && seen.add(r.ref));
  B.$app.innerHTML = `<p class="small"><a href="#/articles">מאמרים</a></p>
  <h1>${esc(a.title)}</h1>
  <div class="meta small muted"><b>${esc(a.author_name)}</b> ${roles} · ${fmt(a.ts)}${a.history.length > 1 ? ` · נערך ${fmt(a.updated)}` : ''}</div>
  <div class="panel text" id="abody" style="font-size:1.1rem">${renderBody(a.text, a.refs)}</div>
  ${mine ? '<div class="row"><button id="aedit" class="ghost">עריכת המאמר</button></div><div id="aform"></div>' : ''}
  <h3>מקורות שזוהו בטקסט</h3>
  <div class="panel">${srcs.map(r => `<div class="post"><a href="#/goto/${enc(r.ref)}"><b>${esc(r.ref)}</b></a>
    <span class="muted small">${esc(r.version_title)}</span><div class="body small">${esc(r.snippet)}</div></div>`).join('')
    || '<p class="muted">לא זוהו מקורות הקיימים בספרייה.</p>'}</div>
  ${a.ignored_edits ? `<p class="small muted">${a.ignored_edits} עריכות של מי שאינו כותב המאמר לא נספרו.</p>` : ''}
  <h3>היסטוריית עריכות</h3>
  <div class="panel">${a.history.map(h => `<details class="post"><summary>${h.kind === 'edit' ? 'עריכה' : 'נוסח ראשון'} · ${fmt(h.ts)}${h.title ? ' · ' + esc(h.title) : ''}</summary>
    <div class="body" style="white-space:pre-wrap">${esc(h.text)}</div></details>`).join('')}</div>`;
  const btn = B.$app.querySelector('#aedit');
  if (btn) btn.onclick = () => {
    const f = B.$app.querySelector('#aform');
    f.innerHTML = `<div class="panel"><input id="et" style="width:100%" value="${esc(a.title)}"><textarea id="eb" style="min-height:240px">${esc(a.text)}</textarea>
      <div class="row"><button id="es">שמירת עריכה חתומה</button><button id="ec" class="ghost">ביטול</button></div></div>`;
    f.querySelector('#ec').onclick = () => { f.innerHTML = ''; };
    f.querySelector('#es').onclick = async () => {
      const text = f.querySelector('#eb').value.trim(), title = f.querySelector('#et').value.trim();
      if (!text) return;
      try { await B.post({ kind: 'edit', target: a.id, body: { text, title } }); pageArticle(id); }
      catch (e) { alert(e.message); }
    };
  };
}

B.register('articles', async () => { await pageList(); });
B.register('article', async (parts) => { if (parts[1]) await pageArticle(parts[1]); else await pageList(); });
})();
