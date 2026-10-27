"""Short description of a base item for the hover tooltip: armour / weapon numbers and requirements from the game tables."""
from .datrows import table

_idx = {}


def _index(store):
    if _idx:
        return _idx
    for name, key in (("armourtypes", "arm"), ("weapontypes", "wep"), ("shieldtypes", "shd"), ("attributerequirements", "req")):
        try:
            t = table(store, name); m = {}
            for i in range(len(t)):
                m[t.get(i, "BaseItemType")] = t.row(i)
            _idx[key] = m
        except Exception:
            _idx[key] = {}
    return _idx


def info(store, row):
    ix = _index(store)
    bi = table(store, "baseitemtypes").row(row)
    out = {"name": bi.get("Name"), "level": bi.get("DropLevel"), "base": {}}
    a = ix["arm"].get(row)
    if a:
        out["base"]["armour"] = {"Armour": a["Armour"], "Evasion": a["Evasion"], "EnergyShield": a["EnergyShield"], "Ward": a["Ward"]}
        if a.get("IncreasedMovementSpeed"):
            out["base"]["move"] = a["IncreasedMovementSpeed"] / 100.0
    w = ix["wep"].get(row)
    if w:
        out["base"]["weapon"] = {"PhysicalMin": w["DamageMin"], "PhysicalMax": w["DamageMax"], "CritChanceBase": (w["CritChance"] or 0) / 100.0,
                                 "AttackRateBase": (1000.0 / w["Speed"]) if w.get("Speed") else None}
    sh = ix["shd"].get(row)
    if sh and sh.get("Block"):
        out["base"]["block"] = sh["Block"]
    r = ix["req"].get(row)
    if r:
        out["base"]["req"] = {"str": r["ReqStr"], "dex": r["ReqDex"], "int": r["ReqInt"]}
    return out


_SLOT = {"Body Armours": "body", "Helmets": "helmet", "Gloves": "gloves", "Boots": "boots", "Shields": "offhand", "Bucklers": "offhand", "Foci": "offhand", "Quivers": "offhand"}
_worn = {}


def worn_model(store, ao, ao2, cls):
    """Model the character actually wears/holds (the .smd behind the equipped .ao skin), or None when it is the same as the drop model."""
    key = (ao, ao2, cls)
    if key in _worn:
        return _worn[key]
    res = None
    try:
        from . import actor, catalog
        e = actor.equipped(store, "", ao or "", ao, _SLOT.get(cls, "weapon"), ao2 or None, "str")
        if e.get("fixed"):
            res = e["fixed"]
        elif e.get("skins"):
            sm = e["skins"][0]
            res = catalog.SM_SMD.search(catalog.text(store, sm) or "")
            res = res.group(1).lower() if res else None
    except Exception:
        res = None
    _worn[key] = res
    return res
