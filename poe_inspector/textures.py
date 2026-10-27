"""Icons and base-colour textures: .dds -> PNG (Pillow), .mat JSON -> base colour + alpha mode."""
import io, json, re
from PIL import Image

BASE_ROLES = ("base_color_texture", "AlbedoTransparency_TEX", "AlbedoSpecMask_TEX", "AlbedoTransparency",
              "AlbedoMetallic", "Masked_AT_Color", "Albedo_TEX", "03 Material01_albedo", "ColourSpecular_TEX")
_png_cache = {}


def mat_text(b):
    for enc in ("utf-16", "utf-8"):
        try:
            t = b.decode(enc).lstrip("﻿")
            if t.lstrip().startswith("{"):
                return t
        except UnicodeDecodeError:
            pass
    return b.decode("utf-16-le", "replace").lstrip("﻿")


_SRGB2UNORM = {72: 71, 75: 74, 78: 77, 99: 98, 91: 87, 29: 28}   # same pixel data, Pillow only knows the UNORM ids


def fix_dds(b):
    """DX10 DDS files with an *_SRGB format id are valid but Pillow rejects them: rewrite the id to the UNORM twin."""
    if len(b) > 132 and b[84:88] == b"DX10":
        f = int.from_bytes(b[128:132], "little")
        if f in _SRGB2UNORM:
            return b[:128] + _SRGB2UNORM[f].to_bytes(4, "little") + b[132:]
    return b


def dds_to_png(store, path, max_size=0, opaque=False, fmt="PNG"):
    key = (path.lower(), max_size, opaque, fmt)
    if key in _png_cache:
        return _png_cache[key]
    b = store.read(path)
    if b is None:
        return None
    im = Image.open(io.BytesIO(fix_dds(b)))
    im.load()
    im = im.convert("RGBA")
    if opaque:
        im.putalpha(255)
    if max_size and max(im.size) > max_size:
        im.thumbnail((max_size, max_size))
    out = io.BytesIO()
    if fmt == "JPEG":
        im = im.convert("RGB")
        im.save(out, "JPEG", quality=85)
    else:
        im.save(out, "PNG")
    data = out.getvalue()
    if len(_png_cache) > 400:
        _png_cache.pop(next(iter(_png_cache)))
    _png_cache[key] = data
    return data


def material(store, mat_path):
    """-> {'base': dds path | None, 'alpha': 'OPAQUE'|'MASK'|'BLEND'} """
    b = store.read(mat_path.lower())
    if b is None:
        return None
    try:
        j = json.loads(mat_text(b))
    except Exception:
        return None
    base, alpha, tiling = None, "OPAQUE", 1.0
    mode, shadow_only, unlit, mult = "opaque", False, False, 1.0
    blend = {}
    for g in j.get("graphinstances", []):
        parent = g.get("parent", "")
        if "ShadowOnly" in parent:
            shadow_only = True
        if "DisableLighting" in parent:
            unlit = True
        if "ForceAdditive" in parent:
            mode = "additive"
        elif "ForceMultiply" in parent:
            mode = "multiply"
        elif "ForceAlphaBlend" in parent or "NoZWriteAlphaBlend" in parent:
            mode = "blend" if mode == "opaque" else mode
        elif "ForceAlphaTest" in parent and mode == "opaque":
            mode = "mask"
        elif parent.endswith("/ForceAlpha.fxgraph") and mode == "opaque":
            mode = "mask"
        if "ForceAlphaTest" in parent:
            alpha = "MASK"
        elif "ForceAlphaBlend" in parent or "ForceNoZWriteAlphaBlend" in parent or "ForceAdditive" in parent:
            alpha = "BLEND" if alpha != "MASK" else alpha
        for cp in g.get("custom_parameters", []):
            if cp.get("name") in ("01 mask", "03 Material01_albedo", "07 Material02_albedo"):
                for p in cp.get("parameters", []):
                    if "path" in p:
                        blend[cp["name"]] = p["path"]
            if cp.get("name") == "Albedo_MULT1":
                for p in cp.get("parameters", []):
                    if isinstance(p.get("value"), (int, float)):
                        mult = float(p["value"])
            if cp.get("name") == "02 TilingRate":
                for p in cp.get("parameters", []):
                    if "value" in p:
                        tiling = float(p["value"])
            if base is None and cp.get("name") in BASE_ROLES:
                for p in cp.get("parameters", []):
                    if "path" in p:
                        base = p["path"]
                        break
    if mode == "mask" and alpha == "OPAQUE":
        alpha = "MASK"
    return {"base": base, "alpha": alpha, "tiling": tiling, "mode": mode, "shadow_only": shadow_only, "unlit": unlit, "mult": mult, "blend": blend if len(blend) == 3 else None}


_sm_dir_cache = {}


def _sm_for(store, smd_path):
    """Find the .sm whose SkinnedMeshData names this .smd (they sit in the same folder, names differ)."""
    from .catalog import text
    d = smd_path.rsplit("/", 1)[0] + "/"
    if d not in _sm_dir_cache:
        m = {}
        for p, _sz in store.search(d + "%.sm", "sm", 2000):
            if "/" in p[len(d):]:
                continue
            t = text(store, p)
            mm = re.search(r'SkinnedMeshData\s+"([^"]+)"', t)
            if mm:
                m[mm.group(1).lower()] = t
        _sm_dir_cache[d] = m
    return _sm_dir_cache[d].get(smd_path.lower())


def sm_materials(store, smd_path):
    """Per-mesh material list of a .smd, from its .sm descriptor."""
    t = _sm_for(store, smd_path)
    if not t:
        return []
    m = re.search(r"Materials\s+(\d+)(.*?)(?:BoundingBox|\Z)", t, re.S)
    out = []
    if m:
        for mm in re.finditer(r'"([^"]+)"\s+(\d+)', m.group(2)):
            out += [mm.group(1)] * int(mm.group(2))
    return out


def resolve_for_mesh(store, path, mesh):
    """Fill mesh.parts' material for .smd and return {material path: (png bytes, alpha mode)}."""
    if path.endswith(".smd"):
        mats = sm_materials(store, path)
        mesh.parts = [(n, mats[i] if i < len(mats) else "", s, c) for i, (n, _m, s, c) in enumerate(mesh.parts)]
    result = {}
    for _n, mat, _s, _c in mesh.parts:
        if not mat or mat in result:
            continue
        try:
            info = material(store, mat)
            if info and info["base"]:
                png = dds_to_png(store, info["base"], max_size=2048, opaque=info["alpha"] == "OPAQUE")
                if png:
                    result[mat] = (png, info["alpha"])
        except Exception:
            pass
    return result


def _mip_layout(size):
    """(offset within a face, edge) for every mip of one BC6H cube face."""
    out, off, e = [], 0, size
    while True:
        out.append((off, e))
        off += max(1, e // 4) ** 2 * 16
        if e == 1:
            break
        e //= 2
    return out, off


def cube_face(store, path, face, want=256, fmt="JPEG"):
    """Decode one face of a BC6H cubemap .dds (DXGI 95) at the mip closest to `want` px -> JPEG/PNG bytes."""
    import struct, texture2ddecoder
    key = ("cube", path.lower(), face, want, fmt)
    if key in _png_cache:
        return _png_cache[key]
    b = store.read(path)
    if b is None:
        return None
    h, w = struct.unpack_from("<II", b, 12)
    dxgi = struct.unpack_from("<I", b, 128)[0] if b[84:88] == b"DX10" else 0
    if dxgi != 95:
        raise ValueError(f"unsupported cubemap format {dxgi}")
    mips, face_size = _mip_layout(w)
    off, edge = min(mips, key=lambda m: abs(m[1] - want))
    start = 148 + face * face_size + off
    raw = texture2ddecoder.decode_bc6(b[start:start + max(1, edge // 4) ** 2 * 16], edge, edge)
    im = Image.frombytes("RGBA", (edge, edge), raw, "raw", "BGRA").convert("RGB")
    out = io.BytesIO()
    im.save(out, fmt, **({"quality": 88} if fmt == "JPEG" else {}))
    _png_cache[key] = out.getvalue()
    return _png_cache[key]


def bake_blend(store, blend, tiling, size=512):
    """Bake a TwoMaterialsMasked terrain material (mask R picks between two tiled albedos) into one texture."""
    import numpy as np

    def load(path, sz=None):
        b = store.read(path.lower())
        im = Image.open(io.BytesIO(fix_dds(b))); im.load()
        im = im.convert("RGB")
        return im.resize((sz, sz), Image.BILINEAR) if sz else im
    mask = np.asarray(load(blend["01 mask"], size), dtype=np.float32)[..., 0:1] / 255.0
    tile = int(round(tiling)) or 1
    a = load(blend["03 Material01_albedo"]); b = load(blend["07 Material02_albedo"])
    def tiled(im):
        base = im.resize((max(8, size // tile), max(8, size // tile)), Image.BILINEAR)
        arr = np.asarray(base, dtype=np.float32)
        arr = np.tile(arr, (tile, tile, 1))[:size, :size]
        if arr.shape[0] < size or arr.shape[1] < size:
            arr = np.pad(arr, ((0, size - arr.shape[0]), (0, size - arr.shape[1]), (0, 0)), mode="edge")
        return arr
    out = tiled(a) * (1 - mask) + tiled(b) * mask
    im = Image.fromarray(np.clip(out, 0, 255).astype("uint8"), "RGB")
    buf = io.BytesIO(); im.save(buf, "PNG")
    return buf.getvalue()


NORMAL_ROLES = ("NormalGlossAO_TEX", "NormalOcclusionGloss", "NormalAOGloss_TEX", "base_normalspec_texture", "Normal_TEX")
METAL_ROLES = ("Metal_TEX", "Metallic", "SpecularMask_TEX")


def mat_roles(store, mat_path):
    b = store.read(mat_path.lower())
    if b is None:
        return None, []
    try:
        j = json.loads(mat_text(b))
    except Exception:
        return None, []
    roles, parents = {}, []
    for g in j.get("graphinstances", []):
        parents.append(g.get("parent", ""))
        for cp in g.get("custom_parameters", []):
            for p in cp.get("parameters", []):
                if "path" in p and cp.get("name") not in roles:
                    roles[cp["name"]] = p["path"]
    return roles, parents


def _img(store, path, size):
    b = store.read(path.lower())
    if b is None:
        return None
    im = Image.open(io.BytesIO(fix_dds(b))); im.load()
    im = im.convert("RGBA")
    if max(im.size) > size:
        im.thumbnail((size, size))
    return im


def _enc(im, fmt="JPEG", q=88):
    out = io.BytesIO()
    if fmt == "JPEG":
        im.convert("RGB").save(out, "JPEG", quality=q)
        return out.getvalue(), "image/jpeg"
    im.save(out, "PNG")
    return out.getvalue(), "image/png"


_pbr_cache = {}


def pbr_textures(store, mat_path, size=1024):
    """base colour + normal + occlusion/roughness/metal maps for one .mat (packing measured in docs/FORMATS.md 6.1)."""
    key = (mat_path.lower(), size)
    if key in _pbr_cache:
        return _pbr_cache[key]
    import numpy as np
    out = {}
    try:
        roles, parents = mat_roles(store, mat_path)
        if roles is None:
            return out
        info = material(store, mat_path)
        out["alpha"] = info["alpha"] if info else "OPAQUE"
        base = next((roles[r] for r in BASE_ROLES if r in roles), None)
        if base:
            im = _img(store, base, size)
            spec_alpha = "ColourSpecular_TEX" in roles and roles.get("ColourSpecular_TEX") == base   # alpha channel = specular, not coverage
            if spec_alpha or (info and info["alpha"] == "OPAQUE"):
                im.putalpha(255)
            opaque = spec_alpha or (info and info["alpha"] == "OPAQUE")
            if spec_alpha:
                out["alpha"] = "OPAQUE"
            out["base"] = _enc(im, "JPEG" if opaque else "PNG")
        if any("FurV2" in p for p in parents):
            out["fur"] = True
            out["alpha"] = "BLEND"
            return out
        vals, parents2 = mat_values(store, mat_path)
        if "Eye Colour" in vals and not base:
            out["base"] = eye_texture(vals["Eye Colour"])
            out["alpha"] = "OPAQUE"
        if base and "Hair Colour" in vals:
            gray = np.asarray(im, dtype=np.float32)
            g = gray[..., 0:1] / 255.0
            root = np.array(vals["Hair Colour"][:3], dtype=np.float32)
            tip = np.array(vals.get("Hair Tip Colour", vals["Hair Colour"])[:3], dtype=np.float32)
            lashes = "Eyes" in mat_path.rsplit("/", 1)[-1]
            t = np.clip((g - 0.08) * 2.0, 0, 1) * (0.0 if lashes else 0.6)
            rgb = (root * (1 - t) + tip * t) ** (1 / 2.2) * (0.5 if lashes else 1.0)
            both = np.concatenate([np.clip(rgb, 0, 1) * 255, gray[..., 3:4]], -1).astype("uint8")
            out["base"] = _enc(Image.fromarray(both, "RGBA"), "PNG")
        nrole = next((roles[r] for r in NORMAL_ROLES if r in roles), None)
        if nrole:
            im = _img(store, nrole, size)
            a = np.asarray(im, dtype=np.float32) / 255.0
            rg = a[..., :2] * 2 - 1
            z_full = a[..., 2] * 2 - 1
            vec_len = np.sqrt((rg ** 2).sum(-1) + z_full ** 2)
            full_normal = abs(vec_len.mean() - 1.0) < 0.12  # RGB holds a unit normal, A = gloss
            if full_normal:
                n = np.stack([a[..., 0], a[..., 1], a[..., 2]], -1); gloss = a[..., 3]; ao = np.ones_like(gloss)
            else:
                z = np.sqrt(np.clip(1 - (rg ** 2).sum(-1), 0, 1))
                n = np.stack([a[..., 0], a[..., 1], z * 0.5 + 0.5], -1); gloss = a[..., 2]; ao = a[..., 3]
            out["normal"] = _enc(Image.fromarray((np.clip(n, 0, 1) * 255).astype("uint8"), "RGB"))
            metal = np.zeros_like(gloss)
            mrole = next((roles[r] for r in METAL_ROLES if r in roles), None)
            fam = next((p for p in parents if "MetalRough" in p), None)
            if mrole and fam:
                mi = _img(store, mrole, size)
                if mi.size != im.size:
                    mi = mi.resize(im.size)
                metal = np.asarray(mi, dtype=np.float32)[..., 0] / 255.0
            rough = 1.0 - gloss * 0.9
            if any("Skin.fxgraph" in p for p in parents):
                rough = np.maximum(rough, 0.55)
            if any("/Hair.fxgraph" in p for p in parents):
                rough = np.maximum(rough, 0.72)
            rough = np.where(metal < 0.3, np.maximum(rough, 0.45), rough)
            orm = np.stack([ao, rough, metal], -1)
            out["orm"] = _enc(Image.fromarray((np.clip(orm, 0, 1) * 255).astype("uint8"), "RGB"))
    except Exception:
        pass
    out["alpha"] = out.get("alpha", "OPAQUE")
    _pbr_cache[key] = out
    return out


def pbr_for_mesh(store, mesh, size=1024):
    res = {}
    for _n, mat, _s, _c in mesh.parts:
        if mat and mat not in res:
            t = pbr_textures(store, mat, size)
            if t.get("base") or t.get("fur"):
                res[mat] = t
    return res


def mat_values(store, mat_path):
    """name -> first authored value (numbers / colour vectors) of a .mat; plus parent graph names."""
    b = store.read(mat_path.lower())
    if b is None:
        return {}, []
    try:
        j = json.loads(mat_text(b))
    except Exception:
        return {}, []
    vals, parents = {}, []
    for g in j.get("graphinstances", []):
        parents.append(g.get("parent", ""))
        for cp in g.get("custom_parameters", []):
            for p in cp.get("parameters", []):
                if "value" in p and cp.get("name") not in vals:
                    vals[cp["name"]] = p["value"]
    return vals, parents


def _srgb(c):
    return [max(0.0, min(1.0, x)) ** (1 / 2.2) for x in c]


def eye_texture(colour, size=512):
    """Procedural eyeball (the game's Eye.fxgraph has no textures): sclera + iris + pupil, iris centred at uv (0.5, 0.5)."""
    import numpy as np
    ys, xs = np.mgrid[0:size, 0:size].astype("float32") / size
    dx = (xs - 0.5) / 0.15
    dy = (ys - 0.5) / 0.2
    r = np.sqrt(dx * dx + dy * dy)
    iris = np.array(_srgb(colour)) * 1.6 + 0.05
    iris = np.clip(iris, 0, 1)
    sclera = np.array([0.80, 0.75, 0.70])
    img = np.zeros((size, size, 3), dtype="float32") + sclera
    # sclera darkens towards the rim/back of the eyeball
    edge = np.clip(np.sqrt(((xs - 0.5) / 0.5) ** 2 + ((ys - 0.5) / 0.5) ** 2), 0, 1)
    img *= (1.0 - 0.35 * edge ** 2)[..., None]
    ring = np.clip((r - 0.82) / 0.18, 0, 1)
    iris_img = iris[None, None, :] * (1.15 - 0.45 * np.clip(r, 0, 1))[..., None] * (1 - 0.6 * ring)[..., None]
    mask = (r < 1.0)[..., None]
    img = np.where(mask, iris_img, img)
    pupil = (r < 0.4)[..., None]
    img = np.where(pupil, 0.02, img)
    hl = (np.sqrt(((xs - 0.47) / 0.02) ** 2 + ((ys - 0.46) / 0.025) ** 2) < 1)[..., None]
    img = np.where(hl, 0.95, img)
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8"), "RGB")
    out = io.BytesIO(); im.save(out, "JPEG", quality=90)
    return out.getvalue(), "image/jpeg"
