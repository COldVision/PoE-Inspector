// Interface language (ru / en). The UI text in the source is Russian; for English this engine swaps exact phrases (and regexp rules for strings with numbers)
// in text nodes and in placeholder / title / aria-label / alt attributes, including content added later by the sections (MutationObserver).
// Section dictionaries live in web/i18n/<name>.js and call I18N.add({ 'Русский текст': 'English text' }, [[/^(\d+) файлов$/, '$1 files']]).
// Names that come from the game data are not translated here: the data has both languages, a section picks the field by I18N.lang.
(function () {
  const KEY = 'poe_inspector.lang';
  const SECTIONS = ['core', 'home', 'editor', 'skills', 'items', 'uniques', 'monsters', 'mods', 'ref', 'tree', 'models', 'tables', 'files', 'sources'];
  const dict = new Map(), rules = [], orig = new WeakMap();
  let lang = 'ru';
  try { lang = localStorage.getItem(KEY) === 'en' ? 'en' : 'ru'; } catch (e) { /* storage blocked */ }
  const ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];
  const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CANVAS', 'SVG', 'NOSCRIPT']);
  const norm = s => s.replace(/\s+/g, ' ').trim();

  function tr(s) {
    const k = norm(s);
    if (!k) return null;
    let o = dict.get(k);
    if (o == null) for (const [re, rep] of rules) { if (re.test(k)) { o = k.replace(re, rep); break; } }
    return o == null || o === k ? null : o;
  }
  const keep = (s, out) => s.replace(/^(\s*)[\s\S]*?(\s*)$/, (_m, a, b) => a + out + b);

  function textNode(n) {
    const rec = orig.get(n);
    if (rec && n.nodeValue === rec.out) return;          // already ours
    const out = tr(n.nodeValue);
    if (out != null) { orig.set(n, { text: n.nodeValue, out: keep(n.nodeValue, out) }); n.nodeValue = orig.get(n).out; }
  }
  function attrs(el) {
    for (const a of ATTRS) {
      if (!el.hasAttribute || !el.hasAttribute(a)) continue;
      const v = el.getAttribute(a), key = '\u0000' + a, r = orig.get(el) || {};
      if (r[key] && r[key].out === v) continue;
      const out = tr(v);
      if (out != null) { r[key] = { text: v, out }; orig.set(el, r); el.setAttribute(a, out); }
    }
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (root.parentNode && !SKIP.has(root.parentNode.nodeName.toUpperCase()) && !root.parentNode.closest('[data-noi18n]')) textNode(root); return; }
    if (root.nodeType !== 1 || SKIP.has(root.nodeName.toUpperCase()) || root.closest('[data-noi18n]')) return;
    attrs(root);
    for (let c = root.firstChild; c; c = c.nextSibling) walk(c);
  }
  function restore(root) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_ALL);
    for (let n = w.currentNode; n; n = w.nextNode()) {
      const r = orig.get(n);
      if (!r) continue;
      if (n.nodeType === 3) { if (n.nodeValue === r.out) n.nodeValue = r.text; }
      else for (const k of Object.keys(r)) if (k[0] === '\u0000') { const a = k.slice(1); if (n.getAttribute(a) === r[k].out) n.setAttribute(a, r[k].text); }
      orig.delete(n);
    }
  }

  let queue = new Set(), raf = 0, busy = false;
  const obs = new MutationObserver(ms => {
    if (busy || lang !== 'en') return;
    for (const m of ms) {
      if (m.type === 'childList') m.addedNodes.forEach(n => queue.add(n));
      else if (m.type === 'characterData') queue.add(m.target);
      else if (m.type === 'attributes') queue.add(m.target);
    }
    if (!raf) raf = setTimeout(flush, 30);   // not rAF: a hidden window pauses it
  });
  function flush() {
    raf = 0; const q = queue; queue = new Set();
    busy = true;
    try { q.forEach(n => { if (n.isConnected) walk(n); }); } finally { obs.takeRecords(); busy = false; }
  }
  function start() {
    obs.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
  function applyAll() {
    busy = true;
    try { if (lang === 'en') walk(document.body); else restore(document.body); } finally { obs.takeRecords(); busy = false; }
    document.documentElement.lang = lang;
    document.title = lang === 'en' ? (tr(document.title) || document.title) : document.title;
  }

  const I18N = {
    get lang() { return lang; },
    add(d, r) { for (const k in (d || {})) dict.set(norm(k), d[k]); for (const x of (r || [])) rules.push(x); if (lang === 'en' && document.body) { applyAll(); } },
    t(s) { return lang === 'en' ? (tr(s) ?? s) : s; },
    pick(ru, en) { return lang === 'en' ? (en || ru) : (ru || en); },   // for data that carries both languages
    set(l) {
      l = l === 'en' ? 'en' : 'ru'; if (l === lang) return;
      lang = l; try { localStorage.setItem(KEY, l); } catch (e) { /* ignore */ }
      applyAll(); syncSwitch();
      window.dispatchEvent(new CustomEvent('i18n:change', { detail: { lang } }));
    },
    apply: applyAll,
  };
  window.I18N = I18N;

  function syncSwitch() {
    document.querySelectorAll('#langsw button').forEach(b => { b.setAttribute('aria-pressed', String(b.dataset.l === lang)); });
  }
  function mount() {
    const h = document.querySelector('header');
    if (h && !document.getElementById('langsw')) {
      const d = document.createElement('div'); d.id = 'langsw'; d.setAttribute('role', 'group'); d.setAttribute('aria-label', 'Language'); d.setAttribute('data-noi18n', '');
      d.innerHTML = '<button type="button" data-l="ru">RU</button><button type="button" data-l="en">EN</button>';
      d.onclick = e => { const b = e.target.closest('button'); if (b) I18N.set(b.dataset.l); };
      h.appendChild(d);
    }
    syncSwitch();
  }
  const css = document.createElement('style');
  css.textContent = '#langsw{flex:none;margin-left:auto;display:flex;border:1px solid var(--line,#3e2d57);border-radius:8px;overflow:hidden}' +
    '#langsw button{background:transparent;color:var(--dim,#b9aed3);border:0;padding:4px 12px;font:600 14px/1.4 inherit;cursor:pointer}' +
    '#langsw button[aria-pressed="true"]{background:var(--acc,#fc4c70);color:var(--on-acc,#030409)}' +
    '#langsw button:hover:not([aria-pressed="true"]){color:#fff}';
  document.head.appendChild(css);

  // section dictionaries (each is optional; they only call I18N.add)
  for (const n of SECTIONS) { const s = document.createElement('script'); s.src = '/static/i18n/' + n + '.js'; s.async = false; document.head.appendChild(s); }
  const boot = () => { mount(); start(); if (lang === 'en') applyAll(); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.addEventListener('load', () => { if (lang === 'en') applyAll(); });
})();
