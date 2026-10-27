"""Gems for the Skills tab: one list of active skills, Spirit, meta, support and lineage gems (+ non-gem skills), compatibility of supports, gem card data."""
import json, os, re
from . import skills
from .datrows import table, ROOT

KINDS = [("active", "Активные"), ("spirit", "Spirit"), ("support", "Поддержки"), ("lineage", "Династические"), ("item", "От предметов"), ("other", "Прочие умения")]
CACHE = os.path.join(ROOT, "cache", "gems_v11.json")
COLORS = {1: "str", 2: "dex", 3: "int", 4: "white"}
_mem = {}
clean = lambda s: re.sub(r"\[([^\]]+)\]", r"\1", re.sub(r"\[([^\]|]+)\|([^\]]+)\]", r"\2", s or ""))


def _has_form(store, ge_row, name, kind):
    if kind not in ("active", "spirit"):
        return False
    try:
        from . import forms
        return bool(forms.for_skill(store, ge_row, name))
    except Exception:
        return False


def item_skills(store):
    """{ActiveSkills row: (Russian item class name, [(item name, Russian name)])} for skills the base items grant by themselves (ItemInherentSkills: amulets, staves, wands, sceptres ...)."""
    ge, bt, btr, ic, icr = table(store, "grantedeffects"), table(store, "baseitemtypes"), table(store, "baseitemtypes", "russian"), table(store, "itemclasses"), table(store, "itemclasses", "russian")
    t = table(store, "iteminherentskills"); out = {}
    for i in range(len(t)):
        b = t.get(i, "BaseItemType"); c = bt.get(b, "ItemClass"); nm = bt.get(b, "Name") or ""
        if not nm or nm.startswith("[DNT"):
            continue
        for g in t.get(i, "SkillsGranted") or []:
            a = ge.get(g, "ActiveSkill") if g is not None and g < len(ge) else None
            if a is not None:
                cls, items = out.setdefault(a, (icr.get(c, "Name") or ic.get(c, "Name") or "", []))
                if len(items) < 8 and nm not in [x[0] for x in items]:
                    items.append((nm, btr.get(b, "Name") or nm))
    return out


JUNK = re.compile(r"^\[DNT|\{0\}|^Coming Soon$|^Removed Skill$|^$", re.I)   # placeholders of unreleased / removed skills


BASIC_CAT = (("crossbow", 9), ("quarterstaff", 10), ("sword", 3), ("axe", 0), ("mace", 6), ("dagger", 4), ("spear", 8), ("flail", 5), ("bow", 2))   # basic attack name -> weapon category


def basic_attacks(store):
    """{skill gem row: weapon category} for the basic attacks of the weapon classes (CharacterMeleeSkills); one gem per attack name (the "Any ..." one wins)."""
    t, sg, bt = table(store, "charactermeleeskills"), table(store, "skillgems"), table(store, "baseitemtypes")
    rows = sorted({g for i in range(len(t)) for g in (t.get(i, "SkillGems") or []) if g is not None})
    best = {}
    for g in rows:
        name = (bt.get(sg.get(g, "BaseItemType"), "Name") or "").lower()
        cat = next((c for w, c in BASIC_CAT if w in name), None)
        if cat is None:
            continue
        best.setdefault((name, cat), []).append(g)
    return {(v[1] if len(v) > 1 else v[0]): k[1] for k, v in best.items()}


def build(store):
    sg, bt, btr = table(store, "skillgems"), table(store, "baseitemtypes"), table(store, "baseitemtypes", "russian")
    gm, gmr, ge = table(store, "gemeffects"), table(store, "gemeffects", "russian"), table(store, "grantedeffects")
    gt, gtr, iv = table(store, "gemtags"), table(store, "gemtags", "russian"), table(store, "itemvisualidentity")
    ast = table(store, "activeskilltype")
    sl = {x["i"]: x for x in skills.skill_list(store)}
    act, actr = table(store, "activeskills"), table(store, "activeskills", "russian")
    tag_id = [gt.get(i, "Id") for i in range(len(gt))]
    tag_en = [clean(gt.get(i, "Name")) for i in range(len(gt))]
    tag_ru = [clean(gtr.get(i, "Name")) for i in range(len(gtr))]
    basics = basic_attacks(store)
    out, used_as = [], set(); from_items = item_skills(store)
    tg = table(store, "tags"); RUNEFORGED = next((i for i in range(len(tg)) if tg.get(i, "Id") == "runeforged"), -1)   # base-item tag of the Kalguuran gems
    for i in range(len(sg)):
        effs = sg.get(i, "GemEffects") or []
        if not effs or sg.get(i, "IsVaalVariant"):
            continue
        e = effs[0]; g = gm.get(e, "GrantedEffect")
        if g is None:
            continue
        b = sg.get(i, "BaseItemType")
        if JUNK.search(bt.get(b, "Name") or ""):
            continue
        gtype = sg.get(i, "GemType")
        tags = [k for k in (gm.get(e, "GemTags") or []) if k is not None]
        ids = [tag_id[k] for k in tags]
        sup = bool(ge.get(g, "IsSupport")); asr = ge.get(g, "ActiveSkill")
        kind = "lineage" if sup and "lineage" in ids else "support" if sup else "spirit" if "persistent" in ids else "active"
        if gtype == 2 and not sup:   # meta gems have no category of their own: attacks / spells go among the ordinary skills, buffs go to Spirit
            kind = "active" if ("attack" in ids or "spell" in ids) else "spirit" if "buff" in ids else "active"
        sk = sl.get(asr) if asr is not None else None
        if asr is not None:
            used_as.add(asr)
        ivr = bt.get(b, "ItemVisualIdentity")
        icon = (sk or {}).get("icon") or (iv.get(ivr, "DDSFile") if ivr is not None else "") or ""
        out.append({"k": f"g{i}", "gem": i, "kind": kind, "name": bt.get(b, "Name") or "", "ru": btr.get(b, "Name") or "", "icon": icon, "color": COLORS.get(sg.get(i, "GemColour"), "white"),
                    "minlvl": sg.get(i, "MinLevelReq") or 0, "tags": [tag_en[k] for k in tags if tag_id[k] != "support" and tag_en[k]], "tags_ru": [tag_ru[k] or tag_en[k] for k in tags if tag_id[k] != "support" and tag_en[k]], "tag_ids": [tag_id[k] for k in tags],
                    "cat": [] if sup else ([basics[i]] if i in basics else [k for k in (sg.get(i, "CraftingTypes") or []) if k is not None]), "basic": i in basics, "kal": RUNEFORGED in (bt.get(b, "Tags") or []) and kind != "lineage", "ge": g, "effect": e, "skill": asr, "anim": bool(sk and sk["anim"]) or _has_form(store, g, bt.get(b, "Name"), kind), "wr": (sk or {}).get("wr", ""),
                    "text": clean(gm.get(e, "SupportText")), "text_ru": clean(gmr.get(e, "SupportText")),
                    "desc": clean(act.get(asr, "Description")) if asr is not None else "", "desc_ru": clean(actr.get(asr, "Description")) if asr is not None else ""})
    # skills that are not gems at all (monster / NPC / trigger skills); the ones items grant form their own group
    for x in skills.skill_list(store):
        if JUNK.search(x["name"] or ""):
            continue
        item = x["i"] in from_items
        if x["i"] in used_as and not item:
            continue
        out.append({"k": f"s{x['i']}" if x["i"] not in used_as else f"i{x['i']}", "gem": None, "kind": "item" if item else "other", "grp": from_items[x["i"]][0] if item else "", "items": [{"n": a, "ru": r} for a, r in from_items[x["i"]][1]] if item else [], "dup": x["i"] in used_as,
                    "name": x["name"], "ru": x["ru"], "icon": x["icon"], "color": "white", "minlvl": 0, "tags": [], "tags_ru": [], "tag_ids": [], "kal": False,
                    "cat": [], "ge": None, "effect": None, "skill": x["i"], "anim": x["anim"], "wr": x["wr"], "text": "", "text_ru": "", "desc": "", "desc_ru": ""})
    return out


def _drops(store):
    """{gem name: [{en, ru}]}: where the lineage supports drop (copied from the reference site, the client files have no such data); boss names in Russian come from the monster table."""
    if "drops" not in _mem:
        raw = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineage_drops.json"), encoding="utf-8"))
        mv, mvr = table(store, "monstervarieties"), table(store, "monstervarieties", "russian")
        ru = {}
        for i in range(len(mv)):
            n = mv.get(i, "Name")
            if n and mvr.get(i, "Name"):
                ru.setdefault(n, mvr.get(i, "Name"))
        ru["Global"] = "Любой источник"
        out = {}
        for k, v in raw.items():
            if k.startswith("_"):
                continue
            tok = v.split(", "); i = 0; lst = []
            while i < len(tok):
                for n in (3, 2, 1):   # names with commas ("Maztli, Flesh-Shaper") are told apart by the monster table
                    c = ", ".join(tok[i:i + n])
                    if c in ru or n == 1:
                        lst.append({"en": c, "ru": ru.get(c, c)}); i += n; break
            out[k] = lst
        _mem["drops"] = out
    return _mem["drops"]


def all_gems(store):
    if "g" not in _mem:
        if os.path.exists(CACHE):
            _mem["g"] = json.load(open(CACHE, encoding="utf-8"))
        else:
            _mem["g"] = build(store)
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            json.dump(_mem["g"], open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return _mem["g"]


CAT_ORDER = [6, 0, 9, 3, 8, 2, 10, 4, 7, 1, 11, 5]   # the order of the game's gem window: mace, axe, crossbow, sword, spear, bow, quarterstaff, dagger, elemental, occult, primal, flail


def cats(store):
    """Gem categories of the game's gem-cutting window (SkillCraftingData): name, Russian name, icon."""
    t, r = table(store, "skillcraftingdata"), table(store, "skillcraftingdata", "russian"); out = []
    for i in CAT_ORDER:
        if i >= len(t):
            continue
        ic = (t.get(i, "Icon") or "").lower().replace("art/2dart/", "art/textures/interface/2d/2dart/", 1) + ".dds"
        out.append({"i": i, "name": t.get(i, "Name"), "ru": r.get(i, "Name") or t.get(i, "Name"), "icon": ic})
    return out


def facets(store):
    gs = all_gems(store); k, t = {}, {}
    cc = {}
    for g in gs:
        k[g["kind"]] = k.get(g["kind"], 0) + 1
        for c in g["cat"]:
            cc[c] = cc.get(c, 0) + 1
        for n, r in zip(g["tags"], g["tags_ru"]):
            t.setdefault(n, [r, 0])[1] += 1
    kg = [g for g in gs if g.get("kal")]
    kal = [{"i": "kal", "name": "Kalguuran", "ru": "Калгуур", "icon": (next((g["icon"] for g in kg if g["name"] == "Remnants of Kalguur"), "") or (kg[0]["icon"] if kg else "")), "n": len(kg)}] if kg else []
    return {"cats": [dict(c, n=cc.get(c["i"], 0)) for c in cats(store)] + kal, "kinds": [{"k": a, "ru": b, "n": k.get(a, 0)} for a, b in KINDS], "tags": [{"k": n, "ru": v[0], "n": v[1]} for n, v in sorted(t.items(), key=lambda x: -x[1][1])]}


def search(store, q="", kind="", tag="", limit=2000, cat=""):
    ql = q.lower().strip(); out = []
    for g in all_gems(store):
        if kind and g["kind"] != kind or tag and tag not in g["tags"]:
            continue
        if cat == "kal":
            if not g.get("kal"):
                continue
        elif cat != "" and int(cat) not in g["cat"]:
            continue
        if g.get("dup") and kind != "item":   # an item-granted copy of a gem skill is listed only in its own group
            continue
        if ql and ql not in (g["name"] + " " + g["ru"]).lower():
            continue
        row = {x: g[x] for x in ("k", "kind", "name", "ru", "icon", "color", "minlvl", "tags", "skill", "anim", "wr")}; row["grp"] = g.get("grp", ""); row["items"] = g.get("items", [])
        row["tags_ru"] = g["tags_ru"]; row["tip"] = (g["desc_ru"] or g["text_ru"] or g["desc"] or g["text"])[:260]; row["tip_en"] = (g["desc"] or g["text"] or g["desc_ru"] or g["text_ru"])[:260]
        out.append(row)
    return out[:limit]


def _types(store):
    if "types" not in _mem:
        a, ge, ty = table(store, "activeskills"), table(store, "grantedeffects"), table(store, "activeskilltype")
        _mem["types"] = {"skill": {}, "ge": {}}
        for g in all_gems(store):
            if g["skill"] is not None:
                _mem["types"]["skill"][g["skill"]] = set(k for k in (a.get(g["skill"], "ActiveSkillTypes") or []) if k is not None)
            if g["ge"] is not None:
                r = ge.row(g["ge"])
                _mem["types"]["ge"][g["ge"]] = ([k for k in (r.get("AllowedActiveSkillTypes") or []) if k is not None],
                                               set(k for k in (r.get("ExcludedActiveSkillTypes") or []) if k is not None), set(k for k in (r.get("AddedActiveSkillTypes") or []) if k is not None), bool(r.get("CannotBeSupported")))
    return _mem["types"]


OP_OR, OP_AND, OP_NOT = 72, 73, 74


def _eval(expr, T):
    """The allowed-types list is a postfix expression (type ids, OR / AND / NOT markers); a list without markers means "any of"."""
    if not expr:
        return True
    if not any(k in (OP_OR, OP_AND, OP_NOT) for k in expr):
        return any(k in T for k in expr)
    st = []
    for k in expr:
        if k == OP_NOT:
            st.append(not (st.pop() if st else False))
        elif k in (OP_OR, OP_AND):
            b = st.pop() if st else False; a = st.pop() if st else False
            st.append((a or b) if k == OP_OR else (a and b))
        else:
            st.append(k in T)
    return bool(st[-1]) if st else True


def _fits(T, sup):
    allow, excl, _added, _cant = sup
    return _eval(allow, T) and not (set(excl) & T)


def detail(store, k):
    gs = all_gems(store); g = next((x for x in gs if x["k"] == k), None)
    if not g:
        return None
    d = dict(g)
    ty = _types(store)
    if g["kind"] in ("support", "lineage"):
        allow, excl, _a, _c = ty["ge"][g["ge"]]
        d["supports"] = [{"k": x["k"], "name": x["name"], "ru": x["ru"], "icon": x["icon"], "kind": x["kind"], "tags": x["tags"], "tags_ru": x["tags_ru"], "minlvl": x["minlvl"], "color": x["color"], "tip": (x["text_ru"] or x["desc_ru"] or x["text"] or x["desc"])[:300], "tip_en": (x["text"] or x["desc"] or x["text_ru"] or x["desc_ru"])[:300]} for x in gs
                         if x["kind"] in ("active", "spirit") and x["skill"] in ty["skill"] and _fits(ty["skill"][x["skill"]], (allow, excl, set(), False))]
    elif g["skill"] is not None and g["skill"] in ty["skill"]:
        T = ty["skill"][g["skill"]]
        no_support = bool(ty["ge"].get(g["ge"], (0, 0, 0, False))[3])   # the skill itself cannot be supported
        d["supported_by"] = [] if no_support else [{"k": x["k"], "name": x["name"], "ru": x["ru"], "icon": x["icon"], "kind": x["kind"], "tags": x["tags"], "tags_ru": x["tags_ru"], "minlvl": x["minlvl"], "color": x["color"], "tip": (x["text_ru"] or x["desc_ru"] or x["text"] or x["desc"])[:300], "tip_en": (x["text"] or x["desc"] or x["text_ru"] or x["desc_ru"])[:300]} for x in gs
                                                     if x["kind"] in ("support", "lineage") and _fits(T, ty["ge"][x["ge"]])]
    if g["gem"] is not None:
        sg = table(store, "skillgems")
        u = (sg.get(g["gem"], "UI_Image") or "").lower().replace("art/2dart/", "art/textures/interface/2d/2dart/", 1)
        if u:
            for c in (u + ".dds", u.rsplit("/", 1)[0] + "/4k/" + u.rsplit("/", 1)[1] + ".dds"):
                if store.read(c) is not None:
                    d["ui_image"] = c; break
        d["req"] = {"str": sg.get(g["gem"], "StrengthRequirementPercent") or 0, "dex": sg.get(g["gem"], "DexterityRequirementPercent") or 0, "int": sg.get(g["gem"], "IntelligenceRequirementPercent") or 0}
    if g["kind"] == "lineage":
        d["drops"] = _drops(store).get(g["name"], [])
    if g["kind"] in ("support", "lineage") and g["gem"] is not None:
        if "sgm" not in _mem:
            t = table(store, "supportgems"); _mem["sgm"] = {t.get(i, "SkillGem"): i for i in range(len(t))}
        i = _mem["sgm"].get(g["gem"])
        if i is not None:
            t, fe, fr = table(store, "supportgems"), table(store, "supportgemfamily"), table(store, "supportgemfamily", "russian")
            fam = [f for f in (t.get(i, "Family") or []) if f is not None]
            d["family"] = [fe.get(f, "Text") for f in fam]; d["family_ru"] = [fr.get(f, "Text") or fe.get(f, "Text") for f in fam]
            d["sup_icon"] = t.get(i, "Icon") or ""
            fl = t.get(i, "FlavourText")
            if fl is not None:
                d["flavour"] = (table(store, "flavourtext").get(fl, "Text") or "").replace("\r\n", " ")
                d["flavour_ru"] = (table(store, "flavourtext", "russian").get(fl, "Text") or "").replace("\r\n", " ")
    if g["ge"] is not None:
        d["levels"] = skills.levels_for(store, g["ge"])
        csd_path = None
        if g["skill"] is not None:
            csd_path = table(store, "activeskills").get(g["skill"], "StatDescription")
        d["stats"] = skills.stats_for(store, g["ge"], csd_path)
        d["quality"] = _quality(store, g["ge"], csd_path)
        d["curve"] = _curve(d)
    return d


def _curve(d):
    """Series of value-by-gem-level for the chart: damage, damage multiplier, cost, reservation, character level."""
    out = {}
    def put(key, pts):
        pts = [[a, b] for a, b in pts if a is not None and b is not None]
        if len(pts) > 1 and len({b for _a, b in pts}) > 1:
            out[key] = pts
    for st in d.get("stats", []):
        if any(l.get("dmg") for l in st["levels"]):
            put("dmg", [(l["level"], l["dmg"]) for l in st["levels"]]); break
    lv = d.get("levels", [])
    for st in d.get("stats", []):   # attack skills: damage multiplier of the attack by gem level
        if any(l.get("mult") for l in st["levels"]):
            put("mult", [(l["level"], round(100 + l["mult"] / 100, 1)) for l in st["levels"] if l.get("mult") is not None]); break
    put("cost", [(l["level"], (l["cost"] or [None])[0]) for l in lv])
    put("reservation", [(l["level"], l["reservation"]) for l in lv])
    put("actor", [(l["level"], round(l["actor_level"], 1) if l["actor_level"] is not None else None) for l in lv])
    return out


def _quality(store, ge_row, csd_path, pct=20):
    """Bonus of the gem's quality (stat value per 1% quality is stored in permille), rendered for `pct`% quality."""
    qs = table(store, "grantedeffectqualitystats")
    if "q" not in _mem:
        _mem["q"] = {}
        for i in range(len(qs)):
            _mem["q"].setdefault(qs.get(i, "GrantedEffect"), []).append(i)
    ids = skills.stat_ids(store); base = {}
    for p in ("data/statdescriptions/skill_stat_descriptions.csd", "data/statdescriptions/active_skill_gem_stat_descriptions.csd"):
        for k, v in skills.parse_csd(store, p).items():
            base.setdefault(k, v)
    if csd_path:
        for k, v in skills.parse_csd(store, csd_path).items():
            base[k] = v
    out = []
    for i in _mem["q"].get(ge_row, []):
        sts = [ids[k] for k in (qs.get(i, "Stats") or []) if k is not None and k < len(ids)]
        vals = qs.get(i, "StatsValuesPermille") or []
        for sid, v in zip(sts, vals):
            lo = {sid: v / 1000}; hi = {sid: v * pct / 1000}
            en = skills.render_stat(base, sid, {sid: round(hi[sid])}, "en"); ru = skills.render_stat(base, sid, {sid: round(hi[sid])}, "Russian")
            one = skills.render_stat(base, sid, {sid: round(lo[sid], 2)}, "Russian"); one_en = skills.render_stat(base, sid, {sid: round(lo[sid], 2)}, "en")
            out.append({"stat": sid, "per_percent": v / 1000, "text": en or sid, "text_ru": ru or en or sid, "per_text_ru": one, "per_text": one_en or one})
    return out
