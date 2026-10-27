"""Section "Источники": where unique items come from (bosses, league content, trials, areas).

The client has no server-side drop tables, so every link carries its provenance:
  pob    - "Source:" line of the local Path of Building PoE2 data (community-verified)
  client - a table of the game client ties the item to the content
  art    - indirect: the item's passive-tree socket art belongs to this content (PassiveJewelUniqueArt)
  guess  - assumption from the name / flavour text of the item (never counted as a known source)
  info   - not a drop source (league of introduction)
"""
import glob, json, os, re
from .paths import DATA
from . import uniques as unq

VERSION = 3
CACHE = os.path.join(DATA, "cache", f"sources_v{VERSION}.json")
_mem = {}

TYPES = [("boss", "Босс"), ("trial", "Испытание"), ("content", "Контент лиги"), ("area", "Карта / локация"),
         ("league", "Лига (добавлено в)"), ("retired", "Больше не добывается"), ("unknown", "Источник неизвестен")]
CONF = {"pob": 3, "client": 3, "user": 3, "art": 2, "guess": 1, "info": 0}
CONF_RU = {"user": "подтверждено игроком (проверено в игре)", "pob": "подтверждено (Path of Building)", "client": "подтверждено (таблица клиента)", "art": "косвенно (арт гнезда в дереве)",
           "guess": "предположение", "info": "лига добавления, не источник дропа"}

# socket art of the passive tree jewel -> content (PassiveJewelUniqueArt, suffix after PassiveSkillScreenJewelSocketActive)
ART = {"DeliriumJewel": ("delirium", "Делириум", "Delirium"), "ExpeditionJewel": ("expedition", "Экспедиция", "Expedition"),
       "RitualJewel": ("ritual", "Ритуал", "Ritual"), "BreachJewel": ("breach", "Разлом", "Breach"),
       "SacredFlameJewel": ("sacredflame", "Священное пламя", "Sacred Flame"), "SpecialSanctumJewel": ("sanctum", "Святилище", "Sanctum"),
       "TrialmasterJewel": ("trialmaster", "Испытание мастера испытаний", "Trial of the Trialmaster"), "AbyssJewel": ("abyss", "Бездна", "Abyss"),
       "VivisectionJewel": ("vivisection", "Вивисекция", "Vivisection")}
AREA_RU = {"Vaal Temple": "Храм Ваал", "Atziri's Vault": "Хранилище Атзири"}
BOSS_ALIAS = {"Trialmaster": "The Trialmaster", "Arbiter of Ash": "The Arbiter of Ash"}


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _pob_sources(pob=unq.POB):
    """[(unique name, boss/content, area|None)] from "Source:" lines; None boss = no longer obtainable."""
    out = []
    for f in glob.glob(os.path.join(pob, "Uniques", "**", "*.lua"), recursive=True):
        src = open(f, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"\[\[\n?(.*?)\]\]", src, re.S):   # list files: [[ name \n base \n Source: ... ]]
            lines = [l.strip() for l in m.group(1).split("\n") if l.strip()]
            for l in lines[2:6]:
                if l.startswith("Source:") and len(lines) > 1:
                    out.append((lines[0], l[7:].strip()))
                    break
        for m in re.finditer(r'"([^"\n]+)",\s*"[^"\n]+",\s*"Source: ([^"\n]+)"', src):   # Special/Generated.lua
            out.append((m.group(1), m.group(2).strip()))
    res, seen = [], set()
    for name, s in out:
        if name in seen:
            continue
        seen.add(name)
        mm = re.match(r"Drops from unique\{([^}]+)\}(?: in normal\{([^}]+)\})?", s)
        if mm:
            res.append((name, mm.group(1), mm.group(2)))
        elif "No longer obtainable" in s:
            res.append((name, None, None))
    return res


def _tables(store):
    from .datrows import table
    mv = table(store, "monstervarieties")
    try:
        mvru = table(store, "monstervarieties", "russian")
    except Exception:
        mvru = None
    by = {}
    for i in range(len(mv)):
        n = (mv.get(i, "Name") or "").strip()
        iid = mv.get(i, "Id") or ""
        if n and n not in by and not re.search(r"(MAP|Clone|Spectre|Summon|Minion)", iid, re.I):
            by[n] = i
    return mv, mvru, by


def _area_ru(store, name):
    from .datrows import table
    if name in AREA_RU:
        return AREA_RU[name]
    try:
        e, r = table(store, "worldareas"), table(store, "worldareas", "russian")
        for i in range(len(e)):
            if e.get(i, "Name") == name:
                return r.get(i, "Name")
    except Exception:
        pass
    return name


def build(store):
    from .datrows import table
    db = store.db
    U = {}
    for name, base, slot, league, icon, data in db.execute("select name,base,slot,league,icon,data from uniques"):
        d = json.loads(data)
        U[name] = {"name": name, "base": base, "slot": slot, "league": league, "icon": icon, "flavour": d.get("flavour") or ""}
    S = {}

    def src(sid, typ, ru, en, **kw):
        s = S.setdefault(sid, dict(id=sid, type=typ, ru=ru, en=en, items=[], note="", area=None, monster=None, monsterRu=None))
        s.update({k: v for k, v in kw.items() if v})
        return s

    def link(sid, name, conf, why):
        if name not in U or conf in ("art", "guess"):   # only confirmed links are kept (PoB / client table / player)
            return
        s = S[sid]
        for it in s["items"]:
            if it["name"] == name:
                if CONF[conf] > CONF[it["conf"]]:
                    it["conf"], it["why"] = conf, why
                return
        s["items"].append({"name": name, "conf": conf, "why": why})

    mv, mvru, mon = _tables(store)

    # 1. Path of Building "Source:" lines
    for name, boss, area in _pob_sources():
        if boss is None:
            src("retired", "retired", "Больше не добывается", "No longer obtainable", note="Путь получения убран из игры (по данным Path of Building).")
            link("retired", name, "pob", "Path of Building: Source: No longer obtainable")
            continue
        en = BOSS_ALIAS.get(boss, boss)
        row = mon.get(en)
        if row is None and area is None and boss == "Atziri's Vault":
            row = None
        if boss == "Atziri's Vault":
            sid, typ, ru = "area-atzirisvault", "area", AREA_RU["Atziri's Vault"]
        elif boss == "Trialmaster":
            sid, typ, ru = "boss-" + _slug(en), "trial", None
        else:
            sid, typ, ru = "boss-" + _slug(en), "boss", None
        if row is not None and ru is None:
            ru = mvru.get(row, "Name") if mvru else None
        s = src(sid, typ, ru or en, boss if boss == "Atziri's Vault" else en, monster=mon.get(en), monsterRu=ru)
        if area:
            s["area"] = {"en": area, "ru": _area_ru(store, area)}
        link(sid, name, "pob", "Path of Building: Drops from " + boss + (" in " + area if area else ""))
    if "boss-the-trialmaster" in S:
        S["boss-the-trialmaster"]["type"] = "trial"
        S["boss-the-trialmaster"]["note"] = "Мастер испытаний в Испытании Хаоса."

    # 2. client: passive-tree jewel socket art tied to league content
    w = table(store, "words")
    art = table(store, "passivejeweluniqueart")
    for i in range(len(art)):
        nm = w.get(art.get(i, "Name"), "Text")
        key = re.sub(r"^.*PassiveSkillScreenJewelSocketActive", "", art.get(i, "JewelArt") or "")
        if key not in ART or nm not in U:
            continue
        cid, ru, en = ART[key]
        sid = "boss-the-trialmaster" if cid == "trialmaster" and "boss-the-trialmaster" in S else "content-" + cid
        src(sid, "content", ru, en, note="Связь по арту гнезда уникального самоцвета (PassiveJewelUniqueArt); точный источник дропа в клиенте не указан.")
        link(sid, nm, "art", f"Арт гнезда в дереве: {key}")

    # 2b. facts confirmed by the player in the game (not present in any local data)
    ex = table(store, "rogueexiles"); exru = table(store, "monstervarieties", "russian")
    names_en = [mv.get(ex.get(i, "MonsterVarietiesKey"), "Name") for i in range(len(ex))]
    src("content-abyss-exiles", "content", "Бездна: изгнанники (Rogue Exiles)", "Abyss: Rogue Exiles",
        note="Изгнанники, убитые в контенте Бездна (в клиенте их %d: %s). Что именно они дропают, клиент не говорит; связи ниже взяты из проверки в игре." % (len(names_en), ", ".join(names_en)))
    link("content-abyss-exiles", "Heart of the Well", "user", "Выпадает с Rogue Exiles, убитых в контенте Abyss (проверено игроком)")
    src("content-abyss", "content", "Бездна", "Abyss", note="Связь по арту гнезда уникального самоцвета (PassiveJewelUniqueArt); точный источник дропа в клиенте не указан.")
    link("content-abyss", "Heart of the Well", "user", "Выпадает с Rogue Exiles, убитых в контенте Abyss (проверено игроком)")

    # 2c. guess: Abyss mechanics named in the item's mods
    for name, u in U.items():
        txt = " ".join(json.loads(db.execute("select data from uniques where name=?", (name,)).fetchone()[0]).get("mods", []))
        if re.search(r"Abyssal|Desecrated|Kulemak", txt):
            src("content-abyss", "content", "Бездна", "Abyss")
            link("content-abyss", name, "guess", "Предположение: в свойствах упомянута механика Бездны (Abyssal / Desecrated / Kulemak)")

    # 3. client: Expedition runes of Olroth's legacy (Expedition2OlrothsLegacyRuneClient)
    t = table(store, "expedition2olrothslegacyruneclient")
    names = [w.get(i, "Text") for i in (t.get(0, "UniqueName") or [])]
    if names:
        src("content-olroth-legacy", "content", "Экспедиция: руна Наследия Олрота", "Expedition: Olroth's Legacy rune",
            note="Таблица Expedition2OlrothsLegacyRuneClient перечисляет уникальные, которые связаны с руной Наследия Олрота. Механизм (дроп или превращение) таблица не описывает.")
        for n in names:
            link("content-olroth-legacy", n, "client", "Expedition2OlrothsLegacyRuneClient")

    # 4. client: Incursion upgrades of unique items with Vials (IncursionUniqueUpgradeComponents)
    t = table(store, "incursionuniqueupgradecomponents"); bi = table(store, "baseitemtypes")
    src("content-incursion-vials", "content", "Вторжение: улучшение флаконами", "Incursion: Vial upgrades",
        note="Эти уникальные улучшаются в Храме Атзири с помощью указанного флакона (IncursionUniqueUpgradeComponents).")
    for i in range(len(t)):
        n = w.get(t.get(i, "BaseUnique"), "Text"); cur = bi.get(t.get(i, "UpgradeCurrency"), "Name")
        link("content-incursion-vials", n, "client", f"IncursionUniqueUpgradeComponents: улучшение флаконом «{cur}»")

    # 5. guess: boss named in the item name or flavour
    keys = {}
    sb = table(store, "standalonebosses")
    for i in range(len(sb)):
        n = (mv.get(sb.get(i, "Monster"), "Name") or "").strip()
        k = re.split(r",| of | the |'s ", n)[0].strip()
        if k and not k.lower().startswith("the ") and len(k) > 3:
            keys.setdefault(k, n)
    for k, n in (("Atziri", "Atziri, the Red Queen"), ("Doryani", "Doryani's Triumph"), ("Olroth", "Olroth, Origin of the Fall"),
                 ("Kosis", "Kosis, The Revelation"), ("Xesht", "Xesht, We That Are One"), ("Kulemak", "Vessel of Kulemak"), ("Zarokh", "Zarokh, the Temporal")):
        keys[k] = n
    for name, u in U.items():
        if any(name in [it["name"] for it in s["items"] if it["conf"] in ("pob", "client")] for s in S.values()):
            continue
        text = name + " " + u["flavour"]
        for k, bossname in keys.items():
            if k in ("Lord", "Incarnation", "Plagueling", "Thane Wulfric") or not re.search(r"\b" + re.escape(k) + r"\b", text):
                continue
            sid = "boss-" + _slug(bossname)
            row = mon.get(bossname)
            ru = mvru.get(row, "Name") if (row is not None and mvru) else None
            src(sid, "boss", ru or bossname, bossname, monster=row, monsterRu=ru)
            link(sid, name, "guess", f"Предположение: «{k}» упомянут в названии или тексте предмета")

    # 7. unknown
    known = {it["name"] for s in S.values() if s["type"] != "league" for it in s["items"] if it["conf"] != "guess"}
    src("unknown", "unknown", "Источник неизвестен", "Source unknown",
        note="В файлах игры и данных Path of Building нет сведений об источнике. Серверные таблицы дропа клиенту недоступны; вики PoE 2 не используется.")
    for name in sorted(U):
        if name not in known:
            link("unknown", name, "info", "Нет данных об источнике")

    rows = []
    for s in S.values():
        if not s["items"]:
            continue
        s["items"].sort(key=lambda it: (-CONF[it["conf"]], it["name"].lower()))
        rows.append(s)
    order = {k: i for i, (k, _) in enumerate(TYPES)}
    rows.sort(key=lambda s: (order[s["type"]], (s["ru"] or "").lower()))
    return {"sources": rows, "total": len(U), "known": len(known)}


def data(store):
    if "d" in _mem:
        return _mem["d"]
    try:
        d = json.load(open(CACHE, encoding="utf-8"))
        if d.get("v") == VERSION and d.get("n") == store.db.execute("select count(*) from uniques").fetchone()[0]:
            _mem["d"] = d
            return d
    except Exception:
        pass
    d = build(store); d["v"] = VERSION; d["n"] = d["total"]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(d, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    _mem["d"] = d
    return d


def _item(store, it, rows):
    r = rows.get(it["name"]) or {}
    return dict(it, base=r.get("base"), slot=r.get("slot"), icon=r.get("icon"), league=r.get("league"), confRu=CONF_RU[it["conf"]])


def _uniq(store):
    return {n: dict(base=b, slot=s, icon=i, league=l) for n, b, s, l, i in store.db.execute("select name,base,slot,league,icon from uniques")}


def listing(store, q="", typ=""):
    d = data(store); q = q.lower().strip(); rows = []
    ur = _uniq(store)
    counts = {}
    for s in d["sources"]:
        if q and not (q in (s["ru"] or "").lower() or q in (s["en"] or "").lower() or any(q in it["name"].lower() for it in s["items"])):
            continue
        counts[s["type"]] = counts.get(s["type"], 0) + 1
        if typ and s["type"] != typ:
            continue
        conf = sum(1 for it in s["items"] if CONF[it["conf"]] >= 2)
        first = next((ur.get(it["name"], {}).get("icon") for it in s["items"] if ur.get(it["name"], {}).get("icon")), None)
        rows.append(dict(id=s["id"], name=s["ru"], en=s["en"], type=s["type"], typeRu=dict(TYPES)[s["type"]], count=len(s["items"]), confirmed=conf, icon=first,
                         area=(s.get("area") or {}).get("ru"), areaEn=(s.get("area") or {}).get("en")))
    return {"types": [{"k": k, "ru": ru, "count": counts.get(k, 0)} for k, ru in TYPES], "rows": rows, "total": d["total"], "known": d["known"]}


def card(store, sid):
    d = data(store); ur = _uniq(store)
    for s in d["sources"]:
        if s["id"] == sid:
            return dict(s, typeRu=dict(TYPES)[s["type"]], items=[_item(store, it, ur) for it in s["items"]], total=d["total"], known=d["known"])
    return None


def for_unique(store, name):
    d = data(store); out = []
    for s in d["sources"]:
        if s["type"] == "unknown":
            continue
        for it in s["items"]:
            if it["name"] == name:
                out.append(dict(id=s["id"], type=s["type"], typeRu=dict(TYPES)[s["type"]], ru=s["ru"], en=s["en"], area=(s.get("area") or {}).get("ru"), areaEn=(s.get("area") or {}).get("en"),
                                conf=it["conf"], confRu=CONF_RU[it["conf"]], why=it["why"]))
    out.sort(key=lambda x: (-CONF[x["conf"]], x["type"] == "league"))
    if not any(CONF[x["conf"]] >= 2 for x in out):
        u = next((s for s in d["sources"] if s["type"] == "unknown" and any(it["name"] == name for it in s["items"])), None)
        if u:
            out.append(dict(id="unknown", type="unknown", typeRu="Источник неизвестен", ru="Источник неизвестен", en="Source unknown", area=None, conf="info",
                            confRu="нет данных", why=u["note"]))
    return out
