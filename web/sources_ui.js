// Section "Источники": where unique items drop from. List on the left (search + type filter in #q/#cls), source card on the right.
// Every link is marked with how well it is known: confirmed (PoB / game client table), indirect (socket art), guess, info.
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
let types = null, curId = null, lastBlock = null;
const P = (ru, en) => (window.I18N ? I18N.pick(ru, en) : ru);   // name from the data in the interface language
const T = s => (window.I18N ? I18N.t(s) : s);                    // text produced by the backend (Russian) -> dictionary

const CONF = {
  user: ['✔', 'ok', 'Подтверждено'], pob: ['✔', 'ok', 'Подтверждено'], client: ['✔', 'ok', 'Подтверждено'],
  art: ['◐', 'mid', 'Косвенно'], guess: ['?', 'guess', 'Предположение'], info: ['•', 'info', 'Справка'],
};

export async function srcControls(api) {
  const r = await api('/api/sources?q=&type=');
  types = r.types;
  const dom = document.querySelector('#cls');
  if (!dom.dataset.src) {
    dom.dataset.src = '1';
    dom.dataset.items = dom.innerHTML;   // the item-class list, put back when leaving the tab
  }
  const cur = dom.value;
  dom.innerHTML = '<option value="">Все типы</option>' + types.map(t => `<option value="${t.k}">${esc(T(t.ru))}</option>`).join('');
  dom.value = types.some(t => t.k === cur) ? cur : '';
}

export function leaveSrc() {
  const dom = document.querySelector('#cls');
  if (dom && dom.dataset.src) { dom.innerHTML = dom.dataset.items; delete dom.dataset.src; dom.value = ''; }
}

export const srcRow = r => [P(r.name, r.en), `${T(r.typeRu)}${r.area ? ' · ' + P(r.area, r.areaEn) : ''} · ${r.count}`, r];

const STYLE = `<style>
.srccard{position:absolute;inset:0;overflow:auto;padding:var(--sp-5) 32px;font-size:18px;line-height:1.55;color:var(--text)}
.srccard h2{margin:0;font-family:var(--font-brand);font-weight:600;font-size:30px;letter-spacing:.04em;line-height:1.2}
.srccard .en{color:var(--dim);font-size:19px;margin-top:2px}
.srccard .tag{display:inline-block;margin:10px 8px 0 0;padding:2px 12px;border:1px solid var(--line-strong);border-radius:999px;color:var(--acc-hi);font-size:15px}
.srccard .note{max-width:820px;margin:14px 0;padding:10px 16px;border-left:3px solid var(--acc);background:var(--surface);border-radius:var(--r-sm);color:var(--dim)}
.srccard h3{margin:26px 0 8px;font-size:20px;font-weight:600;color:var(--acc-hi)}
.srccard h3 small{color:var(--dim);font-weight:400;font-size:15px;margin-left:8px}
.srccard .it{display:flex;gap:14px;align-items:center;max-width:900px;padding:8px 12px;border-bottom:1px solid var(--line);cursor:pointer;border-radius:var(--r-sm)}
.srccard .it:hover{background:var(--surface-hi)}
.srccard .it img{width:48px;height:48px;object-fit:contain;flex:none}
.srccard .it .nm{font-size:20px;color:#e8c07d}.srccard .it .bs{color:var(--dim);font-size:16px}.srccard .it .wy{color:var(--dim);font-size:14px}
.cbadge{flex:none;min-width:30px;text-align:center;font-weight:700;font-size:16px;padding:0 6px;border-radius:var(--r-sm);border:1px solid}
.cbadge.ok{color:var(--ok);border-color:var(--ok)}.cbadge.mid{color:var(--info);border-color:var(--info)}.cbadge.guess{color:var(--acc);border-color:var(--acc)}.cbadge.info{color:var(--dim);border-color:var(--line-strong)}
.srcblk{margin:12px 8px 10px;padding:8px 12px;border:1px solid var(--line);border-radius:var(--r-md);background:var(--surface);font-family:var(--font-text);font-size:16px;line-height:1.5}
.srcblk b.h{display:block;color:var(--acc-hi);font-size:17px;margin-bottom:4px}
.srcblk .sl{display:flex;gap:10px;align-items:baseline;padding:2px 0;cursor:pointer}.srcblk .sl:hover .sn{text-decoration:underline}
.srcblk .sn{color:var(--text)}.srcblk .sw{color:var(--dim);font-size:14px}
</style>`;

export function srcBlock(list) {
  lastBlock = list;
  if (!list || !list.length) return '';
  const rows = list.map(s => {
    const c = CONF[s.conf] || CONF.info;
    return `<div class="sl" data-src="${esc(s.id)}" title="${esc(T(s.why))}"><span class="cbadge ${c[1]}">${c[0]}</span><span class="sn">${esc(P(s.ru, s.en))}${s.area ? ' · ' + esc(P(s.area, s.areaEn)) : ''}</span><span class="sw">${esc(T(s.typeRu))} · ${esc(T(s.confRu))}</span></div>`;
  }).join('');
  return `<div class="srcblk">${STYLE}<b class="h">Откуда падает</b>${rows}</div>`;
}

export async function showSource(ctx, row) {
  const d = await ctx.api(`/api/source?id=${encodeURIComponent(row.id)}`);
  curId = row.id;
  const v = ctx.$('#view'); v.style.display = '';
  const groups = [['ok', 'Подтверждено', 'Path of Building или таблица клиента игры'], ['mid', 'Косвенно', 'по данным клиента, но не прямое указание дропа'],
    ['guess', 'Предположение', 'угадано по названию или тексту предмета, не проверено'], ['info', d.type === 'unknown' ? 'Без данных' : 'Список', '']];
  const body = groups.map(([k, h, sub]) => {
    const its = d.items.filter(it => (CONF[it.conf] || CONF.info)[1] === k);
    if (!its.length) return '';
    return `<h3>${h} · ${its.length}<small>${esc(sub)}</small></h3>` + its.map(it => {
      const c = CONF[it.conf] || CONF.info;
      return `<div class="it" data-u="${esc(it.name)}" title="${esc(T(it.confRu))}">${it.icon ? `<img loading="lazy" src="/api/icon?size=96&path=${encodeURIComponent(it.icon)}" onerror="this.style.visibility='hidden'">` : '<span style="width:48px"></span>'}<div style="flex:1;min-width:0"><div class="nm">${esc(it.name)}</div><div class="bs">${esc(it.base || '')}${it.slot ? ' · ' + esc(it.slot) : ''}</div><div class="wy">${esc(T(it.why))}</div></div><span class="cbadge ${c[1]}">${c[0]}</span></div>`;
    }).join('');
  }).join('');
  const sure = d.items.filter(it => (CONF[it.conf] || CONF.info)[1] === 'ok').length;
  v.innerHTML = `<div class="srccard">${STYLE}<h2>${esc(P(d.ru, d.en))}</h2>${I18N_RU() && d.en && d.en !== d.ru ? `<div class="en">${esc(d.en)}</div>` : ''}
    <span class="tag">${esc(T(d.typeRu))}</span>${d.area ? `<span class="tag">${I18N_RU() ? esc(d.area.ru) + ' · ' + esc(d.area.en) : esc(d.area.en)}</span>` : ''}<span class="tag">Уникальных: ${d.items.length}${sure ? ` · подтверждено ${sure}` : ''}</span>
    ${d.note ? `<div class="note">${esc(T(d.note))}</div>` : ''}${body}</div>`;
  v.querySelector('.srccard').onclick = e => {
    const it = e.target.closest('.it'); if (it && ctx.goUnique) ctx.goUnique(it.dataset.u);
  };
  if (ctx.bindTip) ctx.bindTip(v.querySelector('.srccard'), '.it', 'u');
  ctx.$('#info').textContent = `${P(d.ru, d.en)} — ${d.items.length} уник.`;
}

const I18N_RU = () => !window.I18N || I18N.lang !== 'en';

// language switch: redraw what this section drew from data (names come from the data, so the dictionary alone is not enough)
window.addEventListener('i18n:change', () => {
  const dom = document.querySelector('#cls');
  if (dom && dom.dataset.src) {          // the Sources tab is open: reload the list and reselect the open source
    window.__srcPick = curId;
    const q = document.querySelector('#q'); if (q) q.dispatchEvent(new Event('input', { bubbles: true }));
  }
  const b = document.querySelector('#info .srcblk');
  if (b && lastBlock) b.outerHTML = srcBlock(lastBlock);
});
