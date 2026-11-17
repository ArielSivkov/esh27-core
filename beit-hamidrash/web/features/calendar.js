(() => {
  const { api, esc, enc, register } = window.BHM;
  const todayIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  const shift = (iso, n) => { const [y, m, d] = iso.split('-').map(Number); return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10); };
  let dia = 0; try { dia = localStorage.getItem('bhm-cal-dia') === '1' ? 1 : 0; } catch { }

  register('calendar', async (parts) => {
    const date = /^\d{4}-\d{2}-\d{2}$/.test(parts[1] || '') ? parts[1] : todayIso();
    const w = await api(`/api/calendar/week?diaspora=${dia}&date=${enc(date)}`);
    const p = w.parasha;
    const parasha = p.he
      ? `<h2>פרשת השבוע: ${esc(p.he)} <span class="muted small">${esc(p.en)}</span></h2>
         <p>${p.ranges.map(r => `<a href="#/goto/${enc(r.replace(/-[\d:]+$/, ''))}">${esc(r)}</a>`).join(' · ')}</p>`
      : `<h2>שבת חג: ${esc(p.holiday)}</h2><p class="muted">אין פרשת שבוע בשבת זו.</p>`;
    const days = w.days.map(d => `<div class="card" style="${d.date === date ? 'outline:2px solid currentColor' : ''}">
      <b>${esc(d.weekday_he)}</b> <span class="tag${d.is_shabbat ? ' a' : ''}">${esc(d.hebrew.text)}</span>
      <div class="muted small">${esc(d.date)}</div>
      <div style="margin-top:.4em">פרק יומי: <a href="#/goto/${enc(d.daily.goto)}">${esc(d.daily.ref_he)}</a>
        <div class="muted small">${esc(d.daily.ref)}${d.daily.in_library ? '' : ' · לא בספרייה המקומית'} · יום ${esc(d.daily.day_index)}/${esc(d.daily.of)}</div></div></div>`).join('');
    window.BHM.$app.innerHTML = `<h1>לוח לימוד</h1>
      <div class="row"><a href="#/calendar/${shift(w.start, -7)}">« שבוע קודם</a> <a href="#/calendar">השבוע</a> <a href="#/calendar/${shift(w.start, 7)}">שבוע הבא »</a>
        <label class="small"><input type="checkbox" id="cal-dia" ${dia ? 'checked' : ''}> חוץ לארץ</label>
        <span class="muted small">לוח: ${dia ? 'חוץ לארץ' : 'ארץ ישראל'}</span></div>
      <div class="panel">${parasha}</div>
      <div class="grid">${days}</div>
      <div class="notice">${esc(w.note)}</div>`;
    window.BHM.$app.querySelector('#cal-dia').onchange = (e) => { dia = e.target.checked ? 1 : 0; try { localStorage.setItem('bhm-cal-dia', String(dia)); } catch { } location.reload(); };
  });
})();
