"""Build items / monsters / models catalog tables from data/balance tables and .ao/.sm files."""
import re
from .dat import Dat, NULL

AO_SKIN = re.compile(r'skin\s*=\s*"([^"]+)"', re.I)
AO_FMT = re.compile(r'fixed_mesh\s*=\s*"([^"]+)"', re.I)
SM_SMD = re.compile(r'SkinnedMeshData\s+"([^"]+)"', re.I)
SKIP_MON = ("daemon", "invisible", "clone", "[any monster]")

def text(store, path):
    b = store.read(path)
    if not b: return ""
    return b.decode("utf-16-le" if b[:2] != b"\xff\xfe" else "utf-16", "replace").lstrip("﻿")

def ao_model(store, ao, cache):
    key = ao.lower()
    if key in cache: return cache[key]
    res = None
    try:
        t = text(store, key)
        m = AO_FMT.search(t)
        if m: res = m.group(1).lower()
        else:
            m = AO_SKIN.search(t)
            if m:
                sm = text(store, m.group(1).lower())
                m2 = SM_SMD.search(sm)
                res = m2.group(1).lower() if m2 else None
    except Exception:
        pass
    cache[key] = res
    return res

def build(store, log=print):
    db = store.db
    db.executescript("""
      DROP TABLE IF EXISTS items; DROP TABLE IF EXISTS monsters;
      CREATE TABLE items(id TEXT, name TEXT, icon TEXT, ao TEXT, model TEXT, row INTEGER, class TEXT, ao2 TEXT);
      CREATE TABLE monsters(id TEXT, name TEXT, ao TEXT, model TEXT, row INTEGER);
      CREATE INDEX items_name ON items(name); CREATE INDEX monsters_name ON monsters(name);
    """)
    cache = {}
    bi = Dat(store.read("data/balance/baseitemtypes.datc64"))
    iv = Dat(store.read("data/balance/itemvisualidentity.datc64"))
    ic = Dat(store.read("data/balance/itemclasses.datc64"))
    classes = {i: ic.str(i, 8) or ic.str(i, 0) for i in range(ic.rows)}
    rows = []
    for i in range(bi.rows):
        name = bi.str(i, 32)
        if not name: continue
        fk = bi.fk(i, 124)
        icon = ao = model = ao2 = None
        if fk is not None and fk < iv.rows:
            icon, ao, ao2 = iv.str(fk, 8), iv.str(fk, 16), iv.str(fk, 42)
            if ao: model = ao_model(store, ao, cache)
        rows.append((bi.str(i, 0), name, icon, ao, model, i, classes.get(bi.fk(i, 8)), ao2))
    db.executemany("INSERT INTO items VALUES(?,?,?,?,?,?,?,?)", rows)
    log(f"items={len(rows)} with model={sum(1 for r in rows if r[4])}")
    mv = Dat(store.read("data/balance/monstervarieties.datc64"))
    rows = []
    for i in range(mv.rows):
        name = mv.str(i, 272)
        if not name or name.lower().startswith(SKIP_MON): continue
        name = re.sub(r"^(\[DNT[^\]]*\]|\(DNT[^)]*\))\s*", "", name)
        aos = mv.array(i, 56)
        ao = mv.string_at(aos[0]) if aos else None
        model = ao_model(store, ao, cache) if ao else None
        rows.append((mv.str(i, 0), name, ao, model, i))
    db.executemany("INSERT INTO monsters VALUES(?,?,?,?,?)", rows)
    log(f"monsters={len(rows)} with model={sum(1 for r in rows if r[3])}")
    db.commit()
