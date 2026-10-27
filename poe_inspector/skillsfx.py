"""Sounds of a skill: SoundEvent entries of its animation timeline (.atl, with the time inside every clip), of its effect .ao files,
and the events of the skill's own FMOD bank. Rendering goes through sfx.render (cached WAV)."""
import json, os, re
from .catalog import text
from . import fmodrender, monster, skills

from .paths import DATA as ROOT
_GENERIC = {"audio", "sound effects", "skills", "4.0", "misc", "combat", "event:", "event"}
ATTRS = ("Str", "Dex", "Int", "StrDex", "StrInt", "DexInt")


def _timeline_sounds(store, path, seen=None, depth=0):
    """{clip: [{t, event, bone}]}: sound events of every timeline animation, including the ones it inherits (`inherit_animation_events`)
    and registered under the clip it views (`view.of`, also without the _stationary/_moving suffix) as well as under its own name."""
    out = {}
    if not path or depth > 4:
        return out
    t = text(store, path.lower())
    if not t:
        return out
    try:
        j = json.loads(t)
    except Exception:
        return out
    if j.get("extends"):
        out.update(_timeline_sounds(store, j["extends"], seen, depth + 1))
    anims = {a["name"]: a for a in j.get("animations", [])}

    def own(a):
        ev = []
        for blk in ("events", "client_events"):
            for e in a.get(blk, []):
                if e.get("type") == "SoundEventType" and e.get("filename"):
                    ev.append({"t": round(e.get("time", 0), 3), "event": e["filename"], "bone": e.get("bone_name")})
        return ev

    def full(name, stack=()):
        a = anims.get(name)
        if not a or name in stack:
            return []
        ev = list(own(a))
        for inh in (a.get("inherit_animation_events") or (a.get("view") or {}).get("inherit_animation_events") or []):
            ev += full(inh, stack + (name,))
        return ev
    for name, a in anims.items():
        ev = sorted(full(name), key=lambda x: x["t"])
        if not ev:
            continue
        keys = {name}
        view = (a.get("view") or {}).get("of")
        if view:
            keys |= {view, re.sub(r"_(stationary|moving)$", "", view)}
        for k in keys:
            out[k] = ev
    return out


def _timeline_contacts(store, path, depth=0):
    """{clip: time of the first `contact` event} with inheritance, registered under the animation name and the clip it views."""
    out = {}
    if not path or depth > 4:
        return out
    t = text(store, path.lower())
    if not t:
        return out
    try:
        j = json.loads(t)
    except Exception:
        return out
    if j.get("extends"):
        out.update(_timeline_contacts(store, j["extends"], depth + 1))
    anims = {a["name"]: a for a in j.get("animations", [])}

    def own(a):
        return [e.get("time", 0) for e in a.get("events", []) if e.get("name") == "contact"]

    def full(name, stack=()):
        a = anims.get(name)
        if not a or name in stack:
            return []
        ev = own(a)
        for inh in (a.get("inherit_animation_events") or (a.get("view") or {}).get("inherit_animation_events") or []):
            ev += full(inh, stack + (name,))
        return ev
    for name, a in anims.items():
        ev = full(name)
        if not ev:
            continue
        keys = {name}
        view = (a.get("view") or {}).get("of")
        if view:
            keys |= {view, re.sub(r"_(stationary|moving)$", "", view)}
        for k in keys:
            out[k] = round(min(ev), 3)
    return out


def _ao_sounds(store, ao):
    """Sound events of an effect .ao (any block's animation list)."""
    t = text(store, ao.lower())
    out = []
    for m in re.finditer(r"animations\s*=\s*'(\[.*?\])'", t, re.S):
        try:
            arr = json.loads(m.group(1))
        except Exception:
            continue
        for a in arr:
            for e in a.get("events", []):
                if e.get("type") == "SoundEventType" and e.get("filename"):
                    out.append({"anim": a.get("name"), "t": round(e.get("time", 0), 3), "event": e["filename"]})
    return out


def _candidate_banks(game, events):
    """Banks named after folders of the event paths: Mace/Sunder -> Four_Sunder, Surges/Rock -> Four_RockSurges, Vocal/Str/Efforts -> StrFour_VocalEfforts ..."""
    names = monster._bank_names(game)
    by_stem = {}
    for low, real in names.items():
        stem = re.sub(r"\.bank$", "", low)
        for pre in ("four_", "4.0_"):
            if stem.startswith(pre):
                stem = stem[len(pre):]
        by_stem.setdefault(re.sub(r"[_\s]+", "", stem), real)
    out = []

    def add(b):
        if b and b not in out:
            out.append(b)
    for e in events:
        parts = [x for x in re.split(r"[/\\]", e) if x]
        low = [p.lower() for p in parts]
        if "vocal" in low and "efforts" in low:
            i = low.index("vocal")
            if i + 1 < len(parts) and parts[i + 1] in ATTRS:
                add(names.get((parts[i + 1] + "Four_VocalEfforts.bank").lower()))
            continue
        toks = [re.sub(r"[_\s]+", "", p).lower() for p in parts[:-1] if p.lower() not in _GENERIC]
        # armour / footstep helpers keep their own words
        toks += [re.sub(r"[_\s]+", "", x).lower() for x in re.split(r"[_/]", parts[-1]) if x]
        toks += [x.lower() for p in parts[:-1] if p.lower() not in _GENERIC for x in p.split("_") if x and "_" in p]
        pairs = [x + y for x in toks for y in toks if x != y and len(x) > 2 and len(y) > 2]
        cand = pairs + [x + 's' for x in pairs]
        for i, a in enumerate(toks):
            cand += [a, a + "s", a.rstrip("s")]
            for b in toks[i + 1:i + 2] + toks[max(0, i - 1):i]:
                cand += [a + b, b + a, a + b + "s", b + a + "s"]
        for c in cand:
            add(by_stem.get(c))
    return out[:14]


_IDX = {}


def _index():
    """event path (lower, no `event:/`) -> [(event path, bank)] over every bank of the game (built once into cache/fmod_event_index.json)."""
    if "e" not in _IDX:
        p = os.path.join(ROOT, "cache", "fmod_event_index.json")
        _IDX["e"] = json.load(open(p, encoding="utf-8"))["events"] if os.path.exists(p) else {}
    return _IDX["e"]


def _link(store, x):
    """Attach the FMOD event + its bank, or a plain .ogg file of the bundles, to a sound entry."""
    idx = _index()
    k = re.sub(r"^audio/", "", x["event"].lower())
    base = re.sub(r"(\.(once|loop))?\.ogg$", "", k)
    for c in (k, k + "sg", base, base + "sg"):
        hit = idx.get(c)
        if hit:
            x["sfx"], x["bank"] = hit[0][0], hit[0][1]
            return
    if k.endswith(".ogg"):
        for c in (k, k.replace("$(#)", "1"), k.replace("$(#)", "01")):
            if store.find("audio/" + c):
                x["ogg"] = "Audio/" + (x["event"][6:] if x["event"].lower().startswith("audio/") else x["event"]).replace("$(#)", "1" if c == k.replace("$(#)", "1") else "01")
                return


def skill_sounds(store, d):
    """d is skills.detail(): returns {banks, clips: {clip: [...]}, art: [...], bank_events: [...]}; every entry has sfx+bank (FMOD) or ogg (plain file)."""
    clips = {}
    for a in d.get("anim", []):
        tl = a.get("timeline")
        if not tl:
            continue
        for clip, ev in _timeline_sounds(store, tl).items():
            clips.setdefault(clip, ev)
    art = []
    for g in d.get("art", []):
        for it in g.get("items", []):
            for f in it.get("files", []):
                if f.lower().endswith(".ao"):
                    for s_ in _ao_sounds(store, f):
                        art.append({**s_, "from": f.rsplit("/", 1)[-1]})
    for v in clips.values():
        for x in v:
            _link(store, x)
    for x in art:
        _link(store, x)
    used = {x["sfx"] for v in clips.values() for x in v if x.get("sfx")} | {x["sfx"] for x in art if x.get("sfx")}
    banks = sorted({x["bank"] for v in clips.values() for x in v if x.get("bank")} | {x["bank"] for x in art if x.get("bank")})
    # events of the skill's own bank(s) that nothing names explicitly (cascade, debris ...)
    name = re.sub(r"[^a-z0-9]", "", (d.get("name") or "").lower())
    own = {b for b in banks if name and name in re.sub(r"[^a-z0-9]", "", b.lower())}
    extra = []
    if own:
        for hits in _index().values():
            for path, bank in hits:
                if bank in own and path not in used:
                    extra.append({"path": path, "bank": bank})
    contacts = {}
    for a_ in d.get("anim", []):
        if a_.get("timeline"):
            contacts.update(_timeline_contacts(store, a_["timeline"]))
    return {"banks": banks, "clips": clips, "art": art, "contacts": contacts, "bank_events": sorted(extra, key=lambda e: e["path"])}


def cached(store, i):
    cdir = os.path.join(ROOT, "cache", "skillsfx"); os.makedirs(cdir, exist_ok=True)
    gp = os.path.join(cdir, f"{i}_v5.json")
    if not os.path.exists(gp):
        d = skills.detail(store, i)
        json.dump(skill_sounds(store, d), open(gp, "w", encoding="utf-8"), ensure_ascii=False)
    return json.load(open(gp, encoding="utf-8"))
