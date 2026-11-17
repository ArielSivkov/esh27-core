(function () {
  const { esc } = BHM;
  const num = n => Number(n).toLocaleString('he');
  const d = n => n === 0 ? '<span class="muted">0</span>' : `<b style="color:${n > 0 ? '#b45309' : '#b91c1c'}">${n > 0 ? '+' : ''}${num(n)}</b>`;
  const head = '<tr><th>גרסה</th><th>אותיות</th><th>הפרש</th><th>מילים</th><th>פסוקים</th><th>הפרש</th><th>פרקים</th></tr>';
  const row = v => `<tr><td>${esc(v.version_title)}${v.translation ? ' <span class="tag">תרגום</span>' : ''}</td><td>${num(v.letters)}</td><td>${d(v.delta_letters)}</td><td>${num(v.words)}</td><td>${num(v.verses)}</td><td>${d(v.delta_verses)}</td><td>${num(v.chapters)}</td></tr>`;
  BHM.register('torahqa', async () => {
    BHM.$app.innerHTML = '<p class="muted">מחשב…</p>';
    const r = await BHM.api('/api/torahqa');
    let h = `<div class="panel"><h2>בדיקת איכות טקסט התורה</h2>
      <p class="notice">${esc(r.notes)} הספירה אוטומטית ואינה פסק הלכה.</p>
      <p class="small muted">אותיות: אותיות עבריות בלבד, ללא ניקוד, טעמים, מקף והערות בסוגריים. הנורמה המסורתית: ${num(r.std.letters)} אותיות ו-${num(r.std.verses)} פסוקים. ${r.cached ? 'מהמטמון' : 'חושב כעת'} (${esc(r.computed_at || '')}).</p></div>`;
    h += `<div class="panel"><h3>סיכום חמשת החומשים לפי גרסה</h3><table style="width:100%">${head}${r.totals.map(row).join('')}</table>` +
      (r.totals.length ? '' : '<p class="muted">אין גרסה שמכילה את כל חמשת החומשים.</p>') + '</div>';
    for (const b of r.books) {
      h += `<div class="panel"><h3>${esc(b.he_title)}</h3><p class="small muted">מסורתי: ${num(b.std_letters)} אותיות, ${num(b.std_verses)} פסוקים</p><table style="width:100%">${head}${b.versions.map(row).join('')}</table></div>`;
    }
    BHM.$app.innerHTML = h;
  });
})();
