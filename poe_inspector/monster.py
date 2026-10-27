"""Everything the game data says about one monster variety: stats, skills, animation states/clips, sounds and files."""
import json, os, re
from .datrows import table
from .catalog import text
from . import actor, skills, fmodrender, effects, pet

_FILE_RX = re.compile(r'"?([\w\-./ ]+\.(?:ao|act|ais|ast|amd|sm|smd|fmt|mat|pet|epk|ecf|trl|dds|ogg|ot))"?', re.I)


def _name(store, tname, i, col="Id"):
    try:
        t = table(store, tname)
        return t.get(i, col) if i is not None and i < len(t) else None
    except Exception:
        return None


def _names(store, tname, ids, col="Id"):
    return [x for x in (_name(store, tname, i, col) for i in (ids or []) if i is not None) if x]


def _json_blocks(t):
    """`Block { animations = '[...]' }` sections of an .ao -> {block: [animations]}."""
    out = {}
    for m in re.finditer(r"(\w+)\s*\{[^{}]*?animations\s*=\s*'(\[.*?\])'", t, re.S):
        try:
            out.setdefault(m.group(1), []).extend(json.loads(m.group(2)))
        except Exception:
            pass
    return out


def _act_states(store, act_paths):
    """state -> [clip names] from the monster .act files (`Idle = "idle_01";`)."""
    out = {}
    for p in act_paths:
        t = re.sub(r"//[^\n]*", "", text(store, p.lower()))
        for m in re.finditer(r'^\s*([\w:]+)\s*=\s*"([^"]+)"\s*(?:timeline\s+"[^"]*")?\s*;', t, re.M):
            out.setdefault(m.group(1), [re.split(r"[\s:]", c.strip())[0] for c in m.group(2).split(",") if c.strip()])
    return out


def _ao_chain(store, ao):
    chain, seen = [], set()
    while ao and ao.lower() not in seen and len(chain) < 4:
        seen.add(ao.lower()); chain.append(ao)
        m = re.search(r'extends\s+"([^"]+)"', text(store, ao.lower()))
        ao = m.group(1) if m else None
        if ao and ao.lower().endswith("/parent"):
            break
    return chain


_GENERIC = {"audio", "sound effects", "monstersounds", "npc", "monsters", "4.0", "part1", "part2", "leagues", "vocals", "foley", "effects", "dialogue", "endgame", "common"}
_banks_cache = {}


def _bank_names(game):
    if game not in _banks_cache:
        d = os.path.join(game, "FMOD", "Desktop")
        _banks_cache[game] = {f.lower(): f for f in os.listdir(d) if f.lower().endswith(".bank")} if os.path.isdir(d) else {}
    return _banks_cache[game]


def find_banks(game, event_paths, extra):
    """FMOD banks that hold the monster's sounds: the bank is named after a folder of its event path (…/BrineMaiden/Vocals/Death -> BrineMaiden.bank)."""
    names = _bank_names(game); comps = []
    for e in event_paths:
        parts = [x for x in re.split(r"[/\\]", e) if x]
        parts = [x for x in parts[:-1] if x.lower() not in _GENERIC and not re.fullmatch(r"(act\d+|g\d_[\w]*|g\d+)", x.lower())]
        comps += list(reversed(parts))
    comps += extra
    out = []
    for c in comps:
        k = (re.sub(r"\s+", "", c) + ".bank").lower()
        if k in names and names[k] not in out:
            out.append(names[k])
        if len(out) >= 3:
            break
    return out


def _attachments(store, chain):
    """Hair, clothes, armour and props of a monster: `attached_object = "<bone> <file>.ao"` lines of the .ao chain."""
    out, seen = [], set()
    for ao in chain:
        t = re.sub(r"(?m)//.*$", "", text(store, ao.lower()))
        for m in re.finditer(r'attached_object\s*=\s*"(\S+)\s+(\S+\.ao)', t):
            key = (m.group(1), m.group(2).lower())
            if key in seen or not store.find(m.group(2).lower()):
                continue
            seen.add(key)
            try:
                f = actor.ao_fields(store, m.group(2).lower())
            except Exception:
                continue
            if f["skins"] or f["fixed"]:
                out.append({"bone": m.group(1), "ao": m.group(2), "skins": f["skins"], "skeleton": f["skeleton"], "fixed": f["fixed"],
                            "root": m.group(1) == "<root>", "hide": f.get("hide") or []})
        if re.search(r"clear_inherited_attached_objects\s*=\s*true", t, re.I):
            break
    return out


def _weapons(store, r):
    ivi = table(store, "itemvisualidentity"); out = []
    for key, label in (("Weapon1_ItemVisualIdentity", "Оружие 1"), ("Weapon2_ItemVisualIdentity", "Оружие 2"), ("Back_ItemVisualIdentity", "Спина"), ("Helmet_ItemVisualIdentity", "Шлем")):
        v = r.get(key); v = v if isinstance(v, list) else ([v] if v is not None else [])
        for i in v:
            if i is None or i >= len(ivi):
                continue
            row = ivi.row(i); ao = row.get("AOFile2") or row.get("AOFile") or ""
            w = {"slot": key.split("_")[0], "label": label, "id": row["Id"], "icon": row.get("DDSFile") or "", "ao": ao, "skins": [], "skeleton": None, "fixed": ao if ao.lower().endswith(".fmt") else None}
            if ao and not w["fixed"] and store.find(ao.lower()):
                try:
                    f = actor.ao_fields(store, ao.lower()); w["skins"] = f.get("skins") or []; w["skeleton"] = f.get("skeleton")
                except Exception:
                    pass
            out.append(w)
    return out


def _impacts(store, d, blocks):
    """Ground-slam style attacks: the clip, the moment of impact (strongest ScreenShake event, else the `contact` event) and the ground texture the effect uses."""
    clips = {}
    states = {x["state"]: x["clips"] for x in d.get("states", [])}
    slam = {c for k, v in states.items() if re.search(r"slam|stomp|smash|pound|leapslam", k, re.I) for c in v}
    shake = {}
    for a in blocks.get("ScreenShake", []):
        ev = [x for x in a.get("events", []) if x.get("type") == "ScreenShakeEventType"]
        if ev:
            shake[a["name"]] = max(ev, key=lambda x: x.get("amplitude", 0))
    for c in slam:
        if c in shake:
            clips[c] = {"t": round(shake[c]["time"], 3), "amp": shake[c].get("amplitude", 0)}
        elif (d.get("events", {}).get(c) or {}).get("contact"):
            clips[c] = {"t": d["events"][c]["contact"][0], "amp": 0}
    tex = None
    paths = [it["path"] for g in d.get("effects", []) for it in g["items"] if it.get("path")]
    for pth in paths:
        base = pth.rsplit("/", 1)[0].lower() + "/"
        q = "select path from files where path like ? and path like '%grd%' and path like '%_r.mat' limit 1"
        row = store.db.execute(q, (base + "%slam%",)).fetchone() or store.db.execute(q, (base + "%",)).fetchone()
        if row:
            tex = pet.first_texture(store, row[0])
            if tex:
                break
    return {"clips": clips, "tex": tex}


def detail(store, row):
    mv = table(store, "monstervarieties"); r = mv.row(row)
    d = {"row": row, "id": r["Id"], "name": r["Name"]}
    try:
        d["name_ru"] = table(store, "monstervarieties", "russian").get(row, "Name")
    except Exception:
        d["name_ru"] = None
    d["type"] = _name(store, "monstertypes", r.get("MonsterType"))
    d["category"] = _name(store, "monstercategories", r.get("MonsterCategory"))
    d["tags"] = _names(store, "tags", r.get("Tags"))
    d["mods"] = _names(store, "mods", (r.get("Mods") or []) + (r.get("Special_Mods") or []) + (r.get("Mods2") or []))
    d["stats"] = {k: r.get(k) for k in ("MovementSpeed", "ObjectSize", "MinimumAttackDistance", "MaximumAttackDistance", "ModelSizeMultiplier", "ExperienceMultiplier",
                                          "DamageMultiplier", "LifeMultiplier", "AttackSpeed", "MinAgroRange", "MaxAgroRange", "PoiseThreshold", "AttackCrit") if r.get(k) is not None}
    d["boss"] = bool(r.get("BossHealthBar"))
    # ---- skills --------------------------------------------------------------------------------
    ge = table(store, "grantedeffects"); asr = table(store, "activeskills"); asr_ru = table(store, "activeskills", "russian")
    lst = list(r.get("GrantedEffects") or [])
    if r.get("TauntGrantedEffect") is not None:
        lst.append(r["TauntGrantedEffect"])
    d["skills"] = []
    for g in dict.fromkeys(x for x in lst if x is not None):
        if g >= len(ge):
            continue
        gr = ge.row(g); a = gr.get("ActiveSkill"); s = {"effect": gr["Id"], "cast_time": gr.get("CastTime"), "taunt": g == r.get("TauntGrantedEffect")}
        if a is not None and a < len(asr):
            ar = asr.row(a)
            s.update({"as": a, "name": ar["DisplayedName"], "ru": asr_ru.get(a, "DisplayedName"), "desc": ar["Description"] or ar["ShortDescription"],
                      "desc_ru": asr_ru.get(a, "Description") or asr_ru.get(a, "ShortDescription"), "icon": ar["Icon_DDSFile"]})
            s["animation"] = skills.anim_chain(store, g)
        d["skills"].append(s)
    # ---- animations / sounds from .ao + .act ---------------------------------------------------
    aos = list(r.get("AOFiles") or []); acts = list(r.get("ACTFiles") or [])
    d["files"] = {"act": acts, "ao": [], "ais": [r["AISFile"]] if r.get("AISFile") else [], "misc": []}
    blocks, fields = {}, None
    for ao in aos:
        for p in _ao_chain(store, ao):
            if p not in d["files"]["ao"]:
                d["files"]["ao"].append(p)
            for k, v in _json_blocks(text(store, p.lower())).items():
                blocks.setdefault(k, []).extend(v)
        if fields is None:
            try:
                f = actor.ao_fields(store, ao.lower())
                if f.get("skeleton"):
                    fields = f
            except Exception:
                pass
    d["states"] = [{"state": k, "clips": v} for k, v in _act_states(store, acts).items()]
    clips, rig = [], None
    if fields and fields.get("skeleton"):
        rig = fields["skeleton"]
        try:
            from . import ast as astmod
            a = astmod.load(store, rig.lower())
            clips = [c["name"] for c in a.clips] if a else []
        except Exception:
            clips = []
        d["skeleton"] = rig; d["skins"] = fields.get("skins") or []
    d["clips"] = clips
    ev = {}
    for a in blocks.get("AnimationController", []):
        e = ev.setdefault(a["name"], {"contact": [], "events": []})
        for x in a.get("events", []):
            if x.get("name") == "contact":
                e["contact"].append(round(x.get("time", 0), 3))
            elif x.get("name"):
                e["events"].append({"t": round(x.get("time", 0), 3), "name": x["name"]})
    d["events"] = ev
    sounds = []
    for k, arr in blocks.items():
        for a in arr:
            for x in a.get("events", []):
                if x.get("type") == "SoundEventType" and x.get("filename"):
                    sounds.append({"clip": a["name"], "t": round(x.get("time", 0), 3), "event": x["filename"], "bone": x.get("bone_name")})
    # ---- audio: aggro lines (playable ogg) + weapon sound type -----------------------------------
    aggro = None
    if r.get("AggroAudio") is not None:
        try:
            ag = table(store, "monsteraggroaudio"); row_ = ag.row(r["AggroAudio"])
            aggro = {"id": row_["Id"], "event": row_["Audio"], "oggs": [o for o in (row_["OGGFiles"] or []) if o]}
        except Exception:
            aggro = None
    d["audio"] = {"aggro": aggro, "sounds": sounds, "weapon_sound": _name(store, "weaponsoundtypes", r.get("WeaponSoundType"))}
    # ---- related files ---------------------------------------------------------------------------
    misc, seen = [], set()

    def add(p):
        if p and p.lower() not in seen:
            seen.add(p.lower()); misc.append(p)
    for p in d["files"]["ao"]:
        for m in _FILE_RX.finditer(text(store, p.lower())):
            add(m.group(1))
    for k in ("SinkAnimation_AOFile", "SinkEffect"):
        add(r.get(k))
    for s in d.get("skins", []):
        add(s)
    if rig:
        add(rig)
    exist = {x[0] for x in store.db.execute("select path from files where path in (%s)" % ",".join("?" * len(misc)), [m.lower() for m in misc]).fetchall()} if misc else set()
    d["files"]["misc"] = [m for m in misc if m.lower() in exist][:200]
    # monster-folder siblings: the metadata folder and the model folder of the first .ao
    d["folders"] = []
    if aos:
        base = aos[0].rsplit("/", 1)[0].lower() + "/"
        d["folders"].append({"path": base, "files": [x[0] for x in store.db.execute("select path from files where path like ? limit 80", (base + "%",)).fetchall()]})
    # ---- skill -> animation states -> clips -> sounds, plus the numbers of the skill ----------------
    _skill_links(store, d, ge, asr)
    # ---- visual effects: .ao chain, conditional/sink packs, art of the monster's skills -------------------
    art = []
    for sk in d["skills"]:
        if sk.get("as") is not None and not sk["effect"].startswith("MeleeAtAnimationSpeed") and sk.get("name") != "Basic Attack":   # the generic attack art is shared by every monster
            try:
                items = [it for grp in skills.effects_for(store, sk["as"]) for it in grp["items"]]
            except Exception:
                items = []
            if items:
                art.append((sk.get("ru") or sk.get("name") or sk["effect"], items))
    try:
        d["effects"] = effects.monster_effects(store, r, d["files"]["ao"], art)
    except Exception:
        d["effects"] = []
    try:
        d["impacts"] = _impacts(store, d, blocks)
    except Exception:
        d["impacts"] = {"clips": {}, "tex": None}
    # ---- hair / clothes / extra skins -----------------------------------------------------------------
    d["attachments"] = _attachments(store, d["files"]["ao"])
    d["hide"] = sorted({h for a in d["attachments"] for h in a["hide"]})
    # ---- weapons / equipment -----------------------------------------------------------------------
    d["weapons"] = _weapons(store, r)
    d["main_hand"] = _name(store, "itemclasses", r.get("MainHand_ItemClass"), "Name") or _name(store, "itemclasses", r.get("MainHand_ItemClass"))
    d["off_hand"] = _name(store, "itemclasses", r.get("OffHand_ItemClass"), "Name") or _name(store, "itemclasses", r.get("OffHand_ItemClass"))
    # ---- unpackable sounds: FMOD events of the monster's banks ----------------------------------------
    ev_paths = [x["event"] for x in sounds] + ([aggro["event"]] if aggro and aggro.get("event") else [])
    extra = [(d["type"] or "")] + [x for x in reversed((d["id"] or "").split("/")[:-1])][:2] + [re.sub(r"\W", "", d["name"] or "")]
    d["sfx"] = {"banks": [], "events": []}
    try:
        banks = find_banks(store.game, ev_paths, extra)
        if banks:
            res = fmodrender.run(["list", store.game] + banks, timeout=90)
            if res.returncode == 0:
                d["sfx"] = {"banks": banks, "events": json.loads(res.stdout.decode("utf-8", "replace") or "[]")}
    except Exception:
        pass
    byl = {e["path"].lower().replace("event:/", ""): e["path"] for e in d["sfx"]["events"]}
    for x in sounds:
        k = re.sub(r"^audio/", "", x["event"].lower())
        x["sfx"] = byl.get(k) or byl.get(k + "sg")
    return d


# ---- where a monster appears: acts / interlude / endgame / leagues, from the area and monster-pack tables --------------
TAG_ORDER = ["Акт 1", "Акт 2", "Акт 3", "Акт 4", "Акт 5 (в файлах)", "Интерлюдия", "Эндгейм", "Лиги", "Без зоны", "DNT"]
_area_tags = {}


def _area_group(aid):
    m = re.match(r"G(\d)_", aid)
    if m:
        return "Акт " + m.group(1)
    if re.match(r"P\d_", aid):
        return "Интерлюдия"
    if aid.startswith(("Map", "Endgame", "G_Endgame", "BossRush", "TN_")):
        return "Эндгейм"
    if aid.startswith(("Expedition", "Abyss", "Delirium", "Sanctum", "Incursion", "Chayula", "Breach", "Ritual", "Ultimatum", "Hellscape")):
        return "Лиги"
    return None   # NULL / test / hideout areas: carry no information


def area_tags(store):
    """{MonsterVarieties row: [tag]} - acts the monster spawns in (area monster lists + monster packs), propagated to siblings that share a model."""
    key = id(store)
    if key in _area_tags:
        return _area_tags[key]
    a = table(store, "worldareas"); mp = table(store, "monsterpacks"); pe = table(store, "monsterpackentries")
    ids = [a.get(i, "Id") or "" for i in range(len(a))]
    got = {}

    def add(mi, ai):
        if mi is None or ai is None or ai >= len(ids):
            return
        g = _area_group(ids[ai])
        if g:
            got.setdefault(mi, set()).add(g)
    for i in range(len(a)):
        for col in ("Monsters_MonsterVarietiesKeys", "Bosses_MonsterVarietiesKeys"):
            for r in a.get(i, col) or []:
                add(r, i)
    for i in range(len(pe)):
        p, m = pe.get(i, "MonsterPacksKey"), pe.get(i, "MonsterVarietiesKey")
        if p is None or m is None:
            continue
        for col in ("WorldAreas", "WorldAreas2"):
            for ar in mp.get(p, col) or []:
                add(m, ar)
    for i in range(len(mp)):
        for b in mp.get(i, "BossMonsters") or []:
            for col in ("WorldAreas", "WorldAreas2"):
                for ar in mp.get(i, col) or []:
                    add(b, ar)
    rows = store.db.execute("select row,model from monsters").fetchall()
    # Act 5 (Oriath) has no WorldAreas rows in the files yet, but its monsters' effects live in `Act5_FOUR` folders (Fallen Gods, Rooted Guys, ...)
    mv = table(store, "monstervarieties"); chain_cache = {}
    for r, _m in rows:
        for ao in mv.row(r).get("AOFiles") or []:
            for p in _ao_chain(store, ao):
                if p not in chain_cache:
                    chain_cache[p] = bool(re.search(r"(?i)act5_four", text(store, p.lower())))
                if chain_cache[p]:
                    got.setdefault(r, set()).add("Акт 5 (в файлах)")
    bymodel = {}
    for r, mdl in rows:
        if mdl and r in got:
            bymodel.setdefault(mdl, set()).update(got[r])
    out = {}
    for r, mdl in rows:
        s = set(got.get(r, ()))
        if not s and mdl:
            s = set(bymodel.get(mdl, ()))   # same model as a monster that does spawn somewhere
        out[r] = [x for x in TAG_ORDER if x in s] or ["Без зоны"]
        if re.match(r"\s*[\[(]DNT", mv.get(r, "Name") or "", re.I):   # "Do Not Translate": unfinished / internal placeholder entries
            out[r].append("DNT")
    _area_tags[key] = out
    return out


_DMG_RX = re.compile(r"(?:spell|attack|secondary)_(?:minimum|maximum)_base_(\w+?)_damage")


def _skill_links(store, d, ge, asr):
    """Fill s['clips'] (clips of the monster's own .act states named by the skill's animation ids), s['sounds'] (sound events on those clips) and s['info'] (cast time, crit, damage multiplier, damage types, stat lines)."""
    st = {x["state"]: x["clips"] for x in d.get("states", [])}
    have = set(d.get("clips") or [])
    by_clip = {}
    for x in d["audio"]["sounds"]:
        by_clip.setdefault(x["clip"], []).append(x)
    ty = table(store, "activeskilltype")
    for s in d["skills"]:
        clips = []
        for a in s.get("animation") or []:
            for c in st.get(a, []):
                if c not in clips and (not have or c in have):
                    clips.append(c)
        s["clips"] = clips
        s["sounds"] = [x for c in clips for x in by_clip.get(c, [])]
        info = {"cast_time": s.get("cast_time")}
        s["info"] = info
    ids = {ge.get(i, "Id"): i for i in range(len(ge))}
    for s in d["skills"]:
        gi = ids.get(s["effect"])
        if gi is None:
            continue
        info = s["info"]
        try:
            lv = skills.levels_for(store, gi)
            if lv:
                info.update({"cooldown": lv[0]["cooldown"], "uses": lv[0]["uses"], "atk_speed": lv[0]["atk_speed"]})
            csd = None
            if s.get("as") is not None:
                csd = asr.get(s["as"], "StatDescription")
                tys = asr.get(s["as"], "ActiveSkillTypes") or []
                info["types"] = [ty.get(k, "Id") for k in tys if k is not None and k < len(ty)]
            sts = skills.stats_for(store, gi, csd)
            lines, lines_ru, const, dtypes = [], [], {}, []
            for sset in sts:
                const.update(sset["const"])
                lvl = sset["levels"][0] if sset["levels"] else None
                if lvl:
                    info.setdefault("crit", lvl["crit"]); info.setdefault("mult", lvl["mult"]); info.setdefault("dmg", lvl["dmg"])
                    lines += lvl["text"]; lines_ru += lvl["text_ru"]
                    for k in list(lvl["stats"]) + list(sset["const"]):
                        m = _DMG_RX.fullmatch(k)
                        if m and m.group(1) not in dtypes:
                            dtypes.append(m.group(1))
            info.update({"lines": lines, "lines_ru": lines_ru, "const": const, "dtypes": dtypes})
        except Exception as e:
            info["error"] = str(e)
