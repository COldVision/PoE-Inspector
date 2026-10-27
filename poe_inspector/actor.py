"""Character editor backend: actors (player bodies, NPCs), equipment resolution, weapon animation sets."""
import re, json
from .catalog import text
from . import ast as astmod, mesh as meshmod, textures

PLAYER_SKINS = ["marauder", "ranger", "witch", "templar", "shadow", "scion", "gladiator"]
SOCKET_BONES = {"R": "aux_R_Weapon_attachment_jntBnd", "L": "aux_L_Weapon_attachment_jntBnd"}

SLOTS = {
    "helmet": {"label": "Шлем", "classes": ["Helmets"]},
    "body": {"label": "Броня", "classes": ["Body Armours"]},
    "gloves": {"label": "Перчатки", "classes": ["Gloves"]},
    "boots": {"label": "Обувь", "classes": ["Boots"]},
    "weapon": {"label": "Оружие", "classes": ["One Hand Swords", "Two Hand Swords", "One Hand Axes", "Two Hand Axes", "Daggers", "Spears",
                                              "Staves", "Warstaves", "One Hand Maces", "Two Hand Maces", "Wands", "Sceptres", "Claws",
                                              "Bows", "Crossbows", "Flails", "Quarterstaves"]},
    "offhand": {"label": "Вторая рука", "classes": ["Shields", "Bucklers", "Foci", "Quivers", "Daggers", "Claws"]},
}

# weapon class -> animation token(s) found in clip names
WEAPON_TOKENS = {
    "One Hand Swords": ["sword", "unarmed"], "Two Hand Swords": ["2hsword"], "One Hand Axes": ["sword", "unarmed"], "Two Hand Axes": ["2hsword"],
    "Daggers": ["dagger", "unarmed"], "Spears": ["spear", "unarmed"], "Staves": ["staff"], "Warstaves": ["staff"], "Quarterstaves": ["staff"],
    "One Hand Maces": ["sceptre", "wand", "unarmed"], "Two Hand Maces": ["maul"], "Wands": ["wand", "unarmed"], "Sceptres": ["sceptre", "wand"],
    "Claws": ["claw", "unarmed"], "Bows": ["bow"], "Crossbows": ["crossbow"], "Flails": ["flail", "unarmed"], "": ["unarmed"],
}

_alias = None


def aliases(store):
    """Segment alias table (Head_Seg / Body_Seg / Gloves_Seg / Boots_Seg ...) from a class .ao."""
    global _alias
    if _alias is None:
        t = text(store, "metadata/characters/str/strfour.ao")
        _alias = {}
        for m in re.finditer(r'alias\s*=\s*"(\w+)\s+([^"]+)"', t):
            _alias[m.group(1)] = [x.strip() for x in m.group(2).split(",") if x.strip()]
    return _alias


def np_(p):
    """Some .ao files spell paths with backslashes and without the leading `art/` (models/items/...)."""
    if not p:
        return p
    p = re.sub(r"/+", "/", p.replace("\\", "/"))
    return "Art/" + p if p.lower().startswith("models/") else p


def ao_fields(store, path, depth=0):
    """Resolve skeleton / skins / attachments of an .ao, following `extends` when the field is missing."""
    t = text(store, path.lower())
    t = re.sub(r'(?m)("[^"\n]*")|//.*$', lambda m: m.group(1) or "", t)  # commented-out rules must not apply (but `//` inside a quoted path is not a comment)
    if not t:
        return {"skeleton": None, "skins": [], "attached": [], "fixed": None, "hide": [], "hide_att": []}
    r = {"skeleton": None, "skins": [], "attached": [], "fixed": None, "hide": []}
    m = re.search(r'skeleton\s*=\s*"([^"]+)"', t)
    if m: r["skeleton"] = np_(m.group(1))
    r["skins"] = [np_(x) for x in re.findall(r'^\s*skin\s*=\s*"([^"]+)"', t, re.M)]
    fx = (re.search(r'fixed_mesh\s*=\s*"([^"]+)"', t) or [None, None])[1]
    r["fixed"] = np_(fx)
    for m in re.finditer(r'attached_object\s*=\s*"(\S+)\s+(\S+\.ao)', t):
        r["attached"].append((m.group(1), np_(m.group(2))))
    names = lambda txt: [x.strip() for x in txt.split(",") if x.strip()]
    rep = re.search(r'(?<![\w])hide_parent_segments\s*=\s*"([^"]*)"', t)
    add = re.findall(r'add_hide_parent_segments\s*=\s*"([^"]*)"', t)
    r["hide_replace"] = names(rep.group(1)) if rep else None
    r["hide_add"] = [n for a in add for n in names(a)]
    rep2 = re.search(r'(?<![\w])hide_parent_attachments\s*=\s*"([^"]*)"', t)
    add2 = re.findall(r'add_hide_parent_attachments\s*=\s*"([^"]*)"', t)
    r["att_replace"] = names(rep2.group(1)) if rep2 else None
    r["att_add"] = [n for a in add2 for n in names(a)]
    ext = re.search(r'extends\s+"([^"]+)"', t)
    if depth < 6 and ext and ext.group(1).lower() not in ("nothing", "metadata/parent"):
        parent = ao_fields(store, ext.group(1) + ".ao", depth + 1)
        if not r["skeleton"]: r["skeleton"] = parent["skeleton"]
        if not r["skins"]: r["skins"] = parent["skins"]
        if not r["fixed"]: r["fixed"] = parent["fixed"]
        base_hide = parent["hide"]; base_att = parent["hide_att"]
    else:
        base_hide = []; base_att = []
    if r["hide_replace"] is not None:
        base_hide = list(r["hide_replace"])
    if r["att_replace"] is not None:
        base_att = list(r["att_replace"])
    r["hide"] = base_hide + r["hide_add"]
    r["hide_att"] = base_att + r["att_add"]
    return r


EXTRA_ACTORS = [("metadata/monsters/atziri/humanform/atzirihumanform.ao", "atziri/humanform (Атзири до превращения)")]
# extra rigs with their own skeleton that play the same clip names as the body (cloak of the cinematic Atziri)
COMPANION_HIDE = {"metadata/monsters/atziri/humanform/atzirihumanform.ao": ["inner_topShape", "outer_topShape", "collarShape", "shoulderpadShape"]}
COMPANIONS = {"metadata/monsters/atziri/humanform/atzirihumanform.ao": ["metadata/cinematic/incursion/teaser/attachments/atzirirobe.ao"]}


def build_actor_table(store, log=print):
    db = store.db
    db.executescript("DROP TABLE IF EXISTS actors; CREATE TABLE actors(id TEXT PRIMARY KEY, kind TEXT, name TEXT, ao TEXT, skeleton TEXT, skin TEXT);")
    rows = []
    seen = {}
    for (p,) in db.execute("select path from files where ext='ao' and path like 'metadata/npc/%' and path not like '%/attachments/%' order by path").fetchall():
        try:
            f = ao_fields(store, p)
        except Exception:
            continue
        if f["skeleton"] and f["skins"]:
            key = (f["skeleton"].lower(), f["skins"][0].lower())
            name = p[len("metadata/npc/"):-3]
            if key not in seen or len(name) < len(seen[key][2]):
                seen[key] = (f"npc:{p}", "npc", name, p, key[0], key[1])
    rows += list(seen.values())
    for p, name in EXTRA_ACTORS:   # humanoid forms outside metadata/npc (cinematic Atziri before her transformation)
        try:
            f = ao_fields(store, p)
        except Exception:
            continue
        if f["skeleton"] and f["skins"]:
            rows.append((f"npc:{p}", "npc", name, p, f["skeleton"].lower(), f["skins"][0].lower()))
    db.executemany("INSERT OR REPLACE INTO actors VALUES(?,?,?,?,?,?)", rows)
    db.commit()
    log(f"actors={len(rows)} (players {sum(1 for r in rows if r[1]=='player')}, npc {sum(1 for r in rows if r[1]=='npc')})")


def smd_of(store, sm):
    t = text(store, sm.lower())
    m = re.search(r'SkinnedMeshData\s+"([^"]+)"', t)
    return m.group(1).lower().replace("\\", "/") if m else None


def attr_of(item_id):
    m = re.search(r"(StrDexInt|StrDex|StrInt|DexInt|Str|Dex|Int)", item_id or "")
    return m.group(1).lower() if m else None


# armour meshes exist in six fits (one per class archetype); the fit must follow the CHARACTER's archetype, not the item's stat requirement
ARCH_ORDER = {"str": ["str", "strdex", "strint", "dex", "int", "dexint"], "dex": ["dex", "strdex", "dexint", "str", "int", "strint"],
              "int": ["int", "strint", "dexint", "str", "dex", "strdex"], "strdex": ["strdex", "str", "dex", "strint", "dexint", "int"],
              "strint": ["strint", "str", "int", "strdex", "dexint", "dex"], "dexint": ["dexint", "dex", "int", "strdex", "strint", "str"]}


def arch_of_preset(key):
    """'str', 'dexint', ... ; a trailing 'b' marks the second body of the archetype (Brute, Huntress, Sorceress, Mercenary, Monk, Druid)."""
    if key not in PRESET_FILES:
        return None
    path = PRESET_FILES[key]
    return path.split("/")[0] + ("b" if path.endswith("b") else "")


_VAR_RX = re.compile(r"^(?P<stem>.+?)(?P<attr>strdex|strint|dexint|str|dex|int)(?P<b>b?)(?P<suffix>_[a-z0-9]+)?\.ao$")
_dir_cache = {}


def _norm_stem(x):
    x = x.rstrip("_")
    x = re.sub(r"(drop|body)$", "", x).rstrip("_")
    x = re.sub(r"(drop|body)$", "", x).rstrip("_")
    return x.rstrip("s")


def armour_variants(store, base_ao):
    """All fitted variants of a body-armour/helmet/gloves/boots drop .ao as {(attr, is_b): path}.
    File names follow `<stem><attr>[b][_suffix].ao` but stems drift from the drop name (plural 's', 'body' infix, element suffixes)."""
    base = base_ao.lower(); d, fn = base.rsplit("/", 1)
    if d not in _dir_cache:
        _dir_cache[d] = [r[0] for r in store.db.execute("select path from files where path like ? and ext='ao'", (d + "/%",)).fetchall() if "/" not in r[0][len(d) + 1:]]
    stem = re.sub(r"_?drop", "", fn[:-3], count=1)
    m = re.match(r"^(.*?)(_[a-z0-9]+)?$", stem)
    dstem, dsuffix = m.group(1), m.group(2) or ""
    want = _norm_stem(dstem)
    out = {}
    for p in _dir_cache[d]:
        name = p[len(d) + 1:]
        if "held" in name or name.endswith("drop.ao"):
            continue
        mm = _VAR_RX.match(name)
        if not mm or (mm.group("suffix") or "") != dsuffix or _norm_stem(mm.group("stem")) != want:
            continue
        out.setdefault((mm.group("attr"), bool(mm.group("b"))), p)
    return out


def equipped(store, item_name, item_id, ao, slot, ao2=None, arch=None):
    """Resolve what to attach for an item: skins (+ attachments), fixed mesh, parts to hide on the base body."""
    out = {"skins": [], "fixed": None, "hide": [], "slot": slot}
    if not ao:
        return out
    base = ao.lower()
    cand = []
    if slot in ("helmet", "body", "gloves", "boots"):
        attr = attr_of(item_id)
        stem = base.rsplit("/", 1)[-1][:-3]
        d = base.rsplit("/", 1)[0]
        stem = re.sub(r"drop$", "", stem)
        is_b = bool(arch) and arch.endswith("b")
        arch0 = arch[:-1] if is_b else arch
        order = ARCH_ORDER.get(arch0) or (([attr] if attr else []) + ["str", "dex", "int", "strdex", "strint", "dexint"])
        var = armour_variants(store, base)
        for a in order:   # the character's own fit first (second-body 'b' fit before the shared one), then the closest archetypes
            if is_b and (a, True) in var:
                cand.append(var[(a, True)])
            if (a, False) in var:
                cand.append(var[(a, False)])
        for a in order:
            cand.append(f"{d}/{stem}{a}.ao")
        out["fitted"] = any(store.find(c) for c in cand)
    else:
        if ao2 and ao2.lower().endswith(".fmt"):
            out["fixed"] = ao2.lower()
            return out
        if ao2 and ao2.lower().endswith(".ao"):
            cand.append(ao2.lower())
        stem = base[:-3]
        cand += [re.sub(r"drop$", "held", stem) + ".ao", re.sub(r"drop$", "", stem) + "held.ao"]
    cand.append(base)
    def _usable(c):
        if not store.find(c):
            return False
        if slot in ("helmet", "body", "gloves", "boots") and c != base:
            try:
                f_ = ao_fields(store, c)
                return bool(f_["skins"] or f_["attached"])   # a variant that carries no mesh at all is a data gap: try the next closest fit
            except Exception:
                return False
        return True
    chosen = next((c for c in cand if _usable(c)), base)
    f = ao_fields(store, chosen)
    out["skins"] = [s.lower() for s in f["skins"]]
    out["static"] = slot in ("weapon", "offhand")
    out["fixed"] = f["fixed"].lower() if f["fixed"] else None
    out["skeleton"] = f["skeleton"].lower() if f["skeleton"] and slot in ("weapon", "offhand") else None   # own rig (flail chain, bow string ...)
    out["ao"] = chosen
    al = aliases(store)
    hide = []
    for h in f["hide"]:
        hide += al.get(h, [h])
    out["hide"] = sorted(set(hide))
    out["hide_att"] = sorted(set(f["hide_att"]))
    out["attached"] = [(b, a) for b, a in f["attached"]]
    # every attached object (also the skin-less fx ones: glows, flames, skulls) may carry particle effects
    from . import effects as _fx
    _all, _seen, _stack = [], set(), [a for _b, a in f["attached"]]
    while _stack and len(_all) < 40:
        x = _stack.pop(0)
        if x.lower() in _seen:
            continue
        _seen.add(x.lower()); _all.append(x)
        try:
            _stack += [a2 for _b2, a2 in ao_fields(store, x.lower())["attached"]]
        except Exception:
            pass
    try:
        out["effects"] = _fx.item_effects(store, item_id, ao, chosen, _all)
    except Exception:
        out["effects"] = []
    # skirts, shawls, plumes (own cloth rigs, authored in the local space of the mount bone) and replacement leggings (skinned straight onto the body rig)
    out["attachments"] = []
    for bone, a in f["attached"]:
        try:
            fa = ao_fields(store, a.lower())
        except Exception:
            continue
        sk = [x.lower() for x in fa["skins"]]
        own = bool(fa["skeleton"])
        if sk and not (own and bone == "<root>"):
            out["attachments"].append({"bone": bone, "ao": a, "skins": sk, "own": own})
    return out


def weapon_tokens(cls):
    return WEAPON_TOKENS.get(cls, ["unarmed"])


def build_anim_table(store, log=print):
    db = store.db
    db.executescript("DROP TABLE IF EXISTS anim_clips; CREATE TABLE anim_clips(ast TEXT, move TEXT, clip TEXT, fps INTEGER); CREATE INDEX anim_clip_name ON anim_clips(clip);")
    rows = []
    for (p,) in db.execute("select path from files where ext='ast' and path like 'art/models/charactersfour/animations/%/onerig.ast'").fetchall():
        a = astmod.load(store, p)
        mv = p.split("/")[-2]
        rows += [(p, mv, c["name"], c["fps"]) for c in a.clips]
    db.executemany("INSERT INTO anim_clips VALUES(?,?,?,?)", rows)
    db.commit()
    log(f"anim clips={len(rows)}")


def anim_list(store, tokens, q=""):
    out = []
    seen = set()
    for ti, tk in enumerate(tokens):
        for ast_p, mv, clip, fps in store.db.execute("select ast,move,clip,fps from anim_clips where clip like ? and clip like ? order by clip", (f"%{tk}%", f"%{q}%")).fetchall():
            if (ast_p, clip) in seen: continue
            seen.add((ast_p, clip))
            if clip.endswith(("_additive",)) or "_female" in clip: continue
            if not re.search(rf"(^|_){re.escape(tk)}(_|$)", clip): continue
            out.append({"ast": ast_p, "move": mv, "clip": clip, "fps": fps, "ti": ti})
    def w(r):   # the weapon's own clips first (token order: weapon, then the unarmed fallback), then by kind
        c = r['clip']
        if 'floating' in c or 'relaxed' in c: return (r["ti"], 8, c)
        for i, k in enumerate(('idle', 'run', 'walk', 'attack', 'sprint', 'dodge')):
            if c.startswith(k): return (r["ti"], i, c)
        return (r["ti"], 9, c)
    out.sort(key=w)
    return out


PRESET_FILES = {
    "Marauder": "str/strfour", "Brute": "str/strfourb", "Ranger": "dex/dexfour", "Huntress": "dex/dexfourb",
    "Witch": "int/intfour", "Sorceress": "int/intfourb", "Gladiator": "strdex/strdexfour", "Mercenary": "strdex/strdexfourb",
    "Shadow": "dexint/dexintfour", "Monk": "dexint/dexintfourb", "Templar": "strint/strintfour", "Druid": "strint/strintfourb",
}


def preset(store, key):
    """Default look of a class: body skin + outfit/hair attachments with their hide rules."""
    path = PRESET_FILES[key]
    t = text(store, f"metadata/characters/{path}.ao")
    skins = [x for x in re.findall(r'(?<!remove_)skin\s*=\s*"([^"]+)"', t)]
    body = (skins[-1] if skins else "Art/Models/CharactersFour/Templar.sm").lower()
    al = aliases(store)
    parts = []
    for m in re.finditer(r'attached_object\s*=\s*"(\S+)\s+(\S+\.ao)(?:\s+alias\s+(\w+))?', t):
        bone, ao, tag = m.groups()
        f = ao_fields(store, ao)
        part = {"tag": tag or "Part", "bone": bone, "ao": ao, "skins": [], "hide": []}
        own_rig = bool(f["skeleton"])
        sock = {"Head_Attachment": "aux_Head_attachment"}.get(bone) or ("aux_Head_attachment" if tag == "Head_Attach" else None)
        for sm in f["skins"]:
            part["skins"].append({"sm": sm.lower(), "static": own_rig, "bone": sock if own_rig else None})
        for h in f["hide"]:
            part["hide"] += al.get(h, [h])
        for bone2, a2 in f["attached"]:
            try:
                f2 = ao_fields(store, a2)
            except Exception:
                continue
            for sm in f2["skins"]:
                part["skins"].append({"sm": sm.lower(), "static": True, "bone": bone2 if bone2 != "<root>" else None})
        part["skins"] = [x for x in part["skins"] if not (x["static"] and not x["bone"])]  # own-rig pieces with no known mount would lie on the floor
        parts.append(part)
    return {"id": f"class:{key}", "name": key, "kind": "player", "arch": arch_of_preset(key), "skeleton": "art/models/charactersfour/onerig.ast", "skin": body, "parts": parts}


def npc_preset(store, ao_path):
    """Outfit/hair/weapon pieces an NPC's .ao attaches (attached_object = "<bone or socket> <ao>"), resolved like a class preset."""
    t = text(store, ao_path.lower())
    t = re.sub(r'(?m)("[^"\n]*")|//.*$', lambda m: m.group(1) or "", t)
    socks = {m.group(1): m.group(2) for m in re.finditer(r'socket\s*=\s*"([^"]+)"\s*\n\s*parent\s*=\s*"([^"]+)"', t)}
    al = aliases(store)
    parts, seen = [], set()
    for m in re.finditer(r'attached_object\s*=\s*"(\S+)\s+(\S+\.ao)(?:\s+alias\s+(\w+))?', t):
        bone, ao, tag = m.groups()
        mount = socks.get(bone, bone)
        try:
            f = ao_fields(store, ao)
        except Exception:
            continue
        part = {"tag": tag or "Part", "bone": mount, "ao": ao, "skins": [], "hide": []}
        own_rig = bool(f["skeleton"])
        for sm in f["skins"]:
            part["skins"].append({"sm": sm.lower(), "static": own_rig, "bone": mount if own_rig else None})
        for h in f["hide"]:
            part["hide"] += al.get(h, [h])
        for bone2, a2 in f["attached"]:
            try:
                f2 = ao_fields(store, a2)
            except Exception:
                continue
            for sm in f2["skins"]:
                part["skins"].append({"sm": sm.lower(), "static": True, "bone": socks.get(bone2, bone2) if bone2 != "<root>" else None})
        part["skins"] = [x for x in part["skins"] if not (x["static"] and not x["bone"])]
        if part["skins"]:
            parts.append(part)
    comp = []
    for c in COMPANIONS.get(ao_path.lower(), []):
        try:
            f = ao_fields(store, c)
        except Exception:
            continue
        if f["skeleton"] and f["skins"]:
            comp.append({"skeleton": f["skeleton"].lower(), "skin": f["skins"][0].lower()})
    if comp:   # the cloak replaces the vest / collar / shoulder pads that are part of the body mesh (they are not worn in game)
        parts.append({"tag": "Cloak", "bone": None, "ao": "", "skins": [], "hide": list(COMPANION_HIDE.get(ao_path.lower(), []))})
    return {"parts": parts, "companions": comp}
