(function () {
  const { esc, api } = BHM;
  const TIERS = { certain: 'שכבה A (בוודאות מותר)', conditional: 'שכבה B (בתנאים)' };
  const n = (x) => esc(Number(x || 0).toLocaleString('he-IL'));
  const mb = (b) => b >= 1073741824 ? (b / 1073741824).toFixed(2) + ' GB' : (b / 1048576).toFixed(1) + ' MB';
  const kpi = (l, v) => `<div class="kpi"><b>${v}</b><span class="muted small">${esc(l)}</span></div>`;
  const table = (heads, rows) => `<table style="width:100%;border-collapse:collapse"><thead><tr>${heads.map(h => `<th style="text-align:start;padding:4px 8px">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.length ? rows.map(r => `<tr>${r.map(c => `<td style="padding:4px 8px;border-top:1px solid var(--line)">${c}</td>`).join('')}</tr>`).join('') : `<tr><td class="muted" colspan="${heads.length}">אין נתונים</td></tr>`}</tbody></table>`;
  const kv = (o, f) => Object.entries(o || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => [esc(f ? f(k) : k), n(v)]);

  BHM.register('admin', async () => {
    BHM.$app.innerHTML = '<p class="muted">טוען...</p>';
    let s;
    try { s = await api('/api/admin/stats'); } catch (e) { BHM.$app.innerHTML = `<div class="notice">${esc(String(e.message || e))}</div>`; return; }
    const kinds = (BHM.META && BHM.META.kinds) || {};
    BHM.$app.innerHTML = `
      <h2>לוח בקרה של המחשב</h2>
      <p class="muted small">לקריאה בלבד. הנתונים נשמרים בזיכרון עד דקה${s.generated_at ? ' · נוצר ' + esc(s.generated_at) : ''}.</p>
      <div class="kpis">
        ${kpi('גרסאות', n(s.versions))}${kpi('קטעי טקסט', n(s.segments))}${kpi('ספרים', n(s.books))}
        ${kpi('אירועים', n(s.events))}${kpi('כותבים', n(s.authors))}${kpi('תוכן מוסתר', n(s.hidden))}
        ${kpi('חבילות שיובאו', n(s.imported_bundles_count))}${kpi('גודל מסד הנתונים', esc(mb(s.db_size_bytes)))}
      </div>
      <div class="grid">
        <div class="panel"><h3>גרסאות לפי שכבה</h3>${table(['שכבה', 'כמות'], kv(s.versions_by_tier, k => TIERS[k] || k))}</div>
        <div class="panel"><h3>אירועים לפי סוג</h3>${table(['סוג', 'כמות'], kv(s.events_by_kind, k => kinds[k] || k))}</div>
        <div class="panel"><h3>יומן משפטי לפי החלטה</h3>${table(['החלטה', 'כמות'], kv(s.legal_log))}</div>
      </div>
      <div class="panel"><h3>רשויות מהימנות</h3>${table(['שם', 'טביעת אצבע', 'נוספה'], s.trusted_authorities.map(a => [esc(a.name), `<code dir="ltr">${esc(a.fingerprint)}</code>`, esc(a.added_at)]))}</div>
      <div class="panel"><h3>חבילות שיובאו</h3>${table(['מזהה', 'רשות', 'יובאה', 'אירועים', 'גרסאות'], s.imported_bundles.map(b => [`<code dir="ltr">${esc(b.id.slice(0, 12))}</code>`, `<code dir="ltr">${esc(b.authority.slice(0, 12))}</code>`, esc(b.imported_at), n(b.events), n(b.versions)]))}</div>
      <div class="panel"><h3>10 הספרים עם הכי הרבה פירושים</h3>${table(['ספר', 'פירושים'], s.top_books_by_commentary.map(b => [esc(b.he_title || b.book), n(b.count)]))}</div>`;
  });
})();
