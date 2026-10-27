"""Weapons and shields that NPCs / monsters carry (MonsterVarieties Weapon1/Weapon2 -> ItemVisualIdentity) as wearable entries for the editor."""
import re
from .datrows import table
from . import actor, mesh

_cache = {}
FIELDS = (("Weapon1_ItemVisualIdentity", "weapon"), ("Weapon2_ItemVisualIdentity", "offhand"))


def _pretty(s):
    s = re.sub(r"[_\d]+$", "", s or "")
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s).strip() or (s or "?")


CLASS_OF_DIR = {"OneHandSwords": "One Hand Swords", "TwoHandSwords": "Two Hand Swords", "OneHandAxes": "One Hand Axes", "TwoHandAxes": "Two Hand Axes",
                "Daggers": "Daggers", "Spears": "Spears", "Staves": "Staves", "Warstaves": "Warstaves", "OneHandMaces": "One Hand Maces",
                "TwoHandMaces": "Two Hand Maces", "Wands": "Wands", "Sceptres": "Sceptres", "Claws": "Claws", "Bows": "Bows",
                "Crossbows": "Crossbows", "Flails": "Flails", "Quarterstaves": "Quarterstaves", "Shields": "Shields", "Bucklers": "Bucklers"}


def _class_of(path):
    for part in path.replace("\\", "/").split("/"):
        if part in CLASS_OF_DIR:
            return CLASS_OF_DIR[part]
    return None


def _usable(store, ao, ao2, slot):
    """True when the entry resolves to something drawable (a parsable fixed mesh or a skin)."""
    try:
        e = actor.equipped(store, "npc", "npc", ao, slot, ao2)
        if e.get("fixed"):
            b = store.read(e["fixed"])
            if b is None:
                return False
            mesh.parse(e["fixed"], b)
            return True
        return bool(e.get("skins"))
    except Exception:
        return False


def npc_items(store):
    """{id: {id, name, slot, ao, ao2, by}} — unique held models, named after the model plus the first monster that uses it."""
    if _cache:
        return _cache
    mv, ivi = table(store, "monstervarieties"), table(store, "itemvisualidentity")
    seen, ok_cache = {}, {}
    for row, mname in store.db.execute("select row,name from monsters order by name"):
        d = mv.row(row)
        for field, slot in FIELDS:
            for i in d.get(field) or []:
                a2 = ivi.get(i, "AOFile2") or ""
                if not a2 or not a2.lower().endswith((".ao", ".fmt")):
                    continue
                key = (a2.lower(), slot)
                if key in seen:
                    seen[key]["n"] += 1
                    continue
                ao = ivi.get(i, "AOFile") or ""
                if a2.lower().endswith(".ao") or not ao or "Currency" in ao or "Rings" in ao:
                    ao = a2
                seen[key] = {"id": f"npc:{i}:{slot}", "name": f"{_pretty(ivi.get(i, 'Id'))} (NPC)", "slot": slot, "ao": ao, "ao2": a2, "by": mname, "n": 1, "ivi": i, "class": _class_of(a2)}
    out, names = {}, {}
    for key, it in seen.items():
        if not _usable(store, it["ao"], it["ao2"], it["slot"]):
            continue
        it["name"] = f"{it['name']} — {it['by']}"
        names.setdefault(it["name"], []).append(it)
        out[it["id"]] = it
    for same in names.values():
        if len(same) > 1:   # several models share a name: tell them apart by file name
            for it in same:
                it["name"] += " · " + it["ao2"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
    _cache.update(out)
    return _cache


def for_slot(store, ed_slot):
    return [u for u in npc_items(store).values() if u["slot"] == ed_slot]
