// Particle engine for PoE2 .pet effects (parsed server-side into JSON by poe_inspector/pet.py).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export function gEval(g, t) {
  if (!g || !g.length) return [0];
  if (t <= g[0].t) return g[0].v;
  for (let k = 0; k < g.length - 1; k++) {
    const a = g[k], b = g[k + 1];
    if (t <= b.t) {
      if (a.i === 'Flat') return a.v;
      let u = (t - a.t) / Math.max(b.t - a.t, 1e-6);
      if (a.i === 'Smooth') u = u * u * (3 - 2 * u);
      return a.v.map((x, i) => x + (b.v[i] - x) * u);
    }
  }
  return g[g.length - 1].v;
}

const VERT = `
attribute vec3 aPos; attribute vec3 aVel; attribute vec2 aSize; attribute vec4 aCol; attribute float aRot; attribute float aFrame;
uniform float uMode; uniform float uFrames;
varying vec2 vUv; varying vec4 vCol;
void main(){
  vUv = vec2((uv.x + aFrame) / uFrames, uv.y);
  vCol = aCol;
  vec3 toCam = normalize(cameraPosition - aPos);
  vec3 right, up; vec2 q = position.xy;
  if (uMode < 0.5) {
    right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
    up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
    float c = cos(aRot), s = sin(aRot);
    vec3 r2 = right * c + up * s; vec3 u2 = -right * s + up * c; right = r2; up = u2;
  } else if (uMode < 1.5) {
    up = vec3(0., 1., 0.); right = normalize(cross(up, toCam)); q.y += 0.5;
  } else {
    up = normalize(aVel + vec3(0., 1e-4, 0.)); right = normalize(cross(up, toCam));
  }
  vec3 world = aPos + right * q.x * aSize.x + up * q.y * aSize.y;
  gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.);
}`;
const FRAG = `
uniform sampler2D map; uniform float uAlphaTest; uniform float uLinear; uniform vec3 uTint; uniform float uInt; uniform vec2 uLuma;
varying vec2 vUv; varying vec4 vCol;
void main(){
  vec4 t = texture2D(map, vUv);
  float a = t.a;
  if (uLuma.y > 0.) a = smoothstep(uLuma.x, uLuma.y, dot(t.rgb, vec3(.299, .587, .114)));
  vec4 c = vec4(t.rgb * uTint * uInt * vCol.rgb, a * vCol.a);
  if (uAlphaTest > 0. && c.a < uAlphaTest) discard;
  if (c.a < 0.003) discard;
  if (uLinear > 0.5) c.rgb = pow(c.rgb, vec3(2.2));
  gl_FragColor = c;
}`;

const rnd = () => Math.random() * 2 - 1;

class Emitter {
  constructor(def, tex, origin, opts) {
    this.d = def; this.o = origin; this.S = opts.scale; this.acc = Math.random();
    this.life = def.particle_duration || 1;
    this.pps = gEval(def.particles_per_second, 0)[0] * (opts.density || 1);
    this.max = Math.min(600, Math.ceil(this.pps * this.life * (1 + (def.particle_duration_variance || 0)) * 1.6) + 8);
    this.p = [];
    this.wm = /ember/i.test(def.mat || '') ? 3 : (/bloom_glow/i.test(def.mat || '') ? 0.45 : 1); this.hm = /ember/i.test(def.mat || '') ? 3 : /bloom_glow/i.test(def.mat || '') ? 0.45 : (/fire\.mat/i.test(def.mat || '') ? 2.2 : 1);
    const mode = def.face_type === 'ZLock' ? (def.rotation_lock_type === 'Velocity' ? 2 : 1) : (def.rotation_lock_type === 'Velocity' ? 2 : 0);
    const n = this.max;
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-.5, -.5, 0, .5, -.5, 0, .5, .5, 0, -.5, .5, 0]), 3));
    g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), 2));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    const mk = (name, size) => { const a = new THREE.InstancedBufferAttribute(new Float32Array(n * size), size); a.setUsage(THREE.DynamicDrawUsage); g.setAttribute(name, a); return a; };
    this.a = { pos: mk('aPos', 3), vel: mk('aVel', 3), size: mk('aSize', 2), col: mk('aCol', 4), rot: mk('aRot', 1), frame: mk('aFrame', 1) };
    g.instanceCount = 0;
    const add = def.blend_mode === 'Additive';
    this.mat = new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false,
      blending: add ? THREE.AdditiveBlending : THREE.NormalBlending, side: THREE.DoubleSide,
      uniforms: { map: { value: tex }, uMode: { value: mode }, uFrames: { value: Math.max(1, def.number_of_frames || 1) },
                  uAlphaTest: { value: def.blend_mode === 'AlphaTest' ? 0.45 : 0 }, uLinear: { value: opts.linear ? 1 : 0 },
                  uTint: { value: new THREE.Vector3(...((def.matp && def.matp.tint) || [1, 1, 1])) }, uInt: { value: ((def.matp && def.matp.intensity) || 1) * (/bloom_glow/i.test(def.mat || '') ? 0.15 : (/smoke/i.test(def.mat || '') ? 0.4 : 1)) },
                  uLuma: { value: new THREE.Vector2(...((def.matp && def.matp.luma) || [0, 0])) } },
    });
    this.mesh = new THREE.Mesh(g, this.mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = add ? 12 : 10;
    this.g = g;
  }
  spawn() {
    const d = this.d, S = this.S;
    const life = Math.max(.05, this.life * (1 + (d.particle_duration_variance || 0) * rnd()));
    const R = 10 * S, ang = Math.random() * 6.283, rr = Math.sqrt(Math.random()) * R;
    const cone = Math.min(gEval(d.scatter_cone_size, 0)[0] || 0, Math.PI);
    const phi = Math.random() * 6.283, cz = 1 - Math.random() * (1 - Math.cos(cone)), sz = Math.sqrt(1 - cz * cz);
    const dir = new THREE.Vector3(Math.cos(phi) * sz, cz, Math.sin(phi) * sz);
    this.p.push({
      age: 0, life,
      pos: new THREE.Vector3(this.o.x + Math.cos(ang) * rr, this.o.y + Math.random() * 2 * S, this.o.z + Math.sin(ang) * rr),
      dir, vAlongOff: rnd() * (d.velocity_along_variance || 0), vUpOff: rnd() * (d.velocity_up_variance || 0),
      sOff: rnd() * (d.scale_variance || 0), stOff: 1 + rnd() * (d.stretch_variance || 0),
      rot: d.rotation_lock_type === 'Random' || d.face_type === 'FaceCamera' ? Math.random() * 6.283 : 0,
      rs: rnd() * (d.rotation_speed_variance || 0), frame: Math.floor(Math.random() * Math.max(1, d.number_of_frames || 1)),
      vel: new THREE.Vector3(),
    });
  }
  update(dt) {
    const d = this.d, S = this.S;
    this.acc += this.pps * dt;
    while (this.acc >= 1) { this.acc -= 1; if (this.p.length < this.max) this.spawn(); }
    const ec = gEval(d.emit_colour, 0), a = this.a;
    let n = 0;
    for (let i = this.p.length - 1; i >= 0; i--) { this.p[i].age += dt; if (this.p[i].age >= this.p[i].life) this.p.splice(i, 1); }
    for (const q of this.p) {
      const t = q.age / q.life;
      const along = gEval(d.velocity_along, t)[0] + q.vAlongOff, up = gEval(d.velocity_up, t)[0] + q.vUpOff;
      q.vel.copy(q.dir).multiplyScalar(along * S); q.vel.y += up * S;
      q.pos.addScaledVector(q.vel, dt);
      q.rot += (gEval(d.rotation_speed, t)[0] + q.rs) * dt;
      const sc = Math.max(0, gEval(d.scale, t)[0] + q.sOff) * S, st = (gEval(d.stretch, t)[0] || 1) * q.stOff;
      const c = gEval(d.colour, t);
      a.pos.setXYZ(n, q.pos.x, q.pos.y, q.pos.z); a.vel.setXYZ(n, q.vel.x, q.vel.y, q.vel.z);
      a.size.setXY(n, sc * this.wm, sc * st * this.hm);
      a.col.setXYZW(n, c[0] * ec[0], c[1] * ec[1], c[2] * ec[2], c[3] * ec[3]);
      a.rot.setX(n, q.rot);
      a.frame.setX(n, d.anim_speed > 0 ? Math.floor(t * (d.number_of_frames || 1)) % (d.number_of_frames || 1) : q.frame);
      n++;
    }
    this.g.instanceCount = n;
    for (const k in a) a[k].needsUpdate = true;
  }
}

// one-shot mesh effect (pillar / sphere / helix / ribbon) looped with the emitter's duration
const MESH_SIZE = [[/cyl/i, 2.4], [/sphere/i, 1.5], [/helix|slice/i, 2.4], [/ribbon/i, 2.0]];
class MeshFx {
  constructor(scene, def, tex, origin) {
    this.scene = scene; this.o = origin; this.dur = Math.max(.15, def.particle_duration || 1); this.t = Math.random() * .2; this.gap = Math.min(1.2, this.dur * .6 + .3);
    this.size = (MESH_SIZE.find(m => m[0].test(def.mesh)) || [0, 1.5])[1];
    const tint = (def.matp && def.matp.tint) || [1, 1, 1], k = Math.min(3, (def.matp && def.matp.intensity) || 1);
    tex.colorSpace = THREE.SRGBColorSpace; tex.wrapS = tex.wrapT = THREE.RepeatWrapping; this.tex = tex;
    this.mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, color: new THREE.Color(tint[0] * k, tint[1] * k, tint[2] * k), opacity: 0 });
    this.root = new THREE.Group(); this.root.visible = false; scene.add(this.root);
    new GLTFLoader().load(def.meshUrl, g => {
      if (this.dead) return;
      const m = g.scene; m.traverse(o => { if (o.isMesh) o.material = this.mat; });
      const b = new THREE.Box3().setFromObject(m), sz = b.getSize(new THREE.Vector3()), c = b.getCenter(new THREE.Vector3());
      const f = 1 / Math.max(sz.x, sz.y, sz.z, 1e-4); m.scale.setScalar(f); m.position.copy(c).multiplyScalar(-f);
      this.root.add(m); this.ready = true;
    });
  }
  update(dt) {
    if (!this.ready) return;
    this.t += dt; const cyc = this.dur + this.gap, u = (this.t % cyc) / this.dur;
    if (u > 1) { this.root.visible = false; return; }
    this.root.visible = true; this.root.position.copy(this.o);
    const e = 1 - Math.pow(1 - u, 2.2), s = this.size * (.35 + .65 * e);
    this.root.scale.set(s, s, s);
    this.mat.opacity = Math.min(1, u / .12) * Math.pow(1 - u, .8);
    this.tex.offset.y = -u * .8;
  }
  dispose() { this.dead = true; this.scene.remove(this.root); this.mat.dispose(); }
}

export class PetSystem {
  constructor(scene, emitters, origin, opts = {}) {
    this.scene = scene; this.list = [];
    const loader = new THREE.TextureLoader();
    for (const def of emitters) {
      if (def.type === 'gpu' && def.meshUrl && def.texUrl) {
        const tex = loader.load(def.texUrl); const m = new MeshFx(scene, def, tex, origin); this.list.push(m); continue;
      }
      if (def.type !== 'gpu' && (!def.texUrl || /distortion|shimmer/i.test(def.tex || ''))) continue;
      let tex;
      if (def.type === 'gpu' && (!def.texUrl || /noise|caustic|distortion|shimmer/i.test(def.tex || ''))) {
        // mesh/GPU emitters have no sprite: approximate with a soft glow
        const c = document.createElement('canvas'); c.width = c.height = 64;
        const x = c.getContext('2d'), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
        g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.35, 'rgba(255,255,255,.45)'); g.addColorStop(1, 'rgba(255,255,255,0)');
        x.fillStyle = g; x.fillRect(0, 0, 64, 64);
        tex = new THREE.CanvasTexture(c); def.matp = Object.assign({}, def.matp, { luma: null });
      } else tex = loader.load(def.texUrl);
      tex.colorSpace = THREE.NoColorSpace; tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
      const e = new Emitter(def, tex, origin, { scale: opts.scale || .01, linear: opts.linear, density: opts.density });
      scene.add(e.mesh); this.list.push(e);
    }
  }
  update(dt) { for (const e of this.list) e.update(Math.min(dt, .05)); }
  dispose() { for (const e of this.list) { if (e instanceof MeshFx) { e.dispose(); continue; } this.scene.remove(e.mesh); e.g.dispose(); e.mat.dispose(); } this.list = []; }
}
