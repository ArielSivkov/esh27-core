/* ESH27 Lab — client app (vanilla JS, no dependencies besides optional KaTeX). */
(function () {
  'use strict';

  var DATA = {};
  try { DATA = JSON.parse(document.getElementById('lab-data').textContent || '{}'); } catch (e) { DATA = {}; }
  var I18N = DATA.i18n || { he: {}, en: {} };
  var goals = DATA.goals || [];
  var proofs = DATA.creative_proofs || [];
  var tools = DATA.tools || [];
  var wisdom = DATA.wisdom_projects || [];
  var ledger = DATA.ledger || [];
  var news = DATA.news || [];
  var meta = DATA.meta || {};

  var TIERS = ['A-Moonshot', 'B-Famous-open', 'C-Tractable', 'D-Formalization', 'P-Physics'];

  /* ---------- storage (may be unavailable) ---------- */
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  var lang = store.get('esh27.lang') === 'en' ? 'en' : 'he';

  /* ---------- helpers ---------- */
  function t(key, vars) {
    var s = (I18N[lang] && I18N[lang][key] != null) ? I18N[lang][key]
      : (I18N.he && I18N.he[key] != null ? I18N.he[key] : key);
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function $(id) { return document.getElementById(id); }
  function num(v) { var n = parseFloat(v); return isFinite(n) ? n : 0; }
  function clamp(n) { return Math.max(0, Math.min(100, n)); }
  function uniq(arr) { return arr.filter(function (v, i, a) { return v && a.indexOf(v) === i; }).sort(); }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : ''; }
  function linkify(s) {
    // escape, then turn bare URLs into links (refs/citations)
    return esc(s).replace(/(https?:\/\/[^\s<;,)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
  }
  function tierKey(raw) {
    raw = String(raw || '').trim();
    if (TIERS.indexOf(raw) >= 0) return raw;
    var c = raw.charAt(0).toUpperCase();
    for (var i = 0; i < TIERS.length; i++) if (TIERS[i].charAt(0) === c) return TIERS[i];
    return raw;
  }
  function tierClass(raw) { return 'tier-' + tierKey(raw).charAt(0); }
  function tierName(raw) { var k = tierKey(raw); var s = t('tier.' + k); return s === 'tier.' + k ? raw : s; }
  function statusClass(s) {
    s = String(s || '').toLowerCase();
    if (/(done|proved|verified|complete|closed|solved)/.test(s)) return 'st-done';
    if (/(block|stuck|abandon|fail)/.test(s)) return 'st-blocked';
    if (/(progress|active|attack|working|running|formaliz|literature|survey)/.test(s)) return 'st-active';
    return 'st-wait';
  }
  function levelOf(v) {
    var m = String(v == null ? '' : v).toUpperCase().match(/L?\s*([0-4])/);
    return m ? 'L' + m[1] : '';
  }
  function bar(p) {
    p = clamp(num(p));
    var txt = (Math.round(p * 10) / 10) + '%';
    return '<div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + p +
      '" aria-label="' + esc(t('col.progress')) + ' ' + txt + '"><div class="bar-track"><div class="bar-fill" style="--p:' + p +
      '%"></div></div><span class="bar-num">' + txt + '</span></div>';
  }
  function typeset(el) {
    if (!el || !window.renderMathInElement) return;
    try {
      window.renderMathInElement(el, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '\\[', right: '\\]', display: true },
          { left: '\\(', right: '\\)', display: false },
          { left: '$', right: '$', display: false }
        ],
        ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option', 'input', 'select'],
        throwOnError: false
      });
    } catch (e) { /* math stays as source text */ }
  }

  /* ---------- static text ---------- */
  function applyStatic() {
    var html = document.documentElement;
    html.lang = lang;
    html.dir = lang === 'he' ? 'rtl' : 'ltr';
    document.title = t('meta.title');
    document.querySelectorAll('[data-i18n]').forEach(function (el) { el.innerHTML = t(el.getAttribute('data-i18n')); });
    document.querySelectorAll('[data-i18n-ph]').forEach(function (el) { el.placeholder = t(el.getAttribute('data-i18n-ph')); });
    document.querySelectorAll('[data-i18n-aria]').forEach(function (el) { el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria'))); });
    $('langBtn').lang = lang === 'he' ? 'en' : 'he';
    $('nav').setAttribute('aria-label', lang === 'he' ? 'ניווט ראשי' : 'Main navigation');
    var built = meta.built_at ? t('footer.built', { date: meta.built_at }) : '';
    $('builtAt').textContent = built;
    $('sampleBanner').hidden = !meta.uses_sample;
  }

  /* ---------- stats ---------- */
  function renderStats() {
    var avg = goals.length ? goals.reduce(function (s, g) { return s + clamp(num(g.progress_pct)); }, 0) / goals.length : 0;
    var verified = ledger.filter(function (e) { var l = levelOf(e.claim_level || e.level); return l === 'L3' || l === 'L4'; }).length;
    var items = [
      ['stat.goals', goals.length, ''],
      ['stat.progress', Math.round(avg) + '%', ''],
      ['stat.attempts', ledger.length, ''],
      ['stat.verified', verified, verified ? 'good' : '']
    ];
    $('stats').innerHTML = items.map(function (it) {
      return '<div class="stat ' + it[2] + '"><dt>' + esc(t(it[0])) + '</dt><dd>' + esc(it[1]) + '</dd></div>';
    }).join('');
  }

  /* ---------- goals ---------- */
  var gs = { q: '', tier: '', field: '', status: '', sort: 'tier', dir: 1, open: {} };
  var COLS = [
    { k: 'id', label: 'col.id', cls: 'c-id' },
    { k: 'title', label: 'col.title', cls: 'c-title' },
    { k: 'field', label: 'col.field', cls: 'c-field' },
    { k: 'tier', label: 'col.tier', cls: 'c-tier' },
    { k: 'status', label: 'col.status', cls: 'c-status' },
    { k: 'progress_pct', label: 'col.progress', cls: 'c-prog' },
    { k: 'last_update', label: 'col.updated', cls: 'c-upd' }
  ];
  function gTitle(g) { return lang === 'he' ? (g.title_he || g.title) : (g.title || g.title_he); }
  function gAlt(g) { var a = lang === 'he' ? g.title : g.title_he; return a && a !== gTitle(g) ? a : ''; }

  function fillSelect(sel, values, labeler, current) {
    sel.innerHTML = '<option value="">' + esc(t('goals.filter.all')) + '</option>' +
      values.map(function (v) { return '<option value="' + esc(v) + '"' + (v === current ? ' selected' : '') + '>' + esc(labeler ? labeler(v) : v) + '</option>'; }).join('');
  }
  function renderFilters() {
    var tiers = uniq(goals.map(function (g) { return tierKey(g.tier); }));
    fillSelect($('fTier'), tiers, tierName, gs.tier);
    fillSelect($('fField'), uniq(goals.map(function (g) { return g.field; })), null, gs.field);
    fillSelect($('fStatus'), uniq(goals.map(function (g) { return g.status; })), null, gs.status);
    $('q').value = gs.q;
  }
  function renderTiers() {
    var present = uniq(goals.map(function (g) { return tierKey(g.tier); }));
    var list = TIERS.concat(present.filter(function (x) { return TIERS.indexOf(x) < 0; }));
    $('tiers').innerHTML = list.map(function (k) {
      var gg = goals.filter(function (g) { return tierKey(g.tier) === k; });
      var avg = gg.length ? Math.round(gg.reduce(function (s, g) { return s + clamp(num(g.progress_pct)); }, 0) / gg.length) : 0;
      var desc = t('tier.' + k + '.desc'); if (desc.indexOf('tier.') === 0) desc = '';
      return '<button type="button" class="tier-card ' + tierClass(k) + '" data-tier="' + esc(k) + '" aria-pressed="' + (gs.tier === k) + '">' +
        '<span class="tc-code" dir="ltr">' + esc(k) + '</span><h3>' + esc(tierName(k)) + '</h3><p>' + esc(desc) + '</p>' +
        '<span class="tc-meta"><span>' + esc(t('tier.count', { n: gg.length })) + '</span><span>' + esc(t('tier.avg', { p: avg })) + '</span></span>' +
        bar(avg) + '</button>';
    }).join('');
  }
  function goalMatches(g) {
    if (gs.tier && tierKey(g.tier) !== gs.tier) return false;
    if (gs.field && g.field !== gs.field) return false;
    if (gs.status && g.status !== gs.status) return false;
    if (gs.q) {
      var hay = [g.id, g.title, g.title_he, g.field, g.tier, g.status, g.statement_short, g.why_it_matters, g.suggested_attack, g.owner_agent].join(' ').toLowerCase();
      var words = gs.q.toLowerCase().split(/\s+/).filter(Boolean);
      for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) < 0) return false;
    }
    return true;
  }
  function sortVal(g, k) {
    if (k === 'progress_pct') return num(g.progress_pct);
    if (k === 'title') return gTitle(g) || '';
    if (k === 'tier') return TIERS.indexOf(tierKey(g.tier)) + 100 + ':' + (1000 - num(g.progress_pct)).toFixed(1).padStart(7, '0');
    return String(g[k] || '');
  }
  function renderGoalsHead() {
    $('goalsHead').innerHTML = COLS.map(function (c) {
      var sorted = gs.sort === c.k;
      var arrow = sorted ? (gs.dir > 0 ? '▲' : '▼') : '↕';
      return '<th scope="col"' + (sorted ? ' aria-sort="' + (gs.dir > 0 ? 'ascending' : 'descending') + '"' : '') + '>' +
        '<button type="button" data-sort="' + c.k + '">' + esc(t(c.label)) + ' <span class="arrow" aria-hidden="true">' + arrow + '</span></button></th>';
    }).join('');
  }
  function detailHtml(g) {
    function blk(label, val, cls) { return val ? '<div class="' + (cls || '') + '"><h4>' + esc(t(label)) + '</h4><p>' + linkify(val) + '</p></div>' : ''; }
    var chips = [];
    if (g.ai_tractability) chips.push('<span class="badge">' + esc(t('goal.ai')) + ': ' + esc(g.ai_tractability) + '</span>');
    if (g.formalization_readiness) chips.push('<span class="badge">' + esc(t('goal.formal')) + ': ' + esc(g.formalization_readiness) + '</span>');
    if (g.owner_agent) chips.push('<span class="badge" dir="ltr">' + esc(t('goal.owner')) + ': ' + esc(g.owner_agent) + '</span>');
    return '<div class="detail-grid">' +
      '<div class="full"><h4>' + esc(t('goal.statement')) + '</h4><p class="statement">' + esc(g.statement_short || '—') + '</p></div>' +
      blk('goal.why', g.why_it_matters) + blk('goal.partial', g.known_partial_results) +
      blk('goal.attack', g.suggested_attack) + blk('goal.refs', g.references, 'ref-block') +
      (chips.length ? '<div class="full meta-row">' + chips.join('') + '</div>' : '') + '</div>';
  }
  function renderGoals() {
    renderGoalsHead();
    var body = $('goalsBody');
    if (!goals.length) {
      body.innerHTML = '<tr class="empty-row"><td colspan="7" class="empty">' + esc(t('goals.none')) + '</td></tr>';
      $('goalCount').textContent = '';
      return;
    }
    var rows = goals.filter(goalMatches).slice().sort(function (a, b) {
      var x = sortVal(a, gs.sort), y = sortVal(b, gs.sort);
      if (typeof x === 'number') return (x - y) * gs.dir;
      return String(x).localeCompare(String(y), lang, { numeric: true }) * gs.dir;
    });
    $('goalCount').textContent = t('goals.count', { n: rows.length, total: goals.length });
    if (!rows.length) { body.innerHTML = '<tr class="empty-row"><td colspan="7" class="empty">' + esc(t('goals.empty')) + '</td></tr>'; return; }
    body.innerHTML = rows.map(function (g, i) {
      var open = !!gs.open[g.id];
      var did = 'gd-' + i;
      var alt = gAlt(g);
      var r = '<tr class="g-row' + (open ? '' : ' collapsed') + '">' +
        '<td class="c-id">' + esc(g.id) + '</td>' +
        '<td class="c-title"><button type="button" class="g-title" data-goal="' + esc(g.id) + '" aria-expanded="' + open + '" aria-controls="' + did + '">' +
          '<span class="chev" aria-hidden="true">▶</span><span>' + esc(gTitle(g)) + (alt ? '<span class="g-sub" lang="' + (lang === 'he' ? 'en' : 'he') + '">' + esc(alt) + '</span>' : '') + '</span></button></td>' +
        '<td class="c-field" data-label="' + esc(t('col.field')) + '">' + esc(g.field) + '</td>' +
        '<td class="c-tier" data-label="' + esc(t('col.tier')) + '"><span class="badge ' + tierClass(g.tier) + '">' + esc(tierName(g.tier)) + '</span></td>' +
        '<td class="c-status" data-label="' + esc(t('col.status')) + '"><span class="badge ' + statusClass(g.status) + '">' + esc(g.status || '—') + '</span></td>' +
        '<td class="c-prog" data-label="' + esc(t('col.progress')) + '">' + bar(g.progress_pct) + '</td>' +
        '<td class="c-upd" data-label="' + esc(t('col.updated')) + '">' + esc(g.last_update) + '</td></tr>';
      if (open) r += '<tr class="g-detail" id="' + did + '"><td colspan="7">' + detailHtml(g) + '</td></tr>';
      return r;
    }).join('');
    typeset(body);
  }
  function bindGoals() {
    $('q').addEventListener('input', function (e) { gs.q = e.target.value; renderGoals(); });
    $('fTier').addEventListener('change', function (e) { gs.tier = e.target.value; renderGoals(); renderTiers(); });
    $('fField').addEventListener('change', function (e) { gs.field = e.target.value; renderGoals(); });
    $('fStatus').addEventListener('change', function (e) { gs.status = e.target.value; renderGoals(); });
    $('fReset').addEventListener('click', function () { gs.q = gs.tier = gs.field = gs.status = ''; renderFilters(); renderTiers(); renderGoals(); });
    $('goalsHead').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-sort]'); if (!b) return;
      var k = b.getAttribute('data-sort');
      if (gs.sort === k) gs.dir = -gs.dir; else { gs.sort = k; gs.dir = k === 'progress_pct' || k === 'last_update' ? -1 : 1; }
      renderGoals();
      var nb = $('goalsHead').querySelector('button[data-sort="' + k + '"]'); if (nb) nb.focus();
    });
    $('goalsBody').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-goal]'); if (!b) return;
      var id = b.getAttribute('data-goal');
      gs.open[id] = !gs.open[id];
      renderGoals();
      var nb = $('goalsBody').querySelector('button[data-goal="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]'); if (nb) nb.focus();
    });
    $('tiers').addEventListener('click', function (e) {
      var b = e.target.closest('[data-tier]'); if (!b) return;
      var k = b.getAttribute('data-tier');
      gs.tier = gs.tier === k ? '' : k;
      $('fTier').value = gs.tier;
      renderTiers(); renderGoals();
    });
  }

  /* ---------- tools ---------- */
  function renderTools() {
    var el = $('toolsList');
    if (!tools.length) { el.innerHTML = '<p class="placeholder">' + esc(t('tools.none')) + '</p>'; return; }
    var cats = uniq(tools.map(function (x) { return x.category || '—'; }));
    el.innerHTML = cats.map(function (c) {
      var items = tools.filter(function (x) { return (x.category || '—') === c; });
      return '<div class="tool-cat"><h3>' + esc(c) + ' <span class="muted">· ' + items.length + '</span></h3><div class="tool-grid">' +
        items.map(function (x) {
          var url = safeUrl(x.url);
          var mat = String(x.maturity || '').toLowerCase().replace(/[^a-z]/g, '');
          return '<article class="card"><h4 dir="auto">' + esc(x.name) + '</h4><p>' + esc(x.what_it_does) + '</p>' +
            (x.use_in_lab ? '<p class="use">' + esc(x.use_in_lab) + '</p>' : '') +
            '<div class="card-foot">' + (x.maturity ? '<span class="badge mat-' + esc(mat) + '">' + esc(x.maturity) + '</span>' : '') +
            (x.license_or_cost ? '<span class="badge">' + esc(x.license_or_cost) + '</span>' : '') +
            (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(t('tools.open')) + ' ↗</a>' : '') + '</div></article>';
        }).join('') + '</div></div>';
    }).join('');
  }

  /* ---------- creative proofs ---------- */
  var pf = '';
  function renderProofs() {
    var el = $('proofsList'), chips = $('proofChips');
    if (!proofs.length) { chips.innerHTML = ''; el.innerHTML = '<p class="placeholder">' + esc(t('proofs.none')) + '</p>'; return; }
    var fams = uniq(proofs.map(function (p) { return p.technique_family; }));
    chips.setAttribute('aria-label', t('proofs.all'));
    chips.innerHTML = '<button type="button" class="chip" data-fam="" aria-pressed="' + (!pf) + '">' + esc(t('proofs.all')) + '</button>' +
      fams.map(function (f) { return '<button type="button" class="chip" data-fam="' + esc(f) + '" aria-pressed="' + (pf === f) + '">' + esc(f) + '</button>'; }).join('');
    var list = proofs.filter(function (p) { return !pf || p.technique_family === pf; })
      .sort(function (a, b) { return num(a.year) - num(b.year); });
    el.innerHTML = list.map(function (p) {
      var y = String(p.year || '');
      if (/^-\d+$/.test(y)) y = y.slice(1) + (lang === 'he' ? ' לפנה״ס' : ' BCE');
      return '<article class="card proof"><div class="year">' + esc(y) + '</div><h4 dir="auto">' + esc(p.name) + '</h4>' +
        '<div class="who" dir="auto">' + esc(p.people) + '</div>' +
        '<div class="meta-row">' + (p.field ? '<span class="badge">' + esc(p.field) + '</span>' : '') +
          (p.technique_family ? '<span class="badge tier-A">' + esc(p.technique_family) + '</span>' : '') + '</div>' +
        '<dl>' + (p.what_was_creative ? '<div><dt>' + esc(t('proofs.creative')) + '</dt><dd>' + esc(p.what_was_creative) + '</dd></div>' : '') +
        (p.reusable_lesson ? '<div><dt>' + esc(t('proofs.lesson')) + '</dt><dd class="lesson">' + esc(p.reusable_lesson) + '</dd></div>' : '') +
        (p.ai_relevance ? '<div><dt>' + esc(t('proofs.ai')) + '</dt><dd>' + esc(p.ai_relevance) + '</dd></div>' : '') + '</dl>' +
        (p.reference ? '<div class="ref">' + linkify(p.reference) + '</div>' : '') + '</article>';
    }).join('');
    typeset(el);
  }
  function bindProofs() {
    $('proofChips').addEventListener('click', function (e) {
      var b = e.target.closest('[data-fam]'); if (!b) return;
      pf = b.getAttribute('data-fam'); renderProofs();
      var nb = $('proofChips').querySelector('[data-fam="' + pf.replace(/"/g, '\\"') + '"]'); if (nb) nb.focus();
    });
  }

  /* ---------- wisdom ---------- */
  function renderWisdom() {
    var el = $('wisdomList');
    if (!wisdom.length) { el.innerHTML = '<p class="placeholder">' + esc(t('wisdom.none')) + '</p>'; return; }
    var trads = uniq(wisdom.map(function (w) { return w.tradition; }));
    el.innerHTML = wisdom.map(function (w) {
      return '<article class="card bridge trad-' + (trads.indexOf(w.tradition) % 5) + '"><span class="trad" dir="auto">' + esc(w.tradition) + '</span>' +
        '<h4 dir="auto">' + esc(w.title) + '</h4>' + (w.math_area ? '<span class="area">' + esc(w.math_area) + '</span>' : '') +
        '<p>' + esc(w.description) + '</p>' +
        (w.deliverable ? '<p class="use"><strong>' + esc(t('wisdom.deliverable')) + ':</strong> ' + esc(w.deliverable) + '</p>' : '') +
        '<div class="card-foot">' + (w.feasibility ? '<span class="badge">' + esc(t('wisdom.feasibility')) + ': ' + esc(w.feasibility) + '</span>' : '') + '</div></article>';
    }).join('');
    typeset(el);
  }

  /* ---------- log ---------- */
  function pick(o, keys) { for (var i = 0; i < keys.length; i++) if (o[keys[i]] != null && o[keys[i]] !== '') return o[keys[i]]; return ''; }
  function renderLog() {
    var nl = $('newsList');
    var items = news.slice().sort(function (a, b) { return String(b.date).localeCompare(String(a.date)); });
    nl.innerHTML = items.length ? items.map(function (a, i) {
      var lv = levelOf(a.claim_level);
      var tags = (a.tags || []).map(function (x) { return '<span class="badge">' + esc(x) + '</span>'; }).join('');
      return '<details class="article" lang="' + esc(a.lang || 'he') + '" dir="' + (a.lang === 'en' ? 'ltr' : 'rtl') + '"' + (i === 0 && items.length === 1 ? '' : '') + '>' +
        '<summary><div class="a-meta"><time datetime="' + esc(a.date) + '">' + esc(a.date) + '</time>' +
        (lv ? '<span class="lvl lvl-' + lv + '" title="' + esc(t('log.claim')) + '">' + lv + '</span>' : '') + tags + '</div>' +
        '<h4>' + esc(a.title) + '</h4><p class="a-excerpt">' + esc(a.excerpt) + '</p><span class="a-more">' + esc(t('log.read')) + ' ←</span></summary>' +
        '<div class="prose">' + (a.html || '') + '</div></details>';
    }).join('') : '<p class="placeholder">' + esc(t('log.news.none')) + '</p>';
    nl.querySelectorAll('.a-more').forEach(function (s) { s.textContent = t('log.read') + (lang === 'he' ? ' ←' : ' →'); });

    var ll = $('ledgerList');
    var entries = ledger.slice().sort(function (a, b) {
      return String(pick(b, ['ts', 'timestamp', 'date', 'time'])).localeCompare(String(pick(a, ['ts', 'timestamp', 'date', 'time'])));
    }).slice(0, 40);
    ll.innerHTML = entries.length ? '<ol class="timeline">' + entries.map(function (e) {
      var lv = levelOf(pick(e, ['claim_level', 'level', 'claim']));
      var when = String(pick(e, ['ts', 'timestamp', 'date', 'time'])).replace('T', ' ').slice(0, 16);
      var goal = pick(e, ['goal_id', 'goal', 'target']);
      var agent = pick(e, ['agent', 'owner_agent', 'by']);
      var text = pick(e, ['summary', 'note', 'notes', 'result', 'description', 'message', 'outcome']);
      var link = safeUrl(pick(e, ['url', 'link', 'artifact_url']));
      return '<li style="--c: var(--' + (lv ? 'l' + lv.charAt(1) : 'line-2') + ')"><div class="t-meta"><time>' + esc(when) + '</time>' +
        (lv ? '<span class="lvl lvl-' + lv + '">' + lv + '</span>' : '') +
        (goal ? '<span dir="ltr">' + esc(goal) + '</span>' : '') + (agent ? '<span dir="ltr">· ' + esc(agent) + '</span>' : '') + '</div>' +
        (text ? '<p dir="auto">' + esc(text) + (link ? ' <a href="' + esc(link) + '" target="_blank" rel="noopener">↗</a>' : '') + '</p>' : '') + '</li>';
    }).join('') + '</ol>' : '<p class="placeholder">' + esc(t('log.ledger.none')) + '</p>';
    typeset(nl); typeset(ll);
  }

  /* ---------- chrome: theme, lang, menu, active nav ---------- */
  function bindChrome() {
    $('themeBtn').addEventListener('click', function () {
      var root = document.documentElement;
      var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next); store.set('esh27.theme', next);
    });
    $('langBtn').addEventListener('click', function () {
      lang = lang === 'he' ? 'en' : 'he'; store.set('esh27.lang', lang); renderAll();
    });
    var nav = $('nav'), mb = $('menuBtn');
    mb.addEventListener('click', function () {
      var open = !nav.classList.contains('open');
      nav.classList.toggle('open', open); mb.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) { nav.classList.remove('open'); mb.setAttribute('aria-expanded', 'false'); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('open')) { nav.classList.remove('open'); mb.setAttribute('aria-expanded', 'false'); mb.focus(); }
    });
    if ('IntersectionObserver' in window) {
      var links = {}; nav.querySelectorAll('a').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
      var io = new IntersectionObserver(function (ents) {
        ents.forEach(function (en) {
          if (en.isIntersecting && links[en.target.id]) {
            Object.keys(links).forEach(function (k) { links[k].classList.remove('active'); links[k].removeAttribute('aria-current'); });
            links[en.target.id].classList.add('active'); links[en.target.id].setAttribute('aria-current', 'true');
          }
        });
      }, { rootMargin: '-40% 0px -55% 0px' });
      Object.keys(links).forEach(function (k) { var s = $(k); if (s) io.observe(s); });
    }
  }

  function renderAll() {
    applyStatic(); renderStats(); renderFilters(); renderTiers(); renderGoals();
    renderTools(); renderProofs(); renderWisdom(); renderLog();
    typeset(document.querySelector('.hero'));
  }

  bindChrome(); bindGoals(); bindProofs(); renderAll();
  // KaTeX scripts are deferred: typeset once they are available.
  function lateTypeset() { typeset(document.body); }
  if (document.readyState === 'complete') lateTypeset();
  else window.addEventListener('load', lateTypeset);
})();
