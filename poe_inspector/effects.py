"""Visual effects linked to an item or a monster: particle systems (.pet), effect packs (.epk), trails (.trl) and effect .ao files,
collected from the item/monster .ao chain, the ItemVisualIdentity row (microtransaction effect packs), conditional monster packs and skill art."""
import json, re
from .catalog import text
from .datrows import table

_FILE_RX = re.compile(r'"([^"\n]+?\.(?:pet|epk|trl|ecf|ao))"', re.I)
_KINDS = ("pet", "epk", "trl", "ecf", "ao")
_ivi_by_ao = {}


def _norm(p):
    p = re.sub(r"/+", "/", p.replace("\\", "/").strip())
    return "Art/" + p if p.lower().startswith("models/") else p


def _exists(store, p):
    return bool(p) and bool(store.find(p.lower()))


def _split_bone(raw):
    """`"skull Metadata/Effects/x.pet"` -> ("skull", "Metadata/Effects/x.pet"): effect lines may start with the bone they are attached to."""
    parts = raw.split(None, 1)
    if len(parts) == 2 and "/" not in parts[0] and "\\" not in parts[0] and "." not in parts[0]:
        return parts[0], parts[1]
    return None, raw


def _refs(store, ao_path, depth=0, seen=None):
    """Files an .ao references (recursing into effect .ao files); returns [(path, via, bone)] without duplicates."""
    seen = seen if seen is not None else set()
    out = []
    key = ao_path.lower()
    if key in seen or depth > 3:
        return out
    seen.add(key)
    t = text(store, key)
    for m in _FILE_RX.finditer(t):
        bone, raw = _split_bone(m.group(1))
        p = _norm(raw)
        if p.lower() == key or p.lower() in seen or not _exists(store, p):
            continue
        ext = p.rsplit(".", 1)[-1].lower()
        if ext == "ao":
            if p.lower().startswith("metadata/effects/"):
                out.append((p, ao_path, bone))
                out += _refs(store, p, depth + 1, seen)
            continue
        out.append((p, ao_path, bone))
    return out


def _describe(store, path, via=None, bone=None):
    ext = path.rsplit(".", 1)[-1].lower()
    d = {"path": path, "kind": ext, "pets": [], "mats": []}
    if bone:
        d["bone"] = bone
    if via:
        d["via"] = via
    if ext == "epk":
        t = text(store, path.lower())
        try:
            d["mats"] = [x for x in re.findall(r'"filename"\s*:\s*"([^"]+)"', t)][:12]
        except Exception:
            pass
    elif ext == "pet":
        d["pets"] = [path]
    elif ext == "ao":
        d["pets"] = [p for p, _v, _b in _refs(store, path) if p.lower().endswith(".pet")]
    return d


def _dedupe(items):
    out, seen = [], set()
    for it in items:
        k = it["path"].lower()
        if k not in seen:
            seen.add(k); out.append(it)
    return out


def from_aos(store, aos, label):
    items = []
    for ao in aos:
        for p, via, bone in _refs(store, ao):
            items.append(_describe(store, p, via, bone))
    items = _dedupe(items)
    return {"label": label, "items": items} if items else None


def _ivi_rows(store):
    if not _ivi_by_ao:
        t = table(store, "itemvisualidentity")
        for i in range(len(t)):
            for col in ("AOFile", "AOFile2"):
                a = t.get(i, col)
                if a:
                    _ivi_by_ao.setdefault(a.lower(), []).append(i)
        _ivi_by_ao["__t"] = t
    return _ivi_by_ao


_bt = {}


def _base_ivi(store, item_id):
    """BaseItemTypes.ItemVisualIdentity row of an item (by metadata id)."""
    if (item_id or "").startswith("unique:"):
        from . import uniqmap
        u = uniqmap.unique_items(store).get(item_id[7:])
        return u["ivi"] if u else None
    if not _bt:
        t = table(store, "baseitemtypes")
        for i in range(len(t)):
            k = t.get(i, "Id")
            if k:
                _bt[k.lower()] = t.get(i, "ItemVisualIdentity")
    return _bt.get((item_id or "").lower())


def item_effects(store, item_id, ao, chosen_ao, attachment_aos):
    """Effects of one equipped item. `ao` is the item's drop .ao, `chosen_ao` the equipped variant."""
    groups = []
    g = from_aos(store, [x for x in dict.fromkeys([chosen_ao, ao] + list(attachment_aos or [])) if x], "Файлы предмета (.ao)")
    if g:
        groups.append(g)
    t = table(store, "itemvisualidentity"); i = _base_ivi(store, item_id)
    packs = []
    if i is not None and i < len(t):
        for col in ("EPKFile",):
            epk = t.get(i, col)
            if epk and _exists(store, _norm(epk)):
                packs.append(_describe(store, _norm(epk), "ItemVisualIdentity " + str(t.get(i, "Id"))))
        for col in ("AOFile", "AOFile2"):
            a_ = t.get(i, col)
            if a_ and a_.lower().endswith(".ao") and _exists(store, a_):
                g2 = from_aos(store, [a_], "")
                if g2:
                    packs += g2["items"]
    packs = _dedupe(packs)
    if packs:
        groups.append({"label": "Эффект предмета (ItemVisualIdentity)", "items": packs})
    return groups


def monster_effects(store, mrow, ao_chain, skills_art):
    """Effects of one monster: .ao chain, conditional/sink effects of the variety row, and the art of its skills."""
    groups = []
    g = from_aos(store, ao_chain, "Файлы монстра (.ao)")
    if g:
        groups.append(g)
    extra = []
    for key in ("SinkEffect", "SinkAnimation_AOFile"):
        v = mrow.get(key)
        if v and _exists(store, _norm(v)):
            extra.append(_describe(store, _norm(v), key))
    ce = mrow.get("MonsterConditionalEffectPack")
    if ce is not None:
        try:
            t = table(store, "monsterconditionaleffectpacks"); r = t.row(ce)
            for k, v in r.items():
                for x in (v if isinstance(v, list) else [v]):
                    if isinstance(x, str) and re.search(r"\.(epk|pet|ao|trl)$", x, re.I) and _exists(store, _norm(x)):
                        extra.append(_describe(store, _norm(x), "MonsterConditionalEffectPack " + str(r.get("Id") or "")))
        except Exception:
            pass
    extra = _dedupe(extra)
    if extra:
        groups.append({"label": "Условные эффекты монстра", "items": extra})
    for label, items in skills_art:
        its = []
        for it in items:
            for f in it.get("files", []):
                p = _norm(f)
                if _exists(store, p) and p.rsplit(".", 1)[-1].lower() in _KINDS:
                    its.append(_describe(store, p, it.get("kind")))
        its = _dedupe(its)
        if its:
            groups.append({"label": "Умение: " + label, "items": its})
    return groups
