import json, os, re, time, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from .store import Store
from .dat import Dat
from . import mesh, glb, tables, textures, scene, pet, actor, uniqmap, npcitems, ast as astmod

from .paths import APP as ROOT, DATA, SCHEMA, DB   # ROOT = app files (web, schema); DATA = database and caches
store = None
_dat_cache = {}


def get_dat(name):
    if name not in _dat_cache:
        b = store.read(f"data/balance/{name}.datc64")
        if b is None:
            return None
        _dat_cache[name] = Dat(b)
        if len(_dat_cache) > 12:
            _dat_cache.pop(next(iter(_dat_cache)))
    return _dat_cache[name]


def rows_to_dicts(cur, keys):
    return [dict(zip(keys, r)) for r in cur]


def decode_text(data):
    if data[:2] == b"\xff\xfe" or (len(data) > 1 and data[1] == 0):
        return data.decode("utf-16", "replace").lstrip("﻿")
    return data.decode("utf-8", "replace")


_BOSS = {}


def boss_rows(store):
    """MonsterVarieties rows that show a boss health bar."""
    if "s" not in _BOSS:
        from .datrows import table
        mv = table(store, "monstervarieties")
        _BOSS["s"] = {r for (r,) in store.db.execute("select row from monsters") if mv.row(r).get("BossHealthBar")}
    return _BOSS["s"]


def monmod_order(x):
    from .monster import TAG_ORDER
    return TAG_ORDER.index(x) if x in TAG_ORDER else 99


def dedupe_monsters(store, rows):
    """Collapse varieties with the same name, model and granted skills; the first (shortest id) stays, with a count of the hidden ones."""
    from .datrows import table
    mv = table(store, "monstervarieties")
    groups = {}
    for r in sorted(rows, key=lambda r: (len(r["id"] or ""), r["id"] or "")):
        key = (r["name"], r["model"], tuple(mv.row(r["row"]).get("GrantedEffects") or []))
        g = groups.setdefault(key, [])
        g.append(r)
    keep = {id(g[0]): len(g) - 1 for g in groups.values()}
    for g in groups.values():
        if len(g) > 1 and "tags" in g[0]:
            g[0]["tags"] = sorted({x for r in g for x in r["tags"]}, key=lambda x: monmod_order(x))
    out = []
    for r in rows:
        if id(r) in keep:
            r["dups"] = keep[id(r)]
            out.append(r)
    return out


store = None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            from . import recsrv
            n = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(n) if n else b""
            if u.path == "/api/rec/start":
                return self.send(200, {"id": recsrv.start(int(q.get("fps", 30)), q.get("alpha") == "1", q.get("name", ""), int(q.get("crf", 20)))})
            if u.path == "/api/rec/frame":
                recsrv.frame(q["id"], body)
                return self.send(200, {"ok": True})
            if u.path == "/api/rec/finish":
                return self.send(200, recsrv.finish(q["id"]))
            if u.path == "/api/rec/cancel":
                recsrv.cancel(q["id"])
                return self.send(200, {"ok": True})
            return self.send(404, {"error": "not found"})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            try:
                self.send(500, {"error": f"{type(e).__name__}: {e}"})
            except OSError:
                pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        p = u.path
        try:
            if p.startswith("/api/setup/") or store is None:   # no database yet (first run): only the setup page and its API work
                from . import setup, home
                if p == "/api/setup/status":
                    return self.send(200, dict(setup.state, games=setup.find_games() if setup.state["phase"] == "idle" else [], ready=store is not None))
                if p == "/api/setup/checkdir":
                    return self.send(200, home.check_dir(q.get("path", "")))
                if p == "/api/setup/start":
                    try:
                        return self.send(200, setup.start(q.get("game", "")))
                    except ValueError as e:
                        return self.send(400, {"error": str(e)})
                if store is None:
                    if p == "/":
                        return self.send(200, open(os.path.join(ROOT, "web", "setup.html"), "rb").read(), "text/html; charset=utf-8", {"Cache-Control": "no-store"})
                    if not p.startswith("/static/") and not p.startswith("/fonts/"):
                        return self.send(503, {"error": "database not built yet"})
            if p.startswith("/api/update/"):
                from . import updater
                a = p[12:]
                if a == "check":
                    return self.send(200, updater.check())
                if a == "status":
                    return self.send(200, updater.status())
                if a == "download":
                    return self.send(200, updater.download())
                if a == "restart":
                    import subprocess, sys, threading
                    if updater.state["phase"] != "ready":
                        return self.send(409, {"error": "no downloaded update"})
                    self.send(200, {"ok": True})
                    def _re():
                        time.sleep(.4)
                        main = os.path.join(ROOT, "app_main.pyw")
                        exe = sys.executable.replace("python.exe", "pythonw.exe")
                        subprocess.Popen([exe, main], cwd=ROOT, env=dict(os.environ, POE2_RESTART="1"), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                        os._exit(0)
                    threading.Thread(target=_re, daemon=True).start()
                    return
            if p == "/":
                return self.send(200, open(os.path.join(ROOT, "web", "index.html"), "rb").read(), "text/html; charset=utf-8", {"Cache-Control": "no-store"})
            if p.startswith("/api/home/"):
                from . import home
                a = p[10:]
                if a == "status":
                    return self.send(200, home.status(store))
                if a == "news":
                    from . import news
                    return self.send(200, news.get(q.get("force") == "1"))
                if a == "checkdir":
                    return self.send(200, home.check_dir(q.get("path", "")))
                if a == "snapshot":
                    return self.send(200, home.make_snapshot(store, q.get("label", "")))
                if a == "diff":
                    d = home.diff(store, q.get("base", ""))
                    return self.send(200 if d else 404, d or {"error": "no snapshot"})
            if p == "/api/stats":
                c = store.db.execute
                return self.send(200, {
                    "files": c("select count(*) from files").fetchone()[0],
                    "items": c("select count(*) from items").fetchone()[0],
                    "monsters": c("select count(*) from monsters").fetchone()[0],
                    "uniques": c("select count(*) from uniques").fetchone()[0],
                    "models": c("select count(*) from files where ext in ('smd','fmt')").fetchone()[0],
                    "tables": c("select count(*) from files where ext='datc64' and path like 'data/balance/%' and path not like 'data/balance/%/%'").fetchone()[0],
                    "schema": os.path.exists(SCHEMA)})
            if p in ("/api/items", "/api/monsters"):
                t = p.split("/")[-1]
                s = f"%{q.get('q', '')}%"
                lim = min(int(q.get("limit", 200)), 6000)
                only = " and model is not null" if q.get("model") == "1" else ""
                cols = "id,name,icon,model,class,row" if t == "items" else "id,name,model,row,ao"
                args = [s, s]
                if t == "items" and q.get("class"):
                    only += " and class=?"; args.append(q["class"])
                if t == "monsters":
                    cur = store.db.execute(f"select {cols} from {t} where (name like ? or id like ?){only} order by name", args)
                    rows = rows_to_dicts(cur, cols.split(","))
                    bosses = boss_rows(store)
                    for r in rows:
                        r["boss"] = r["row"] in bosses and not (r["name"] or "").startswith(("-|-", "Placeholder"))
                    from . import monster as monmod
                    atags = monmod.area_tags(store)
                    for r in rows:
                        r["tags"] = atags.get(r["row"], ["Без зоны"])
                    if q.get("dedup", "1") == "1":
                        rows = dedupe_monsters(store, rows)
                    if q.get("act"):
                        rows = [r for r in rows if q["act"] in r["tags"]]
                    rows.sort(key=lambda r: not r["boss"])   # stable: bosses first, name order kept inside each group
                    return self.send(200, rows[:lim])
                cur = store.db.execute(f"select {cols} from {t} where (name like ? or id like ?){only} order by name limit ?", args + [lim])
                return self.send(200, rows_to_dicts(cur, cols.split(",")))
            if p == "/api/itemclasses":
                return self.send(200, [{"name": a, "count": b} for a, b in store.db.execute("select class,count(*) from items where class is not null group by class order by class")])
            if p == "/api/uniques":
                like = f"%{q.get('q', '')}%"
                cur = store.db.execute("select name,base,slot,league,icon,model from uniques where (name like ? or base like ?)" + (" and slot=?" if q.get("slot") else "") + " order by name",
                                       (like, like) + ((q["slot"],) if q.get("slot") else ()))
                return self.send(200, rows_to_dicts(cur, ["name", "base", "slot", "league", "icon", "model"]))
            if p == "/api/unique":
                r = store.db.execute("select data,icon,model from uniques where name=?", (q["name"],)).fetchone()
                if not r:
                    return self.send(404, {"error": "not found"})
                d = json.loads(r[0]); d["icon"], d["model"] = r[1], r[2]
                try:
                    from . import sources
                    d["sources"] = sources.for_unique(store, q["name"])
                except Exception:
                    d["sources"] = []
                try:
                    from . import effects
                    u = uniqmap.unique_items(store).get(q["name"])
                    d["effects"] = []
                    if u:
                        sl = uniqmap.SLOT_OF.get(u["slot"])
                        if sl:
                            d["effects"] = actor.equipped(store, u["name"], u["id"], u["ao"], sl, u["ao2"], "str").get("effects", [])
                        else:
                            d["effects"] = effects.item_effects(store, u["id"], u["ao"], u["ao"], [])
                except Exception:
                    d["effects"] = []
                return self.send(200, d)
            if p == "/api/files":
                rows = store.search(f"%{q.get('q', '')}%", q.get("ext") or None, min(int(q.get("limit", 200)), 1000))
                return self.send(200, [{"path": a, "size": b} for a, b in rows])
            if p == "/api/dir":
                fo, fi = store.listdir(q.get("path", ""))
                return self.send(200, {"path": q.get("path", "").strip("/").lower(), "folders": fo, "files": [{"name": n, "size": z} for n, z in fi]})
            if p == "/api/tables":
                s = q.get("q", "").lower()
                rows = store.db.execute(
                    "select path,size from files where ext='datc64' and path like 'data/balance/%' and path not like 'data/balance/%/%' and path like ? order by path",
                    (f"%{s}%",)).fetchall()
                return self.send(200, [{"name": a[len("data/balance/"):-len(".datc64")], "size": b} for a, b in rows])
            if p == "/api/table":
                name = q["name"]
                d = get_dat(name)
                if d is None:
                    return self.send(404, {"error": "no such table"})
                cols, schema = tables.describe(d, name, SCHEMA)
                off, lim, flt = int(q.get("offset", 0)), q.get("lang", "ru"), min(int(q.get("limit", 100)), 500), q.get("q", "").lower()
                out, total = [], 0
                for i in range(d.rows):
                    row = [tables.cell(d, i, c) for c in cols]
                    if flt and not any(flt in str(v).lower() for v in row if v is not None):
                        continue
                    total += 1
                    if total > off and len(out) < lim:
                        out.append([i] + row)
                return self.send(200, {"rows": d.rows, "width": d.width, "schema": schema, "total": total,
                                       "columns": ["#"] + [c[0] + ("[]" if c[2] else "") for c in cols], "data": out})
            if p == "/api/model":
                path = q["path"].lower()
                data = store.read(path)
                if data is None:
                    return self.send(404, {"error": "not found"})
                m = mesh.parse(path, data)
                tex = textures.resolve_for_mesh(store, path, m) if q.get('tex', '1') == '1' else {}
                name = os.path.basename(path).rsplit(".", 1)[0] + ".glb"
                return self.send(200, glb.to_glb(m, textures=tex, raw=q.get("raw") == "1"), "model/gltf-binary", {"Content-Disposition": f'inline; filename="{name}"'})
            if p == "/api/modelinfo":
                path = q["path"].lower()
                m = mesh.parse(path, store.read(path))
                return self.send(200, {"vertices": len(m.pos), "triangles": len(m.idx) // 3, "lods": m.lods, "bbox": m.bbox,
                                       "parts": [{"name": a, "material": b, "indices": d} for a, b, c, d in m.parts]})
            if p == "/api/icon":
                jpg = q.get("fmt") == "jpg"
                png = textures.dds_to_png(store, q["path"].lower(), int(q.get("size", 0)), fmt="JPEG" if jpg else "PNG")
                if png is None:
                    return self.send(404, {"error": "not found"})
                hdrs = {"Cache-Control": "max-age=86400"}
                if q.get("dl") == "1":
                    hdrs["Content-Disposition"] = 'attachment; filename="%s"' % (os.path.basename(q["path"]).rsplit(".", 1)[0] + (".jpg" if jpg else ".png"))
                return self.send(200, png, "image/jpeg" if jpg else "image/png", hdrs)
            if p == "/api/cube":
                jpg = textures.cube_face(store, q["path"].lower(), int(q["face"]), int(q.get("size", 512)))
                if jpg is None:
                    return self.send(404, {"error": "not found"})
                return self.send(200, jpg, "image/jpeg", {"Cache-Control": "max-age=86400"})
            if p == "/api/actors":
                like = f"%{q.get('q', '')}%"
                kind = q.get("kind")
                rows = store.db.execute("select id,kind,name,skeleton,skin from actors where name like ? and name not like '%attachments%'" + (" and kind=?" if kind else "") + " order by kind desc, name limit 400",
                                        (like,) + ((kind,) if kind else ())).fetchall()
                out = [dict(zip(("id", "kind", "name", "skeleton", "skin"), r)) for r in rows]
                if kind in (None, "", "player"):
                    pre = [{"id": "class:" + k, "kind": "player", "name": k, "skeleton": "art/models/charactersfour/onerig.ast", "skin": "", "preset": k}
                           for k in actor.PRESET_FILES if like.strip("%").lower() in k.lower()]
                    out = pre + out
                return self.send(200, out)
            if p == "/api/preset":
                if q.get("npc"):
                    return self.send(200, actor.npc_preset(store, q["npc"]))
                return self.send(200, actor.preset(store, q["name"]))
            if p == "/api/rig":
                a = astmod.load(store, q["ast"])
                if a is None:
                    return self.send(404, {"error": "no rig"})
                return self.send(200, {"bones": [{"n": b["name"], "p": b["parent"], "m": list(b["m"])} for b in a.bones],
                                       "clips": [{"name": c["name"], "fps": c["fps"]} for c in a.clips]})
            if p == "/api/clip":
                a = astmod.load(store, q["ast"])
                c = a.clip_tracks(q["name"]) if a else None
                if c is None:
                    return self.send(404, {"error": "no clip"})
                me = next((x for x in a.clips if x["name"] == q["name"]), None)
                c["parent"] = (me or {}).get("parent") or ""
                return self.send(200, c)
            if p == "/api/skin":
                sm = q["sm"].lower()
                smd = actor.smd_of(store, sm)
                if not smd:
                    return self.send(404, {"error": "no smd"})
                m = mesh.parse_smd(store.read(smd))
                mats = textures.sm_materials(store, smd)
                m.parts = [(n, mats[i] if i < len(mats) else "", s0, c0) for i, (n, _m, s0, c0) in enumerate(m.parts)]
                tex = textures.pbr_for_mesh(store, m, min(int(q.get("tex", 2048)), 4096)) if q.get("pbr", "1") == "1" else {}
                return self.send(200, glb.to_glb_parts(m, textures=tex, skinned=q.get("static") != "1"), "model/gltf-binary")
            if p == "/api/slotitems":
                sl = actor.SLOTS[q["slot"]]
                ph = ",".join("?" * len(sl["classes"]))
                like = f"%{q.get('q', '')}%"
                rows = store.db.execute(f"select id,name,icon,ao,model,class from items where class in ({ph}) and ao is not null and name like ? and name not like '[%' order by name limit 1500", sl["classes"] + [like]).fetchall()
                rows = [r for r in rows if not re.match(r"^(Runeforged|Runemastered) ", r[1])]   # rune-upgraded copies share the model of the base item
                if q.get("unique") == "1" or q.get("npc") == "1":
                    rows = []
                if q["slot"] in ("helmet", "body", "gloves", "boots"):   # armour that has no model fitted to a character (drop-only legacy items) would render broken
                    rows = [r for r in rows if actor.armour_variants(store, r[3])][:400]
                out = [dict(zip(("id", "name", "icon", "ao", "model", "class"), r)) | {"attr": actor.attr_of(r[0])} for r in rows]
                # unique items: their own visual identity (drop .ao with effects), listed after the base types
                ql = q.get("q", "").lower()
                for u in uniqmap.for_slot(store, q["slot"]):
                    if ql in u["name"].lower() and (q["slot"] not in ("helmet", "body", "gloves", "boots") or actor.armour_variants(store, u["ao"])) and u["class"] in (sl["classes"] + [None]):
                        out.append({"id": u["id"], "name": u["name"], "icon": u["icon"], "ao": u["ao"], "model": None, "class": u["class"] or "", "attr": actor.attr_of(u["ao"]), "unique": True})
                if q.get("unique") != "1":
                    for u in npcitems.for_slot(store, q["slot"]):
                        if ql in u["name"].lower():
                            out.append({"id": u["id"], "name": u["name"], "icon": None, "ao": u["ao"], "model": None, "class": u["class"] or "", "attr": None, "npc": True})
                if q.get("npc") == "1":
                    out = [o for o in out if o.get("npc")]
                elif q.get("unique") == "1":
                    out = [o for o in out if o.get("unique")]
                return self.send(200, out)
            if p == "/api/equipped":
                if q["id"].startswith("npc:"):
                    u = npcitems.npc_items(store).get(q["id"])
                    r = (u["id"], u["name"], u["ao"], None, u["class"], u["ao2"]) if u else None
                elif q["id"].startswith("unique:"):
                    u = uniqmap.unique_items(store).get(q["id"][7:])
                    r = (u["id"], u["name"], u["ao"], None, u["class"], u["ao2"]) if u else None
                else:
                    r = store.db.execute("select id,name,ao,model,class,ao2 from items where id=? limit 1", (q["id"],)).fetchone()
                if not r:
                    return self.send(404, {"error": "no item"})
                e = actor.equipped(store, r[1], r[0], r[2], q["slot"], r[5], q.get("arch") or None)
                e["fixed"] = e["fixed"] or (r[3] if r[3] and r[3].endswith(".fmt") else None)
                e["class"] = r[4]; e["tokens"] = actor.weapon_tokens(r[4])
                return self.send(200, e)
            if p == "/api/anims":
                tokens = q.get("tokens", "unarmed").split(",")
                return self.send(200, actor.anim_list(store, tokens, q.get("q", ""))[:min(int(q.get("limit", 600)), 5000)])
            if p == "/tile":
                return self.send(200, open(os.path.join(ROOT, "web", "tile.html"), "rb").read(), "text/html; charset=utf-8", {"Cache-Control": "no-store"})
            if p == "/api/tile":
                tgt = q["tgt"].lower()
                cdir = os.path.join(DATA, "cache"); os.makedirs(cdir, exist_ok=True)
                gp = os.path.join(cdir, "tile_" + re.sub(r"\W", "_", tgt) + ".glb")
                if not os.path.exists(gp):
                    out, acc = scene.build_tgt(store, tgt, log=lambda *a: None)
                    open(gp, "wb").write(scene.finish_scene(store, out, acc, log=lambda *a: None))
                return self.send(200, open(gp, "rb").read(), "model/gltf-binary")
            if p == "/api/pet":
                em = pet.load(store, q["path"])
                for e in em:
                    e["texUrl"] = "/api/icon?size=256&path=" + urllib.parse.quote(e["tex"]) if e.get("tex") else None
                    if e.get("mesh"):
                        e["meshUrl"] = "/api/model?raw=1&tex=0&path=" + urllib.parse.quote(e["mesh"])
                return self.send(200, em)
            if p.startswith("/static/fonts/") and p.endswith(".ttf"):
                f = os.path.join(ROOT, "web", "fonts", os.path.basename(p))
                if os.path.exists(f):
                    return self.send(200, open(f, "rb").read(), "font/ttf", {"Cache-Control": "max-age=86400"})
                return self.send(404, {"error": "not found"})
            if p.startswith("/static/") and p.endswith(".js"):
                f = os.path.join(ROOT, "web", "i18n" if p.startswith("/static/i18n/") else "", os.path.basename(p))
                if os.path.exists(f):
                    return self.send(200, open(f, "rb").read(), "text/javascript; charset=utf-8", {"Cache-Control": "no-store"})
                return self.send(404, {"error": "not found"})
            if p == "/api/tree":
                from . import tree
                return self.send(200, tree.tree(store, "atlas" if q.get("kind") == "atlas" else "passives"))
            if p == "/api/rec/file":
                from . import recsrv
                f, nm = recsrv.path_of(q.get("id", ""))
                if not f or not os.path.exists(f):
                    return self.send(404, {"error": "no recording"})
                return self.send(200, open(f, "rb").read(), "video/webm", {"Content-Disposition": f'attachment; filename="{nm}"'})
            if p == "/api/sources":
                from . import sources
                return self.send(200, sources.listing(store, q.get("q", ""), q.get("type", "")))
            if p == "/api/source":
                from . import sources
                d = sources.card(store, q.get("id", ""))
                return self.send(200 if d else 404, d or {"error": "no source"})
            if p == "/api/refsections":
                from . import sections
                return self.send(200, [{"k": k, "ru": v} for k, v in sections.SECTIONS])
            if p == "/api/ref":
                from . import sections
                return self.send(200, sections.listing(store, q.get("sec", "passives"), q.get("q", ""), q.get("f", ""), min(int(q.get("limit", 500)), 2000), int(q.get("offset", 0)), q.get("lang", "ru")))
            if p == "/api/refcard":
                from . import sections
                d = sections.card(store, q["sec"], q["id"], q.get("lang", "ru"))
                return self.send(200 if d else 404, d or {"error": "no entry"})
            if p == "/api/mods":
                from . import mods
                return self.send(200, mods.search(store, q.get("q", ""), q.get("domain", ""), q.get("gen", ""), q.get("tag", ""), min(int(q.get("limit", 100)), 500), int(q.get("offset", 0))))
            if p == "/api/modfacets":
                from . import mods
                return self.send(200, mods.facets(store))
            if p == "/api/modbases":
                from . import modbases
                return self.send(200, modbases.bases(store))
            if p == "/api/modclass":
                from . import modbases
                d = modbases.for_class(store, q["cls"], int(q.get("group", -1)), q.get("q", ""))
                return self.send(200 if d else 404, d or {"error": "no class"})
            if p == "/api/mod":
                from . import mods
                d = mods.detail(store, q["id"])
                return self.send(200 if d else 404, d or {"error": "no mod"})
            if p == "/api/monster":
                from . import monster
                row = int(q["row"])
                cdir = os.path.join(DATA, "cache", "monsters"); os.makedirs(cdir, exist_ok=True)
                gp = os.path.join(cdir, f"{row}_m10.json")
                if not os.path.exists(gp):
                    json.dump(monster.detail(store, row), open(gp, "w", encoding="utf-8"), ensure_ascii=False)
                return self.send(200, open(gp, "rb").read())
            if p == "/api/sfx":
                from . import sfx
                wav = sfx.render(store, q["event"], q.get("banks", "").split("|"))
                if wav is None:
                    return self.send(500, {"error": "render failed"})
                extra = {"Cache-Control": "max-age=86400"}
                if q.get("dl") == "1":
                    extra["Content-Disposition"] = f'attachment; filename="{sfx.filename(q["event"])}"'
                return self.send(200, open(wav, "rb").read(), "audio/wav", extra)
            if p == "/api/sfxzip":
                from . import sfx
                data = sfx.zip_monster(store, int(q["row"]))
                return self.send(200, data, "application/zip", {"Content-Disposition": f'attachment; filename="monster_{int(q["row"])}_sounds.zip"'})
            if p == "/api/audio":
                path = q["path"].lower()
                if not path.endswith(".ogg"):
                    return self.send(400, {"error": "ogg only"})
                data = store.read(path)
                if data is None:
                    return self.send(404, {"error": "not found"})
                extra = {"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'} if q.get("dl") == "1" else None
                return self.send(200, data, "audio/ogg", extra)
            if p == "/api/skills":
                from . import skills
                ql = q.get("q", "").lower(); gem = q.get("gem") == "1"
                rows = [x for x in skills.skill_list(store) if not x["aura"] and (not gem or (x["gem"] and x["ge"])) and (not ql or ql in x["name"].lower() or ql in x["ru"].lower() or ql in x["id"].lower())]
                return self.send(200, rows[:1500])
            if p == "/api/gems":
                from . import gems
                return self.send(200, gems.search(store, q.get("q", ""), q.get("kind", ""), q.get("tag", ""), cat=q.get("cat", "")))
            if p == "/api/gemfacets":
                from . import gems
                return self.send(200, gems.facets(store))
            if p == "/api/gem":
                from . import gems
                d = gems.detail(store, q["k"])
                return self.send(200 if d else 404, d or {"error": "no gem"})
            if p == "/api/skill":
                from . import skills
                i = int(q["i"])
                cdir = os.path.join(DATA, "cache", "skills"); os.makedirs(cdir, exist_ok=True)
                gp = os.path.join(cdir, f"{i}.json")
                if not os.path.exists(gp):
                    d = skills.detail(store, i)
                    for a_ in d["anim"]:
                        tl = a_.pop("timeline_events", None)
                        if tl:
                            a_["events"] = [{"name": x["name"], "view": x["view"], "events": x["events"][:12]} for x in tl["animations"] if x["events"]][:6]
                    json.dump(d, open(gp, "w", encoding="utf-8"), ensure_ascii=False)
                return self.send(200, json.load(open(gp, encoding="utf-8")))
            if p == "/api/skillsfx":
                from . import skillsfx
                return self.send(200, skillsfx.cached(store, int(q["i"])))
            if p == "/api/aomesh":
                from . import pet as petmod
                f = actor.ao_fields(store, q["ao"].lower())
                sm = (f["skins"] or [None])[0]
                tex, tris = None, 0
                if sm:
                    smd = actor.smd_of(store, sm.lower())
                    if smd:
                        m = mesh.parse_smd(store.read(smd)); tris = sum(c for *_x, c in m.parts) // 3
                        for mt in textures.sm_materials(store, smd):
                            info = textures.material(store, mt)
                            tex = (info or {}).get("base") or petmod.first_texture(store, mt.lower())
                            if tex:
                                break
                return self.send(200, {"sm": sm, "tex": tex, "tris": tris})
            if p == "/api/wornmodel":
                from . import iteminfo
                if q.get("unique"):
                    u = uniqmap.unique_items(store).get(q["unique"])
                    r = (u["ao"], u["ao2"], u["class"]) if u else None
                else:
                    r = store.db.execute("select ao,ao2,class from items where row=?", (int(q["row"]),)).fetchone()
                return self.send(200, {"model": iteminfo.worn_model(store, *r) if r else None})
            if p == "/api/iteminfo":
                from . import iteminfo
                return self.send(200, iteminfo.info(store, int(q["row"])))
            if p == "/api/ground":
                from . import ground
                cdir = os.path.join(DATA, "cache"); os.makedirs(cdir, exist_ok=True)
                kind = "normal" if q.get("k") == "normal" else "colour"
                gp = os.path.join(cdir, f"ground_{kind}.jpg")
                if not os.path.exists(gp):
                    open(gp, "wb").write(getattr(ground, kind)(store))
                return self.send(200, open(gp, "rb").read(), "image/jpeg")
            if p == "/api/envs":
                rows = store.db.execute("select path from files where ext='env' and path like 'metadata/environmentsettings/%' order by path").fetchall()
                loads = store.db.execute("select path from files where ext='dds' and path like 'art/textures/interface/loadingimages/%' order by path").fetchall()
                return self.send(200, {"envs": [r[0][len("metadata/environmentsettings/"):-4] for r in rows],
                                       "loading": [{"name": r[0].rsplit("/", 1)[-1][:-4], "path": r[0]} for r in loads]})
            if p == "/api/lut":
                b = store.read("metadata/environmentsettings/" + q["name"].lower() + ".env")
                j = json.loads(decode_text(b)) if b else {}
                tp = (j.get("post_transform") or {}).get("texture")
                d = store.read(tp.lower()) if tp else None
                if not d:
                    return self.send(404, {"error": "no lut"})
                import struct
                h, w, depth = struct.unpack_from("<III", d, 12)[0], struct.unpack_from("<I", d, 16)[0], struct.unpack_from("<I", d, 24)[0]
                return self.send(200, d[128:128 + w * h * depth * 4], "application/octet-stream", {"X-Lut-Size": f"{w},{h},{depth}"})
            if p == "/api/env":
                b = store.read("metadata/environmentsettings/" + q["name"].lower() + ".env")
                if b is None:
                    return self.send(404, {"error": "not found"})
                j = json.loads(decode_text(b))
                dl, pl, em, fog = j.get("directional_light", {}), j.get("player_light", {}), j.get("environment_mapping", {}), j.get("screenspace_fog", {})
                return self.send(200, {"dir": {k: dl.get(k) for k in ("colour", "multiplier", "phi", "theta")} if dl else None,
                                       "player": pl.get("colour"), "env_brightness": em.get("env_brightness"),
                                       "cube": em.get("diffuse_cube"), "hor_angle": em.get("hor_angle"), "fog": fog.get("ssf_color"), "fog_alpha": fog.get("ssf_color_alpha"),
                                       "area_dust": j.get("area", {}).get("dust_color")})
            if p == "/api/file":
                path = q["path"].lower()
                data = store.read(path)
                if data is None:
                    return self.send(404, {"error": "not found"})
                if q.get("text") == "1":
                    return self.send(200, decode_text(data), "text/plain; charset=utf-8")
                return self.send(200, data, "application/octet-stream",
                                 {"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'})
            self.send(404, {"error": "not found"})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # the browser cancelled the request (e.g. scrolled past a lazy icon)
        except Exception as e:
            try:
                self.send(500, {"error": f"{type(e).__name__}: {e}"})
            except OSError:
                pass


def main(db_path=DB, port=8765):
    global store
    store = Store(db_path) if os.path.isfile(db_path) else None   # None: first run, the setup page builds the database
    ThreadingHTTPServer.request_queue_size = 256   # default backlog of 5 resets connections when a long list loads thousands of icons
    ThreadingHTTPServer.daemon_threads = True
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"http://127.0.0.1:{port}", flush=True)
    srv.serve_forever()
