// Image viewer for the Files tab: zoom (wheel) / pan (drag), channels, backgrounds, save as PNG.
const BGS = { checker: 'conic-gradient(#2a2540 25%,#1d1a30 0 50%,#2a2540 0 75%,#1d1a30 0) 0 0/16px 16px', dark: '#0b0912', light: '#e8e4f0', magenta: '#ff00ff' };

export function hideImage(host) { const o = host.querySelector(':scope > .imgv'); if (o) o.remove(); }

export function showImage(host, path, esc) {
  hideImage(host);
  const el = document.createElement('div'); el.className = 'imgv';
  const url = '/api/icon?size=0&path=' + encodeURIComponent(path);
  el.innerHTML = `<div class="imgtb" role="toolbar" aria-label="Просмотр изображения">
      <span class="imgnm">${esc(path.split('/').pop())}</span><span class="imginfo" role="status">Загрузка…</span>
      <select class="ch" aria-label="Канал"><option value="rgba">RGB + альфа</option><option value="rgb">RGB (без альфы)</option><option value="r">R</option><option value="g">G</option><option value="b">B</option><option value="a">Альфа</option></select>
      <select class="bg" aria-label="Фон"><option value="checker">Шахматка</option><option value="dark">Тёмный</option><option value="light">Светлый</option><option value="magenta">Пурпурный</option></select>
      <button class="fit" title="Вписать в окно">Вписать</button><button class="one" title="Масштаб 100%">1:1</button><button class="sv" title="Сохранить изображение в PNG (выбранный канал и полное разрешение)">Сохранить PNG</button></div>
    <div class="imgst"><canvas></canvas></div>`;
  host.appendChild(el);
  const st = el.querySelector('.imgst'), cv = el.querySelector('canvas'), info = el.querySelector('.imginfo'), ctx = cv.getContext('2d', { willReadFrequently: true });
  let img = null, src = null, k = 1, x = 0, y = 0;
  const bgSel = el.querySelector('.bg'), chSel = el.querySelector('.ch');
  const apply = () => { cv.style.transform = `translate(${x}px,${y}px) scale(${k})`; info.textContent = img ? `${img.naturalWidth}×${img.naturalHeight} · ${Math.round(k * 100)}%` : ''; };
  const fit = () => { const w = st.clientWidth, h = st.clientHeight; k = Math.min(w / img.naturalWidth, h / img.naturalHeight, 1); x = (w - img.naturalWidth * k) / 2; y = (h - img.naturalHeight * k) / 2; apply(); };
  const draw = () => {
    if (!src) return;
    const m = chSel.value; ctx.putImageData(src, 0, 0);
    if (m === 'rgba') return;
    const d = ctx.getImageData(0, 0, cv.width, cv.height), p = d.data;
    for (let i = 0; i < p.length; i += 4) {
      if (m === 'rgb') p[i + 3] = 255;
      else { const v = m === 'r' ? p[i] : m === 'g' ? p[i + 1] : m === 'b' ? p[i + 2] : p[i + 3]; p[i] = p[i + 1] = p[i + 2] = v; p[i + 3] = 255; }
    }
    ctx.putImageData(d, 0, 0);
  };
  const setBg = () => { st.style.background = BGS[bgSel.value]; };
  setBg(); bgSel.onchange = setBg; chSel.onchange = draw;
  const im = new Image();
  im.onload = () => {
    img = im; cv.width = im.naturalWidth; cv.height = im.naturalHeight; ctx.drawImage(im, 0, 0); src = ctx.getImageData(0, 0, cv.width, cv.height);
    cv.style.cssText += ';width:' + im.naturalWidth + 'px;height:' + im.naturalHeight + 'px'; cv.style.imageRendering = 'auto'; fit();
  };
  im.onerror = () => { info.textContent = 'Не удалось показать изображение (формат не поддерживается)'; };
  im.src = url;
  st.onwheel = e => {
    if (!img) return; e.preventDefault();
    const r = st.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top, nk = Math.max(.05, Math.min(32, k * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    x = px - (px - x) * nk / k; y = py - (py - y) * nk / k; k = nk; cv.style.imageRendering = k >= 3 ? 'pixelated' : 'auto'; apply();
  };
  let drag = null;
  st.onpointerdown = e => { drag = { sx: e.clientX - x, sy: e.clientY - y }; st.setPointerCapture(e.pointerId); st.style.cursor = 'grabbing'; };
  st.onpointermove = e => { if (drag) { x = e.clientX - drag.sx; y = e.clientY - drag.sy; apply(); } };
  st.onpointerup = st.onpointercancel = () => { drag = null; st.style.cursor = ''; };
  st.ondblclick = () => img && fit();
  el.querySelector('.fit').onclick = () => img && fit();
  el.querySelector('.one').onclick = () => { if (!img) return; const w = st.clientWidth, h = st.clientHeight; k = 1; x = (w - img.naturalWidth) / 2; y = (h - img.naturalHeight) / 2; cv.style.imageRendering = 'auto'; apply(); };
  el.querySelector('.sv').onclick = () => {
    const name = path.split('/').pop().replace(/\.[^.]+$/, '');
    if (chSel.value === 'rgba') { const a = document.createElement('a'); a.href = url + '&dl=1'; a.download = name + '.png'; document.body.appendChild(a); a.click(); a.remove(); return; }   // original, straight from the server
    cv.toBlob(b => { const u = URL.createObjectURL(b), a = document.createElement('a'); a.href = u; a.download = name + '_' + chSel.value + '.png'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 5000); }, 'image/png');
  };
  return el;
}
