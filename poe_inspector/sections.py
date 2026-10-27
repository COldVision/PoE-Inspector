"""Reference sections of the game (port of the the reference site sections): passive skills, classes + ascendancies, areas, quests, achievements.
Every section gives a list (id, name, sub, icon) and a generic card {title, sub, icon, tags, kv, desc, lines, flavour, blocks}."""
import json, os, re, threading
from . import mods, skills
from .datrows import table, ROOT

SECTIONS = [("passives", "Пассивные умения"), ("classes", "Классы и восхождения"), ("areas", "Локации"), ("quests", "Задания"), ("achievements", "Достижения"), ("currency", "Валюта и расходники"), ("essences", "Сущности"), ("runes", "Руны и души"), ("flasks", "Флаконы"), ("maps", "Карты (поздняя игра)"), ("hideouts", "Убежища"), ("strongboxes", "Ларцы")]
_loc = threading.local()


def en():
    """True while the current request asks for English texts (lang=en): the "ru" tables are then replaced by the English ones."""
    return getattr(_loc, "en", False)


class LMem(dict):
    """Per-language memo: the same key holds a separate value for ru and en."""
    def _k(self, k):
        return (k, en())
    def __contains__(self, k):
        return dict.__contains__(self, self._k(k))
    def __getitem__(self, k):
        return dict.__getitem__(self, self._k(k))
    def __setitem__(self, k, v):
        dict.__setitem__(self, self._k(k), v)


_mem = LMem()


def _t(store, name, ru=False):
    try:
        return table(store, name, "russian" if ru and not en() else None)
    except Exception:
        return None


def _g(t, i, col, default=None):
    try:
        v = t.get(i, col)
        return default if v is None else v
    except Exception:
        return default


def _clean(s):
    s = re.sub(r"\[([^\]|]+)\|([^\]]+)\]", r"\2", s or "")
    return re.sub(r"\[([^\]]+)\]", r"\1", s).replace("\r\n", "\n")


def _flat(v):
    return [x for x in (v or []) if x is not None]


# ------------------------------------------------------------------ passives
PTYPES = {"key": "Ключевые", "notable": "Значимые", "small": "Обычные", "asc": "Восхождения", "attr": "Атрибуты", "jewel": "Гнёзда самоцветов"}


def passives(store):
    if "p" in _mem:
        return _mem["p"]
    cache = os.path.join(ROOT, "cache", "passives_v2.json")
    if os.path.exists(cache):
        _mem["p"] = json.load(open(cache, encoding="utf-8")); return _mem["p"]
    en, ru = _t(store, "passiveskills"), _t(store, "passiveskills", True)
    asc_t, asc_ru = _t(store, "ascendancy"), _t(store, "ascendancy", True)
    ch, chr_ = _t(store, "characters"), _t(store, "characters", True)
    st = _t(store, "stats"); csd = mods._csd(store)
    out = []
    for i in range(len(en)):
        r = en.row(i)
        if not r.get("Name"):
            continue
        sids, lo = [], {}
        for n, sref in enumerate(_flat(r.get("Stats")), 1):
            sid = st.get(sref, "Id"); v = r.get(f"Stat{n}Value") or 0; sids.append(sid); lo[sid] = v
        kind = "key" if r["IsKeystone"] else "asc" if r["Ascendancy"] is not None else "notable" if r["IsNotable"] else "attr" if r.get("IsAttribute") else "jewel" if r["IsJewelSocket"] else "small"
        asc = r["Ascendancy"]
        out.append({"i": i, "id": r["Id"], "name": r["Name"], "ru": (ru.get(i, "Name") or "").strip() or r["Name"], "icon": r.get("Icon_DDSFile") or "", "kind": kind, "notable": bool(r["IsNotable"]),
                    "asc": asc, "asc_ru": (_g(asc_ru, asc, "Name") or _g(asc_t, asc, "Name")) if asc is not None else "", "asc_en": _g(asc_t, asc, "Name") or "" if asc is not None else "",
                    "classes": [(_g(chr_, c, "Name") or _g(ch, c, "Name")) for c in _flat(r.get("Characters"))], "classes_en": [_g(ch, c, "Name") or "" for c in _flat(r.get("Characters"))],
                    "points": r.get("SkillPointsGranted") or 0, "text": mods._render(csd, sids, lo, lo, "en"), "text_ru": mods._render(csd, sids, lo, lo, "Russian"),
                    "reminder": [_clean(x) for x in _flat(r.get("ReminderStrings"))],
                    "flavour": _clean(ru.get(i, "FlavourText") or r.get("FlavourText") or ""), "flavour_en": _clean(r.get("FlavourText") or "")})
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    _mem["p"] = out
    return out


def _passive_card(p):
    E = en()
    kv = [["Тип", PTYPES.get(p["kind"], p["kind"]) + (" (значимая)" if p["kind"] == "asc" and p["notable"] else ""), True]]
    if p["asc_ru"]:
        kv.append(["Восхождение", p["asc_en"] if E else p["asc_ru"], False])
    if p["classes"]:
        kv.append(["Класс", ", ".join(p["classes_en"] if E else p["classes"]), False])
    if p["points"]:
        kv.append(["Очков умений", str(p["points"]), False])
    return {"title": p["name"] if E else p["ru"], "sub": "" if E else p["name"], "icon": p["icon"], "tags": [PTYPES.get(p["kind"], "")], "kv": kv, "desc": "", "lines": p["text"] if E else (p["text_ru"] or p["text"]), "reminder": p["reminder"], "flavour": p["flavour_en"] if E else p["flavour"], "blocks": []}


# ------------------------------------------------------------------ classes / ascendancies
def classes(store):
    if "c" in _mem:
        return _mem["c"]
    ch, chr_ = _t(store, "characters"), _t(store, "characters", True)
    at, atr = _t(store, "ascendancy"), _t(store, "ascendancy", True)
    out = []
    for i in range(len(ch)):
        n = ch.get(i, "Name")
        if not n:
            continue
        out.append({"k": f"c{i}", "kind": "class", "i": i, "name": n, "ru": _g(chr_, i, "Name") or n})
    for j in range(len(at)):
        n = at.get(j, "Name") or ""
        if not n or n.startswith("[DNT") or at.get(j, "Disabled"):
            continue
        c = at.get(j, "Character")
        out.append({"k": f"a{j}", "kind": "asc", "i": j, "name": n, "ru": _g(atr, j, "Name") or n, "class": c, "class_ru": (_g(chr_, c, "Name") or _g(ch, c, "Name")) if c is not None else ""})
    _mem["c"] = out
    return out


def _class_card(store, k):
    items = classes(store); it = next((x for x in items if x["k"] == k), None)
    if not it:
        return None
    ch, chr_ = _t(store, "characters"), _t(store, "characters", True)
    at, atr = _t(store, "ascendancy"), _t(store, "ascendancy", True)
    if it["kind"] == "class":
        i = it["i"]
        kv = [["Сила", str(_g(ch, i, "BaseStrength", 0)), False], ["Ловкость", str(_g(ch, i, "BaseDexterity", 0)), False], ["Интеллект", str(_g(ch, i, "BaseIntelligence", 0)), False],
              ["Базовая жизнь", str(_g(ch, i, "BaseMaxLife", 0)), True], ["Базовая мана", str(_g(ch, i, "BaseMaxMana", 0)), True]]
        asc = [{"t": x["ru"], "s": x["name"]} for x in items if x["kind"] == "asc" and x.get("class") == i]
        return {"title": it["ru"], "sub": it["name"], "icon": "", "tags": ["Класс"], "kv": kv, "desc": _clean(_g(chr_, i, "Description") or _g(ch, i, "Description") or ""), "lines": [],
                "flavour": _clean(_g(chr_, i, "TraitDescription") or _g(ch, i, "TraitDescription") or ""), "blocks": [{"h": "Классы восхождения", "items": asc}] if asc else []}
    j = it["i"]
    ps = [p for p in passives(store) if p["asc"] == j]
    pn = lambda p: p["name"] if en() else p["ru"]
    px = lambda p: "; ".join(p["text"] if en() else (p["text_ru"] or p["text"])) or ""
    items_ = [{"t": pn(p), "s": px(p), "key": p["notable"]} for p in ps if p["notable"]] + [{"t": pn(p), "s": px(p)} for p in ps if not p["notable"] and p["text"]]
    return {"title": it["ru"], "sub": it["name"], "icon": "", "tags": ["Восхождение", it.get("class_ru") or ""], "kv": [["Класс", it.get("class_ru") or "—", True], ["Узлов дерева", str(len(ps)), False]], "desc": "",
            "lines": [], "flavour": _clean(_g(atr, j, "FlavourText") or _g(at, j, "FlavourText") or ""), "blocks": [{"h": "Умения восхождения", "items": items_}] if items_ else []}


# ------------------------------------------------------------------ areas
def areas(store):
    if "a" in _mem:
        return _mem["a"]
    en, ru = _t(store, "worldareas"), _t(store, "worldareas", True)
    out = []
    for i in range(len(en)):
        n = en.get(i, "Name")
        if not n or n == "NULL":
            continue
        out.append({"i": i, "name": n, "ru": (_g(ru, i, "Name") or n).strip(), "act": en.get(i, "Act") or 0, "level": en.get(i, "AreaLevel") or 0, "town": bool(en.get(i, "IsTown")), "wp": bool(en.get(i, "HasWaypoint")),
                    "map": bool(en.get(i, "IsMapArea")), "hideout": bool(en.get(i, "IsHideout")), "id": en.get(i, "Id")})
    out.sort(key=lambda a: (a["act"], a["level"], a["name"]))
    _mem["a"] = out
    return out


def _area_card(store, i):
    en, ru = _t(store, "worldareas"), _t(store, "worldareas", True)
    mv, mvr = _t(store, "monstervarieties"), _t(store, "monstervarieties", True)
    a = next((x for x in areas(store) if x["i"] == i), None)
    if not a:
        return None
    names = lambda ids, lim=40: [{"t": (_g(mvr, k, "Name") or _g(mv, k, "Name") or "?")} for k in _flat(ids)[:lim]]
    conn = [{"t": (_g(ru, k, "Name") or _g(en, k, "Name") or "?"), "s": f"акт {_g(en, k, 'Act', 0)} · ур. {_g(en, k, 'AreaLevel', 0)}"} for k in _flat(en.get(i, "Connections"))]
    kv = [["Акт", str(a["act"]), False], ["Уровень зоны", str(a["level"]), True], ["Город", "да" if a["town"] else "нет", False], ["Путевой камень", "есть" if a["wp"] else "нет", False]]
    tags = [x for x, f in (("Город", a["town"]), ("Карта", a["map"]), ("Убежище", a["hideout"])) if f]
    blocks = []
    if conn:
        blocks.append({"h": "Переходы", "items": conn})
    b = names(en.get(i, "Bosses_MonsterVarietiesKeys"))
    if b:
        blocks.append({"h": "Боссы", "items": b})
    m = names(en.get(i, "Monsters_MonsterVarietiesKeys"))
    if m:
        blocks.append({"h": "Монстры", "items": m})
    return {"title": a["ru"], "sub": f'{a["name"]} · {a["id"]}', "icon": "", "tags": tags, "kv": kv, "desc": "", "lines": [], "flavour": "", "blocks": blocks}


# ------------------------------------------------------------------ quests
def quests(store):
    if "q" in _mem:
        return _mem["q"]
    en, ru = _t(store, "quest"), _t(store, "quest", True)
    out = []
    for i in range(len(en)):
        n = en.get(i, "Name")
        if n:
            out.append({"i": i, "name": n, "ru": (_g(ru, i, "Name") or n).strip(), "act": en.get(i, "Act") or 0, "icon": en.get(i, "Icon_DDSFile") or "", "id": en.get(i, "Id")})
    _mem["q"] = out
    return out


def _quest_card(store, i):
    q = next((x for x in quests(store) if x["i"] == i), None)
    if not q:
        return None
    qs, qsr = _t(store, "queststates"), _t(store, "queststates", True)
    steps = []
    for k in range(len(qs)):
        if qs.get(k, "Quest") == i:
            steps.append((qs.get(k, "Order") or 0, (_g(qsr, k, "Text") or _g(qs, k, "Text") or "").strip(), (_g(qsr, k, "MapPinsText") or _g(qs, k, "MapPinsText") or "").strip()))
    steps.sort(key=lambda x: x[0])
    items = [{"t": f"{n}. {t}", "s": pin.replace("\n", " · ")} for n, (_o, t, pin) in enumerate(steps, 1) if t]
    return {"title": q["ru"], "sub": f'{q["name"]} · {q["id"]}', "icon": q["icon"], "tags": [f'Акт {q["act"]}'], "kv": [["Акт", str(q["act"]), True], ["Этапов", str(len(items)), False]], "desc": "", "lines": [], "flavour": "", "blocks": [{"h": "Прохождение", "items": items}] if items else []}


# ------------------------------------------------------------------ achievements
def achievements(store):
    if "ac" in _mem:
        return _mem["ac"]
    en, ru = _t(store, "achievements"), _t(store, "achievements", True)
    out = []
    for i in range(len(en)):
        d = en.get(i, "Description")
        if d:
            out.append({"i": i, "name": d, "ru": (_g(ru, i, "Description") or d).strip(), "obj": _clean(_g(ru, i, "Objective") or en.get(i, "Objective") or ""), "hc": bool(en.get(i, "HardcoreOnly")), "sc": bool(en.get(i, "SoftcoreOnly"))})
    _mem["ac"] = out
    return out


# ------------------------------------------------------------------ public API
def listing(store, sec, q="", f="", limit=500, offset=0, lang="ru"):
    _loc.en = lang == "en"
    try:
        return _tr(_listing(store, sec, q, f, limit, offset))
    finally:
        _loc.en = False


def _listing(store, sec, q, f, limit, offset):
    from . import sections2
    if sec in sections2.KEYS:
        return sections2.listing(store, sec, q, f, limit, offset)
    ql = q.lower().strip(); rows, filters = [], []
    if sec == "passives":
        for p in passives(store):
            if f and p["kind"] != f:
                continue
            if ql and ql not in (p["name"] + " " + p["ru"] + " " + " ".join(p["text"]) + " " + " ".join(p["text_ru"]) + " " + p["asc_ru"]).lower():
                continue
            E = en()
            rows.append({"id": str(p["i"]), "name": p["name"] if E else p["ru"], "sub": PTYPES[p["kind"]] + (f' · {p["asc_en"] if E else p["asc_ru"]}' if p["asc_ru"] else ""), "text": (p["text"] if E else (p["text_ru"] or p["text"]))[:1], "icon": p["icon"], "key": p["kind"] in ("key", "notable")})
        filters = [{"k": k, "ru": v} for k, v in PTYPES.items()]
    elif sec == "classes":
        for c in classes(store):
            if ql and ql not in (c["name"] + " " + c["ru"]).lower():
                continue
            if f and c["kind"] != f:
                continue
            rows.append({"id": c["k"], "name": c["ru"], "sub": "Класс" if c["kind"] == "class" else f'Восхождение · {c.get("class_ru") or ""}', "icon": "", "key": c["kind"] == "class"})
        filters = [{"k": "class", "ru": "Классы"}, {"k": "asc", "ru": "Восхождения"}]
    elif sec == "areas":
        for a in areas(store):
            if f and str(a["act"]) != f:
                continue
            if ql and ql not in (a["name"] + " " + a["ru"] + " " + (a["id"] or "")).lower():
                continue
            rows.append({"id": str(a["i"]), "name": a["ru"], "sub": f'Акт {a["act"]} · ур. {a["level"]}' if a["level"] else f'Акт {a["act"]}', "icon": "", "key": a["town"]})
        filters = [{"k": str(k), "ru": f"Акт {k}"} for k in sorted({a["act"] for a in areas(store)})]
    elif sec == "quests":
        for x in quests(store):
            if f and str(x["act"]) != f:
                continue
            if ql and ql not in (x["name"] + " " + x["ru"]).lower():
                continue
            rows.append({"id": str(x["i"]), "name": x["ru"], "sub": f'Акт {x["act"]}', "icon": x["icon"], "key": False})
        filters = [{"k": str(k), "ru": f"Акт {k}"} for k in sorted({x["act"] for x in quests(store)})]
    elif sec == "achievements":
        for x in achievements(store):
            if ql and ql not in (x["name"] + " " + x["ru"] + " " + x["obj"]).lower():
                continue
            rows.append({"id": str(x["i"]), "name": x["ru"], "sub": x["obj"][:80], "icon": "", "key": False})
    return {"total": len(rows), "rows": rows[offset:offset + limit], "filters": filters}


def card(store, sec, id_, lang="ru"):
    _loc.en = lang == "en"
    try:
        return _tr(_card(store, sec, id_), True)
    finally:
        _loc.en = False


def _card(store, sec, id_):
    from . import sections2
    if sec in sections2.KEYS:
        return sections2.card(store, sec, id_)
    if sec == "passives":
        p = next((x for x in passives(store) if str(x["i"]) == str(id_)), None)
        return _passive_card(p) if p else None
    if sec == "classes":
        return _class_card(store, id_)
    if sec == "areas":
        return _area_card(store, int(id_))
    if sec == "quests":
        return _quest_card(store, int(id_))
    if sec == "achievements":
        x = next((a for a in achievements(store) if str(a["i"]) == str(id_)), None)
        return {"title": x["ru"], "sub": x["name"], "icon": "", "tags": ["Достижение"], "kv": [], "desc": x["obj"], "lines": [], "flavour": "", "blocks": []} if x else None
    return None


# ------------------------------------------------------------------ English labels (applied to the output when lang=en)
_EN = {"Пассивные умения": "Passive Skills", "Классы и восхождения": "Classes and Ascendancies", "Локации": "Areas", "Задания": "Quests", "Достижения": "Achievements", "Валюта и расходники": "Currency and Consumables",
       "Сущности": "Essences", "Руны и души": "Runes and Soul Cores", "Флаконы": "Flasks", "Карты (поздняя игра)": "Maps (Endgame)", "Убежища": "Hideouts", "Ларцы": "Strongboxes",
       "Ключевые": "Keystones", "Значимые": "Notables", "Обычные": "Small Passives", "Восхождения": "Ascendancies", "Атрибуты": "Attributes", "Гнёзда самоцветов": "Jewel Sockets",
       "Тип": "Type", "Восхождение": "Ascendancy", "Класс": "Class", "Очков умений": "Skill points", "Сила": "Strength", "Ловкость": "Dexterity", "Интеллект": "Intelligence", "Базовая жизнь": "Base life", "Базовая мана": "Base mana",
       "Классы восхождения": "Ascendancy classes", "Узлов дерева": "Tree nodes", "Умения восхождения": "Ascendancy passives", "Акт": "Act", "Уровень зоны": "Area level", "Город": "Town", "да": "yes", "нет": "no",
       "Путевой камень": "Waypoint", "есть": "yes", "Карта": "Map", "Убежище": "Hideout", "Переходы": "Connections", "Боссы": "Bosses", "Монстры": "Monsters", "Этапов": "Steps", "Прохождение": "Walkthrough",
       "Классы": "Classes", "Достижение": "Achievement", "Размер стопки": "Stack size", "Сущность": "Essence", "Тир": "Tier", "Улучшается в": "Upgrades to", "Требуемый уровень": "Required level", "Свойства": "Properties",
       "Жизни за применение": "Life per use", "Маны за применение": "Mana per use", "Время восстановления": "Recovery time", "Доступно": "Available", "Ларец": "Strongbox", "Вес появления": "Spawn weight", "отключено": "disabled",
       "Любой предмет": "Any item", "Доспехи": "Armour", "Нательная броня": "Body Armour", "Обувь": "Boots", "Лук": "Bow", "Баклер": "Buckler", "Шлем": "Helmet", "Перчатки": "Gloves", "Щит": "Shield", "Копьё": "Spear", "Посох": "Staff", "Жезл": "Wand",
       "(значимая)": "(notable)", "связанный": "bonded"}
_ENRE = [(re.compile(r"^Акт (\d+)$"), r"Act \1"), (re.compile(r"^акт (\d+)$"), r"act \1"), (re.compile(r"^ур\. (\d+)$"), r"Lv \1"), (re.compile(r"^Тир (\d+)$"), r"Tier \1"), (re.compile(r"^вес (\d+)$"), r"weight \1"),
         (re.compile(r"^([\d.]+) с$"), r"\1 s"), (re.compile(r"^(.*) \(значимая\)$"), r"\1 (notable)"), (re.compile(r"^(.*) · связанный$"), r"\1 · bonded")]


def _x(s):
    if not en() or not any("А" <= c <= "я" or c in "Ёё" for c in s):
        return s
    parts = s.split(" · ")
    out = []
    for p in parts:
        r = _EN.get(p)
        if r is None:
            for rx, rep in _ENRE:
                if rx.match(p):
                    r = rx.sub(rep, p); break
        out.append(r if r is not None else p)
    return " · ".join(out)


def _tr(o, card=False):
    if not en():
        return o
    if isinstance(o, str):
        return _x(o)
    if isinstance(o, list):
        return [_tr(v) for v in o]
    if isinstance(o, dict):
        d = {k: _tr(v) for k, v in o.items()}
        if card and d.get("sub"):
            sub = d["sub"]
            if sub == d.get("title"):
                d["sub"] = ""
            elif sub.startswith(str(d.get("title")) + " · "):
                d["sub"] = sub[len(str(d["title"])) + 3:]
        return d
    return o
