import * as THREE from 'three';
// Monsters tab: animated model (+ weapon) in a chosen scene and everything related (stats, skills, animations, sounds, files).
import { GroundSlamFx, surfaceOf } from '/static/groundfx.js';
import { Editor } from '/static/editor.js';
import { getEd, studioStage, gameStage, gridStage, clearGrid, exportHtml, bindExport } from '/static/editor_ui.js';

const clean = s => String(s || '').replace(/\[([^\]|]+)\|([^\]]+)\]/g, '$2').replace(/\[([^\]]+)\]/g, '$1');
const STAT = { MovementSpeed: 'Скорость движения', ObjectSize: 'Размер объекта', ModelSizeMultiplier: 'Масштаб модели, %', MinimumAttackDistance: 'Мин. дистанция атаки', MaximumAttackDistance: 'Макс. дистанция атаки',
  ExperienceMultiplier: 'Опыт, %', DamageMultiplier: 'Урон, %', LifeMultiplier: 'Здоровье, %', AttackSpeed: 'Скорость атаки, мс', MinAgroRange: 'Мин. дальность агро', MaxAgroRange: 'Макс. дальность агро', PoiseThreshold: 'Порог стойкости', AttackCrit: 'Шанс крита' };
const SECTIONS = [['ov', 'Обзор'], ['sk', 'Умения'], ['an', 'Анимации'], ['au', 'Озвучка'], ['fl', 'Файлы']];
const SCENES = [['studio', 'Студия'], ['game', 'Игровой вид'], ['grid', 'Земля, вид сверху']];
let token = 0, scene = 'studio';
let monEd = null;     // the Monsters tab owns its own Editor: the Editor and Skills tabs keep theirs, so monster models never leak into them
function monsterEd(ctx) {
  if (!monEd) monEd = new Editor({ api: ctx.api, esc: ctx.esc, $: ctx.$, getViewer: () => ctx.viewer(), ensureViewer: () => ctx.ensureViewer() });
  return monEd;
}
export function leaveMonsters(ctx) {
  token++; dropSlam(ctx);
  if (monEd && monEd.root) monEd.clear();
  const V = ctx.viewer(); if (V && monEd && V.editor === monEd) V.editor = null;
}
let slamRun = null;   // pilot: ground-slam impact effect bound to the playing clip
function dropSlam(ctx) { if (!slamRun) return; const V = ctx.viewer(); if (V) V.pets = (V.pets || []).filter(x => x !== slamRun); slamRun.dispose(); slamRun = null; }
const audio = typeof Audio !== 'undefined' ? (window.__audio = new Audio()) : null;   // one shared player: starting a sound stops the previous one

// attachment bone names in .ao files omit the `_jntBnd` suffix or differ in case
function boneOf(E, name) {
  const lc = name.toLowerCase();
  return E.byName.get(name) || E.byName.get(name + '_jntBnd') || E.bones.find(b => b.name.toLowerCase() === lc || b.name.toLowerCase() === lc + '_jntbnd')
    || E.bones.find(b => b.name.toLowerCase() === 'aux_' + lc + '_attachment') || E.bones.find(b => b.name.toLowerCase() === 'aux_' + lc + '_attachment_02') || null;   // socket names like L_Weapon live on the rig as aux_L_Weapon_attachment
}

// socket bone for a held item: right hand for the first weapon, left for the second
function socket(E, slot) {
  const names = E.bones.map(b => b.name);
  const pick = rx => names.find(n => rx.test(n));
  const bone = slot === 'Weapon1' ? pick(/R.*weapon.*attach/i) || pick(/weapon.*R/i) || pick(/R_?(hand|wrist)/i)
    : slot === 'Weapon2' ? pick(/L.*weapon.*attach/i) || pick(/weapon.*L/i) || pick(/L_?(hand|wrist)/i)
    : slot === 'Helmet' ? pick(/^head/i) : pick(/chest|spine/i);
  return bone ? E.byName.get(bone) : null;
}

window.addEventListener('i18n:change', () => { if (window.__monRerender) window.__monRerender(); });

export async function showMonster(ctx, m) {
  const { api, esc, $ } = ctx, my = ++token; dropSlam(ctx);
  const info = $('#info'); info.style.maxHeight = '56%'; info.innerHTML = '<div class="msg">Загрузка монстра…</div>';
  let d;
  try { d = await api('/api/monster?row=' + m.row); } catch (e) { info.innerHTML = `<div class="msg">Ошибка: ${esc(e.message)}</div>`; return; }
  if (my !== token) return;
  const E = monsterEd(ctx), skin = (d.skins || [])[0], rig = d.skeleton && d.skeleton.toLowerCase();
  let animated = false, curClip = null; const attached = {};

  // ground slam: fire the effect when the playing clip reaches its impact moment (strongest ScreenShake / contact event of the data)
  function setupSlam() {
    dropSlam(ctx);
    const imp = (d.impacts && d.impacts.clips) || {}; if (!Object.keys(imp).length) return;
    const V = ctx.viewer(); if (!V) return;
    const fx = new GroundSlamFx(V.scene, d.impacts.tex ? '/api/icon?size=1024&path=' + encodeURIComponent(d.impacts.tex) : null);
    const rx = /claw|tail_\d+|tail_end|tip|R_hand|L_hand|weapon/i, v = new THREE.Vector3();
    const spot = () => {
      let best = null, by = 1e9; E.root.updateWorldMatrix(true, true);
      for (const b of E.bones) { if (!rx.test(b.name)) continue; b.getWorldPosition(v); if (v.y < by) { by = v.y; best = v.clone(); } }
      if (!best) { E.root.getWorldPosition(v); best = v.clone(); }
      return best;
    };
    let prev = 0;
    slamRun = {
      update(dt) {
        fx.update(dt);
        const cur = E.curClip && E.curClip[1], i = cur && imp[cur];
        if (!i || !E.action) { prev = 0; return; }
        const t = E.action.time;
        if (t < prev) prev = 0;
        if (prev < i.t && t >= i.t) { fx.useSurface(surfaceOf(V)); fx.trigger(spot()); }
        prev = t;
      },
      dispose() { fx.dispose(); },
    };
    V.pets = V.pets || []; V.pets.push(slamRun);
  }

  async function loadModel() {
    const sh = getEd(ctx); if (sh.root) sh.clear();   // drop the character of the Editor / Skills tabs from the shared viewer
    ctx.ensureViewer(); E.showMarker(false); clearGrid(ctx);
    (scene === 'game' ? gameStage : scene === 'grid' ? gridStage : studioStage)(ctx); E.ctx.keepCamera = false;
    E.envScale = sh.envScale; ctx.viewer().editor = E;   // the stage helpers wire the shared Editor; the viewer must drive this one
    animated = false;
    if (rig && skin) {
      try {
        await E.loadActor({ id: 'monster:' + d.id, kind: 'npc', name: d.name, skeleton: rig, skin: skin.toLowerCase() });
        animated = !!E.root;
        const parts = [];   // everything mounted below is also recorded in the actor, so a reload (Skills tab, scene switch) puts it back
        if (animated) {
          for (const w of d.weapons) {
            const bone = socket(E, w.slot); attached[w.id] = false;
            if (!bone) continue;
            if (w.fixed) {
              try { const g = await E.loader.loadAsync('/api/model?raw=1&path=' + encodeURIComponent(w.fixed.toLowerCase())); g.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.material.side = 2; } }); bone.add(g.scene); attached[w.id] = true; parts.push({ tag: 'weapon', skins: [], hide: [], fixed: [{ path: w.fixed.toLowerCase(), bone: bone.name }], nodes: [g.scene] }); } catch (e) { /* model missing */ }
              continue;
            }
            for (const sm of w.skins) { try { const n = await E.addSkin(sm.toLowerCase(), 'weapon', { static: true, parent: bone }); if (n.length) { attached[w.id] = true; parts.push({ tag: 'weapon', skins: [{ sm: sm.toLowerCase(), static: true, bone: bone.name }], hide: [], nodes: n }); } } catch (e) { /* attachment without mesh */ } }
          }
          // extra skins of the .ao, then hair / clothes / armour attachments (skinned to the monster rig when they share it, mounted on a bone otherwise)
          for (const sm of (d.skins || []).slice(1)) { try { const n = await E.addSkin(sm.toLowerCase(), 'base'); parts.push({ tag: 'skin2', skins: [{ sm: sm.toLowerCase(), static: false, bone: null }], hide: [], nodes: n }); } catch (e) { /* skin without mesh */ } }
          d.attachCount = 0;
          const heldAo = new Set(d.weapons.filter(w => attached[w.id]).map(w => (w.ao || '').toLowerCase()));
          for (const a of d.attachments || []) {
            if (heldAo.has(a.ao.toLowerCase())) { d.attachCount++; continue; }   // the same item was already mounted as the weapon
            const bone = a.root ? null : boneOf(E, a.bone);
            if (a.fixed && bone) {
              try { const g = await E.loader.loadAsync('/api/model?raw=1&path=' + encodeURIComponent(a.fixed.toLowerCase())); g.scene.traverse(o => { if (o.isMesh) { o.castShadow = true; o.material.side = 2; } }); bone.add(g.scene); d.attachCount++; parts.push({ tag: 'att', skins: [], hide: [], fixed: [{ path: a.fixed.toLowerCase(), bone: bone.name }], nodes: [g.scene] }); } catch (e) { /* fixed mesh missing */ }
            }
            const sameRig = !a.skeleton || a.skeleton.toLowerCase() === rig;
            for (const sm of a.skins) {
              try {
                let n = [], it = null;
                if (a.root && sameRig) { n = await E.addSkin(sm.toLowerCase(), 'att'); it = { sm: sm.toLowerCase(), static: false, bone: null }; }
                else if (bone) { n = await E.addSkin(sm.toLowerCase(), 'att', { static: true, parent: bone }); it = { sm: sm.toLowerCase(), static: true, bone: bone.name }; }
                else if (sameRig) { n = await E.addSkin(sm.toLowerCase(), 'att'); it = { sm: sm.toLowerCase(), static: false, bone: null }; }
                if (it && n.length) parts.push({ tag: 'att', skins: [it], hide: [], nodes: n });
                d.attachCount += n.length ? 1 : 0;
              } catch (e) { /* attachment without a loadable mesh */ }
            }
          }
          if ((d.hide || []).length) { const hs = new Set(d.hide); E.root.traverse(o => { if (o.userData.tag === 'base' && hs.has(o.name)) o.visible = false; }); parts.push({ tag: 'monster-hide', skins: [], hide: [...hs], nodes: [] }); }
          E.actor.parts = parts; E.parts = parts;
          const idle = (d.states.find(s => /^idle/i.test(s.state)) || {}).clips;
          curClip = curClip || (idle && idle.find(c => d.clips.includes(c))) || d.clips.find(c => /idle/.test(c)) || d.clips[0];
          if (curClip) await E.play(rig, curClip);
          E.fit();
          setupSlam();
        }
      } catch (e) { animated = false; }
    }
    if (!animated && m.model) ctx.showModel(m.model, d.name, null, true);
  }
  await loadModel();
  if (my !== token) return;

  let sec = 'ov';
  const evUrl = (path, dl) => `/api/sfx?event=${encodeURIComponent(path)}&banks=${encodeURIComponent((d.sfx.banks || []).join('|'))}${dl ? '&dl=1' : ''}`;
  const tabs = () => `<div class="mtabs" role="tablist">${SECTIONS.map(([k, n]) => `<button role="tab" aria-selected="${k === sec}" data-s="${k}" class="${k === sec ? 'on' : ''}">${n}${k === 'sk' ? ` <i>${d.skills.length}</i>` : k === 'an' ? ` <i>${d.clips.length}</i>` : k === 'au' ? ` <i>${d.sfx.events.length + ((d.audio.aggro || {}).oggs || []).length}</i>` : ''}</button>`).join('')}
    <label class="mscene">Сцена <select id="mscene" aria-label="Сцена">${SCENES.map(([k, n]) => `<option value="${k}"${k === scene ? ' selected' : ''}>${n}</option>`).join('')}</select></label></div>`;
  const chips = a => (a || []).map(x => `<span class="chip">${esc(x)}</span>`).join('');
  const short = p => p.replace(/^event:\/Sound Effects\//, '').replace(/^Audio\/Sound Effects\//, '');
  const snd = (path, ms) => `<div class="sfx"><button class="play" data-ev="${esc(path)}" aria-label="Воспроизвести">▶</button><div class="nm"><div>${esc(path.split('/').slice(-2).join(' / '))}</div><div class="f">${esc(short(path))}${ms ? ' · ' + (ms / 1000).toFixed(1) + ' с' : ''}</div></div><a class="dl" href="${evUrl(path, true)}" download aria-label="Сохранить WAV" title="Сохранить WAV">⬇</a></div>`;
  let curSk = -1;
  const DMG = [['Physical', 'Физический'], ['Fire', 'Огонь'], ['Cold', 'Холод'], ['Lightning', 'Молния'], ['Chaos', 'Хаос']];
  const dmgTypes = s => {
    const i = s.info || {}, txt = (i.lines || []).join(' '), out = DMG.filter(([en]) => new RegExp('⟦' + en, 'i').test(txt) || (i.dtypes || []).some(t => t.toLowerCase() === en.toLowerCase())).map(([en, ru]) => I18N.pick(ru, en));
    if (!out.length && (i.types || []).includes('Attack')) out.push(I18N.pick('Физический (атака)', 'Physical (attack)'));
    return out;
  };
  const skDetail = s => {
    const i = s.info || {}, num = (l, v) => v == null || v === '' ? '' : `<tr><td>${l}</td><td>${esc(v)}</td></tr>`, sec = v => String(v / 1000).replace('.', ',') + ' с';
    const rows = num('Тип урона', dmgTypes(s).join(', ')) + num('Шанс крита', i.crit ? (i.crit / 100).toFixed(2).replace('.', ',') + '%' : i.crit === 0 ? '—' : '') + num('Множитель урона', i.mult ? (i.mult / 100) + '%' : '') +
      num('Урон за срабатывание', i.dmg) + num('Время применения', s.cast_time ? sec(s.cast_time) : '') + num('Перезарядка', i.cooldown ? sec(i.cooldown) : '') + num('Заряды', i.uses || '') +
      num('Скорость атаки, %', i.atk_speed || '') + num('Типы умения', (i.types || []).join(', '));
    const lines = I18N.pick(i.lines_ru, i.lines) || i.lines || [], cl = x => clean(x).replace(/[⟦⟧]/g, '');
    const const_ = Object.entries(i.const || {}).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');
    return `<div class="skdet"><table class="mt">${rows}</table>
      ${lines.length ? `<div class="kv">${lines.map(l => esc(cl(l))).join('<br>')}</div>` : ''}
      <h4>Анимация (${s.clips.length})</h4>${s.clips.length ? s.clips.map(c => `<div class="row skclip${c === curClip ? ' on' : ''}" data-c="${esc(c)}"><div>${esc(c)}</div><span>${(d.events[c] && d.events[c].contact.length) ? 'контакт: ' + d.events[c].contact.join(', ') + ' с' : ''}</span></div>`).join('') : '<div class="kv">Для этого умения в данных нет клипа</div>'}
      <h4>Звуки (${s.sounds.length})</h4>${s.sounds.length ? s.sounds.map(x => `<div class="evl">${x.sfx ? `<button class="play sm" data-ev="${esc(x.sfx)}" aria-label="Воспроизвести">▶</button>` : '<span class="nop"></span>'}<span class="f">${esc(x.clip)} · ${x.t.toFixed(2)} с · ${esc(short(x.event))}</span></div>`).join('') : '<div class="kv">Звуков на этой анимации нет</div>'}</div>`;
  };
  const body = {
    ov: () => `<div class="mcard"><b>Экспорт</b>${exportHtml()}</div><div class="skill-head"><div><div class="name">${esc(I18N.pick(d.name_ru, d.name))}</div><div class="sub">${esc(d.name)} · ${esc(d.id)}</div></div></div>${(() => { const st = d.stats || {}, x = k => st[k] ? String(+(st[k] / 100).toFixed(2)).replace('.', ',') : '', T = (l, v, key) => v ? `<div class="tile${key ? ' key' : ''}"><small>${l}</small><b>${v}</b></div>` : ''; const h = T('Жизнь', x('LifeMultiplier') && '×' + x('LifeMultiplier'), true) + T('Урон', x('DamageMultiplier') && '×' + x('DamageMultiplier')) + T('Скорость', st.MovementSpeed) + T('Опыт', x('ExperienceMultiplier') && '×' + x('ExperienceMultiplier')) + T('Размер', st.ObjectSize) + T('Дистанция атаки', st.MaximumAttackDistance); return h ? `<div class="tiles">${h}</div>` : ''; })()}
      <div class="kv">${[d.type && 'Тип: ' + d.type, d.category && 'Категория: ' + d.category, d.boss && 'Босс'].filter(Boolean).map(esc).join(' · ')}</div>
      ${(m.tags || []).length ? `<div>${chips(m.tags)}</div>` : ''}
      <h4>Оружие и снаряжение</h4>${d.weapons.length || d.main_hand || d.off_hand ? `<div class="kv">${[d.main_hand && 'Основная рука: ' + d.main_hand, d.off_hand && 'Вторая рука: ' + d.off_hand].filter(Boolean).map(esc).join(' · ')}</div>
        ${d.weapons.map(w => `<div class="mcard"><div class="skill-head">${w.icon ? `<img width="36" height="36" src="/api/icon?size=96&path=${encodeURIComponent(w.icon)}" style="object-fit:contain" onerror="this.style.visibility='hidden'">` : ''}<div><b>${esc(w.label)}</b> · ${esc(w.id)}<div class="f">${esc(w.ao || '')}</div><div class="kv">${attached[w.id] ? 'показано на модели' : (w.skins.length || w.fixed) ? 'не удалось прикрепить к скелету' : 'без отдельной модели'}</div></div></div></div>`).join('')}` : '<div class="kv">Своего оружия в данных нет</div>'}
      ${(d.attachments || []).length ? `<h4>Одежда, волосы, броня (${d.attachments.length})</h4><div class="kv">показано на модели: ${d.attachCount || 0}</div>${d.attachments.map(a => `<div class="file">${esc(a.ao.split('/').pop())} · ${esc(a.root ? 'на теле' : a.bone)}</div>`).join('')}` : ''}
      <h4>Параметры</h4><table class="mt">${Object.entries(d.stats).map(([k, v]) => `<tr><td>${esc(STAT[k] || k)}</td><td>${esc(typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(2) : v)}</td></tr>`).join('')}</table>
      ${d.tags.length ? `<h4>Теги</h4><div>${chips(d.tags)}</div>` : ''}${d.mods.length ? `<h4>Свойства</h4><div>${chips(d.mods)}</div>` : ''}`,
    sk: () => d.skills.map((s, si) => `<div class="mcard sk${si === curSk ? ' on' : ''}" data-sk="${si}" style="cursor:pointer"><div class="skill-head">${s.icon ? `<img width="40" height="40" src="/api/icon?size=96&path=${encodeURIComponent(s.icon)}" style="object-fit:contain" onerror="this.style.visibility='hidden'">` : ''}<div><b>${esc(I18N.pick(s.ru, s.name) || s.effect)}</b>${s.taunt ? ' <span class="chip">провокация</span>' : ''}<div class="sub">${esc(s.name || '')} <span class="f">${esc(s.effect)}</span></div></div></div>
      ${s.desc_ru || s.desc ? `<div class="lead">${esc(clean(I18N.pick(s.desc_ru, s.desc)))}</div>` : '<div class="kv">Служебный эффект без описания</div>'}
      <div class="kv">${s.cast_time ? 'Время применения: ' + s.cast_time / 1000 + ' с' : ''}${(s.animation || []).length ? ' · анимация: ' + esc(s.animation.join(' → ')) : ''}</div>${si === curSk ? skDetail(s) : ''}</div>`).join('') || '<div class="msg">У монстра нет собственных умений в данных</div>',
    an: () => `${d.states.length ? `<h4>Состояния → клипы</h4><div class="edlist" id="mstates" style="max-height:none">${d.states.map(s => `<div class="row" data-c="${esc(s.clips[0] || '')}"><div>${esc(s.state)}</div><span>${esc(s.clips.join(', '))}</span></div>`).join('')}</div>` : ''}
      <h4>Все клипы скелета</h4><div class="edlist" id="mclips" style="max-height:none">${d.clips.map(c => { const ev = d.events[c]; return `<div class="row${c === curClip ? ' on' : ''}" data-c="${esc(c)}"><div>${esc(c)}</div><span>${ev && ev.contact.length ? 'контакт: ' + ev.contact.join(', ') + ' с' : ''}</span></div>`; }).join('') || '<div class="msg">Нет клипов (у монстра нет собственного скелета)</div>'}</div>`,
    au: () => {
      const ag = d.audio.aggro, byClip = {}, oggs = (ag && ag.oggs) || [];
      d.audio.sounds.forEach(s => (byClip[s.clip] = byClip[s.clip] || []).push(s));
      return `${d.audio.weapon_sound ? `<div class="kv">Тип звука оружия: ${esc(d.audio.weapon_sound)}</div>` : ''}
      <h4>Звуки монстра (${d.sfx.events.length})</h4>
      ${d.sfx.events.length ? `<div class="kv">Банки: ${esc(d.sfx.banks.join(', '))} · звук собирается из игрового банка FMOD при первом нажатии ▶. <a class="zip" href="/api/sfxzip?row=${d.row}" download>⬇ Скачать всё одним архивом</a></div>${d.sfx.events.map(e => snd(e.path, e.ms)).join('')}` : '<div class="msg">Банк звуков этого монстра не найден</div>'}
      ${oggs.length ? `<h4>Реплики (${oggs.length})</h4>${oggs.map(o => `<div class="aud"><span class="f">${esc(o.split('/').pop())}</span><audio controls preload="none" src="/api/audio?path=${encodeURIComponent(o)}"></audio><a class="dl" href="/api/audio?path=${encodeURIComponent(o)}&dl=1" download aria-label="Сохранить" title="Сохранить OGG">⬇</a></div>`).join('')}` : ''}
      <h4>Звуки по анимациям</h4>${Object.entries(byClip).map(([c, a]) => `<div class="mcard"><b>${esc(c)}</b>${a.map(s => `<div class="evl">${s.sfx ? `<button class="play sm" data-ev="${esc(s.sfx)}" aria-label="Воспроизвести">▶</button>` : '<span class="nop"></span>'}<span class="f">${s.t.toFixed(2)} с · ${esc(short(s.event))}${s.bone ? ' · ' + esc(s.bone) : ''}</span></div>`).join('')}</div>`).join('') || '<div class="msg">Событий звука нет</div>'}`;
    },
    fl: () => {
      const grp = (t, a) => a && a.length ? `<h4>${t} (${a.length})</h4>${a.map(f => `<div class="file" data-p="${esc(f)}">${/\.(smd|fmt)$/i.test(f) ? '<b>3D</b> ' : ''}${esc(f)}</div>`).join('')}` : '';
      return grp('Поведение (.act)', d.files.act) + grp('Объекты (.ao)', d.files.ao) + grp('Искусственный интеллект (.ais)', d.files.ais) + grp('Модель, скелет, эффекты', d.files.misc) +
        d.folders.map(f => grp('Папка ' + f.path, f.files)).join('');
    },
  };
  const play = async e => {
    const r = e.target.closest('.row'); if (!r || !r.dataset.c || !animated) return;
    info.querySelectorAll('.row.on').forEach(x => x.classList.remove('on')); r.classList.add('on'); curClip = r.dataset.c;
    try { await E.play(rig, r.dataset.c); } catch (err) { /* clip missing in this skeleton */ }
  };
  window.__monRerender = () => { if (my === token && info.isConnected) render(); };
  const render = () => {
    info.innerHTML = tabs() + `<div class="mbody">${body[sec]()}</div>`;
    info.querySelector('.mtabs').onclick = e => { const b = e.target.closest('button'); if (b && b.dataset.s) { sec = b.dataset.s; render(); } };
    bindExport(ctx, info, E, () => d.name || 'monster');
    info.querySelector('#mscene').onchange = async e => { scene = e.target.value; await loadModel(); };
    ['#mstates', '#mclips'].forEach(s => { const el = info.querySelector(s); if (el) el.onclick = play; });
    info.querySelectorAll('.mcard[data-sk]').forEach(el => el.onclick = async e => {
      if (e.target.closest('.play, .dl, a, audio')) return;
      const clipRow = e.target.closest('.skclip');
      if (clipRow) { info.querySelectorAll('.skclip.on').forEach(x => x.classList.remove('on')); clipRow.classList.add('on'); curClip = clipRow.dataset.c; try { await E.play(rig, curClip); } catch (err) { /* clip missing */ } return; }
      const si = +el.dataset.sk; if (si === curSk) return;
      curSk = si; const c = d.skills[si].clips[0]; if (c) curClip = c;
      render(); if (c && animated) { try { await E.play(rig, c); } catch (err) { /* clip missing */ } }
    });
    info.querySelectorAll('.file').forEach(el => { el.onclick = () => { const p = el.dataset.p; if (/\.(smd|fmt)$/i.test(p)) ctx.showModel(p.toLowerCase(), p.split('/').pop(), null, true); }; });
    info.querySelectorAll('.mbody .play').forEach(b => { b.onclick = () => {
      if (!audio) return;
      if (b.classList.contains('on')) { audio.pause(); b.classList.remove('on'); b.textContent = '▶'; return; }
      info.querySelectorAll('.play.on').forEach(x => { x.classList.remove('on'); x.textContent = '▶'; });
      b.classList.add('on'); b.textContent = '…';
      audio.volume = window.__vol ? window.__vol() : 1; audio.src = evUrl(b.dataset.ev); audio.onended = () => { b.classList.remove('on'); b.textContent = '▶'; };
      audio.onerror = () => { b.classList.remove('on'); b.textContent = '✕'; };
      audio.oncanplay = () => { if (b.classList.contains('on')) b.textContent = '■'; };
      audio.play().catch(() => { b.classList.remove('on'); b.textContent = '✕'; });
    }; });
  };
  render();
}
