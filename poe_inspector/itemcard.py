"""Card of a base item: art, description, flavour, gem data, 'sources' (uniques built on this base) and the model the character wears."""
import re
from .datrows import table
from . import iteminfo, gems

DNT = re.compile(r"^\s*\[(DNT[^\]]*|UNUSED)\]\s*", re.I)
_cur = {}


def clean_name(name):
    return DNT.sub("", name or "").strip()


def dnt_kind(name):
    """'' for a normal name; 'unused' for [DNT-UNUSED] / [UNUSED] / 'not shown/visible to players'; 'dnt' for other [DNT] placeholders."""
    n = name or ""
    if not DNT.match(n):
        return ""
    if re.search(r"UNUSED|not shown|not visible", n, re.I):
        return "unused"
    return "dnt"


def markup(t):
    t = re.sub(r"\[([^\]|]*)\|([^\]]*)\]", r"\2", t or "")
    return re.sub(r"\[([^\]]*)\]", r"\1", t).replace("\n", "\n").strip()


def _descriptions(store):
    if not _cur:
        try:
            c = table(store, "currencyitems")
            for i in range(len(c)):
                d = c.get(i, "Description")
                if d:
                    _cur[c.get(i, "BaseItemType")] = (markup(d), c.get(i, "StackSize"))
        except Exception:
            pass
    return _cur


def _flavour(store, key):
    """BaseItemTypes.FlavourText is a row reference into FlavourText.Text."""
    if key is None or key == "":
        return ""
    if isinstance(key, int):
        try:
            return markup(table(store, "flavourtext").get(key, "Text"))
        except Exception:
            return ""
    return markup(key)


_EQUIP = re.compile(r"Hand|Bows|Crossbow|Dagger|Claw|Flail|Stav|Spear|Wand|Sceptre|Quiver|Foci|Shield|Buckler|Armour|Helmet|Gloves|Boots", re.I)


def card(store, row):
    r = store.db.execute("select id,name,icon,ao,ao2,model,class from items where row=?", (row,)).fetchone()
    if not r:
        return None
    iid, name, icon, ao, ao2, model, cls = r
    bt = table(store, "baseitemtypes")
    out = {"row": row, "id": iid, "name": clean_name(name), "dnt": dnt_kind(name), "rawName": name, "icon": icon, "class": cls,
           "level": bt.get(row, "DropLevel"), "size": [bt.get(row, "Width"), bt.get(row, "Height")],
           "flavour": _flavour(store, bt.get(row, "FlavourText")), "model": model}
    desc, stack = _descriptions(store).get(row, ("", None))
    out["description"] = desc
    out["stack"] = stack or None
    out["info"] = iteminfo.info(store, row)
    out["worn"] = iteminfo.worn_model(store, ao, ao2, cls) if model and _EQUIP.search(cls or "") else None   # only gear has a worn version
    g = next((x for x in gems.all_gems(store) if x.get("name") == clean_name(name) or x.get("name") == name), None)
    if g:
        out["gem"] = {"kind": g.get("kind"), "tags": g.get("tags"), "text": g.get("text") or g.get("desc"), "k": g.get("k"), "minlvl": g.get("minlvl")}
        if not out["description"]:
            out["description"] = markup(g.get("desc") or g.get("text") or "")
    out["sources"] = [{"kind": "unique", "name": n, "icon": i} for n, i in store.db.execute("select name,icon from uniques where base=? order by name", (out["name"],))]
    return out
