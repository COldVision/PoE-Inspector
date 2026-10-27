"""Passive skill tree for the planner page: nodes with positions from the game's passiveskillgraph.psg + names / stat texts of the passives."""
import json, os
from . import psg, mods, sections
from .datrows import table, ROOT

CLASSES = [6, 1, 2, 7, 8, 9, 10, 11]   # Characters rows of the current classes: Warrior, Witch, Ranger, Sorceress, Huntress, Mercenary, Monk, Druid
_mem = {}


ATLAS_NAMES = {"Generic": "Общее", "Ritual": "Ритуал", "Breach": "Разлом", "Delirium": "Делириум", "Abyss": "Бездна", "Incursion": "Вторжение", "Expedition": "Экспедиция"}


def _art(store, p):
    """Table art path ('Art/2DArt/UIImages/...') -> existing dds path in the bundles, or ''."""
    if not p:
        return ""
    q = p.lower()
    if q.endswith(".dds"):
        q = q[:-4]
    pre = q.split("/", 4)
    cands = [q, "art/textures/interface/2d/" + q[4:]]
    if "/ingame/" in cands[1]:
        a, b = cands[1].rsplit("/ingame/", 1)
        cands += [a + "/ingame/4k/" + b, a + "/ingame/" + b]
    for c in cands:
        if store.find(c + ".dds"):
            return c + ".dds"
    return ""


def _layout_ascendancies(nodes, centres, asc):
    """Place the ascendancy islands like the Path of Building tree: every island is shifted as a whole (nodes and group centres)
    onto the ring around the passive tree; the round art of each one gets its centre and size from the same table."""
    lay = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "asc_layout.json"), encoding="utf-8"))["asc"]
    by = {a["i"]: a for a in asc}
    done = set()
    for n in nodes:
        a = by.get(n["a"])
        if not a or a["en"] not in lay:
            continue
        dx, dy = lay[a["en"]]["d"]
        n["x"] = round(n["x"] + dx, 1); n["y"] = round(n["y"] + dy, 1)
        if n["g"] not in done and n["g"] in centres:
            done.add(n["g"]); cx, cy = centres[n["g"]]; centres[n["g"]] = (round(cx + dx, 1), round(cy + dy, 1))
    for a in asc:
        if a["en"] in lay:
            a["bg"] = lay[a["en"]]["bg"]; a["bgs"] = lay[a["en"]]["size"]
    # Abyssal Lich replaces the Lich island: same place, same art centre
    lich = next((a for a in asc if a["en"] == "Lich"), None)
    for a in asc:
        if a["en"] == "Abyssal Lich" and lich and "bg" in lich:
            a["bg"] = lich["bg"]; a["bgs"] = lich["bgs"]


def _outer_ring(nodes, centres, active, radius=19800, half=2100):
    """Ascendancies that are in the game files but have no art / name yet: keep their islands, place them on a second ring
    outside the ring of the finished ones, in the order of their original angle around the tree."""
    import math
    box = {}
    for n in nodes:
        if n["a"] >= 0 and n["a"] not in active:
            b = box.setdefault(n["a"], [1e9, 1e9, -1e9, -1e9])
            b[0] = min(b[0], n["x"]); b[1] = min(b[1], n["y"]); b[2] = max(b[2], n["x"]); b[3] = max(b[3], n["y"])
    if not box:
        return
    cen = {a: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for a, b in box.items()}
    ids = sorted(cen, key=lambda a: math.atan2(cen[a][1], cen[a][0]))
    gap = 2 * math.asin(min(1, half / radius))                 # smallest angle between two neighbours
    ang = [math.atan2(cen[a][1], cen[a][0]) for a in ids]
    orig = list(ang)
    for i in range(1, len(ang)):            # forward sweep: every island at least `gap` after the previous one
        ang[i] = max(ang[i], ang[i - 1] + gap)
    mean = sum(a - o for a, o in zip(ang, orig)) / len(ang)
    ang = [a - mean for a in ang]            # keep the group around where it was
    if len(ang) > 1 and ang[0] + 2 * math.pi - ang[-1] < gap:   # wrapped round the circle: spread evenly
        ang = [orig[0] + k * 2 * math.pi / len(ang) for k in range(len(ang))]
    shift = {a: (round(radius * math.cos(t) - cen[a][0], 1), round(radius * math.sin(t) - cen[a][1], 1)) for a, t in zip(ids, ang)}
    done = set()
    for n in nodes:
        if n["a"] in shift:
            dx, dy = shift[n["a"]]
            n["x"] = round(n["x"] + dx, 1); n["y"] = round(n["y"] + dy, 1)
            if n["g"] not in done and n["g"] in centres:
                done.add(n["g"]); cx, cy = centres[n["g"]]; centres[n["g"]] = (round(cx + dx, 1), round(cy + dy, 1))


def build(store, kind="passives"):
    atlas = kind == "atlas"
    cache = os.path.join(ROOT, "cache", "tree_atlas_v7.json" if atlas else "tree_v7.json")
    if os.path.exists(cache):
        return json.load(open(cache, encoding="utf-8"))
    g = psg.parse(store.read("metadata/atlasskillgraphs/atlasskillgraph.psg" if atlas else "metadata/passiveskillgraph.psg"))
    en, ru = table(store, "passiveskills"), table(store, "passiveskills", "russian")
    asc_t, asc_ru = table(store, "ascendancy"), table(store, "ascendancy", "russian")
    ch, chr_ = table(store, "characters"), table(store, "characters", "russian")
    st = table(store, "stats"); csd = mods._csd(store)
    by = {en.get(i, "PassiveSkillGraphId"): i for i in range(len(en))}
    mg, mart = table(store, "passiveskillmasterygroups"), table(store, "passiveskilltreemasteryart")
    fx, fxi = [], {}   # glow images behind the mastery nodes (shared list, nodes carry an index)
    ids = sorted(g["nodes"]); idx = {n: k for k, n in enumerate(ids)}
    nodes = []
    for n in ids:
        i = by.get(n); nd = g["nodes"][n]
        if i is None:
            nodes.append({"x": nd["x"], "y": nd["y"], "g": nd["g"], "o": nd["orbit"], "k": "s", "n": "", "t": [], "a": -1}); continue
        r = en.row(i)
        sids, lo = [], {}
        for m, sref in enumerate([x for x in (r.get("Stats") or []) if x is not None], 1):
            sid = st.get(sref, "Id"); sids.append(sid); lo[sid] = r.get(f"Stat{m}Value") or 0
        kind = "k" if r["IsKeystone"] else "n" if r["IsNotable"] else "j" if r["IsJewelSocket"] else "s"
        if r.get("IsAscendancyStartingNode"):
            kind = "r"
        a = r["Ascendancy"] if r["Ascendancy"] is not None else -1
        name = (ru.get(i, "Name") or "").strip() or r.get("Name") or ""
        nodes.append({"x": nd["x"], "y": nd["y"], "g": nd["g"], "o": nd["orbit"], "k": kind, "n": name, "e": r.get("Name") or "", "t": mods._render(csd, sids, lo, lo, "Russian") or mods._render(csd, sids, lo, lo, "en"),
                      "ic": r.get("Icon_DDSFile") or "", "a": a, "fl": (sections._clean(ru.get(i, "FlavourText") or r.get("FlavourText") or "")) if kind == "k" else "",
                      "rm": [sections._clean(x) for x in (r.get("ReminderStrings") or []) if x], "at": bool(r.get("IsAttribute")),
                      "te": mods._render(csd, sids, lo, lo, "en") or [], "fle": (sections._clean(r.get("FlavourText") or "")) if kind == "k" else ""})
        if r.get("IsJustIcon") and r.get("MasteryGroup") is not None:
            ai = mg.get(r["MasteryGroup"], "Art")
            path = _art(store, mart.get(ai, "ActiveEffectImage")) if ai is not None and ai < len(mart) else ""
            if path:
                if path not in fxi:
                    fxi[path] = len(fx); fx.append(path)
                nodes[-1]["ma"] = fxi[path]
    edges = [[idx[a], idx[b]] for a, b in g["edges"] if a in idx and b in idx]
    if atlas:
        classes, asc = [], []
        for n in g["roots"]:
            i = by.get(n)
            key = (en.get(i, "Id") or "").replace("Atlas", "").replace("Start", "").strip("_") if i is not None else ""
            classes.append({"i": n, "ru": ATLAS_NAMES.get(key, key or "Старт"), "en": key, "root": idx.get(n)})
    else:
        roots = {}
        for n in g["roots"]:
            i = by.get(n)
            for c in (en.get(i, "Characters") or []) if i is not None else []:
                if c in CLASSES:
                    roots[c] = idx[n]
        classes = [{"i": c, "ru": chr_.get(c, "Name") or ch.get(c, "Name"), "en": ch.get(c, "Name"), "root": roots.get(c),
                    "img": _art(store, "Art/2DArt/BaseClassIllustrations/%sBaseIllustration" % ch.get(c, "Name"))} for c in CLASSES]
        asc = []
        for j in range(len(asc_t)):
            nm = asc_t.get(j, "Name") or ""
            c = asc_t.get(j, "Character")
            if nm and not nm.startswith("[DNT") and not asc_t.get(j, "Disabled") and c in CLASSES:
                asc.append({"i": j, "ru": asc_ru.get(j, "Name") or nm, "en": nm, "class": c, "img": _art(store, asc_t.get(j, "PassiveTreeImage"))})
    # the start node of each ascendancy (its "…Start" passive carries the ascendancy index)
    starts = {}
    for k, nd in enumerate(nodes):
        if nd["k"] == "r" and nd["a"] >= 0:
            starts.setdefault(nd["a"], k)
    groups = {}
    for n in ids:
        nd = g["nodes"][n]; groups.setdefault(nd["g"], None)
    if not atlas:
        active = {a["i"] for a in asc}
        _layout_ascendancies(nodes, g["centres"], asc)
        _outer_ring(nodes, g["centres"], active)
    uiart = table(store, "passiveskilltreeuiart")
    ua = 4 if atlas else 0
    gbart = [_art(store, uiart.get(ua, k)) for k in ("GroupBackgroundSmall", "GroupBackgroundMedium", "GroupBackgroundLarge")]
    # psg group "background" class: 4 small, 2 medium, 3 large; the extent is the farthest orbit used by the group
    far = {}
    for n in ids:
        nd = g["nodes"][n]
        far[nd["g"]] = max(far.get(nd["g"], 0), psg.ORBIT_RADIUS[nd["orbit"]] if nd["orbit"] < len(psg.ORBIT_RADIUS) else 0)
    ascg = {nodes[idx[n]]["g"] for n in ids if nodes[idx[n]]["a"] >= 0}
    gb = [] if not atlas else [[g["centres"][gi][0], g["centres"][gi][1], {4: 0, 2: 1, 3: 2}.get(b, 0), far.get(gi, 0)] for gi, b in g["backs"].items() if gi in g["centres"] and gi in far and gi not in ascg]
    out = {"gb": gb, "gbart": gbart, "gbhalf": not atlas, "fx": fx, "nodes": nodes, "edges": edges, "classes": classes, "asc": asc, "starts": starts, "orbit_r": psg.ORBIT_RADIUS, "orbit_n": g["orbits"]}
    out["centres"] = {str(k): list(v) for k, v in g["centres"].items()}
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def tree(store, kind="passives"):
    if kind not in _mem:
        _mem[kind] = build(store, kind)
    return _mem[kind]
