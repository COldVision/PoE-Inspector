// A real object of the skill's art thrown (Forge Hammer: HammerOfTheGods) or dropped from the sky (Starborn Onslaught: the verisium maul),
// with the mesh and colour texture named by the effect's .pet. The burst on impact is done by the caller.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const S = 0.01;
const GAME = new THREE.Matrix4().set(S, 0, 0, 0, 0, 0, -S, 0, 0, S, 0, 0, 0, 0, 0, 1);
const glow = c => { const k = document.createElement('canvas'); k.width = k.height = 64; const x = k.getContext('2d'), g = x.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.4, `rgba(${c.map(v => Math.round(v * 255))},.6)`); g.addColorStop(1, 'rgba(0,0,0,0)'); x.fillStyle = g; x.fillRect(0, 0, 64, 64); const t = new THREE.CanvasTexture(k); t.colorSpace = THREE.SRGBColorSpace; return t; };

export async function petAsset(petPath, idx = 0) {
  const em = await (await fetch('/api/pet?path=' + encodeURIComponent(petPath))).json();
  const e = em.filter(x => x.meshUrl)[idx]; return e ? { meshUrl: e.meshUrl, texUrl: e.texUrl } : null;
}

export class ObjectFx {
  constructor(scene, opt) {
    window.__obj = this; this.scene = scene; this.o = opt; this.state = 'idle'; this.t = 0; this.size = opt.size || 1.2; this.onLand = null;
    this.pivot = new THREE.Group(); this.pivot.visible = false; scene.add(this.pivot);
    const tr = opt.trail || [1, .6, .3]; this.trailTex = glow(tr);
    this.trail = Array.from({ length: 22 }, () => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.trailTex, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })); s.visible = false; scene.add(s); return { s, life: 0 }; });
    this.ready = this._load();
  }
  async _load() {
    const o = this.o, g = await new GLTFLoader().loadAsync(o.meshUrl);
    const holder = new THREE.Group(); holder.matrixAutoUpdate = false; holder.matrix.copy(GAME); holder.add(g.scene); holder.updateMatrixWorld(true);
    let map = null; if (o.texUrl && (await fetch(o.texUrl).catch(() => ({ ok: false }))).ok) { map = new THREE.TextureLoader().load(o.texUrl); map.colorSpace = THREE.SRGBColorSpace; map.anisotropy = 8; }
    const mat = new THREE.MeshStandardMaterial({ map, color: map ? 0xffffff : 0x8a8f96, roughness: .55, metalness: .45, emissive: new THREE.Color(...(o.emissive || [0, 0, 0])), emissiveIntensity: .55, side: THREE.DoubleSide, transparent: true });
    this.mat = mat; g.scene.traverse(m => { if (m.isMesh) { m.material = mat; m.castShadow = true; } });
    const bb = new THREE.Box3().setFromObject(holder), sz = bb.getSize(new THREE.Vector3()), c = bb.getCenter(new THREE.Vector3());
    // heavy end = side of the long axis where the vertices pile up
    let up = 0, n = 0; const v = new THREE.Vector3(); g.scene.traverse(m => { if (m.isMesh) { const p = m.geometry.attributes.position; for (let i = 0; i < p.count; i += 3) { v.fromBufferAttribute(p, i).applyMatrix4(m.matrixWorld).applyMatrix4(holder.matrix); up += v.y - c.y; n++; } } });
    const long = Math.max(sz.x, sz.y, sz.z), f = this.size / long;
    holder.matrixAutoUpdate = true; const inner = new THREE.Group(); inner.add(holder);
    holder.matrix.decompose(holder.position, holder.quaternion, holder.scale); holder.matrixAutoUpdate = true; holder.position.sub(c.clone().multiplyScalar(1)).multiplyScalar(1);
    inner.scale.setScalar(f); inner.position.set(0, 0, 0);
    // re-centre after scaling: the holder carries the centering in its own (unscaled) space
    holder.position.copy(holder.position);
    if (sz.y < Math.max(sz.x, sz.z)) inner.rotation.z = Math.PI / 2;   // long axis is not vertical: stand it up
    this.headDown = up < 0;   // heavy end at -Y: flip so the head leads upward
    if (this.headDown) inner.rotation.x += Math.PI;
    this.pivot.add(inner); this.inner = inner; this.len = long * f;
    return true;
  }
  _trailBit(p, col) {
    const b = this.trail.find(x => x.life <= 0); if (!b) return; b.life = .45; b.s.position.copy(p).add(new THREE.Vector3((Math.random() - .5) * .25, (Math.random() - .5) * .25, (Math.random() - .5) * .25)); b.s.visible = true; b.sc = .35 + Math.random() * .4;
  }
  // throw from `from` to `to` in an arc, spinning end over end
  throw(from, to, onLand, flight = .55) {
    this.onLand = onLand; this.from = from.clone(); this.to = to.clone(); this.flight = flight; this.t = 0; this.state = 'fly'; this.pivot.visible = true; this.pivot.scale.setScalar(1); this.mat && (this.mat.opacity = 1);
    this.dir = to.clone().sub(from).setY(0).normalize();
  }
  // drop from the sky onto `to`, head first
  drop(to, onLand, fall = .38, height = 11) {
    this.onLand = onLand; this.to = to.clone(); this.from = to.clone().add(new THREE.Vector3(0, height, 0)); this.flight = fall; this.t = 0; this.state = 'fall'; this.pivot.visible = true; this.pivot.scale.setScalar(1); this.mat && (this.mat.opacity = 1);
  }
  update(dt) {
    for (const b of this.trail) if (b.life > 0) { b.life -= dt; const k = Math.max(0, b.life / .45); b.s.material.opacity = k * .9; b.s.scale.setScalar(b.sc * (1.3 - k * .5)); if (b.life <= 0) b.s.visible = false; }
    if (!this.inner) return;
    if (this.state === 'fly' || this.state === 'fall') {
      this.t += dt; const k = Math.min(1, this.t / this.flight);
      if (this.state === 'fly') {
        this.pivot.position.lerpVectors(this.from, this.to, k); this.pivot.position.y += Math.sin(Math.PI * k) * 1.5 + (1 - k) * 0;
        this.pivot.rotation.set(0, Math.atan2(this.dir.x, this.dir.z), 0); this.inner.rotation.x += 0; this.pivot.rotateX(k * 16);
      } else {
        const e = k * k; this.pivot.position.lerpVectors(this.from, this.to, e); this.pivot.position.y = this.to.y + (this.from.y - this.to.y) * (1 - e) + this.len * .5;
        this.pivot.rotation.set(Math.PI, 0, 0.05);
      }
      this._trailBit(this.pivot.position);
      if (k >= 1) {
        this.state = 'stay'; this.t = 0;
        if (this.o.mode === 'fall') { this.pivot.position.copy(this.to); this.pivot.position.y += this.len * .32; this.pivot.rotation.set(Math.PI, 0, .06); }
        else { this.pivot.position.copy(this.to); this.pivot.position.y += .22; this.pivot.rotation.set(Math.PI * .5, Math.atan2(this.dir.x, this.dir.z) + 1.2, .25); }
        const cb = this.onLand; if (cb) cb();
      }
      return;
    }
    if (this.state === 'stay') {
      this.t += dt; const stay = this.o.stay || 1.8;
      if (this.t > stay) { const k = Math.min(1, (this.t - stay) / .5); if (this.mat) this.mat.opacity = 1 - k; if (k >= 1) { this.state = 'idle'; this.pivot.visible = false; } }
    }
  }
  dispose() { this.scene.remove(this.pivot); this.trail.forEach(b => this.scene.remove(b.s)); if (this.mat) this.mat.dispose(); }
}
