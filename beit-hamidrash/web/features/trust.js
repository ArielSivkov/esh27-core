BHM.register('trust', async () => {
  const e = BHM.esc;
  const d = await BHM.api('/api/trust/info');
  if (!d.present) {
    BHM.$app.innerHTML = `<div class="panel"><h2>אמון ומטא-נתוני שורש</h2>
      <p class="muted">לא הוגדר קובץ root.json בצומת זה.</p></div>`;
    return;
  }
  const roles = Object.entries(d.roles || {}).map(([n, r]) =>
    `<div class="card"><b>${e(n)}</b><div class="small muted">חתימות נדרשות: ${e(r.threshold)} מתוך ${e(r.keys)}</div></div>`).join('');
  BHM.$app.innerHTML = `<div class="panel"><h2>אמון ומטא-נתוני שורש</h2>
    <div class="kpis">
      <div class="kpi"><b>${e(d.version)}</b><span>גרסה</span></div>
      <div class="kpi"><b>${e(d.keys)}</b><span>מפתחות</span></div>
    </div>
    <p>תוקף עד: ${e(d.expires)} ${d.expired ? '<span class="tag">פג תוקף</span>' : ''}</p>
    <p>${d.self_signed_ok ? 'החתימות על השורש תקינות.' : '<span class="notice">חתימות השורש אינן עומדות בסף!</span>'}</p>
    <div class="grid">${roles}</div>
    <p class="small muted">מידע טכני בלבד; אין בכך פסיקה הלכתית.</p></div>`;
});
