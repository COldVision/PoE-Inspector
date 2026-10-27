// Real effect meshes of a skill's art (.ao -> .sm) spawned procedurally at the impact: cracks / fissures / craters are laid on the ground,
// spikes rise out of it. The authored vertex animation is not reproduced (formats of the effect rigs are not readable), the shapes and textures are the game's.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const S = 0.01;
const GAME = new THREE.Matrix4().set(S, 0, 0, 0, 0, 0, -S, 0, 0, S, 0, 0, 0, 0, 0, 1);   // game (x,y,z) -> three (x,-z,y)*0.01 as in the editor
const kindOf = n => /spike|spine|pillar|rock|shard|stalag/i.test(n) ? 'rise' : /crack|fissure|crater|marker|core|edge|scorch|decal/i.test(n) ? 'decal' : 'skip';

export class AoMeshFx {
  constructor(scene) { window.__ao = this; this.scene = scene; this.root = new THREE.Group(); scene.add(this.root); this.defs = []; this.live = []; this.ready = false; }
  async load(aoPaths) {
    const loader = new GLTFLoader(), tl = new THREE.TextureLoader(), seen = new Set(), jobs = [];
    for (const ao of aoPaths) {
      const name = ao.split('/').pop(), kind = kindOf(name); if (kind === 'skip' || seen.has(name.toLowerCase())) continue; seen.add(name.toLowerCase());
      jobs.push((async () => {
        try {
          const info = await (await fetch('/api/aomesh?ao=' + encodeURIComponent(ao))).json(); if (!info.sm) return;
          const g = await loader.loadAsync('/api/skin?sm=' + encodeURIComponent(info.sm.toLowerCase()) + '&static=1&pbr=0');
          let map = null; if (info.tex) { map = tl.load('/api/icon?size=512&path=' + encodeURIComponent(info.tex)); map.colorSpace = THREE.SRGBColorSpace; map.wrapS = map.wrapT = THREE.RepeatWrapping; }
          if (kind === 'decal' && (!info.tex || /general_mesh_particle_test/i.test(info.tex))) return;   // projected-heightmap materials (no texture of their own) cannot be drawn: skip instead of a black blob
          const mat = kind === 'rise'
            ? new THREE.MeshStandardMaterial({ map, color: map ? 0xffffff : 0x8a7a6a, roughness: .95, metalness: 0, side: THREE.DoubleSide })
            : new THREE.MeshBasicMaterial({ map, color: map ? 0xffffff : 0x222222, transparent: true, depthWrite: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, alphaTest: .02 });
          g.scene.traverse(o => { if (o.isMesh) { o.material = mat; o.castShadow = kind === 'rise'; } });
          const holder = new THREE.Group(); holder.matrixAutoUpdate = false; holder.matrix.copy(GAME); holder.add(g.scene); holder.updateMatrixWorld(true);
          const bb = new THREE.Box3().setFromObject(holder), sz = bb.getSize(new THREE.Vector3());
          this.defs.push({ name, kind, holder, mat, size: sz, center: bb.getCenter(new THREE.Vector3()), minY: bb.min.y });
        } catch (e) { /* mesh not loadable: skip */ }
      })());
    }
    await Promise.all(jobs); this.ready = true; return this.defs.length;
  }
  // pos = impact point, dir = forward (xz); R = reach in metres
  spawn(pos, dir, R = 3) {
    const d = new THREE.Vector3(dir.x, 0, dir.z).normalize(), yaw = Math.atan2(d.x, d.z);
    const decals = this.defs.filter(x => x.kind === 'decal'), rises = this.defs.filter(x => x.kind === 'rise');
    decals.forEach((def, i) => {
      const inst = this._inst(def); const fiss = /fissure/i.test(def.name), long = Math.max(def.size.x, def.size.z) || 1, want = fiss ? R * 2.2 : R * 1.6;
      const sc = Math.min(3, want / long); inst.scale.setScalar(sc);
      inst.position.copy(pos); inst.position.y += .015 + i * .004;
      inst.rotation.y = fiss ? yaw : Math.random() * 6.28;
      if (fiss) inst.position.addScaledVector(d, long * sc * .35);
      this.live.push({ o: inst, def, t: 0, life: 2.6, kind: 'decal', s: sc, delay: i * .05 });
    });
    const side = new THREE.Vector3(-d.z, 0, d.x);
    rises.forEach((def, i) => {
      const n = 4 + (i % 3);
      for (let k = 0; k < n; k++) {
        const inst = this._inst(def), a = Math.random() * 6.28;
        const along = .6 + Math.random() * R, lat = (Math.random() * 2 - 1) * R * .45, sc = (.7 + Math.random() * .8) * Math.min(2.5, 1.4 / Math.max(.2, def.size.y));
        inst.position.copy(pos).addScaledVector(d, along).addScaledVector(side, lat); inst.position.y -= def.minY * sc;
        inst.rotation.set((Math.random() - .5) * .3, a, (Math.random() - .5) * .3); inst.scale.setScalar(sc * .001);
        this.live.push({ o: inst, def, t: 0, life: 1.7, kind: 'rise', s: sc, delay: (k + i) * .045 + along * .03, y0: inst.position.y });
      }
    });
  }
  _inst(def) { const o = new THREE.Group(); o.add(def.holder.clone(true)); o.visible = false; this.root.add(o); return o; }
  update(dt) {
    for (let i = this.live.length - 1; i >= 0; i--) {
      const e = this.live[i]; e.t += dt; const t = e.t - e.delay;
      if (t < 0) continue;
      if (t > e.life) { this.root.remove(e.o); this.live.splice(i, 1); continue; }
      e.o.visible = true;
      if (e.kind === 'rise') { const k = t < .14 ? 1 - Math.pow(1 - t / .14, 3) : t < .8 ? 1 : 1 - Math.pow((t - .8) / (e.life - .8), 2); e.o.scale.set(e.s, Math.max(.001, e.s * k), e.s); e.o.position.y = e.y0; }
      else { const a = Math.min(1, t / .12) * (1 - Math.max(0, t - 1.1) / (e.life - 1.1)); e.def.mat.opacity = 1; e.o.traverse(m => { if (m.isMesh) m.material = e.def.mat; }); e.o.scale.setScalar(e.s * (.7 + .3 * Math.min(1, t / .25))); e.o.userData.a = a; }
    }
    // decals share one material: use the dimmest live instance as the overall opacity (simple, no per-instance clones)
    for (const def of this.defs) if (def.kind === 'decal') { const l = this.live.filter(e => e.def === def); def.mat.opacity = l.length ? Math.max(...l.map(e => e.o.userData.a ?? 0)) : 0; }
  }
  dispose() { this.scene.remove(this.root); this.defs.forEach(d => d.mat.dispose()); }
}
