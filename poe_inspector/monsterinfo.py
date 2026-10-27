"""Everything the game data says about one monster (MonsterVarieties row): stats, skills, animations (+ events from its .ao),
sound events / audio files, and related files in the index."""
import json, os, re
from .datrows import table
from .catalog import text
from . import actor, ast as astmod

FILE_EXT = ("ao", "act", "ais", "ast", "sm", "smd", "fmt", "mat", "pet", "epk", "amd", "atl", "dds", "ogg", "tgm", "ecf", "ot", "otc")


def _names(store, tname, ids, col="Id"):
    try:
        t = table(store, tname)
    except Exception:
        return [str(i) for i in ids]
    out = []
    for i in ids or []:
        if i is not None and i < len(t):
            out.append(t.get(i, col) or str(i))
    return out


def ao_chain(store, path, depth=0, seen=None):
    """Texts of an .ao and the files it extends (nearest first)."""
    seen = seen if seen is not None else set()
    path = path.lower()
    if depth > 6 or path in seen:
        return []
    seen.add(path)
    t = text(store, path)
    if not t:
        return []
    out = [(path, t)]
    m = re.search(r'^extends\s+"([^"]+)"', t, re.M)
    if m and m.group(1).lower() != "metadata/parent":
        p = m.group(1).lower()
        if not p.endswith(".ao"):
            p += ".ao"
        out += ao_chain(store, p, depth + 1, seen)
    return out


def _json_blocks(t):
    for m in re.finditer(r"animations\s*=\s*'(\[.*?\])'", t, re.S):
        try:
            yield json.loads(m.group(1))
        except Exception:
            continue


def detail(store, row):
    mv = table(store, "monstervarieties"); r = mv.row(row)
    try:
        ru = table(store, "monstervarieties", "russian").get(row, "Name")
    except Exception:
        ru = ""
    d = {"row": row, "id": r["Id"], "name": r["Name"], "ru": ru, "ao": (r["AOFiles"] or [None])[0], "act": (r["ACTFiles"] or [None])[0], "ais": r["AISFile"]}
    d["stats"] = {"type": (_names(store, "monstertypes", [r["MonsterType"]]) or [""])[0], "category": (_names(store, "monstercategories", [r["MonsterCategory"]], "Name") or [""])[0] if r["MonsterCategory"] is not None else "",
                  "speed": r["MovementSpeed"], "size": r["ObjectSize"], "size_mult": r["ModelSizeMultiplier"], "attack_dist": [r["MinimumAttackDistance"], r["MaximumAttackDistance"]],
                  "life": r["LifeMultiplier"], "damage": r["DamageMultiplier"], "attack_speed": r["AttackSpeed"], "exp": r["ExperienceMultiplier"], "agro": [r["MinAgroRange"], r["MaxAgroRange"]],
                  "poise": r["PoiseThreshold"], "crit": r["AttackCrit"], "boss_bar": bool(r["BossHealthBar"]), "stance": r["Stance"]}
    d["tags"] = _names(store, "tags", r["Tags"]); d["mods"] = _names(store, "mods", (r["Mods"] or []) + (r["Mods2"] or []) + (r["Special_Mods"] or []) + (r["Part1_Mods"] or []) + (r["Part2_Mods"] or []) + (r["Endgame_Mods"] or []))
    # skills
    from . import skills as sk
    ge = table(store, "grantedeffects"); act = table(store, "activeskills"); actr = table(store, "activeskills", "russian"); lst = {x["i"]: x for x in sk.skill_list(store)}
    d["skills"] = []
    for g in (r["GrantedEffects"] or []):
        if g is None or g >= len(ge):
            continue
        a = ge.get(g, "ActiveSkill"); s = {"ge": ge.get(g, "Id"), "cast_time": ge.get(g, "CastTime")}
        if a is not None and a < len(act):
            s.update({"skill": a, "name": act.get(a, "DisplayedName"), "ru": actr.get(a, "DisplayedName"), "icon": act.get(a, "Icon_DDSFile"), "desc": act.get(a, "Description"), "desc_ru": actr.get(a, "Description"), "player": a in lst and lst[a]["ge"] > 0 and lst[a]["gem"]})
        d["skills"].append(s)
    # animations + sounds from the .ao chain
    chain = ao_chain(store, d["ao"]) if d["ao"] else []
    anims, sounds, effects = {}, [], []
    for p, t in chain:
        for blk in _json_blocks(t):
            for a in blk:
                n = a.get("name")
                if n and n not in anims:
                    anims[n] = [{"t": round(e.get("time", 0), 3), "name": e.get("name") or e.get("type"), "file": e.get("filename")} for e in a.get("events", [])][:20]
        for f in re.findall(r'"filename":\s*"([^"]+)"', t):
            (sounds if f.lower().startswith("audio/") else effects).append(f)
    # aggro audio
    d["audio"] = {"weapon_sound": None, "aggro": None, "ogg": []}
    try:
        ws = r["WeaponSoundType"]
        if ws is not None:
            wt = table(store, "weaponsoundtypes"); d["audio"]["weapon_sound"] = [wt.get(ws, "Id"), wt.get(ws, "Sound")]
        ag = r["AggroAudio"]
        if ag is not None:
            at = table(store, "monsteraggroaudio"); d["audio"]["aggro"] = {"id": at.get(ag, "Id"), "event": at.get(ag, "Audio")}
            d["audio"]["ogg"] += [x for x in (at.get(ag, "OGGFiles") or []) if x]
    except Exception:
        pass
    d["audio"]["events"] = list(dict.fromkeys(sounds))[:200]
    d["audio"]["ogg"] = [p for p in d["audio"]["ogg"] if store.find(p)]
    # skeleton / skin / clips
    d["rig"] = None
    try:
        f = actor.ao_fields(store, d["ao"]) if d["ao"] else None
        if f and f["skeleton"] and f["skins"]:
            a = astmod.load(store, f["skeleton"].lower())
            d["rig"] = {"skeleton": f["skeleton"].lower(), "skin": f["skins"][0].lower()}
            names = [c["name"] for c in a.clips] if a else []
            d["clips"] = [{"name": n, "events": anims.get(n, [])} for n in names]
    except Exception as e:
        d["rig_error"] = str(e)
    d.setdefault("clips", [])
    d["anim_events"] = {k: v for k, v in anims.items() if k not in {c["name"] for c in d["clips"]}}
    d["effects"] = list(dict.fromkeys(effects))[:100]
    # related files: by the monster's folder names
    toks = set()
    for p in filter(None, [d["ao"], d["act"], d["ais"], (d["rig"] or {}).get("skeleton"), d["id"]]):
        parts = [x for x in p.lower().replace(".ao", "").replace(".act", "").replace(".ais", "").split("/") if x and x not in ("metadata", "monsters", "art", "models", "rig.ast")]
        if parts:
            toks.add(parts[0] if "/" in p and len(parts) > 1 else parts[-1])
    files = {}
    for tk in sorted(toks)[:3]:
        if len(tk) < 4:
            continue
        for path, ext in store.db.execute("select path,ext from files where path like ? and ext not in ('header','') limit 800", (f"%/{tk}/%",)).fetchall():
            files[path] = ext
    d["files"] = [{"path": p, "ext": e} for p, e in sorted(files.items(), key=lambda x: (x[1], x[0]))][:600]
    d["tokens"] = sorted(toks)
    return d
