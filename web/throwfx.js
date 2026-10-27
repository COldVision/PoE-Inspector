// Pilot: thrown flask (Concoction skills): the flask sits in the hand during the wind-up, flies in an arc to a point in front of the
// character and bursts there (flash, shock ring, arcs or splash, scorch / puddle on the ground).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const KINDS = {
  lightning: { c: [.55, .82, 1], c2: [1, 1, 1], arcs: true, scorch: [.04, .05, .07] },
  fire: { c: [1, .45, .12], c2: [1, .85, .4], arcs: false, scorch: [.05, .03, .02], flames: true },
  cold: { c: [.65, .9, 1], c2: [1, 1, 1], arcs: false, scorch: [.5, .65, .75], shards: true },
  chaos: { c: [.5, .85, .25], c2: [.85, 1, .5], arcs: false, scorch: [.12, .3, .06], puddle: true },
  blood: { c: [.7, .05, .08], c2: [1, .25, .2], arcs: false, scorch: [.25, .02, .03], puddle: true },
};

const glow = (inner, outer) => {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d'), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, inner); g.addColorStop(.4, outer); g.addColorStop(1, 'rgba(0,0,0,0)'); x.fillStyle = g; x.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
};

export class FlaskThrowFx {
  constructor(scene, opt) {
    this.scene = scene; this.k = KINDS[opt.kind] || KINDS.lightning; this.R = opt.radius || 1.8; this.flight = opt.flight || .72; this.range = opt.range || 5.5;
    this.root = new THREE.Group(); scene.add(this.root);
    this.flask = null; this.held = null; this.t = -1; this.state = 'idle';
    const col = new THREE.Color(...this.k.c), col2 = new THREE.Color(...this.k.c2);
    this.ring = new THREE.Mesh(new THREE.RingGeometry(.82, 1, 64), new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    this.ring.rotation.x = -Math.PI / 2; this.ring.visible = false; this.root.add(this.ring);
    this.flash = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow('rgba(255,255,255,1)', `rgba(${this.k.c.map(v => Math.round(v * 255))},.55)`), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.flash.visible = false; this.root.add(this.flash);
    this.light = new THREE.PointLight(col, 0, 7, 2); this.root.add(this.light);
    const sc = document.createElement('canvas'); sc.width = sc.height = 64; const sx = sc.getContext('2d'), sg = sx.createRadialGradient(32, 32, 0, 32, 32, 32);
    const rgb = this.k.scorch.map(v => Math.round(v * 255)).join(',');
    sg.addColorStop(0, `rgba(${rgb},.85)`); sg.addColorStop(.6, `rgba(${rgb},.45)`); sg.addColorStop(1, `rgba(${rgb},0)`); sx.fillStyle = sg; sx.fillRect(0, 0, 64, 64);
    this.scorch = new THREE.Mesh(new THREE.CircleGeometry(1, 40), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(sc), transparent: true, opacity: 0, depthWrite: false }));
    this.scorch.rotation.x = -Math.PI / 2; this.scorch.position.y = .02; this.scorch.visible = false; this.scorch.renderOrder = 4; this.root.add(this.scorch);
    this.arcs = [];
    if (this.k.arcs) for (let i = 0; i < 12; i++) { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(10 * 3), 3)); const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color: col2, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })); l.visible = false; l.frustumCulled = false; this.root.add(l); this.arcs.push(l); }
    // droplets / embers / shards
    this.bits = Array.from({ length: 36 }, () => { const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow(`rgba(${this.k.c2.map(v => Math.round(v * 255))},1)`, `rgba(${this.k.c.map(v => Math.round(v * 255))},.6)`), transparent: true, opacity: 0, blending: this.k.puddle ? THREE.NormalBlending : THREE.AdditiveBlending, depthWrite: false })); m.visible = false; this.root.add(m); return { m, v: new THREE.Vector3(), life: 1 }; });
    this.puddle = null;
    // the flask model
    new GLTFLoader().load(opt.flaskUrl, g => {
      const m = g.scene; m.traverse(o => { if (o.isMesh) { o.castShadow = true; if (o.material) o.material.side = THREE.DoubleSide; } });
      const b = new THREE.Box3().setFromObject(m), sz = b.getSize(new THREE.Vector3()), c = b.getCenter(new THREE.Vector3()), f = 1 / Math.max(sz.y, 1e-4);
      m.scale.setScalar(f); m.position.copy(c).multiplyScalar(-f);
      this.template = new THREE.Group(); this.template.add(m);
    });
  }
  _flaskClone(h) { const g = this.template.clone(true); g.scale.setScalar(h); return g; }
  // flask in the hand while the character winds up (bone local units = game units)
  hold(bone) {
    this.release();
    if (!this.template || !bone) return;
    this.held = this._flaskClone(34); this.held.rotation.set(0, 0, Math.PI * .5); bone.add(this.held); this.heldBone = bone;
  }
  release() { if (this.held && this.heldBone) this.heldBone.remove(this.held); this.held = null; }
  // launch from `from` to `to` (world, y = ground); the explosion calls onLand
  launch(from, to, onLand) {
    this.release();
    if (!this.template) { this._boom(to); if (onLand) onLand(); return; }
    this.flask = this._flaskClone(.34); this.flask.position.copy(from); this.scene.add(this.flask);
    this.from = from.clone(); this.to = to.clone(); this.t = 0; this.state = 'fly'; this.onLand = onLand; this.spin = new THREE.Vector3(rnd() * 10 + 8, rnd() * 4, rnd() * 6);
  }
  _boom(p) {
    this.root.position.set(p.x, 0, p.z); this.state = 'boom'; this.t = 0;
    for (const o of [this.ring, this.flash, this.scorch]) o.visible = true;
    this.flash.position.y = .35; this.light.position.y = .8; this.light.intensity = 26;
    this.scorch.scale.setScalar(this.R * .9);
    for (const b of this.bits) { const a = Math.random() * 6.283, sp = this.k.puddle ? 1.5 + Math.random() * 3 : 1 + Math.random() * 3.4; b.m.position.set(0, .15, 0); b.v.set(Math.cos(a) * sp, (this.k.puddle ? 1.6 : 2.4) + Math.random() * 2.6, Math.sin(a) * sp); b.life = .5 + Math.random() * .7; b.m.visible = true; b.m.material.opacity = 0; b.s = .12 + Math.random() * .22; }
    this.arcs.forEach(l => { l.visible = true; });
  }
  update(dt) {
    if (this.state === 'fly') {
      this.t += dt; const k = Math.min(1, this.t / this.flight);
      this.flask.position.lerpVectors(this.from, this.to, k); this.flask.position.y = this.from.y + (this.to.y - this.from.y) * k + Math.sin(Math.PI * k) * 1.3;
      this.flask.rotation.x += this.spin.x * dt; this.flask.rotation.y += this.spin.y * dt; this.flask.rotation.z += this.spin.z * dt;
      if (k >= 1) { this.scene.remove(this.flask); this.flask = null; const cb = this.onLand; this._boom(this.to); if (cb) cb(); }
      return;
    }
    if (this.state !== 'boom') return;
    this.t += dt; const t = this.t;
    const R = this.R, e = 1 - Math.pow(1 - Math.min(t / .3, 1), 3);
    this.ring.scale.setScalar(Math.max(.05, e * R)); this.ring.position.y = .06; this.ring.material.opacity = Math.max(0, 1 - t / .45) * .95;
    const fs = R * (1.2 + e * 1.4); this.flash.scale.set(fs, fs, 1); this.flash.material.opacity = Math.max(0, 1 - t / .32);
    this.light.intensity = Math.max(0, 26 * (1 - t / .45));
    this.scorch.material.opacity = Math.min(1, t / .1) * Math.max(0, 1 - Math.max(0, t - .5) / 1.9);
    this.arcs.forEach((l, i) => {
      if (t > .34) { l.visible = false; return; }
      const p = l.geometry.attributes.position, a = i / this.arcs.length * 6.283 + rnd() * .2, len = R * (.5 + Math.random() * .6);
      let x = 0, y = .15, z = 0;
      for (let j = 0; j < 10; j++) { p.setXYZ(j, x, y, z); const s = len / 9; x += Math.cos(a) * s + rnd() * .12; z += Math.sin(a) * s + rnd() * .12; y = .12 + Math.random() * .5 * (1 - j / 10); }
      p.needsUpdate = true; l.material.opacity = Math.max(0, 1 - t / .34) * (.6 + Math.random() * .4);
    });
    for (const b of this.bits) {
      const k = t / b.life; if (k >= 1) { b.m.visible = false; continue; }
      b.m.position.addScaledVector(b.v, dt); b.v.y -= 6 * dt; if (b.m.position.y < .04) { b.m.position.y = .04; b.v.multiplyScalar(.3); }
      const s = b.s * (1 + k * .6); b.m.scale.set(s, s, 1); b.m.material.opacity = Math.min(1, k / .06) * (1 - k);
    }
    if (t > 2.4) { this.state = 'idle'; for (const o of [this.ring, this.flash, this.scorch]) o.visible = false; this.arcs.forEach(l => { l.visible = false; }); this.light.intensity = 0; this.bits.forEach(b => { b.m.visible = false; }); }
  }
  dispose() { this.release(); if (this.flask) this.scene.remove(this.flask); this.scene.remove(this.root); }
}
const rnd = () => Math.random() * 2 - 1;
