// Compliance pages: #/policies and #/policies/<slug>. Drafts pending lawyer review.
BHM.register('policies', async (parts) => {
  const esc = BHM.esc;
  const slug = parts[1];
  try {
    if (!slug) {
      const d = await BHM.api('/api/compliance');
      BHM.$app.innerHTML = `<div class="panel"><h2>מדיניות ומסמכים משפטיים</h2>
        <div class="notice">${esc(d.disclaimer)}</div>
        <div class="grid">${d.items.map(i => `<a class="card" href="#/policies/${esc(BHM.enc(i.slug))}">
          <b>${esc(i.title)}</b><div class="muted small">${esc(d.disclaimer)}</div></a>`).join('')}</div></div>`;
      return;
    }
    const d = await BHM.api('/api/compliance/' + BHM.enc(slug));
    // d.html is produced by the server's escape-first converter
    BHM.$app.innerHTML = `<div class="panel" style="direction:rtl">
      <a href="#/policies" class="small">חזרה לרשימה</a>
      <div class="notice">${esc(d.disclaimer)}</div>
      <div class="text">${d.html}</div></div>`;
  } catch (e) {
    BHM.$app.innerHTML = `<div class="panel"><div class="notice">${esc(String(e.message || e))}</div></div>`;
  }
});
