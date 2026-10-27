"""Section "Свойства" (Modifiers): every row of the Mods table with its readable text (EN/RU), tier, tags and spawn weights."""
import json, os, re
from . import skills
from .datrows import table, ROOT

DOMAINS = ['ITEM', 'FLASK', 'MONSTER', 'CHEST', 'AREA', None, 'SANCTUM_RELIC', None, 'CRAFTED', 'BASE_JEWEL', 'ATLAS', 'LEAGUESTONE', 'ABYSS_JEWEL', 'MAP_DEVICE', 'DUMMY', 'DELVE', 'DELVE_AREA', 'SYNTHESIS_A',
           'SYNTHESIS_GLOBALS', 'SYNTHESIS_BONUS', 'AFFLICTION_JEWEL', 'HEIST_AREA', 'HEIST_NPC', 'HEIST_TRINKET', 'WATCHSTONE', 'VEILED', 'EXPEDITION_RELIC', 'UNVEILED', 'ELDRITCH_ALTAR', 'SENTINEL', 'MEMORY_LINE',
           'SANCTUM_SPECIAL', 'CRUCIBLE_MAP', 'TINCTURE', 'ANIMAL_CHARM', 'NECROPOLIS_MONSTER', 'IDOL', 'GRAFT']
GENS = ['PREFIX', 'SUFFIX', 'UNIQUE', 'NEMESIS', 'CORRUPTED', 'BLOODLINES', 'TORMENT', 'TEMPEST', 'TALISMAN', 'ENCHANTMENT', 'ESSENCE', None, 'BESTIARY', 'DELVE_AREA', 'SYNTHESIS_A', 'SYNTHESIS_GLOBALS',
        'SYNTHESIS_BONUS', 'BLIGHT', 'BLIGHT_TOWER', 'MONSTER_AFFLICTION', 'FLASK_ENCHANTMENT_ENKINDLING', 'FLASK_ENCHANTMENT_INSTILLING', 'EXPEDITION_LOGBOOK', 'SCOURGE_UPSIDE', 'SCOURGE_DOWNSIDE', 'SCOURGE_MAP']
DOMAIN_RU = {'ITEM': 'Предметы', 'FLASK': 'Флаконы', 'MONSTER': 'Монстры', 'CHEST': 'Сундуки', 'AREA': 'Зоны', 'SANCTUM_RELIC': 'Реликвии Святилища', 'CRAFTED': 'Верстак', 'BASE_JEWEL': 'Самоцветы',
             'ATLAS': 'Атлас', 'LEAGUESTONE': 'Камни лиг', 'ABYSS_JEWEL': 'Самоцветы Бездны', 'MAP_DEVICE': 'Картограф', 'WATCHSTONE': 'Хранители', 'EXPEDITION_RELIC': 'Реликвии Экспедиции',
             'TINCTURE': 'Настойки', 'IDOL': 'Идолы', 'SENTINEL': 'Стражи', 'SANCTUM_SPECIAL': 'Святилище', 'UNVEILED': 'Раскрытые', 'VEILED': 'Скрытые'}
GEN_RU = {'PREFIX': 'Префикс', 'SUFFIX': 'Суффикс', 'UNIQUE': 'Уникальное', 'NEMESIS': 'Немезида', 'CORRUPTED': 'Осквернённое', 'ESSENCE': 'Эссенция', 'ENCHANTMENT': 'Зачарование', 'TALISMAN': 'Талисман',
          'BESTIARY': 'Бестиарий', 'BLIGHT': 'Скверна', 'EXPEDITION_LOGBOOK': 'Журнал Экспедиции'}
CSD = ["stat_descriptions", "map_stat_descriptions", "atlas_stat_descriptions", "chest_stat_descriptions", "monster_stat_descriptions", "endgame_map_stat_descriptions", "tablet_stat_descriptions",
       "sanctum_relic_stat_descriptions", "expedition_relic_stat_descriptions", "utility_flask_buff_stat_descriptions", "leaguestone_stat_descriptions", "passive_skill_stat_descriptions", "advanced_mod_stat_descriptions"]
CACHE = os.path.join(ROOT, "cache", "mods_v1.json")
_mem = {}
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _csd(store):
    out = {}
    for n in CSD:
        for k, v in skills.parse_csd(store, f"data/statdescriptions/{n}.csd").items():
            out.setdefault(k, v)
    return out


def _render(csd, sids, lo, hi, lang):
    """One text line per description; a (min-max) range replaces every number that differs between the min and max roll."""
    lines, used = [], set()
    for sid in sids:
        if sid in used or sid not in csd:
            continue
        ent = next((e for e in csd[sid] if set(e[0]) <= set(sids)), csd[sid][0])
        used.update(ent[0])
        stub = {sid: [ent]}
        a = skills.render_stat(stub, sid, {k: lo.get(k, 0) for k in ent[0]}, lang)
        b = skills.render_stat(stub, sid, {k: hi.get(k, 0) for k in ent[0]}, lang)
        if a is None:
            continue
        if a != b and b is not None:
            ta, tb = NUM.findall(a), NUM.findall(b)
            if len(ta) == len(tb):
                parts, it = [], iter(zip(ta, tb))
                last = 0
                for m in NUM.finditer(a):
                    x, y = next(it)
                    parts.append(a[last:m.start()]); last = m.end()
                    parts.append(x if x == y else f"({x}–{y})")
                parts.append(a[last:]); a = "".join(parts)
        lines.append(a)
    return lines


def _clean(n):
    """Russian names carry gender variants: <if:MS>{Опасный}<elif:FS>{Опасная}… -> the first one."""
    m = re.match(r"<if:\w+>\{([^}]*)\}", n or "")
    return m.group(1) if m else (n or "")


def build(store):
    t_en, t_ru = table(store, "mods"), table(store, "mods", "russian")
    st, tg, mt, fam = table(store, "stats"), table(store, "tags"), table(store, "modtype"), table(store, "modfamily")
    csd = _csd(store)
    sid_of = lambda r: st.get(r, "Id")
    tag_of = lambda r: tg.get(r, "Id")
    out = []
    for i in range(len(t_en)):
        r = t_en.row(i)
        sids, lo, hi = [], {}, {}
        for n in range(1, 9):
            ref = r.get(f"Stat{n}")
            if ref is None:
                continue
            s = sid_of(ref); sids.append(s); lo[s] = r.get(f"Stat{n}Min") or 0; hi[s] = r.get(f"Stat{n}Max") or 0
        stats = [[s, lo[s], hi[s]] for s in sids]
        spawn = [[tag_of(a), w] for a, w in zip(r.get("SpawnWeight_Tags") or [], r.get("SpawnWeight_Values") or []) if w and a is not None]
        dom = DOMAINS[r["Domain"] - 1] if r.get("Domain") and 0 < r["Domain"] <= len(DOMAINS) else None
        gen = GENS[r["GenerationType"] - 1] if r.get("GenerationType") and 0 < r["GenerationType"] <= len(GENS) else None
        fams = [fam.get(f, "Id") for f in (r.get("Families") or []) if f is not None]
        out.append({"i": i, "id": r["Id"], "name": r.get("Name") or "", "name_ru": _clean(t_ru.get(i, "Name")), "type": mt.get(r["ModType"], "Name") if r.get("ModType") is not None else "",
                    "domain": dom, "gen": gen, "level": r.get("Level") or 0, "max_level": r.get("MaxLevel") or 0, "families": fams,
                    "tags": [tag_of(a) for a in (r.get("Tags") or []) if a is not None], "spawn": spawn, "stats": stats,
                    "text": _render(csd, sids, lo, hi, "en"), "text_ru": _render(csd, sids, lo, hi, "Russian")})
    return out


def all_mods(store):
    if "m" in _mem:
        return _mem["m"]
    if os.path.exists(CACHE):
        _mem["m"] = json.load(open(CACHE, encoding="utf-8"))
    else:
        _mem["m"] = build(store)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(_mem["m"], open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return _mem["m"]


def facets(store):
    ms = all_mods(store); d, g, tags = {}, {}, {}
    for m in ms:
        d[m["domain"]] = d.get(m["domain"], 0) + 1; g[m["gen"]] = g.get(m["gen"], 0) + 1
        for t, _w in m["spawn"]:
            tags[t] = tags.get(t, 0) + 1
    return {"domains": [{"k": k, "n": n, "ru": DOMAIN_RU.get(k, k)} for k, n in sorted(d.items(), key=lambda x: -x[1]) if k],
            "gens": [{"k": k, "n": n, "ru": GEN_RU.get(k, k)} for k, n in sorted(g.items(), key=lambda x: -x[1]) if k],
            "tags": [{"k": k, "n": n} for k, n in sorted(tags.items(), key=lambda x: -x[1])[:120]], "total": len(ms)}


def search(store, q="", domain="", gen="", tag="", limit=100, offset=0, lang="ru"):
    ms = all_mods(store); ql = q.lower().strip(); out = []
    for m in ms:
        if domain and m["domain"] != domain or gen and m["gen"] != gen:
            continue
        if tag and not any(t == tag for t, _w in m["spawn"]):
            continue
        if ql and ql not in (m["id"] + " " + m["name"] + " " + m["name_ru"] + " " + " ".join(m["text"]) + " " + " ".join(m["text_ru"]) + " " + m["type"] + " " + " ".join(s[0] for s in m["stats"])).lower():
            continue
        out.append(m)
    go = {"PREFIX": 0, "SUFFIX": 1}
    out.sort(key=lambda m: (m["domain"] != "ITEM", go.get(m["gen"], 2), m["type"], m["level"]))
    return {"total": len(out), "rows": [dict(m, spawn=m["spawn"][:6]) for m in out[offset:offset + limit]]}


def detail(store, mid):
    ms = all_mods(store); m = next((x for x in ms if x["id"] == mid), None)
    if not m:
        return None
    sib = [x for x in ms if x["type"] == m["type"] and x["domain"] == m["domain"] and x["gen"] == m["gen"] and x["id"] != m["id"]]
    sib.sort(key=lambda x: x["level"])
    return dict(m, siblings=[{"id": x["id"], "level": x["level"], "text": x["text"], "text_ru": x["text_ru"], "name": x["name"], "name_ru": x["name_ru"]} for x in sib])
