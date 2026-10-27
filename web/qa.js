// Visual QA helpers for equipment fitting (used from the browser console / automation, not by the UI).
const w = ms => new Promise(r => setTimeout(r, ms));
window.__tiles = [];
window.__qa = async (cls, slot, names, extra = {}) => {
  const E = window._E, V = window._V(); E.showMarker(false);
  const acts = await (await fetch('/api/actors?q=' + encodeURIComponent(cls))).json(); const a = acts.find(x => x.name === cls);
  for (const nm of names) {
    await E.loadActor(a);
    let msg = '';
    for (const [sl, nm2] of Object.entries(extra)) { const it = ((await (await fetch('/api/slotitems?slot=' + sl + '&q=' + encodeURIComponent(nm2))).json()).find(i => i.name === nm2)); if (it) await E.setSlot(sl, it); }
    if (nm) {
      const items = await (await fetch('/api/slotitems?slot=' + slot + '&q=' + encodeURIComponent(nm))).json(); const it = items.find(i => i.name === nm) || items[0];
      if (!it) msg = 'noitem'; else { try { await E.setSlot(slot, it); } catch (e) { msg = 'ERR ' + e.message; } }
    }
    await w(250); V.r.render(V.scene, V.cam);
    window.__tiles.push({ cls, nm, msg, url: V.r.domElement.toDataURL('image/jpeg', 0.85) });
  }
  return window.__tiles.length;
};
window.__show = async (from = 0, cols = 4, crop = [.2, .06, .6, .62]) => {
  const tiles = window.__tiles.slice(from); const imgs = await Promise.all(tiles.map(t => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = t.url; })));
  const iw = imgs[0].width, ih = imgs[0].height, sw = iw * crop[2], sh = ih * crop[3]; const tw = 400, th = Math.round(tw * sh / sw), rows = Math.ceil(imgs.length / cols);
  let c = document.getElementById('qa'); if (c) c.remove(); c = document.createElement('canvas'); c.id = 'qa'; c.width = tw * cols; c.height = (th + 18) * rows;
  c.style.cssText = 'position:fixed;left:0;top:0;z-index:9999;background:#000;width:100vw'; c.onclick = () => c.remove(); document.body.appendChild(c);
  const x = c.getContext('2d'); x.font = '14px sans-serif';
  imgs.forEach((im, i) => { const cx = (i % cols) * tw, cy = Math.floor(i / cols) * (th + 18); x.drawImage(im, iw * crop[0], ih * crop[1], sw, sh, cx, cy + 18, tw, th); x.fillStyle = '#fff'; x.fillText(tiles[i].cls + ' · ' + (tiles[i].nm || 'без брони') + ' ' + tiles[i].msg, cx + 4, cy + 13); });
  return [c.width, c.height];
};
window.__qaReady = true;
