import * as THREE from 'three';
// Viewport recorder: PNG sequence (ZIP, transparent, frame-exact) or WebM (real time, alpha when the browser supports it).
const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc32 = u8 => { let c = 0xFFFFFFFF; for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };

// store-only ZIP (PNG is already compressed)
function zip(files) {
  const enc = new TextEncoder(), parts = [], cen = []; let off = 0;
  const now = new Date(), dosT = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1), dosD = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  for (const f of files) {
    const nm = enc.encode(f.name), crc = crc32(f.data), h = new DataView(new ArrayBuffer(30));
    h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint16(10, dosT, true); h.setUint16(12, dosD, true); h.setUint32(14, crc, true);
    h.setUint32(18, f.data.length, true); h.setUint32(22, f.data.length, true); h.setUint16(26, nm.length, true);
    parts.push(h.buffer, nm, f.data);
    const c = new DataView(new ArrayBuffer(46));
    c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true); c.setUint16(12, dosT, true); c.setUint16(14, dosD, true); c.setUint32(16, crc, true);
    c.setUint32(20, f.data.length, true); c.setUint32(24, f.data.length, true); c.setUint16(28, nm.length, true); c.setUint32(42, off, true);
    cen.push(c.buffer, nm); off += 30 + nm.length + f.data.length;
  }
  const csz = cen.reduce((a, b) => a + b.byteLength, 0), e = new DataView(new ArrayBuffer(22));
  e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true); e.setUint32(12, csz, true); e.setUint32(16, off, true);
  return new Blob([...parts, ...cen, e.buffer], { type: 'application/zip' });
}

const save = (blob, name) => { const u = URL.createObjectURL(blob), a = document.createElement('a'); a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 10000); };
const blobOf = c => new Promise(r => c.toBlob(r, 'image/png'));
const tick = () => new Promise(r => setTimeout(r, 0));
// Rendering is frame-exact, so the speed of the picture does not depend on how long a frame takes; only the total time does. To keep it short the PNG encoding / upload of the
// previous frames runs while the next one renders: toBlob() takes its snapshot at the call, so a frame can be queued right after render().
function pipeline(depth, sink) {
  const q = []; let err = null, tail = Promise.resolve();   // the encoders (jobs) run concurrently, the sink gets the results strictly in frame order
  return {
    async push(job) {
      if (err) throw err;
      q.push(tail = tail.then(() => job).then(sink).catch(e => { err = e; }));
      while (q.length > depth) await q.shift();
      if (err) throw err;
    },
    async drain() { while (q.length) await q.shift(); if (err) throw err; },
  };
}

// the scene's background is CSS on the viewer (the canvas itself is transparent): draw the same gradient / picture on a canvas so it can be rendered into the frames
function splitTop(str) { const out = []; let d = 0, cur = ''; for (const ch of str) { if (ch === '(') d++; if (ch === ')') d--; if (ch === ',' && d === 0) { out.push(cur.trim()); cur = ''; } else cur += ch; } if (cur.trim()) out.push(cur.trim()); return out; }
function paintCss(g, css, w, h) {
  css = (css || '').trim();
  const m = /^(radial|linear)-gradient\((.*)\)$/s.exec(css);
  if (!m) { g.fillStyle = css || '#000'; g.fillRect(0, 0, w, h); return; }
  const parts = splitTop(m[2]); if (/^(to |\d+deg|circle|ellipse)/.test(parts[0])) parts.shift();
  const stops = parts.map((p, i) => { const mm = /^(.*?)(?:\s+(\d+(?:\.\d+)?)%)?$/.exec(p); return [mm[1].trim(), mm[2] != null ? +mm[2] / 100 : i / Math.max(1, parts.length - 1)]; });
  let gr;
  if (m[1] === 'radial') { gr = g.createRadialGradient(0, 0, 0, 0, 0, 1); stops.forEach(([c, t]) => gr.addColorStop(Math.min(1, Math.max(0, t)), c)); g.save(); g.translate(w / 2, h / 2); g.scale(w / 2 * Math.SQRT2, h / 2 * Math.SQRT2); g.fillStyle = gr; g.fillRect(-1, -1, 2, 2); g.restore(); }
  else { gr = g.createLinearGradient(0, 0, 0, h); stops.forEach(([c, t]) => gr.addColorStop(Math.min(1, Math.max(0, t)), c)); g.fillStyle = gr; g.fillRect(0, 0, w, h); }
}
async function backgroundTexture(V, w, h) {
  const k = Math.min(1, 2048 / Math.max(w, h)), cw = Math.max(2, Math.round(w * k)), ch = Math.max(2, Math.round(h * k)), cv = document.createElement('canvas'); cv.width = cw; cv.height = ch;
  const g = cv.getContext('2d');
  if (V.bgimg) {
    const img = await new Promise((res, rej) => { const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = rej; i.src = '/api/icon?fmt=jpg&size=1600&path=' + encodeURIComponent(V.bgimg); }).catch(() => null);
    if (img) { const sc = Math.max(cw / img.width, ch / img.height); g.drawImage(img, (cw - img.width * sc) / 2, (ch - img.height * sc) / 2, img.width * sc, img.height * sc); const ov = g.createLinearGradient(0, 0, 0, ch); ov.addColorStop(0, 'rgba(0,0,0,.4)'); ov.addColorStop(1, 'rgba(0,0,0,.67)'); g.fillStyle = ov; g.fillRect(0, 0, cw, ch); }
    else paintCss(g, V.bg, cw, ch);
  } else paintCss(g, V.bg, cw, ch);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export function initRecorder(getV, host, nameFn) {
  const box = document.createElement('div'); box.className = 'recbox';
  box.innerHTML = `<button class="ctl rec" aria-label="Запись окна" title="Запись окна (с прозрачным фоном)" aria-expanded="false"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg></button>
  <div class="recpanel" hidden>
    <label>Формат<select class="rf" aria-label="Формат записи"><option value="webma">WebM VP9 с прозрачностью (для Premiere с плагином)</option><option value="png">PNG-последовательность (ZIP, с прозрачностью)</option><option value="mp4">MP4 H.264 (для Premiere, без прозрачности)</option><option value="webm">WebM (видео, не для монтажа)</option></select></label>
    <label>Конец<select class="rm" aria-label="Когда остановить"><option value="end">Конец анимации</option><option value="stop">По кнопке «Стоп»</option></select></label>
    <label>Кадров/с<select class="rfps" aria-label="Частота кадров"><option>24</option><option selected>30</option><option>60</option></select></label>
    <label>Размер<select class="rres" aria-label="Разрешение записи"><option value="win">Как окно</option><option value="1080">1920×1080 (1080p)</option><option value="1440">2560×1440 (1440p)</option><option value="2160">3840×2160 (4K)</option></select></label>
    <label class="chk"><input type="checkbox" class="rfit"> Персонаж на весь кадр</label>
    <label class="chk"><input type="checkbox" class="rt" checked> Прозрачный фон (без галочки фон записывается)</label>
    <button class="go">Начать запись</button><div class="rs" role="status"></div>
  </div>`;
  host.appendChild(box);
  const $q = s => box.querySelector(s), btn = $q('.rec'), panel = $q('.recpanel'), go = $q('.go'), st = $q('.rs');
  btn.onclick = () => { panel.hidden = !panel.hidden; btn.setAttribute('aria-expanded', String(!panel.hidden)); };
  let stopReq = false, busy = false;
  const RES = { '1080': [1920, 1080], '1440': [2560, 1440], '2160': [3840, 2160] };

  // render size independent of the window (the preview stays aspect-correct), camera framing on the whole animation
  function setRes(V, wh) {
    const sz = V.r.getSize(new THREE.Vector2()), c = V.r.domElement.style;
    const snap = { w: sz.x, h: sz.y, pr: V.r.getPixelRatio(), aspect: V.cam.aspect, fov: V.cam.fov, pos: V.cam.position.clone(), target: V.ctl.target.clone(), fit: c.objectFit };
    if (wh) { V.recSize = true; V.r.setPixelRatio(1); V.r.setSize(wh[0], wh[1], false); V.cam.aspect = wh[0] / wh[1]; V.cam.updateProjectionMatrix(); c.objectFit = 'contain'; }
    return snap;
  }
  function resetRes(V, snap) {
    V.recSize = false; V.r.setPixelRatio(snap.pr); V.r.setSize(snap.w, snap.h, false); V.cam.aspect = snap.aspect; V.cam.fov = snap.fov;
    V.cam.position.copy(snap.pos); V.ctl.target.copy(snap.target); V.cam.updateProjectionMatrix(); V.ctl.update(); V.r.domElement.style.objectFit = snap.fit;
  }
  // union of the skeleton's joints over the whole clip (or the model's box) -> camera distance so the character fills the frame
  function frameCharacter(V, fps, steps) {
    const E = V.editor, box = new THREE.Box3(), v = new THREE.Vector3();
    const grab = () => { if (E && E.bones && E.root) { E.root.updateMatrixWorld(true); for (const b of E.bones) { b.getWorldPosition(v); box.expandByPoint(v); } } };
    if (E && E.bones && E.root) {
      const act = E.action; if (act && steps) { act.time = 0; E.mixer.update(0); for (let i = 0; i < steps; i++) { grab(); E.update(1 / fps); } act.time = 0; E.mixer.update(0); } else grab();
      box.min.addScalar(-.1); box.max.addScalar(.1); box.max.y += .1; box.min.y = Math.min(box.min.y, 0);
    } else if (V.cur) { box.setFromObject(V.cur); }
    if (box.isEmpty()) return;
    const c = box.getCenter(new THREE.Vector3()), dir = V.cam.position.clone().sub(V.ctl.target); if (dir.lengthSq() < 1e-6) dir.set(0, .3, 1); dir.normalize();
    const corners = []; for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) corners.push(new THREE.Vector3(x, y, z));
    let dist = box.getSize(v).length() * 1.5 + 1;
    for (let it = 0; it < 12; it++) {
      V.cam.position.copy(c).addScaledVector(dir, dist); V.ctl.target.copy(c); V.cam.lookAt(c); V.cam.updateMatrixWorld(true); V.cam.updateProjectionMatrix();
      let m = 0; for (const p of corners) { const q = p.clone().project(V.cam); m = Math.max(m, Math.abs(q.x), Math.abs(q.y)); }
      dist *= Math.max(.2, m / .97);
      if (Math.abs(m - .97) < .008) break;
    }
    V.cam.position.copy(c).addScaledVector(dir, dist); V.cam.lookAt(c); V.cam.updateProjectionMatrix(); V.ctl.update();
  }

  async function prep(V, transparent) {
    const s = { bg: V.scene.background, fog: V.scene.fog, composer: V.composer, vis: [], clear: V.r.getClearAlpha(), tex: null };
    if (!transparent && !V.scene.background) {   // record the background too (the studio gradient lives in CSS, not in the scene)
      const sz = V.r.getSize(new THREE.Vector2()); s.tex = await backgroundTexture(V, sz.x, sz.y); V.scene.background = s.tex;
    }
    V.composer = null;   // post-processing (atmosphere, bloom, LUT, depth targets) at 1080p+ is what slowed recordings with a background down; the frame-exact paths render directly anyway
    if (transparent) {
      V.scene.background = null; V.scene.fog = null;
      for (const o of [V.grid, V.gridFloor, V.floor, V.catcher, V.editor && V.editor.marker]) if (o) { s.vis.push([o, o.visible]); o.visible = false; }
      V.r.setClearColor(0x000000, 0);
    }
    V.rec = true; return s;
  }
  function restore(V, s) {
    V.rec = false; V.scene.background = s.bg; V.scene.fog = s.fog; V.composer = s.composer; s.vis.forEach(([o, v]) => { o.visible = v; });
    V.r.setClearAlpha(s.clear); if (s.tex) s.tex.dispose();
  }

  async function recordPng(V, fps, untilEnd, transparent, wh, fit) {
    const E = V.editor, act = E && E.action, clip = act && act.getClip();
    const dur = clip ? clip.duration / (E.speed || 1) : 0;
    if (untilEnd && !dur) throw new Error('Анимация не выбрана — выберите «По кнопке Стоп»');
    const total = untilEnd ? Math.max(1, Math.round(dur * fps)) : Infinity, dt = 1 / fps, files = [], pad = n => String(n).padStart(5, '0');
    const view = setRes(V, wh); if (fit) frameCharacter(V, fps, total === Infinity ? Math.round(fps * 4) : total);
    if (act) { act.reset(); act.paused = false; E.mixer.update(0); }
    const s = await prep(V, transparent); let bytes = 0;
    try {
      const pl = pipeline(4, async ({ i, b }) => { files.push({ name: `frame_${pad(i)}.png`, data: new Uint8Array(await b.arrayBuffer()) }); bytes += b.size; });
      for (let i = 0; i < total && !stopReq; i++) {
        if (E) E.update(dt);
        V.ctl.update(); V.r.render(V.scene, V.cam);
        await pl.push(blobOf(V.r.domElement).then(b => ({ i, b })));
        st.textContent = `Кадров: ${i + 1}${untilEnd ? ' / ' + total : ''} · ${(bytes / 1048576).toFixed(0)} МБ`;
        if (bytes > 1.4e9) { stopReq = true; st.textContent += ' — лимит памяти, останавливаю'; }
        if (i % 3 === 0) await tick();
      }
      await pl.drain();
    } finally { var outSize = V.r.domElement.width + '×' + V.r.domElement.height; restore(V, s); resetRes(V, view); }
    if (!files.length) throw new Error('Нет кадров');
    save(zip(files), `${nameFn()}_${fps}fps.zip`);
    return `Сохранено ${files.length} кадров (${outSize}), PNG ${transparent ? 'с альфа-каналом' : 'с фоном сцены'}`;
  }

  async function recordWebm(V, fps, untilEnd, transparent, wh, fit) {
    const E = V.editor, act = E && E.action, clip = act && act.getClip();
    const dur = clip ? clip.duration / (E.speed || 1) : 0;
    if (untilEnd && !dur) throw new Error('Анимация не выбрана — выберите «По кнопке Стоп»');
    const mime = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'].find(m => MediaRecorder.isTypeSupported(m));
    if (!mime) throw new Error('WebM не поддерживается браузером');
    const view = setRes(V, wh); if (fit) frameCharacter(V, fps, dur ? Math.round(dur * fps) : Math.round(fps * 4));
    const s = await prep(V, transparent); V.rec = false;   // real time: let the normal loop render
    const px = V.r.domElement.width * V.r.domElement.height, bits = Math.min(90e6, Math.max(12e6, Math.round(px * fps * 0.22)));
    const stream = V.r.domElement.captureStream(fps), rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: bits }), chunks = [];
    rec.ondataavailable = e => e.data.size && chunks.push(e.data);
    if (act) { act.reset(); act.paused = false; }
    const done = new Promise(r => { rec.onstop = r; });
    rec.start(250); const t0 = performance.now();
    try {
      while (!stopReq && (!untilEnd || (performance.now() - t0) / 1000 < dur)) { st.textContent = `Запись: ${((performance.now() - t0) / 1000).toFixed(1)} c`; await new Promise(r => setTimeout(r, 100)); }
    } finally { rec.stop(); await done; restore(V, s); resetRes(V, view); }
    save(new Blob(chunks, { type: 'video/webm' }), `${nameFn()}.webm`);
    return 'Сохранено видео WebM' + (transparent ? ' (альфа зависит от плеера)' : '') + '. Для Premiere выберите MP4 или PNG-последовательность';
  }

  // MP4 / H.264 through WebCodecs: constant frame rate, frame-exact (like the PNG path), a proper index: opens in Premiere / DaVinci. No alpha (H.264 has none): the background is recorded.
  async function recordMp4(V, fps, untilEnd, transparent, wh, fit) {
    if (!('VideoEncoder' in window)) throw new Error('Нужен браузер с WebCodecs (Chrome / Edge)');
    const E = V.editor, act = E && E.action, clip = act && act.getClip();
    const dur = clip ? clip.duration / (E.speed || 1) : 0;
    if (untilEnd && !dur) throw new Error('Анимация не выбрана — выберите «По кнопке Стоп»');
    const lib = await import('https://cdn.jsdelivr.net/npm/mp4-muxer@5.1.3/+esm').catch(() => null);
    if (!lib) throw new Error('Не удалось загрузить мультиплексор MP4 (нужен интернет)');
    if (!wh) { const sz = V.r.getSize(new THREE.Vector2()); wh = [Math.max(2, Math.floor(sz.x / 2) * 2), Math.max(2, Math.floor(sz.y / 2) * 2)]; }   // H.264 wants even sizes
    const total = untilEnd ? Math.max(1, Math.round(dur * fps)) : Infinity, dt = 1 / fps;
    const view = setRes(V, wh); if (fit) frameCharacter(V, fps, total === Infinity ? Math.round(fps * 4) : total);
    if (act) { act.reset(); act.paused = false; E.mixer.update(0); }
    const w = V.r.domElement.width, h = V.r.domElement.height, bitrate = Math.min(80e6, Math.max(8e6, Math.round(w * h * fps * 0.12)));
    let codec = null;
    for (const c of ['avc1.640034', 'avc1.640033', 'avc1.64002a', 'avc1.4d0028', 'avc1.42001f']) { try { const r = await VideoEncoder.isConfigSupported({ codec: c, width: w, height: h, bitrate, framerate: fps }); if (r.supported) { codec = c; break; } } catch (e) { /* next */ } }
    if (!codec) throw new Error(`H.264 ${w}×${h} не поддерживается этим браузером`);
    const target = new lib.ArrayBufferTarget(), muxer = new lib.Muxer({ target, video: { codec: 'avc', width: w, height: h, frameRate: fps }, fastStart: 'in-memory' });
    let err = null; const enc = new VideoEncoder({ output: (chunk, meta) => muxer.addVideoChunk(chunk, meta), error: e => { err = e; } });
    enc.configure({ codec, width: w, height: h, bitrate, framerate: fps, latencyMode: 'quality' });
    const s = await prep(V, false); let n = 0;
    try {
      for (let i = 0; i < total && !stopReq && !err; i++) {
        if (E) E.update(dt);
        V.ctl.update(); V.r.render(V.scene, V.cam);
        const f = new VideoFrame(V.r.domElement, { timestamp: Math.round(i * 1e6 / fps), duration: Math.round(1e6 / fps) });
        enc.encode(f, { keyFrame: i % (fps * 2) === 0 }); f.close(); n++;
        while (enc.encodeQueueSize > 6) await new Promise(r => setTimeout(r, 4));
        st.textContent = `Кадров: ${i + 1}${untilEnd ? ' / ' + total : ''}`;
        if (i % 3 === 0) await tick();
      }
      await enc.flush();
    } finally { restore(V, s); resetRes(V, view); }
    if (err) throw err;
    if (!n) throw new Error('Нет кадров');
    muxer.finalize(); save(new Blob([target.buffer], { type: 'video/mp4' }), `${nameFn()}_${fps}fps.mp4`);
    return `Сохранён MP4 ${w}×${h}, ${fps} к/с, ${n} кадров, H.264` + (transparent ? ' (в MP4 нет прозрачности: фон записан; для прозрачного фона выберите PNG-последовательность)' : '');
  }

  // WebM VP9 with alpha through the local server (ffmpeg): frame-exact, constant frame rate, duration + seek index in the file; for editing programs that import WebM (Premiere with a WebM plugin)
  const post = async (u, body) => { const r = await fetch(u, { method: 'POST', body }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status)); return j; };
  async function recordWebmAlpha(V, fps, untilEnd, transparent, wh, fit) {
    const E = V.editor, act = E && E.action, clip = act && act.getClip();
    const dur = clip ? clip.duration / (E.speed || 1) : 0;
    if (untilEnd && !dur) throw new Error('Анимация не выбрана — выберите «По кнопке Стоп»');
    const total = untilEnd ? Math.max(1, Math.round(dur * fps)) : Infinity, dt = 1 / fps;
    if (!wh) { const sz = V.r.getSize(new THREE.Vector2()); wh = [Math.max(2, Math.floor(sz.x / 2) * 2), Math.max(2, Math.floor(sz.y / 2) * 2)]; }   // odd sizes (e.g. 2200×1211) break 4:2:0 video in editors
    const sid = (await post(`/api/rec/start?fps=${fps}&alpha=${transparent ? 1 : 0}&name=${encodeURIComponent(nameFn())}`)).id;
    const view = setRes(V, wh); if (fit) frameCharacter(V, fps, total === Infinity ? Math.round(fps * 4) : total);
    if (act) { act.reset(); act.paused = false; E.mixer.update(0); }
    const s = await prep(V, transparent); let n = 0, ok = false;
    try {
      const pl = pipeline(4, b => post('/api/rec/frame?id=' + sid, b));
      for (let i = 0; i < total && !stopReq; i++) {
        if (E) E.update(dt);
        V.ctl.update(); V.r.render(V.scene, V.cam);
        await pl.push(blobOf(V.r.domElement)); n++;
        st.textContent = `Кадров: ${i + 1}${untilEnd ? ' / ' + total : ''} (кодирование идёт параллельно)`;
        if (i % 4 === 0) await tick();
      }
      await pl.drain();
      if (!n) throw new Error('Нет кадров');
      st.textContent = 'Завершаю кодирование…'; ok = true;
    } finally { restore(V, s); resetRes(V, view); if (!ok) { try { await post('/api/rec/cancel?id=' + sid); } catch (e) { /* ignore */ } } }
    const r = await post('/api/rec/finish?id=' + sid);
    const a = document.createElement('a'); a.href = r.file; a.download = r.name; document.body.appendChild(a); a.click(); a.remove();
    return `Сохранён ${r.name}: ${r.n} кадров, ${(r.size / 1048576).toFixed(1)} МБ, WebM VP9${transparent ? ' с прозрачностью' : ''}, ${fps} к/с (постоянная частота, с длительностью и индексом)`;
  }

  go.onclick = async () => {
    const V = getV(); if (!V) return;
    if (busy) { stopReq = true; go.disabled = true; return; }
    busy = true; stopReq = false; go.textContent = 'Стоп'; st.textContent = 'Подготовка…';
    const fmt = $q('.rf').value, fps = +$q('.rfps').value, end = $q('.rm').value === 'end', tr = $q('.rt').checked, wh = RES[$q('.rres').value] || null, fit = $q('.rfit').checked;
    try { st.textContent = await (fmt === 'png' ? recordPng : fmt === 'mp4' ? recordMp4 : fmt === 'webma' ? recordWebmAlpha : recordWebm)(V, fps, end, tr, wh, fit); }
    catch (e) { st.textContent = 'Ошибка: ' + (e.message || e); }
    busy = false; go.disabled = false; go.textContent = 'Начать запись';
  };
  return box;
}
