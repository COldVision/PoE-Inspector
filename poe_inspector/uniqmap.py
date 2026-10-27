"""Unique items as wearable entries: UniqueStashLayout links Words (the unique's name) to an ItemVisualIdentity row (drop .ao, held .ao, effect pack)."""
import re
from .datrows import table

SLOT_OF = {"body": "body", "helmet": "helmet", "gloves": "gloves", "boots": "boots", "shield": "offhand", "focus": "offhand", "quiver": "offhand",
           "mace": "weapon", "staff": "weapon", "bow": "weapon", "spear": "weapon", "wand": "weapon", "sceptre": "weapon", "crossbow": "weapon"}
_map = {}


def unique_items(store):
    """{name: {name, base, slot, ao, ao2, ivi, class, icon}} for the uniques that have a visual identity."""
    if _map:
        return _map
    usl, w, ivi = table(store, "uniquestashlayout"), table(store, "words"), table(store, "itemvisualidentity")
    by_name = {}
    for i in range(len(usl)):
        wk, ik = usl.get(i, "WordsKey"), usl.get(i, "ItemVisualIdentityKey")
        if wk is None or ik is None or wk >= len(w) or ik >= len(ivi):
            continue
        by_name.setdefault(w.get(wk, "Text"), []).append((bool(usl.get(i, "IsAlternateArt")), ik))
    cls = {r[0]: r[1] for r in store.db.execute("select name,class from items where class is not null").fetchall()}
    for name, base, slot, icon in store.db.execute("select name,base,slot,icon from uniques").fetchall():
        c = by_name.get(name)
        if not c:
            continue
        ik = sorted(c)[0][1]
        ao = ivi.get(ik, "AOFile")
        if not ao:
            continue
        _map[name] = {"name": name, "base": base, "slot": slot, "ao": ao, "ao2": ivi.get(ik, "AOFile2") or None, "ivi": ik,
                      "class": cls.get(base), "icon": icon, "id": "unique:" + name}
    return _map


def for_slot(store, ed_slot):
    return [u for u in unique_items(store).values() if SLOT_OF.get(u["slot"]) == ed_slot]
