// Character editor: skeleton + skinned parts + equipment slots + animation playback.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { applyContrast } from '/static/contrast.js';

const S = 0.01;
const GAME = new THREE.Matrix4().set(S, 0, 0, 0, 0, 0, -S, 0, 0, S, 0, 0, 0, 0, 0, 1); // game (x,y,z) -> three (x,-z,y)*0.01
const SOCKET = { R: 'aux_R_Weapon_attachment_jntBnd', L: 'aux_L_Weapon_attachment_jntBnd' };
const SLOT_ORDER = ['helmet', 'body', 'gloves', 'boots', 'weapon', 'offhand'];
const SLOT_LABEL = { helmet: 'Шлем', body: 'Броня', gloves: 'Перчатки', boots: 'Обувь', weapon: 'Оружие', offhand: 'Вторая рука' };

// GLTFExporter writes one skin per skinned mesh; all of ours share a skeleton, so keep a single skin (one armature in Blender)
function mergeSkins(buf) {
  const dv = new DataView(buf), jl = dv.getUint32(12, true), j = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 20, jl)));
  if (!j.skins || j.skins.length < 2) return buf;
  const keep = [], map = new Map();
  j.skins.forEach((sk, i) => { const k = (sk.joints || []).join(','); if (!map.has(k)) { map.set(k, keep.length); keep.push(sk); } map.set('i' + i, map.get(k)); });
  (j.nodes || []).forEach(n => { if (n.skin !== undefined) n.skin = map.get('i' + n.skin); });
  j.skins = keep;
  let js = new TextEncoder().encode(JSON.stringify(j)); const pad = (4 - js.length % 4) % 4;
  if (pad) { const t = new Uint8Array(js.length + pad).fill(32); t.set(js); js = t; }
  const binOff = 20 + jl, rest = new Uint8Array(buf, binOff), out = new Uint8Array(20 + js.length + rest.length), o = new DataView(out.buffer);
  o.setUint32(0, 0x46546C67, true); o.setUint32(4, 2, true); o.setUint32(8, out.length, true); o.setUint32(12, js.length, true); o.setUint32(16, 0x4E4F534A, true);
  out.set(js, 20); out.set(rest, 20 + js.length);
  return out.buffer;
}

export class Editor {
  constructor(ctx) {
    this.ctx = ctx; // {api, esc, $, getViewer, ensureViewer}
    this.actor = null; this.rig = null; this.root = null; this.skeleton = null; this.mixer = null;
    this.base = []; this.equip = {}; this.hidden = new Set(); this.weaponTokens = ['unarmed'];
    this.loader = new GLTFLoader(); this.action = null; this.clipCache = new Map();
  }

  // ---- loading ----------------------------------------------------------------------------
  clear() {
    const V = this.ctx.getViewer();
    if (this.root) { if (this.root.parent) this.root.parent.remove(this.root); this.root = null; }
    if (this.mixer) { this.mixer.stopAllAction(); this.mixer = null; }
    (this.companions || []).forEach(c => c.mixer.stopAllAction()); this.companions = [];
    this.gen = (this.gen || 0) + 1;   // invalidates loads that are still awaiting the server (tab switched meanwhile)
    this.base = []; this.equip = {}; this.hidden = new Set(); this.action = null; this.skeleton = null; this.phys = [];
  }

  async loadActor(a, opts = {}) {
    const { api } = this.ctx; const V = this.ctx.ensureViewer();
    this.clear(); this.opts = opts; const gen = this.gen;
    if (!a.preset && a.id && a.id.startsWith('npc:') && !a.parts) { const pr = await api('/api/preset?npc=' + encodeURIComponent(a.id.slice(4))); if (gen !== this.gen) return null; a = { ...a, parts: pr.parts, companions: pr.companions }; }
    if (a.preset) { const pr = await api('/api/preset?name=' + encodeURIComponent(a.preset)); if (gen !== this.gen) return null; a = { ...a, skin: pr.skin, parts: pr.parts, arch: pr.arch }; }
    this.actor = a; this.parts = a.parts || [];
    if (V.cur && !opts.parent) { V.scene.remove(V.cur); V.cur = null; }
    const rig = await api('/api/rig?ast=' + encodeURIComponent(a.skeleton));
    if (gen !== this.gen) return null;
    this.rig = rig;
    this.root = new THREE.Group(); this.root.matrixAutoUpdate = false; this.root.matrix.copy(GAME);
    this.root.matrix.premultiply(new THREE.Matrix4().makeTranslation(opts.x || 0, opts.y || 0, opts.z || 0));
    this.root.matrixWorldNeedsUpdate = true;
    const bones = rig.bones.map(b => { const o = new THREE.Bone(); o.name = b.n; const m = new THREE.Matrix4().fromArray(b.m); m.decompose(o.position, o.quaternion, o.scale); return o; });
    rig.bones.forEach((b, i) => { if (b.p >= 0) bones[b.p].add(bones[i]); else this.root.add(bones[i]); });
    this.bones = bones; this.byName = new Map(bones.map(b => [b.name, b]));
    this.skeleton = new THREE.Skeleton(bones);
    (opts.parent || V.scene).add(this.root);
    this.root.updateWorldMatrix(true, true);
    this.skeleton.calculateInverses();
    this.mixer = new THREE.AnimationMixer(this.root);
    await this.addSkin(a.skin, 'base');
    if (gen !== this.gen) return null;
    for (const part of this.parts) { if (gen !== this.gen) return null; part.nodes = [];
      for (const f of part.fixed || []) { try { const g = await this.loader.loadAsync('/api/model?raw=1&path=' + encodeURIComponent(f.path)); g.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.material.side = 2; } }); const pb = f.bone ? this.byName.get(f.bone) : null; if (pb) { pb.add(g.scene); part.nodes.push(g.scene); } } catch (e) { /* fixed mesh missing */ } } for (const it of part.skins) { try { part.nodes.push(...await this.addSkin(it.sm, 'part:' + part.tag, { static: it.static, parent: it.bone ? this.byName.get(it.bone) : null })); } catch (e) { /* part without mesh */ } } }
    if (gen !== this.gen) return null;
    for (const c of a.companions || []) { if (gen !== this.gen) return null; try { await this.addCompanion(c, gen); } catch (err) { /* companion rig unavailable */ } }
    this.applyHide();
    this.fit();
    return rig;
  }

  // second rig that moves with the actor (cinematic Atziri's cloak): own skeleton and mixer, plays the same clip name when it has it
  async addCompanion(c, gen) {
    const rig = await this.ctx.api('/api/rig?ast=' + encodeURIComponent(c.skeleton));
    if (gen !== this.gen || !this.root) return;
    const group = new THREE.Group(); this.root.add(group);
    const bones = rig.bones.map(b => { const o = new THREE.Bone(); o.name = b.n; const m = new THREE.Matrix4().fromArray(b.m); m.decompose(o.position, o.quaternion, o.scale); return o; });
    rig.bones.forEach((b, i) => { if (b.p >= 0) bones[b.p].add(bones[i]); else group.add(bones[i]); });
    group.updateWorldMatrix(true, true);
    const skeleton = new THREE.Skeleton(bones); skeleton.calculateInverses();
    await this.addSkin(c.skin, 'att', { skeleton, bones, group });
    this.companions.push({ ast: c.skeleton, group, rig, bones, mixer: new THREE.AnimationMixer(group), clips: new Set(rig.clips.map(x => x.name)), action: null });
  }

  async addSkin(sm, tag, opts = {}) {
    const gen = this.gen;
    let tq = 2048; try { tq = +localStorage.getItem('poe_inspector.tex') || 2048; } catch (e) { /* default */ }
    const gltf = await this.loader.loadAsync('/api/skin?sm=' + encodeURIComponent(sm) + '&tex=' + tq + (opts.static ? '&static=1' : ''));
    { const V = this.ctx.getViewer(), an = V && V.r ? V.r.capabilities.getMaxAnisotropy() : 8; gltf.scene.traverse(o => { if (o.isMesh && o.material) for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap']) if (o.material[k]) o.material[k].anisotropy = an; }); }
    const sk = opts.skeleton || this.skeleton, bn = opts.bones || this.bones, rt = opts.group || this.root;
    if (gen !== this.gen || !sk || !rt) return [];
    const list = [];
    gltf.scene.traverse(o => {
      if (!o.isMesh) return;
      const mat = o.material; if (mat.map) mat.map.colorSpace = THREE.SRGBColorSpace;
      mat.side = THREE.DoubleSide; mat.envMapIntensity = 1.4; applyContrast(mat); mat.needsUpdate = true;
      let m;
      const si = o.geometry.attributes.skinIndex;
      if (si && !si.userData_fixed) { const nb = bn.length, arr = si.array; for (let i = 0; i < arr.length; i++) if (arr[i] >= nb) arr[i] = 0; si.userData_fixed = true; }
      if (si) {
        m = new THREE.SkinnedMesh(o.geometry, mat); rt.add(m); m.bind(sk, new THREE.Matrix4().copy(rt.matrixWorld));
      } else { m = new THREE.Mesh(o.geometry, mat); rt.add(m); }
      if (opts.parent) { rt.remove(m); opts.parent.add(m); }
      m.name = o.name; m.frustumCulled = false; m.castShadow = true; m.receiveShadow = true; m.userData.tag = tag;
      list.push(m);
    });
    return list;
  }

  // weapon with its own skeleton and phys_* bones (flail chain): skinned to that skeleton, the chain is simulated (the game does the same at runtime)
  async addRigged(sm, rig, parent, slot) {
    const gen = this.gen;
    let tq = 2048; try { tq = +localStorage.getItem('poe_inspector.tex') || 2048; } catch (e) { /* default */ }
    const gltf = await this.loader.loadAsync('/api/skin?sm=' + encodeURIComponent(sm) + '&tex=' + tq);
    if (gen !== this.gen || !this.root) return [];
    const bones = rig.bones.map(b => { const o = new THREE.Bone(); o.name = b.n; const m = new THREE.Matrix4().fromArray(b.m); m.decompose(o.position, o.quaternion, o.scale); return o; });
    const roots = [];
    rig.bones.forEach((b, i) => { if (b.p >= 0) bones[b.p].add(bones[i]); else { parent.add(bones[i]); roots.push(bones[i]); } });
    this.root.updateWorldMatrix(true, true);
    const sk = new THREE.Skeleton(bones); sk.calculateInverses();
    const nodes = [...roots];
    gltf.scene.traverse(o => {
      if (!o.isMesh) return;
      const mat = o.material; if (mat.map) mat.map.colorSpace = THREE.SRGBColorSpace; mat.side = THREE.DoubleSide; applyContrast(mat); mat.needsUpdate = true;
      const si = o.geometry.attributes.skinIndex;
      if (si && !si.userData_fixed) { const arr = si.array; for (let i = 0; i < arr.length; i++) if (arr[i] >= bones.length) arr[i] = 0; si.userData_fixed = true; }
      const m = si ? new THREE.SkinnedMesh(o.geometry, mat) : new THREE.Mesh(o.geometry, mat);
      parent.add(m); m.updateWorldMatrix(true, false); if (si) m.bind(sk, m.matrixWorld.clone());
      m.name = o.name; m.frustumCulled = false; m.castShadow = true; m.receiveShadow = true; m.userData.tag = slot; nodes.push(m);
    });
    // chain = phys_skinned_* bones in hierarchy order (links, then the head)
    const chain = bones.filter(b => /^phys_skinned/i.test(b.name));
    if (chain.length > 1) {
      this.root.updateWorldMatrix(true, true);
      const pos = chain.map(b => b.getWorldPosition(new THREE.Vector3()));
      const len = pos.map((p, i) => i ? p.distanceTo(pos[i - 1]) : 0);
      (this.phys = this.phys || []).push({ slot, sk, chain, pos, prev: pos.map(p => p.clone()), len, restQ: chain.map(b => b.quaternion.clone()), restDir: chain.map((b, i) => i < chain.length - 1 ? chain[i + 1].position.clone().normalize() : null) });
    }
    return nodes;
  }

  stepPhys(dt) {
    if (!this.phys || !this.phys.length || !(dt > 0)) return;
    dt = Math.min(dt, 1 / 20) * (this.chainSpeed ?? 0.5); this.root.updateMatrixWorld(true);   // chainSpeed: 1 = real time, lower = slower, heavier-looking chain
    const N = 4, h = dt / N, g = -16 * h * h, damp = 0.975, tmp = new THREE.Vector3(), q = new THREE.Quaternion(), pq = new THREE.Quaternion(), wq = new THREE.Quaternion(), dc = new THREE.Vector3(), dn = new THREE.Vector3();
    for (const c of this.phys) {
      const n = c.chain.length, P = c.pos, Q = c.prev;
      c.chain[0].getWorldPosition(P[0]); Q[0].copy(P[0]);
      for (let s = 0; s < N; s++) {
        for (let i = 1; i < n; i++) { tmp.copy(P[i]).sub(Q[i]).multiplyScalar(damp); if (tmp.length() > 0.04) tmp.setLength(0.04); Q[i].copy(P[i]); P[i].add(tmp); P[i].y += g; if (P[i].y < 0.01) P[i].y = 0.01; }
        for (let it = 0; it < 8; it++) for (let i = 1; i < n; i++) {
          tmp.copy(P[i]).sub(P[i - 1]); const d = tmp.length() || 1e-6, k = (d - c.len[i]) / d;
          if (i === 1) P[i].addScaledVector(tmp, -k); else { P[i].addScaledVector(tmp, -k * 0.5); P[i - 1].addScaledVector(tmp, k * 0.5); }
        }
      }
      for (let i = 1; i < n; i++) { tmp.copy(P[i]).sub(P[i - 1]); const d = tmp.length() || 1e-6; P[i].copy(P[i - 1]).addScaledVector(tmp, c.len[i] / d); }   // hard length pass: fast hand moves must not stretch the chain
      c.chain[0].parent.getWorldQuaternion(pq);
      for (let i = 0; i < n; i++) {
        const b = c.chain[i];
        wq.copy(pq).multiply(c.restQ[i]);                         // rest orientation under the (already moved) parent
        if (i < n - 1) { dc.copy(c.restDir[i]).applyQuaternion(wq); dn.copy(P[i + 1]).sub(P[i]).normalize(); q.setFromUnitVectors(dc, dn); wq.premultiply(q); }
        q.copy(pq).invert().multiply(wq); b.quaternion.slerp(q, 0.55); pq.multiply(b.quaternion);   // eased: no snapping between frames
      }
    }
  }

  async reload(opts) {
    const a = this.actor; if (!a) return;
    const items = {}; for (const s in this.equip) items[s] = this.equip[s].item;
    const cur = this.curClip;
    await this.loadActor(a, opts);
    for (const s in items) await this.setSlot(s, items[s]);
    if (cur) this.play(cur[0], cur[1]);
    this.applyLook();
  }

  setShine(v) { this.shine = v; this.applyLook(); }
  applyLook() {
    const v = this.shine ?? 0.4;
    this.root && this.root.traverse(o => {
      if (!o.isMesh || !o.material || o.userData.tag === undefined) return;
      const m = o.material; if (m.userData.baseRough === undefined) m.userData.baseRough = m.roughness;
      m.envMapIntensity = (0.3 + v * 2.2) * (this.envScale ?? 1); m.roughness = m.userData.baseRough * (1.7 - 1.3 * v);
    });
  }
  setShadows(on) { const V = this.ctx.getViewer(); V.lights.forEach(l => { if (l.isDirectionalLight && l.shadow && l.shadow.mapSize) l.castShadow = on; if (l.isPointLight && l.shadow) l.castShadow = on; }); }
  // ---- key light: position relative to its target, shown by a draggable marker ------------------
  keyLight() { const V = this.ctx.getViewer(); return V && V.lights.find(l => l.isDirectionalLight); }
  getLight() {
    const kd = this.keyLight(); if (!kd) return null;
    const t = kd.target ? kd.target.position : new THREE.Vector3(), v = kd.position.clone().sub(t), d = v.length() || 1;
    return { az: ((Math.atan2(v.x, v.z) * 180 / Math.PI) + 360) % 360, el: Math.asin(THREE.MathUtils.clamp(v.y / d, -1, 1)) * 180 / Math.PI, d };
  }
  setLight({ az, el, d }) {
    const kd = this.keyLight(); if (!kd) return;
    const cur = this.getLight(); az = az ?? cur.az; el = el ?? cur.el; d = d ?? cur.d;
    const a = az * Math.PI / 180, e = el * Math.PI / 180, t = kd.target ? kd.target.position : new THREE.Vector3();
    kd.position.set(t.x + d * Math.sin(a) * Math.cos(e), t.y + d * Math.sin(e), t.z + d * Math.cos(a) * Math.cos(e));
    this.updateMarker();
  }
  setLightAzimuth(deg) { this.setLight({ az: deg }); }
  ensureMarker() {
    const V = this.ctx.getViewer();
    if (!this.marker) {
      const g = new THREE.Group();
      const m = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false, transparent: true }));
      const halo = new THREE.Mesh(new THREE.SphereGeometry(1.9, 24, 16), new THREE.MeshBasicMaterial({ color: 0xfc4c70, depthTest: false, transparent: true, opacity: .35 }));
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0xfc4c70, depthTest: false, transparent: true, opacity: .55 }));
      [m, halo, line].forEach(o => { o.renderOrder = 999; }); m.userData.marker = true;
      g.add(halo, m); g.userData = { line, core: m }; this.marker = g; this.markerLine = line;
    }
    if (!this.marker.parent) V.scene.add(this.marker), V.scene.add(this.markerLine);
    return this.marker;
  }
  showMarker(on) {
    this.lightShown = on; const V = this.ctx.getViewer();
    if (!on) { if (this.marker && this.marker.parent) { V.scene.remove(this.marker); V.scene.remove(this.markerLine); } return; }
    this.ensureMarker(); this.updateMarker();
  }
  updateMarker() {
    if (!this.lightShown || !this.marker) return;
    const kd = this.keyLight(), V = this.ctx.getViewer(); if (!kd) return;
    // the sun is directional, so the marker sits on a sphere (radius R) around the character, in the light's direction
    const t = kd.target ? kd.target.position : new THREE.Vector3(), c = new THREE.Vector3(t.x, t.y + .9, t.z);
    const dir = kd.position.clone().sub(t).normalize(); this.markerCenter = c;
    const R = THREE.MathUtils.clamp(V.cam.position.distanceTo(c) * .15, 1.2, 8);
    this.marker.position.copy(c).addScaledVector(dir, R);
    const sc = Math.max(.03, V.cam.position.distanceTo(this.marker.position) * .014); this.marker.scale.setScalar(sc);
    const pos = this.markerLine.geometry.attributes.position; pos.setXYZ(0, this.marker.position.x, this.marker.position.y, this.marker.position.z); pos.setXYZ(1, c.x, c.y, c.z); pos.needsUpdate = true;
  }

  findBone(name) {
    const lc = name.toLowerCase();
    return this.byName.get(name) || this.byName.get(name + '_jntBnd') || this.bones.find(b => b.name.toLowerCase() === lc || b.name.toLowerCase() === lc + '_jntbnd') || null;
  }

  // ---- equipment --------------------------------------------------------------------------
  async setSlot(slot, item) {
    const { api } = this.ctx; const gen = this.gen;
    const prev = this.equip[slot];
    if (prev) { prev.nodes.forEach(n => n.parent && n.parent.remove(n)); delete this.equip[slot]; }
    this.phys = (this.phys || []).filter(p => p.slot !== slot);
    this.applyHide();
    if (!item) { if (slot === 'weapon') this.weaponTokens = ['unarmed']; return; }
    const e = await api(`/api/equipped?id=${encodeURIComponent(item.id)}&slot=${slot}&arch=${(this.actor && this.actor.arch) || ''}`);
    if (gen !== this.gen) return;
    const nodes = [];
    if (slot === 'weapon' || slot === 'offhand') {
      if (slot === 'weapon') this.weaponTokens = e.tokens || ['unarmed'];
      const left = slot === 'offhand' || (e.class === 'Bows');
      const bone = this.byName.get(left ? SOCKET.L : SOCKET.R);
      if (e.fixed && bone) {
        const g = await this.loader.loadAsync('/api/model?raw=1&path=' + encodeURIComponent(e.fixed));
        g.scene.traverse(o => { if (o.isMesh) { const m = o.material; if (m.map) m.map.colorSpace = THREE.SRGBColorSpace; m.side = THREE.DoubleSide; o.castShadow = true; } });
        g.scene.frustumCulled = false; bone.add(g.scene); nodes.push(g.scene);
      } else if (e.skins && e.skins.length) {
        let rg = null; if (e.skeleton && bone) { try { rg = await api('/api/rig?ast=' + encodeURIComponent(e.skeleton)); } catch (err) { rg = null; } }
        if (gen !== this.gen) return;
        if (rg && rg.bones.some(b => /^phys_/i.test(b.n))) { for (const sm of e.skins) nodes.push(...await this.addRigged(sm, rg, bone, slot)); }   // chain / flail: own skeleton, simulated
        else for (const sm of e.skins) nodes.push(...await this.addSkin(sm, slot, { static: true, parent: bone }));
      }
    } else {
      for (const sm of e.skins || []) nodes.push(...await this.addSkin(sm, slot));
      // skirts / shawls / plumes ride on their mount bone; leggings without a rig of their own are skinned to the body
      for (const a of e.attachments || []) {
        const bone = a.bone === '<root>' ? null : this.findBone(a.bone);
        for (const sm of a.skins) {
          try {
            if (!a.own) nodes.push(...await this.addSkin(sm, slot));
            else if (bone) nodes.push(...await this.addSkin(sm, slot, { static: true, parent: bone }));
          } catch (err) { /* attachment without a loadable mesh */ }
        }
      }
    }
    if (gen !== this.gen) { nodes.forEach(n => n.parent && n.parent.remove(n)); return; }
    this.equip[slot] = { item, nodes, hide: e.hide || [], att: e.hide_att || [], effects: e.effects || [] };
    this.applyHide(); this.applyLook();
  }

  applyHide() {
    const hide = new Set(), att = new Set();
    for (const sl in this.equip) { this.equip[sl].hide.forEach(h => hide.add(h)); (this.equip[sl].att || []).forEach(x => att.add(x)); }
    for (const part of this.parts || []) {
      const vis = !att.has(part.tag);
      (part.nodes || []).forEach(n => { n.visible = vis; });
      if (vis) part.hide.forEach(h => hide.add(h));
    }
    this.root && this.root.traverse(o => { if (o.userData.tag === 'base') o.visible = !hide.has(o.name); });
  }

  // ---- animation --------------------------------------------------------------------------
  async clipFor(astPath, name, tgt) {
    const rigT = (tgt && tgt.rig) || this.rig, bonesT = (tgt && tgt.bones) || this.bones;   // a companion rig (cloak) binds the clip to its own bones
    const { api } = this.ctx;
    const key = astPath + '|' + name;
    let clip = this.clipCache.get(key);
    if (!clip) {
      const c = await api(`/api/clip?ast=${encodeURIComponent(astPath)}&name=${encodeURIComponent(name)}`);
      if (c.parent) {   // additive layer (*_stationary / *_moving) over its parent pose: result = parent pose + delta (rotations: parent * delta)
        try {
          const p = await api(`/api/clip?ast=${encodeURIComponent(astPath)}&name=${encodeURIComponent(c.parent)}`), pb = new Map(p.tracks.map(t => [t.bone, t]));
          const qa = new THREE.Quaternion(), qb = new THREE.Quaternion();
          for (const t of c.tracks) {
            const pt = pb.get(t.bone); if (!pt) continue;
            if (pt.pos.length && t.pos.length) for (let i = 0; i < t.pos.length; i += 4) { t.pos[i + 1] += pt.pos[1]; t.pos[i + 2] += pt.pos[2]; t.pos[i + 3] += pt.pos[3]; }
            if (pt.rot.length && t.rot.length) { qa.set(pt.rot[1], pt.rot[2], pt.rot[3], pt.rot[4]); for (let i = 0; i < t.rot.length; i += 5) { qb.set(t.rot[i + 1], t.rot[i + 2], t.rot[i + 3], t.rot[i + 4]); qb.premultiply(qa); t.rot[i + 1] = qb.x; t.rot[i + 2] = qb.y; t.rot[i + 3] = qb.z; t.rot[i + 4] = qb.w; } }
          }
        } catch (e) { /* parent missing: play the layer as is */ }
      }
      const tracks = []; let dur = 0;
      for (const t of c.tracks) {
        const bone = bonesT[t.bone]; if (!bone) continue;
        if (t.pos.length) { const times = [], vals = []; const lock = rigT.bones[t.bone].p < 0; const x0 = t.pos[1], y0 = t.pos[2]; for (let i = 0; i < t.pos.length; i += 4) { times.push(t.pos[i]); vals.push(lock ? t.pos[i + 1] - x0 : t.pos[i + 1], lock ? t.pos[i + 2] - y0 : t.pos[i + 2], t.pos[i + 3]); } dur = Math.max(dur, times[times.length - 1]); tracks.push(new THREE.VectorKeyframeTrack(bone.name + '.position', times, vals)); }
        if (t.rot.length) { const times = [], vals = []; for (let i = 0; i < t.rot.length; i += 5) { times.push(t.rot[i]); vals.push(t.rot[i + 1], t.rot[i + 2], t.rot[i + 3], t.rot[i + 4]); } dur = Math.max(dur, times[times.length - 1]); tracks.push(new THREE.QuaternionKeyframeTrack(bone.name + '.quaternion', times, vals)); }
      }
      clip = new THREE.AnimationClip(name, dur || 1, tracks); this.clipCache.set(key, clip);
    }
    return clip;
  }

  async play(astPath, name) {
    const clip = await this.clipFor(astPath, name);
    const comp = await Promise.all((this.companions || []).map(async c => [c, c.clips.has(name) ? await this.clipFor(c.ast, name, c) : null]));   // fetch every clip first so body and cloak start on the same frame
    if (this.action) this.action.fadeOut(0.15);
    this.curClip = [astPath, name];
    this.action = this.mixer.clipAction(clip); this.action.reset().setLoop(THREE.LoopRepeat).fadeIn(0.15).play();
    this.action.timeScale = this.speed || 1;
    for (const [c, cc] of comp) {
      if (c.action) c.action.fadeOut(0.15);
      c.action = null; c.group.visible = !!cc;   // the cloak is shown only on clips it has its own animation for
      if (!cc) continue;
      c.action = c.mixer.clipAction(cc); c.action.reset().setLoop(THREE.LoopRepeat).fadeIn(0.15).play(); c.action.timeScale = this.speed || 1;
    }
  }

  // glTF export for Blender: skeleton + all visible skinned meshes (+textures) + every clip of the rig
  async exportGLB({ clips = true, rows = null, onProgress = () => {} } = {}) {
    if (!this.root || !this.skeleton) throw new Error('Нет модели');
    const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
    const anims = [];
    if (clips && this.rig && this.actor) {
      const list = rows && rows.length ? rows : this.rig.clips.map(c => ({ ast: this.actor.skeleton, clip: c.name }));
      let done = 0, i = 0;
      const worker = async () => { while (i < list.length) { const r = list[i++]; try { const c = await this.clipFor(r.ast, r.clip); if (c && c.tracks.length) anims.push({ c, name: r.clip }); } catch (e) { /* clip not usable on this rig */ } onProgress(++done, list.length); } };
      await Promise.all(Array.from({ length: 6 }, worker));
      anims.sort((x, y) => x.name.localeCompare(y.name));
    }
    const used = new Map(), final = anims.map(({ c, name }) => { const n = (used.get(name) || 0) + 1; used.set(name, n); return n === 1 ? c : new THREE.AnimationClip(name + '__' + n, c.duration, c.tracks); });
    const prev = this.curClip;
    if (this.mixer) this.mixer.stopAllAction();
    this.skeleton.pose(); (this.phys || []).forEach(c => c.sk.pose()); this.root.updateWorldMatrix(true, true);
    try {
      const buf = await new Promise((res, rej) => new GLTFExporter().parse(this.root, res, rej, { binary: true, animations: final, onlyVisible: true }));
      return mergeSkins(buf);
    } finally { if (prev) { try { await this.play(prev[0], prev[1]); } catch (e) { /* ignore */ } } }
  }

  setSpeed(v) { this.speed = v; if (this.action) this.action.timeScale = v; (this.companions || []).forEach(c => { if (c.action) c.action.timeScale = v; }); }
  update(dt) { if (this.mixer) this.mixer.update(dt); this.stepPhys(dt); for (const c of this.companions || []) c.mixer.update(dt); if (this.lightShown) this.updateMarker(); }

  fit() {
    const V = this.ctx.getViewer(); const p = new THREE.Vector3(); this.root.updateWorldMatrix(true, true);
    const bb = new THREE.Box3(); this.root.traverse(o => { if (o.isSkinnedMesh) { o.geometry.computeBoundingBox(); const b = o.geometry.boundingBox.clone().applyMatrix4(this.root.matrixWorld); bb.union(b); } });
    if (bb.isEmpty()) return; const c = bb.getCenter(p), sz = bb.getSize(new THREE.Vector3()), h = Math.max(sz.y, sz.x, sz.z);
    V.ctl.target.set(c.x, c.y, c.z);
    if (!this.ctx.keepCamera) V.cam.position.set(c.x, c.y + h * 0.12, c.z - (h * 2.0 + 0.8));
    V.ctl.update();
  }
}

export { SLOT_ORDER, SLOT_LABEL };
