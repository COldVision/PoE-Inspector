// Editor tab UI (list panel, slot pickers, animation list) on top of editor.js
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Editor, SLOT_ORDER, SLOT_LABEL } from '/static/editor.js';
import { setContrast } from '/static/contrast.js';
const studioContrast = () => { let v = 120; try { v = +localStorage.getItem('poe_inspector.contrast') || 120; } catch (e) { /* default */ } return v; };

let ed;
export function getEd(ctx) {
  if (!ed) window._E = ed = new Editor({ api: ctx.api, esc: ctx.esc, $: ctx.$, getViewer: () => ctx.viewer(), ensureViewer: () => ctx.ensureViewer() });
  return ed;
}

export function studioStage(ctx) {
  const V = ctx.ensureViewer(); ctx.leaveScene(); setContrast(studioContrast() / 100);
  if (V.cur) { V.scene.remove(V.cur); V.cur = null; }
  if (V.gridFloor) V.gridFloor.visible = false;
  V.scene.fog = null; V.grid.visible = true; V.r.shadowMap.enabled = true; V.r.shadowMap.type = THREE.PCFSoftShadowMap;
  ctx.applyEnv('studio');
  const key = V.lights.find(l => l.isDirectionalLight);
  if (key) {
    key.position.set(3, 5, 4); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
    const c = key.shadow.camera; c.left = c.bottom = -2.5; c.right = c.top = 2.5; c.near = .5; c.far = 20; key.shadow.bias = -.0004; key.shadow.normalBias = .02;
  }
  if (!V.catcher) {
    const g = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: .45 }));
    g.rotation.x = -Math.PI / 2; g.receiveShadow = true; V.catcher = g; V.scene.add(g);
  }
  if (V.floor) V.floor.visible = false; V.r.toneMapping = THREE.NoToneMapping; getEd(ctx).envScale = 1;
  V.catcher.visible = true; V.editor = getEd(ctx); V.cam.fov = 35; V.cam.updateProjectionMatrix();
}

function woodTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 1024; const x = c.getContext('2d');
  x.fillStyle = '#2a1d14'; x.fillRect(0, 0, 1024, 1024);
  for (let i = 0; i < 16; i++) {
    const w = 64, y = i * w, b = 28 + Math.random() * 22;
    x.fillStyle = `rgb(${b + 10},${b + 4},${b})`; x.fillRect(0, y, 1024, w - 2);
    for (let k = 0; k < 40; k++) { x.strokeStyle = `rgba(0,0,0,${0.06 + Math.random() * 0.1})`; x.lineWidth = 1 + Math.random() * 2; x.beginPath(); const yy = y + Math.random() * w; x.moveTo(0, yy); x.bezierCurveTo(300, yy + Math.random() * 6 - 3, 700, yy + Math.random() * 6 - 3, 1024, yy); x.stroke(); }
    x.fillStyle = 'rgba(0,0,0,.5)'; const jx = Math.random() * 1024; x.fillRect(jx, y, 2, w);
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(22, 22); t.anisotropy = 8; t.colorSpace = THREE.SRGBColorSpace; return t;
}

// In-game look: dim warm lighting, no bright IBL, tone mapping, dark planked floor, isometric-style camera.
export function gameStage(ctx) {
  setContrast(1);
  const V = ctx.ensureViewer(); ctx.leaveScene();
  if (V.cur) { V.scene.remove(V.cur); V.cur = null; }
  V.lights.forEach(l => { V.scene.remove(l); if (l.target) V.scene.remove(l.target); }); V.lights = []; V.flick = []; V.flames = null;
  const add = l => { V.scene.add(l); V.lights.push(l); return l; };
  add(new THREE.HemisphereLight(0x8a8478, 0x1a1612, 1.4));
  const key = add(new THREE.DirectionalLight(0xfff0de, 4.0)); key.position.set(-3, 6.5, -3);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); const c = key.shadow.camera; c.left = c.bottom = -3; c.right = c.top = 3; c.near = .5; c.far = 20; key.shadow.bias = -.0004; key.shadow.normalBias = .02;
  const fill = add(new THREE.PointLight(0xffb070, 10, 0, 2)); fill.position.set(2.2, 1.2, -2.2);
  const rim = add(new THREE.DirectionalLight(0x7088b8, 1.0)); rim.position.set(3, 3, 4);
  V.scene.environment = null; V.scene.fog = null; V.scene.background = new THREE.Color(0x0b0907); V.cubeTex = null; V.bgimg = null;
  if (V.gridFloor) V.gridFloor.visible = false;
  V.grid.visible = false; if (V.catcher) V.catcher.visible = false;
  if (!V.floor) { const g = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({ map: woodTexture(), roughness: .85, metalness: 0 })); g.rotation.x = -Math.PI / 2; g.receiveShadow = true; V.floor = g; V.scene.add(g); }
  V.floor.visible = true;
  V.r.shadowMap.enabled = true; V.r.shadowMap.type = THREE.PCFSoftShadowMap; V.r.toneMapping = THREE.ACESFilmicToneMapping; V.r.toneMappingExposure = 1.25;
  $v(V).style.background = '#0b0907'; V.editor = getEd(ctx); V.cam.fov = 22; V.cam.updateProjectionMatrix();
  V.cam.position.set(0.8, 5.0, -4.4); V.ctl.target.set(0, 0.85, 0); V.ctl.update();
  getEd(ctx).envScale = 0.12;
}
const $v = V => document.querySelector('#view');


function gridTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 512; const x = c.getContext('2d');
  x.fillStyle = '#5a5246'; x.fillRect(0, 0, 512, 512);
  x.strokeStyle = 'rgba(40,28,18,.35)'; x.lineWidth = 3; x.strokeRect(1.5, 1.5, 509, 509);
  x.strokeStyle = 'rgba(40,28,18,.14)'; x.lineWidth = 1.5; for (let i = 1; i < 4; i++) { x.beginPath(); x.moveTo(i * 128, 0); x.lineTo(i * 128, 512); x.moveTo(0, i * 128); x.lineTo(512, i * 128); x.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(60, 60); t.anisotropy = 16; t.colorSpace = THREE.SRGBColorSpace; return t;
}

// Empty scene: only the character on a grid floor; distant high isometric camera and warm low sun with a long shadow.
export function gridStage(ctx) {
  setContrast(1);
  const V = ctx.ensureViewer(); ctx.leaveScene();
  if (V.cur) { V.scene.remove(V.cur); V.cur = null; }
  V.lights.forEach(l => { V.scene.remove(l); if (l.target) V.scene.remove(l.target); }); V.lights = []; V.flick = []; V.flames = null;
  const add = l => { V.scene.add(l); V.lights.push(l); return l; };
  add(new THREE.HemisphereLight(0xcbbfb0, 0x5a4b3c, 1.5));
  const key = add(new THREE.DirectionalLight(0xffe2bc, 4.2)); key.position.set(-3.5, 9, 2.5);
  key.castShadow = true; key.shadow.mapSize.set(4096, 4096); const c = key.shadow.camera; c.left = c.bottom = -9; c.right = c.top = 9; c.near = .5; c.far = 40; key.shadow.bias = -.0003; key.shadow.normalBias = .02;
  V.scene.add(key.target); key.target.position.set(0, 0, 0);
  const rim = add(new THREE.DirectionalLight(0xe8dccc, 2.0)); rim.position.set(1.5, 6, -9);
  V.scene.environment = null; V.scene.fog = null; V.scene.background = new THREE.Color(0x1a140e); V.cubeTex = null; V.bgimg = null;
  V.grid.visible = false; if (V.catcher) V.catcher.visible = false;
  if (!V.gridFloor) {
    const tl = new THREE.TextureLoader(), prep = (t, srgb) => { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(16, 16); t.anisotropy = 16; if (srgb) t.colorSpace = THREE.SRGBColorSpace; return t; };
    const mat = new THREE.MeshStandardMaterial({ map: prep(tl.load('/api/ground'), true), normalMap: prep(tl.load('/api/ground?k=normal'), false), normalScale: new THREE.Vector2(1.2, 1.2), roughness: .95, metalness: 0 });
    const g = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), mat); g.rotation.x = -Math.PI / 2; g.receiveShadow = true; V.gridFloor = g; }
  if (!V.gridFloor.parent) V.scene.add(V.gridFloor); V.gridFloor.visible = true; if (V.floor) V.floor.visible = false;
  V.r.shadowMap.enabled = true; V.r.shadowMap.type = THREE.PCFSoftShadowMap; V.r.toneMapping = THREE.ACESFilmicToneMapping; V.r.toneMappingExposure = 1.05;
  V.editor = getEd(ctx); V.cam.fov = 20; V.cam.updateProjectionMatrix();
  V.cam.position.set(0, 30, -21); V.ctl.target.set(0, 0.8, 0); V.ctl.update();
  getEd(ctx).envScale = 0.15;
}
export const exportHtml = () => `<div class="slot"><b>Анимации</b><select class="exmode" aria-label="Какие анимации экспортировать" style="flex:1"><option value="main">Основные (бег, атаки, уклон…)</option><option value="cur">Только выбранная</option><option value="all">Все (файл может быть очень большим)</option><option value="none">Без анимаций</option></select></div><div class="slot"><button class="exbtn" style="flex:1">Экспорт в Blender (.glb)</button></div><div class="exst" style="color:var(--dim);font-size:var(--fs-xs)" role="status"></div>`;
export function bindExport(ctx, root, E, nameFn, rowsFn) {
  const btn = root.querySelector('.exbtn'), st = root.querySelector('.exst'), mode = root.querySelector('.exmode');
  if (!btn) return;
  btn.onclick = async () => {
    btn.disabled = true; st.textContent = 'Подготовка…';
    try {
      const m = mode.value; let rows = m === 'none' ? null : rowsFn ? await rowsFn() : null;
      if (rows && m === 'main') rows = rows.filter(r => /^(idle|run|walk|sprint|dodge|attack|death|hit|stun|cast|spell|channel|block|roll)/.test(r.clip) && !/_(add|additive)/.test(r.clip)).slice(0, 150);
      if (rows && m === 'cur') rows = E.curClip ? [{ ast: E.curClip[0], clip: E.curClip[1] }] : [];
      const buf = await E.exportGLB({ clips: m !== 'none', rows, onProgress: (a, b) => { st.textContent = `Загрузка анимаций ${a}/${b}`; } });
      const url = URL.createObjectURL(new Blob([buf], { type: 'model/gltf-binary' })), a = document.createElement('a');
      a.href = url; a.download = (nameFn() || 'model').replace(/[^\w.-]+/g, '_') + '.glb'; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      st.textContent = `Готово: ${(buf.byteLength / 1048576).toFixed(1)} МБ. В Blender: File → Import → glTF 2.0`;
    } catch (e) { st.textContent = 'Ошибка экспорта: ' + (e.message || e); }
    btn.disabled = false;
  };
}
export function clearGrid(ctx) { const V = ctx.viewer(); if (V && V.gridFloor) V.gridFloor.visible = false; }

export const lightControlsHtml = () => `<div class="slot"><b>Угол</b><input id="ltaz" aria-label="Положение света: угол" type="range" min="0" max="360" step="1" value="45" style="flex:1"></div>
  <div class="slot"><b>Высота</b><input id="ltel" aria-label="Положение света: высота" type="range" min="5" max="88" step="1" value="45" style="flex:1"></div>
  <label class="slot kv"><input type="checkbox" id="ltshow" checked style="flex:none"> Показывать источник света (можно перетаскивать)</label>`;

let refreshLightFn = () => {};
export const refreshLight = () => refreshLightFn();

// sliders <-> light <-> draggable marker in the 3D view
export function bindLightControls(ctx) {
  const { $ } = ctx, E = getEd(ctx), V = ctx.ensureViewer();
  const sync = () => {
    const l = E.getLight(); if (!l || !$('#ltaz')) return;
    $('#ltaz').value = Math.round(l.az); $('#ltel').value = Math.round(THREE.MathUtils.clamp(l.el, 5, 88));
  };
  refreshLightFn = () => { E.showMarker($('#ltshow') ? $('#ltshow').checked : true); sync(); E.updateMarker(); };
  const apply = () => E.setLight({ az: +$('#ltaz').value, el: +$('#ltel').value });
  ['#ltaz', '#ltel'].forEach(id => { $(id).oninput = apply; });
  $('#ltshow').onchange = e => E.showMarker(e.target.checked);
  if (!V._lightDrag) {
    V._lightDrag = true;
    const dom = V.r.domElement, ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(), hit = new THREE.Vector3();
    let drag = false;
    const toNdc = ev => { const r = dom.getBoundingClientRect(); ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1); ray.setFromCamera(ndc, V.cam); };
    dom.addEventListener('pointerdown', ev => {
      if (!E.lightShown || !E.marker || ev.button !== 0) return;
      toNdc(ev);
      if (ray.intersectObject(E.marker.userData.core, false).length || ray.intersectObjects(E.marker.children, false).length) {
        drag = true; V.ctl.enabled = false; dom.setPointerCapture(ev.pointerId);
        plane.setFromNormalAndCoplanarPoint(V.cam.getWorldDirection(new THREE.Vector3()).negate(), E.marker.position);
        ev.stopImmediatePropagation(); ev.preventDefault();
      }
    }, true);
    dom.addEventListener('pointermove', ev => {
      if (!drag) { if (E.lightShown && E.marker) { toNdc(ev); dom.style.cursor = ray.intersectObjects(E.marker.children, false).length ? 'grab' : ''; } return; }
      toNdc(ev); if (!ray.ray.intersectPlane(plane, hit)) return;
      const kd = E.keyLight(); if (!kd) return;
      const v = hit.clone().sub(E.markerCenter || new THREE.Vector3()), len = v.length() || 1;
      const el = THREE.MathUtils.clamp(Math.asin(THREE.MathUtils.clamp(v.y / len, -1, 1)) * 180 / Math.PI, 5, 88);
      E.setLight({ az: ((Math.atan2(v.x, v.z) * 180 / Math.PI) + 360) % 360, el }); sync();
    });
    const end = ev => { if (drag) { drag = false; V.ctl.enabled = true; try { dom.releasePointerCapture(ev.pointerId); } catch (e) { /* ignore */ } } };
    dom.addEventListener('pointerup', end); dom.addEventListener('pointercancel', end);
  }
  refreshLightFn();
}

export function leaveEditor(ctx) {
  const V = ctx.viewer(); if (!V) return;
  clearGrid(ctx); if (ed) ed.showMarker(false); if (ed && ed.root) ed.clear();
  if (V.catcher) V.catcher.visible = false;
  if (V.floor) V.floor.visible = false;
  V.r.toneMapping = THREE.NoToneMapping; V.r.shadowMap.enabled = false; V.editor = null;
}

function pickItem(ctx, slot) {
  const { api, esc } = ctx;
  return new Promise(resolve => {
    const d = document.createElement('div'); d.id = 'picker';
    d.innerHTML = `<div class="box"><div style="display:flex;gap:8px"><input id="pq" placeholder="Поиск: ${esc(SLOT_LABEL[slot])}" style="flex:1"><button id="pc" aria-label="Закрыть">✕</button></div><label class="kv" style="margin-top:6px;display:flex;align-items:center;gap:6px"><input type="checkbox" id="pu" autocomplete="off" style="height:auto"> Только уникальные</label>${slot === 'weapon' || slot === 'offhand' ? `<label class="kv" style="margin-top:4px;display:flex;align-items:center;gap:6px"><input type="checkbox" id="pn" autocomplete="off" style="height:auto"> Только NPC (оружие и щиты монстров)</label>` : ''}<div class="lst" id="pl"></div></div>`;
    document.body.appendChild(d);
    const close = v => { d.remove(); resolve(v); };
    d.onclick = e => { if (e.target === d) close(undefined); };
    d.querySelector('#pc').onclick = () => close(undefined);
    let t;
    const run = async () => {
      const rows = await api(`/api/slotitems?slot=${slot}&q=${encodeURIComponent(d.querySelector('#pq').value)}${d.querySelector('#pu').checked ? '&unique=1' : ''}${d.querySelector('#pn') && d.querySelector('#pn').checked ? '&npc=1' : ''}`);
      d.querySelector('#pl').innerHTML = rows.map((r, i) => `<div class="row" data-i="${i}"><div style="display:flex;align-items:center;gap:8px">${r.icon ? `<img loading="lazy" width="32" height="32" src="/api/icon?size=64&path=${encodeURIComponent(r.icon)}" style="object-fit:contain" onerror="this.style.visibility='hidden'">` : ''}${esc(r.name)}</div><span>${r.unique ? 'Уникальный · ' : ''}${esc(r.class)}</span></div>`).join('') || '<div class="msg">Ничего не найдено</div>';
      d.querySelector('#pl').onclick = e => { const row = e.target.closest('.row'); if (row) close(rows[row.dataset.i]); };
    };
    d.querySelector('#pq').oninput = () => { clearTimeout(t); t = setTimeout(run, 200); };
    d.querySelector('#pu').onchange = () => { if (d.querySelector('#pn') && d.querySelector('#pu').checked) d.querySelector('#pn').checked = false; run(); };
    if (d.querySelector('#pn')) d.querySelector('#pn').onchange = () => { if (d.querySelector('#pn').checked) d.querySelector('#pu').checked = false; run(); };
    run(); d.querySelector('#pq').focus();
  });
}

function slotRow(ctx, slot) {
  const it = getEd(ctx).equip[slot];
  return `<div class="slot" data-slot="${slot}"><b>${SLOT_LABEL[slot]}</b><button class="pick">${it ? ctx.esc(it.item.name) : '— выбрать —'}</button><button class="x" title="Снять" aria-label="Снять">✕</button></div>`;
}

export async function openEditor(ctx) {
  const { api, esc, $ } = ctx;
  studioStage(ctx);
  const E = getEd(ctx), L = $('#list'); L.onclick = null; $('#info').innerHTML = '';
  L.innerHTML = `<div class="ed"><h4>Персонаж</h4><div style="display:flex;gap:6px"><input id="edq" placeholder="Поиск" aria-label="Поиск персонажа" style="flex:1"><select id="edk" aria-label="Тип персонажа"><option value="">Все</option><option value="player">Игроки</option><option value="npc">NPC</option></select></div><div class="edlist" id="edactors"></div>
  <h4>Экипировка</h4><div id="edslots">${SLOT_ORDER.map(s => slotRow(ctx, s)).join('')}</div>
  <div class="legacy-scene" style="display:none"><h4>Сцена и свет</h4><div class="slot"><b>Сцена</b><select id="edstage" aria-label="Сцена" style="flex:1"><option value="studio">Студия</option><option value="game">Игровой вид (тусклый свет, пол)</option><option value="grid">Пустая сцена (сетка, вид сверху)</option></select></div>
  <div class="slot"><b>Контраст</b><input id="edcon" aria-label="Контраст в студии, % (100 = без изменений)" type="range" min="80" max="160" step="1" value="${studioContrast()}" style="flex:1"><span id="edconv" style="width:3.2em;text-align:right;color:var(--dim)">${studioContrast()}%</span></div>
  <div class="slot"><b>Блеск</b><input id="edshine" aria-label="Блеск" type="range" min="0" max="1" step=".05" value=".4" style="flex:1"></div>
  ${lightControlsHtml()}
  <label class="slot" style="color:var(--dim)"><input type="checkbox" id="edshadow" checked style="flex:none"> Тени от персонажа</label></div>
  <h4>Экспорт</h4><div id="edexp">${exportHtml()}</div>
  <h4>Анимации</h4><div id="edawl" style="color:var(--dim);margin-bottom:4px"></div><div style="display:flex;gap:6px;align-items:center"><input id="edaq" placeholder="Фильтр" style="flex:1"><label style="color:var(--dim)">скорость <input id="eds" type="range" min=".25" max="1.5" step=".05" value="1" style="width:80px;padding:0"></label></div><div class="edlist edanim" id="edanims" style="max-height:260px"></div></div>`;
  bindExport(ctx, $('#edexp'), E, () => (E.actor && (E.actor.name || E.actor.id)) || 'character', async () => E.actor && E.actor.kind === 'player' ? api(`/api/anims?limit=5000&tokens=${encodeURIComponent((E.weaponTokens || ['unarmed']).join(','))}`) : null);
  const refreshSlots = () => { const b = $('#edslots'); if (b) b.innerHTML = SLOT_ORDER.map(s => slotRow(ctx, s)).join(''); };
  let rowsAnim = [];
  const refreshAnims = async () => {
    const box = $('#edanims'); if (!box || !E.actor) return;
    const q = ($('#edaq') && $('#edaq').value) || '';
    if (E.actor.kind === 'player') {
      const tk = (E.weaponTokens || ['unarmed']).join(',');
      rowsAnim = await api(`/api/anims?tokens=${encodeURIComponent(tk)}&q=${encodeURIComponent(q)}`);
      if ($('#edawl')) $('#edawl').textContent = 'Анимации для оружия: ' + tk;
    } else {
      rowsAnim = (E.rig ? E.rig.clips : []).filter(c => c.name.toLowerCase().includes(q.toLowerCase())).map(c => ({ ast: E.actor.skeleton, move: '', clip: c.name }));
      if ($('#edawl')) $('#edawl').textContent = 'Анимации этого персонажа';
    }
    if (!$('#edanims')) return;
    box.innerHTML = rowsAnim.map((r, i) => `<div class="row" data-i="${i}"><div>${esc(r.clip)}</div><span>${esc(r.move)}</span></div>`).join('') || '<div class="msg">Нет анимаций</div>';
    box.onclick = async e => {
      const row = e.target.closest('.row'); if (!row) return;
      document.querySelectorAll('#edanims .row.on').forEach(x => x.classList.remove('on')); row.classList.add('on');
      const r = rowsAnim[row.dataset.i];
      try { await E.play(r.ast, r.clip); } catch (err) { $('#info').textContent = 'Анимация: ' + err.message; }
    };
  };
  let t;
  const lst = async () => {
    if (!$('#edq')) return;
    const rows = await api(`/api/actors?q=${encodeURIComponent($('#edq').value)}&kind=${$('#edk').value}`);
    if (!$('#edactors')) return;
    $('#edactors').innerHTML = rows.map((r, i) => `<div class="row" data-i="${i}"><div>${esc(r.name)}</div><span>${r.kind === 'player' ? 'игрок' : 'NPC'}</span></div>`).join('');
    $('#edactors').onclick = async e => {
      const row = e.target.closest('.row'); if (!row) return;
      document.querySelectorAll('#edactors .row.on').forEach(x => x.classList.remove('on')); row.classList.add('on');
      $('#info').textContent = 'Загрузка персонажа…';
      try { await E.loadActor(rows[row.dataset.i]); $('#info').textContent = rows[row.dataset.i].name; refreshSlots(); refreshAnims(); }
      catch (err) { $('#info').textContent = 'Ошибка: ' + err.message; }
    };
  };
  $('#edq').oninput = () => { clearTimeout(t); t = setTimeout(lst, 200); };
  $('#edk').onchange = lst; lst();
  $('#edaq').oninput = () => { clearTimeout(t); t = setTimeout(refreshAnims, 200); };
  $('#eds').oninput = e => E.setSpeed(+e.target.value);
  $('#edshine').oninput = e => E.setShine(+e.target.value);
  $('#edcon').oninput = e => { const v = +e.target.value; $('#edconv').textContent = v + '%'; try { localStorage.setItem('poe_inspector.contrast', String(v)); } catch (err) { /* ignore */ } if ($('#edstage').value === 'studio') setContrast(v / 100); };
  bindLightControls(ctx);
  $('#edshadow').onchange = e => E.setShadows(e.target.checked);
  let stage = 'studio';
  $('#edstage').onchange = async e => {
    const which = e.target.value; $('#info').textContent = 'Загрузка сцены…'; E.ctx.keepCamera = which !== 'studio'; clearGrid(ctx);
    try {
      if (which === 'grid') { gridStage(ctx); await E.reload({}); }
      else if (which === 'game') { gameStage(ctx); await E.reload({}); }
      else { studioStage(ctx); await E.reload({}); }
      refreshLight(); stage = which; $('#info').textContent = which === 'grid' ? 'Сцена: сетка' : which === 'game' ? 'Сцена: игровой вид' : 'Сцена: студия';
    } catch (err) { $('#info').textContent = 'Ошибка сцены: ' + err.message; }
  };
  $('#edslots').onclick = async e => {
    const row = e.target.closest('.slot'); if (!row) return; const slot = row.dataset.slot;
    if (!E.actor || E.actor.kind !== 'player') { $('#info').textContent = 'Экипировка доступна для игровых персонажей'; return; }
    if (e.target.classList.contains('x')) { await E.setSlot(slot, null); refreshSlots(); if (slot === 'weapon') refreshAnims(); return; }
    const it = await pickItem(ctx, slot); if (!it) return;
    $('#info').textContent = 'Загрузка ' + it.name + '…';
    try { await E.setSlot(slot, it); $('#info').textContent = it.name; refreshSlots(); if (slot === 'weapon') refreshAnims(); }
    catch (err) { $('#info').textContent = 'Ошибка: ' + err.message; }
  };
  if (E.actor) { E.ctx.keepCamera = false; E.reload({}).then(() => { refreshSlots(); refreshAnims(); }).catch(() => {}); }
}
