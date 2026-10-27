// "Умения" tab: skill list + description + animation preview on the character carried over from the editor.
import * as THREE from 'three';
import { getEd, gridStage, lightControlsHtml, bindLightControls } from '/static/editor_ui.js';
import { GroundSlamFx, surfaceOf } from '/static/groundfx.js';
import { FlaskThrowFx } from '/static/throwfx.js';
import { AoMeshFx } from '/static/aomesh.js';
import { ObjectFx, petAsset } from '/static/objfx.js';

// pilot: ground effects bound to the impact (`contact`) moment of the skill's animation; textures come from the skill's art folder
const SLAM_FX = {
  new_sunder: { R: 2.3, tex: 'Art/particles/FXLib/PBR/1024x1024/G_KGB_DrySand01_colour.dds', tint: [1.25, 1.0, .75], spikeTex: 'Art/Particles/shockwave_slam_03/a_spike_colour_dxt5.dds', spikes: 16 },
};
// pilot: thrown flasks (Concoctions): the flask model of the items, element colours of the burst
const THROW_FX = {
  explosive_concoction: { kind: 'fire', radius: 2.0 }, fulminating_concoction: { kind: 'lightning', radius: 1.8 }, shattering_concoction: { kind: 'cold', radius: 1.8 },
  acidic_concoction: { kind: 'chaos', radius: 1.8 }, bleeding_concoction: { kind: 'blood', radius: 1.8 },
};
const FLASK_MODEL = 'art/models/items/flasks/basetypes/flaskmana01drop_8118c186.smd';
// ground-impact skills whose art has real meshes (cracks, fissures, craters, spikes): the meshes come from the skill's own art files
const AO_SLAM = new Set(['earthquake', 'endurance_charge_slam', 'earthshatter', 'volcanic_fissure', 'starborn_onslaught', 'forge_hammer']);   // (the object skills below also get the ground burst)
// skills where the character's attack involves a real object: a thrown hammer (Forge Hammer) and the maul falling from the sky (Starborn Onslaught)
const OBJ_FX = {
  forge_hammer: { mode: 'throw', pet: 'Metadata/Effects/Spells/warrior_forgehammer/fx/hammerHurl_01.pet', size: 1.5, emissive: [.9, .35, .1], trail: [1, .55, .2], range: 7, stay: 2.2, R: 2.0 },
  starborn_onslaught: { mode: 'fall', pet: 'Metadata/Effects/Microtransactions/Misc/uniques/Himindrygr/EmpireanDesent/fx/verisium_hammerfall_main.pet', size: 3.4, emissive: [.3, .7, 1], trail: [.5, .85, 1], range: 4.5, stay: 1.8, R: 3.4 },
};
let seqRun = null, slamRun = null, sfxRun = null, throwRun = null, fireArt = () => {};
function dropSeq(ctx) { if (!seqRun) return; const V = ctx.viewer(); if (V) V.pets = (V.pets || []).filter(x => x !== seqRun); seqRun = null; }
function dropThrow(ctx) { if (!throwRun) return; const V = ctx.viewer(); if (V) V.pets = (V.pets || []).filter(x => x !== throwRun); throwRun.dispose(); throwRun = null; }
function dropSfx(ctx) { if (!sfxRun) return; const V = ctx.viewer(); if (V) V.pets = (V.pets || []).filter(x => x !== sfxRun); sfxRun.dispose(); sfxRun = null; }
function dropSlam(ctx) { if (!slamRun) return; const V = ctx.viewer(); if (V) V.pets = (V.pets || []).filter(x => x !== slamRun); slamRun.dispose(); slamRun = null; }

const clean = s => String(s || '').replace(/\[([^\]|]+)\|([^\]]+)\]/g, '$2').replace(/\[([^\]]+)\]/g, '$1');
// weapon requirement id -> weapon groups (order = list section order)
const GROUPS = ['Безоружный', 'Мечи', 'Топоры', 'Булавы', 'Кинжалы', 'Когти', 'Посохи', 'Жезлы', 'Копья', 'Цепы', 'Луки', 'Арбалеты', 'Щиты', 'Любое оружие ближнего боя', 'Без требований к оружию'];
function groupsOf(wr) {
  if (!wr || wr === 'Nothing') return ['Без требований к оружию'];
  const g = [], w = wr.toLowerCase();
  const add = x => { if (!g.includes(x)) g.push(x); };
  if (w.includes('unarmed')) add('Безоружный');
  if (w.includes('sword')) add('Мечи');
  if (w.includes('axe')) add('Топоры');
  if (w.includes('mace') || w.includes('blunt')) add('Булавы');
  if (w.includes('dagger')) add('Кинжалы');
  if (w.includes('claw')) add('Когти');
  if (w.includes('staff')) add('Посохи');
  if (w.includes('wand')) add('Жезлы');
  if (w.includes('spear')) add('Копья');
  if (w.includes('flail')) add('Цепы');
  if (w.replace('crossbow', '').includes('bow')) add('Луки');
  if (w.includes('crossbow')) add('Арбалеты');
  if (w.includes('shield') || w.includes('buckler')) add('Щиты');
  if (w.includes('melee') || w.includes('martial') || w.includes('sharp')) add('Любое оружие ближнего боя');
  return g.length ? g : ['Без требований к оружию'];
}
const CLASS_GROUP = { 'One Hand Swords': 'Мечи', 'Two Hand Swords': 'Мечи', 'One Hand Axes': 'Топоры', 'Two Hand Axes': 'Топоры', 'One Hand Maces': 'Булавы', 'Two Hand Maces': 'Булавы', 'Daggers': 'Кинжалы', 'Claws': 'Когти', 'Staves': 'Посохи', 'Warstaves': 'Посохи', 'Quarterstaves': 'Посохи', 'Wands': 'Жезлы', 'Sceptres': 'Булавы', 'Spears': 'Копья', 'Flails': 'Цепы', 'Bows': 'Луки', 'Crossbows': 'Арбалеты' };
const TOKEN_LABEL = { '2hsword': 'Двуручный меч', sword: 'Меч', dagger: 'Кинжал', staff: 'Посох', bow: 'Лук', crossbow: 'Арбалет', maul: 'Двуручная булава', sceptre: 'Скипетр', wand: 'Жезл', spear: 'Копьё', flail: 'Цеп', claw: 'Когти', unarmed: 'Безоружный', buckler: 'Баклер', shield: 'Щит' };
const tokenOf = c => Object.keys(TOKEN_LABEL).find(tk => c.includes('_' + tk + '_') || c.endsWith('_' + tk)) || null;
const MOVE_ORDER = c => /stationary/.test(c) ? 0 : /moving/.test(c) ? 1 : 2;

export async function openSkills(ctx) {
  const { api, esc, $ } = ctx;
  // game data carries both languages: with the English interface the English fields are shown
  const EN = () => !!(window.I18N && window.I18N.lang === 'en');
  const nm = o => EN() ? (o.name || o.ru || '') : (o.ru || o.name || '');
  const tagN = (o, i) => EN() ? ((o.tags && o.tags[i]) || '') : ((o.tags_ru && o.tags_ru[i]) || (o.tags && o.tags[i]) || '');
  const tagsOf = g => EN() ? (g.tags || []) : (g.tags_ru && g.tags_ru.length ? g.tags_ru : (g.tags || []));
  const stxt = z => EN() ? (z.text && z.text.length ? z.text : z.text_ru || []) : (z.text_ru || []);
  const quoteOf = x => EN() ? (x.text || x.text_ru) : x.text_ru, perOf = x => EN() ? (x.per_text || x.per_text_ru) : x.per_text_ru;
  const flavOf = g => EN() ? (g.flavour || g.flavour_ru) : (g.flavour_ru || g.flavour);
  const dmgOf = t => { const u = t.replace(/[⟦⟧]/g, ''), m = EN() ? /([\d.,]+)\s+to\s+([\d.,]+)\s+(?:[\w ]+?\s)?damage/i.exec(u) : /от\s+([\d.,]+)\s+до\s+([\d.,]+)\s+урона/.exec(u); return m ? m[1] + '–' + m[2] : ''; };
  const dropsOf = g => (g && g.kind === 'lineage' && (g.drops || []).length) ? `<b>${g.drops.map(x => esc(EN() ? x.en : x.ru)).join(', ')}</b>` : '';
  const srcItemsHtml = d => (d.srcItems || []).length ? `<div class="kvl"><span>Даёт предмет:</span> ${d.srcItems.map(x => `<a class="itemlink" data-item="${esc(x.n)}" data-itemru="${esc(x.ru)}" title="Открыть в разделе предметов">${esc(EN() ? x.n : x.ru)}</a>`).join(', ')}</div>` : '';
  // opens the Items tab on a base item (search + first matching row)
  const goItem = (n, ru) => {
    const b = document.querySelector('#nav button[data-t="items"]'); if (!b) return; b.click(); let k = 0;
    const iv = setInterval(() => {
      const i = document.querySelector('#q');
      if (!i || ++k <= 3) { if (k > 60) clearInterval(iv); return; }
      clearInterval(iv); const u = document.querySelector('#uonly'); if (u && u.checked) { u.checked = false; u.dispatchEvent(new Event('change', { bubbles: true })); }
      i.value = n; i.dispatchEvent(new Event('input', { bubbles: true })); let m = 0;
      const iv2 = setInterval(() => { const rows = [...document.querySelectorAll('#list .row')], row = rows.find(r => r.textContent.includes(n) || (ru && r.textContent.includes(ru))) || rows[0]; if (row) { clearInterval(iv2); row.click(); } else if (++m > 40) clearInterval(iv2); }, 250);
    }, 150);
  };
  const typeOf = g => EN() ? ((g.tags || []).find(t => t === 'Attack' || t === 'Spell') || '') : ((g.tags_ru || []).find(t => /^(Атака|Чары)/.test(t)) || '');
  const E = getEd(ctx), L = $('#list'); L.onclick = null; $('#info').innerHTML = '<div id="skstat" class="kv"></div><div id="sksup"></div>';
  const status = t => { const e = $('#skstat'); if (e) e.textContent = t; };
  $('#skmid').innerHTML = '<div id="skdetail"></div>';
  L.innerHTML = `<div class="ed skwrap"><div class="skfil"><input id="skq" placeholder="Поиск умения или камня" aria-label="Поиск умения или камня" style="width:100%">
    <div class="chips" id="skk" role="group" aria-label="Тип"></div>
    <div style="display:flex;gap:6px;margin-top:6px"><select id="skt" aria-label="Тег" style="flex:1;min-width:0"><option value="">Любой тег</option></select></div>
    <label class="kv" style="display:flex;gap:6px;align-items:center;margin-top:6px"><input type="checkbox" id="ska" style="height:auto"> Только с анимацией</label></div>
    <div class="skbody"><div id="skside" role="group" aria-label="Класс оружия"></div><div id="sgrip" role="separator" aria-orientation="vertical" aria-label="Ширина столбца категорий (двойной щелчок — сбросить)" tabindex="0"></div><div class="edlist" id="sklist" style="max-height:none;overflow:auto"></div></div><div class="legacy-scene" style="display:none"><h4>Свет</h4>${lightControlsHtml()}</div></div>
    <style>#sgrip{flex:none;width:6px;margin:0 -3px;z-index:5;cursor:col-resize;position:relative;touch-action:none}#sgrip::after{content:'';position:absolute;left:2px;top:0;bottom:0;width:2px;background:transparent}#sgrip:hover::after,#sgrip.on::after,#sgrip:focus-visible::after{background:#fc4c70}.skwrap{display:flex;flex-direction:column;height:100%}.skbody{flex:1;min-height:0;display:flex}#sklist{flex:1;min-width:0}#skside{flex:none;width:120px;overflow:auto;border-right:1px solid var(--line);padding:6px 4px 6px 8px;display:flex;flex-direction:column;gap:4px}#skside button{display:flex;align-items:center;gap:8px;width:100%;padding:6px 10px 6px 8px;border:0;border-radius:0;background:rgba(255,255,255,.04);clip-path:polygon(0 4px,4px 0,calc(100% - 4px) 0,100% 4px,100% calc(100% - 4px),calc(100% - 4px) 100%,4px 100%,0 calc(100% - 4px));color:var(--text);font:inherit;font-family:'Palatino Linotype','Book Antiqua',Palatino,Georgia,serif;font-variant:small-caps;font-size:15px;text-align:left;cursor:pointer;min-height:44px;transition:.2s}#skside button:hover{background:rgba(255,255,255,.1)}#skside button.on{background:rgba(122,90,248,.28);box-shadow:inset 0 0 0 1px #7a5af8;margin-left:-6px;width:calc(100% + 6px);padding-right:6px}#skside button.on img{filter:brightness(1.25)}#skside img{width:32px;height:32px;object-fit:contain;flex:none}#skside .wg{width:32px;height:32px;flex:none;border-radius:6px;background:rgba(255,255,255,.08);display:grid;place-items:center;font-size:16px}.tgrid{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;padding:8px 6px 12px}.row.gtile{position:relative;display:block;width:144px;height:96px;min-height:0;padding:0;overflow:hidden;border:1px solid rgba(148,163,184,.25);border-radius:2px;background:rgba(255,255,255,.04);text-align:center;user-select:none}.row.gtile:hover{background:rgba(255,255,255,.1)}.row.gtile.on{background:rgba(122,90,248,.28);border-color:#7a5af8;box-shadow:none}.row.gtile img{position:absolute;left:50%;top:6px;transform:translateX(-50%);object-fit:contain;border-radius:6px}.gn{position:absolute;left:0;right:0;bottom:0;height:40px;display:flex;flex-direction:column;justify-content:center;padding:0 4px;background:rgba(0,0,0,.2);font-variant:small-caps;font-size:14px;line-height:1.1;overflow:hidden}.gn span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.gn small{opacity:.6;font-size:12px;font-variant:normal;margin-top:1px}.sec-head.tier{display:flex;gap:8px;align-items:center;font-variant:small-caps}.sec-head .tb{min-width:28px;padding:0 6px;text-align:center;font-weight:700;line-height:24px;background:rgba(255,255,255,.12);box-shadow:0 2px 4px #0006}.row.gtile .cdot{position:absolute;top:8px;left:8px}.kvl{font-size:16px;line-height:1.7}.kvl span{color:var(--dim)}.kvl b{font-weight:600}.tagline{margin:6px 0 10px;font-size:15px;line-height:1.8}.lead{font-style:italic;color:#e0d2a8;text-align:center;margin:14px 0}.stats{text-align:center;color:#aab4ff}.stats hr{border-top-color:rgba(255,255,255,.08)}.ktype{color:#8fd3c4;font-size:16px}.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:8px;margin:12px 0}.tile{background:rgba(255,255,255,.06);border-radius:10px;padding:10px 12px}.tile small{display:block;font-size:13px;color:var(--dim);margin-bottom:2px}.tile b{font-size:24px;font-weight:600;line-height:1.1}.tile.key{background:rgba(122,90,248,.25)}.tile.key b{color:#c9bfff}.num{color:#ffd48a;font-weight:600}.lvbar{display:flex;align-items:center;gap:14px;margin:14px 0 8px}.lvn{font-size:22px;font-weight:600;min-width:84px}.lvbar input{flex:1}.skill-head .name{font-size:26px}.lead{font-size:16px;line-height:1.6}.skfil{position:sticky;top:0;z-index:5;background:var(--panel);padding-bottom:6px;border-bottom:1px solid var(--line)}.skhov{position:fixed;z-index:60;width:320px;pointer-events:none;background:#0c0a08;border:1px solid #5b4a32;border-radius:6px;padding:10px 12px;box-shadow:0 8px 24px #000a;font-size:13px;line-height:1.45;color:#c8c8c8}.skhov .hn{font-size:16px;color:#e8c070}.skhov .hs{color:#8c8c8c;font-size:14px}.skhov .hd{margin-top:6px}.crv svg{width:100%;height:auto;display:block}.crv .cb button{padding:1px 8px;margin:0 4px 6px 0;border:1px solid var(--line);border-radius:10px;background:transparent;color:var(--dim);font-size:13px;cursor:pointer}.crv .cb button.on{background:var(--accent,#7a5af8);color:#fff;border-color:transparent}.sup-h{margin:0 0 8px;color:var(--text);font-size:16px;font-weight:600}.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}.chips button{padding:2px 9px;border:1px solid var(--line);border-radius:12px;background:transparent;color:var(--dim);font-size:14px;cursor:pointer}.chips button.on{background:var(--accent,#7a5af8);color:#fff;border-color:transparent}
    .kind{font-size:13px;padding:1px 6px;border-radius:8px;background:rgba(255,255,255,.08);color:var(--dim);margin-left:auto;white-space:nowrap}.cdot{width:10px;height:10px;border-radius:50%;display:inline-block;flex:none}
    .gemblk{border:1px solid var(--line);border-radius:6px;padding:6px 8px;margin:8px 0}.gemblk b{display:block;font-weight:normal;color:var(--dim);font-size:13px;margin-bottom:4px}
    .tg a{color:var(--accent-text,#9b8afb);cursor:pointer}.req{white-space:nowrap;margin-right:8px}.lvt{width:100%;border-collapse:collapse;font-size:13px}.lvt td,.lvt th{border-bottom:1px solid var(--line);padding:2px 6px;text-align:left;vertical-align:top;font-weight:normal;white-space:nowrap}.lvt th{white-space:normal;max-width:130px;line-height:1.2;color:var(--dim);font-size:13px}.lvt tr.on td{background:rgba(255,255,255,.08)}.lvt tr{cursor:pointer}.lvw{max-height:320px;overflow:auto}.gl{max-height:260px;overflow:auto;display:flex;flex-wrap:wrap;gap:6px}.gl a.gt{display:flex;flex-direction:column;align-items:center;width:84px;margin:0 0 6px;text-align:center;font-size:13px;line-height:1.15;overflow-wrap:anywhere;hyphens:auto;color:var(--text,#ddd)}.gl a.gt img{object-fit:contain;border-radius:6px;background:rgba(255,255,255,.05)}.gl a.gt:hover span{color:var(--accent-text,#9b8afb)}.gl a{display:inline-block;margin:1px 8px 1px 0;color:var(--accent-text,#9b8afb);cursor:pointer}.skill-head img{width:56px;height:56px}.skill-head .name{font-size:22px}.skill-head{gap:10px}.ktype{font-size:14px}.tagline{margin:2px 0 6px;font-size:14px;line-height:1.5}.kvb{display:grid;grid-template-columns:1fr 1fr;gap:0 16px;margin-bottom:4px}.kvl{font-size:15px;line-height:1.45}.gemblk{margin:6px 0;padding:5px 8px;font-size:14px}.gemblk details summary{cursor:pointer;color:var(--dim)}.lead{font-size:14.5px;line-height:1.5;margin:8px 0}.lvbar{margin:8px 0 4px}.stats{font-size:14.5px;line-height:1.45}.stats hr{margin:3px 0}.crv{margin:6px 0}.crv svg{max-height:120px}.lvw{max-height:200px}.sup-sec{margin:10px 0 4px;color:var(--dim);font-size:14px;font-weight:600}.gl a.gt.lin img{outline:2px solid #e8c070;outline-offset:1px}#sksup .chips{margin:0 0 4px}.gl{max-height:none;overflow:visible}#skdetail{position:relative;font-family:'Palatino Linotype','Book Antiqua',Palatino,Georgia,'Times New Roman',serif}#skdetail>*{position:relative;z-index:1}#skdetail>.gbg{position:absolute;z-index:0;top:0;right:0;left:25%;height:320px;background-size:cover;background-position:center top;opacity:.55;pointer-events:none;-webkit-mask-image:linear-gradient(to left,#000 0%,transparent 90%),linear-gradient(to bottom,#000 55%,transparent 100%);-webkit-mask-composite:source-in;mask-composite:intersect}#skdetail .skill-head .name{color:#9fe3d3;font-weight:400;font-size:24px}#skdetail .ktype{color:#8fc9bd;text-decoration:underline;font-size:17px}#skdetail .skill-head .sub{color:#7d8a96;font-size:14px}#skdetail .tagline a{color:#cfd6dc;text-decoration:underline;margin-right:2px}#skdetail .tagline{font-size:16px}#skdetail .kvb{display:block}#skdetail .kvl{font-size:18px;line-height:1.55}#skdetail .kvl span{color:#7fb8ad}#skdetail .kvl b{font-weight:400;color:#fff}#skdetail .gemblk{background:rgba(255,255,255,.04);border:none;color:#9aa6b0}#skdetail .lead{font-size:17px;color:#d9c89a;line-height:1.55}#skdetail .lead u,#skdetail .kv u{text-decoration:underline;text-underline-offset:3px}#skdetail .stats{font-size:17px;color:#8f8fff;line-height:1.55}#skdetail .stats u{text-underline-offset:3px}#skdetail .stats .num{color:#a9a9ff;font-weight:400}#skdetail .stats hr{border:0;border-top:1px solid rgba(255,255,255,.07);margin:4px 0}#skdetail .stats{font-size:18.5px;line-height:1.5;color:#c2c2ff;background:rgba(120,120,255,.07);border:1px solid rgba(150,150,255,.18);border-radius:6px;padding:6px 14px;margin:10px 0}#skdetail .stats>*{padding:0}#skdetail .stats hr{border:0;border-top:1px solid rgba(190,190,255,.22);margin:7px 0}#skdetail .stats u{color:#e4e4ff;text-decoration-color:#9a9aff;text-underline-offset:4px;text-decoration-thickness:1.5px}#skdetail .stats .num{color:#fff;font-weight:700}#skdetail .qbox{margin:8px 0 12px;border:1px solid rgba(127,184,173,.35);background:rgba(127,184,173,.08);border-radius:6px;padding:8px 14px;font-size:17.5px;line-height:1.5}#skdetail .qlab{color:#7fe0cc;font-weight:700}#skdetail .qval{color:#f1f1f1}#skdetail .qsub{color:#8ca29c;font-size:14.5px;margin-top:2px}#skdetail .flav{margin:12px 0 8px;font-style:italic;color:#e8832d;text-align:center;font-size:17px;line-height:1.5}#skdetail .shint{margin:8px 0 10px;font-style:italic;color:#9a9a9a;text-align:center;font-size:14.5px;line-height:1.45}#skdetail .kvl u{text-decoration:underline;text-underline-offset:3px}.skhov .hflav{margin-top:8px;font-style:italic;color:#e8832d;text-align:center;font-size:14.5px;line-height:1.45}.skhov{position:fixed;z-index:70;width:380px;pointer-events:none;overflow:hidden;background:#09090c;border:1px solid #55524a;border-radius:4px;padding:12px 16px 14px;box-shadow:0 10px 30px #000c;font-family:'Palatino Linotype','Book Antiqua',Palatino,Georgia,serif;color:#e6e6e6}.skhov>*{position:relative;z-index:1}.skhov>.hbg{position:absolute;z-index:0;top:0;right:0;left:20%;height:170px;background-size:cover;background-position:center top;opacity:.5;-webkit-mask-image:linear-gradient(to left,#000 0%,transparent 90%),linear-gradient(to bottom,#000 50%,transparent 100%);-webkit-mask-composite:source-in;mask-composite:intersect}.skhov .hhead{display:flex;gap:10px;align-items:center}.skhov .hname{color:#9fe3d3;font-size:22px;line-height:1.2}.skhov .htype{color:#8fc9bd;text-decoration:underline;font-size:16px}.skhov .htags{margin:6px 0 6px;font-size:15px;color:#cfd6dc;text-decoration:underline}.skhov .hk{font-size:17px;line-height:1.5}.skhov .hk span{color:#7fb8ad}.skhov .hk b{font-weight:400;color:#fff}.skhov .hdesc{margin:10px 0 6px;font-style:italic;color:#d9c89a;text-align:center;font-size:15.5px;line-height:1.5}.skhov .hdesc u,.skhov .hstats u{text-underline-offset:3px}.skhov .hstats{text-align:center;color:#8f8fff;font-size:15.5px;line-height:1.5}.skhov .hstats div+div{border-top:1px solid rgba(255,255,255,.07);margin-top:3px;padding-top:3px}#skdetail .kvl.key,.skhov .hk.key{background:linear-gradient(90deg,rgba(255,200,80,.22),rgba(255,200,80,.04));border-left:3px solid #ffc850;border-radius:3px;padding:1px 10px;margin:3px 0}#skdetail .kvl.key span,.skhov .hk.key span{color:#e8d6a0}#skdetail .kvl.key b,.skhov .hk.key b{color:#ffe08a;font-weight:700;font-size:1.18em}.skhov{width:440px}.skhov .hsep{height:2px;width:180px;margin:4px 0 6px;background:linear-gradient(90deg,#29413b,#29413b00)}.skhov .hwide{height:2px;margin:6px 14px;background:linear-gradient(to right,#0000,#d9c89a 35%,#d9c89a 65%,#0000)}.skhov .hhead{padding:2px 0 4px}.skhov .hdesc{margin:6px 0}.skhov .hstats div+div{border-top:0;margin-top:0;padding-top:0}.skhov .hstats div:nth-child(even){background:linear-gradient(to right,#fff1,#fff2,#fff1)}.skhov .hq{margin-top:6px;text-align:center;font-size:14.5px;color:#8f8fff}.skhov .hq div:first-child{color:#fff}</style>`;
  // carry the editor's character (with its equipment) into this tab
  status('Загрузка персонажа…');
  let humanActor = null, humanEquip = null, curForm = null;
  const V = ctx.ensureViewer(); E.ctx.keepCamera = true;
  gridStage(ctx);
  try {
    if (E.actor) await E.reload({});
    else {
      const a = (await api('/api/actors?q=Marauder&kind=player'))[0];
      await E.loadActor(a);
    }
    humanActor = E.actor; status(E.actor.name || '');
    V.cam.fov = 30; V.cam.updateProjectionMatrix(); V.cam.position.set(0, 6.2, -7.4); V.ctl.target.set(0, 0.9, 0); V.ctl.update();
  } catch (err) { status('Ошибка персонажа: ' + err.message); }
  bindLightControls(ctx);
  if (!$('#skq')) return;   // another tab was opened while the character loaded
  const slots = Object.keys(E.equip).length;
  let rows = [], t;
  const curGroup = () => { const it = E.equip.weapon && E.equip.weapon.item; return it ? (CLASS_GROUP[it.class] || '') : 'Безоружный'; };
  let wsel = '', cats = [];
  const drawSide = () => {
    $('#skside').innerHTML = [{ i: '', ru: 'Все', icon: '' }, ...cats].map(c => `<button data-w="${c.i}" class="${String(c.i) === wsel ? 'on' : ''}" title="${esc(nm(c))}">${c.icon ? `<img src="/api/icon?size=64&path=${encodeURIComponent(c.icon)}" alt="" onerror="this.style.visibility='hidden'">` : '<span class="wg">∗</span>'}<span>${esc(nm(c))}</span></button>`).join('');
  };
  drawSide();
  {
    const g = $('#sgrip'), S = $('#skside'); let drag = false, w0 = 0; try { w0 = +localStorage.getItem('poe_inspector.sw') || 0; } catch (e) { /* ignore */ }
    if (w0) S.style.width = w0 + 'px';
    const apply = w => { w = Math.max(70, Math.min(320, Math.round(w))); S.style.width = w + 'px'; try { localStorage.setItem('poe_inspector.sw', String(w)); } catch (e) { /* ignore */ } };
    g.onpointerdown = e => { drag = true; g.classList.add('on'); g.setPointerCapture(e.pointerId); e.preventDefault(); };
    g.onpointermove = e => { if (drag) apply(e.clientX - S.getBoundingClientRect().left); };
    g.onpointerup = g.onpointercancel = () => { drag = false; g.classList.remove('on'); };
    g.onkeydown = e => { if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { apply(S.getBoundingClientRect().width + (e.key === 'ArrowRight' ? 16 : -16)); e.preventDefault(); } };
    g.ondblclick = () => { try { localStorage.removeItem('poe_inspector.sw'); } catch (e) { /* ignore */ } S.style.width = ''; };
  }
  $('#skside').onclick = e => { const b = e.target.closest('button'); if (!b) return; wsel = b.dataset.w; drawSide(); list(); };
  const KIND = { active: 'умение', spirit: 'Spirit', support: 'поддержка', lineage: 'династич.', item: 'предмет', other: 'прочее' };
  const KIND_SEC = { spirit: 'Spirit', support: 'Поддерживающие камни', lineage: 'Династические поддержки', other: 'Прочие умения' };
  const DOT = { str: '#d4553a', dex: '#4aa86a', int: '#4a86d4', white: '#c8c8c8' };
  let kind = 'active', facets = null;
  const drawChips = () => { $('#skk').innerHTML = [{ k: '', ru: 'Все' }].concat(facets ? facets.kinds : []).map(x => `<button data-k="${x.k}" class="${x.k === kind ? 'on' : ''}">${esc(x.ru)}${x.n ? ' ' + x.n : ''}</button>`).join(''); };
  const drawTags = () => { if (!facets || !$('#skt')) return; const cur = $('#skt').value; $('#skt').innerHTML = `<option value="">Любой тег</option>` + facets.tags.slice(0, 60).map(t => `<option value="${esc(t.k)}">${esc(EN() ? t.k : t.ru)} (${t.n})</option>`).join(''); $('#skt').value = cur; };
  api('/api/gemfacets').then(f => { facets = f; cats = f.cats || []; drawSide(); drawChips(); drawTags(); }).catch(() => {});
  drawChips();
  $('#skk').onclick = e => { const b = e.target.closest('button'); if (!b) return; kind = b.dataset.k; drawChips(); list(); };
  const TIERS = [1, 7, 15, 23, 32, 42, 53], ROMAN = ['I', 'III', 'V', 'VII', 'IX', 'XI', 'XIII'];
  const tierLab = m => { const i = TIERS.indexOf(m); return i >= 0 ? `<span class="tb">${ROMAN[i]}</span>Камни от уровня ${m}` : (m ? `Камни от уровня ${m}` : 'Без уровня'); };
  const list = async () => {
    let all = await api(`/api/gems?q=${encodeURIComponent($('#skq').value)}&kind=${kind}&tag=${encodeURIComponent($('#skt').value)}&cat=${wsel}`);
    if (!$('#sklist')) return;
    if ($('#ska').checked) all = all.filter(r => r.anim);
    all.forEach(r => { r.sec = r.kind === 'item' ? 'Умения предметов: ' + (r.grp || 'прочее') : r.kind === 'other' ? 'Прочие умения' : tierLab(r.minlvl); r.so = r.kind === 'item' ? 1e9 + (r.grp || '').charCodeAt(0) : r.kind === 'other' ? 2e9 : r.minlvl; });
    all.sort((a, b) => a.so - b.so || (b.anim - a.anim) || nm(a).localeCompare(nm(b)));
    rows = all; let last = null, html = '';
    all.forEach((r, i) => {
      if (r.sec !== last) { if (last !== null) html += '</div>'; last = r.sec; html += `<div class="sec-head tier">${r.kind === 'other' || r.kind === 'item' ? esc(r.sec) : r.sec}</div><div class="tgrid">`; }
      html += rowHtml(r, i);
    });
    $('#sklist').innerHTML = html ? html + '</div>' : '<div class="msg">Ничего не найдено</div>';
  };
  const rowHtml = (r, i) => `<div class="row gtile ${r.anim || r.kind !== 'active' ? '' : 'muted'}" data-i="${i}" title="${r.anim ? '' : r.kind === 'active' ? 'Нет анимации' : ''}">${r.color && r.kind !== 'other' && r.kind !== 'item' ? `<i class="cdot" style="background:${DOT[r.color]}"></i>` : ''}<img loading="lazy" width="56" height="56" src="/api/icon?size=128&path=${encodeURIComponent(r.icon)}" onerror="this.style.visibility='hidden'"><div class="gn"><span>${esc(nm(r))}</span>${r.minlvl && r.kind !== 'other' && r.kind !== 'item' ? `<small>Ур. ${r.minlvl}</small>` : ''}</div></div>`;
  $('#skq').oninput = () => { clearTimeout(t); t = setTimeout(list, 200); };
  $('#skt').onchange = list; $('#ska').onchange = list;
  let hov = null, hovT = 0, hovTok = 0;
  const hideHov = () => { clearTimeout(hovT); hovTok++; if (hov) { hov.remove(); hov = null; } };
  const hideSHov = hideHov;
  const gemCache = new Map();
  const getGem = k => { if (!gemCache.has(k)) gemCache.set(k, api('/api/gem?k=' + encodeURIComponent(k)).catch(() => null)); return gemCache.get(k); };
  const umk = t => esc(t).replace(/\u27e6(.*?)\u27e7/g, '<u>$1</u>').replace(/\[([^\]|]+)\|([^\]]+)\]/g, '<u>$2</u>').replace(/\[([^\]]+)\]/g, '<u>$1</u>');
  const KIND_P = { active: 'Камень умения', spirit: 'Камень Spirit', support: 'Поддерживающий камень', lineage: 'Династическая поддержка', other: 'Умение' };
  const previewHtml = (g, seed) => {
    const lv = g.levels || [], li = lv.find(l => l.level === 20) || lv[lv.length - 1] || {};
    const sets = (g.stats || []).filter(st => st.levels.length), at = st => st.levels.find(z => z.level === li.level) || {};
    const lines = [...new Set(sets.map(st => stxt(at(st))).flat())];
    const mset = sets.find(st => at(st).mult != null), mult = mset ? at(mset).mult : null, crit = sets[0] ? at(sets[0]).crit : null;
    const isAtk = (g.tags || []).includes('Attack'), f = v => String(+v.toFixed(2)).replace('.', ',');
    let dmg = ''; for (const t of lines) { dmg = dmgOf(t); if (dmg) break; }
    const KV = (k, v, key) => v ? `<div class="hk${key ? ' key' : ''}"><span>${k}:</span> ${v}</div>` : '';
    const wr = groupsOf((seed && seed.wr) || ''), wtxt = wr.includes('Без требований к оружию') ? '' : wr.join(', ');
    const req = g.req ? ['str', 'dex', 'int'].filter(a => g.req[a]).map(a => ATTR_RU[a]).join(', ') : '';
    const isSup = g.kind === 'support' || g.kind === 'lineage', tags = tagsOf(g);
    const type = typeOf(g) || KIND_P[g.kind] || '';
    return `${g.ui_image ? `<div class="hbg" style="background-image:url('/api/icon?size=512&path=${encodeURIComponent(g.ui_image)}')"></div>` : ''}
      <div class="hhead"><img width="52" height="52" src="/api/icon?size=128&path=${encodeURIComponent(g.icon || '')}" onerror="this.style.visibility='hidden'"><div><div class="hname">${esc(nm(g))}</div><div class="htype">${esc(type)}</div></div></div>
      ${tags.length ? `<div class="htags">${esc(tags.join(', '))}</div>` : ''}
      <div class="hsep"></div>
      ${isSup ? `${KV('<u>Категория</u>', (g.family_ru || g.family || []).length ? `<b>${esc((EN() ? (g.family || g.family_ru) : (g.family_ru && g.family_ru.length ? g.family_ru : g.family)).join(', '))}</b>` : '')}${KV('<u>Множитель расхода ресурсов</u>', li.cost_mult ? `<b>${li.cost_mult}%</b>` : '', true)}${KV('Требуется', g.minlvl ? `<b>Уровень ${g.minlvl}</b>` : '')}${KV('Выпадает с', dropsOf(g))}` : `${KV('Уровень', li.level ? `<b>${li.level}</b>` : '')}${KV(li.reservation ? 'Резерв' : 'Расход ресурсов', li.reservation ? `<b>${li.reservation}</b> духа` : (li.cost && li.cost[0] ? `<b>${li.cost[0]}</b> маны` : ''), true)}${KV('Множитель расхода маны', isSup && li.cost_mult ? `<b>${li.cost_mult}%</b>` : '', true)}${KV('Скорость атаки', !isSup && isAtk && li.atk_speed != null ? `<b>${100 + li.atk_speed}%</b> от базовой` : '', true)}${KV('Урон от атаки', !isSup && isAtk && mult != null ? `<b>${f(100 + mult / 100)}%</b>` : '', true)}${KV('Урон', !isSup && !isAtk && dmg ? `<b>${dmg}</b>` : '', true)}${KV('Шанс крита', !isSup && !isAtk && crit ? `<b>${f(crit / 100)}%</b>` : '')}${KV('Требуется атрибут', req)}${KV('Требуется', wtxt)}${KV('Требуется уровень', g.minlvl ? `<b>${g.minlvl}</b>` : '')}`}
      <div class="hwide"></div>
      <div class="hdesc">${umk(EN() ? (g.desc || g.text || g.desc_ru || g.text_ru || '') : (g.desc_ru || g.text_ru || g.desc || g.text || ''))}</div>
      <div class="hwide"></div>
      ${lines.length ? `<div class="hstats">${lines.slice(0, 7).map(t => `<div>${umk(t)}</div>`).join('')}</div>` : ''}
      ${(g.quality || []).length ? `<div class="hq"><div>Дополнительно при качестве 20%:</div>${g.quality.map(x => `<div>${esc(quoteOf(x))}</div>`).join('')}</div>` : ''}
      ${isSup && flavOf(g) ? `<div class="hflav">${esc(flavOf(g))}</div>` : ''}`;
  };
  const placeHov = a => {
    if (!hov) return;
    const b = a.getBoundingClientRect(), w = hov.offsetWidth, h = hov.offsetHeight;
    let left = b.right + 8; if (left + w > innerWidth - 8) left = Math.max(8, b.left - w - 8);
    hov.style.left = left + 'px'; hov.style.top = Math.max(8, Math.min(b.top - 6, innerHeight - h - 8)) + 'px';
  };
  const showPreview = (a, k, seed) => {
    clearTimeout(hovT); const tok = ++hovTok;
    hovT = setTimeout(async () => {
      if (hov) { hov.remove(); hov = null; }
      hov = document.createElement('div'); hov.className = 'skhov'; hov.innerHTML = `<div class="hname">${esc((seed && nm(seed)) || '')}</div><div class="hk"><span>Загрузка…</span></div>`;
      document.body.appendChild(hov); placeHov(a);
      const g = /^g\d+$/.test(k) ? await getGem(k) : null;
      if (tok !== hovTok || !hov) return;
      hov.innerHTML = g ? previewHtml(g, seed) : `<div class="hname">${esc((seed && nm(seed)) || '')}</div><div class="hdesc">${esc((seed && (EN() ? (seed.tip_en || seed.tip) : seed.tip)) || '')}</div>`;
      placeHov(a);
    }, 220);
  };
  $('#sklist').onmouseover = e => { const row = e.target.closest('.row'); if (!row) return; const r = rows[row.dataset.i]; if (r) showPreview(row, r.k, r); };
  $('#sklist').onmouseleave = hideHov; $('#list').onscroll = hideHov;
  // the hero holds a weapon of the skill's category (SkillCraftingData); skills that are used unarmed (and Primal ones) are shown with empty hands
  const CAT_WEAPON = { 6: 'Two Hand Maces', 0: 'Two Hand Axes', 3: 'One Hand Swords', 4: 'Daggers', 8: 'Spears', 5: 'Flails', 2: 'Bows', 9: 'Crossbows', 10: 'Quarterstaves', 7: 'Staves', 1: 'Wands', 11: null };
  const TWO_HANDED = new Set(['Two Hand Maces', 'Two Hand Axes', 'Two Hand Swords', 'Spears', 'Bows', 'Crossbows', 'Quarterstaves', 'Staves']);
  let origEquip = null, weaponList = null, shieldList = null;
  const weaponItem = async cls => {
    if (!weaponList) weaponList = await api('/api/slotitems?slot=weapon&q=');
    return weaponList.find(r => r.class === cls && !r.unique) || null;
  };
  const shieldItem = async () => {
    if (!shieldList) shieldList = await api('/api/slotitems?slot=offhand&q=');
    return shieldList.find(r => r.class === 'Shields' && !r.unique) || null;
  };
  const ONE_HANDED = { 6: 'One Hand Maces', 0: 'One Hand Axes', 3: 'One Hand Swords' };
  const clsFromWr = wr => {   // weapon requirement of a skill without a gem category (basic attacks): "Sword", "Any Mace", "Bow" …
    const w = wr.toLowerCase();
    if (/crossbow/.test(w)) return 'Crossbows'; if (/\bbow\b/.test(w)) return 'Bows'; if (/dagger/.test(w)) return 'Daggers'; if (/claw/.test(w)) return 'Claws';
    if (/spear/.test(w)) return 'Spears'; if (/flail/.test(w)) return 'Flails'; if (/wand/.test(w)) return 'Wands'; if (/sceptre/.test(w)) return 'Sceptres';
    if (/staff|quarterstaff/.test(w)) return 'Quarterstaves'; if (/mace|blunt/.test(w)) return 'One Hand Maces'; if (/axe/.test(w)) return 'One Hand Axes'; if (/sword/.test(w)) return 'One Hand Swords';
    return undefined;
  };
  const applyCategoryWeapon = async d => {
    if (d.form || !E.root) return;
    const g = d.gem, cats = (g && g.cat) || [], wr = String(d.weapons || ''), types = d.types || [];
    const needShield = types.includes('RequiresShield') || /shield|buckler/i.test(wr);
    const unarmedOnly = /unarmed/i.test(wr) && !/any|sword|axe|mace|dagger|bow|spear|staff|flail|wand|claw|sceptre|talisman/i.test(wr);
    let cls;
    if (unarmedOnly) cls = null;
    else if (needShield) cls = ONE_HANDED[cats[0]] || clsFromWr(wr) || 'One Hand Swords';   // a shield skill: one-handed weapon in the right hand, the shield in the left
    else if (cats.length && !(g && g.basic)) cls = cats[0] in CAT_WEAPON ? CAT_WEAPON[cats[0]] : undefined;
    else cls = /unarmed/i.test(wr) ? undefined : clsFromWr(wr);   // basic attacks have no category: the weapon of their requirement
    if (cls === undefined) return;
    if (!origEquip) { origEquip = { weapon: (E.equip.weapon && E.equip.weapon.item) || null, offhand: (E.equip.offhand && E.equip.offhand.item) || null }; }
    if (cls === null) { if (E.equip.weapon) await E.setSlot('weapon', null); if (E.equip.offhand) await E.setSlot('offhand', null); return; }
    const it = await weaponItem(cls); if (!it) return;
    if (!E.equip.weapon || E.equip.weapon.item.id !== it.id) await E.setSlot('weapon', it);
    if (needShield) {
      const sh = await shieldItem();
      if (sh && (!E.equip.offhand || E.equip.offhand.item.id !== sh.id)) await E.setSlot('offhand', sh);
    } else if ((TWO_HANDED.has(cls) || cls === 'Bows' || cls === 'Crossbows') && E.equip.offhand) await E.setSlot('offhand', null);
  };
  window.__skRestore = async () => {   // leaving the tab: the editor gets the hero's own weapons back
    const o = origEquip; origEquip = null; if (!o || curForm || !E.root) return;
    try { await E.setSlot('weapon', o.weapon); await E.setSlot('offhand', o.offhand); } catch (e) { /* item gone */ }
  };
  // skills performed in a shapeshift form (bear / wolf / wyvern) are shown on the form's model; any other skill brings the human back
  const ensureActor = async d => {
    const f = d.form, V = ctx.viewer();
    if (f && curForm !== f.id) {
      if (!curForm) { humanEquip = {}; for (const k in E.equip) humanEquip[k] = E.equip[k].item; }
      curForm = f.id; E.ctx.keepCamera = false;
      await E.loadActor({ id: 'form:' + f.id, kind: 'npc', name: f.ru, skeleton: f.skeleton.toLowerCase(), skin: f.skin.toLowerCase() });
      E.ctx.keepCamera = true; status('Форма: ' + f.ru);
    } else if (!f && curForm) {
      curForm = null; await E.loadActor(humanActor);
      for (const k in (humanEquip || {})) { try { await E.setSlot(k, humanEquip[k]); } catch (e) { /* item gone */ } }
      humanEquip = null;
      if (V) { V.cam.position.set(0, 6.2, -7.4); V.ctl.target.set(0, 0.9, 0); V.ctl.update(); }
    }
  };
  let lastRow = null;
  const openRow = async r => {
    hideHov(); lastRow = r;
    $('#skdetail').innerHTML = '<div class="msg">Загрузка…</div>';
    try {
      const g = r.kind === 'other' || r.kind === 'item' ? null : await api('/api/gem?k=' + encodeURIComponent(r.k));
      if (r.skill !== null && r.skill !== undefined) { const d = await api('/api/skill?i=' + r.skill); d.gem = g; d.srcItems = r.items || []; show(d); }
      else show(gemOnly(g));
    } catch (err) { $('#skdetail').innerHTML = `<div class="msg">Ошибка: ${esc(err.message)}</div>`; }
  };
  $('#sklist').onclick = e => {
    const row = e.target.closest('.row'); if (!row) return;
    document.querySelectorAll('#sklist .row.on').forEach(x => x.classList.remove('on')); row.classList.add('on');
    openRow(rows[row.dataset.i]);
  };
  // a support / lineage gem has no skill of its own: build the card from the gem data (no animation, sounds or effects)
  const gemOnly = g => ({ i: null, id: g.k, name: g.name, ru: g.ru, icon: g.sup_icon || g.icon, description: g.text, description_ru: g.text_ru, short: '', noAnim: true, gem: g, anim: [], art: [],
    effects: [{ cast_time: null, tags: g.tags, levels: g.levels || [], stats: g.stats || [], animation: [] }] });
  const KIND_FULL = { active: 'Камень умения', spirit: 'Камень Spirit', support: 'Поддерживающий камень', lineage: 'Династическая поддержка', item: 'Умение от предмета', other: 'Умение без камня' };
  const links = (arr, max = 400) => arr.slice(0, max).map(x => `<a class="gt${x.kind === 'lineage' ? ' lin' : ''}" data-gk="${x.k}" title="${esc(nm(x))}"><img loading="lazy" width="56" height="56" src="/api/icon?size=128&path=${encodeURIComponent(x.icon || '')}" onerror="this.style.visibility='hidden'"><span>${esc(nm(x))}</span></a>`).join('') + (arr.length > max ? `<span class="kv"> и ещё ${arr.length - max}</span>` : '');
  const ATTR_RU = { str: 'Сила', dex: 'Ловкость', int: 'Интеллект' };
  const tagLine = g => `<div class="tagline tg">${(g.tags || []).map((t, i) => `<a data-tag="${esc(t)}" title="Показать все камни с этим тегом">${esc(tagN(g, i) || t)}</a>`).join(', ')}</div>`;
  const qualityHtml = g => (g && g.quality && g.quality.length) ? `<div class="qbox">${g.quality.map(x => `<div class="qline"><span class="qlab">Качество 20%:</span> <span class="qval">${esc(quoteOf(x))}</span><div class="qsub">за каждый 1% качества: ${esc(perOf(x))}</div></div>`).join('')}</div>` : '';
  const supExtras = g => (g && (g.kind === 'support' || g.kind === 'lineage')) ? `${flavOf(g) ? `<div class="flav">${esc(flavOf(g))}</div>` : ''}<div class="shint">Вставьте в гнездо для камня поддержки в окне умений, чтобы применить эффекты камня к выбранному умению. Нельзя использовать несколько камней поддержки одной и той же категории на одном умении.</div>` : '';
  const gemBlock = g => {
    if (!g) return '';
    const req = g.req ? ['str', 'dex', 'int'].filter(a => g.req[a]).map(a => `<span class="req"><i class="cdot" style="background:${DOT[a]}"></i>${ATTR_RU[a]} ${g.req[a]}%</span>`).join(' ') : '';
    const q = (g.quality || []).map(x => `<div>${esc(quoteOf(x))} <span class="kv">(на 20%; за 1% — ${esc(perOf(x))})</span></div>`).join('');
    return `<div class="gemblk"><i class="cdot" style="background:${DOT[g.color] || DOT.white}"></i> ${KIND_FULL[g.kind] || ''}${g.minlvl ? ' · требуется уровень ' + g.minlvl : ''}${req ? ' · ' + req : ''}</div>`;
  };
  let supTag = '', curGem = null, supIdx = {};
  const TAG_ORDER = ['Fire', 'Cold', 'Lightning', 'Chaos', 'Physical', 'Projectile', 'AoE', 'Chaining', 'Melee', 'Attack', 'Spell', 'Minion', 'Duration', 'Totem', 'Trap', 'Mine', 'Curse', 'Warcry', 'Channelling', 'Aura', 'Slam', 'Strike', 'Trigger', 'Payoff', 'Conditional'];
  const supBlock = g => {
    if (!g) return '';
    const isSup = g.kind === 'support' || g.kind === 'lineage', arr = isSup ? (g.supports || []) : (g.supported_by || []);
    const title = isSup ? 'Подходит умениям' : 'Подходящие поддержки';
    if (!arr.length) return `<div class="sup-h">${title} · 0</div><div class="kv">${isSup ? 'Нет подходящих умений' : 'Для этого умения нет подходящих поддержек'}</div>`;
    supIdx = Object.fromEntries(arr.map(x => [x.k, x]));
    const ru = {}, cnt = {};
    arr.forEach(x => (x.tags || []).forEach((t, i) => { ru[t] = tagN(x, i) || t; cnt[t] = (cnt[t] || 0) + 1; }));
    const lin = arr.filter(x => x.kind === 'lineage').length;
    const shown = arr.filter(x => !supTag || (supTag === '__lin' ? x.kind === 'lineage' : (x.tags || []).includes(supTag)));
    const chips = [['', 'Все', arr.length]].concat(lin ? [['__lin', 'Династические', lin]] : [], TAG_ORDER.filter(t => cnt[t]).map(t => [t, ru[t], cnt[t]]), Object.keys(cnt).filter(t => !TAG_ORDER.includes(t) && t !== 'Support' && t !== 'Lineage' && cnt[t] >= 3).sort((a, b) => cnt[b] - cnt[a]).slice(0, 6).map(t => [t, ru[t], cnt[t]]));
    const keyOf = x => x.kind === 'lineage' ? '__lin' : (TAG_ORDER.find(t => (x.tags || []).includes(t)) || '__other');
    const groups = {}; shown.forEach(x => (groups[keyOf(x)] = groups[keyOf(x)] || []).push(x));
    const order = ['__lin', ...TAG_ORDER, '__other'].filter(k => groups[k]);
    return `<div class="sup-h">${title} · ${shown.length}${shown.length !== arr.length ? ' из ' + arr.length : ''}</div>
      <div class="chips">${chips.map(([k, n, c]) => `<button data-st="${esc(k)}" class="${k === supTag ? 'on' : ''}">${esc(n)} ${c}</button>`).join('')}</div>
      ${order.map(k => `<div class="sup-sec">${k === '__lin' ? 'Династические' : k === '__other' ? 'Прочие' : esc(ru[k])} · ${groups[k].length}</div><div class="gl">${links(groups[k])}</div>`).join('')}`;
  };
  const onGemClick = e => {
    const it = e.target.closest('a[data-item]'); if (it) { goItem(it.dataset.item, it.dataset.itemru); return; }
    const st = e.target.closest('button[data-st]');
    if (st) { supTag = st.dataset.st; $('#sksup').innerHTML = supBlock(curGem); return; }
    const tg = e.target.closest('a[data-tag]');
    if (tg) { const t = tg.dataset.tag, sel = $('#skt'); if (![...sel.options].some(o => o.value === t)) sel.insertAdjacentHTML('beforeend', `<option value="${esc(t)}">${esc(tg.textContent)}</option>`); sel.value = t; kind = ''; drawChips(); list(); return; }
    const a = e.target.closest('a[data-gk]'); if (!a) return;
    const k = a.dataset.gk, i = rows.findIndex(r => r.k === k);
    if (i >= 0) { const row = document.querySelector(`#sklist .row[data-i="${i}"]`); if (row) { row.click(); row.scrollIntoView({ block: 'nearest' }); return; } }
    api('/api/gems?q=').then(all => { const r = all.find(x => x.k === k); if (r) openRow(r); });
  };
  $('#skdetail').onclick = onGemClick; $('#sksup').onclick = onGemClick;
  $('#sksup').onmouseover = e => { const a = e.target.closest('a.gt'); if (a) showPreview(a, a.dataset.gk, supIdx[a.dataset.gk] || {}); };
  $('#sksup').onmouseleave = hideHov; $('#sksup').onscroll = hideHov; $('#info').onscroll = hideHov;

  // ---- sounds of the skill: timeline sound events of the playing clip, rendered from the game's FMOD banks ----
  const ATTR = { str: 'Str', dex: 'Dex', int: 'Int', strdex: 'StrDex', strint: 'StrInt', dexint: 'DexInt' };
  const vol = () => (typeof window.__vol === 'function' ? window.__vol() : .8);
  const sfxUrl = (ev, dl) => ev.ogg ? '/api/audio?path=' + encodeURIComponent(ev.ogg) + (dl ? '&dl=1' : '') : '/api/sfx?event=' + encodeURIComponent(ev.sfx) + '&banks=' + encodeURIComponent(ev.bank || (sfxData.banks || []).join('|')) + (dl ? '&dl=1' : '');
  let sfxData = null, autoPlay = true;
  const attrOf = () => ATTR[String((E.actor && E.actor.arch) || '').replace(/b$/, '')] || null;
  const vocalOk = ev => { if (/\/RogueExiles\//i.test(ev.event)) return false; const m = /\/Vocal\/(\w+)\/Efforts\//i.exec(ev.event); return !m || !attrOf() || m[1].toLowerCase() === attrOf().toLowerCase(); };
  const clipSounds = clip => ((sfxData && sfxData.clips[clip]) || []).filter(vocalOk);
  function setupSfx() {
    dropSfx(ctx);
    const V = ctx.viewer(); if (!V) return;
    const cache = new Map(), warm = ev => { if (!ev.sfx && !ev.ogg) return null; const u = sfxUrl(ev); if (!cache.has(u)) { const a = new Audio(); a.preload = 'auto'; a.src = u; cache.set(u, a); } return cache.get(u); };
    const imp = {}; for (const a of (sfxD && sfxD.anim) || []) for (const c of a.events || []) { const e = (c.events || []).find(x => x.name === 'contact'); if (e) imp[c.name] = e.t; }
    const seenEv = new Set(), hit = (sfxData.art || []).filter(e => (e.sfx || e.ogg) && /\/(Slam|Cascade|Debris)$/i.test(e.event) && !/FistOfWar/i.test(e.event) && !seenEv.has(e.event) && seenEv.add(e.event));
    hit.forEach(warm);
    let prev = 0, last = null;
    fireArt = rx => { for (const ev of (sfxData.art || []).filter(e => (e.sfx || e.ogg) && rx.test(e.event)).slice(0, 1)) { const a = warm(ev); if (a && a.readyState >= 3 && autoPlay) { const c = a.cloneNode(); c.volume = vol(); c.play().catch(() => {}); } } };
    sfxRun = {
      warm,
      update() {
        const cur = E.curClip && E.curClip[1]; if (!sfxData || !cur || !E.action) { prev = 0; return; }
        if (cur !== last) { last = cur; prev = 0; clipSounds(cur).forEach(warm); }
        const t = E.action.time; if (t < prev) prev = 0;
        if (autoPlay) for (const ev of clipSounds(cur)) {
          if (prev < ev.t && t >= ev.t && (ev.sfx || ev.ogg) && !/Loop(\.\w+)?$/i.test(ev.event)) { const a = warm(ev); if (a && a.readyState >= 3) { const c = a.cloneNode(); c.volume = vol(); c.play().catch(() => {}); } }
        }
        if (autoPlay && imp[cur] !== undefined && prev < imp[cur] && t >= imp[cur]) for (const ev of hit) { const a = warm(ev); if (a && a.readyState >= 3) { const c = a.cloneNode(); c.volume = vol(); c.play().catch(() => {}); } }
        prev = t;
      },
      dispose() { cache.clear(); },
    };
    V.pets = V.pets || []; V.pets.push(sfxRun);
  }
  function drawSfx() {
    const box = $('#sksfx'); if (!box || !sfxData) return;
    const cur = E.curClip && E.curClip[1], list = clipSounds(cur || ''), row = (ev, label) => {
      const nm = ev.event.split('/').slice(-2).join('/');
      return `<div class="sfx"><span class="kv" style="width:3.4em">${label}</span><span class="nm" title="${esc(ev.event)}">${esc(nm)}</span>${ev.sfx || ev.ogg ? `<button class="play" data-u="${esc(sfxUrl(ev))}" aria-label="Воспроизвести">▶</button><a href="${esc(sfxUrl(ev, true))}" download aria-label="Сохранить WAV" title="Сохранить WAV">⬇</a>` : '<span class="kv">нет в банках</span>'}</div>`;
    };
    const art = (sfxData.art || []).filter(vocalOk);
    box.innerHTML = `<label class="kv" style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="skauto" ${autoPlay ? 'checked' : ''} style="height:auto"> Звуки вместе с анимацией</label>
      <h5>Анимация ${esc(cur || '')}</h5>${list.length ? list.map(e => row(e, e.t.toFixed(2) + ' c')).join('') : '<div class="kv">У этой анимации звуков в таймлайне нет</div>'}
      ${art.length ? `<h5>Эффекты умения</h5>${art.map(e => row(e, 'эфф.')).join('')}` : ''}
      ${(sfxData.bank_events || []).length ? `<h5>Остальное в банке умения</h5>${sfxData.bank_events.map(e => row({ event: e.path, sfx: e.path, bank: e.bank }, '')).join('')}` : ''}`;
    $('#skauto').onchange = ev => { autoPlay = ev.target.checked; };
    box.onclick = ev => {
      const b = ev.target.closest('button.play'); if (!b) return;
      const a = window.__audio || (window.__audio = new Audio()); a.pause(); a.src = b.dataset.u; a.volume = vol(); a.play().catch(() => {});
    };
  }
  async function loadSfx(d) {
    sfxData = null; const box = $('#sksfx'); if (box) box.innerHTML = '<div class="msg">Загрузка звуков из игровых банков…</div>';
    try { const r = await api('/api/skillsfx?i=' + d.i); if (sfxD !== d) return; sfxData = r; setupSfx(); drawSfx(); }
    catch (e) { if ($('#sksfx')) $('#sksfx').innerHTML = `<div class="msg">Звуки недоступны: ${esc(e.message)}</div>`; }
  }
  let sfxD = null;

  function makeFacing() {
    const v = new THREE.Vector3(), w = new THREE.Vector3(), fwd = new THREE.Vector3();
    // facing = where the face looks: the head bone's forward axis, calibrated on the bind pose (where the feet point forward), then rotated with the head
    const q0 = new THREE.Quaternion(), q1 = new THREE.Quaternion(), m0 = new THREE.Matrix4(), p0 = new THREE.Vector3(), p1 = new THREE.Vector3(), s0 = new THREE.Vector3();
    let cal = null, calFor = null;
    const bindPos = (bone, out) => { const i = E.skeleton.bones.indexOf(bone); if (i < 0) return false; m0.copy(E.skeleton.boneInverses[i]).invert(); m0.decompose(out, q0, s0); return true; };
    const calibrate = () => {
      const head = E.findBone('head_jntBnd'); if (!head) return null;
      fwd.set(0, 0, 0);
      for (const s_ of ['L', 'R']) { const a = E.findBone(s_ + '_ankle_jntBnd'), t = E.findBone(s_ + '_toe_jntBnd'); if (a && t && bindPos(a, p0) && bindPos(t, p1)) fwd.add(p1.sub(p0)); }
      fwd.y = 0; if (fwd.lengthSq() < 1e-6) return null; fwd.normalize();
      const i = E.skeleton.bones.indexOf(head); m0.copy(E.skeleton.boneInverses[i]).invert(); m0.decompose(p0, q1, s0);
      return { head, local: fwd.clone().applyQuaternion(q1.clone().invert()) };
    };
    const facing = () => {
      if (calFor !== E.skeleton) { cal = calibrate(); calFor = E.skeleton; }
      if (cal) { cal.head.getWorldQuaternion(q0); fwd.copy(cal.local).applyQuaternion(q0); fwd.y = 0; if (fwd.lengthSq() > 1e-4) return fwd.normalize(); }
      fwd.set(0, 0, 0);
      for (const s_ of ['L', 'R']) { const a = E.findBone(s_ + '_ankle_jntBnd'), t = E.findBone(s_ + '_toe_jntBnd'); if (a && t) { a.getWorldPosition(v); t.getWorldPosition(w); fwd.add(w.sub(v)); } }
      fwd.y = 0; return fwd.lengthSq() > 1e-6 ? fwd.normalize() : fwd.set(0, 0, 1);
    };
    return facing;
  }

  function setupThrow(d) {
    dropThrow(ctx);
    const cfg = THROW_FX[d.id]; if (!cfg) return;
    const V = ctx.viewer(); if (!V) return;
    const fx = new FlaskThrowFx(V.scene, { kind: cfg.kind, radius: cfg.radius, flaskUrl: '/api/model?path=' + encodeURIComponent(FLASK_MODEL) });
    const v = new THREE.Vector3(), w = new THREE.Vector3(), hip = new THREE.Vector3(), fwd = new THREE.Vector3();
    const releaseOf = clip => { const e = ((sfxData && sfxData.clips[clip]) || []).find(x => /\/Throw$/.test(x.event)); return e ? e.t : .33; };
    const facing = makeFacing();
    let prev = 0, holding = false;
    throwRun = {
      update(dt) {
        fx.update(dt);
        const cur = E.curClip && E.curClip[1];
        if (!cur || !/^throw_flask/.test(cur) || !E.action) { prev = 0; if (holding) { fx.release(); holding = false; } return; }
        const t = E.action.time, tr = releaseOf(cur);
        if (t < prev) { prev = 0; holding = false; }
        if (!holding && t < tr && fx.state !== 'fly') { fx.hold(E.findBone('R_wrist_jntBnd')); holding = true; }
        if (prev < tr && t >= tr) {
          holding = false; const hand = E.findBone('R_wrist_jntBnd'), hb = E.findBone('hip_jntBnd');
          hand.getWorldPosition(w); const from = w.clone(); hb.getWorldPosition(hip);
          const to = hip.clone().addScaledVector(facing(), fx.range); to.y = 0;
          fx.launch(from, to, () => fireArt(/\/Explode/i));
        }
        prev = t;
      },
      dispose() { fx.dispose(); },
    };
    V.pets = V.pets || []; V.pets.push(throwRun);
  }

  function setupSlam(d) {
    dropSlam(ctx);
    const cfg = SLAM_FX[d.id] || (AO_SLAM.has(d.id) ? { R: 2.6, tex: 'Art/particles/FXLib/PBR/1024x1024/G_KGB_DrySand01_colour.dds', tint: [1.15, .95, .75], ao: true } : null); if (!cfg) return;
    const imp = {};
    for (const a of d.anim || []) for (const c of a.events || []) { const e = (c.events || []).find(x => x.name === 'contact'); if (e) imp[c.name] = e.t; }
    if (!Object.keys(imp).length && !cfg.ao) return;
    const V = ctx.viewer(); if (!V) return;
    let aoFx = null, objFx = null; const objCfg = OBJ_FX[d.id], facing = objCfg ? makeFacing() : null;
    if (objCfg) petAsset(objCfg.pet).then(a => { if (a) objFx = new ObjectFx(V.scene, { ...objCfg, meshUrl: a.meshUrl, texUrl: a.texUrl }); });
    if (cfg.ao) { aoFx = new AoMeshFx(V.scene); const g = (d.art || [])[0]; aoFx.load(((g && g.items) || []).flatMap(it => it.files).filter(f => /\.ao$/i.test(f) && !/microtransactions/i.test(f))); }
    const url = p => '/api/icon?size=1024&path=' + encodeURIComponent(p);
    const fx = new GroundSlamFx(V.scene, url(cfg.tex), { R: cfg.R, tint: cfg.tint });
    if (cfg.spikes) fx.initSpikes(url(cfg.spikeTex), cfg.spikes);
    const v = new THREE.Vector3(), w = new THREE.Vector3(), hip = new THREE.Vector3();
    const spot = () => {   // lowest part of the held weapon = where it meets the ground
      const node = E.equip.weapon && E.equip.weapon.nodes && E.equip.weapon.nodes[0];
      E.root.updateWorldMatrix(true, true); let best = null;
      if (node && node.geometry) {
        node.updateWorldMatrix(true, false); const pos = node.geometry.attributes.position; let minY = 1e9; const pts = [];
        for (let i = 0; i < pos.count; i += 2) { v.fromBufferAttribute(pos, i).applyMatrix4(node.matrixWorld); pts.push(v.clone()); if (v.y < minY) minY = v.y; }
        const low = pts.filter(p => p.y < minY + .25); if (low.length) { best = new THREE.Vector3(); low.forEach(p => best.add(p)); best.divideScalar(low.length); }
      }
      if (!best) { const b = E.findBone && E.findBone('R_hand_jntBnd'); best = new THREE.Vector3(); if (b) b.getWorldPosition(best); }
      return best;
    };
    let prev = 0;
    slamRun = {
      update(dt) {
        fx.update(dt); if (aoFx) aoFx.update(dt); if (objFx) objFx.update(dt);
        const cur = E.curClip && E.curClip[1], t0 = cur && ((sfxData && sfxData.contacts && sfxData.contacts[cur]) ?? imp[cur]);
        if (t0 === undefined || !E.action) { prev = 0; return; }
        const t = E.action.time; if (t < prev) prev = 0;
        if (objFx && objFx.inner) {
          // real object: the burst happens where it lands
          const fall = objCfg.mode === 'fall', t1 = fall ? t0 - .38 : t0;
          if (prev < t1 && t >= t1) {
            const hb = E.findBone('hip_jntBnd'); hb.getWorldPosition(hip);
            const dir = facing().clone(), to = hip.clone().addScaledVector(dir, objCfg.range); to.y = 0;
            const land = () => { fx.useSurface(surfaceOf(V)); fx.trigger(to, dir); if (aoFx) aoFx.spawn(to, dir, cfg.R); fireArt(/\/(Slam|Impact|Explode)/i); };
            if (fall) objFx.drop(to, land); else { const hand = E.findBone('R_wrist_jntBnd'), from = new THREE.Vector3(); hand.getWorldPosition(from); objFx.throw(from, to, land); }
          }
          prev = t; return;
        }
        if (prev < t0 && t >= t0) {
          const p = spot(), hb = E.findBone && E.findBone('hip_jntBnd'); if (hb) hb.getWorldPosition(hip);
          const dir = new THREE.Vector3(p.x - hip.x, 0, p.z - hip.z).lengthSq() > .01 ? new THREE.Vector3(p.x - hip.x, 0, p.z - hip.z) : new THREE.Vector3(0, 0, 1);
          fx.useSurface(surfaceOf(V)); fx.trigger(p, dir); if (aoFx) aoFx.spawn(p, dir, cfg.R);
        }
        prev = t;
      },
      dispose() { fx.dispose(); if (aoFx) aoFx.dispose(); if (objFx) objFx.dispose(); },
    };
    V.pets = V.pets || []; V.pets.push(slamRun);
  }

  function show(d) {
    setupSlam(d); setupThrow(d); sfxD = d; dropSfx(ctx); dropSeq(ctx);
    hideSHov(); supTag = ''; curGem = d.gem; if ($('#sksup')) $('#sksup').innerHTML = supBlock(d.gem);
    const e0 = (d.effects || [])[0] || {};
    let tokens = (E.weaponTokens || ['unarmed']);
    const clips = [];
    for (const a of (d.form ? d.form.anim : d.anim) || []) for (const c of a.clips) clips.push({ ...c, state: a.state });
    const fits = c => tokens.some(tk => c.clip.includes('_' + tk + '_') || c.clip.includes('_' + tk));
    const exact = c => tokens.some(tk => new RegExp('(^|_)' + tk + '_\\d').test(c.clip));   // throw_flask_unarmed_01 beats throw_flask_claw_unarmed_01
    clips.sort((a, b) => (fits(b) - fits(a)) || (exact(b) - exact(a)) || (MOVE_ORDER(a.clip) - MOVE_ORDER(b.clip)) || (a.clip.length - b.clip.length) || a.clip.localeCompare(b.clip));
    const animHtml = () => {
      let last = '', h = '';
      const order = clips.map((c, i) => ({ c, i, tk: tokenOf(c.clip) }));
      order.sort((a, b) => (fits(a.c) ? 0 : 1) - (fits(b.c) ? 0 : 1) || String(a.tk).localeCompare(String(b.tk)));
      for (const o of order) {
        const lab = (o.tk ? TOKEN_LABEL[o.tk] : 'Общие') + (fits(o.c) ? ' — оружие персонажа' : '');
        if (lab !== last) { last = lab; h += `<div class="sec-head${fits(o.c) ? ' ok' : ''}">${esc(lab)}</div>`; }
        h += `<div class="row" data-i="${o.i}"><div>${esc(o.c.clip)}</div></div>`;
      }
      return h;
    };
    const lv = (e0.stats && e0.stats[0] && e0.stats[0].levels) || [];
    const lvls = (e0.levels || []);
    const firstTextLevels = (e0.stats || []).filter(s => s.levels.length);
    const maxL = lvls.length ? lvls[lvls.length - 1].level : 1;
    let level = Math.min(20, maxL), allLv = false, curveKey = null;
    const CURVE_LAB = { mult: 'Урон от атаки по уровню камня', dmg: 'Урон по уровню камня (средний)', cost: 'Стоимость маны по уровню камня', reservation: 'Резерв Spirit по уровню камня', actor: 'Уровень персонажа по уровню камня' };
    const CURVE_SHORT = { mult: 'Множитель', dmg: 'Урон', cost: 'Мана', reservation: 'Резерв', actor: 'Ур. персонажа' };
    const fmtV = v => (Math.abs(v) >= 100 ? String(Math.round(v)) : String(+v.toFixed(1)));
    const curveHtml = () => {
      const cv = (d.gem && d.gem.curve) || {}, keys = Object.keys(cv); if (!keys.length) return '';
      if (!curveKey || !cv[curveKey]) curveKey = keys[0];
      const pts = cv[curveKey].filter(p => allLv || p[0] <= 20), W = 300, H = 140, L0 = 38, R0 = 10, T0 = 12, B0 = 20;
      const lo = pts[0][0], hi = pts[pts.length - 1][0], vs = pts.map(p => p[1]), mn = Math.min(...vs), mx = Math.max(...vs);
      const X = l => L0 + (l - lo) / ((hi - lo) || 1) * (W - L0 - R0), Y = v => H - B0 - (v - mn) / ((mx - mn) || 1) * (H - B0 - T0);
      const cur = pts.find(p => p[0] === level) || pts[0];
      const ticks = [lo, 20, hi].filter((v, i, a) => v >= lo && v <= hi && a.indexOf(v) === i);
      return `<div class="gemblk crv"><b>${esc(CURVE_LAB[curveKey])}</b><div class="cb">${keys.map(k => `<button data-ck="${k}" class="${k === curveKey ? 'on' : ''}">${CURVE_SHORT[k]}</button>`).join('')}</div>
        <svg id="skcurve" viewBox="0 0 ${W} ${H}" role="img" aria-label="${EN() ? 'Curve: ' + ({ mult: 'Attack damage', dmg: 'Damage', cost: 'Mana', reservation: 'Reservation', actor: 'Char. level' })[curveKey] + ' by gem level' : 'Кривая: ' + esc(CURVE_SHORT[curveKey]) + ' по уровням камня'}">
          <line x1="${L0}" y1="${H - B0}" x2="${W - R0}" y2="${H - B0}" stroke="var(--line)"/><line x1="${L0}" y1="${T0}" x2="${L0}" y2="${H - B0}" stroke="var(--line)"/>
          ${ticks.map(t => `<line x1="${X(t)}" y1="${H - B0}" x2="${X(t)}" y2="${H - B0 + 3}" stroke="var(--dim)"/><text x="${X(t)}" y="${H - 6}" text-anchor="middle" font-size="12" fill="var(--dim)">${t}</text>`).join('')}
          <text x="${L0 - 4}" y="${T0 + 3}" text-anchor="end" font-size="12" fill="var(--dim)">${fmtV(mx)}</text><text x="${L0 - 4}" y="${H - B0}" text-anchor="end" font-size="12" fill="var(--dim)">${fmtV(mn)}</text>
          ${20 >= lo && 20 <= hi ? `<line x1="${X(20)}" y1="${T0}" x2="${X(20)}" y2="${H - B0}" stroke="var(--line)" stroke-dasharray="3 3"/>` : ''}
          <path d="${pts.map((p, i) => (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1)).join(' ')}" fill="none" stroke="#7F77DD" stroke-width="2"/>
          <circle cx="${X(cur[0])}" cy="${Y(cur[1])}" r="4" fill="#7F77DD"/><text x="${Math.min(X(cur[0]) + 6, W - 60)}" y="${Math.max(Y(cur[1]) - 6, 10)}" font-size="10" fill="var(--text)">${EN() ? 'lv.' : 'ур.'} ${cur[0]} · ${fmtV(cur[1])}</text>
          <rect x="${L0}" y="${T0}" width="${W - L0 - R0}" height="${H - B0 - T0}" fill="transparent" style="cursor:pointer"/>
        </svg><div class="kv">Клик по графику выбирает уровень · ${allLv ? 'уровни 1–' + hi : 'уровни 1–20'}</div></div>`;
    };
    const levelTable = () => {
      const shown = lvls.filter(x => allLv || x.level <= 20);
      const NUM = /-?\d+(?:[.,]\d+)?/g;
      const lines = L => [...new Set(firstTextLevels.map(st => { const z = st.levels.find(y => y.level === L); return z ? stxt(z).map(plain) : []; }).flat())];
      // only the stats whose numbers change between levels get a column; a cell holds just the numbers ("8 – 12")
      const cols = new Map();
      shown.forEach(x => lines(x.level).forEach(t => {
        const tpl = t.replace(NUM, '#'); let c = cols.get(tpl); if (!c) cols.set(tpl, c = { tpl, vals: new Map(), texts: new Set() });
        if (!c.vals.has(x.level)) c.vals.set(x.level, (t.match(NUM) || []).join(' – '));
        c.texts.add(t);
      }));
      const ch = [...cols.values()].filter(c => c.texts.size > 1);
      const short = t => { const u = t.replace(/\s*#\s*/g, ' # ').replace(/\s+/g, ' ').trim(); return u.length > 34 ? u.slice(0, 33) + '…' : u; };
      const spirit = shown.some(x => x.reservation), hasCost = shown.some(x => x.cost && x.cost.length);
      return `<h4>Таблица уровней (${shown.length} из ${lvls.length})</h4><div class="lvw"><table class="lvt"><tr><th>Ур.</th>${hasCost || spirit ? `<th>${spirit ? 'Spirit / мана' : 'Мана'}</th>` : ''}${ch.map(c => `<th title="${esc(c.tpl.replace(/#/g, '…'))}">${esc(short(c.tpl))}</th>`).join('')}</tr>${shown.map(x => `<tr data-lv="${x.level}" class="${x.level === level ? 'on' : ''}"><td>${x.level}</td>${hasCost || spirit ? `<td>${[x.reservation ? 'резерв ' + x.reservation : '', x.cost && x.cost.length ? x.cost.join('/') : ''].filter(Boolean).join(' · ')}</td>` : ''}${ch.map(c => `<td>${esc(c.vals.get(x.level) ?? '')}</td>`).join('')}</tr>`).join('')}</table></div>${ch.length ? '' : '<div class="kv">Параметры умения не зависят от уровня камня.</div>'}${lvls.length > shown.length || allLv ? `<button id="sklvall" style="margin-top:4px">${allLv ? 'Только 1–20' : 'Показать все ' + lvls.length}</button>` : ''}`;
    };
    const art = (d.art || []).flatMap(g => g.items.map(it => ({ ...it, group: g.id })));
    const um = t => esc(t).replace(/\u27e6(.*?)\u27e7/g, '<u>$1</u>').replace(/\[([^\]|]+)\|([^\]]+)\]/g, '<u>$2</u>').replace(/\[([^\]]+)\]/g, '<u>$1</u>');
    const plain = t => String(t).replace(/[\u27e6\u27e7]/g, '');
    const hiNum = t => um(t).replace(/(-?\d[\d.,]*\s?%?)/g, '<b class="num">$1</b>');
    const tiles = li => {
      const sl = (firstTextLevels.find(st => st.levels.find(z => z.level === level && z.mult != null)) || firstTextLevels[0] || { levels: [] }).levels.find(z => z.level === level) || {};
      const lines = firstTextLevels.map(st => { const z = st.levels.find(y => y.level === level); return z ? stxt(z) : []; }).flat();
      const isAtk = ((d.gem && d.gem.tags) || []).includes('Attack');
      let dmg = ''; for (const t of lines) { dmg = dmgOf(t); if (dmg) break; }
      const f = v => String(+v.toFixed(2)).replace('.', EN() ? '.' : ',');
      const KV = (k, v, key) => v ? `<div class="kvl${key ? ' key' : ''}"><span>${k}:</span> ${v}</div>` : '';
      const wr = groupsOf(d.weapons || ''), wtxt = wr.includes('Без требований к оружию') ? '' : wr.join(', ');
      const req = d.gem && d.gem.req ? ['str', 'dex', 'int'].filter(a => d.gem.req[a]).map(a => ATTR_RU[a]).join(', ') : '';
      const supG = d.gem && (d.gem.kind === 'support' || d.gem.kind === 'lineage');
      if (supG) {
        const fam = (EN() ? (d.gem.family || []) : (d.gem.family_ru && d.gem.family_ru.length ? d.gem.family_ru : d.gem.family || [])).join(', ');
        return `<div class="kvb">${KV('<u>Категория</u>', fam ? `<b>${esc(fam)}</b>` : '')}${KV('<u>Множитель расхода ресурсов</u>', li.cost_mult ? `<b>${li.cost_mult}%</b>` : '', true)}${KV('Требуется', d.gem.minlvl ? `<b>Уровень ${d.gem.minlvl}</b>` : '')}${KV('Выпадает с', dropsOf(d.gem))}${KV('<u>Требования камней поддержки</u>', req ? `<b>${esc(req)}</b>` : '')}</div>`;
      }
      return `<div class="kvb">${KV('Уровень', `<b>${level}</b>`)}${KV(li.reservation ? 'Резерв' : 'Расход ресурсов', li.reservation ? `<b>${li.reservation}</b> духа` : (li.cost && li.cost[0] ? `<b>${li.cost[0]}</b> маны` : ''), true)}${KV('Множитель расхода маны', d.gem && (d.gem.kind === 'support' || d.gem.kind === 'lineage') && li.cost_mult ? `<b>${li.cost_mult}%</b>` : '', true)}${KV('Скорость атаки', isAtk && li.atk_speed != null ? `<b>${100 + li.atk_speed}%</b> от базовой` : '', true)}${KV('Урон от атаки', isAtk && sl.mult != null ? `<b>${f(100 + sl.mult / 100)}%</b>` : '', true)}${KV('Урон', !isAtk && dmg ? `<b>${dmg}</b>` : '', true)}${KV('Время применения', !isAtk && e0.cast_time ? `<b>${f(e0.cast_time / 1000)}</b> с` : '')}${KV('Шанс крита', !isAtk && sl.crit ? `<b>${f(sl.crit / 100)}%</b>` : '')}${KV('Перезарядка', li.cooldown ? `<b>${f(li.cooldown / 1000)}</b> с` : '')}${KV('Требуется атрибут', req)}${KV('Требуется', wtxt)}</div>`;
    };
    const html = () => {
      const li = lvls.find(x => x.level === level) || {};
      const txt = [...new Set(firstTextLevels.map(st => { const x = st.levels.find(z => z.level === level); return x ? stxt(x) : []; }).flat())].map(hiNum).join('<hr>');
      return `${d.gem && d.gem.ui_image ? `<div class="gbg" style="background-image:url('/api/icon?size=1024&path=${encodeURIComponent(d.gem.ui_image)}')"></div>` : ''}<div class="skill-head"><img width="72" height="72" src="/api/icon?size=128&path=${encodeURIComponent(d.icon)}" style="object-fit:contain;border-radius:12px" onerror="this.style.visibility='hidden'"><div><div class="name">${esc(EN() ? (d.name || d.ru) : (d.ru || d.name))}</div><div class="ktype">${esc((d.gem ? typeOf(d.gem) : '') || (d.gem ? (d.gem.kind === 'support' || d.gem.kind === 'lineage' ? 'Поддержка' : KIND_FULL[d.gem.kind]) : ''))}</div><div class="sub">${EN() ? '' : esc(d.name)}</div></div></div>
      ${d.gem ? tagLine(d.gem) : `<div class="tags">${esc(clean((e0.tags || []).join(' · ')))}</div>`}
      ${tiles(li)}
      ${srcItemsHtml(d)}
      <div class="lead">${um(EN() ? (d.description || d.description_ru || '') : (d.description_ru || d.description || ''))}</div>
      <div class="lvbar"><span class="lvn">ур. <b id="sklv">${level}</b></span><input id="skl" aria-label="Уровень камня" type="range" min="1" max="${maxL}" value="${level}"></div>
      <div class="stats">${txt || '<span class="kv">Нет описания параметров</span>'}</div>
      ${qualityHtml(d.gem)}
      ${supExtras(d.gem)}
      ${curveHtml()}
      ${lvls.length ? levelTable() : ''}`;
    };
    const render = () => {
      $('#skdetail').innerHTML = html();
      $('#skl').oninput = ev => { level = +ev.target.value; render(); };
      document.querySelectorAll('.crv .cb button').forEach(b => { b.onclick = () => { curveKey = b.dataset.ck; render(); }; });
      const cs = $('#skcurve'); if (cs) cs.onclick = ev => {
        const rc = cs.getBoundingClientRect(), pts = d.gem.curve[curveKey].filter(p => allLv || p[0] <= 20), lo = pts[0][0], hi = pts[pts.length - 1][0];
        const x = (ev.clientX - rc.left) / rc.width * 300, l = Math.round(lo + (x - 38) / (300 - 38 - 10) * (hi - lo));
        level = Math.max(lo, Math.min(hi, l)); render();
      };
      document.querySelectorAll('.lvt tr[data-lv]').forEach(r => { r.onclick = () => { level = +r.dataset.lv; render(); }; });
      if ($('#sklvall')) $('#sklvall').onclick = () => { allLv = !allLv; render(); };
      if ($('#skanims')) $('#skanims').onclick = async ev => {
        const r = ev.target.closest('.row'); if (!r) return;
        document.querySelectorAll('#skanims .row.on').forEach(x => x.classList.remove('on')); r.classList.add('on');
        const c = clips[r.dataset.i];
        try { await E.play(c.ast, c.clip); status(c.clip); drawSfx(); } catch (err) { status('Анимация: ' + err.message); }
      };
    };
    render(); if (!d.noAnim) loadSfx(d);
    // the standard animation of the skill for the character's weapon; when it is a series (attack_01, attack_02 …) the series is played in a loop
    const still = c => !/moving/.test(c.clip);
    let seq = [], si = 0, sprev = 0, sbusy = false;
    const buildSeq = async () => {
      tokens = (E.weaponTokens || ['unarmed']);
      const others = Object.keys(TOKEN_LABEL).filter(k => !tokens.includes(k)), pure = c => !others.some(k => c.clip.includes('_' + k + '_') || c.clip.endsWith('_' + k));   // clips of another weapon (claw_unarmed for an unarmed hero) are not mixed in
      seq = clips.filter(c => exact(c) && still(c) && pure(c));
      if (!seq.length) seq = clips.filter(c => exact(c) && still(c));
      if (!seq.length) seq = clips.filter(c => fits(c) && still(c));
      if (!seq.length && clips.length) seq = [clips[0]];
      if (d.form) seq = clips.filter(still);   // a form has no weapon variants: every clip of the skill, in order
      // weapon clips are named attack_<weapon>_<off-hand>_NN: keep the ones for what the hero holds in the left hand
      const oh = E.equip.offhand && E.equip.offhand.item, offTok = !oh ? 'unarmed' : oh.class === 'Shields' ? 'shield' : oh.class === 'Bucklers' ? 'buckler' : oh.class === 'Sceptres' ? 'sceptre' : tokens[0];
      const two = c => /^attack_[a-z0-9]+_[a-z0-9]+_\d/.test(c.clip), byOff = seq.filter(c => two(c) && c.clip.split('_')[2] === offTok);
      if (byOff.length) seq = byOff;
      seq = seq.filter((c, i, a) => a.findIndex(x => x.clip === c.clip) === i).slice(0, 12);
      // the numbered variants of one animation (…_01, _02, _03 …) are the same move played faster for high attack speed: keep the base one, drop the shorter repeats
      const dur = {}; for (const c of seq) { try { dur[c.clip] = (await E.clipFor(c.ast, c.clip)).duration; } catch (e) { /* unreadable: keep */ } }
      const stem = c => c.clip.replace(/_(\d+)([a-z]?)(?=_|$)/, '_#$2'), num = c => +((/_(\d+)[a-z]?(?=_|$)/.exec(c.clip) || [0, 0])[1]);
      const base = {}; seq.slice().sort((x, y) => num(x) - num(y)).forEach(c => { const k = stem(c); if (!(k in base)) base[k] = dur[c.clip]; });
      seq = seq.filter(c => { const k = stem(c); return !(base[k] && dur[c.clip] && dur[c.clip] < base[k] * 0.92); }).slice(0, 8);
      const rank = c => /start|windup|begin/.test(c.clip) ? 0 : /loop/.test(c.clip) ? 1 : /end|finish|recover/.test(c.clip) ? 3 : 2;
      seq = seq.map((c, i) => [c, i]).sort((x, y) => rank(x[0]) - rank(y[0]) || x[1] - y[1]).map(x => x[0]);
    };
    const go = async i => {
      si = i % seq.length; sbusy = true;
      try { await E.play(seq[si].ast, seq[si].clip); status(seq[si].clip + (seq.length > 1 ? ` (${si + 1} из ${seq.length})` : '')); }
      catch (err) { status('Анимация: ' + err.message); }
      sbusy = false; sprev = 0;
    };
    ensureActor(d).then(async () => {
      if (sfxD !== d) return;   // another skill was picked while the model loaded
      await applyCategoryWeapon(d);
      if (sfxD !== d) return;
      await buildSeq();
      if (sfxD !== d || !seq.length) return;
      go(0);
      const V = ctx.viewer();
      if (seq.length > 1 && V) {
        seqRun = { update() { if (sbusy || !E.action || !$('#skdetail') || $('#skmid').hidden) return; const t = E.action.time; if (t < sprev - 1e-3) go(si + 1); sprev = t; }, dispose() {} };
        V.pets = V.pets || []; V.pets.push(seqRun);
      }
    }).catch(err => status('Форма: ' + err.message));
  }
  list();
  // the interface language changed: redraw the lists and the open card with the data of the other language
  if (window.__skLang) window.removeEventListener('i18n:change', window.__skLang);
  window.__skLang = () => {
    if (!$('#skq')) { window.removeEventListener('i18n:change', window.__skLang); return; }
    hideHov(); drawSide(); drawChips(); drawTags(); list();
    if (lastRow && $('#skdetail') && $('#skdetail').children.length) openRow(lastRow);
  };
  window.addEventListener('i18n:change', window.__skLang);
}
