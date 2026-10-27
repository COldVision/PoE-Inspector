"""Unique items: names/art from the game's own tables, mods/base stats from the local Path of Building PoE2 data."""
import glob, json, os, re
from .dat import Dat
from . import tables, catalog

POB = os.path.join(os.environ.get("APPDATA", ""), "Path of Building Community (PoE2)", "Data")


def parse_bases(pob=POB):
    bases = {}
    for f in glob.glob(os.path.join(pob, "Bases", "*.lua")):
        src = open(f, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'itemBases\["([^"]+)"\]\s*=\s*\{(.*?)\n\}', src, re.S):
            body = m.group(2)
            b = {}
            for key in ("armour", "weapon", "req"):
                mm = re.search(key + r"\s*=\s*\{([^}]*)\}", body)
                if mm:
                    b[key] = {k: float(v) if "." in v else int(v) for k, v in re.findall(r"(\w+)\s*=\s*(-?[\d.]+)", mm.group(1))}
            for key in ("type", "subType", "implicit"):
                mm = re.search(key + r'\s*=\s*"([^"]*)"', body)
                if mm:
                    b[key] = mm.group(1)
            bases[m.group(1)] = b
    return bases


def parse_flavour(pob=POB):
    fp = os.path.join(pob, "FlavourText.lua")
    if not os.path.exists(fp):
        return {}
    src = open(fp, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r'\["name"\]\s*=\s*"((?:[^"\\]|\\.)*)",(.*?)\n\t\},', src, re.S):
        lines = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(2).split('["text"]')[-1])
        out[m.group(1).lower()] = " ".join(l.replace('\\"', '"') for l in lines)
    return out


def parse_uniques(pob=POB):
    items = []
    for f in sorted(glob.glob(os.path.join(pob, "Uniques", "*.lua"))):
        src = open(f, encoding="utf-8", errors="replace").read()
        slot = os.path.splitext(os.path.basename(f))[0]
        for m in re.finditer(r"\[\[\n?(.*?)\]\]", src, re.S):
            lines = [l.rstrip() for l in m.group(1).split("\n") if l.strip()]
            if len(lines) < 2:
                continue
            it = {"name": lines[0], "base": lines[1], "slot": slot, "variants": [], "league": None, "level": None,
                  "implicits": [], "mods": []}
            rest = lines[2:]
            n_impl = 0
            mods = []
            for l in rest:
                if l.startswith("Variant:"):
                    it["variants"].append(l[8:].strip())
                elif l.startswith("League:"):
                    it["league"] = l[7:].strip()
                elif l.startswith("Requires Level"):
                    it["level"] = int(re.sub(r"\D", "", l) or 0)
                elif l.startswith("Implicits:"):
                    n_impl = int(re.sub(r"\D", "", l) or 0)
                elif re.match(r"(Sockets|Limited to|Has \d+ Sockets|Source|Selected Variant|Talisman Tier|Radius|Upgrade):", l) or l.startswith("Has ") and "Socket" in l:
                    pass
                else:
                    mods.append(l)
            sel = max(len(it["variants"]), 1)
            out = []
            for l in mods:
                vm = re.match(r"\{variant:([\d,]+)\}", l)
                if vm and str(sel) not in vm.group(1).split(","):
                    continue
                l = re.sub(r"\{[^}]*\}", "", l).strip()
                if l:
                    out.append(l)
            # variant filtering may drop implicit lines; implicit count only trusted without variants
            it["implicits"], it["mods"] = out[:n_impl], out[n_impl:]
            items.append(it)
    return items


def parse_generated(pob=POB):
    """Uniques that Path of Building builds with Lua code (Special/Generated.lua): only their fixed lines can be read without
    running Lua - name, base, source/league, and the mod lines written as plain strings. Variable mods are not included."""
    out = {}
    fp = os.path.join(pob, "Uniques", "Special", "Generated.lua")
    if not os.path.exists(fp):
        return out
    src = open(fp, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'local (\w+) = \{\s*\n((?:\s*"[^\n]*",?\s*\n)+)\s*\}', src):
        var, head = m.group(1), re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(2))
        if len(head) < 2 or var in ("excludedItemKeystones", "excludedGems"):
            continue
        it = {"name": head[0], "base": head[1], "slot": "", "variants": [], "league": None, "level": None, "implicits": [], "mods": [], "source": None, "generated": True}
        for l in head[2:]:
            if l.startswith("League:"):
                it["league"] = l[7:].strip()
            elif l.startswith("Source:"):
                it["source"] = re.sub(r"\w+\{([^}]*)\}", r"\1", l[7:]).strip()
        for l in re.findall(r'table\.insert\(' + var + r', "((?:[^"\\]|\\.)*)"\)', src):
            if not re.match(r"(Variant|Selected|Implicits|Has Alt)", l) and not l.startswith("{variant"):
                it["mods"].append(l)
        out[it["name"].lower()] = it
    return out


def build(store, log=print, pob=POB):
    sch = tables.load_schema(__import__("poe_inspector.paths", fromlist=["SCHEMA"]).SCHEMA)
    def load(name):
        d = Dat(store.read(f"data/balance/{name}.datc64"))
        return d, tables.cols_from_schema(sch[name], d.width)
    w, wc = load("words")
    wtext = {i: w.str(i, 4) for i in range(w.rows)}
    iv, _ = load("itemvisualidentity")
    usl, uc = load("uniquestashlayout")
    st, _ = load("uniquestashtypes")
    stash = {i: st.str(i, st_off) for i in range(st.rows)} if (st_off := next((c[3] for c in tables.cols_from_schema(sch["uniquestashtypes"], st.width) if c[0] == "Id"), None)) is not None else {}
    stash_name = {i: st.str(i, next(c[3] for c in tables.cols_from_schema(sch["uniquestashtypes"], st.width) if c[0] == "Name")) for i in range(st.rows)}
    alt_off = next(c[3] for c in uc if c[0] == "IsAlternateArt")
    game = {}   # every unique the game's stash knows: name -> (icon, ao, stash type)
    for i in range(usl.rows):
        name = wtext.get(usl.fk(i, 0))
        ivk = usl.fk(i, 16)
        if not name:
            continue
        icon, ao = (iv.str(ivk, 8), iv.str(ivk, 16)) if ivk is not None and ivk < iv.rows else (None, None)
        sk = usl.fk(i, 32); typ = stash_name.get(sk) if sk is not None else None
        alt = bool(usl.u8(i, alt_off))
        if name.lower() not in game or (game[name.lower()][3] and not alt):
            game[name.lower()] = (icon, ao, typ, alt, name)
    bases, flavour, items = parse_bases(pob), parse_flavour(pob), parse_uniques(pob)
    pobmap = {}
    for it in items:
        pobmap.setdefault(it["name"].lower(), it)
    genmap = parse_generated(pob)
    cache = {}
    db = store.db
    db.executescript("DROP TABLE IF EXISTS uniques; CREATE TABLE uniques(name TEXT, base TEXT, slot TEXT, league TEXT, icon TEXT, model TEXT, data TEXT);")
    rows = []
    for key in sorted(set(game) | set(pobmap)):
        g = game.get(key); it = pobmap.get(key)
        icon, ao, typ, _alt, gname = g if g else (None, None, None, False, None)
        if it is None and key in genmap:   # built by Lua code in PoB: fixed lines only
            it = dict(genmap[key]); it["pob"] = "partial"; it["slot"] = (typ or "").lower()
        elif it is None:   # in the game but not in Path of Building: name, art and model only
            it = {"name": gname, "base": "", "slot": (typ or "").lower(), "variants": [], "league": None, "level": None, "implicits": [], "mods": [], "pob": False}
        elif it is not None and "pob" not in it:
            it["pob"] = True
        it["inGame"] = bool(g)
        model = catalog.ao_model(store, ao, cache) if ao else None
        b = bases.get(it["base"], {})
        it.update({"flavour": flavour.get(key), "baseInfo": b, "stashType": typ})
        if it["level"] is None and b.get("req"):
            it["level"] = b["req"].get("level")
        rows.append((it["name"], it["base"], it["slot"], it["league"], icon, model, json.dumps(it, ensure_ascii=False)))
    db.executemany("INSERT INTO uniques VALUES(?,?,?,?,?,?,?)", rows)
    db.execute("CREATE INDEX uniques_name ON uniques(name)")
    db.commit()
    log(f"uniques={len(rows)} with PoB mods={sum(1 for r in rows if json.loads(r[6]).get('pob'))} icon={sum(1 for r in rows if r[4])} model={sum(1 for r in rows if r[5])} flavour={sum(1 for r in rows if json.loads(r[6])['flavour'])}")
