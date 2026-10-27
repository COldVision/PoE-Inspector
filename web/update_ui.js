// Update notice: checks GitHub Releases through the local server (only when update.json names a repository) and offers download + restart. Nothing happens without a click.
(function () {
  const L = (ru, en) => (window.I18N ? I18N.pick(ru, en) : ru);
  const j = u => fetch(u).then(r => r.json());
  let box, st = null;
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const css = document.createElement('style');
  css.textContent = '#upd{position:fixed;left:16px;bottom:16px;z-index:200;max-width:380px;background:var(--panel,#1a162f);border:1px solid var(--acc,#fc4c70);border-radius:12px;padding:14px 16px;box-shadow:0 8px 30px #000a;font:15px/1.45 inherit;color:var(--text,#fff)}' +
    '#upd b{display:block;font-size:16px;margin-bottom:4px}#upd small{display:block;color:var(--dim,#b9aed3);margin:2px 0 8px;white-space:pre-wrap;max-height:90px;overflow:auto}' +
    '#upd button{background:var(--acc,#fc4c70);color:var(--on-acc,#030409);border:0;border-radius:8px;padding:7px 14px;font:600 14px inherit;cursor:pointer;margin-right:8px}' +
    '#upd button.x{background:transparent;color:var(--dim,#b9aed3);border:1px solid var(--line,#3e2d57)}#upd .bar{height:6px;background:var(--surface,#251d3b);border-radius:4px;overflow:hidden;margin:6px 0}#upd .bar i{display:block;height:100%;background:var(--acc,#fc4c70)}';
  document.head.appendChild(css);

  function draw() {
    if (!st || !['available', 'downloading', 'ready', 'error'].includes(st.phase) || (st.phase === 'error' && !st.shown)) { if (box) box.remove(); box = null; return; }
    if (!box) { box = document.createElement('div'); box.id = 'upd'; box.setAttribute('role', 'status'); document.body.appendChild(box); }
    let h = '';
    if (st.phase === 'available') h = `<b>${L('Доступно обновление', 'Update available')} ${esc(st.latest)}</b><small>${L('Сейчас установлена', 'Installed')} ${esc(st.current)}\n${esc(st.notes)}</small><button data-a="dl">${L('Скачать', 'Download')}</button><button class="x" data-a="no">${L('Позже', 'Later')}</button>`;
    else if (st.phase === 'downloading') h = `<b>${L('Скачивание обновления…', 'Downloading update…')}</b><div class="bar"><i style="width:${st.pct || 3}%"></i></div>`;
    else if (st.phase === 'ready') h = `<b>${L('Обновление скачано', 'Update downloaded')}</b><small>${L('Программа перезапустится и применит его.', 'The app will restart and apply it.')}</small><button data-a="go">${L('Перезапустить', 'Restart')}</button><button class="x" data-a="no">${L('Позже', 'Later')}</button>`;
    else h = `<b>${L('Не удалось обновить', 'Update failed')}</b><small>${esc(st.error)}</small><button class="x" data-a="no">${L('Закрыть', 'Close')}</button>`;
    box.innerHTML = h;
  }
  async function poll() {
    st = Object.assign(await j('/api/update/status'), { shown: st && st.shown });
    draw();
    if (st.phase === 'downloading') setTimeout(poll, 700);
  }
  document.addEventListener('click', async e => {
    const b = e.target.closest('#upd button'); if (!b) return;
    const a = b.dataset.a;
    if (a === 'no') { st.phase = 'idle'; draw(); }
    if (a === 'dl') { st = Object.assign(await j('/api/update/download'), { shown: true }); draw(); poll(); }
    if (a === 'go') { await j('/api/update/restart'); box.innerHTML = `<b>${L('Перезапуск…', 'Restarting…')}</b>`; }
  });
  window.addEventListener('i18n:change', draw);
  (async () => {
    try { st = Object.assign(await j('/api/update/check'), { shown: false }); draw(); } catch (e) { /* offline */ }
  })();
})();
