// Section "Справочник": passive skills, classes and ascendancies, areas, quests, achievements. One list + one generic card in the style of the game's cards.
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
let sections = null;

export async function refControls(api) {
  if (!sections) sections = await api('/api/refsections');
  const dom = document.querySelector('#cls');
  if (!dom.dataset.ref) {
    dom.dataset.ref = '1';
    dom.dataset.items = dom.innerHTML;   // the item-class list, put back when leaving the tab
    dom.innerHTML = sections.map(s => `<option value="${s.k}">${esc(s.ru)}</option>`).join('');
    dom.value = sections[0].k;
  }
}

export function fillFilter(filters) {
  const g = document.querySelector('#gsel'), cur = g.value;
  g.innerHTML = '<option value="">Все</option>' + (filters || []).map(f => `<option value="${esc(f.k)}">${esc(f.ru)}</option>`).join('');
  g.value = [...g.options].some(o => o.value === cur) ? cur : '';
  g.style.display = (filters || []).length ? '' : 'none';
}

export function leaveRef() {
  const dom = document.querySelector('#cls');
  if (dom && dom.dataset.ref) { dom.innerHTML = dom.dataset.items; delete dom.dataset.ref; dom.value = ''; }
}

export const refRow = r => [r.name, r.sub || '', r];

let last = null;   // the card on screen, redrawn when the interface language changes
export async function showRefCard(ctx, sec, row) {
  last = { ctx, sec, row };
  const d = await ctx.api(`/api/refcard?sec=${encodeURIComponent(sec)}&id=${encodeURIComponent(row.id)}&lang=${window.I18N ? I18N.lang : 'ru'}`);
  const v = ctx.$('#view'); v.style.display = '';
  const kv = (d.kv || []).map(([k, val, key]) => `<div class="rk${key ? ' key' : ''}"><span>${esc(k)}:</span> <b>${esc(val)}</b></div>`).join('');
  const blocks = (d.blocks || []).map(b => `<h4>${esc(b.h)} · ${b.items.length}</h4><div class="rb">${b.items.map(x => `<div class="ri${x.key ? ' key' : ''}"><b>${esc(x.t)}</b>${x.s ? `<span>${esc(x.s)}</span>` : ''}</div>`).join('')}</div>`).join('');
  v.innerHTML = `<div class="refcard"><style>
    .refcard{position:absolute;inset:0;overflow:auto;padding:22px 30px;font-family:'Palatino Linotype','Book Antiqua',Palatino,Georgia,serif;font-size:18px;line-height:1.55}
    .refcard .rh{display:flex;gap:14px;align-items:center}.refcard .rh img{width:64px;height:64px;object-fit:contain}
    .refcard .rt{font-size:28px;color:#9fe3d3;line-height:1.2}.refcard .rs{color:#7d8a96;font-size:15px}
    .refcard .tg{margin:8px 0;color:#cfd6dc;text-decoration:underline}
    .refcard .rk{font-size:19px;line-height:1.6}.refcard .rk span{color:#7fb8ad}.refcard .rk b{font-weight:400;color:#fff}
    .refcard .rk.key{background:linear-gradient(90deg,rgba(255,200,80,.22),rgba(255,200,80,.04));border-left:3px solid #ffc850;border-radius:3px;padding:1px 10px;margin:3px 0;max-width:520px}.refcard .rk.key b{color:#ffe08a;font-weight:700;font-size:1.15em}
    .refcard .rd{font-style:italic;color:#d9c89a;text-align:center;margin:14px auto;max-width:760px}
    .refcard .rl{color:#c2c2ff;background:rgba(120,120,255,.07);border:1px solid rgba(150,150,255,.18);border-radius:6px;padding:6px 14px;margin:12px auto;max-width:760px;text-align:center;font-size:19px}.refcard .rl div+div{border-top:1px solid rgba(190,190,255,.22);margin-top:6px;padding-top:6px}
    .refcard .rr{color:#9a9a9a;font-size:15px;text-align:center;font-style:italic}.refcard .rf{font-style:italic;color:#e8832d;text-align:center;margin:12px auto;max-width:760px}
    .refcard h4{margin:18px 0 6px;color:#9fe3d3;font-weight:400;font-size:20px}.refcard .rb{max-width:900px}
    .refcard .ri{padding:6px 10px;border-bottom:1px solid rgba(255,255,255,.07)}.refcard .ri b{font-weight:400;color:#f1f1f1}.refcard .ri span{display:block;color:#aab0ff;font-size:16px}.refcard .ri.key b{color:#ffe08a}
    </style>
    <div class="rh">${d.icon ? `<img src="/api/icon?size=128&path=${encodeURIComponent(d.icon)}" onerror="this.style.visibility='hidden'">` : ''}<div><div class="rt">${esc(d.title)}</div><div class="rs">${esc(d.sub)}</div></div></div>
    ${(d.tags || []).filter(Boolean).length ? `<div class="tg">${d.tags.filter(Boolean).map(esc).join(', ')}</div>` : ''}
    ${kv}
    ${d.desc ? `<div class="rd">${esc(d.desc)}</div>` : ''}
    ${(d.lines || []).length ? `<div class="rl">${d.lines.map(t => `<div>${esc(t)}</div>`).join('')}</div>` : ''}
    ${(d.reminder || []).length ? `<div class="rr">${d.reminder.map(esc).join('<br>')}</div>` : ''}
    ${d.flavour ? `<div class="rf">${esc(d.flavour)}</div>` : ''}
    ${blocks}</div>`;
  ctx.$('#info').textContent = d.title;
}

window.addEventListener('i18n:change', () => {
  if (!last || !last.ctx.$('#view').querySelector('.refcard')) return;
  const { ctx, sec, row } = last;
  setTimeout(() => showRefCard(ctx, sec, row).catch(() => {}), 150);   // after the list reload
});
