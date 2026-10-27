"""Section "Свойства", item-type view: which prefixes/suffixes can roll on which item class (and base group, e.g. STR/DEX/INT armour), with weights."""
import json, os, re
from . import mods
from .datrows import table, ROOT

_W = ['weapon']
CLS = {  # item class id -> (category, Russian name, implicit tags mods can spawn on; base tags come from BaseItemTypes)
    'Bow': ('2h', 'Луки', _W + ['bow', 'ranged', 'two_hand_weapon']), 'Crossbow': ('2h', 'Арбалеты', _W + ['crossbow', 'ranged', 'two_hand_weapon']),
    'Staff': ('2h', 'Посохи', _W + ['staff', 'two_hand_weapon']), 'Warstaff': ('2h', 'Боевые посохи', _W + ['warstaff', 'two_hand_weapon']),
    'Two Hand Axe': ('2h', 'Двуручные топоры', _W + ['axe', 'two_hand_weapon']), 'Two Hand Mace': ('2h', 'Двуручные булавы', _W + ['mace', 'two_hand_weapon']),
    'Two Hand Sword': ('2h', 'Двуручные мечи', _W + ['sword', 'two_hand_weapon']), 'Talisman': ('2h', 'Талисманы', _W + ['talisman', 'two_hand_weapon']),
    'TrapTool': ('2h', 'Ловушки', _W + ['trap', 'two_hand_weapon']), 'FishingRod': ('2h', 'Удочки', _W + ['fishing_rod', 'two_hand_weapon']),
    'Wand': ('1h', 'Жезлы', _W + ['wand', 'one_hand_weapon']), 'Sceptre': ('1h', 'Скипетры', _W + ['sceptre', 'one_hand_weapon']), 'Claw': ('1h', 'Когти', _W + ['claw', 'one_hand_weapon']),
    'Dagger': ('1h', 'Кинжалы', _W + ['dagger', 'one_hand_weapon']), 'Flail': ('1h', 'Цепы', _W + ['flail', 'one_hand_weapon']), 'Spear': ('1h', 'Копья', _W + ['spear', 'one_hand_weapon']),
    'One Hand Axe': ('1h', 'Одноручные топоры', _W + ['axe', 'one_hand_weapon']), 'One Hand Mace': ('1h', 'Одноручные булавы', _W + ['mace', 'one_hand_weapon']),
    'One Hand Sword': ('1h', 'Одноручные мечи', _W + ['sword', 'one_hand_weapon']),
    'Body Armour': ('arm', 'Нательная броня', ['armour', 'body_armour']), 'Helmet': ('arm', 'Шлемы', ['armour', 'helmet']), 'Gloves': ('arm', 'Перчатки', ['armour', 'gloves']),
    'Boots': ('arm', 'Ботинки', ['armour', 'boots']),
    'Shield': ('off', 'Щиты', ['armour', 'shield']), 'Buckler': ('off', 'Баклеры', ['armour', 'shield']), 'Focus': ('off', 'Фокусы', ['armour', 'focus']), 'Quiver': ('off', 'Колчаны', ['quiver']),
    'Amulet': ('jew', 'Амулеты', ['amulet']), 'Ring': ('jew', 'Кольца', ['ring']), 'Belt': ('jew', 'Пояса', ['belt']),
    'LifeFlask': ('fl', 'Флаконы здоровья', []), 'ManaFlask': ('fl', 'Флаконы маны', []), 'UtilityFlask': ('fl', 'Обереги', []),
    'Jewel': ('oth', 'Самоцветы', ['jewel']), 'Map': ('oth', 'Путевые камни', []), 'Relic': ('oth', 'Реликвии', [])}
CATS = [('2h', 'Двуручное оружие'), ('1h', 'Одноручное оружие'), ('arm', 'Броня'), ('off', 'Щиты, фокусы, колчаны'), ('jew', 'Бижутерия'), ('fl', 'Флаконы и обереги'), ('oth', 'Прочее')]
COSMETIC = {'ezomyte_basetype', 'maraketh_basetype', 'karui_basetype', 'vaal_basetype', 'runeforged', 'not_for_sale', 'demigods', 'breachstone'}
TAG_RU = {'str_armour': 'Сила', 'dex_armour': 'Ловкость', 'int_armour': 'Интеллект', 'str_dex_armour': 'Сила/Ловкость', 'str_int_armour': 'Сила/Интеллект', 'dex_int_armour': 'Ловкость/Интеллект',
          'str_dex_int_armour': 'Сила/Ловкость/Интеллект', 'fire_implicit_skill': 'Огонь', 'cold_implicit_skill': 'Холод', 'lightning_implicit_skill': 'Молния',
          'chaos_implicit_skill': 'Хаос', 'physical_implicit_skill': 'Физика'}
CLS_EN = {'Bow': 'Bows', 'Crossbow': 'Crossbows', 'Staff': 'Staves', 'Warstaff': 'Quarterstaves', 'Two Hand Axe': 'Two Hand Axes', 'Two Hand Mace': 'Two Hand Maces',
          'Two Hand Sword': 'Two Hand Swords', 'Talisman': 'Talismans', 'TrapTool': 'Traps', 'FishingRod': 'Fishing Rods', 'Wand': 'Wands', 'Sceptre': 'Sceptres', 'Claw': 'Claws',
          'Dagger': 'Daggers', 'Flail': 'Flails', 'Spear': 'Spears', 'One Hand Axe': 'One Hand Axes', 'One Hand Mace': 'One Hand Maces', 'One Hand Sword': 'One Hand Swords',
          'Body Armour': 'Body Armours', 'Helmet': 'Helmets', 'Gloves': 'Gloves', 'Boots': 'Boots', 'Shield': 'Shields', 'Buckler': 'Bucklers', 'Focus': 'Foci', 'Quiver': 'Quivers',
          'Amulet': 'Amulets', 'Ring': 'Rings', 'Belt': 'Belts', 'LifeFlask': 'Life Flasks', 'ManaFlask': 'Mana Flasks', 'UtilityFlask': 'Charms', 'Jewel': 'Jewels', 'Map': 'Waystones', 'Relic': 'Relics'}
CATS_EN = {'2h': 'Two-Handed Weapons', '1h': 'One-Handed Weapons', 'arm': 'Armour', 'off': 'Shields, Foci, Quivers', 'jew': 'Jewellery', 'fl': 'Flasks and Charms', 'oth': 'Other'}
SEC_EN = {'base': 'Base', 'minion': 'Genesis Tree Minion', 'caster': 'Genesis Tree Caster', 'ow': 'Otherworldly'}
CACHE = os.path.join(ROOT, "cache", "mod_bases_v3.json")
_mem = {}


SECTIONS = [('base', 'Базовый'), ('minion', 'Дерево зарождения Приспешник'), ('caster', 'Дерево зарождения Чародейский'), ('ow', 'Потусторонние')]
GENESIS = {'genesis_tree_minion': 1, 'genesis_tree_caster': 2}
NUM = re.compile(r"\(-?[\d.]+[–-]-?[\d.]+\)|-?\d+(?:\.\d+)?")


def _attr(sig):
    return '_'.join(t[:-len('_armour')] for t in sig if t.endswith('_armour'))


def _label(sig):
    keep = [t for t in sig if t in TAG_RU]
    return ' · '.join(TAG_RU[t] for t in keep) if keep else 'Обычные'


def _build(store):
    ms = mods.all_mods(store)
    t, tg = table(store, "mods"), table(store, "tags")
    tagname = {}
    nm = lambda a: tagname.setdefault(a, tg.get(a, "Id"))
    ru_tg = table(store, "tags", "russian")
    modtags = {m["i"]: [] for m in ms}
    for m in ms:
        if m["gen"] in ("PREFIX", "SUFFIX") and m["domain"] in ("ITEM", "UNVEILED"):
            modtags[m["i"]] = [[tg.get(a, "Id"), ru_tg.get(a, "DisplayString"), tg.get(a, "DisplayString")] for a in (t.row(m["i"]).get("ImplicitTags") or []) if a is not None and ru_tg.get(a, "DisplayString")]
    by_dom = {}   # the full ordered spawn list is needed here: a weight-0 entry blocks later tags, but mods.py drops zero weights
    for m in ms:
        if m["gen"] in ("PREFIX", "SUFFIX"):
            r = t.row(m["i"])
            sp = [(nm(a), w) for a, w in zip(r.get("SpawnWeight_Tags") or [], r.get("SpawnWeight_Values") or []) if a is not None]
            by_dom.setdefault(m["domain"], []).append((m["i"], sp))
    bt, btr, ic = table(store, "baseitemtypes"), table(store, "baseitemtypes", "russian"), table(store, "itemclasses")
    groups = {}
    for i in range(len(bt)):
        r = bt.row(i)
        if r.get("ItemClass") is None or not r.get("Name") or r["Name"].startswith("[DNT]") or not r.get("ModDomain") or not 0 < r["ModDomain"] <= len(mods.DOMAINS):
            continue
        cid = ic.get(r["ItemClass"], "Id")
        if cid not in CLS:
            continue
        tags = {nm(a) for a in (r.get("Tags") or []) if a is not None}
        extra = set(GENESIS) if CLS[cid][0] not in ("fl", "oth") else set()
        g = groups.setdefault((cid, mods.DOMAINS[r["ModDomain"] - 1], tuple(sorted(tags - COSMETIC))), {"bases": [], "tags": tags | set(CLS[cid][2]) | {"default"} | extra})
        g["bases"].append([mods._clean(btr.get(i, "Name")) or r["Name"], r["Name"]])
    out = {}
    for (cid, dom, sig), g in groups.items():
        res = []
        for d2 in ([dom, "UNVEILED"] if dom == "ITEM" and CLS[cid][0] not in ("fl", "oth") else [dom]):
            for mi, sp in by_dom.get(d2, []):
                for tag, w in sp:
                    if tag in g["tags"]:
                        if w > 0:
                            res.append([mi, GENESIS.get(tag, 3 if d2 == "UNVEILED" else 0)])
                        break
        if not res:
            continue
        c = out.setdefault(cid, {"cat": CLS[cid][0], "ru": CLS[cid][1], "groups": []})
        same = next((x for x in c["groups"] if x["mods"] == res), None)
        if same:
            same["bases"] += g["bases"]
        else:
            c["groups"].append({"label": _label(sig), "attr": _attr(sig), "bases": g["bases"], "mods": res})
    for c in out.values():
        for x in c["groups"]:
            x["bases"] = sorted({(a, b) for a, b in x["bases"]})
            x["bases"] = [[a, b] for a, b in x["bases"]]
    out["_tags"] = {str(i): v for i, v in modtags.items() if v}
    return out


def _index(store):
    if "ix" not in _mem:
        if os.path.exists(CACHE) and os.path.getmtime(CACHE) >= os.path.getmtime(mods.CACHE):
            _mem["ix"] = json.load(open(CACHE, encoding="utf-8"))
        else:
            _mem["ix"] = _build(store)
            json.dump(_mem["ix"], open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return _mem["ix"]


def _icons(store):
    if "ic" not in _mem:
        ic = table(store, "itemclasses")
        names = {ic.get(i, "Id"): ic.get(i, "Name") for i in range(len(ic))}
        out = {}
        for cid in CLS:
            r = store.db.execute("select icon from items where class=? and icon is not null and icon not like '%Demigod%' and icon not like '%Unique%' order by rowid limit 1", (names.get(cid),)).fetchone()
            if r:
                out[cid] = r[0]
        _mem["ic"] = out
    return _mem["ic"]


def bases(store):
    ix = _index(store); cats = []; icons = _icons(store)
    for k, ru in CATS:
        en = CATS_EN[k]
        cl = []
        for cid, c in sorted(((a, b) for a, b in ix.items() if a != "_tags" and b["cat"] == k), key=lambda x: x[1]["ru"]):
            attrs = [(i, g["attr"]) for i, g in enumerate(c["groups"]) if g["attr"]]
            if attrs:
                cl += [{"k": cid, "g": i, "ru": f"{c['ru']}({a})", "en": f"{CLS_EN[cid]}({a})", "icon": icons.get(cid)} for i, a in attrs]
            else:
                cl.append({"k": cid, "g": -1, "ru": c["ru"], "en": CLS_EN[cid], "icon": icons.get(cid)})
        if cl:
            cats.append({"k": k, "ru": ru, "en": en, "classes": cl})
    return {"cats": cats}


BASE_CUR = ["Orb of Transmutation", "Orb of Augmentation", "Regal Orb", "Orb of Alchemy", "Chaos Orb", "Exalted Orb"]
BONES = {"Jawbone": ["Gnawed Jawbone", "Preserved Jawbone", "Ancient Jawbone"], "Rib": ["Gnawed Rib", "Preserved Rib", "Ancient Rib"],
         "Collarbone": ["Gnawed Collarbone", "Preserved Collarbone", "Ancient Collarbone", "Altered Collarbone"], "Cranium": ["Preserved Cranium"], "Vertebrae": ["Preserved Vertebrae"]}
WOMB = {"Ring": "Signet Wombgift", "Amulet": "Ornate Wombgift", "Belt": "Banded Wombgift"}   # Brequel (Genesis tree) currency; other types use the generic one


def _sec_currency(sk, cid, cat):
    if cat == "fl":
        return []
    if sk == "base":
        return BASE_CUR
    if sk in ("minion", "caster"):
        return [WOMB.get(cid, "Lavish Wombgift")]
    bone = ("Collarbone" if cid in WOMB else "Jawbone" if cat in ("1h", "2h") or cid == "Quiver" else "Rib" if cat in ("arm", "off") else
            "Cranium" if cid == "Jewel" else "Vertebrae" if cid == "Map" else "")
    return BONES.get(bone, [])


def _plain(t):
    return re.sub(r"\[([^\]|]*)\|([^\]]*)\]", lambda m: m.group(2), t or "").replace("[", "").replace("]", "")


def _currency(store, names):
    bt = table(store, "baseitemtypes", "russian"); out = []
    if "cd" not in _mem:
        ci, cie = table(store, "currencyitems", "russian"), table(store, "currencyitems")
        _mem["cd"] = {ci.row(i).get("BaseItemType"): (_plain(ci.row(i).get("Description")), _plain(cie.row(i).get("Description"))) for i in range(len(ci))}
    for n in names:
        r = store.db.execute("select name,icon,row from items where name=? and class in ('Stackable Currency','Wombgifts') limit 1", (n,)).fetchone()
        if r:
            d = _mem["cd"].get(r[2], ("", ""))
            out.append({"name": mods._clean(bt.get(r[2], "Name")) or r[0], "name_en": r[0], "icon": r[1], "desc": d[0], "desc_en": d[1]})
    return out


def _tmpl(texts):
    """'+(10-19) to maximum Life' over all tiers -> '+# to maximum Life': numbers that differ between the first and last tier (or any range) become #."""
    a, b = texts[0], texts[-1]
    ta, tb = NUM.findall(a), NUM.findall(b)
    same = len(ta) == len(tb)
    it = iter(zip(ta, tb))
    def rep(m):
        x, y = next(it) if same else (m.group(0), m.group(0))
        return "#" if m.group(0).startswith("(") or x != y else m.group(0)
    return NUM.sub(rep, a)


def for_class(store, cid, group=-1, q=""):
    ix = _index(store); c = ix.get(cid)
    if not c or cid == "_tags":
        return None
    ms = mods.all_mods(store); tags = ix["_tags"]
    pick = c["groups"] if not 0 <= group < len(c["groups"]) else [c["groups"][group]]
    acc = {}
    for g in pick:
        for mi, sec in g["mods"]:
            acc[mi] = sec
    ql = q.lower().strip(); bk = {}
    for mi, sec in acc.items():
        m = ms[mi]
        if ql and ql not in (m["id"] + " " + m["name"] + " " + m["name_ru"] + " " + " ".join(m["text"]) + " " + " ".join(m["text_ru"]) + " " + m["type"]).lower():
            continue
        bk.setdefault((sec, m["gen"], m["type"]), []).append(m)
    secs = []
    for si, (sk, sru) in enumerate(SECTIONS):
        cols = {}
        for (s2, gen, _t), lst in bk.items():
            if s2 != si:
                continue
            lst.sort(key=lambda m: m["level"], reverse=True)
            tx = [(m["text_ru"] or m["text"]) for m in lst]
            te = [m["text"] or m["text_ru"] for m in lst]
            line = " / ".join(_tmpl([t[i] for t in tx if i < len(t)]) for i in range(max(len(t) for t in tx))) if any(tx) else (lst[0]["name_ru"] or lst[0]["name"] or lst[0]["id"])
            line_en = " / ".join(_tmpl([t[i] for t in te if i < len(t)]) for i in range(max(len(t) for t in te))) if any(te) else (lst[0]["name"] or lst[0]["name_ru"] or lst[0]["id"])
            cols.setdefault(gen, []).append({"id": lst[0]["id"], "text": line, "text_en": line_en, "tags": tags.get(str(lst[0]["i"]), []), "tiers": len(lst), "ilvl": lst[0]["level"],
                                     "t": [[m["level"], " / ".join(m["text_ru"] or m["text"]), m["name_ru"] or m["name"], " / ".join(m["text"] or m["text_ru"]), m["name"] or m["name_ru"]] for m in lst]})
        for v in cols.values():
            v.sort(key=lambda r: (r["tags"][0][0] if r["tags"] else "~", r["text"]))
        if cols:
            cur = _currency(store, _sec_currency(sk, cid, c["cat"]))
            secs.append({"k": sk, "ru": sru, "en": SEC_EN[sk], "currency": cur, "prefix": cols.get("PREFIX", []), "suffix": cols.get("SUFFIX", [])})
    return {"cls": cid, "ru": c["ru"], "en": CLS_EN[cid], "group": group, "label": c["groups"][group]["label"] if 0 <= group < len(c["groups"]) else "",
            "bases": [x[0] for x in sorted({tuple(b) for g in pick for b in g["bases"]})], "bases_en": [x[1] for x in sorted({tuple(b) for g in pick for b in g["bases"]})], "sections": secs}
