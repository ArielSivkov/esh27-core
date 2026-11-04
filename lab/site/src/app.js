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
    if (/(disput|block|stuck|abandon|fail|refut)/.test(s)) return 'st-blocked';
    if (/(partial|progress|active|attack|working|running|literature|survey)/.test(s)) return 'st-active';
    if (/(elsewhere|formaliz)/.test(s)) return 'st-formal';
    if (/(done|proved|verified|complete|closed|solved)/.test(s)) return 'st-done';
    return 'st-wait';
  }
  function statusName(s) { var k = 'status.' + s; var v = t(k); return v === k ? s : v; }
  /* 1–5 scale rendered as dots; any other value shown as text */
  function scale(v) {
    var n = parseInt(v, 10);
    if (!(n >= 1 && n <= 5) || String(n) !== String(v).trim()) return esc(v);
    var dots = '';
    for (var i = 1; i <= 5; i++) dots += '<i class="' + (i <= n ? 'on' : '') + '"></i>';
    return '<span class="dots" role="img" aria-label="' + esc(t('scale.of', { v: n })) + '">' + dots + '</span>';
  }
  /* "c. 300 BC", "1976–1977", "1946 (puzzle)" -> sortable number */
  function yearNum(y) {
    var m = String(y || '').match(/(\d{1,4})/);
    if (!m) return 99999;
    var n = parseInt(m[1], 10);
    return /\bB\.?C|BCE|^-/i.test(String(y)) ? -n : n;
  }
  function yearLabel(y) {
    y = String(y || '');
    if (lang !== 'he') return y.replace(/^-(\d+)$/, '$1 BCE');
    return y.replace(/^-(\d+)$/, '$1 לפנה״ס').replace(/^c\.\s*(\d+)\s*BC$/i, 'בערך $1 לפנה״ס');
  }
  /* claim level per goal = max over ledger attempts that are not dry runs and not superseded */
  var goalLevel = {};
  (function () {
    var superseded = {};
    ledger.forEach(function (e) { if (e.supersedes) superseded[e.supersedes] = true; });
    ledger.forEach(function (e) {
      if (e.dry_run === true || superseded[e.attempt_id]) return;
      var l = levelOf(e.claim_level); if (!l) return;
      if (l >= 'L3' && !(e.certificate && e.certificate.verified === true)) l = 'L2'; // L3+ needs a verified certificate
      var g = e.goal_id; if (!g) return;
      if (!goalLevel[g] || l > goalLevel[g]) goalLevel[g] = l;
    });
  })();
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
    var verified = Object.keys(goalLevel).filter(function (g) { return goalLevel[g] >= 'L3'; }).length;
    var items = [
      ['stat.goals', goals.length, ''],
      ['stat.progress', Math.round(avg) + '%', ''],
      ['stat.attempts', ledger.length, ''],
      ['stat.verified', verified, verified ? 'good' : '']
    ];
    $('stats').innerHTML = items.map(function (it) {
      return '<div class="stat ' + it[2] + '"><dt>' + esc(t(it[0])) + '</dt><dd dir="auto">' + esc(it[1]) + '</dd></div>';
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
    fillSelect($('fStatus'), uniq(goals.map(function (g) { return g.status; })), statusName, gs.status);
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
      var hay = [g.id, g.title, g.title_he, g.field, g.tier, tierName(g.tier), g.status, statusName(g.status), g.statement_short, g.why_it_matters, g.suggested_attack, g.owner_agent].join(' ').toLowerCase();
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
    function blk(label, val, cls) { return val ? '<div class="' + (cls || '') + '"><h4>' + esc(t(label)) + '</h4><p dir="auto">' + linkify(val) + '</p></div>' : ''; }
    var chips = [];
    if (g.ai_tractability) chips.push('<span class="badge nodot">' + esc(t('goal.ai')) + ' ' + scale(g.ai_tractability) + '</span>');
    if (g.formalization_readiness) chips.push('<span class="badge nodot">' + esc(t('goal.formal')) + ' ' + scale(g.formalization_readiness) + '</span>');
    if (goalLevel[g.id]) chips.push('<span class="badge nodot">' + esc(t('goal.level')) + ' <span class="lvl lvl-' + goalLevel[g.id] + '">' + goalLevel[g.id] + '</span></span>');
    if (g.owner_agent) chips.push('<span class="badge nodot">' + esc(t('goal.owner')) + ': <span dir="ltr">' + esc(g.owner_agent) + '</span></span>');
    return '<div class="detail-grid">' +
      '<div class="full"><h4>' + esc(t('goal.statement')) + '</h4><p class="statement" dir="auto">' + esc(g.statement_short || '—') + '</p></div>' +
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
        '<td class="c-field" dir="auto" data-label="' + esc(t('col.field')) + '">' + esc(g.field) + '</td>' +
        '<td class="c-tier" data-label="' + esc(t('col.tier')) + '"><span class="badge ' + tierClass(g.tier) + '">' + esc(tierName(g.tier)) + '</span></td>' +
        '<td class="c-status" data-label="' + esc(t('col.status')) + '"><span class="badge ' + statusClass(g.status) + '">' + esc(statusName(g.status) || '—') + '</span>' +
          (goalLevel[g.id] ? ' <span class="lvl lvl-' + goalLevel[g.id] + '">' + goalLevel[g.id] + '</span>' : '') + '</td>' +
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

  /* ---------- shared: chips + "show more" ---------- */
  function chipsHtml(values, current, allLabel, attr) {
    return '<button type="button" class="chip" ' + attr + '="" aria-pressed="' + (!current) + '">' + esc(allLabel) + '</button>' +
      values.map(function (v) {
        return '<button type="button" class="chip" ' + attr + '="' + esc(v[0]) + '" aria-pressed="' + (current === v[0]) + '">' + esc(v[0]) +
          ' <span class="chip-n">' + v[1] + '</span></button>';
      }).join('');
  }
  function counts(list, key) {
    var c = {};
    list.forEach(function (x) { var k = x[key] || '—'; c[k] = (c[k] || 0) + 1; });
    return Object.keys(c).sort(function (a, b) { return c[b] - c[a] || a.localeCompare(b); }).map(function (k) { return [k, c[k]]; });
  }
  function moreBtn(btn, total, limit, expanded) {
    btn.hidden = total <= limit;
    btn.textContent = expanded ? t('ui.less') : t('ui.more', { n: total });
    btn.setAttribute('aria-expanded', String(!!expanded));
  }

  /* ---------- tools ---------- */
  var ts = { cat: '', all: false, LIMIT: 12 };
  function toolCard(x) {
    var url = safeUrl(x.url);
    return '<article class="card tool"><div class="tool-top"><h4 dir="auto">' + esc(x.name) + '</h4>' +
      (x.maturity ? '<span class="mat" title="' + esc(t('tools.maturity')) + '">' + scale(x.maturity) + '</span>' : '') + '</div>' +
      '<span class="area">' + esc(x.category) + '</span>' +
      '<p dir="auto">' + esc(x.what_it_does) + '</p>' +
      (x.use_in_lab ? '<p class="use" dir="auto">' + esc(x.use_in_lab) + '</p>' : '') +
      '<div class="card-foot">' + (x.license_or_cost ? '<span class="lic">' + esc(x.license_or_cost) + '</span>' : '') +
      (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(t('tools.open')) + ' ↗</a>' : '') + '</div></article>';
  }
  function renderTools() {
    var el = $('toolsList'), chips = $('toolChips'), btn = $('toolsMore');
    if (!tools.length) { chips.innerHTML = ''; btn.hidden = true; el.innerHTML = '<p class="placeholder">' + esc(t('tools.none')) + '</p>'; return; }
    chips.setAttribute('aria-label', t('tools.all'));
    chips.innerHTML = chipsHtml(counts(tools, 'category'), ts.cat, t('tools.all'), 'data-cat');
    var list = tools.filter(function (x) { return !ts.cat || (x.category || '—') === ts.cat; })
      .sort(function (a, b) { return num(b.maturity) - num(a.maturity); });
    var shown = ts.all || ts.cat ? list : list.slice(0, ts.LIMIT);
    el.innerHTML = '<div class="tool-grid">' + shown.map(toolCard).join('') + '</div>';
    if (ts.cat) btn.hidden = true; else moreBtn(btn, list.length, ts.LIMIT, ts.all);
  }
  function bindTools() {
    $('toolChips').addEventListener('click', function (e) {
      var b = e.target.closest('[data-cat]'); if (!b) return;
      ts.cat = b.getAttribute('data-cat'); renderTools();
      var nb = $('toolChips').querySelector('[data-cat="' + ts.cat.replace(/"/g, '\\"') + '"]'); if (nb) nb.focus();
    });
    $('toolsMore').addEventListener('click', function () { ts.all = !ts.all; renderTools(); if (!ts.all) $('tools').scrollIntoView(); });
  }

  /* ---------- creative proofs ---------- */
  var ps = { fam: '', all: false, LIMIT: 9 };
  function renderProofs() {
    var el = $('proofsList'), chips = $('proofChips'), btn = $('proofsMore');
    if (!proofs.length) { chips.innerHTML = ''; btn.hidden = true; el.innerHTML = '<p class="placeholder">' + esc(t('proofs.none')) + '</p>'; return; }
    chips.setAttribute('aria-label', t('proofs.all'));
    chips.innerHTML = chipsHtml(counts(proofs, 'technique_family'), ps.fam, t('proofs.all'), 'data-fam');
    var list = proofs.filter(function (p) { return !ps.fam || (p.technique_family || '—') === ps.fam; })
      .sort(function (a, b) { return yearNum(a.year) - yearNum(b.year); });
    var shown = ps.all || ps.fam ? list : list.slice(0, ps.LIMIT);
    el.innerHTML = shown.map(function (p) {
      return '<article class="card proof"><div class="year">' + esc(yearLabel(p.year)) + '</div><h4 dir="auto">' + esc(p.name) + '</h4>' +
        '<div class="who" dir="auto">' + esc(p.people) + '</div>' +
        '<div class="meta-row">' + (p.field ? '<span class="badge">' + esc(p.field) + '</span>' : '') +
          (p.technique_family ? '<span class="badge tier-A">' + esc(p.technique_family) + '</span>' : '') + '</div>' +
        '<dl>' + (p.what_was_creative ? '<div><dt>' + esc(t('proofs.creative')) + '</dt><dd dir="auto">' + esc(p.what_was_creative) + '</dd></div>' : '') +
        (p.reusable_lesson ? '<div><dt>' + esc(t('proofs.lesson')) + '</dt><dd class="lesson" dir="auto">' + esc(p.reusable_lesson) + '</dd></div>' : '') +
        (p.ai_relevance ? '<div><dt>' + esc(t('proofs.ai')) + '</dt><dd dir="auto">' + esc(p.ai_relevance) + '</dd></div>' : '') + '</dl>' +
        (p.reference ? '<div class="ref">' + linkify(p.reference) + '</div>' : '') + '</article>';
    }).join('');
    if (ps.fam) btn.hidden = true; else moreBtn(btn, list.length, ps.LIMIT, ps.all);
    typeset(el);
  }
  function bindProofs() {
    $('proofChips').addEventListener('click', function (e) {
      var b = e.target.closest('[data-fam]'); if (!b) return;
      ps.fam = b.getAttribute('data-fam'); renderProofs();
      var nb = $('proofChips').querySelector('[data-fam="' + ps.fam.replace(/"/g, '\\"') + '"]'); if (nb) nb.focus();
    });
    $('proofsMore').addEventListener('click', function () { ps.all = !ps.all; renderProofs(); if (!ps.all) $('proofs').scrollIntoView(); });
  }

  /* ---------- wisdom ---------- */
  function renderWisdom() {
    var el = $('wisdomList');
    if (!wisdom.length) { el.innerHTML = '<p class="placeholder">' + esc(t('wisdom.none')) + '</p>'; return; }
    function fam(w) { return String(w.tradition || '').split(/\s*[\/(]\s*/)[0]; }
    var trads = uniq(wisdom.map(fam));
    el.innerHTML = wisdom.map(function (w) {
      return '<article class="card bridge trad-' + (trads.indexOf(fam(w)) % 5) + '"><span class="trad" dir="auto">' + esc(w.tradition) + '</span>' +
        '<h4 dir="auto">' + esc(w.title) + '</h4>' + (w.math_area ? '<span class="area">' + esc(w.math_area) + '</span>' : '') +
        '<p dir="auto">' + esc(w.description) + '</p>' +
        (w.deliverable ? '<p class="use"><strong>' + esc(t('wisdom.deliverable')) + ':</strong> ' + esc(w.deliverable) + '</p>' : '') +
        '<div class="card-foot">' + (w.feasibility ? '<span class="badge nodot">' + esc(t('wisdom.feasibility')) + ' ' + scale(w.feasibility) + '</span>' : '') + '</div></article>';
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
      var unverified = lv >= 'L3' && !(e.certificate && e.certificate.verified === true);
      if (unverified) lv = 'L2';
      var when = String(pick(e, ['ts', 'timestamp', 'date', 'time'])).replace('T', ' ').slice(0, 16);
      var goal = pick(e, ['goal_id', 'goal', 'target']);
      var agent = pick(e, ['agent', 'owner_agent', 'by']);
      var text = pick(e, ['summary', 'note', 'notes', 'result', 'description', 'message']);
      var link = safeUrl(pick(e, ['url', 'link', 'artifact_url']));
      var outc = String(pick(e, ['outcome', 'status']));
      var oName = outc ? (t('outcome.' + outc) === 'outcome.' + outc ? outc : t('outcome.' + outc)) : '';
      var method = pick(e, ['method']);
      return '<li style="--c: var(--' + (lv ? 'l' + lv.charAt(1) : 'line-2') + ')"><div class="t-meta"><time>' + esc(when) + '</time>' +
        (lv ? '<span class="lvl lvl-' + lv + '">' + lv + '</span>' : '') +
        (goal ? '<span dir="ltr">' + esc(goal) + '</span>' : '') + (agent ? '<span dir="ltr">· ' + esc(agent) + '</span>' : '') +
        (oName ? '<span class="badge ' + statusClass(outc === 'success' ? 'done' : outc) + '">' + esc(oName) + '</span>' : '') +
        (e.dry_run === true ? '<span class="badge">' + esc(t('log.dry')) + '</span>' : '') +
        (unverified ? '<span class="badge st-blocked">' + esc(t('log.unverified')) + '</span>' : '') +
        (method ? '<span dir="ltr">' + esc(method) + '</span>' : '') + '</div>' +
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

  bindChrome(); bindGoals(); bindTools(); bindProofs(); renderAll();
  // KaTeX scripts are deferred: typeset once they are available.
  function lateTypeset() { typeset(document.body); }
  if (document.readyState === 'complete') lateTypeset();
  else window.addEventListener('load', lateTypeset);
})();
