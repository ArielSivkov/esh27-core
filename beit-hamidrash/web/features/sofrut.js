(function () {
  const { esc, enc, api } = BHM;
  const num = n => Number(n).toLocaleString('he');
  const link = ref => `<a href="#/goto/${enc(ref)}">${esc(ref)}</a>`;
  const BOOK_HE = { Genesis: 'בראשית', Exodus: 'שמות', Leviticus: 'ויקרא', Numbers: 'במדבר', Deuteronomy: 'דברים' };
  const KIND = { open: 'פתוחה (פ)', closed: 'סתומה (ס)' };
  const TYPE = { kind_differs: 'סוג שונה', only_masorah: 'רק במסורה', only_leningrad: 'רק בתגיות' };
  const DIG = { yes: ['a', 'אפשר לבדוק (כעזר)'], partial: ['b', 'חלקית'], no: ['x', 'אי אפשר דיגיטלית'] };
  const delta = n => n === 0 ? '<span class="muted">0</span>' : `<b style="color:${n > 0 ? 'var(--warn)' : 'var(--accent)'}">${n > 0 ? '+' : ''}${num(n)}</b>`;
  const sofrutNotice = d => `<div class="notice">${esc(d)}</div>`;

  if (!document.getElementById('sofrut-css')) {
    const st = document.createElement('style');
    st.id = 'sofrut-css';
    st.textContent = `
      .sf-tabs{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
      .sf-tabs a{padding:4px 14px;border-radius:99px;background:var(--surface-2);color:var(--ink);text-decoration:none}
      .sf-tabs a.on{background:var(--accent);color:#fff}
      .sf-law h3{margin:.1em 0 .3em}
      .sf-views{margin:.3em 0;padding-inline-start:1.2em}
      .sf-views li{margin:.25em 0}
      .sf-src a{margin-inline-end:10px}
      .sf-miss{color:var(--warn);font-weight:600}
      .sf-box{overflow-x:auto;border:1px solid var(--line);border-radius:10px;padding:8px;background:var(--surface)}
      .sf-song{min-width:720px;direction:rtl;font-family:var(--serif);font-size:clamp(11px,1.5vw,17px);line-height:1.45}
      .sf-line{display:flex;align-items:stretch;margin:2px 0}
      .sf-n{flex:0 0 2.4em;color:var(--muted);font:.68rem var(--sans);text-align:center;align-self:center}
      .sf-body{flex:1;display:flex;direction:rtl;min-width:0}
      .sf-seg{display:flex;justify-content:space-between;gap:.35em;white-space:nowrap;overflow:hidden;min-width:0;background:var(--accent-soft);border-radius:3px;padding:0 5px}
      .sf-gap{background:repeating-linear-gradient(45deg,transparent 0 4px,var(--line) 4px 5px)}
      .sf-v{font:.62rem var(--sans);margin-inline-end:2px;vertical-align:super;text-decoration:none}
      .sf-bad .sf-n{color:var(--warn)}
      .sf-frame{font:.8rem var(--sans);color:var(--muted);margin:6px 0}
      .sf-legend span{display:inline-block;width:2.2em;height:.9em;vertical-align:middle;margin-inline-end:4px}
    `;
    document.head.appendChild(st);
  }

  const tabsHtml = (cur) => `<div class="sf-tabs">${[['parashiyot', 'פרשיות פתוחות וסתומות'], ['laws', 'רשימת ההלכות'], ['shirot', 'שירת הים והאזינו']]
    .map(([k, t]) => `<a href="#/sofrut${k === 'parashiyot' ? '' : '/' + k}" class="${k === cur ? 'on' : ''}">${esc(t)}</a>`).join('')}</div>`;

  const head = (cur, disclaimer) => `<h1>הלכות סת״ם</h1>${sofrutNotice(disclaimer)}${tabsHtml(cur)}`;

  // ---------------------------------------------------------------- parashiyot
  async function pageParashiyot() {
    BHM.$app.innerHTML = '<p class="muted">מחשב…</p>';
    const [r, ram] = await Promise.all([api('/api/sofrut/parashiyot'), api('/api/sofrut/rambam-sections')]);
    let h = head('parashiyot', r.disclaimer);
    if (!r.available) { BHM.$app.innerHTML = h + '<p>מהדורות המקרא עם סימוני פרשיות אינן בספרייה.</p>'; return; }
    const t = r.traditional;
    h += `<div class="panel"><h2>סך הפרשיות</h2>
      <p class="small muted">${ram.found ? `רשימת הרמב״ם עצמו נמצאה בספרייה: ${link(ram.ref)}` : `רשימת הרמב״ם (${esc(ram.ref)}) <b>לא נמצאה</b> בספרייה: ${esc(ram.reason || '')}. המנין המסורתי להלן הוא מנין מקובל ולא נקרא מהספרייה.`}
      ${esc(t.note)}</p>
      <table><tr><th>מקור</th><th>פתוחות</th><th>סתומות</th><th>סך הכול</th><th>הפרש פתוחות</th><th>הפרש סתומות</th><th>הפרש כולל</th><th>בתוך פסוק</th></tr>
      <tr><td><b>מנין מסורתי</b> (${esc(t.source)})</td><td>${num(t.open)}</td><td>${num(t.closed)}</td><td>${num(t.total)}</td><td></td><td></td><td></td><td></td></tr>
      ${r.versions.filter(v => v.present).map(v => `<tr><td>${esc(v.version_title)}${v.complete ? '' : ' <span class="tag x">חלקי</span>'}</td><td>${num(v.totals.open)}</td><td>${num(v.totals.closed)}</td><td>${num(v.totals.total)}</td><td>${delta(v.totals.delta_open)}</td><td>${delta(v.totals.delta_closed)}</td><td>${delta(v.totals.delta_total)}</td><td>${num(v.totals.mid_verse)}</td></tr>`).join('')}</table>
      ${r.notes.map(n => `<p class="small muted">${esc(n)}</p>`).join('')}
      <p class="small muted">${r.cached ? 'מהמטמון' : 'חושב כעת'} (${esc(r.computed_at || '')})</p></div>`;
    // per-book table
    const vs = r.versions.filter(v => v.present);
    const byBook = {};
    vs.forEach(v => v.books.forEach(b => { (byBook[b.title] = byBook[b.title] || {})[v.key] = b; }));
    const stated = {};
    (ram.books || []).forEach(b => { stated[b.title] = b.stated; });
    const cell = (o, c) => o == null ? '<td class="muted">-</td>' : `<td>${num(o)} / ${num(c)} / <b>${num(o + c)}</b></td>`;
    h += `<div class="panel"><h2>לפי ספר (פתוחות / סתומות / סך הכול)</h2><div style="overflow-x:auto"><table><tr><th>ספר</th><th>הרמב״ם (מנין בטקסט)</th>${vs.map(v => `<th>${esc(v.version_title)}</th>`).join('')}</tr>
      ${Object.keys(BOOK_HE).filter(b => byBook[b] || stated[b]).map(b => {
        const s = stated[b];
        return `<tr><td>${esc(BOOK_HE[b])}</td>${s ? cell(s.open, s.closed) : '<td class="muted">-</td>'}${vs.map(v => { const x = (byBook[b] || {})[v.key]; return x ? cell(x.open, x.closed) : '<td class="muted">-</td>'; }).join('')}</tr>`;
      }).join('')}</table></div></div>`;
    // Rambam groups
    if (ram.found) {
      h += `<div class="panel"><h2>רשימת הרמב״ם (הלכות ספר תורה ח:ד)</h2><p class="small muted">${esc(ram.note)}${ram.sum_matches_stated_total ? ' סכום מנייני הספרים שווה למנין הכולל שהרמב״ם כותב.' : ''}</p>
        ${ram.books.map(b => `<details><summary><b>${esc(b.he_title)}</b>: ${num(b.stated.open)} פתוחות, ${num(b.stated.closed)} סתומות, ${num(b.stated.total)} בסך הכול (${num(b.parsed.groups)} קבוצות בטקסט)</summary>
          <table><tr><th>סוג</th><th>מספר</th><th>פתיחות (כלשון הרמב״ם)</th></tr>${b.groups.map(g => `<tr><td>${esc(KIND[g.kind])}</td><td>${g.count == null ? '<span class="muted">לא צוין</span>' : num(g.count)}</td><td>${esc(g.incipits)}</td></tr>`).join('')}</table></details>`).join('')}</div>`;
    } else {
      h += `<div class="panel"><h2>רשימת הרמב״ם</h2><p>הרשימה לא נמצאה במהדורה שבספרייה: ${esc(ram.reason || '')}</p></div>`;
    }
    // diff
    const d = r.diff;
    h += `<div class="panel"><h2>הבדלים בין שתי המהדורות (${num(d.count)} מקומות)</h2>
      <p class="small muted">מקומות שבהם המסורה והתגיות לא מסכימות: סוג שונה (${num(d.by_type.kind_differs || 0)}), פרשה רק במסורה (${num(d.by_type.only_masorah || 0)}), פרשה רק בתגיות (${num(d.by_type.only_leningrad || 0)}).</p>
      <div class="row"><select id="sf-book"><option value="">כל הספרים</option>${Object.keys(BOOK_HE).map(b => `<option value="${esc(b)}">${esc(BOOK_HE[b])} (${num(d.by_book[b] || 0)})</option>`).join('')}</select>
      <select id="sf-type"><option value="">כל הסוגים</option>${Object.keys(TYPE).map(k => `<option value="${k}">${esc(TYPE[k])}</option>`).join('')}</select></div>
      <div style="overflow-x:auto"><table id="sf-diff"></table></div></div>`;
    BHM.$app.innerHTML = h;
    const draw = () => {
      const b = BHM.$app.querySelector('#sf-book').value, ty = BHM.$app.querySelector('#sf-type').value;
      const rows = d.rows.filter(x => (!b || x.book === b) && (!ty || x.type === ty));
      BHM.$app.querySelector('#sf-diff').innerHTML = `<tr><th>ספר</th><th>פסוק</th><th>המסורה</th><th>התגיות</th><th>סוג</th></tr>` +
        rows.map(x => `<tr><td>${esc(BOOK_HE[x.book])}</td><td>${link(x.ref)}${x.slot !== 'end' ? ' <span class="tag">בתוך הפסוק</span>' : ''}</td><td>${x.masorah ? esc(KIND[x.masorah]) : '<span class="muted">אין</span>'}</td><td>${x.leningrad ? esc(KIND[x.leningrad]) : '<span class="muted">אין</span>'}</td><td><span class="tag ${x.type === 'kind_differs' ? 'b' : 'x'}">${esc(TYPE[x.type])}</span></td></tr>`).join('') +
        (rows.length ? '' : '<tr><td colspan="5" class="muted">אין</td></tr>');
    };
    BHM.$app.querySelector('#sf-book').onchange = draw;
    BHM.$app.querySelector('#sf-type').onchange = draw;
    draw();
  }

  // ---------------------------------------------------------------- laws
  async function pageLaws() {
    BHM.$app.innerHTML = '<p class="muted">טוען…</p>';
    const r = await api('/api/sofrut/laws');
    let h = head('laws', r.disclaimer);
    h += `<p class="small muted">${esc(r.note)}</p>
      <div class="row"><label class="small">סינון לפי בדיקה דיגיטלית:</label><select id="sf-dig"><option value="">הכול</option>${Object.entries(r.digital_levels).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
      ${r.all_refs_exist ? '' : `<div class="notice">מקורות שלא נמצאו בספרייה: ${r.missing_refs.map(esc).join(' · ')}</div>`}<div id="sf-laws"></div>`;
    h += `<div class="panel"><h2>עשרים הפוסלים לפי הרמב״ם (${link('Mishneh Torah, Tefillin, Mezuzah and the Torah Scroll 10:1')})</h2>
      ${r.rambam_20.length ? `<table><tr><th>#</th><th>הפוסל</th><th>בדיקה דיגיטלית</th></tr>${r.rambam_20.map(i => `<tr><td>${num(i.n)}</td><td>${esc(i.text)}${i.tail ? `<div class="small muted">${esc(i.tail)}</div>` : ''}</td><td><span class="tag ${DIG[i.digital.level][0]}">${esc(DIG[i.digital.level][1])}</span> <span class="small muted">${esc(i.digital.text)}</span></td></tr>`).join('')}</table>` : '<p class="muted">הרשימה לא נמצאה בספרייה.</p>'}</div>`;
    BHM.$app.innerHTML = h;
    const draw = () => {
      const f = BHM.$app.querySelector('#sf-dig').value;
      BHM.$app.querySelector('#sf-laws').innerHTML = r.laws.filter(l => !f || l.digital.level === f).map(l => `<div class="panel sf-law" id="law-${esc(l.id)}">
        <h3>${esc(l.title)} <span class="tag ${l.level === 'מעכב' ? 'x' : 'b'}">${esc(l.level)}</span> <span class="tag ${DIG[l.digital.level][0]}">${esc(DIG[l.digital.level][1])}</span></h3>
        <p>${esc(l.summary)}</p>
        <p class="small"><b>רלוונטיות דיגיטלית:</b> ${esc(l.digital.text)}</p>
        <div class="sf-src small"><b>מקורות:</b> ${l.sources.map(s => s.exists ? `<a href="#/goto/${enc(s.ref)}" title="${esc(s.excerpt || '')}">${esc(s.ref)}</a>` : `<span class="sf-miss">${esc(s.ref)} (חסר בספרייה)</span>`).join('')}</div>
        <details><summary>דעות הפוסקים (${num(l.views.length)})</summary><ul class="sf-views">${l.views.map(v => `<li><b>${esc(v.who)}:</b> ${esc(v.gist)} ${v.ref ? (v.exists ? `<a class="small" href="#/goto/${enc(v.ref)}">[מקור]</a>` : '<span class="sf-miss small">[מקור חסר בספרייה]</span>') : ''}</li>`).join('')}</ul></details></div>`).join('') || '<p class="muted">אין.</p>';
    };
    BHM.$app.querySelector('#sf-dig').onchange = draw;
    draw();
  }

  // ---------------------------------------------------------------- shirot
  const verseNo = ref => String(ref).split(':').pop();
  function segHtml(seg, widthPct) {
    const words = seg.words.map((w, i) => {
      const m = seg.marks.find(x => x.i === i);
      return `<span>${m ? `<a class="sf-v" href="#/goto/${enc(m.ref)}" title="${esc(m.ref)}">${esc(verseNo(m.ref))}</a>` : ''}${esc(w)}</span>`;
    }).join('');
    return `<div class="sf-seg" style="width:${widthPct}%" title="${esc(seg.words.join(' '))}">${words}</div>`;
  }
  function lineHtml(l) {
    const g = l.segments.length - 1;
    let body;
    if (g === 0) body = segHtml(l.segments[0], 100);
    else if (g === 1) body = segHtml(l.segments[0], 44) + '<div class="sf-gap" style="width:12%"></div>' + segHtml(l.segments[1], 44);
    else body = segHtml(l.segments[0], 27) + '<div class="sf-gap" style="width:6%"></div>' + segHtml(l.segments[1], 34) + '<div class="sf-gap" style="width:6%"></div>' + segHtml(l.segments[2], 27);
    return `<div class="sf-line ${l.opener_match === false ? 'sf-bad' : ''}"><div class="sf-n">${esc(l.n)}</div><div class="sf-body">${body}</div></div>`;
  }
  const frameHtml = (f, label) => `<div class="sf-frame">${esc(label)}: ${f.map(esc).join(' · ')}</div>`;

  async function pageShirot() {
    BHM.$app.innerHTML = '<p class="muted">מחשב…</p>';
    const r = await api('/api/sofrut/shirot');
    let h = head('shirot', r.disclaimer);
    h += `<div class="notice">${esc(r.illustration)}</div>
      <p class="small muted">החלוקה לשיטין נגזרת מרשימות פתיחות השיטין שבמקורות (הרמב״ם ח:ד, מסכת סופרים יב) ומוצמדת לטקסט הפסוקים שבספרייה, בלי ניקוד, כפי שנכתב בספר תורה. רוחב הריוחים ומקומם בתוך השיטה משוערים. מספר קטן הוא תחילת פסוק (לחיצה פותחת אותו). שיטה מסומנת באדום: פתיחת השיטה לא הותאמה בבטחון לנוסח.
      <span class="sf-legend"><span class="sf-gap" style="border:1px solid var(--line)"></span>ריוח</span> ${r.cached ? 'מהמטמון' : 'חושב כעת'}.</p>`;
    if (!r.available) { BHM.$app.innerHTML = h + '<p>הטקסט של שמות טו ודברים לב, או רשימות הפתיחות במקורות, אינם בספרייה.</p>'; return; }
    for (const [key, fr] of [['yam', 'yam'], ['haazinu', 'haazinu']]) {
      const d = r[key];
      if (!d) { h += `<div class="panel"><h2>${key === 'yam' ? 'שירת הים' : 'האזינו'}</h2><p class="muted">אין מספיק נתונים בספרייה (הטקסט או רשימת הפתיחות).</p></div>`; continue; }
      h += `<div class="panel"><h2>${esc(d.title)} <span class="small muted">${link(d.range.split('-')[0])}–${esc(d.range.split('-')[1])}</span></h2>
        <p><span class="tag b">${esc(d.form)}</span> ${num(d.line_count)} שיטין${d.stated_lines ? ` (הרמב״ם: ${num(d.stated_lines)})` : ''} · ${num(d.words)} מילים · ${esc(d.version)}</p>
        <p class="small">${esc(d.gap_rule)}</p>${d.openers_note ? `<p class="small muted">${esc(d.openers_note)}</p>` : ''}
        <p class="small muted">מקורות: ${d.rule_sources.map(link).join(' · ')}; פתיחות השיטין: ${link(d.openers_source)}. ${d.soferim_vs_rambam ? `פתיחות מסכת סופרים (יב:ט) מול רשימת הרמב״ם: ${num(d.soferim_vs_rambam.soferim_openers)} מול ${num(d.soferim_vs_rambam.rambam_openers)}.` : ''}</p>
        ${frameHtml(r.frame[fr].above, `${r.frame[fr].above.length} שיטין למעלה (תחילת השיטות)`)}
        <div class="sf-box"><div class="sf-song">${d.lines.map(lineHtml).join('')}</div></div>
        ${frameHtml(r.frame[fr].below, `${r.frame[fr].below.length} שיטין למטה (תחילת השיטות)`)}
        <p class="small muted">${esc(d.note)}</p></div>`;
    }
    BHM.$app.innerHTML = h;
  }

  BHM.register('sofrut', async (parts) => {
    const tab = parts[1] || 'parashiyot';
    if (tab === 'laws') return pageLaws();
    if (tab === 'shirot') return pageShirot();
    return pageParashiyot();
  });
})();
