// Section "Свойства": every game modifier with readable text, tiers, tags and spawn weights.
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
let facets = null;
const EN = () => window.I18N && I18N.lang === 'en';
const pk = (ru, en) => (EN() ? (en || ru) : (ru || en));

export async function modFilters(api) {
  if (!facets) facets = await api('/api/modfacets');
  const dom = document.querySelector('#cls'), gen = document.querySelector('#gsel'), tag = document.querySelector('#tsel');
  if (!dom.dataset.mods) {
    dom.dataset.mods = '1';
    dom.dataset.items = dom.innerHTML;   // the item-class list, put back when leaving the tab
    dom.innerHTML = '<option value="">Все области</option>' + facets.domains.map(d => `<option value="${d.k}">${esc(d.ru)} (${d.n})</option>`).join('');
    gen.innerHTML = '<option value="">Префикс/суффикс…</option>' + facets.gens.map(g => `<option value="${g.k}">${esc(g.ru)} (${g.n})</option>`).join('');
    tag.innerHTML = '<option value="">Любой тег</option>' + facets.tags.map(t => `<option value="${esc(t.k)}">${esc(t.k)} (${t.n})</option>`).join('');
  }
}

export function leaveMods() {
  const dom = document.querySelector('#cls');
  if (dom && dom.dataset.mods) { dom.innerHTML = dom.dataset.items; delete dom.dataset.mods; dom.value = ''; }
  for (const id of ['#gsel', '#tsel']) { const e = document.querySelector(id); if (e) e.style.display = 'none'; }
}

export const modRow = m => [(m.text_ru[0] || m.text[0] || m.name_ru || m.name || m.id), `${m.name_ru || m.name || m.id} · ${m.gen || ''} · ур.${m.level}`, m];

const line = (m, i) => {
  const ru = m.text_ru[i] || '', en = m.text[i] || '';
  if (EN()) return `<div class="mt">${esc(en || ru)}</div>`;
  return `<div class="mt">${esc(ru || en)}</div>${ru && en && ru !== en ? `<div class="me">${esc(en)}</div>` : ''}`;
};

export async function showMod(ctx, m) {
  const d = await ctx.api('/api/mod?id=' + encodeURIComponent(m.id));
  const v = ctx.$('#view'); v.style.display = '';
  const n = Math.max(d.text.length, d.text_ru.length);
  const lines = n ? Array.from({ length: n }, (_, i) => line(d, i)).join('') : d.stats.map(s => `<div class="me">${esc(s[0])}: ${s[1]}–${s[2]}</div>`).join('') || '<div class="me">нет характеристик</div>';
  const tiers = d.siblings.concat([d]).sort((a, b) => a.level - b.level);
  v.innerHTML = `<div class="modcard">${cur.cls ? `<a href="#" class="modback" style="color:var(--dim)">← ${esc(pk(cur.ru, cur.en))}</a>` : ''}<style>
    .modcard{position:absolute;inset:0;overflow:auto;padding:18px 22px;line-height:1.5}
    .modcard h2{margin:0 0 2px;font-size:20px}.modcard .sub{color:var(--dim);margin-bottom:12px}
    .mt{font-size:19px;font-weight:600;color:#c9bfff}.me{color:var(--dim);font-size:15px;margin-bottom:4px}
    .modcard table{border-collapse:collapse;margin:8px 0 14px;min-width:420px}.modcard td,.modcard th{border-bottom:1px solid var(--line);padding:4px 10px;text-align:left;vertical-align:top;font-weight:normal}
    .modcard tr.cur td{background:rgba(255,255,255,.07)}.modcard .chip{display:inline-block;border:1px solid var(--line);border-radius:10px;padding:1px 8px;margin:2px 4px 2px 0;font-size:15px}
    .modcard h4{margin:16px 0 4px;color:var(--dim);font-weight:normal;text-transform:uppercase;font-size:15px;letter-spacing:.06em}</style>
    <h2>${esc(pk(d.name_ru, d.name) || d.id)}${!EN() && d.name && d.name_ru && d.name !== d.name_ru ? ` <span style="color:var(--dim);font-size:15px">${esc(d.name)}</span>` : ''}</h2>
    <div class="sub">${esc(d.id)} · ${esc(d.domain || '')} · ${esc(d.gen || '')} · уровень предмета ${d.level}${d.max_level ? ' (до ' + d.max_level + ')' : ''} · тип ${esc(d.type)}</div>
    <div class="tiles"><div class="tile key"><small>Уровень предмета</small><b>${d.level}</b></div><div class="tile"><small>Тиров в группе</small><b>${tiers.length}</b></div><div class="tile"><small>Тип</small><b style="font-size:18px">${esc(d.gen === 'PREFIX' ? 'Префикс' : d.gen === 'SUFFIX' ? 'Суффикс' : d.gen || '—')}</b></div><div class="tile"><small>Область</small><b style="font-size:18px">${esc(d.domain || '—')}</b></div></div>
    ${lines}
    <h4>Тиры этой группы (${tiers.length})</h4>
    <table><tr><th>Ур.</th><th>Название</th><th>Свойство</th></tr>${tiers.map(t => `<tr class="${t.id === d.id ? 'cur' : ''}"><td>${t.level}</td><td>${esc(pk(t.name_ru, t.name))}</td><td>${esc((EN() ? (t.text.length ? t.text : t.text_ru) : (t.text_ru.length ? t.text_ru : t.text)).join(' / '))}</td></tr>`).join('')}</table>
    <h4>Где выпадает (вес)</h4>${d.spawn.length ? d.spawn.map(s => `<span class="chip">${esc(s[0])} · ${s[1]}</span>`).join('') : '<span class="me">не выпадает на предметах</span>'}
    <h4>Характеристики</h4>${d.stats.map(s => `<span class="chip" title="min–max">${esc(s[0])} · ${s[1]}–${s[2]}</span>`).join('') || '—'}
    <h4>Семейства и теги</h4>${d.families.map(f => `<span class="chip">${esc(f)}</span>`).join('')}${d.tags.map(t => `<span class="chip">#${esc(t)}</span>`).join('')}
  </div>`;
  last = { kind: 'mod', ctx, m };
  const bk = v.querySelector('.modback'); if (bk) bk.onclick = e => { e.preventDefault(); showClass(ctx); };
  ctx.$('#info').textContent = `${d.id} · ${d.siblings.length + 1} тиров в группе`;
}

// ---- left column: item types grouped by category; click shows the mods that can roll on that type ----
const cur = { cls: '', ru: '', en: '', group: -1 };
let last = null;   // what is on screen, redrawn when the language changes
let bases = null;
const TAGC = { fire: '#c8553d', cold: '#4d8fd1', lightning: '#d4b13a', chaos: '#9a5fc7', physical: '#9a8f86', elemental: '#8a7a5a', damage: '#b04a3a', life: '#b04a3a', mana: '#3f77c4', attack: '#a8573a', caster: '#4a7fc0',
  speed: '#3aa6a6', critical: '#b6a14a', minion: '#4d9a6a', resistance: '#6a8a9a', attribute: '#5a8a5a', defences: '#7a8a9a', evasion: '#4aa07a', armour: '#8a8a6a', curse: '#8a5aa0', gem: '#4aa09a', ailment: '#a0705a', resource: '#4a7fa0' };
const sv = p => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
const SEC_ICON = { base: sv('<path d="M12 2 3 7v10l9 5 9-5V7z"/><path d="M3 7l9 5 9-5M12 12v10"/>'), minion: sv('<circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><path d="M8 20v2h8v-2"/><path d="M16 20a2 2 0 0 0 1.56-3.25 8 8 0 1 0-11.12 0A2 2 0 0 0 8 20"/>'),
  caster: sv('<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>'), ow: sv('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/>') };
const tip = (() => { let el = null; return { show(h, e) { if (!el) { el = document.createElement('div'); el.style.cssText = 'position:fixed;z-index:200;max-width:min(900px,calc(100vw - 24px));background:#14110f;border:1px solid #5a4a30;border-radius:4px;padding:12px 16px;font-size:18px;line-height:1.5;pointer-events:none;box-shadow:0 8px 24px #000a'; document.body.appendChild(el); } el.innerHTML = h; el.style.display = ''; this.move(e); }, move(e) { if (!el) return; const w = el.offsetWidth, hh = el.offsetHeight; el.style.left = Math.max(4, Math.min(innerWidth - w - 8, e.clientX + 16)) + 'px'; el.style.top = Math.max(4, Math.min(innerHeight - hh - 8, e.clientY + 16)) + 'px'; }, hide() { if (el) el.style.display = 'none'; } }; })();
const SS = 'background:var(--line);border-radius:3px;padding:0 5px;margin-left:5px;font-size:12px;font-weight:600;color:#fff';

export async function openModClasses(ctx, q) {
  if (!bases) bases = await ctx.api('/api/modbases');
  const list = ctx.$('#list');
  list.innerHTML = '<div class="modlist" style="padding:6px 12px">' + bases.cats.map(c => `<div style="padding:7px 0;border-bottom:1px solid var(--line);line-height:2.2"><span style="color:var(--dim)">${esc(pk(c.ru, c.en))} •</span> ` +
    c.classes.map(x => `<a href="#" class="mcls" data-k="${esc(x.k)}" data-g="${x.g}" data-ru="${esc(x.ru)}" data-en="${esc(x.en)}" style="color:#e8c36a;text-decoration:none;white-space:nowrap;margin-right:6px${x.k === cur.cls && x.g === cur.group ? ';border-bottom:1px dashed #fff' : ''}">${esc(pk(x.ru, x.en))}</a>`).join(' ')).join('</div>') + '</div></div>';
  list.onclick = e => {
    const r = e.target.closest('.mcls'); if (!r) return; e.preventDefault();
    cur.cls = r.dataset.k; cur.ru = r.dataset.ru; cur.en = r.dataset.en; cur.group = +r.dataset.g;
    list.querySelectorAll('.mcls').forEach(x => x.style.borderBottom = x === r ? '1px dashed #fff' : '');
    showClass(ctx);
  };
  list.onmouseover = null;
  ctx.$('#info').textContent = 'Выберите тип предмета слева';
  if (cur.cls) showClass(ctx);
}

export async function showClass(ctx) {
  const d = await ctx.api(`/api/modclass?cls=${encodeURIComponent(cur.cls)}&group=${cur.group}&q=${encodeURIComponent(ctx.$('#q').value)}`);
  const v = ctx.$('#view'); v.style.display = '';
  const table = (rows, title, ru, sk) => {
    const badge = t => `<span style="background:${TAGC[t[0]] || '#4a6a8a'};border-radius:3px;padding:0 5px;margin-left:5px;font-size:12px;font-weight:600;color:#fff">${esc(pk(t[1], t[2]))}</span>`;
    const body = rows.map((r, i) => `<div class="mrow" data-id="${esc(r.id)}" data-i="${i}"><span>${esc(pk(r.text, r.text_en))}${r.tags.map(badge).join('')}</span><span class="nn"><span style="${SS};background:#3a8a4a" title="тиров">${r.tiers}</span><span style="${SS};background:#9a8a3a" title="уровень предмета топ-тира">${r.ilvl}</span></span></div>`).join('');
    return `<div class="mcol"><h3>${SEC_ICON[sk] || ''}${esc(title)} ${ru}</h3>${body}<div class="mtot"><span>Всего</span><span class="nn"><span style="${SS}">${rows.length}</span></span></div></div>`;
  };
  v.innerHTML = `<div class="modcard"><style>
    .modcard{position:absolute;inset:0;overflow:auto;padding:12px 16px;line-height:1.45}.modcard h2{margin:0 0 8px;font-size:18px;color:#e8c36a}.modcard h2 small{color:var(--dim);font-weight:normal;font-size:14px}
    .mcur{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:6px 0;font-size:16px}.mc{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:6px;padding:3px;background:rgba(255,255,255,.04);cursor:help}.msec{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px}@media(max-width:1100px){.msec{grid-template-columns:1fr}}
    .mcol h3{margin:0;padding:3px 8px;font-size:21px;display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.08);border-radius:3px 3px 0 0}.mcol h3 svg{width:26px;height:26px;flex:none}
    .mrow,.mtot{display:flex;justify-content:space-between;gap:8px;padding:3px 8px;border-bottom:1px solid var(--line);font-size:16px;align-items:flex-start}.mrow{cursor:pointer;color:#a9b6ff}.mrow:hover{background:rgba(255,255,255,.07)}
    .mtot{border-bottom:2px dashed var(--line);color:var(--dim)}.nn{white-space:nowrap;flex:none}</style>
    <h2><span style="color:var(--dim)">${pk('Свойства', 'Properties')} ›</span> ${esc(pk(d.ru, d.en))} <small>${EN() ? d.bases.length + ' bases' : d.bases.length + ' баз'}${d.bases.length < 8 ? ': ' + esc((EN() ? d.bases_en : d.bases).join(', ')) : ''}</small></h2>
    ${d.sections.map(s => `${s.currency && s.currency.length ? `<div class="mcur"><span style="color:var(--dim)">Получение:</span>${s.currency.map((c, i) => `<span class="mc" data-i="${i}"><img src="/api/icon?size=64&path=${encodeURIComponent(c.icon)}" width="40" height="40" alt="${esc(pk(c.name, c.name_en))}" onerror="this.replaceWith(document.createTextNode(this.alt))"></span>`).join('')}</div>` : ''}<div class="msec">${table(s.prefix, pk(s.ru, s.en), pk('Префикс', 'Prefix'), s.k)}${table(s.suffix, pk(s.ru, s.en), pk('Суффикс', 'Suffix'), s.k)}</div>`).join('') || '<div class="me">Ничего не найдено</div>'}</div>`;
  v.querySelectorAll('.mcur').forEach((row, k) => {
    const cur = d.sections.filter(s => s.currency && s.currency.length)[k].currency;
    row.querySelectorAll('.mc').forEach(el => { const c = cur[+el.dataset.i];
      el.onmouseenter = e => tip.show(`<div style="color:#e8c36a;font-size:20px;margin-bottom:6px">${esc(pk(c.name, c.name_en))}</div>${c.desc ? `<div>${esc(pk(c.desc, c.desc_en))}</div>` : ''}`, e);
      el.onmousemove = e => tip.move(e); el.onmouseleave = () => tip.hide(); });
  });
  const byId = {}; d.sections.forEach(s => s.prefix.concat(s.suffix).forEach(r => byId[r.id] = r));
  v.querySelectorAll('.mrow').forEach(r => {
    r.onclick = () => { tip.hide(); showMod(ctx, { id: r.dataset.id }); };
    r.onmouseenter = e => { const x = byId[r.dataset.id]; tip.show(`<div style="color:#e8c36a;margin-bottom:6px;font-size:20px">${esc(pk(x.text, x.text_en))}</div><table style="border-collapse:collapse">${x.t.map(t => `<tr><td style="padding:2px 14px 2px 0;color:#d9b84a;white-space:nowrap">${EN() ? 'ilvl' : 'ур.'} ${t[0]}</td><td style="padding:2px 14px 2px 0;color:var(--dim);white-space:nowrap">${esc(pk(t[2], t[4]))}</td><td style="color:#a9b6ff">${esc(pk(t[1], t[3]))}</td></tr>`).join('')}</table>`, e); };
    r.onmousemove = e => tip.move(e); r.onmouseleave = () => tip.hide();
  });
  ctx.$('#info').textContent = `${pk(d.ru, d.en)}: ${d.sections.reduce((n, s) => n + s.prefix.length + s.suffix.length, 0)} ${pk('групп свойств', 'property groups')}`;
  last = { kind: 'class', ctx };
}

window.addEventListener('i18n:change', () => {
  if (!last || !document.querySelector('#view .modcard')) return;
  bases = null;
  if (last.kind === 'class') showClass(last.ctx); else showMod(last.ctx, last.m);
  if (document.querySelector('.modlist')) openModClasses(last.ctx, '');
});
