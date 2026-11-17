BHM.register('envelope', async () => {
  const i = await BHM.api('/api/envelope/info');
  BHM.$app.innerHTML = `<h1>מעטפת תוכן (פרוטוקול v2)</h1><div class="panel"><p>${BHM.esc(i.summary)}</p>
  <p class="muted small">שדות חתומים: ${i.signed_fields.map(f => `<span class="tag">${BHM.esc(f)}</span>`).join(' ')}</p>
  <p class="notice small">${BHM.esc(i.note)}</p></div>`;
});
