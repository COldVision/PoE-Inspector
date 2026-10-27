"""Druid shapeshift forms (bear / wolf / wyvern): the model + the animation clips behind the skills that are performed in a form.

ShapeshiftForms.AOFile names the form's .act (animation state -> clip names); its .ao holds the rig and the skin; the clips of a skill live in
`.../Shapeshifters/<form>/Animations/<skill>/rig.ast`, which shares the skeleton of the form's base rig."""
import re
from . import actor, monster, skills

FORMS = [
    ("bear", "Медведь", "metadata/monsters/werebear/werebear.ao", "metadata/monsters/werebear/werebearplayer.act", "art/models/charactersfour/shapeshifters/bear/"),
    ("wolf", "Волк", "metadata/monsters/werewolf/werewolf.ao", "metadata/monsters/werewolf/werewolfplayer.act", "art/models/charactersfour/shapeshifters/wolf/"),
    ("wyvern", "Виверна", "metadata/monsters/werewyvern/werewyvern.ao", "metadata/monsters/werewyvern/werewyvernplayer.act", "art/models/charactersfour/shapeshifters/wyvern/"),
]
_cache = {}


def _defs(store, act):
    """State definitions of a form's .act (same syntax as character.act), on top of the character templates."""
    from .catalog import text
    t = re.sub(r"//[^\n]*", "", text(store, act.lower())); own = {}
    for m in re.finditer(r"^[ \t]*((?:Template::)?[\w:]+)\s*=\s*(.*?);", t, re.M | re.S):
        own.setdefault(m.group(1), m.group(2))
    d = dict(skills.act_defs(store)); d.update(own)
    return d, own


def forms(store):
    if "f" in _cache:
        return _cache["f"]
    out = []
    for fid, ru, ao, act, folder in FORMS:
        try:
            f = actor.ao_fields(store, ao)
        except Exception:
            continue
        if not f.get("skeleton") or not f.get("skins"):
            continue
        defs, own = _defs(store, act)
        out.append({"id": fid, "ru": ru, "ao": ao, "act": act, "folder": folder, "skeleton": f["skeleton"], "skin": f["skins"][0], "defs": defs, "own": set(own)})
    _cache["f"] = out
    return out


def _resolve(form, state, depth=0):
    """Clip names a state plays (templates expanded, "@Other" references followed)."""
    rhs = form["defs"].get(state)
    if not rhs or depth > 6:
        return []
    out = []
    for pats, _tl in skills.expand_state(form["defs"], rhs):
        for p in pats:
            out += _resolve(form, p[1:], depth + 1) if p.startswith("@") else [p]
    return out


def _pack(store, form):
    """clip name -> [ast paths] over the form's base rig and all of its animation packs (they are not in the anim_clips index)."""
    if "pack" not in form:
        from . import ast as astmod
        m = {}
        paths = [form["skeleton"].lower()] + [p for p, _ in store.search(form["folder"] + "animations/%", "ast", 400)]
        for p in paths:
            try:
                a = astmod.load(store, p)
            except Exception:
                a = None
            for c in (a.clips if a else []):
                m.setdefault(c["name"], []).append(p)
        form["pack"] = m
    return form["pack"]


def _clips(store, form, names):
    """Clip names (patterns with * allowed) -> [{ast, clip}] among the animation packs of the form."""
    pack, res, seen = _pack(store, form), [], set()
    for n in names:
        rx = re.compile("^" + re.escape(n).replace(r"\*", "[a-z0-9_]+") + "$")
        for clip, asts in pack.items():
            if rx.match(clip):
                for ast in asts:
                    if (ast, clip) not in seen:
                        seen.add((ast, clip)); res.append({"ast": ast, "clip": clip})
    return res


GENERIC = {"Melee", "OffMelee", "Channel", "Cast", "Idle", "Run", "Attack", "OffAttack", "PlaceTotemStomp", "PlaceTotem"}


def _norm(x):
    return re.sub(r"[^a-z]", "", (x or "").lower())


def for_skill(store, ge_row, name=""):
    """The form + clips of a skill performed in a shapeshift form, or None.
    The first animation state of the skill that a form's .act defines wins; skills without such a state fall back to the animation pack named like the skill."""
    chain = skills.anim_chain(store, ge_row)
    for st in chain:
        if st in GENERIC:
            continue
        for f in forms(store):
            if st in f["own"]:
                clips = _clips(store, f, _resolve(f, st))
                if clips:
                    anim = [{"state": st, "clips": clips}]
                    for st2 in chain[chain.index(st) + 1:]:
                        if st2 not in GENERIC and st2 in f["own"]:
                            c2 = _clips(store, f, _resolve(f, st2))
                            if c2:
                                anim.append({"state": st2, "clips": c2})
                    return {"id": f["id"], "ru": f["ru"], "skeleton": f["skeleton"], "skin": f["skin"], "anim": anim}
    n = _norm(name)
    if n:
        for f in forms(store):
            for p, _sz in store.search(f["folder"] + "animations/%", "ast", 400):
                pk = p[len(f["folder"] + "animations/"):].split("/")[0]
                if pk and (pk == n or (len(pk) >= 4 and pk in n)) and pk not in ("blink", "warcry", "shapeshifting", "groundstomp", "ascendancymartialartist", "tormentedspirit", "vesselofwrath"):
                    from . import ast as astmod
                    a = astmod.load(store, p)
                    clips = [{"ast": p, "clip": c["name"]} for c in (a.clips if a else []) if not re.search(r"_(moving|stationary)$|standing", c["name"])]
                    if clips:
                        return {"id": f["id"], "ru": f["ru"], "skeleton": f["skeleton"], "skin": f["skin"], "anim": [{"state": pk, "clips": clips}]}
    return None
