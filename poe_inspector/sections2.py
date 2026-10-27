"""More reference sections built on BaseItemTypes: currency, essences, runes and soul cores, flasks; plus endgame maps, hideouts, strongboxes."""
from .sections import _t, _g, _clean, LMem, en

def _cs(store, v, ru=True):
    """A text column: either a string or a row of ClientStrings2."""
    if isinstance(v, str):
        return _clean(v)
    if isinstance(v, int):
        t = _t(store, "clientstrings2", ru) or _t(store, "clientstrings2")
        return _clean(_g(t, v, "Text") or "") if t is not None else ""
    return ""


KEYS = ("currency", "essences", "runes", "flasks", "maps", "hideouts", "strongboxes")
_mem = LMem()


def _bi(store, b):
    if b is None:
        return None
    bt, btr = _t(store, "baseitemtypes"), _t(store, "baseitemtypes", True)
    ic, icr, iv = _t(store, "itemclasses"), _t(store, "itemclasses", True), _t(store, "itemvisualidentity")
    cls = _g(bt, b, "ItemClass"); v = _g(bt, b, "ItemVisualIdentity")
    return {"name": _g(bt, b, "Name") or "", "ru": (_g(btr, b, "Name") or _g(bt, b, "Name") or "").strip(), "cls": _g(ic, cls, "Name") or "", "cls_ru": _g(icr, cls, "Name") or _g(ic, cls, "Name") or "",
            "icon": (_g(iv, v, "DDSFile") or "") if v is not None else ""}


def _items_of(store, key, table_name, extra=None):
    if key in _mem:
        return _mem[key]
    t = _t(store, table_name); out = []
    for i in range(len(t)):
        b = _bi(store, _g(t, i, "BaseItemType"))
        if not b or not b["name"] or b["name"].startswith("[") or b["name"] == "NULL":
            continue
        d = {"i": i, **b}
        if extra:
            d.update(extra(t, i))
        out.append(d)
    _mem[key] = out
    return out


def _currency(store):
    tr = _t(store, "currencyitems", True)
    return _items_of(store, "cur", "currencyitems", lambda t, i: {"stack": _g(t, i, "StackSize", 0), "desc": _cs(store, _g(tr, i, "Description") or _g(t, i, "Description")), "how": _cs(store, _g(tr, i, "Directions") or _g(t, i, "Directions"))})


def _essences(store):
    return _items_of(store, "ess", "essences", lambda t, i: {"tier": _g(t, i, "Tier", 0), "up": (_bi(store, _g(t, i, "UpgradeResult")) or {}).get("ru", "")})


RUNE_CAT = {"All": "Любой предмет", "Armour": "Доспехи", "Body Armour": "Нательная броня", "Boots": "Обувь", "Bow": "Лук", "Buckler": "Баклер", "Caster Weapon": "Оружие заклинателя", "Crossbow": "Арбалет",
            "Crossbow Bow or Spear": "Арбалет, лук или копьё", "Focus": "Фокус", "Gloves": "Перчатки", "Helmet": "Шлем", "Maces or Talisman": "Булавы или талисман", "Martial Or Caster Weapon": "Боевое оружие или оружие заклинателя",
            "Martial Weapon": "Боевое оружие", "Martial Weapon Wand or Staff": "Боевое оружие, жезл или посох", "One Hand Mace": "Одноручная булава", "One Hand Mace or Quarterstaff": "Одноручная булава или боевой посох",
            "Quarterstaff": "Боевой посох", "Quarterstaff or Spear": "Боевой посох или копьё", "Sceptre": "Скипетр", "Shield": "Щит", "Shield or Buckler": "Щит или баклер", "Spear": "Копьё", "Staff": "Посох",
            "Talisman": "Талисман", "Two Hand Mace": "Двуручная булава", "Wand": "Жезл", "Wand or Staff": "Жезл или посох"}


def _rune_stats(store):
    """soul core / rune -> [(category, lines, bonded lines)] from SoulCoreStats."""
    if "rs" in _mem:
        return _mem["rs"]
    from . import mods
    t, cat, catr, st = _t(store, "soulcorestats"), _t(store, "soulcorestatcategories"), _t(store, "soulcorestatcategories", True), _t(store, "stats")
    csd = mods._csd(store); out = {}
    def render(ids, vals):
        sids = [st.get(k, "Id") for k in (ids or []) if k is not None]; lo = dict(zip(sids, vals or []))
        return mods._render(csd, sids, lo, lo, "en" if en() else "Russian") or mods._render(csd, sids, lo, lo, "en")
    for i in range(len(t)):
        c = _g(t, i, "StatCategory")
        name = (_g(catr, c, "Name") or _g(cat, c, "Name") or _g(cat, c, "Id") or "") if c is not None else ""
        out.setdefault(_g(t, i, "SoulCore"), []).append((name if en() else RUNE_CAT.get(name, name), render(_g(t, i, "Stats"), _g(t, i, "StatsValues")), render(_g(t, i, "BondedStats"), _g(t, i, "BondedStatsValues"))))
    _mem["rs"] = out
    return out


def _runes(store):
    return _items_of(store, "rune", "soulcores", lambda t, i: {"lvl": _g(t, i, "RequiredLevel", 0), "desc": _cs(store, _g(t, i, "Description")) + (" " + _cs(store, _g(t, i, "ExtraDescription")) if _g(t, i, "ExtraDescription") is not None else "")})


def _flasks(store):
    return _items_of(store, "fl", "flasks", lambda t, i: {"life": _g(t, i, "LifePerUse", 0), "mana": _g(t, i, "ManaPerUse", 0), "rec": _g(t, i, "RecoveryTime", 0)})


def _maps(store):
    if "mp" in _mem:
        return _mem["mp"]
    em, emr, wa, war = _t(store, "endgamemaps"), _t(store, "endgamemaps", True), _t(store, "worldareas"), _t(store, "worldareas", True)
    out = []
    for i in range(len(em)):
        w = _g(em, i, "WorldArea")
        if w is not None:
            out.append({"i": i, "name": _g(wa, w, "Name") or "", "ru": (_g(war, w, "Name") or _g(wa, w, "Name") or "").strip(), "level": _g(wa, w, "AreaLevel", 0), "flavour": _cs(store, _g(emr, i, "FlavourText") or _g(em, i, "FlavourText")), "obj": _cs(store, _g(em, i, "ObjectiveDescription"))})
    _mem["mp"] = out
    return out


def _hideouts(store):
    if "hd" in _mem:
        return _mem["hd"]
    ht, wa, war = _t(store, "hideouts"), _t(store, "worldareas"), _t(store, "worldareas", True)
    out = []
    for i in range(len(ht)):
        w = _g(ht, i, "HideoutArea")
        if w is not None:
            out.append({"i": i, "name": _g(wa, w, "Name") or "", "ru": (_g(war, w, "Name") or _g(wa, w, "Name") or "").strip(), "on": bool(_g(ht, i, "IsEnabled"))})
    _mem["hd"] = out
    return out


def _boxes(store):
    if "sb" in _mem:
        return _mem["sb"]
    sb, ch, chr_ = _t(store, "strongboxes"), _t(store, "chests"), _t(store, "chests", True)
    out = []
    for i in range(len(sb)):
        c = _g(sb, i, "ChestsKey")
        if c is not None:
            out.append({"i": i, "name": _g(ch, c, "Name") or _g(ch, c, "Id") or "", "ru": (_g(chr_, c, "Name") or _g(ch, c, "Name") or _g(ch, c, "Id") or "").strip(), "w": _g(sb, i, "SpawnWeight", 0)})
    _mem["sb"] = out
    return out


def _match(ql, *parts):
    return not ql or ql in " ".join(p for p in parts if p).lower()


def listing(store, sec, q, f, limit, offset):
    ql = q.lower().strip(); rows, filters = [], []
    row = lambda x, sub, icon="": {"id": str(x["i"]), "name": x["ru"], "sub": sub, "icon": icon, "key": False}
    if sec == "currency":
        cl = {}
        for x in _currency(store):
            cl[x["cls"]] = x["cls_ru"]
            if (not f or x["cls"] == f) and _match(ql, x["name"], x["ru"], x["desc"]):
                rows.append(row(x, x["cls_ru"], x["icon"]))
        filters = [{"k": k, "ru": v} for k, v in sorted(cl.items(), key=lambda a: a[1])]
    elif sec == "essences":
        rows = [row(x, f'Тир {x["tier"]}' if x["tier"] else x["cls_ru"], x["icon"]) for x in _essences(store) if _match(ql, x["name"], x["ru"])]
    elif sec == "runes":
        rows = [row(x, f'ур. {x["lvl"]}' if x["lvl"] else x["cls_ru"], x["icon"]) for x in _runes(store) if _match(ql, x["name"], x["ru"], x["desc"])]
    elif sec == "flasks":
        rows = [row(x, x["cls_ru"], x["icon"]) for x in _flasks(store) if _match(ql, x["name"], x["ru"])]
    elif sec == "maps":
        rows = [row(x, f'ур. {x["level"]}' if x["level"] else "") for x in _maps(store) if _match(ql, x["name"], x["ru"], x["flavour"])]
    elif sec == "hideouts":
        rows = [row(x, "" if x["on"] else "отключено") for x in _hideouts(store) if _match(ql, x["name"], x["ru"])]
    elif sec == "strongboxes":
        rows = [row(x, f'вес {x["w"]}') for x in _boxes(store) if _match(ql, x["name"], x["ru"])]
    return {"total": len(rows), "rows": rows[offset:offset + limit], "filters": filters}


def card(store, sec, id_):
    i = int(id_)
    find = lambda lst: next((x for x in lst if x["i"] == i), None)
    base = lambda x, tags, kv, **k: {"title": x["ru"], "sub": x["name"], "icon": x.get("icon", ""), "tags": tags, "kv": kv, "desc": k.get("desc", ""), "lines": k.get("lines", []), "reminder": k.get("reminder", []), "flavour": k.get("flavour", ""), "blocks": []}
    if sec == "currency":
        x = find(_currency(store))
        return x and base(x, [x["cls_ru"]], [["Размер стопки", str(x["stack"]), True]] if x["stack"] else [], desc=x["desc"], reminder=[x["how"]] if x["how"] else [])
    if sec == "essences":
        x = find(_essences(store))
        return x and base(x, ["Сущность"], ([["Тир", str(x["tier"]), True]] if x["tier"] else []) + ([["Улучшается в", x["up"], False]] if x["up"] else []))
    if sec == "runes":
        x = find(_runes(store))
        if not x:
            return None
        c = base(x, [x["cls_ru"]], [["Требуемый уровень", str(x["lvl"]), True]] if x["lvl"] else [], lines=[x["desc"]] if x["desc"] else [])
        for name, lines, bonded in _rune_stats(store).get(x["i"], []):
            if lines:
                c["blocks"].append({"h": name or "Свойства", "items": [{"t": t} for t in lines]})
            if bonded:
                c["blocks"].append({"h": (name or "Свойства") + " · связанный", "items": [{"t": t} for t in bonded]})
        return c
    if sec == "flasks":
        x = find(_flasks(store))
        if not x:
            return None
        kv = [[l, str(v), True] for l, v in (("Жизни за применение", x["life"]), ("Маны за применение", x["mana"])) if v]
        return base(x, [x["cls_ru"]], kv + ([["Время восстановления", f'{x["rec"] / 10:g} с', False]] if x["rec"] else []))
    if sec == "maps":
        x = find(_maps(store))
        return x and base(x, ["Карта"], [["Уровень зоны", str(x["level"]), True]] if x["level"] else [], desc=x["obj"], flavour=x["flavour"])
    if sec == "hideouts":
        x = find(_hideouts(store))
        return x and base(x, ["Убежище"], [["Доступно", "да" if x["on"] else "нет", False]])
    if sec == "strongboxes":
        x = find(_boxes(store))
        return x and base(x, ["Ларец"], [["Вес появления", str(x["w"]), True]])
    return None
