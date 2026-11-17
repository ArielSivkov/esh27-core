// כלי לימוד: גימטריה, מילוי, אתב"ש/אלב"ם, 231 שערים
(() => {
  const LETTERS = 'אבגדהוזחטיכלמנסעפצקרשת';
  const VALS = [1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100,200,300,400];
  const FIN = { 'ך':'כ','ם':'מ','ן':'נ','ף':'פ','ץ':'צ' };
  const BIG = { 'ך':500,'ם':600,'ן':700,'ף':800,'ץ':900 };
  const NAMES = { 'א':'אלף','ב':'בית','ג':'גימל','ד':'דלת','ה':'הא','ו':'ואו','ז':'זין','ח':'חית','ט':'טית','י':'יוד','כ':'כף','ל':'למד','מ':'מם','נ':'נון','ס':'סמך','ע':'עין','פ':'פא','צ':'צדי','ק':'קוף','ר':'ריש','ש':'שין','ת':'תיו' };
  const FILL = { 'ע"ב': { 'ה':'הי','ו':'ויו' }, 'ס"ג': { 'ה':'הי','ו':'ואו' }, 'מ"ה': { 'ה':'הא','ו':'ואו' }, 'ב"ן': { 'ה':'הה','ו':'וו' } };
  const METHODS = [['standard','רגיל'],['big','גדול (סופיות 500-900)'],['small','קטן'],['ordinal','סידורי'],['kolel','עם הכולל'],['milui','מילוי (שמות האותיות)']];
  const STD = {}; const ORD = {};
  [...LETTERS].forEach((c, i) => { STD[c] = VALS[i]; ORD[c] = i + 1; });
  const base = c => FIN[c] || c;
  const norm = s => (s || '').replace(/[֑-ׇ]/g, '').replace(/[^א-ת]/g, '');
  const sum = (str, f) => [...str].reduce((a, c) => a + f(c), 0);
  const nameVal = (c, fill) => { const b = base(c); return NAMES[b] ? sum((fill && fill[b]) || NAMES[b], x => STD[x]) : 0; };
  function gem(s, m) {
    s = norm(s);
    switch (m) {
      case 'big': return sum(s, c => BIG[c] || STD[c]);
      case 'small': return sum(s, c => { const v = STD[base(c)]; return v < 10 ? v : v < 100 ? v / 10 : v / 100; });
      case 'ordinal': return sum(s, c => ORD[base(c)]);
      case 'kolel': return sum(s, c => STD[base(c)]) + s.length;
      case 'milui': return sum(s, c => nameVal(c));
      default: return sum(s, c => STD[base(c)]);
    }
  }
  const AT = {}, AL = {};
  [...LETTERS].forEach((c, i) => { AT[c] = LETTERS[21 - i]; AL[c] = LETTERS[(i + 11) % 22]; });
  const mapStr = (s, m) => [...norm(s)].map(c => m[base(c)]).join('');
  const gates = () => { const o = []; for (let i = 0; i < 22; i++) for (let j = i + 1; j < 22; j++) o.push([LETTERS[i] + LETTERS[j], VALS[i] + VALS[j]]); return o; };
  const wordsOf = t => (t || '').replace(/[֑-ׇ]/g, '').match(/[א-ת]+/g) || [];

  BHM.register('tools', async () => {
    const e = BHM.esc;
    BHM.$app.innerHTML = `
      <h2>כלי לימוד</h2>
      <div class="panel">
        <h3>מחשבון גימטריה</h3>
        <input id="tl-in" class="text" dir="rtl" placeholder="הקלד מילה או משפט" style="width:100%">
        <div id="tl-out" class="kpis" style="margin-top:10px"></div>
        <div id="tl-tr" class="small muted" style="margin-top:8px"></div>
      </div>
      <div class="panel">
        <h3>מילוי השם (יהוה)</h3>
        <div class="kpis">${Object.keys(FILL).map(k => `<div class="kpi"><b>${e(String(sum('יהוה', c => nameVal(c, FILL[k]))))}</b><div class="small muted">${e(k)}</div></div>`).join('')}</div>
      </div>
      <div class="panel">
        <h3>גימטריה של פסוק</h3>
        <div class="row"><input id="tl-ref" class="text" dir="ltr" placeholder="Genesis 1:1" style="width:260px">
        <select id="tl-m">${METHODS.map(m => `<option value="${m[0]}">${e(m[1])}</option>`).join('')}</select>
        <button id="tl-go">חשב</button></div>
        <div id="tl-ref-out" style="margin-top:10px"></div>
      </div>
      <div class="panel">
        <h3>מילים בספר בעלות אותו ערך</h3>
        <div class="row"><input id="tl-v" class="text" type="number" placeholder="ערך" style="width:100px">
        <input id="tl-book" class="text" dir="ltr" placeholder="Genesis" style="width:200px">
        <button id="tl-same">חפש</button></div>
        <div id="tl-same-out" style="margin-top:10px"></div>
      </div>
      <div class="panel">
        <h3>231 שערים</h3>
        <details><summary>הצג את כל השערים</summary>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">${gates().map(g => `<span class="tag">${e(g[0])} ${g[1]}</span>`).join('')}</div></details>
      </div>
      <p class="muted small">הכלים חישוביים בלבד ואינם פוסקים הלכה. שערי האותיות אינם תוצר בינה מלאכותית.</p>`;
    const $ = id => document.getElementById(id);
    const calc = () => {
      const s = $('tl-in').value;
      $('tl-out').innerHTML = METHODS.map(m => `<div class="kpi"><b>${e(String(gem(s, m[0])))}</b><div class="small muted">${e(m[1])}</div></div>`).join('');
      $('tl-tr').innerHTML = s.trim() ? `אתב"ש: <b>${e(mapStr(s, AT))}</b> · אלב"ם: <b>${e(mapStr(s, AL))}</b>` : '';
    };
    $('tl-in').addEventListener('input', calc); calc();
    $('tl-go').onclick = async () => {
      const out = $('tl-ref-out'); const ref = $('tl-ref').value.trim();
      if (!ref) return;
      try {
        const d = await BHM.api(`/api/tools/gematria?ref=${BHM.enc(ref)}&method=${BHM.enc($('tl-m').value)}`);
        out.innerHTML = d.segments.map(s => `<div class="card"><b dir="ltr">${e(s.ref)}</b> · סה"כ ${e(String(s.total))}<div class="small">${s.words.map(w => `<span class="tag">${e(w.word)} ${e(String(w.value))}</span>`).join(' ')}</div></div>`).join('') + `<div class="notice">סה"כ: ${e(String(d.total))}</div>`;
      } catch (x) { out.innerHTML = `<div class="notice">לא נמצא (${e(String(x.message || x))})</div>`; }
    };
    $('tl-same').onclick = async () => {
      const out = $('tl-same-out'); const v = $('tl-v').value; const b = $('tl-book').value.trim();
      if (!v || !b) return;
      try {
        const d = await BHM.api(`/api/tools/same?value=${BHM.enc(v)}&book=${BHM.enc(b)}&method=${BHM.enc($('tl-m').value)}&limit=50`);
        out.innerHTML = d.matches.length ? d.matches.map(m => `<span class="tag">${e(m.word)} <span dir="ltr">${e(m.ref)}</span></span>`).join(' ') : '<span class="muted">לא נמצאו מילים</span>';
      } catch (x) { out.innerHTML = `<div class="notice">לא נמצא (${e(String(x.message || x))})</div>`; }
    };
  });
})();
