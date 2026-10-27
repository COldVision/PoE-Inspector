// Pilot: ground-slam impact (heaving, cracked ground disc + dust) fired when a slam animation reaches its impact moment.
import * as THREE from 'three';

const VERT = `
uniform float uP; uniform float uR;
varying vec2 vXZ; varying float vH; varying float vRad;
float h21(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
void main(){
  float pop = 1. - pow(1. - min(uP / .12, 1.), 3.);
  vec2 xz = position.xz * pop; float rad = length(position.xz);
  float n = vn(xz * 1.6) * .65 + vn(xz * 4.1) * .35;
  float heave = sin(3.14159 * min(uP / .35, 1.)) * (1. - smoothstep(.35, 1., uP));
  float ring = smoothstep(1., .55, rad) * (.35 + .65 * smoothstep(0., .5, rad));
  float h = n * .2 * heave * ring;
  vXZ = xz; vH = h; vRad = rad;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(xz.x, h, xz.y, 1.);
}`;
const FRAG = `
uniform sampler2D map; uniform float uP; uniform float uR; uniform vec3 uTint;
varying vec2 vXZ; varying float vH; varying float vRad;
float h21(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
void main(){
  vec3 c = texture2D(map, vXZ * uR * .22).rgb;
  c *= uTint;
  float n = vn(vXZ * 1.6) * .65 + vn(vXZ * 4.1) * .35;
  float crack = smoothstep(.455, .5, abs(fract(n * 6.) - .5));
  c *= .7 + .6 * smoothstep(0., .2, vH);
  c = mix(c, vec3(.05, .035, .025), crack * .8);
  float a = (1. - smoothstep(.45, 1., uP)) * (1. - smoothstep(.62, 1., vRad));
  gl_FragColor = vec4(c, a);
}`;

const rnd = () => Math.random() * 2 - 1;

// the floor the character stands on: texture, normal map and tiling, so the impact can reuse exactly that ground
export function surfaceOf(V) {
  if (!V) return null;
  const f = V.gridFloor && V.gridFloor.visible && V.gridFloor.parent ? V.gridFloor : (V.floor && V.floor.visible && V.floor.parent ? V.floor : null);
  if (!f || !f.material || !f.material.map) return null;
  const par = f.geometry.parameters || {}, m = f.material.map;
  return { map: m, normalMap: f.material.normalMap || null, size: par.width || 60, repeat: m.repeat.x || 1, srgb: m.colorSpace === THREE.SRGBColorSpace };
}
function avgColour(map) {
  try {
    const img = map.image; if (!img || !(img.width || img.videoWidth)) return null;
    const c = document.createElement('canvas'); c.width = c.height = 8; const x = c.getContext('2d'); x.drawImage(img, 0, 0, 8, 8);
    const d = x.getImageData(0, 0, 8, 8).data; let r = 0, g = 0, b = 0; for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; }
    const n = d.length / 4; return [r / n / 255, g / n / 255, b / n / 255];
  } catch (e) { return null; }
}
const NOISE_GLSL = `
float h21(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
float nz(vec2 p){ return vn(p * 1.6) * .65 + vn(p * 4.1) * .35; }`;

export class GroundSlamFx {
  constructor(scene, texUrl, opt = {}) {
    this.opt = opt; this.scene = scene; this.t = -1; this.life = 2.2; this.R = opt.R || 3.2; this.root = new THREE.Group(); this.root.visible = false; scene.add(this.root);
    const tex = texUrl ? new THREE.TextureLoader().load(texUrl) : null;
    if (tex) { tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.colorSpace = THREE.NoColorSpace; tex.anisotropy = 8; }
    const g = new THREE.CircleGeometry(1, 96, 0, Math.PI * 2); g.rotateX(-Math.PI / 2);
    // polar subdivision so the heave has vertices to move
    const rings = 28, seg = 96, pos = [], idx = [];
    for (let r = 0; r <= rings; r++) for (let s = 0; s < seg; s++) { const a = s / seg * Math.PI * 2, rr = r / rings; pos.push(Math.cos(a) * rr, 0, Math.sin(a) * rr); }
    for (let r = 0; r < rings; r++) for (let s = 0; s < seg; s++) { const a = r * seg + s, b = r * seg + (s + 1) % seg, c = (r + 1) * seg + s, d = (r + 1) * seg + (s + 1) % seg; idx.push(a, c, b, b, c, d); }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.setIndex(idx); g.dispose();
    this.uni = { map: { value: tex }, uP: { value: 1 }, uR: { value: this.R }, uTint: { value: new THREE.Vector3(...(opt.tint || (/sand|dust|dirt/i.test(texUrl || '') ? [1.55, 1.2, .78] : [1, 1, 1]))) } };
    this.mat = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: this.uni, transparent: true, depthWrite: false, side: THREE.DoubleSide });
    this.disc = new THREE.Mesh(geo, this.mat); this.disc.frustumCulled = false; this.disc.renderOrder = 5; this.root.add(this.disc);
    // the same floor lifted: standard lighting + the floor's own texture / normal map, sampled by world position so it matches the ground under it
    this.uSurf = { uP: { value: 1 } };
    this.surfDisc = null; this.surfKey = null;
    // dust puffs
    const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d'), gr = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(214,182,128,.9)'); gr.addColorStop(.5, 'rgba(190,156,108,.45)'); gr.addColorStop(1, 'rgba(170,140,100,0)'); x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
    const st = new THREE.CanvasTexture(c); st.colorSpace = THREE.SRGBColorSpace;
    this.puffs = Array.from({ length: 56 }, () => { const m = new THREE.SpriteMaterial({ map: st, transparent: true, depthWrite: false, opacity: 0 }); const sp = new THREE.Sprite(m); sp.visible = false; this.root.add(sp); return { sp, v: new THREE.Vector3(), s0: 1, life: 1 }; });
  }
  setRadius(r) { this.R = r; }
  _surfaceDisc(sf) {
    if (this.surfKey === sf.map) return;
    if (this.surfDisc) { this.root.remove(this.surfDisc); this.surfDisc.material.dispose(); }
    const mat = new THREE.MeshStandardMaterial({ map: sf.map, normalMap: sf.normalMap, normalScale: new THREE.Vector2(1.2, 1.2), roughness: .95, metalness: 0, transparent: true, depthWrite: false });
    const U = this.uSurf, size = sf.size.toFixed(2), rep = sf.repeat.toFixed(2);
    mat.onBeforeCompile = sh => {
      sh.uniforms.uP = U.uP;
      sh.vertexShader = `uniform float uP; varying float vRad; varying vec2 vUnit;
` + NOISE_GLSL + `
      float hgt(vec2 p){ float rad = length(p); float heave = sin(3.14159 * min(uP / .35, 1.)) * (1. - smoothstep(.35, 1., uP));
        float ring = smoothstep(1., .55, rad) * (.35 + .65 * smoothstep(0., .5, rad)); return nz(p) * .2 * heave * ring; }
` + sh.vertexShader
        .replace('#include <beginnormal_vertex>', `#include <beginnormal_vertex>
          { vec2 q = position.xz; float e = .02; float gx = (hgt(q + vec2(e, 0.)) - hgt(q - vec2(e, 0.))) / (2. * e), gz = (hgt(q + vec2(0., e)) - hgt(q - vec2(0., e))) / (2. * e);
            objectNormal = normalize(vec3(-gx, 1., -gz)); }`)
        .replace('#include <begin_vertex>', `#include <begin_vertex>
          { float pop = 1. - pow(1. - min(uP / .12, 1.), 3.); vUnit = position.xz; vRad = length(position.xz);
            transformed.xz *= pop; transformed.y += hgt(position.xz * pop);
            vec4 wp = modelMatrix * vec4(transformed, 1.); vec2 uvw = vec2(wp.x / ${size} + .5, -wp.z / ${size} + .5) * ${rep};
            #ifdef USE_MAP
              vMapUv = uvw;
            #endif
            #ifdef USE_NORMALMAP
              vNormalMapUv = uvw;
            #endif
          }`);
      sh.fragmentShader = `uniform float uP; varying float vRad; varying vec2 vUnit;
` + NOISE_GLSL + `
` + sh.fragmentShader.replace('#include <map_fragment>', `#include <map_fragment>
          { float n = nz(vUnit); float crack = smoothstep(.455, .5, abs(fract(n * 6.) - .5));
            diffuseColor.rgb *= mix(1., .35, crack * .8);
            diffuseColor.a *= (1. - smoothstep(.45, 1., uP)) * (1. - smoothstep(.62, 1., vRad)); }`);
    };
    const m = new THREE.Mesh(this.disc.geometry, mat); m.frustumCulled = false; m.renderOrder = 5; m.receiveShadow = true; this.root.add(m);
    this.surfDisc = m; this.surfKey = sf.map;
  }
  useSurface(sf) {
    this.surf = sf || null;
    if (sf) { this._surfaceDisc(sf); this.avg = avgColour(sf.map) || this.avg; }
    if (this.surfDisc) this.surfDisc.visible = !!sf;
    this.disc.visible = !sf;
    // spikes and dust follow the ground: its colour and relief
    if (this.spikeMat) {
      if (sf) {
        if (!this.spikeMap || this.spikeSrc !== sf.map) { this.spikeMap = sf.map.clone(); this.spikeMap.repeat.set(1.5, 1.5); this.spikeMap.needsUpdate = true; this.spikeSrc = sf.map; }
        this.spikeMat.map = this.spikeMap; this.spikeMat.color.setRGB(1.1, 1.05, 1); this.spikeMat.needsUpdate = true;
      }
    }
    const dc = sf && this.avg ? this.avg.map(v => Math.min(1, .55 + v * .75)) : [1, 1, 1];
    for (const p of this.puffs) p.sp.material.color.setRGB(dc[0], dc[1], dc[2]);
  }
  // rock spikes erupting one after another along a direction (Sunder-style cascade)
  initSpikes(texUrl, count = 16) {
    const tex = texUrl ? new THREE.TextureLoader().load(texUrl) : null;
    if (tex) { tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.colorSpace = THREE.SRGBColorSpace; }
    const mk = seed => {
      const g = new THREE.ConeGeometry(.2, 1.0, 7, 4, true); g.translate(0, .5, 0);
      const p = g.attributes.position; let k = seed;
      const r = () => { k = (k * 9301 + 49297) % 233280; return k / 233280 - .5; };
      for (let i = 0; i < p.count; i++) { const y = p.getY(i), f = Math.min(1, y / 1.0); p.setX(i, p.getX(i) * (1 + r() * .5) + r() * .07 * f); p.setZ(i, p.getZ(i) * (1 + r() * .5) + r() * .07 * f); p.setY(i, y + r() * .08); }
      g.computeVertexNormals(); return g;
    };
    const geos = [mk(7), mk(31), mk(77)];
    const mat = new THREE.MeshStandardMaterial({ map: tex, color: 0xb59c86, roughness: .95, metalness: 0, flatShading: true, side: THREE.DoubleSide });
    this.spikes = Array.from({ length: count }, (_, i) => { const m = new THREE.Mesh(geos[i % 3], mat); m.visible = false; m.castShadow = true; this.root.add(m); return { m, d: 0, s: 1 }; });
    this.spikeMat = mat; this.spikeGeos = geos;
  }
  trigger(pos, dir) {
    this.root.position.set(pos.x, 0.02, pos.z); this.root.visible = true; this.t = 0;
    this.disc.scale.setScalar(this.R); this.uni.uR.value = this.R; if (this.surfDisc) this.surfDisc.scale.setScalar(this.R);
    for (const p of this.puffs) {
      const a = Math.random() * Math.PI * 2, rr = this.R * (.25 + Math.random() * .6);
      p.sp.position.set(Math.cos(a) * rr * .5, .1, Math.sin(a) * rr * .5);
      p.v.set(Math.cos(a) * (1.2 + Math.random() * 2.2), .5 + Math.random() * 1.1, Math.sin(a) * (1.2 + Math.random() * 2.2));
      p.s0 = .7 + Math.random() * .8; p.life = .9 + Math.random() * 1.1; p.sp.visible = true; p.sp.material.opacity = 0;
    }
    if (this.spikes && dir) {
      const d = new THREE.Vector3(dir.x, 0, dir.z).normalize(), side = new THREE.Vector3(-d.z, 0, d.x), n = this.spikes.length;
      this.spikes.forEach((sp, i) => {
        const along = .4 + (i >> 1) * .62 + Math.random() * .2, lat = (i % 2 ? 1 : -1) * (.35 + Math.random() * .35 + (i >> 1) * .035);
        sp.m.position.set(d.x * along + side.x * lat, 0, d.z * along + side.z * lat);
        sp.d = (i >> 1) * .05; sp.s = .8 + Math.random() * .9 + (i >> 1) * .04; sp.m.rotation.set(rnd() * .25 - d.z * .35, Math.random() * 6.28, rnd() * .25 + d.x * .35); sp.m.visible = false; sp.m.scale.set(sp.s, 0.001, sp.s);
      });
    }
  }
  update(dt) {
    if (this.t < 0) return;
    this.t += dt; const u = this.t / this.life;
    if (u >= 1) { this.t = -1; this.root.visible = false; return; }
    this.uni.uP.value = u; this.uSurf.uP.value = u;
    for (const sp of this.spikes || []) {
      const k = this.t - sp.d; if (k < 0) continue; if (k > 1.1) { sp.m.visible = false; continue; }
      sp.m.visible = true; const up = k < .14 ? 1 - Math.pow(1 - k / .14, 3) : k < .6 ? 1 : 1 - Math.pow((k - .6) / .5, 2);
      sp.m.scale.set(sp.s, Math.max(.001, up * sp.s * 1.15), sp.s);
    }
    for (const p of this.puffs) {
      const k = this.t / p.life; if (k >= 1) { p.sp.visible = false; continue; }
      p.sp.position.addScaledVector(p.v, dt); p.v.multiplyScalar(1 - 1.4 * dt); p.v.y -= .3 * dt;
      const s = p.s0 * (1 + k * 2.6); p.sp.scale.set(s, s, 1); p.sp.material.opacity = .55 * Math.min(1, k / .08) * (1 - k);
    }
  }
  dispose() { (this.spikeGeos || []).forEach(g => g.dispose()); if (this.spikeMat) this.spikeMat.dispose(); this.scene.remove(this.root); if (this.surfDisc) this.surfDisc.material.dispose(); if (this.spikeMap) this.spikeMap.dispose(); this.disc.geometry.dispose(); this.mat.dispose(); this.puffs.forEach(p => p.sp.material.dispose()); }
}
