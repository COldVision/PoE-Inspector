"""Home page backend: game folder check, version snapshots and "what is new" diff between two versions of the game client."""
import glob, json, os, re, time

from .paths import DATA as ROOT
SNAPS = os.path.join(ROOT, "cache", "snapshots")
CATS = [("skills", "Умения и камни"), ("items", "Предметы"), ("uniques", "Уникальные"), ("monsters", "Монстры"), ("mods", "Свойства"),
        ("models", "Модели"), ("tables", "Таблицы"), ("sounds", "Звуки")]
_cur = {}


def steam_build(game):
    """Steam buildid / last update time of the install that owns this folder (appmanifest next to the 'common' folder)."""
    try:
        apps = os.path.dirname(os.path.dirname(os.path.abspath(game)))
        name = os.path.basename(os.path.abspath(game)).lower()
        for f in glob.glob(os.path.join(apps, "appmanifest_*.acf")):
            t = open(f, encoding="utf-8", errors="replace").read()
            d = dict(re.findall(r'"(\w+)"\s+"([^"]*)"', t))
            if d.get("installdir", "").lower() == name:
                return {"buildid": d.get("buildid", ""), "updated": int(d.get("LastUpdated", 0) or 0)}
    except OSError:
        pass
    return {"buildid": "", "updated": 0}


def check_dir(path):
    path = (path or "").strip().strip('"')
    idx = os.path.join(path, "Bundles2", "_.index.bin")
    ok = bool(path) and os.path.isfile(idx)
    r = {"path": path, "ok": ok}
    if ok:
        r.update(steam_build(path)); r["index_mtime"] = int(os.path.getmtime(idx)); r["index_size"] = os.path.getsize(idx)
    return r


def collect(store):
    """Current content of the database as {category: {key: display name}}."""
    from . import gems, mods
    c = store.db.execute
    out = {
        "skills": {g["k"]: g.get("ru") or g["name"] for g in gems.search(store, "", "")},
        "items": {i: n or i for i, n in c("select id,name from items")},
        "uniques": {n: b or "" for n, b in c("select name,base from uniques")},
        "monsters": {i: n or i for i, n in c("select id,name from monsters")},
        "mods": {m["id"]: (m.get("text") or [m.get("name")])[0] or m["id"] for m in mods.search(store, "", "", "", "", 100000, 0)["rows"]},
        "models": {p: "" for (p,) in c("select path from files where ext in ('smd','fmt')")},
        "tables": {p.rsplit("/", 1)[-1][:-8]: "" for (p,) in c("select path from files where ext='datc64' and path like 'data/balance/%' and path not like 'data/balance/%/%'")},
        "sounds": {p: "" for (p,) in c("select path from files where ext='ogg'")},
    }
    return out


def current(store):
    """collect() cached per database file (it is rebuilt only when poe2.db changes)."""
    m = os.path.getmtime(store._path)
    if _cur.get("m") != m:
        _cur.clear(); _cur.update(m=m, data=collect(store))
    return _cur["data"]


def snapshots():
    out = []
    for f in sorted(glob.glob(os.path.join(SNAPS, "*.json")), reverse=True):
        try:
            h = json.load(open(f, encoding="utf-8"))["meta"]; h["id"] = os.path.basename(f)[:-5]; out.append(h)
        except (OSError, ValueError, KeyError):
            pass
    return out


def make_snapshot(store, label=""):
    os.makedirs(SNAPS, exist_ok=True)
    sb = steam_build(store.game); ts = int(time.time())
    meta = {"time": ts, "buildid": sb["buildid"], "label": label, "counts": {}}
    data = current(store)
    meta["counts"] = {k: len(v) for k, v in data.items()}
    sid = time.strftime("%Y%m%d_%H%M%S", time.localtime(ts)) + (f"_{sb['buildid']}" if sb["buildid"] else "")
    json.dump({"meta": meta, "data": data}, open(os.path.join(SNAPS, sid + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    meta["id"] = sid
    return meta


def status(store):
    g = store.game
    sn = snapshots()
    if not sn:   # first run: the current database becomes the baseline
        sn = [make_snapshot(store, "первая версия")]
    return {"game": g, "exists": os.path.isdir(g), **steam_build(g), "db_time": int(os.path.getmtime(store._path)),
            "cats": CATS, "counts": {k: len(v) for k, v in current(store).items()}, "snapshots": sn}


def diff(store, base, limit=200):
    """What is in the database now but not in snapshot `base` (and what disappeared)."""
    p = os.path.join(SNAPS, os.path.basename(base) + ".json")
    if not os.path.isfile(p):
        return None
    old = json.load(open(p, encoding="utf-8"))["data"]; cur = current(store); res = {}
    for k, _n in CATS:
        o, n = old.get(k, {}), cur.get(k, {})
        add = [(x, n[x]) for x in n if x not in o]; rem = [(x, o[x]) for x in o if x not in n]
        rows = [{"key": x, "name": v} for x, v in sorted(add, key=lambda t: t[0])[:limit]]
        _enrich(store, k, rows)
        res[k] = {"added": len(add), "removed": len(rem), "rows": rows}
    return res


def _enrich(store, cat, rows):
    """Preview-card fields for the new entries: icon, subtitle, short text, and where a click should go (`tab` + search text `q`)."""
    if not rows:
        return
    c = store.db.execute
    keys = [r["key"] for r in rows]
    if cat == "skills":
        from . import gems
        g = {x["k"]: x for x in gems.search(store, "", "")}
        kinds = {"active": "умение", "spirit": "Spirit", "meta": "мета", "support": "поддержка", "lineage": "династическая", "other": "прочее", "item": "умение предмета"}
        for r in rows:
            x = g.get(r["key"])
            if x:
                r.update(tab="skills", q=x.get("ru") or x["name"], icon=x.get("icon"), sub=kinds.get(x["kind"], x["kind"]) + (f" · ур. {x['minlvl']}" if x.get("minlvl") else ""),
                         text=(x.get("tip") or "")[:260], tags=x.get("tags_ru") or x.get("tags") or [], tags_en=x.get("tags") or [], en=x["name"])
    elif cat in ("items", "monsters"):
        for i in range(0, len(keys), 500):
            part = keys[i:i + 500]; ph = ",".join("?" * len(part))
            cols = "id,name,icon,class,model" if cat == "items" else "id,name,model"
            by = {row[0]: row for row in c(f"select {cols} from {cat} where id in ({ph})", part)}
            for r in rows:
                row = by.get(r["key"])
                if row:
                    r.update(tab=cat, q=row[1] or row[0], sub=(row[3] if cat == "items" else "монстр") or "", model=row[-1] or "", id=row[0])
                    if cat == "items":
                        r["icon"] = row[2]
    elif cat == "uniques":
        for r in rows:
            row = c("select name,base,slot,league,icon,model from uniques where name=?", (r["key"],)).fetchone()
            if row:
                r.update(name=row[0], tab="items", q=row[0], unique=1, sub=" · ".join(x for x in (row[1], row[2], row[3]) if x), icon=row[4], model=row[5] or "")
    elif cat == "mods":
        for r in rows:
            r.update(tab="mods", q=r["name"] or r["key"], sub=r["key"])
    elif cat == "models":
        for r in rows:
            r.update(tab="models", q=r["key"].rsplit("/", 1)[-1], sub=r["key"], model=r["key"])
    elif cat == "sounds":
        for r in rows:
            r.update(tab="files", q=r["key"].rsplit("/", 1)[-1], sub=r["key"])
    elif cat == "tables":
        for r in rows:
            r.update(tab="tables", q=r["key"], sub="data/balance")
