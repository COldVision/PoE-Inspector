// Passive skill tree planner: the game's layout (passiveskillgraph.psg), pan / zoom, class + ascendancy choice, point allocation with shortest paths, search, summary of the chosen stats.
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const LS = { get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* ignore */ } } };
const MAX_PASSIVES = 123, MAX_ASC = 8, MAX_WSET = 24;
const datas = {};
let builtKind = null;

// game data carries both languages: names / stat lines / flavour text and class names are swapped in place by the interface language
const langData = d => {
  const en = window.I18N && I18N.lang === 'en';
  d.nodes.forEach(n => { if (n.n0 === undefined) { n.n0 = n.n; n.t0 = n.t; n.fl0 = n.fl; } n.n = en ? (n.e || n.n0) : n.n0; n.t = en && n.te && n.te.length ? n.te : n.t0; n.fl = en && n.fle ? n.fle : n.fl0; });
  [...d.classes, ...d.asc].forEach(c => { if (c.ru0 === undefined) c.ru0 = c.ru; c.ru = en ? (c.en || c.ru0) : c.ru0; });
};
export async function openTree(host, api, kind = 'passives') {
  const ATLAS = kind === 'atlas', KEY = 'poe_inspector.tree.' + kind;
  if (!datas[kind]) { host.innerHTML = '<div class="tmsg">Загрузка дерева…</div>'; datas[kind] = await api('/api/tree?kind=' + kind); builtKind = null; }
  const data = datas[kind];
  langData(data);
  if (builtKind === kind) { host.querySelector('canvas').dispatchEvent(new Event('treeshow')); return; }
  builtKind = kind;
  const N = data.nodes, E = data.edges, C = data.classes, A = data.asc;
  host.innerHTML = `<style>
    #treev{position:relative;overflow:hidden;background:radial-gradient(#1b1630,#07060c)}#treev canvas{display:block;width:100%;height:100%;cursor:grab}#treev canvas.drag{cursor:grabbing}
    .tbar{position:absolute;left:12px;right:12px;top:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;pointer-events:none}.tbar>*{pointer-events:auto}
    .tpanel{background:rgba(10,8,18,.94);backdrop-filter:blur(6px);box-shadow:0 2px 12px #000a;border:1px solid #4a4160;border-radius:8px;padding:6px 12px;display:flex;gap:14px;align-items:center;font-size:15px;color:#cfd2e6}
    .tpanel b{font-size:20px;color:#fff}.tpanel .over b{color:#ff8a8a}.tpanel small{color:#9a96b5;text-transform:none}
    .tcls button,.tasc button,.tact button{background:rgba(26,22,47,.96);border:1px solid #4a4160;color:#cfd2e6;border-radius:6px;padding:5px 11px;font:inherit;font-size:14px;cursor:pointer}
    .tasc#tlay button.on{background:#c9a24a;color:#1a1408}.tcls button.on,.tasc button.on{background:#7a5af8;border-color:transparent;color:#fff}.tcls button:hover,.tasc button:hover,.tact button:hover{border-color:#9a8cff}
    .tcls,.tasc,.tact{display:flex;gap:6px;flex-wrap:wrap;background:rgba(10,8,18,.92);border:1px solid #4a4160;border-radius:8px;padding:5px 6px;box-shadow:0 2px 12px #000a;backdrop-filter:blur(6px)}.tcls:empty,.tasc:empty{display:none}.tsearch{background:#0f0c1a;border:1px solid #4a4160;color:#fff;border-radius:6px;padding:6px 10px;font:inherit;font-size:15px;width:230px}
    .ttip{position:absolute;z-index:6;width:340px;pointer-events:none;background:#09090c;border:1px solid #55524a;border-radius:4px;padding:10px 14px;font-family:'Palatino Linotype','Book Antiqua',Georgia,serif;color:#e6e6e6;box-shadow:0 10px 30px #000c;display:none}
    .ttip .tn{font-size:20px;color:#9fe3d3}.ttip .tt{color:#8fc9bd;text-decoration:underline;font-size:14px}.ttip .tl{margin-top:6px;color:#aab0ff;font-size:16px;line-height:1.45;text-align:center}.ttip .tl div+div{border-top:1px solid rgba(255,255,255,.08);margin-top:3px;padding-top:3px}.ttip .tf{margin-top:6px;font-style:italic;color:#e8832d;font-size:14.5px;text-align:center}.ttip .tr{margin-top:6px;color:#9a9a9a;font-style:italic;font-size:13.5px;text-align:center}.ttip .th{margin-top:6px;color:#7fb8ad;font-size:13px}
    .tsum{position:absolute;right:12px;top:64px;bottom:12px;width:330px;background:rgba(14,12,24,.93);border:1px solid #4a4160;border-radius:8px;padding:10px 14px;overflow:auto;color:#c2c2ff;font-family:'Palatino Linotype',Georgia,serif;font-size:15.5px;line-height:1.45;display:none}.tsum h4{margin:0 0 8px;color:#9fe3d3;font-weight:400;font-size:18px}.tsum div.l{padding:3px 0;border-bottom:1px solid rgba(255,255,255,.07)}
    .tzoom{position:absolute;left:12px;bottom:12px;display:flex;flex-direction:column;gap:6px}.tzoom button{width:38px;height:38px;border-radius:8px;border:1px solid #4a4160;background:rgba(14,12,24,.9);color:#fff;font-size:20px;cursor:pointer}.tmsg{padding:30px;color:#aaa}
    </style>
    <canvas></canvas>
    <div class="tbar">
      <div class="tpanel"><span>${ATLAS ? 'Очки Атласа' : 'Пассивные'} <b id="tcp">0</b>${ATLAS ? '' : ' / ' + MAX_PASSIVES}</span><span>Восхождение <b id="tca">0</b> / ${MAX_ASC}</span><span style="color:#ff8a8a">Набор I <b id="tcw1">0</b> / ${MAX_WSET}</span><span style="color:#7fe8a0">Набор II <b id="tcw2">0</b> / ${MAX_WSET}</span></div>
      <div class="tasc" id="tlay" role="group" aria-label="Куда ставить очки"><button class="on" data-l="0" title="Очки, общие для обоих наборов оружия">Общие</button><button data-l="1" title="Очки только для набора оружия I">Набор I</button><button data-l="2" title="Очки только для набора оружия II">Набор II</button></div><div class="tcls" id="tcls" role="group" aria-label="Класс"></div><div class="tasc" id="tasc" role="group" aria-label="Восхождение"></div>
      <style>${ATLAS ? '#tlay,#tasc,#tca,#tca~*,.tpanel span:nth-child(n+2){display:none!important}#tcls{display:none!important}' : ''}</style><input class="tsearch" id="tq" placeholder="Поиск пассивки или свойства…" aria-label="Поиск по дереву"><span class="tpanel" id="tqn" style="display:none"></span>
      <div class="tact"><button id="tsumb">Сводка</button><button id="texp">Экспорт</button><button id="timp">Импорт</button><button id="treset">Сбросить</button></div>
    </div>
    <div class="tzoom"><button id="tzi" aria-label="Приблизить">+</button><button id="tzo" aria-label="Отдалить">−</button><button id="tfit" aria-label="Вписать в окно" title="Вписать всё дерево">⤢</button></div>
    <div class="ttip" id="ttip"></div><div class="tsum" id="tsum"></div>`;
  const cv = host.querySelector('canvas'), g = cv.getContext('2d'), tip = host.querySelector('#ttip');
  // ---- geometry helpers
  const R = k => k === 'k' ? 76 : k === 'n' ? 50 : k === 'j' ? 48 : k === 'r' ? 62 : 29;   // node radius in tree units
  const adj = N.map(() => []); E.forEach(([a, b]) => { adj[a].push(b); adj[b].push(a); });
  const HID = N.map(n => !!n.h);   // unused ascendancies: present in the game graph, never shown
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  N.forEach(n => { if (n.h) return; minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x); minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y); });
  const CELL = 300, grid = new Map(); N.forEach((n, i) => { if (n.h) return; const k = Math.floor(n.x / CELL) + ',' + Math.floor(n.y / CELL); (grid.get(k) || grid.set(k, []).get(k)).push(i); });
  const nearest = (wx, wy, rad) => { let best = -1, bd = 1e18; const cx = Math.floor(wx / CELL), cy = Math.floor(wy / CELL), k = Math.ceil(rad / CELL);
    for (let x = cx - k; x <= cx + k; x++) for (let y = cy - k; y <= cy + k; y++) for (const i of grid.get(x + ',' + y) || []) { const n = N[i], d = (n.x - wx) ** 2 + (n.y - wy) ** 2, r = Math.max(R(n.k), rad * .4); if (d < r * r && d < bd) { bd = d; best = i; } }
    return best; };
  // ---- state
  let selClass = LS.get(KEY + '.class', C[0].i), selAsc = LS.get(KEY + '.asc', -1);
  const store = LS.get(KEY + '.alloc', {});   // per class: {asc, nodes[]}
  let alloc = new Set(), wsets = [new Set(), new Set()], layer = 0;   // shared points, weapon set I, weapon set II; `layer` = where a click puts points
  const loadClass = c => { const s_ = store[c] || {}; alloc = new Set(s_.nodes || []); wsets = [new Set(s_.w1 || []), new Set(s_.w2 || [])]; selAsc = s_.asc != null ? s_.asc : -1; };
  loadClass(selClass); if (store[selClass] && store[selClass].asc != null) selAsc = store[selClass].asc;
  const rootOf = c => (C.find(x => x.i === c) || {}).root;
  const startsNow = () => { if (ATLAS) return C.map(c => c.root).filter(r => r != null); const s = []; const r = rootOf(selClass); if (r != null) s.push(r); if (selAsc >= 0 && data.starts[selAsc] != null) s.push(data.starts[selAsc]); return s; };
  const domainOk = i => { const a = N[i].a; return a < 0 ? true : a === selAsc; };
  const isStart = i => startsNow().includes(i);
  const persist = () => { store[selClass] = { asc: selAsc, nodes: [...alloc], w1: [...wsets[0]], w2: [...wsets[1]] }; LS.set(KEY + '.alloc', store); LS.set(KEY + '.class', selClass); LS.set(KEY + '.asc', selAsc); };
  let view = { x: 0, y: 0, s: .03 }, W = 0, H = 0, hover = -1, matches = new Set(), dirty = true;
  const fit = (all = true) => { const pad = 40; view.s = Math.min((W - pad) / (maxX - minX), (H - pad) / (maxY - minY)); view.x = W / 2 - ((minX + maxX) / 2) * view.s; view.y = H / 2 - ((minY + maxY) / 2) * view.s; dirty = true; };
  const centerOn = (i, s) => { view.s = s || Math.max(view.s, .12); view.x = W / 2 - N[i].x * view.s; view.y = H / 2 - N[i].y * view.s; dirty = true; };
  const resize = () => { const r = host.getBoundingClientRect(); W = r.width; H = r.height; const d = window.devicePixelRatio || 1; cv.width = W * d; cv.height = H * d; g.setTransform(d, 0, 0, d, 0, 0); dirty = true; };
  // ---- allocation
  const reachOf = sets => { const has = x => sets.some(z => z.has(x)), seen = new Set(startsNow()), q = [...seen]; while (q.length) { const a = q.pop(); for (const b of adj[a]) if (!seen.has(b) && has(b)) { seen.add(b); q.push(b); } } return seen; };
  const prune = () => {   // drop what lost its way to the start; weapon-set points may also hang on shared ones
    const ok = reachOf([alloc]); for (const a of [...alloc]) if (!ok.has(a)) alloc.delete(a);
    wsets.forEach(w => { const o = reachOf([alloc, w]); for (const a of [...w]) if (!o.has(a) || alloc.has(a)) w.delete(a); });
  };
  const toggle = i => {
    if (!domainOk(i) || N[i].k === 'r' || isStart(i)) return;
    const W_ = layer > 0 ? wsets[layer - 1] : null;
    if (layer > 0 && N[i].a >= 0) return;   // weapon sets belong to the main tree
    if (alloc.has(i)) { if (layer > 0) return; alloc.delete(i); prune(); }
    else if (W_ && W_.has(i)) { W_.delete(i); prune(); }
    else {   // shortest path from what is already allocated (or the start nodes) inside the chosen tree
      const src = new Set([...startsNow(), ...alloc, ...(W_ || [])]), prev = new Map(), q = [...src]; src.forEach(s_ => prev.set(s_, null)); let found = false;
      for (let h = 0; h < q.length && !found; h++) { const a = q[h]; for (const b of adj[a]) { if (prev.has(b) || !domainOk(b) || (N[b].a >= 0 && N[a].a >= 0 && N[a].a !== N[b].a)) continue; if (N[b].k === 'r' && b !== i && !startsNow().includes(b)) continue; if (layer > 0 && N[b].a >= 0) continue; prev.set(b, a); if (b === i) { found = true; break; } q.push(b); } }
      if (!found) return;
      for (let c = i; c != null && !src.has(c); c = prev.get(c)) (W_ || alloc).add(c);
    }
    persist(); counts(); draw();
  };
  const counts = () => { const isRoot = i => C.some(c => c.root === i), main = [...alloc].filter(i => N[i].a < 0 && !isRoot(i)).length, asc = [...alloc].filter(i => N[i].a >= 0 && N[i].k !== 'r').length;
    host.querySelector('#tcp').textContent = main; host.querySelector('#tca').textContent = asc; host.querySelector('#tcw1').textContent = wsets[0].size; host.querySelector('#tcw2').textContent = wsets[1].size;
    host.querySelector('#tcp').parentElement.className = !ATLAS && main > MAX_PASSIVES ? 'over' : ''; host.querySelector('#tca').parentElement.className = asc > MAX_ASC ? 'over' : '';
    [['#tcw1', 0], ['#tcw2', 1]].forEach(([sel, k]) => { host.querySelector(sel).parentElement.className = wsets[k].size > MAX_WSET ? 'over' : ''; });
    if (host.querySelector('#tsum').style.display === 'block') summary(); };
  const aggregate = nodes => {
    const agg = new Map(), other = [];
    for (const i of nodes) for (const t of N[i].t || []) { const nums = t.match(/-?\d+(?:[.,]\d+)?/g) || []; if (nums.length === 1) { const k = t.replace(/-?\d+(?:[.,]\d+)?/, '#'); const a = agg.get(k) || { sum: 0, k }; a.sum += parseFloat(nums[0].replace(',', '.')); agg.set(k, a); } else other.push(t); }
    return [...agg.values()].map(a => a.k.replace('#', String(+a.sum.toFixed(2)))).concat(other).sort();
  };
  const summary = () => {
    const part = (title, nodes) => nodes.length ? `<h4>${title} · ${nodes.length}</h4>` + aggregate(nodes).map(l => `<div class="l">${esc(l)}</div>`).join('') : '';
    const html = part('Общие', [...alloc]) + part('Набор оружия I', [...wsets[0]]) + part('Набор оружия II', [...wsets[1]]);
    host.querySelector('#tsum').innerHTML = html || '<h4>Выбранные свойства</h4><div class="l" style="color:#8a86a5">Нажимайте узлы дерева, чтобы набрать очки.</div>';
  };
  // ---- drawing
  const icons = new Map(); let pend = 0;
  const icon = (p, sz = 64) => { if (!p) return null; const key = p + '@' + sz; let im = icons.get(key); if (im) return im.ok ? im : null; if (pend > 24) return null; im = new Image(); im.ok = false; pend++; im.onload = () => { im.ok = true; pend--; dirty = true; }; im.onerror = () => { pend--; }; im.src = '/api/icon?size=' + sz + '&path=' + encodeURIComponent(p); icons.set(key, im); return null; };
  const ORB = data.orbit_r;
  const cross = (a, b) => (N[a].a < 0) !== (N[b].a < 0);   // links between the main tree and an ascendancy cluster are not drawn
  const edgePath = pred => { const p = new Path2D(); E.forEach(([a, b]) => { if (cross(a, b) || !pred(a) || HID[a] || HID[b]) return; const A_ = N[a], B_ = N[b]; if (A_.g === B_.g && A_.o === B_.o && A_.o > 0 && data.centres[A_.g]) { const [cx, cy] = data.centres[A_.g], r = ORB[A_.o], a1 = Math.atan2(A_.y - cy, A_.x - cx), a2 = Math.atan2(B_.y - cy, B_.x - cx); let d = a2 - a1; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI; p.moveTo(A_.x, A_.y); p.arc(cx, cy, r, a1, a2, d < 0); } else { p.moveTo(A_.x, A_.y); p.lineTo(B_.x, B_.y); } }); return p; };
  const basePath = edgePath(a => N[a].a < 0), ascPath = edgePath(a => N[a].a >= 0);
  // background art: group discs, mastery glows, ascendancy illustrations
  const maIdx = []; N.forEach((n, i) => { if (n.ma != null) maIdx.push(i); });
  const ascBox = {}; N.forEach(n => { if (n.a >= 0) { const b = ascBox[n.a] || (ascBox[n.a] = [1e9, 1e9, -1e9, -1e9]); b[0] = Math.min(b[0], n.x); b[1] = Math.min(b[1], n.y); b[2] = Math.max(b[2], n.x); b[3] = Math.max(b[3], n.y); } });
  const DISC = [.46, .40, .36];   // share of the image width taken by the inner disc (small / medium / large)
  const drawBack = (vx0, vy0, vx1, vy1) => {
    const half = data.gbhalf !== false;
    for (const [x, y, k, R] of data.gb || []) {
      const d = Math.max(2 * (R + 60), 300) / DISC[k];
      if (x < vx0 - d || x > vx1 + d || y < vy0 - d || y > vy1 + d) continue;
      const im = icon(data.gbart[k], 512); if (!im) continue;
      if (k === 2 && half) { const h = d * im.naturalHeight / im.naturalWidth; g.drawImage(im, x - d / 2, y - h, d, h); g.save(); g.translate(x, y); g.rotate(Math.PI); g.drawImage(im, -d / 2, -h, d, h); g.restore(); }
      else g.drawImage(im, x - d / 2, y - d / 2, d, d);
    }
    const medal = (im, cx, cy, r, alpha) => {   // illustration cropped to a circle with a soft dark edge, no ornaments
      g.save(); g.beginPath(); g.arc(cx, cy, r, 0, 7); g.clip();
      const sc = 2 * r / Math.min(im.naturalWidth, im.naturalHeight), w = im.naturalWidth * sc, h = im.naturalHeight * sc;
      g.globalAlpha = alpha; g.drawImage(im, cx - w / 2, cy - h / 2, w, h);
      const gr = g.createRadialGradient(cx, cy, r * .72, cx, cy, r); gr.addColorStop(0, 'rgba(7,6,12,0)'); gr.addColorStop(1, 'rgba(7,6,12,.97)');
      g.globalAlpha = 1; g.fillStyle = gr; g.fillRect(cx - r, cy - r, 2 * r, 2 * r); g.restore();
    };
    const cls = C.find(c => c.i === selClass);
    if (!ATLAS && cls && cls.img) { const im = icon(cls.img, 1024); if (im) medal(im, 0, 0, 1500, .95); }
    for (const a of A) {   // round art on the ring around the tree; the position and size come from the layout table
      if (!a.img || !a.bg) continue;
      const r = a.bgs || 1500, cx = a.bg[0], cy = a.bg[1];
      if (cx < vx0 - r || cx > vx1 + r || cy < vy0 - r || cy > vy1 + r) continue;
      const im = icon(a.img, 1024); if (!im) continue;
      medal(im, cx, cy, r, a.i === selAsc ? 1 : .5);
    }
    g.globalCompositeOperation = 'lighter';
    for (const i of maIdx) {
      const n = N[i]; if (n.x < vx0 - 500 || n.x > vx1 + 500 || n.y < vy0 - 500 || n.y > vy1 + 500) continue;
      const im = icon(data.fx[n.ma], 512); if (!im) continue;
      g.globalAlpha = alloc.has(i) ? .9 : .45; g.drawImage(im, n.x - 450, n.y - 450, 900, 900);
    }
    g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
  };
  const draw = () => {
    dirty = false; g.clearRect(0, 0, W, H); g.save(); g.translate(view.x, view.y); g.scale(view.s, view.s);
    drawBack(-view.x / view.s, -view.y / view.s, (W - view.x) / view.s, (H - view.y) / view.s);
    const lw = Math.max(2, 1.6 / view.s); g.lineWidth = lw; g.strokeStyle = 'rgba(150,125,70,.45)'; g.stroke(basePath);
    g.lineWidth = Math.max(5, 3.4 / view.s); g.strokeStyle = 'rgba(5,4,3,.92)'; g.stroke(ascPath); g.lineWidth = lw;   // clear dark lines over the ascendancy art
    const base = new Set(startsNow()), okS = new Set([...alloc, ...base]);
    const layerEdges = (has, only, color, w) => { g.beginPath(); g.strokeStyle = color; g.lineWidth = lw * w;
      E.forEach(([a, b]) => { if (!has(a) || !has(b) || cross(a, b) || (only && !(only.has(a) || only.has(b)))) return; const A_ = N[a], B_ = N[b];
        if (A_.g === B_.g && A_.o === B_.o && A_.o > 0 && data.centres[A_.g]) { const [cx, cy] = data.centres[A_.g], r = ORB[A_.o], a1 = Math.atan2(A_.y - cy, A_.x - cx), a2 = Math.atan2(B_.y - cy, B_.x - cx); let d = a2 - a1; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI; g.moveTo(A_.x, A_.y); g.arc(cx, cy, r, a1, a2, d < 0); } else { g.moveTo(A_.x, A_.y); g.lineTo(B_.x, B_.y); } });
      g.stroke(); };
    layerEdges(x => okS.has(x), null, '#ffd36a', 2.4);
    layerEdges(x => okS.has(x) || wsets[0].has(x), wsets[0], '#ff6b6b', 2.4);
    layerEdges(x => okS.has(x) || wsets[1].has(x), wsets[1], '#5fe08a', 2.4);
    const x0 = -view.x / view.s, y0 = -view.y / view.s, x1 = (W - view.x) / view.s, y1 = (H - view.y) / view.s, pxMin = 4 / view.s, showLab = view.s > .2;   // icons from ~4 px node radius, names of notables / keystones from 20 % zoom
    for (let i = 0; i < N.length; i++) {
      const n = N[i]; if (n.h || n.x < x0 - 80 || n.x > x1 + 80 || n.y < y0 - 80 || n.y > y1 + 80) continue;
      const r = R(n.k), s1 = wsets[0].has(i), s2 = wsets[1].has(i), on = alloc.has(i) || startsNow().includes(i) || s1 || s2, dim = n.a >= 0 && n.a !== selAsc, isRoot = C.some(c => c.root === i);
      g.globalAlpha = dim ? .4 : 1;
      const fill = s1 ? '#e8575a' : s2 ? '#4fcf7c' : on ? '#ffcf5a' : n.k === 'r' ? '#d8b04a' : n.a >= 0 ? (n.k === 'n' ? '#55663a' : '#3f4e2e') : n.k === 'k' ? '#7a3a3a' : n.k === 'n' ? '#4a4372' : n.k === 'j' ? '#2d5a88' : '#3a3322';
      g.beginPath(); if (n.k === 'k' || n.k === 'r') { g.moveTo(n.x, n.y - r); g.lineTo(n.x + r, n.y); g.lineTo(n.x, n.y + r); g.lineTo(n.x - r, n.y); g.closePath(); } else g.arc(n.x, n.y, r, 0, 7);
      g.fillStyle = fill; g.fill(); g.lineWidth = n.a >= 0 ? Math.max(5, 3.6 / view.s) : Math.max(2, 2 / view.s); g.strokeStyle = on ? '#fff6d0' : n.a >= 0 ? '#c9a24a' : n.k === 'n' ? '#9a90d8' : n.k === 'k' ? '#e07a7a' : '#8a7a50'; g.stroke();
      if (r > pxMin && n.ic) { const im = icon(n.ic); if (im) { g.save(); g.beginPath(); g.arc(n.x, n.y, r * .88, 0, 7); g.clip(); g.drawImage(im, n.x - r, n.y - r, r * 2, r * 2); g.restore(); } }
      if (isRoot) { g.beginPath(); g.arc(n.x, n.y, 92, 0, 7); g.strokeStyle = '#fff'; g.stroke(); }
      if (matches.has(i)) { g.beginPath(); g.arc(n.x, n.y, r + 16, 0, 7); g.strokeStyle = '#38e8ff'; g.lineWidth = Math.max(5, 4 / view.s); g.stroke(); }
      if (i === hover) { g.beginPath(); g.arc(n.x, n.y, r + 10, 0, 7); g.strokeStyle = '#fff'; g.lineWidth = Math.max(3, 3 / view.s); g.stroke(); }
      if (showLab && (n.k === 'k' || n.k === 'n') && n.n) { g.fillStyle = '#e8e4ff'; g.font = Math.round(Math.max(30, 11 / view.s)) + 'px sans-serif'; g.textAlign = 'center'; g.fillText(n.n, n.x, n.y + r + Math.max(36, 13 / view.s)); }
    }
    g.globalAlpha = 1; g.restore();
    host.querySelector('#tzi').title = Math.round(view.s * 100) + '%';
  };
  window.__tree = { N, toggle, draw, get view() { return view; }, alloc: () => alloc, wsets: () => wsets, setLayer: l => { layer = l; } };
  const loop = () => { if (!host.isConnected) return; if (dirty && host.offsetParent !== null) draw(); requestAnimationFrame(loop); };
  // ---- pointer
  let dragging = false, moved = 0, lx = 0, ly = 0;
  const world = e => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left - view.x) / view.s, (e.clientY - r.top - view.y) / view.s]; };
  cv.onpointerdown = e => { dragging = true; moved = 0; lx = e.clientX; ly = e.clientY; cv.setPointerCapture(e.pointerId); cv.classList.add('drag'); };
  cv.onpointermove = e => {
    if (dragging) { const dx = e.clientX - lx, dy = e.clientY - ly; moved += Math.abs(dx) + Math.abs(dy); view.x += dx; view.y += dy; lx = e.clientX; ly = e.clientY; dirty = true; tip.style.display = 'none'; return; }
    const [wx, wy] = world(e), i = nearest(wx, wy, 26 / view.s);
    if (i !== hover) { hover = i; dirty = true; }
    if (i < 0) { tip.style.display = 'none'; return; }
    const n = N[i];
    if (!n.n && !(n.t || []).length) { tip.style.display = 'none'; return; }
    tip.innerHTML = `<div class="tn">${esc(n.n || 'Узел')}</div><div class="tt">${n.k === 'k' ? 'Ключевая' : n.k === 'n' ? 'Значимая' : n.k === 'j' ? 'Гнездо самоцвета' : n.k === 'r' ? 'Начало восхождения' : n.at ? 'Атрибут' : 'Пассивное умение'}${n.a >= 0 ? ' · ' + esc((A.find(a => a.i === n.a) || {}).ru || 'восхождение') : ''}</div>${(n.t || []).length ? `<div class="tl">${n.t.map(t => `<div>${esc(t)}</div>`).join('')}</div>` : ''}${(n.rm || []).length ? `<div class="tr">${n.rm.map(esc).join('<br>')}</div>` : ''}${n.fl ? `<div class="tf">${esc(n.fl)}</div>` : ''}<div class="th">${alloc.has(i) ? 'Нажмите, чтобы убрать' : domainOk(i) ? 'Нажмите, чтобы взять по кратчайшему пути' : 'Другое восхождение: выберите его сверху'}</div>`;
    tip.style.display = 'block'; const r = host.getBoundingClientRect(); let tx = e.clientX - r.left + 18, ty = e.clientY - r.top + 18; if (tx + 350 > W) tx = e.clientX - r.left - 358; if (ty + tip.offsetHeight > H) ty = Math.max(8, H - tip.offsetHeight - 8); tip.style.left = tx + 'px'; tip.style.top = ty + 'px';
  };
  cv.onpointerup = e => { const wasClick = moved < 5; dragging = false; cv.classList.remove('drag'); if (wasClick) { const [wx, wy] = world(e), i = nearest(wx, wy, 26 / view.s); if (i >= 0) toggle(i); } };
  cv.onpointerleave = () => { hover = -1; tip.style.display = 'none'; dirty = true; };
  cv.onwheel = e => { e.preventDefault(); const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top, k = Math.exp(-e.deltaY * .0015), ns = Math.max(.02, Math.min(1.5, view.s * k)); view.x = mx - (mx - view.x) * ns / view.s; view.y = my - (my - view.y) * ns / view.s; view.s = ns; dirty = true; };
  const zoom = k => { const ns = Math.max(.02, Math.min(1.5, view.s * k)); view.x = W / 2 - (W / 2 - view.x) * ns / view.s; view.y = H / 2 - (H / 2 - view.y) * ns / view.s; view.s = ns; dirty = true; };
  host.querySelector('#tzi').onclick = () => zoom(1.4); host.querySelector('#tzo').onclick = () => zoom(1 / 1.4); host.querySelector('#tfit').onclick = () => fit();
  // ---- class / ascendancy / search / summary
  const drawClasses = () => {
    host.querySelector('#tcls').innerHTML = C.map(c => `<button data-c="${c.i}" class="${c.i === selClass ? 'on' : ''}">${esc(c.ru)}</button>`).join('');
    host.querySelector('#tasc').innerHTML = A.filter(a => a.class === selClass).map(a => `<button data-a="${a.i}" class="${a.i === selAsc ? 'on' : ''}" title="Восхождение">${esc(a.ru)}</button>`).join('');
  };
  host.querySelector('#tcls').onclick = e => { const b = e.target.closest('button'); if (!b) return; persist(); selClass = +b.dataset.c; loadClass(selClass); persist(); drawClasses(); counts(); const r = rootOf(selClass); if (r != null) centerOn(r, .1); };
  host.querySelector('#tasc').onclick = e => { const b = e.target.closest('button'); if (!b) return; const a = +b.dataset.a; for (const i of [...alloc]) if (N[i].a >= 0) alloc.delete(i); selAsc = selAsc === a ? -1 : a; persist(); drawClasses(); counts(); if (selAsc >= 0 && data.starts[selAsc] != null) centerOn(data.starts[selAsc], .12); dirty = true; };
  host.querySelector('#treset').onclick = () => { alloc.clear(); wsets.forEach(w => w.clear()); persist(); counts(); dirty = true; };
  host.querySelector('#tlay').onclick = e => { const b = e.target.closest('button'); if (!b) return; layer = +b.dataset.l; host.querySelectorAll('#tlay button').forEach(x => x.classList.toggle('on', +x.dataset.l === layer)); };
  // build code: class, ascendancy and the three point sets; copy it or paste one
  host.querySelector('#texp').onclick = async () => { const code = btoa(unescape(encodeURIComponent(JSON.stringify({ v: 1, c: selClass, a: selAsc, s: [...alloc], w1: [...wsets[0]], w2: [...wsets[1]] })))); try { await navigator.clipboard.writeText(code); host.querySelector('#texp').textContent = 'Скопировано'; setTimeout(() => { host.querySelector('#texp').textContent = 'Экспорт'; }, 1600); } catch (e) { prompt('Код билда:', code); } };
  host.querySelector('#timp').onclick = () => { const code = prompt((window.I18N ? I18N.t('Вставьте код билда') : 'Вставьте код билда')); if (!code) return; try { const j = JSON.parse(decodeURIComponent(escape(atob(code.trim())))); if (!C.some(c => c.i === j.c)) throw new Error('класс'); persist(); selClass = j.c; const ok = x => Number.isInteger(x) && x >= 0 && x < N.length; store[selClass] = { asc: j.a ?? -1, nodes: (j.s || []).filter(ok), w1: (j.w1 || []).filter(ok), w2: (j.w2 || []).filter(ok) }; loadClass(selClass); persist(); drawClasses(); counts(); const r = rootOf(selClass); if (r != null) centerOn(r, .1); } catch (e) { alert((window.I18N ? I18N.t('Не удалось прочитать код билда') : 'Не удалось прочитать код билда')); } };
  host.querySelector('#tsumb').onclick = () => { const s = host.querySelector('#tsum'); s.style.display = s.style.display === 'block' ? 'none' : 'block'; if (s.style.display === 'block') summary(); };
  let qi = 0;
  host.querySelector('#tq').oninput = e => { const q = e.target.value.trim().toLowerCase(); matches = new Set(); if (q.length >= 2) N.forEach((n, i) => { if (!n.h && (n.n + ' ' + (n.e || '') + ' ' + (n.t || []).join(' ')).toLowerCase().includes(q)) matches.add(i); }); const c = host.querySelector('#tqn'); c.style.display = q.length >= 2 ? '' : 'none'; c.textContent = `Найдено: ${matches.size}`; qi = 0; if (matches.size) centerOn([...matches][0], .2); dirty = true; };
  host.querySelector('#tq').onkeydown = e => { if (e.key === 'Enter' && matches.size) { qi = (qi + 1) % matches.size; centerOn([...matches][qi], .25); } };
  cv.addEventListener('treeshow', () => { resize(); dirty = true; });
  new ResizeObserver(resize).observe(host);
  resize(); drawClasses(); counts(); const r0 = rootOf(selClass); fit(); if (alloc.size && r0 != null) centerOn(r0, .08); requestAnimationFrame(loop);
  const onLang = () => {
    if (!cv.isConnected) { window.removeEventListener('i18n:change', onLang); return; }
    langData(data); drawClasses(); counts(); if (host.querySelector('#tsum').style.display === 'block') summary();
    const q = host.querySelector('#tq'); if (q.value) q.oninput({ target: q }); tip.style.display = 'none'; dirty = true;
  };
  window.addEventListener('i18n:change', onLang);
}
