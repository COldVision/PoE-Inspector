"""Assemble a character-selection scene (terrain tiles + character) from game files into one GLB.

Layout facts measured from the data: forest.tgt lists 94 materials and, per 4x4 tile (row 4 first), run-length
(material, count) pairs for the tile's .tgm parts; tile (c,r) sits at ((c-1)*250, (r-1)*250); forest.tmd gives
world positions (campfire, character) in the same units."""
import io, math, os, re, struct
from . import mesh as meshmod, textures
from .catalog import text
from .glb import to_glb
from PIL import Image

ROOT = "art/models/interface/gallowscharacterselection/"
TILE = 250.0
CHAR_YAW = 0.0  # armour bind pose heading offset (radians), tuned visually


def parse_tgt(store, name):
    t = text(store, f"{ROOT}{name}.tgt")
    mats = re.findall(r'^\s*"([^"]+\.mat)"', t, re.M)
    sec = t.split("SubTileMaterialIndices", 1)[1]
    lines = [l.strip() for l in sec.split("\n") if l.strip()]
    tiles = []
    for l in lines:
        v = [int(x) for x in l.split() if re.fullmatch(r"-?\d+", x)]
        if not v or len(v) != 1 + 2 * v[0]:
            continue
        per = []
        for i in range(v[0]):
            per += [v[1 + 2 * i]] * v[2 + 2 * i]
        tiles.append(per)
    return mats, tiles[:16]


def parse_tmd(store, name):
    out = []
    for l in text(store, f"{ROOT}{name}.tmd").split("\n"):
        m = re.match(r'^\s*-?\d+ -?\d+ \d+ (\S+) (\S+) (\S+) (\S+) \S+ \S+ \S+ \S+ \S+ \S+ "([^"]*)" "([^"]*)"', l)
        if m:
            x, y, z, rot = (float(m.group(i)) for i in (1, 2, 3, 4))
            out.append({"x": x, "y": y, "z": z, "rot": rot, "ao": m.group(5), "name": m.group(6)})
    return out


_tile_cache = {}


_info_cache = {}


def info_of(store, mat):
    if mat not in _info_cache:
        try:
            _info_cache[mat] = textures.material(store, mat)
        except Exception:
            _info_cache[mat] = None
    return _info_cache[mat]


def tiling_of(store, mat):
    info = info_of(store, mat)
    if info and info.get("blend"):
        return 1.0  # baked into the texture
    return info["tiling"] if info and info["base"] else 1.0


def camera_pose(store, clip_name):
    """Camera bone position/rotation (world units) of a clip in the interface camera .ast (format per FORMATS §8)."""
    from . import bundle
    d = store.read(ROOT + "camera/camera.ast")
    nb, na, nl = d[1], d[3], d[7]
    p = 8
    for _ in range(nb):
        p += 68 + d[p + 66]
    for _ in range(nl):
        p += 2 + 48 + 4 + 4 + 2 + d[p]
    clip = None
    for _ in range(na):
        off, size = struct.unpack_from("<II", d, p + 7)
        nlen, plen = d[p + 5], d[p + 6]
        p += 15
        name = d[p:p + nlen].decode()
        p += nlen + plen
        if name == clip_name:
            clip = (off, size)
    raw = bundle.unpack(d[p:])
    q = raw[clip[0]:clip[0] + clip[1]]
    o = 0
    while o + 33 <= len(q):
        bi, ns, nr, npo = struct.unpack_from("<4I", q, o + 1)
        o += 33
        rot = struct.unpack_from("<5f", q, o + 16 * ns)
        pos = struct.unpack_from("<4f", q, o + 16 * ns + 20 * nr)
        if bi == 1:
            return {"pos": list(pos[1:]), "quat": list(rot[1:])}
        o += 16 * ns + 20 * nr + 16 * npo
    return None


def jpeg_if_opaque(png, alpha):
    if alpha != "OPAQUE":
        return png, alpha, "image/png"
    im = Image.open(io.BytesIO(png)).convert("RGB")
    out = io.BytesIO()
    im.save(out, "JPEG", quality=82)
    return out.getvalue(), alpha, "image/jpeg"


def build(store, name="forest", log=print, tex_size=512, with_character=True):
    mats, tiles = parse_tgt(store, name)
    entries = parse_tmd(store, name)
    log(f"materials={len(mats)} tiles={len(tiles)} entries={len(entries)}")
    out = meshmod.Mesh()
    acc = {}  # material path -> list of triangles (global vertex ids)
    order = [(c, r) for r in (4, 3, 2, 1) for c in (1, 2, 3, 4)]
    campfire = None
    for ti, (c, r) in enumerate(order):
        d = store.read(f"{ROOT}tgms/{name}_c{c}r{r}.tgm")
        if d is None or ti >= len(tiles):
            continue
        m = meshmod.Mesh()
        _p, nmesh, ranges = meshmod._dolm(d, 0x1f, m, struct.unpack_from("<I", d, 25)[0])
        per = tiles[ti]
        if len(per) != len(ranges):
            log(f"  tile c{c}r{r}: {len(ranges)} parts vs {len(per)} materials - skipped")
            continue
        dx, dy = (c - 1) * TILE, r * TILE
        for (start, cnt), mi in zip(ranges, per):
            ids = m.idx[start:start + cnt]
            if not ids:
                continue
            remap = {}
            for v in ids:
                if v not in remap:
                    remap[v] = len(out.pos)
                    x, y, z = m.pos[v]
                    out.pos.append((x + dx, y + dy, z))
                    out.nrm.append(m.nrm[v] if v < len(m.nrm) else (0, 0, -1))
                    out.uv.append(m.uv[v] if v < len(m.uv) else (0, 0))
            mat = mats[mi] if mi < len(mats) else ""
            ts = tiling_of(store, mat)
            if ts != 1.0:
                for gi in remap.values():
                    u, v2 = out.uv[gi]
                    out.uv[gi] = (u * ts, v2 * ts)
            acc.setdefault(mat, []).extend(remap[v] for v in ids)
    # character + other placed skinned objects
    placed = []
    for e in entries:
        if "Character" in e["ao"] and "Login" in e["ao"] and e["name"].endswith("PreviousCharacter"):
            placed.append(e)
    tex = {}
    AR = "art/models/items/armours/"
    ARMOUR = [AR + "bodyarmours/armoursfour/steelplate/steelplatestr.sm",
              AR + "helmets/armoursfour/spiredgreathelm/spiredgreathelmstr.sm",
              AR + "gloves/armoursfour/bolsteredmitts/bolsteredmittsstr.sm",
              AR + "boots/armoursfour/trimmedgreaves/trimmedgreavesstr.sm"]

    def add_skinned(smpath, e, yaw):
        smt = text(store, smpath)
        smd = re.search(r'SkinnedMeshData\s+"([^"]+)"', smt)
        if not smd:
            return
        p = smd.group(1).lower()
        cm = meshmod.parse_smd(store.read(p))
        materials = []
        for mm in re.finditer(r'"([^"]+\.mat)"\s+(\d+)', smt):
            materials += [mm.group(1)] * int(mm.group(2))
        ca, sa = math.cos(yaw), math.sin(yaw)
        base = len(out.pos)
        for (x, y, z), n, uv in zip(cm.pos, cm.nrm or [(0, 0, -1)] * len(cm.pos), cm.uv or [(0, 0)] * len(cm.pos)):
            out.pos.append((e["x"] + x * ca - y * sa, e["y"] + x * sa + y * ca, e["z"] + z))
            out.nrm.append((n[0] * ca - n[1] * sa, n[0] * sa + n[1] * ca, n[2]))
            out.uv.append(uv)
        for i, (_n, _m, start, cnt) in enumerate(cm.parts):
            mat = materials[i] if i < len(materials) else ""
            acc.setdefault(mat, []).extend(base + v for v in cm.idx[start:start + cnt])
        log(f"  {p.rsplit('/', 1)[-1]}: {len(cm.pos)} verts")

    for e in (placed[:1] if with_character else []):
        yaw = e["rot"] + CHAR_YAW
        for smpath in ARMOUR:
            try:
                add_skinned(smpath, e, yaw)
            except Exception as ex:
                log(f"  armour {smpath}: {ex}")
    for e in entries:
        if "campfire" in e["ao"].lower() and campfire is None:
            campfire = (e["x"], e["y"], e["z"])
    # the fire belongs on the log pile: use the burnt-wood / campfire base mesh centroid when present
    pile = [out.pos[v] for m_, ids in acc.items() if "campfirebase" in m_.lower() or "burntwood" in m_.lower() for v in set(ids)]
    if pile:
        px = sorted(p[0] for p in pile)[len(pile) // 2]
        py = sorted(p[1] for p in pile)[len(pile) // 2]
        near = [p for p in pile if abs(p[0] - px) < 60 and abs(p[1] - py) < 60]
        campfire = (px, py, min(p[2] for p in near) if near else campfire[2])
        log(f"campfire pile at {campfire} from {len(pile)} vertices")
    # parts + textures
    for mat, ids in acc.items():
        inf = info_of(store, mat) if mat else None
        if "shadowonly" in mat.lower() or (inf and inf["shadow_only"]):
            continue
        start = len(out.idx)
        out.idx.extend(ids)
        out.parts.append((mat.rsplit("/", 1)[-1], mat, start, len(ids)))
    extras = {}
    for mat in acc:
        inf = info_of(store, mat) if mat else None
        if inf and (inf["mode"] in ("additive", "multiply") or inf["unlit"]):
            extras[mat] = {"mode": inf["mode"], "unlit": inf["unlit"], "mult": inf["mult"]}
    for mat in acc:
        if mat and mat not in tex:
            try:
                info = textures.material(store, mat)
                if info and info.get("blend"):
                    tex[mat] = jpeg_if_opaque(textures.bake_blend(store, info["blend"], info["tiling"], 1024), "OPAQUE")
                elif info and info["base"]:
                    png = textures.dds_to_png(store, info["base"], max_size=tex_size, opaque=info["alpha"] == "OPAQUE")
                    if png:
                        tex[mat] = jpeg_if_opaque(png, info["alpha"])
            except Exception as ex:
                log(f"  texture {mat}: {ex}")
    log(f"verts={len(out.pos)} tris={len(out.idx)//3} materials={len(acc)} textured={len(tex)}")
    cam = None
    try:
        cam = camera_pose(store, "On" + name.title())
    except Exception as ex:
        log(f"camera: {ex}")
    effects = []
    for e in entries:
        if "campfire" in e["ao"].lower() and e["ao"].lower().endswith(".ao") and campfire:
            ao = text(store, e["ao"].lower())
            for f in re.findall(r'"filename":\s*"([^"]+\.pet)"', ao):
                if f not in [x["pet"] for x in effects]:
                    effects.append({"pet": f, "pos": campfire})
    meta = {"effects": effects, "camera": cam, "campfire": campfire, "character": [(e["x"], e["y"], e["z"], e["rot"]) for e in placed[:1]]}
    return to_glb(out, textures=tex, extras=extras), meta


def mesh_count(d):
    """DOLm stores the part count as u8; the tile header keeps the true u32 when it overflowed."""
    u8 = d[0x1f + 4 + 3] if d[0x1f:0x23] == b"DOLm" else None
    u32 = struct.unpack_from("<I", d, 25)[0]
    if u8 is not None and 0 < u32 < 5000 and u32 % 256 == u8:
        return u32
    return u8


def parse_tgt_generic(store, tgt_path):
    t = text(store, tgt_path)
    mats = re.findall(r'^\s*"([^"]+\.mat)"', t, re.M)
    size = re.search(r"Size\s+(\d+)\s+(\d+)", t)
    w, h = int(size.group(1)), int(size.group(2))
    root = re.search(r'TileMeshRoot\s+"([^"]+)"', t).group(1)
    sec = t.split("SubTileMaterialIndices", 1)[1]
    lines = [l.strip() for l in sec.split("\n") if l.strip()]
    tiles = []
    for l in lines:
        v = [int(x) for x in l.split() if re.fullmatch(r"-?\d+", x)]
        if not v or len(v) != 1 + 2 * v[0]:
            continue
        per = []
        for i in range(v[0]):
            per += [v[1 + 2 * i]] * v[2 + 2 * i]
        tiles.append(per)
    return mats, tiles[:w * h], w, h, root


def build_tgt(store, tgt_path, log=print, tex_size=256, offset=(0.0, 0.0), out=None, acc=None):
    """Assemble all chunks of one tile template (any Size) into a Mesh + material->index lists."""
    mats, tiles, w, h, root = parse_tgt_generic(store, tgt_path)
    out = out or meshmod.Mesh()
    acc = acc if acc is not None else {}
    order = [(c, r) for r in range(h, 0, -1) for c in range(1, w + 1)]
    used = 0
    for ti, (c, r) in enumerate(order):
        if ti >= len(tiles):
            break
        d = store.read(f"{root.lower()}_c{c}r{r}.tgm")
        if d is None:
            continue
        m = meshmod.Mesh()
        try:
            _p, nmesh, ranges = meshmod._dolm(d, 0x1f, m, mesh_count(d))
        except Exception as ex:
            log(f"  chunk c{c}r{r}: {ex}")
            continue
        per = tiles[ti]
        if len(per) != len(ranges):
            continue
        dx, dy = offset[0] + (c - 1) * TILE, offset[1] + r * TILE
        for (start, cnt), mi in zip(ranges, per):
            ids = m.idx[start:start + cnt]
            if not ids:
                continue
            remap = {}
            for v in ids:
                if v not in remap:
                    remap[v] = len(out.pos)
                    x, y, z = m.pos[v]
                    out.pos.append((x + dx, y + dy, z))
                    out.nrm.append(m.nrm[v] if v < len(m.nrm) else (0, 0, -1))
                    out.uv.append(m.uv[v] if v < len(m.uv) else (0, 0))
            mat = mats[mi] if mi < len(mats) else ""
            acc.setdefault(mat, []).extend(remap[v] for v in ids)
        used += 1
    log(f"{tgt_path.rsplit('/',1)[-1]}: size {w}x{h}, chunks used {used}, verts {len(out.pos)}")
    return out, acc


def finish_scene(store, out, acc, tex_size=256, log=print, extra_tex=None):
    """Materials -> textures, shadow-only removal, extras; return GLB bytes."""
    tex, extras = dict(extra_tex or {}), {}
    for mat, ids in list(acc.items()):
        inf = info_of(store, mat) if mat and mat not in tex else None
        if "shadowonly" in mat.lower() or (inf and inf["shadow_only"]):
            continue
        start = len(out.idx)
        out.idx.extend(ids)
        out.parts.append((mat.rsplit("/", 1)[-1], mat, start, len(ids)))
        if inf and (inf["mode"] in ("additive", "multiply") or inf["unlit"]):
            extras[mat] = {"mode": inf["mode"], "unlit": inf["unlit"], "mult": inf["mult"]}
        if mat and mat not in tex:
            try:
                if inf and inf.get("blend"):
                    tex[mat] = jpeg_if_opaque(textures.bake_blend(store, inf["blend"], inf["tiling"], 512), "OPAQUE")
                elif inf and inf["base"]:
                    png = textures.dds_to_png(store, inf["base"], max_size=tex_size, opaque=inf["alpha"] == "OPAQUE")
                    if png:
                        tex[mat] = jpeg_if_opaque(png, inf["alpha"])
            except Exception as ex:
                log(f"  texture {mat}: {ex}")
    log(f"scene verts={len(out.pos)} tris={len(out.idx)//3} mats={len(out.parts)} textured={len(tex)}")
    return to_glb(out, textures=tex, extras=extras)
