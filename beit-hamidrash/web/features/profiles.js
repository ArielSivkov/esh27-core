(() => {
  const B = window.BHM, esc = B.esc, enc = B.enc;
  const KIND = { commentary: 'פירושים', article: 'מאמרים', reply: 'תגובות', sheet: 'דפי מקורות', psak_draft: 'טיוטות (בית הדין)' };
  const me = async () => {
    const sel = document.getElementById('me'); const us = await B.api('/api/users');
    return us.find(u => u.user === (sel && sel.value)) || null;
  };
  const roleTags = (rs) => rs.map(r => `<span class="tag b">${esc(B.META.roles[r] || r)}</span>`).join(' ');

  async function people() {
    const ps = await B.api('/api/profiles');
    B.$app.innerHTML = `<h1>אנשים</h1><div class="grid">${ps.map(p => `<a class="card" href="#/profile/${enc(p.pubkey)}"><b>${esc(p.name)}</b> ${roleTags(p.roles)}
      <div class="muted small">${p.posts} פרסומים · ${p.endorsements} הסכמות · ${p.followers} עוקבים · ${p.following} במעקב</div>
      <div class="muted small" dir="ltr">${esc(p.fingerprint)}</div></a>`).join('') || '<p class="muted">אין משתמשים.</p>'}</div>`;
  }

  async function profile(parts) {
    const pk = parts[1];
    const [p, feed, u] = await Promise.all([B.api(`/api/profiles/${enc(pk)}`), B.api(`/api/profiles/${enc(pk)}/feed`), me()]);
    const mine = u && u.pubkey === pk;
    const iFollow = u && p.followers.some(f => f.pubkey === u.pubkey);
    const list = (xs) => xs.map(x => `<a class="tag" href="#/profile/${enc(x.pubkey)}">${esc(x.name)}</a>`).join(' ') || '<span class="muted small">אין</span>';
    B.$app.innerHTML = `<p class="small"><a href="#/people">אנשים</a></p>
    <h1>${esc(p.name)} ${roleTags(p.roles)}</h1>
    <p class="muted small" dir="ltr">${esc(p.fingerprint)}</p>${p.bio ? `<p>${esc(p.bio)}</p>` : ''}
    ${u && !mine ? `<div class="row"><button id="fl" class="${iFollow ? 'ghost' : ''}">${iFollow ? 'ביטול מעקב' : 'מעקב'}</button><span class="small muted">בשם ${esc(u.name)}</span></div>` : ''}
    <div class="kpis"><div class="kpi"><b>${p.posts}</b>פרסומים</div><div class="kpi"><b>${p.endorsements_received}</b>הסכמות שהתקבלו${p.scholar_endorsements_received ? ` (${p.scholar_endorsements_received} של ת"ח)` : ''}</div><div class="kpi"><b>${p.followers_count}</b>עוקבים</div><div class="kpi"><b>${p.following_count}</b>במעקב</div></div>
    <div class="panel"><h3>פרסומים לפי סוג</h3>${Object.entries(p.posts_by_kind).map(([k, n]) => `<span class="tag">${esc(KIND[k] || k)}: ${n}</span>`).join(' ') || '<span class="muted">אין</span>'}</div>
    <div class="panel"><h3>עוקבים</h3>${list(p.followers)}<h3>במעקב</h3>${list(p.following)}</div>
    <h2>מה חדש אצל מי ש${esc(p.name)} עוקב אחריהם</h2><div class="panel">${feed.map(e => B.postHTML(e)).join('') || '<p class="muted">אין פרסומים.</p>'}</div>`;
    B.wirePosts(B.$app, () => profile(parts));
    const fl = B.$app.querySelector('#fl');
    if (fl) fl.onclick = async () => {
      try { await B.post({ kind: iFollow ? 'unfollow' : 'follow', body: { subject: pk } }); profile(parts); } catch (e) { alert(e.message); }
    };
  }

  B.register('people', people);
  B.register('profile', profile);
})();
