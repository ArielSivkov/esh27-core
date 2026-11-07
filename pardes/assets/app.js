/* Pardes Rimonim – 32 ways. Single-page app, no build step. */
(() => {
'use strict';

const $app = document.getElementById('app');
const cache = {};
const load = (p) => cache[p] || (cache[p] = fetch(p).then(r => { if (!r.ok) throw new Error(p); return r.json(); }));
const gate = (g) => load(`data/gates/${g}.json`);
const allGates = () => Promise.all(Array.from({ length: 32 }, (_, i) => gate(i + 1)));
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};

/* ---------- Hebrew helpers ---------- */
const VAL = { 'א':1,'ב':2,'ג':3,'ד':4,'ה':5,'ו':6,'ז':7,'ח':8,'ט':9,'י':10,'כ':20,'ך':20,'ל':30,'מ':40,'ם':40,'נ':50,'ן':50,'ס':60,'ע':70,'פ':80,'ף':80,'צ':90,'ץ':90,'ק':100,'ר':200,'ש':300,'ת':400 };
const FINAL_BIG = { 'ך':500,'ם':600,'ן':700,'ף':800,'ץ':900 };
const LETTERS = 'אבגדהוזחטיכלמנסעפצקרשת'.split('');
const FIN2REG = { 'ך':'כ','ם':'מ','ן':'נ','ף':'פ','ץ':'צ' };
const REG2FIN = { 'כ':'ך','מ':'ם','נ':'ן','פ':'ף','צ':'ץ' };
const LNAME = { 'א':'אלף','ב':'בית','ג':'גימל','ד':'דלת','ה':'הא','ו':'ואו','ז':'זין','ח':'חית','ט':'טית','י':'יוד','כ':'כף','ל':'למד','מ':'מם','נ':'נון','ס':'סמך','ע':'עין','פ':'פא','צ':'צדי','ק':'קוף','ר':'ריש','ש':'שין','ת':'תו' };
const onlyHeb = (s) => (s || '').replace(/[^א-ת]/g, '');
const gem = (s) => [...onlyHeb(s)].reduce((a, c) => a + (VAL[c] || 0), 0);
const gemBig = (s) => [...onlyHeb(s)].reduce((a, c) => a + (FINAL_BIG[c] || VAL[c] || 0), 0);
const gemSmall = (s) => [...onlyHeb(s)].reduce((a, c) => { let v = VAL[c] || 0; while (v >= 10) v /= 10; return a + v; }, 0);
const fixFinals = (w) => [...w].map((c, i, a) => i === a.length - 1 ? (REG2FIN[c] || c) : (FIN2REG[c] || c)).join('');
function numHeb(n) {
  let o = '';
  for (const [v, c] of [[400,'ת'],[300,'ש'],[200,'ר'],[100,'ק'],[90,'צ'],[80,'פ'],[70,'ע'],[60,'ס'],[50,'נ'],[40,'מ'],[30,'ל'],[20,'כ'],[10,'י']]) while (n >= v) { o += c; n -= v; }
  if (o.endsWith('י') && (n === 5 || n === 6)) { o = o.slice(0, -1) + (n === 5 ? 'טו' : 'טז'); n = 0; }
  if (n) o += 'אבגדהוזחט'[n - 1];
  return o;
}

/* ---------- sefirot ---------- */
const SEF = ['keter','chochma','bina','chesed','gevura','tiferet','netzach','hod','yesod','malchut'];
const SEFN = { keter:'כתר', chochma:'חכמה', bina:'בינה', chesed:'חסד', gevura:'גבורה', tiferet:'תפארת', netzach:'נצח', hod:'הוד', yesod:'יסוד', malchut:'מלכות' };
const POS = { keter:[180,40], chochma:[300,110], bina:[60,110], chesed:[300,230], gevura:[60,230], tiferet:[180,290], netzach:[300,370], hod:[60,370], yesod:[180,430], malchut:[180,520] };
// schematic drawing of the tree (22 lines), used only as a layout
const TREE_EDGES = [['keter','chochma'],['keter','bina'],['keter','tiferet'],['chochma','bina'],['chochma','chesed'],['chochma','tiferet'],['bina','gevura'],['bina','tiferet'],['chesed','gevura'],['chesed','tiferet'],['chesed','netzach'],['gevura','tiferet'],['gevura','hod'],['tiferet','netzach'],['tiferet','hod'],['tiferet','yesod'],['netzach','hod'],['netzach','yesod'],['hod','yesod'],['netzach','malchut'],['hod','malchut'],['yesod','malchut']];

/* ---------- small renderers ---------- */
function bars(rows, opts = {}) {
  const max = Math.max(1, ...rows.map(r => r[1]));
  return `<div class="bars">${rows.map(([label, v, href]) =>
    `<span>${href ? `<a href="${href}">${esc(label)}</a>` : esc(label)}</span><span><span class="bar ${opts.alt ? 'alt' : ''}" style="width:${(v / max * 100).toFixed(1)}%"></span></span><span class="muted small">${v.toLocaleString('he')}</span>`).join('')}</div>`;
}
const gref = (g, c, label) => `<a class="ref" href="#/read/${g}/${c}">${label || `שער ${numHeb(g)} פרק ${numHeb(c)}`}</a>`;
function highlight(text, re) { return re ? esc(text).replace(re, m => `<mark>${m}</mark>`) : esc(text); }
function reEsc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

function kwicCollect(gates, re, limit = 200) {
  const hits = []; const perGate = {};
  for (const G of gates) for (const ch of G.chapters) ch.paras.forEach((p, pi) => {
    re.lastIndex = 0; let m;
    while ((m = re.exec(p))) {
      perGate[G.n] = (perGate[G.n] || 0) + 1;
      if (hits.length < limit) {
        const s = Math.max(0, m.index - 80), e = Math.min(p.length, m.index + m[0].length + 110);
        hits.push({ g: G.n, c: ch.n, pi, pre: (s ? '…' : '') + p.slice(s, m.index), hit: m[0], post: p.slice(m.index + m[0].length, e) + (e < p.length ? '…' : '') });
      }
      if (!re.global) break;
    }
  });
  return { hits, perGate, total: Object.values(perGate).reduce((a, b) => a + b, 0) };
}
function kwicHTML(res, q) {
  return `<p class="muted">${res.total.toLocaleString('he')} מופעים בספר${res.total > res.hits.length ? ` · מוצגים ${res.hits.length} הראשונים` : ''}</p>
  <div class="two"><div>${bars(Object.entries(res.perGate).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([g, v]) => [`שער ${numHeb(+g)}`, v, `#/way/${g}`]))}</div><div></div></div>
  <ul class="kwic">${res.hits.map(h => `<li>${esc(h.pre)}<mark>${esc(h.hit)}</mark>${esc(h.post)} ${gref(h.g, h.c)}</li>`).join('')}</ul>`;
}
async function kwicInto(el, term, gates) {
  el.innerHTML = '<p class="muted">מחפש בספר…</p>';
  const G = gates ? await Promise.all(gates.map(gate)) : await allGates();
  el.innerHTML = kwicHTML(kwicCollect(G, new RegExp(reEsc(term), 'g'), 60), term);
}

/* ---------- pages ---------- */
async function pageHome() {
  const [meta, ways] = await Promise.all([load('data/meta.json'), load('data/ways.json')]);
  const words = meta.gates.reduce((a, g) => a + g.words, 0);
  const axes = ['לימוד', 'חקר', 'מידול', 'תוצר'];
  $app.innerHTML = `
  <section class="hero">
    <h1>ספר פרדס רימונים · ל"ב דרכים</h1>
    <p>הספר המלא של הרמ"ק, ומעליו ל"ב דרכי עבודה, דרך אחת לכל שער. כל דרך כוללת תוכנית (שאלה, שיטה ותוצר), נתונים שחולצו מהטקסט וכלי עבודה.</p>
    <div class="kpis">
      <div class="kpi"><b>32</b><span>שערים</span></div>
      <div class="kpi"><b>${meta.toc.length}</b><span>פרקים</span></div>
      <div class="kpi"><b>${words.toLocaleString('he')}</b><span>מילים</span></div>
      <div class="kpi"><b>${(await load('data/kinuyim.json')).length.toLocaleString('he')}</b><span>ערכי כינויים במילון</span></div>
    </div>
    <div class="row"><a href="#/plan"><button>לתוכנית המלאה</button></a><a href="#/read/1/1"><button class="ghost">להתחיל לקרוא</button></a></div>
  </section>
  ${axes.map(ax => `<h2>${ax}</h2><div class="grid">${ways.filter(w => w.axis === ax).map(w => wayCard(w, meta)).join('')}</div>`).join('')}`;
}
function wayCard(w, meta) {
  const g = meta.gates[w.n - 1];
  return `<a class="card" href="#/way/${w.n}"><span class="num">${numHeb(w.n)}</span> <span class="tag s">שער ${esc(g.title)}</span><h3>${esc(w.name)}</h3><p>${esc(w.deliverable)}</p></a>`;
}

async function pagePlan() {
  const [meta, ways] = await Promise.all([load('data/meta.json'), load('data/ways.json')]);
  $app.innerHTML = `
  <h1>התוכנית המלאה</h1>
  <p>ל"ב דרכים, אחת לכל שער. כל דרך שייכת לאחד מארבעה צירים: <span class="tag">לימוד</span> הבנת הטקסט, <span class="tag">חקר</span> שאלות על מקורות ועמדות, <span class="tag">מידול</span> בניית מודל פורמלי, <span class="tag">תוצר</span> כלי שימושי.</p>
  <div class="panel">
    <h3>שלבי העבודה</h3>
    <div class="phase"><b>שלב א · תשתית נתונים (בנוי).</b> חלוקת הספר לשערים, פרקים ופסקאות; ספירת אזכורי ספירות ומקורות; הפניות פנימיות בין שערים; חילוץ ערכי שער כ"ג.</div>
    <div class="phase"><b>שלב ב · כלים ומודלים (בנוי).</b> לכל דרך דף עם נתונים וכלי: מילון, מחשבון גימטריה, מחולל צירופים, אילן, רשת, מטריצות, לוח לימוד.</div>
    <div class="phase"><b>שלב ג · עיון אנושי (פתוח).</b> בכל דרך מופיע "המשך מחקר": מה צריך עין אנושית כדי להפוך את הנתונים למסקנות. את זה המחשב לא עושה במקומך.</div>
    <div class="phase"><b>שלב ד · חיבור לגרף ידע אחד.</b> דרכים 4, 7, 16, 20, 23 ו-27 מזינות סכמה אחת של הספירות (דרך 4), שממנה אפשר לבנות API במחשוב ESH27.</div>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>#</th><th>שער</th><th>דרך</th><th>ציר</th><th>שאלה</th><th>שיטה</th><th>תוצר</th><th>המשך מחקר</th></tr></thead>
    <tbody>${ways.map(w => `<tr>
      <td><a href="#/way/${w.n}">${numHeb(w.n)}</a></td><td>${esc(meta.gates[w.n - 1].title)}</td>
      <td><a href="#/way/${w.n}">${esc(w.name)}</a></td><td><span class="tag">${w.axis}</span></td>
      <td>${esc(w.question)}</td><td><ol>${w.method.map(m => `<li>${esc(m)}</li>`).join('')}</ol></td>
      <td>${esc(w.deliverable)}</td><td class="muted">${esc(w.research)}</td></tr>`).join('')}</tbody>
  </table></div>`;
}

async function pageWay(n) {
  n = Math.min(32, Math.max(1, n | 0));
  const [meta, ways, stats] = await Promise.all([load('data/meta.json'), load('data/ways.json'), load('data/stats.json')]);
  const w = ways[n - 1], g = meta.gates[n - 1];
  const sef = stats.sefByGate[n];
  const src = stats.srcByGate[n];
  const outRefs = stats.refs.filter(r => r[0] === n).sort((a, b) => b[2] - a[2]);
  const inRefs = stats.refs.filter(r => r[1] === n).sort((a, b) => b[2] - a[2]);
  const T = (k) => meta.gates[k - 1].title;
  $app.innerHTML = `
  <div class="row small muted"><a href="#/plan">התוכנית</a> › דרך ${numHeb(n)}</div>
  <h1><span class="muted">${numHeb(n)}.</span> ${esc(w.name)}</h1>
  <p><span class="tag">${w.axis}</span> <span class="tag s">שער ${numHeb(n)}: ${esc(g.title)}</span> <span class="muted small">${g.chapters} פרקים · ${g.words.toLocaleString('he')} מילים</span></p>
  <div class="two">
    <div class="panel plan"><h3>התוכנית</h3><dl>
      <dt>שאלה</dt><dd>${esc(w.question)}</dd>
      <dt>שיטה</dt><dd><ol>${w.method.map(m => `<li>${esc(m)}</li>`).join('')}</ol></dd>
      <dt>תוצר</dt><dd>${esc(w.deliverable)}</dd>
      <dt>המשך מחקר</dt><dd class="muted">${esc(w.research)}</dd></dl></div>
    <div class="panel"><h3>פתיחת השער</h3><p class="text" style="font-size:1.05rem">${esc(g.intro)}</p>${gref(n, 1, 'לקריאת השער ←')}</div>
  </div>
  <h2>${esc(w.deliverable)}</h2>
  <div id="widget" class="panel"><p class="muted">טוען…</p></div>
  <h2>נתוני השער</h2>
  <div class="two">
    <div class="panel"><h3>אזכורי ספירות</h3>${bars(SEF.map(k => [SEFN[k], sef[k]]))}</div>
    <div class="panel"><h3>מקורות מצוטטים</h3>${(() => { const r = stats.sources.filter(s => src[s.key]).map(s => [s.name, src[s.key]]).sort((a, b) => b[1] - a[1]); return r.length ? bars(r, { alt: true }) : '<p class="muted">לא אותרו</p>'; })()}</div>
  </div>
  <div class="two">
    <div class="panel"><h3>מונחים אופייניים לשער</h3><div class="chips">${g.terms.map(([t, c]) => `<a class="chip" href="#/search?q=${encodeURIComponent(t)}">${esc(t)} <small>${c}</small></a>`).join('')}</div></div>
    <div class="panel"><h3>הפניות לשערים אחרים</h3>
      <p class="small muted">השער מפנה אל:</p><div class="chips">${outRefs.map(r => `<a class="chip" href="#/way/${r[1]}">${esc(T(r[1]))} <small>${r[2]}</small></a>`).join('') || '<span class="muted">—</span>'}</div>
      <p class="small muted">מפנים אליו:</p><div class="chips">${inRefs.map(r => `<a class="chip" href="#/way/${r[0]}">${esc(T(r[0]))} <small>${r[2]}</small></a>`).join('') || '<span class="muted">—</span>'}</div></div>
  </div>
  <div class="panel"><h3>פרקי השער</h3><ul class="kwic">${g.chapterOpenings.map((o, i) => `<li>${gref(n, i + 1, `פרק ${numHeb(i + 1)}`)} ${esc(o)}…</li>`).join('')}</ul></div>
  <div class="pager">${n > 1 ? `<a href="#/way/${n - 1}">→ ${esc(ways[n - 2].name)}</a>` : '<span></span>'}${n < 32 ? `<a href="#/way/${n + 1}">${esc(ways[n].name)} ←</a>` : '<span></span>'}</div>`;
  const el = document.getElementById('widget');
  try { await (WIDGETS[w.widget] || WIDGETS.outline)(el, n, w); }
  catch (e) { el.innerHTML = `<p class="muted">שגיאה בטעינת הכלי: ${esc(e.message)}</p>`; }
}

/* ---------- widgets ---------- */
const WIDGETS = {};

WIDGETS.outline = async (el, n) => {
  const G = await gate(n);
  el.innerHTML = `<p class="muted small">מתווה השער: פתיחת כל פרק. לחצו כדי לקרוא.</p><ol class="steps">${G.chapters.map(c => `<li><b>פרק ${c.heb}</b> · <span class="muted small">${c.paras.length} פסקאות</span><div class="text" style="font-size:1rem">${esc((c.paras[0] || '').slice(0, 260))}…</div>${gref(n, c.n, 'קריאה ←')}</li>`).join('')}</ol>`;
};
WIDGETS.timeline = WIDGETS.outline;

WIDGETS.sources = async (el) => {
  const [stats, meta] = await Promise.all([load('data/stats.json'), load('data/meta.json')]);
  const tot = {};
  for (let g = 1; g <= 32; g++) for (const s of stats.sources) tot[s.key] = (tot[s.key] || 0) + stats.srcByGate[g][s.key];
  const srcs = stats.sources.filter(s => tot[s.key]).sort((a, b) => tot[b.key] - tot[a.key]);
  el.innerHTML = `<p class="muted small">כמה פעמים כל מקור נזכר בכל שער (התאמת מחרוזות; קיצורים כמו ס"י עשויים לכלול רעש).</p>
  <h3>בכל הספר</h3>${bars(srcs.map(s => [s.name, tot[s.key]]), { alt: true })}
  <h3>מקור × שער</h3>${heatTable(srcs.map(s => s.name), meta.gates.map(g => g.n), (ri, g) => stats.srcByGate[g][srcs[ri].key])}`;
};
function heatTable(rowLabels, cols, val, colLabel = (g) => `<a href="#/way/${g}">${numHeb(g)}</a>`) {
  let max = 1;
  rowLabels.forEach((_, ri) => cols.forEach(c => { max = Math.max(max, val(ri, c)); }));
  return `<div class="scroll"><table class="heat"><thead><tr><th></th>${cols.map(c => `<th>${colLabel(c)}</th>`).join('')}</tr></thead><tbody>
  ${rowLabels.map((rl, ri) => `<tr><th>${esc(rl)}</th>${cols.map(c => { const v = val(ri, c); const a = v ? 0.12 + 0.88 * Math.sqrt(v / max) : 0; return `<td class="h" style="background:rgba(var(--heat),${a.toFixed(2)});${a > .55 ? 'color:#fff' : ''}">${v || ''}</td>`; }).join('')}</tr>`).join('')}</tbody></table></div>`;
}

WIDGETS.debate = async (el, n) => {
  const G = await gate(n);
  const re = /(יש מי|ויש אומרים|יש מפרשים|קצת מפרשים|קצת המקובלים|דעת|סברת|לדעת|והנראה לנו|ולדעתנו|והעולה|ויש מן)/g;
  const rows = [];
  G.chapters.forEach(c => c.paras.forEach(p => { re.lastIndex = 0; if (re.test(p)) rows.push({ c: c.n, p }); }));
  const hre = new RegExp(re.source, 'g');
  el.innerHTML = `<p class="muted small">${rows.length} פסקאות שבהן מוצגת דעה או הכרעה. אלה חומרי הגלם לטבלת המחלוקת.</p>
  <table><thead><tr><th>פרק</th><th>קטע</th></tr></thead><tbody>${rows.map(r => `<tr><td>${gref(n, r.c, numHeb(r.c))}</td><td class="text" style="font-size:1rem">${highlight(r.p.slice(0, 420) + (r.p.length > 420 ? '…' : ''), hre)}</td></tr>`).join('')}</tbody></table>`;
};

WIDGETS.ontology = async (el) => {
  const [stats, lex, kin] = await Promise.all([load('data/stats.json'), load('data/lexicons.json'), load('data/kinuyim.json')]);
  const tot = Object.fromEntries(SEF.map(k => [k, Object.values(stats.sefByGate).reduce((a, g) => a + g[k], 0)]));
  const topBy = (L, k) => L.filter(e => e.co[k]).sort((a, b) => b.co[k] - a.co[k]).slice(0, 3).map(e => e.label);
  const schema = SEF.map(k => ({
    id: k, name: SEFN[k], mentions: tot[k],
    colors: topBy(lex.colors, k), names: topBy(lex.names, k), heichalot: topBy(lex.heichalot, k),
    kinuyim: kin.filter(e => e.s[0] === k).length,
    kinuyimSample: kin.filter(e => e.s[0] === k).slice(0, 8).map(e => e.t),
    essence: null, vessel: null,
  }));
  el.innerHTML = `<p class="muted small">סכמה אחת לכל ספירה, ממולאת אוטומטית מהדרכים האחרות. השדות essence ו-vessel (עצם וכלי) נשארים ריקים, להשלמה ידנית מתוך שער ד'.</p>
  <div class="scroll"><table><thead><tr><th>ספירה</th><th>אזכורים</th><th>גוונים קרובים</th><th>שמות קרובים</th><th>היכלות קרובים</th><th>כינויים (ראשי)</th></tr></thead><tbody>
  ${schema.map(s => `<tr><th>${s.name}</th><td>${s.mentions.toLocaleString('he')}</td><td>${s.colors.join(', ')}</td><td>${s.names.join(', ')}</td><td>${s.heichalot.join(', ')}</td><td><a href="#/way/23?s=${s.id}">${s.kinuyim}</a></td></tr>`).join('')}
  </tbody></table></div><div class="row"><button id="dl">הורדת הסכמה (JSON)</button></div>`;
  el.querySelector('#dl').onclick = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(schema, null, 2)], { type: 'application/json' }));
    a.download = 'sefirot-schema.json'; a.click();
  };
};

function treeSVG(values, edges, opts = {}) {
  const max = Math.max(1, ...Object.values(values));
  const emax = Math.max(1, ...edges.map(e => e[2] || 1));
  return `<svg viewBox="0 0 360 570" role="img" aria-label="אילן הספירות">
  ${edges.map(([a, b, w]) => { const [x1, y1] = POS[a], [x2, y2] = POS[b]; const sw = w == null ? 2 : 1 + 9 * (w / emax); return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--line)" stroke-width="${sw.toFixed(1)}" ${w != null ? 'stroke-opacity=".9" style="stroke:var(--accent-2)"' : ''}><title>${SEFN[a]} – ${SEFN[b]}${w != null ? ': ' + w : ''}</title></line>`; }).join('')}
  ${SEF.map(k => { const [x, y] = POS[k]; const r = 18 + 16 * Math.sqrt((values[k] || 0) / max); return `<g class="node" data-k="${k}" style="cursor:pointer"><circle cx="${x}" cy="${y}" r="${r.toFixed(1)}" fill="var(--surface)" stroke="var(--accent)" stroke-width="2"/><text x="${x}" y="${y + 5}" text-anchor="middle" font-size="15" fill="var(--ink)">${SEFN[k]}</text>${opts.showVal ? `<text x="${x}" y="${y + r + 14}" text-anchor="middle" font-size="11" fill="var(--muted)">${values[k] || 0}</text>` : ''}</g>`; }).join('')}
  </svg>`;
}

WIDGETS.tree = async (el, n) => {
  const [stats, kin, meta] = await Promise.all([load('data/stats.json'), load('data/kinuyim.json'), load('data/meta.json')]);
  const draw = (g) => {
    const vals = g === 'all' ? Object.fromEntries(SEF.map(k => [k, Object.values(stats.sefByGate).reduce((a, x) => a + x[k], 0)])) : stats.sefByGate[g];
    el.querySelector('.tree').innerHTML = treeSVG(vals, TREE_EDGES, { showVal: true });
    el.querySelectorAll('.node').forEach(nd => nd.onclick = () => {
      const k = nd.dataset.k; const ks = kin.filter(e => e.s[0] === k);
      el.querySelector('.side').innerHTML = `<h3>${SEFN[k]}</h3><p>${vals[k]} אזכורים${g === 'all' ? ' בכל הספר' : ` בשער ${numHeb(+g)}`}. ${ks.length} ערכים במילון שבהם זו הספירה העיקרית.</p><div class="chips">${ks.slice(0, 40).map(e => `<a class="chip" href="#/read/23/${e.c}">${esc(e.t)}</a>`).join('')}</div><p><a href="#/way/23?s=${k}">לכל הכינויים של ${SEFN[k]} ←</a></p>`;
    });
  };
  el.innerHTML = `<div class="row"><label>גודל העיגול לפי אזכורים ב: <select id="tg"><option value="all">כל הספר</option>${meta.gates.map(g => `<option value="${g.n}" ${g.n === n ? 'selected' : ''}>שער ${numHeb(g.n)} · ${esc(g.title)}</option>`).join('')}</select></label></div>
  <div class="tree-wrap"><div class="tree"></div><div class="side"><p class="muted">לחצו על ספירה כדי לראות את כינוייה מתוך המילון.</p><p class="muted small">הקווים הם שרטוט סכמטי של האילן לצורך תצוגה, לא שחזור של ציור מסוים מתוך שער ו'.</p></div></div>`;
  el.querySelector('#tg').onchange = (e) => draw(e.target.value);
  draw(String(n));
};

WIDGETS.network = async (el, n) => {
  const [stats, meta] = await Promise.all([load('data/stats.json'), load('data/meta.json')]);
  const draw = (g) => {
    const pairs = stats.pairsByGate[g] || [];
    const vals = stats.sefByGate[g];
    const strength = Object.fromEntries(SEF.map(k => [k, 0]));
    pairs.forEach(([a, b, c]) => { strength[a] += c; strength[b] += c; });
    el.querySelector('.tree').innerHTML = treeSVG(vals, pairs.slice(0, 30).map(([a, b, c]) => [a, b, c]));
    el.querySelector('.side').innerHTML = `<h3>הקשרים החזקים בשער ${numHeb(+g)}</h3>${bars(pairs.slice(0, 12).map(([a, b, c]) => [`${SEFN[a]} – ${SEFN[b]}`, c]))}<h3>מרכזיות (סכום קשרים)</h3>${bars(SEF.map(k => [SEFN[k], strength[k]]).sort((a, b) => b[1] - a[1]), { alt: true })}`;
  };
  el.innerHTML = `<p class="muted small">עובי הקו = מספר הפסקאות שבהן שתי הספירות מופיעות יחד. זה קשר טקסטואלי מחושב, לא רשימת הצנורות כפי שהיא מנויה בשער.</p>
  <div class="row"><select id="ng">${meta.gates.map(g => `<option value="${g.n}" ${g.n === n ? 'selected' : ''}>שער ${numHeb(g.n)} · ${esc(g.title)}</option>`).join('')}</select></div>
  <div class="tree-wrap"><div class="tree"></div><div class="side"></div></div>`;
  el.querySelector('#ng').onchange = (e) => draw(e.target.value);
  draw(String(n));
};

function sefCount(text) {
  const P = '(?<![א-ת"\'])[ובכלמשהד]{0,3}', E = '(?![א-ת])';
  const pats = { keter:'כתר', chochma:'חכמה', bina:'בינה', chesed:'(?:חסד|גדולה)', gevura:'(?:גבורה|פחד)', tiferet:'(?:תפארת|ת"ת)', netzach:'נצח', hod:'הוד', yesod:'יסוד', malchut:"(?:מלכות|מל')" };
  return Object.fromEntries(SEF.map(k => [k, (text.match(new RegExp(P + pats[k] + E, 'g')) || []).length]));
}

WIDGETS.studybook = async (el, n) => {
  const G = await gate(n);
  const key = `pr-study-${n}`; const done = store.get(key, {});
  el.innerHTML = `<p class="muted small">כרטיס לכל פרק: פתיחה, היקף והספירות הבולטות בו. סמנו פרקים שלמדתם (נשמר בדפדפן שלכם בלבד).</p><div class="grid">${G.chapters.map(c => {
    const t = c.paras.join(' '); const sc = sefCount(t); const top = SEF.filter(k => sc[k]).sort((a, b) => sc[b] - sc[a]).slice(0, 3);
    return `<div class="card"><div class="row" style="justify-content:space-between;margin:0"><span class="num">פרק ${c.heb}</span><label class="small"><input type="checkbox" data-c="${c.n}" ${done[c.n] ? 'checked' : ''}> למדתי</label></div>
    <p class="small">${t.split(/\s+/).length.toLocaleString('he')} מילים · ${top.map(k => `<span class="tag">${SEFN[k]}</span>`).join('')}</p>
    <p class="text" style="font-size:.98rem;color:var(--ink)">${esc((c.paras[0] || '').slice(0, 200))}…</p>${gref(n, c.n, 'קריאה ←')}</div>`; }).join('')}</div>`;
  el.querySelectorAll('input[type=checkbox]').forEach(cb => cb.onchange = () => { done[cb.dataset.c] = cb.checked; store.set(key, done); });
};

WIDGETS.balance = async (el, n) => {
  el.innerHTML = `<p class="muted small">מודל דידקטי: חסד ודין כשני כוחות, והקו האמצעי מכריע ביניהם. הוא ממחיש את רעיון ההכרעה, ואינו משחזר חשבון מתוך הספר.</p>
  <div class="slider"><label>חסד</label><input type="range" id="c" min="0" max="100" value="60"><output id="co"></output></div>
  <div class="slider"><label>גבורה (דין)</label><input type="range" id="g" min="0" max="100" value="40"><output id="go"></output></div>
  <div class="slider"><label>כוח המכריע</label><input type="range" id="k" min="0" max="100" value="50"><output id="ko"></output></div>
  <div class="balance"><i id="pt"></i></div><div class="row small muted" style="justify-content:space-between"><span>חסד</span><span>רחמים</span><span>דין</span></div>
  <p id="res" class="text"></p><h3>"מכריע" בספר</h3><div id="kw"></div>`;
  const upd = () => {
    const c = +el.querySelector('#c').value, g = +el.querySelector('#g').value, k = +el.querySelector('#k').value / 100;
    const raw = (c - g) / Math.max(1, c + g);           // -1 = all din, +1 = all chesed
    const val = raw * (1 - k);                         // the mediator pulls toward the middle
    el.querySelector('#co').textContent = c; el.querySelector('#go').textContent = g; el.querySelector('#ko').textContent = Math.round(k * 100);
    el.querySelector('#pt').style.right = `calc(${((1 - val) / 2 * 100).toFixed(1)}% - 3px)`;
    el.querySelector('#res').textContent = Math.abs(val) < .1 ? 'הכרעה מאוזנת: רחמים (תפארת).' : val > 0 ? 'ההכרעה נוטה לחסד.' : 'ההכרעה נוטה לדין.';
  };
  el.querySelectorAll('input').forEach(i => i.oninput = upd); upd();
  kwicInto(el.querySelector('#kw'), 'מכריע', [n]);
};

function lexTable(L, title) {
  return `<div class="scroll"><table><thead><tr><th>${title}</th><th>מופעים</th><th>ספירות קרובות (מספר פסקאות משותפות)</th><th>דוגמה</th></tr></thead><tbody>
  ${L.map(e => { const top = Object.entries(e.co).sort((a, b) => b[1] - a[1]).slice(0, 4); const q = e.quotes[0];
    return `<tr><th>${esc(e.label)}</th><td>${e.count}</td><td>${top.map(([k, v]) => `<span class="tag">${SEFN[k]} ${v}</span>`).join('') || '—'}</td><td class="text" style="font-size:.95rem">${q ? esc(q.q.slice(0, 220)) + ' ' + gref(q.g, q.c) : ''}</td></tr>`; }).join('')}</tbody></table></div>`;
}
const lexWidget = (key, title, note) => async (el) => {
  const lex = await load('data/lexicons.json');
  el.innerHTML = `<p class="muted small">${note}</p>${lexTable(lex[key], title)}`;
};
WIDGETS.names = lexWidget('names', 'שם', 'כל שמות הקודש בכל הספר: מספר המופעים, וליד אילו ספירות הם מופיעים באותה פסקה. כתיבי השמות בספר מגוונים (אלקים, אלדים, ידו"ד), והספירה מקורבת.');
WIDGETS.heichalot = lexWidget('heichalot', 'היכל', 'שבעת ההיכלות בשער כ"ד: מופעים וספירות קרובות. שמות כמו "רצון" ו"אהבה" הם גם מילים רגילות, ולכן הספירה כוללת רעש.');
WIDGETS.nikud = lexWidget('nikud', 'נקודה', 'שמות הנקודות בשער כ"ח והספירות שנזכרות איתם באותה פסקה.');
WIDGETS.teamim = lexWidget('teamim', 'טעם', 'שמות הטעמים בשער כ"ט והספירות שנזכרות איתם באותה פסקה.');
WIDGETS.souls = lexWidget('souls', 'חלק הנשמה', 'חלקי הנשמה בשער ל"א והספירות שנזכרות איתם באותה פסקה.');

WIDGETS.colors = async (el) => {
  const lex = await load('data/lexicons.json');
  const C = lex.colors.filter(c => c.count);
  el.innerHTML = `<p class="muted small">כל תא = מספר הפסקאות בשער י' שבהן הצבע והספירה מופיעים יחד. זו נקודת פתיחה לפלטה, לא הכרעה: אותה פסקה עשויה להביא כמה שיטות.</p>
  ${heatTable(SEF.map(k => SEFN[k]), C.map((_, i) => i), (ri, ci) => C[ci].co[SEF[ri]] || 0, (ci) => esc(C[ci].label))}
  <h3>ציטוטים לכל צבע</h3>${C.map(c => `<details><summary><b>${esc(c.label)}</b> <span class="muted small">${c.count} מופעים</span></summary><ul class="kwic">${c.quotes.map(q => `<li>${esc(q.q)} ${gref(q.g, q.c)}</li>`).join('')}</ul></details>`).join('')}`;
};

WIDGETS.kwic = async (el, n, w) => {
  el.innerHTML = `<div class="row"><input type="search" id="kq" value="${esc(w.kwic || '')}"><button id="kb">חיפוש בכל הספר</button><button class="ghost" id="kg">רק בשער ${numHeb(n)}</button></div><div id="kr"></div>`;
  const run = (only) => { const q = el.querySelector('#kq').value.trim(); if (q) kwicInto(el.querySelector('#kr'), q, only ? [n] : null); };
  el.querySelector('#kb').onclick = () => run(false); el.querySelector('#kg').onclick = () => run(true);
  run(false);
};

WIDGETS.pathsList = async (el, n) => {
  const G = await gate(n);
  const cnt = {};
  G.chapters.forEach(c => c.paras.forEach(p => (p.match(/שכל [א-ת"']+/g) || []).forEach(m => { cnt[m] = (cnt[m] || 0) + 1; })));
  const rows = Object.entries(cnt).filter(([k]) => !/שכל (ה?זה|הוא|היא|כי|של|אשר|על|ה?נקרא)$/.test(k)).sort((a, b) => b[1] - a[1]);
  el.innerHTML = `<p class="muted small">כל צירופי "שכל ___" שמופיעים בשער י"ב. מתוכם בונים את מפתח הנתיבות, ואת הרשימה צריך לאמת מול ספר יצירה.</p><div class="chips">${rows.map(([k, v]) => `<a class="chip" href="#/search?q=${encodeURIComponent(k)}">${esc(k)} <small>${v}</small></a>`).join('')}</div>`;
};

WIDGETS.fractal = async (el, n) => {
  const hue = (i) => `hsl(${(i * 36 + 10) % 360} 55% 50% / .25)`;
  el.innerHTML = `<p class="muted small">כל ספירה כלולה מכל העשר: 10 × 10 = 100 בחינות. השורה היא הספירה הכוללת, והעמודה היא הבחינה שבתוכה.</p>
  <div class="scroll"><div class="fr" style="min-width:560px"><div></div>${SEF.map(k => `<div><b>${SEFN[k]}</b></div>`).join('')}
  ${SEF.map((r, ri) => `<div><b>${SEFN[r]}</b></div>${SEF.map((c, ci) => `<div style="background:${hue(ri)};outline:${ri === ci ? '2px solid var(--accent)' : 'none'}" title="${SEFN[c]} שב${SEFN[r]}">${SEFN[c]} שב${SEFN[r]}</div>`).join('')}`).join('')}</div></div>
  <h3>"כלול" בשער</h3><div id="kw"></div>`;
  kwicInto(el.querySelector('#kw'), 'כלול', [n]);
};

WIDGETS.direction = async (el) => {
  const G = await allGates();
  const a = kwicCollect(G, /ממטה למעלה/g, 0), b = kwicCollect(G, /ממעלה למטה/g, 0);
  const gs = [...new Set([...Object.keys(a.perGate), ...Object.keys(b.perGate)])].map(Number).sort((x, y) => x - y);
  el.innerHTML = `<p class="muted small">כמה פעמים מופיע כל כיוון בכל שער. סה"כ: ממטה למעלה ${a.total}, ממעלה למטה ${b.total}.</p>
  ${heatTable(['ממטה למעלה', 'ממעלה למטה'], gs, (ri, g) => (ri ? b : a).perGate[g] || 0)}<h3>הקשרים</h3><div id="kw"></div>`;
  kwicInto(el.querySelector('#kw'), 'ממטה למעלה', [15]);
};

WIDGETS.worlds = async (el) => {
  const lex = await load('data/lexicons.json');
  const W = ['אצילות', 'בריאה', 'יצירה', 'עשיה'];
  el.innerHTML = `<p class="muted small">ארבעה עולמות × עשר ספירות = 40 צמתים. כל שורה היא עולם שלם של עשר ספירות.</p>
  <div class="scroll"><div class="fr" style="min-width:560px">${W.map((w, wi) => `<div><b>${w}</b></div>${SEF.map(k => `<div style="background:hsl(${20 + wi * 55} 50% 50% / ${0.35 - wi * 0.07})">${SEFN[k]}</div>`).join('')}`).join('')}</div></div>
  <h3>העולמות בשער ט"ז</h3>${lexTable(lex.worlds, 'עולם')}`;
};

WIDGETS.gematria = async (el) => {
  const MILUI = { 'ע"ב (יוד הי ויו הי)': 'יוד הי ויו הי', 'ס"ג (יוד הי ואו הי)': 'יוד הי ואו הי', 'מ"ה (יוד הא ואו הא)': 'יוד הא ואו הא', 'ב"ן (יוד הה וו הה)': 'יוד הה וו הה' };
  el.innerHTML = `<div class="row"><input type="text" id="gi" value="אהבה" style="font-family:var(--serif);font-size:1.3rem;width:260px"></div>
  <div id="go"></div><h3>מילויי השם בן ד'</h3><table><tbody>${Object.entries(MILUI).map(([k, v]) => `<tr><th>${k}</th><td style="font-family:var(--serif)">${v}</td><td><b>${gem(v)}</b></td></tr>`).join('')}</tbody></table>
  <p class="muted small">מילוי כל אות לפי שמה המקובל (אלף, בית, גימל…). למילויים חלופיים, כמו ה"י או ה"א, יש להקליד את המילוי ידנית.</p>`;
  const calc = () => {
    const w = onlyHeb(el.querySelector('#gi').value);
    const mil = [...w].map(c => LNAME[FIN2REG[c] || c]).join(' ');
    const eq = gem(w);
    el.querySelector('#go').innerHTML = `<table><tbody>
      <tr><th>מספר הכרחי (רגיל)</th><td><b>${eq}</b></td></tr>
      <tr><th>מספר גדול (ך=500…ץ=900)</th><td>${gemBig(w)}</td></tr>
      <tr><th>מספר קטן</th><td>${gemSmall(w)}</td></tr>
      <tr><th>מספר כולל (עם האותיות)</th><td>${eq + w.length}</td></tr>
      <tr><th>מילוי</th><td style="font-family:var(--serif)">${esc(mil)} = <b>${gem(mil)}</b></td></tr>
      <tr><th>מספר מילים בספר שערכן ${eq}</th><td id="same" class="muted">…</td></tr></tbody></table>`;
    findSame(eq).then(list => { const s = el.querySelector('#same'); if (s) s.innerHTML = list.length ? `<div class="chips">${list.slice(0, 40).map(([t, c]) => `<a class="chip" href="#/search?q=${encodeURIComponent(t)}">${esc(t)} <small>${c}</small></a>`).join('')}</div>` : '—'; });
  };
  el.querySelector('#gi').oninput = calc; calc();
};
let wordIndex = null;
async function findSame(v) {
  if (!wordIndex) {
    const G = await allGates(); const cnt = new Map();
    for (const g of G) for (const c of g.chapters) for (const p of c.paras) for (const w of p.match(/[א-ת]{2,}/g) || []) cnt.set(w, (cnt.get(w) || 0) + 1);
    wordIndex = [...cnt.entries()].map(([w, c]) => [w, c, gem(w)]);
  }
  return wordIndex.filter(x => x[2] === v && x[1] > 1).sort((a, b) => b[1] - a[1]);
}

WIDGETS.dictionary = async (el) => {
  const kin = await load('data/kinuyim.json');
  const q0 = new URLSearchParams(location.hash.split('?')[1] || '');
  el.innerHTML = `<p class="muted small">${kin.length} ערכים חולצו אוטומטית משער כ"ג. ערך שמתחיל ב"עוד נקראת" מסומן כתת-ערך. הספירות ליד כל ערך הן אלה שנזכרות בו הכי הרבה, וזה קירוב בלבד.</p>
  <div class="row"><input type="search" id="dq" placeholder="חיפוש כינוי או מילה בפירוש"><select id="dl"><option value="">כל האותיות</option>${LETTERS.map(l => `<option>${l}</option>`).join('')}</select>
  <select id="ds"><option value="">כל הספירות</option>${SEF.map(k => `<option value="${k}" ${q0.get('s') === k ? 'selected' : ''}>${SEFN[k]}</option>`).join('')}</select><label class="small"><input type="checkbox" id="dx"> חיפוש גם בגוף הפירוש</label></div>
  <p id="dc" class="muted small"></p><div id="dr"></div><div class="row"><button class="ghost" id="dm">עוד</button></div>`;
  let shown = 50, res = [];
  const render = () => {
    el.querySelector('#dr').innerHTML = res.slice(0, shown).map(e => `<div class="entry"><b>${esc(e.t)}</b> ${e.sub ? '<span class="tag s">תת-ערך</span>' : ''} ${e.s.map(k => `<span class="tag">${SEFN[k]}</span>`).join('')} ${gref(23, e.c, `ערכי ${e.l}`)}<p class="x">${esc(e.x)}</p></div>`).join('');
    el.querySelector('#dc').textContent = `${res.length} ערכים`;
    el.querySelector('#dm').style.display = res.length > shown ? '' : 'none';
  };
  const filt = () => {
    const q = el.querySelector('#dq').value.trim(), l = el.querySelector('#dl').value, s = el.querySelector('#ds').value, x = el.querySelector('#dx').checked;
    res = kin.filter(e => (!l || e.l === l) && (!s || e.s[0] === s) && (!q || e.t.includes(q) || (x && e.x.includes(q))));
    shown = 50; render();
  };
  el.querySelectorAll('input,select').forEach(i => i.oninput = filt);
  el.querySelector('#dm').onclick = () => { shown += 50; render(); };
  filt();
};

WIDGETS.shadow = async (el, n) => {
  const G = await allGates();
  const r = kwicCollect(G, /קליפ/g, 0);
  el.innerHTML = `<p class="muted small">מילים מהשורש "קליפ" בכל שער (${r.total} בכל הספר): היכן הספר עוסק בצד שכנגד.</p>
  ${bars(Object.entries(r.perGate).sort((a, b) => b[1] - a[1]).map(([g, v]) => [`שער ${numHeb(+g)}`, v, `#/way/${g}`]), { alt: true })}<h3>בשער כ"ה</h3><div id="kw"></div>`;
  kwicInto(el.querySelector('#kw'), 'קליפ', [n]);
};

WIDGETS.letters = async (el) => {
  const [lex, kin] = await Promise.all([load('data/lexicons.json'), load('data/kinuyim.json')]);
  const byL = Object.fromEntries(lex.letters.map(e => [e.label, e]));
  el.innerHTML = `<p class="muted small">לכל אות: ערך מספרי, כמה פעמים שמה נזכר בשער האותיות, הספירות שלידה וכמה ערכים יש לה במילון הכינויים.</p><div class="lettercards">${LETTERS.map(l => { const e = byL[l] || { count: 0, co: {}, quotes: [] }; const top = Object.entries(e.co).sort((a, b) => b[1] - a[1]).slice(0, 2);
    return `<div class="card"><div class="big">${l}</div><div class="small">${LNAME[l]} · ${VAL[l]}</div><div class="small muted">${e.count} אזכורים בשער</div><div>${top.map(([k]) => `<span class="tag">${SEFN[k]}</span>`).join('')}</div><div class="small"><a href="#/way/23">${kin.filter(k => k.l === l).length} כינויים</a></div>${e.quotes[0] ? gref(e.quotes[0].g, e.quotes[0].c, 'מובאה ←') : ''}</div>`; }).join('')}</div>`;
};

WIDGETS.tzeruf = async (el) => {
  const pairs = [];
  for (let i = 0; i < 22; i++) for (let j = i + 1; j < 22; j++) pairs.push(LETTERS[i] + LETTERS[j]);
  const atbash = (w) => [...w].map(c => { const i = LETTERS.indexOf(FIN2REG[c] || c); return i < 0 ? c : LETTERS[21 - i]; }).join('');
  const albam = (w) => [...w].map(c => { const i = LETTERS.indexOf(FIN2REG[c] || c); return i < 0 ? c : LETTERS[(i + 11) % 22]; }).join('');
  const achbi = (w) => [...w].map(c => { const i = LETTERS.indexOf(FIN2REG[c] || c); if (i < 0) return c; return i < 11 ? LETTERS[10 - i] : LETTERS[32 - i]; }).join('');
  const next = (w) => [...w].map(c => { const i = LETTERS.indexOf(FIN2REG[c] || c); return i < 0 ? c : LETTERS[(i + 1) % 22]; }).join('');
  const perms = (s) => s.length <= 1 ? [s] : [...new Set([...s].flatMap((c, i) => perms(s.slice(0, i) + s.slice(i + 1)).map(p => c + p)))];
  el.innerHTML = `<div class="row"><input type="text" id="ti" value="יהוה" style="font-family:var(--serif);font-size:1.3rem;width:240px"></div><div id="to"></div>
  <h3>רל"א שערים</h3><p class="muted small">כל צירופי שתי אותיות מתוך כ"ב: 22 × 21 ÷ 2 = 231.</p><div class="pairs">${pairs.map(p => `<span>${p}</span>`).join('')}</div>`;
  const run = () => {
    const w = onlyHeb(el.querySelector('#ti').value).slice(0, 12);
    const P = w.length <= 6 ? perms([...w].map(c => FIN2REG[c] || c).join('')) : [];
    const row = (k, v) => `<tr><th>${k}</th><td style="font-family:var(--serif);font-size:1.15rem">${esc(fixFinals(v))}</td><td class="muted">${gem(v)}</td></tr>`;
    el.querySelector('#to').innerHTML = `<table><tbody>${row('המילה', w)}${row('א"ת ב"ש', atbash(w))}${row('א"ל ב"ם', albam(w))}${row('א"י ב"ט', achbi(w))}${row('אות שאחריה (אב"ג)', next(w))}${row('היפוך', [...w].reverse().join(''))}</tbody></table>
    ${P.length ? `<h3>כל הצירופים (${P.length})</h3><div class="pairs">${P.map(p => `<span>${esc(fixFinals(p))}</span>`).join('')}</div>` : '<p class="muted small">צירופים מלאים מוצגים למילים של עד 6 אותיות.</p>'}`;
  };
  el.querySelector('#ti').oninput = run; run();
};

WIDGETS.calendar = async (el, n) => {
  const meta = await load('data/meta.json');
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const start0 = store.get('pr-cal-start', today.toISOString().slice(0, 10));
  const done = store.get('pr-cal-done', {});
  el.innerHTML = `<p class="muted small">פרק אחד ליום: ${meta.toc.length} ימים, בערך תשעה וחצי חודשים. תאריך ההתחלה וסימוני ההתקדמות נשמרים בדפדפן שלכם בלבד.</p>
  <div class="row"><label>התחלה: <input type="date" id="cs" value="${start0}"></label><span id="cp" class="muted small"></span></div><ul class="cal" id="cl"></ul><h3>"יכוין" בשער הכוונה</h3><div id="kw"></div>`;
  const draw = () => {
    const s = new Date(el.querySelector('#cs').value || start0); s.setHours(0, 0, 0, 0);
    const idx = Math.round((today - s) / 864e5);
    el.querySelector('#cl').innerHTML = meta.toc.map(([g, c], i) => { const d = new Date(s.getTime() + i * 864e5); const k = `${g}-${c}`;
      return `<li class="${i === idx ? 'today' : ''}" ${i === idx ? 'id="todayrow"' : ''}><input type="checkbox" data-k="${k}" ${done[k] ? 'checked' : ''}><span class="muted small" style="min-width:90px">${d.toLocaleDateString('he-IL')}</span>${gref(g, c, `שער ${numHeb(g)} · ${esc(meta.gates[g - 1].title)} · פרק ${numHeb(c)}`)}</li>`; }).join('');
    el.querySelector('#cp').textContent = `הושלמו ${Object.values(done).filter(Boolean).length} מתוך ${meta.toc.length}`;
    el.querySelectorAll('#cl input').forEach(cb => cb.onchange = () => { done[cb.dataset.k] = cb.checked; store.set('pr-cal-done', done); draw(); });
    const t = el.querySelector('#todayrow'); if (t) t.parentNode.scrollTop = t.offsetTop - t.parentNode.offsetTop - 60;
  };
  el.querySelector('#cs').onchange = (e) => { store.set('pr-cal-start', e.target.value); draw(); };
  draw();
  kwicInto(el.querySelector('#kw'), 'יכוין', [n]);
};

/* ---------- reader ---------- */
async function pageRead(g, c, q) {
  g = Math.min(32, Math.max(1, g | 0));
  const [meta, G] = await Promise.all([load('data/meta.json'), gate(g)]);
  c = Math.min(G.chapters.length, Math.max(1, c | 0));
  const ch = G.chapters[c - 1];
  const i = meta.toc.findIndex(([a, b]) => a === g && b === c);
  const prev = meta.toc[i - 1], next = meta.toc[i + 1];
  const re = q ? new RegExp(reEsc(q), 'g') : null;
  $app.innerHTML = `<div class="reader"><aside>${meta.gates.map(x => `<a href="#/read/${x.n}/1" class="${x.n === g ? 'on' : ''}">${numHeb(x.n)}. ${esc(x.title)}</a>${x.n === g ? `<div class="chs">${Array.from({ length: x.chapters }, (_, k) => `<a href="#/read/${g}/${k + 1}" class="${k + 1 === c ? 'on' : ''}">${numHeb(k + 1)}</a>`).join('')}</div>` : ''}`).join('')}</aside>
  <article><div class="small muted"><a href="#/way/${g}">דרך ${numHeb(g)}: לכלים ולנתוני השער ←</a></div>
  <h1>שער ${numHeb(g)} · ${esc(G.title)}</h1><h2 style="margin-top:0">פרק ${ch.heb}</h2>
  <div class="text">${ch.paras.map(p => `<p>${highlight(p, re)}</p>`).join('')}</div>
  <div class="pager">${prev ? `<a href="#/read/${prev[0]}/${prev[1]}">→ שער ${numHeb(prev[0])} פרק ${numHeb(prev[1])}</a>` : '<span></span>'}${next ? `<a href="#/read/${next[0]}/${next[1]}">שער ${numHeb(next[0])} פרק ${numHeb(next[1])} ←</a>` : '<span></span>'}</div></article></div>`;
  if (re) { const m = $app.querySelector('mark'); if (m) m.scrollIntoView({ block: 'center' }); } else window.scrollTo(0, 0);
}

async function pageSearch(q) {
  $app.innerHTML = `<h1>חיפוש בכל הספר</h1><div class="row"><input type="search" id="sq" value="${esc(q || '')}" placeholder="מילה או צירוף, למשל: אין סוף" style="width:min(420px,100%)"><button id="sb">חיפוש</button></div><div id="sr"></div>`;
  const go = () => { const v = $app.querySelector('#sq').value.trim(); if (v) location.hash = `#/search?q=${encodeURIComponent(v)}`; };
  $app.querySelector('#sb').onclick = go;
  $app.querySelector('#sq').onkeydown = (e) => { if (e.key === 'Enter') go(); };
  if (q) {
    const el = $app.querySelector('#sr'); el.innerHTML = '<p class="muted">מחפש…</p>';
    const res = kwicCollect(await allGates(), new RegExp(reEsc(q), 'g'), 300);
    el.innerHTML = kwicHTML(res, q).replace(/href="#\/read\/(\d+)\/(\d+)"/g, `href="#/read/$1/$2?q=${encodeURIComponent(q)}"`);
  }
}

async function pageMap() {
  const [meta, stats] = await Promise.all([load('data/meta.json'), load('data/stats.json')]);
  const gs = meta.gates.map(g => g.n);
  $app.innerHTML = `<h1>מפות הספר</h1><p class="muted">מבט על כל 32 השערים. לחיצה על מספר שער פותחת את הדרך שלו.</p>
  <h2>ספירות × שערים</h2><p class="muted small">אזכורים לכל 1,000 מילים, כך שאפשר להשוות בין שערים בגדלים שונים.</p>
  ${heatTable(SEF.map(k => SEFN[k]), gs, (ri, g) => Math.round(stats.sefByGate[g][SEF[ri]] / stats.words[g] * 1000))}
  <h2>מקורות × שערים</h2>${heatTable(stats.sources.map(s => s.name), gs, (ri, g) => stats.srcByGate[g][stats.sources[ri].key])}
  <h2>הפניות בין שערים</h2><p class="muted small">שורה = השער המפנה, עמודה = השער שאליו הוא מפנה ("כמו שביארנו בשער…").</p>
  ${heatTable(gs.map(g => `${numHeb(g)} ${meta.gates[g - 1].title}`), gs, (ri, g) => { const r = stats.refs.find(x => x[0] === ri + 1 && x[1] === g); return r ? r[2] : 0; })}
  <h2>גודל השערים</h2>${bars(meta.gates.map(g => [`${numHeb(g.n)} · ${g.title}`, g.words, `#/way/${g.n}`]))}`;
}

/* ---------- router ---------- */
async function route() {
  const h = location.hash.slice(1) || '/';
  const [path, qs] = h.split('?');
  const params = new URLSearchParams(qs || '');
  const parts = path.split('/').filter(Boolean);
  document.querySelectorAll('.top nav a').forEach(a => { const hp = a.getAttribute('href').split('/').filter(x => x !== '#'); a.classList.toggle('on', hp[0] === parts[0] && (hp[0] !== 'way' || hp[1] === parts[1])); });
  try {
    if (!parts.length) await pageHome();
    else if (parts[0] === 'plan') await pagePlan();
    else if (parts[0] === 'way') await pageWay(+parts[1]);
    else if (parts[0] === 'read') await pageRead(+parts[1] || 1, +parts[2] || 1, params.get('q'));
    else if (parts[0] === 'search') await pageSearch(params.get('q'));
    else if (parts[0] === 'map') await pageMap();
    else await pageHome();
    if (parts[0] !== 'read') window.scrollTo(0, 0);
  } catch (e) {
    $app.innerHTML = `<p class="pad">שגיאה בטעינה: ${esc(e.message)}</p>`;
  }
}
window.addEventListener('hashchange', route);

/* theme toggle */
const themeBtn = document.getElementById('theme');
const savedTheme = store.get('pr-theme', null);
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
themeBtn.onclick = () => {
  const cur = document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const nxt = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = nxt; store.set('pr-theme', nxt);
};

route();
})();
