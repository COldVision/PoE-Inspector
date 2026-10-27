// Files tab: folder catalogue of Bundles2 with breadcrumbs; the search box above it switches the list to path search results.
let cur = '';          // current folder, '' = root
let selected = '';     // highlighted file path

const fmt = n => n < 1024 ? n + ' Б' : n < 1048576 ? (n / 1024).toFixed(1) + ' КБ' : (n / 1048576).toFixed(1) + ' МБ';
const ICO = { dds: '🖼', png: '🖼', jpg: '🖼', jpeg: '🖼', bmp: '🖼', smd: '🧊', fmt: '🧊', tgm: '🧊', ogg: '🔊', wav: '🔊', bk2: '🎬', webm: '🎬' };
const ico = n => ICO[n.split('.').pop()] || '📄';

// ctx: {list, query, api, esc, open(path,size)}; call on every tab load / search change
export async function renderFiles(ctx) {
  const { list, api, esc } = ctx, q = ctx.query.trim();
  const bind = (rows, nav) => {
    list.onclick = e => {
      const r = e.target.closest('[data-k]'); if (!r) return;
      const k = r.dataset.k, v = r.dataset.v;
      if (k === 'dir') { cur = v; ctx.reload(true); return; }
      selected = v; list.querySelectorAll('.row.on').forEach(x => x.classList.remove('on')); r.classList.add('on');
      if (nav) cur = v.slice(0, Math.max(0, v.lastIndexOf('/')));
      ctx.open(v, +r.dataset.s);
    };
  };
  const row = (k, v, name, sub, s = 0) =>
    `<div class="row${k === 'file' && v === selected ? ' on' : ''}" data-k="${k}" data-v="${esc(v)}" data-s="${s}"><div>${k === 'dir' ? '📁' : ico(name)} ${esc(name)}</div><span>${esc(sub)}</span></div>`;
  if (q) {
    const rows = await api(`/api/files?q=${encodeURIComponent(q)}&limit=500`);
    list.innerHTML = `<div class="msg">Результаты поиска: ${rows.length}${rows.length >= 500 ? '+' : ''}. Очистите строку, чтобы вернуться к папкам.</div>` +
      rows.map(r => row('file', r.path, r.path.split('/').pop(), r.path + ' · ' + fmt(r.size), r.size)).join('');
    bind(rows, true); return;
  }
  const d = await api('/api/dir?path=' + encodeURIComponent(cur));
  const parts = cur ? cur.split('/') : [];
  const crumbs = ['<a href="#" data-k="dir" data-v="">Bundles2</a>'].concat(parts.map((p, i) => `<a href="#" data-k="dir" data-v="${esc(parts.slice(0, i + 1).join('/'))}">${esc(p)}</a>`)).join(' / ');
  list.innerHTML = `<div class="msg" style="line-height:1.8">${crumbs}</div>` +
    (cur ? row('dir', parts.slice(0, -1).join('/'), '..', 'на уровень выше') : '') +
    d.folders.map(f => row('dir', (cur ? cur + '/' : '') + f, f, 'папка')).join('') +
    d.files.map(f => row('file', (cur ? cur + '/' : '') + f.name, f.name, fmt(f.size), f.size)).join('') ||
    '<div class="msg">Пусто</div>';
  list.onclick = null;
  bind(d);
  list.querySelectorAll('.msg a').forEach(a => a.onclick = e => { e.preventDefault(); cur = a.dataset.v; ctx.reload(true); });
}
