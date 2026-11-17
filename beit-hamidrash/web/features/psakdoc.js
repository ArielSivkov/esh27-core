(() => {
  const { api, esc, enc, $app } = BHM;
  const CSS = `
  .pd-sheet{position:relative;max-width:800px;margin:0 auto;padding:2rem;background:#fff;color:#000;border:1px solid #888;direction:rtl;font-family:serif;line-height:1.7;overflow:hidden}
  .pd-wm{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:9rem;color:rgba(200,0,0,.12);transform:rotate(-30deg);pointer-events:none;user-select:none;z-index:0}
  .pd-sheet>*:not(.pd-wm){position:relative;z-index:1}
  .pd-head{text-align:center;border-bottom:2px solid #000;margin-bottom:1rem}
  .pd-bsd{text-align:left;font-size:.9rem}
  .pd-meta{display:flex;justify-content:space-between;flex-wrap:wrap;gap:1rem;font-size:.95rem}
  .pd-sec h3{border-bottom:1px solid #888;margin-top:1.4rem}
  .pd-notice{border:2px solid #b00;color:#b00;padding:.6rem;margin:.8rem 0;font-weight:bold;text-align:center}
  .pd-src{border-right:3px solid #888;padding:.2rem .8rem;margin:.4rem 0}
  .pd-sign{display:inline-block;min-width:200px;margin:1rem;text-align:center;border-top:1px solid #000;padding-top:.3rem}
  @media print{
    nav,header,footer,.pd-noprint{display:none!important}
    body{background:#fff!important}
    .pd-sheet{border:none;max-width:none;padding:0}
    .pd-wm{color:rgba(0,0,0,.10)}
    .pd-sec{page-break-inside:avoid}
  }`;
  function css() {
    if (document.getElementById('psakdoc-style')) return;
    const s = document.createElement('style'); s.id = 'psakdoc-style'; s.textContent = CSS; document.head.appendChild(s);
  }
  BHM.register('psakdoc', async (parts) => {
    css();
    const id = parts[1];
    if (!id) { $app.innerHTML = '<div class="notice">נא לפתוח מסמך לפי מזהה טיוטה: #/psakdoc/&lt;מזהה&gt;</div>'; return; }
    let d;
    try { d = await api(`/api/psakdoc/${enc(id)}`); }
    catch (e) { $app.innerHTML = `<div class="notice">${esc(e.message || 'המסמך לא נמצא')}</div>`; return; }
    const notices = d.notices.map(n => `<div class="pd-notice">${esc(n)}</div>`).join('');
    const src = d.sources.map(s => `<div class="pd-src"><b>${esc(s.ref)}</b>${s.found
      ? s.versions.map(v => `<div class="text">${esc(v.text)} <span class="small muted">(${esc(v.he_title || '')} · ${esc(v.version_title)})</span></div>`).join('')
      : ' <span class="small muted">(המקור אינו קיים בספרייה המקומית)</span>'}</div>`).join('');
    const rev = d.reviews.map(r => `<div class="post"><div class="meta">${esc(r.by)} · ${esc(r.ts)}</div><div>${esc(r.note)}</div></div>`).join('') || '<p class="muted">אין הערות עיון.</p>';
    const sig = d.signatures.map(s => `<div class="pd-sign"><b>${esc(s.by)}</b><br>${s.decision === 'approved' ? 'מאשר' : 'דוחה'}<br><span class="small">${esc(s.ts)}</span>${s.note ? `<br><span class="small">${esc(s.note)}</span>` : ''}</div>`).join('') || '<p class="muted">טרם נחתם בידי דיין מוסמך.</p>';
    $app.innerHTML = `<p class="small pd-noprint"><a href="#/beitdin/${enc(d.id)}">חזרה לטיוטה</a> · <button class="ghost" id="pd-print">הדפסה</button></p>
    <div class="pd-sheet">${d.watermark ? `<div class="pd-wm">${esc(d.watermark)}</div>` : ''}
      <div class="pd-bsd">${esc(d.header.blessing)}</div>
      <div class="pd-head"><h1>${esc(d.header.beit_din)}</h1></div>
      <div class="pd-meta"><span>מס׳ תיק: <b>${esc(d.file_number)}</b></span><span>תאריך: ${esc(d.date.hebrew ? d.date.hebrew + ' · ' : '')}${esc(d.date.gregorian)}</span><span>סטטוס: <b>${esc(d.status_he)}</b> (${d.approvals}/${d.required})</span></div>
      ${notices}
      <div class="pd-sec"><h3>השאלה</h3><div style="white-space:pre-wrap">${esc(d.question)}</div></div>
      <div class="pd-sec"><h3>${d.approved ? 'התשובה' : 'התשובה המוצעת (טיוטה)'}</h3><div style="white-space:pre-wrap">${esc(d.answer)}</div></div>
      <div class="pd-sec"><h3>מקורות</h3>${src || '<p class="muted">אין</p>'}</div>
      <div class="pd-sec"><h3>הערות עיון</h3>${rev}</div>
      <div class="pd-sec"><h3>חתימות הדיינים</h3>${sig}</div>
    </div>`;
    const p = $app.querySelector('#pd-print'); if (p) p.onclick = () => window.print();
  });
})();
