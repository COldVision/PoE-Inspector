// Scene and light settings overlay for every 3D preview (Items, Monsters, Models, Files, Skills, Editor).
import * as THREE from 'three';
import { setContrast } from '/static/contrast.js';

const LS = (k, d) => { try { const v = localStorage.getItem('poe_inspector.sp.' + k); return v === null ? d : +v; } catch (e) { return d; } };
const LSset = (k, v) => { try { localStorage.setItem('poe_inspector.sp.' + k, String(v)); } catch (e) { /* ignore */ } };

const getCt = () => { try { return +localStorage.getItem('poe_inspector.contrast') || 120; } catch (e) { return 120; } };

export function initScenePanel(getV, host) {
  const box = document.createElement('div'); box.className = 'spbox';
  box.innerHTML = `<div class="sprow"><select class="ctl stagesel" aria-label="Сцена"></select><button class="ctl sp" aria-label="Сцена и свет" title="Сцена и свет" aria-expanded="false"><svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button></div>
  <div class="sppanel" hidden>
    <b class="sph">Сцена и свет</b>
    <label>Угол света<input class="s-az" type="range" min="0" max="360" step="1" aria-label="Угол света"></label>
    <label>Высота света<input class="s-el" type="range" min="5" max="88" step="1" aria-label="Высота света"></label>
    <label>Яркость света<input class="s-in" type="range" min="20" max="250" step="5" aria-label="Яркость света, %"><span class="v v-in"></span></label>
    <label>Контраст<input class="s-ct" type="range" min="80" max="160" step="1" aria-label="Контраст, %"><span class="v v-ct"></span></label>
    <label class="only-ed">Блеск<input class="s-sh" type="range" min="0" max="1" step=".05" aria-label="Блеск"></label>
    <label class="chk only-ed"><input type="checkbox" class="s-sd"> Тени от модели</label>
    <label class="chk only-ed"><input type="checkbox" class="s-mk"> Показывать источник света</label>
    <button class="s-rs">Сбросить</button>
  </div>`;
  host.appendChild(box);
  const q = s => box.querySelector(s), btn = q('.sp'), panel = q('.sppanel'), stageSel = q('.stagesel');
  // the scene choice lives here: the editor's / monster's own stage <select> when the tab has one, otherwise the environment <select>; the originals stay in the DOM (hidden) and keep doing the work
  const source = () => document.querySelector('#edstage') || document.querySelector('#mscene') || host.querySelector('select[aria-label="Окружение"]');
  let bound = null;
  const syncStage = () => {
    const src = source(); if (!src) return;
    if (src !== bound) {
      bound = src; stageSel.innerHTML = [...src.options].map(o => `<option value="${o.value}">${o.textContent.replace(/\s*\(.*\)$/, '')}</option>`).join('');
      const wrap = src.closest('.slot, .mscene'); if (wrap) wrap.style.display = 'none'; else src.style.display = 'none';
    }
    if (stageSel.value !== src.value && document.activeElement !== stageSel) stageSel.value = src.value;
  };
  stageSel.onchange = () => { const src = source(); if (!src) return; src.value = stageSel.value; src.dispatchEvent(new Event('change', { bubbles: true })); };
  setInterval(syncStage, 400); syncStage();
  const key = V => V.lights.find(l => l.isDirectionalLight);
  const getL = V => { const kd = key(V); if (!kd) return null; const t = kd.target ? kd.target.position : new THREE.Vector3(), v = kd.position.clone().sub(t), d = v.length() || 1; const az = ((Math.atan2(v.x, v.z) * 180 / Math.PI) + 360) % 360, el = Math.asin(THREE.MathUtils.clamp(v.y / d, -1, 1)) * 180 / Math.PI; if (kd.userData.az0 === undefined) { kd.userData.az0 = az; kd.userData.el0 = el; } return { kd, t, d, az, el }; };
  const setL = (V, az, el) => {
    const l = getL(V); if (!l) return; const a = az * Math.PI / 180, e = el * Math.PI / 180;
    l.kd.position.set(l.t.x + l.d * Math.sin(a) * Math.cos(e), l.t.y + l.d * Math.sin(e), l.t.z + l.d * Math.cos(a) * Math.cos(e));
    if (V.editor && V.editor.updateMarker) V.editor.updateMarker();
  };
  // light brightness: every light keeps its authored intensity (b0); the slider is a multiplier on top of it
  const applyIntensity = V => {
    const k = LS('lint', 100) / 100;
    for (const l of V.lights) { if (l.userData.b0 === undefined) l.userData.b0 = l.intensity; if (!(V.flick || []).some(p => p[0] === l)) l.intensity = l.userData.b0 * k; }
    for (const p of V.flick || []) { if (p.b0 === undefined) p.b0 = p[1]; p[1] = p.b0 * k; }
  };
  const applyContrastNow = V => { setContrast(V && V.env === 'studio' ? getCt() / 100 : 1); };
  const sync = () => {
    const V = getV(); if (!V) return; const l = getL(V), ed = V.editor;
    if (l) { q('.s-az').value = Math.round(l.az); q('.s-el').value = Math.round(THREE.MathUtils.clamp(l.el, 5, 88)); }
    q('.s-in').value = LS('lint', 100); q('.v-in').textContent = LS('lint', 100) + '%';
    q('.s-ct').value = getCt(); q('.v-ct').textContent = getCt() + '%';
    box.querySelectorAll('.only-ed').forEach(e => { e.style.display = ed ? '' : 'none'; });
    if (ed) { q('.s-sh').value = ed.shine ?? .4; const kd = key(V); q('.s-sd').checked = !!(kd && kd.castShadow); q('.s-mk').checked = !!ed.lightShown; }
  };
  btn.onclick = () => { panel.hidden = !panel.hidden; btn.setAttribute('aria-expanded', String(!panel.hidden)); if (!panel.hidden) sync(); };
  q('.s-az').oninput = () => { const V = getV(), l = V && getL(V); if (l) setL(V, +q('.s-az').value, l.el); };
  q('.s-el').oninput = () => { const V = getV(), l = V && getL(V); if (l) setL(V, l.az, +q('.s-el').value); };
  q('.s-in').oninput = e => { LSset('lint', +e.target.value); q('.v-in').textContent = e.target.value + '%'; const V = getV(); if (V) applyIntensity(V); };
  q('.s-ct').oninput = e => { try { localStorage.setItem('poe_inspector.contrast', e.target.value); } catch (err) { /* ignore */ } q('.v-ct').textContent = e.target.value + '%'; applyContrastNow(getV()); };
  q('.s-sh').oninput = e => { const V = getV(); if (V && V.editor) V.editor.setShine(+e.target.value); };
  q('.s-sd').onchange = e => { const V = getV(); if (V && V.editor) V.editor.setShadows(e.target.checked); };
  q('.s-mk').onchange = e => { const V = getV(); if (V && V.editor) V.editor.showMarker(e.target.checked); };
  q('.s-rs').onclick = () => { LSset('lint', 100); try { localStorage.setItem('poe_inspector.contrast', '120'); } catch (e) { /* ignore */ } const V = getV(); if (V) { applyIntensity(V); applyContrastNow(V); const l = getL(V); if (l && l.kd.userData.az0 !== undefined) setL(V, l.kd.userData.az0, l.kd.userData.el0); } sync(); };
  setInterval(() => { if (!panel.hidden && !panel.contains(document.activeElement)) sync(); }, 800);   // follows tab / stage changes while open
  return { apply: V => { applyIntensity(V); applyContrastNow(V); if (!panel.hidden) sync(); }, sync };
}
