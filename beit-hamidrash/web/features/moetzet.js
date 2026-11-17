(() => {
  const { esc, enc, api } = BHM;
  const V = { verified: ['a', 'אומת'], quote_mismatch: ['x', 'ציטוט לא תואם'], ref_missing: ['x', 'מקור לא נמצא'], url_unsupported: ['x', 'הקישור אינו תומך'], unverifiable: ['b', 'לא אומת'] };
  // geniza notice on every printed page (recommendation of the council, topic "shem")
  const st = document.createElement('style');
  st.textContent = '@media print{body::after{content:"דף זה עשוי לכלול שמות קדושים ודברי תורה. נא לנהוג בו כבוד ולגנוז, לא לזרוק.";display:block;margin-top:24px;padding-top:8px;border-top:1px solid #999;font-size:12px;text-align:center}}';
  document.head.appendChild(st);

  BHM.register('moetzet', async (parts) => {
    if (parts[1]) {
      const t = await api(`/api/moetzet/${enc(parts[1])}`);
      const pos = t.positions.map(p => {
        const [c, l] = V[p.verdict] || ['b', p.verdict];
        const q = p.corrected_quote || p.quote;
        return `<div class="post"><div class="meta"><b>${esc(p.authority)}</b> · ${esc(p.era)} <span class="tag ${c}">${esc(l)}</span>${p.kind === 'contemporary_web' ? '<span class="tag">פוסק בן זמננו</span>' : ''}</div>
          <div class="body">${esc(p.position)}</div>
          ${q ? `<div class="text" style="font-size:1rem;margin-top:4px">"${esc(q)}"</div>` : ''}
          <div class="small">${p.ref ? `<a href="#/goto/${enc(p.ref)}">${esc(p.ref)}</a>` : ''} ${p.url ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">מקור ברשת</a>` : ''}</div>
          ${p.verdict !== 'verified' && p.verify_note ? `<div class="small muted">הערת המאמת: ${esc(p.verify_note)}</div>` : ''}</div>`;
      }).join('');
      BHM.$app.innerHTML = `<p class="small"><a href="#/moetzet">מועצת חכמים</a></p><h1>${esc(t.title)}</h1><div class="notice">${esc(t.notice)}</div>
        <div class="panel"><p>${esc(t.summary)}</p></div>
        <h2>מקורות ודעות (${t.positions.length})</h2><div class="panel">${pos}</div>
        <h2>השלכות למערכת <span class="tag">הסקה, להכרעת רבנים</span></h2><div class="panel"><ul>${t.implications.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
        <h2>שאלות פתוחות</h2><div class="panel"><ul>${t.open_questions.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
        <p class="small muted">${esc(t.verification_summary || '')}</p>`;
      return;
    }
    const d = await api('/api/moetzet');
    const tot = d.totals || {};
    BHM.$app.innerHTML = `<h1>מועצת חכמים</h1><div class="notice">${esc(d.notice)}</div>
      <p>עשרה חוקרים אספו מקורות מחז"ל, ראשונים, אחרונים ופוסקי זמננו על כל תחום בעבודה. עשרה מאמתים בדקו כל ציטוט: מקור קלאסי מול הטקסט בספרייה, ופוסק בן זמננו מול קישור ברשת.</p>
      <div class="kpis"><div class="kpi"><b>${tot.verified || 0}</b>אומתו</div><div class="kpi"><b>${tot.unverifiable || 0}</b>לא אומתו (בעיקר אתרים חסומים)</div><div class="kpi"><b>${(tot.quote_mismatch || 0) + (tot.ref_missing || 0)}</b>ציטוט לא תואם</div></div>
      <div class="grid">${d.topics.map(t => `<a class="card" href="#/moetzet/${enc(t.key)}"><b>${esc(t.title)}</b><div class="small muted">${t.verified}/${t.positions} מקורות אומתו</div></a>`).join('')}</div>`;
  });
})();
