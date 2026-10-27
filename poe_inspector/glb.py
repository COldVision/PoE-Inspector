"""Write a Mesh to binary glTF (.glb). Native (x,y,z) -> glTF (x,-z,y), scaled to metres."""
import json, struct

def to_glb(mesh, scale=0.01, textures=None, extras=None, raw=False):
    textures = textures or {}
    pos = []; nrm = []
    if raw:
        pos = [tuple(p) for p in mesh.pos]; nrm = [tuple(n) for n in mesh.nrm]
    else:
        for x, y, z in mesh.pos: pos.append((x * scale, -z * scale, y * scale))
        for x, y, z in mesh.nrm: nrm.append((x, -z, y))
    have_n = len(nrm) == len(pos); have_uv = len(mesh.uv) == len(pos)
    buf = bytearray(); views = []; acc = []
    def add(blob, target=None):
        while len(buf) % 4: buf.append(0)
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(blob), **({"target": target} if target else {})})
        buf.extend(blob); return len(views) - 1
    mn = [min(p[i] for p in pos) for i in range(3)]; mx = [max(p[i] for p in pos) for i in range(3)]
    flat = [c for p in pos for c in p]
    acc.append({"bufferView": add(struct.pack(f"<{len(flat)}f", *flat), 34962), "componentType": 5126, "count": len(pos), "type": "VEC3", "min": mn, "max": mx})
    attrs = {"POSITION": 0}
    if have_n:
        f = [c for n in nrm for c in n]
        acc.append({"bufferView": add(struct.pack(f"<{len(f)}f", *f), 34962), "componentType": 5126, "count": len(nrm), "type": "VEC3"}); attrs["NORMAL"] = len(acc) - 1
    if have_uv:
        f = [c for u in mesh.uv for c in u]
        acc.append({"bufferView": add(struct.pack(f"<{len(f)}f", *f), 34962), "componentType": 5126, "count": len(mesh.uv), "type": "VEC2"}); attrs["TEXCOORD_0"] = len(acc) - 1
    prims = []; mats = {}; materials = []; images = []; gtex = []
    for name, mat, start, cnt in mesh.parts:
        ids = mesh.idx[start:start + cnt]
        if not ids: continue
        acc.append({"bufferView": add(struct.pack(f"<{len(ids)}I", *ids), 34963), "componentType": 5125, "count": len(ids), "type": "SCALAR"})
        if mat not in mats:
            mats[mat] = len(materials)
            pbr = {"metallicFactor": 0.1, "roughnessFactor": 0.8}
            md = {"name": mat.rsplit("/", 1)[-1] or "default", "pbrMetallicRoughness": pbr, "doubleSided": True}
            if mat in textures:
                png, alpha = textures[mat][:2]
                mime = textures[mat][2] if len(textures[mat]) > 2 else "image/png"
                img = add(png)
                images.append({"bufferView": img, "mimeType": mime})
                gtex.append({"source": len(images) - 1, "sampler": 0})
                pbr["baseColorTexture"] = {"index": len(gtex) - 1}
                pbr["metallicFactor"] = 0.0
                md["alphaMode"] = alpha
                if alpha == "MASK": md["alphaCutoff"] = 0.35
            if extras and mat in extras:
                md["extras"] = extras[mat]
            materials.append(md)
        prims.append({"attributes": attrs, "indices": len(acc) - 1, "mode": 4, "material": mats[mat]})
    g = {"asset": {"version": "2.0", "generator": "PoE Inspector"}, "scene": 0, "scenes": [{"nodes": [0]}],
         "nodes": [{"mesh": 0}], "meshes": [{"primitives": prims}], "materials": materials,
         "accessors": acc, "bufferViews": views, "buffers": [{"byteLength": len(buf)}]}
    if images: g.update({"images": images, "textures": gtex, "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]})
    j = json.dumps(g, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    b = bytes(buf) + b"\0" * (-len(buf) % 4)
    return struct.pack("<III", 0x46546C67, 2, 28 + len(j) + len(b)) + struct.pack("<II", len(j), 0x4E4F534A) + j + struct.pack("<II", len(b), 0x004E4942) + b


def _norm_weights(ws):
    """Some meshes (the cinematic Atziri cloak) store skin weights that sum to less than 255 for a few vertices; the viewer would pull those towards the origin, so rescale to a full sum."""
    out = []
    for w in ws:
        s = sum(w)
        if 0 < s < 250 or s > 260:
            w = tuple(min(255, round(x * 255 / s)) for x in w)
        out.append(w)
    return out


def to_glb_parts(mesh, scale=1.0, textures=None, extras=None, rotate=False, skinned=True):
    """Skinned-part GLB: one node per mesh part (name kept), JOINTS_0/WEIGHTS_0 attributes, no skin object.
    Positions stay in native game space (the client applies the game->glTF transform on the rig root)."""
    textures = textures or {}
    buf = bytearray(); views = []; acc = []
    def add(blob, target=None):
        while len(buf) % 4: buf.append(0)
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(blob), **({"target": target} if target else {})})
        buf.extend(blob); return len(views) - 1
    n = len(mesh.pos)
    flat = [c for p in mesh.pos for c in p]
    mn = [min(p[i] for p in mesh.pos) for i in range(3)]; mx = [max(p[i] for p in mesh.pos) for i in range(3)]
    acc.append({"bufferView": add(struct.pack(f"<{len(flat)}f", *flat), 34962), "componentType": 5126, "count": n, "type": "VEC3", "min": mn, "max": mx})
    attrs = {"POSITION": 0}
    if len(mesh.nrm) == n:
        f = [c for v in mesh.nrm for c in v]
        acc.append({"bufferView": add(struct.pack(f"<{len(f)}f", *f), 34962), "componentType": 5126, "count": n, "type": "VEC3"}); attrs["NORMAL"] = len(acc) - 1
    if len(mesh.uv) == n:
        f = [c for v in mesh.uv for c in v]
        acc.append({"bufferView": add(struct.pack(f"<{len(f)}f", *f), 34962), "componentType": 5126, "count": n, "type": "VEC2"}); attrs["TEXCOORD_0"] = len(acc) - 1
    if skinned and len(mesh.joints) == n:
        f = [c for v in mesh.joints for c in v]
        acc.append({"bufferView": add(struct.pack(f"<{len(f)}B", *f), 34962), "componentType": 5121, "count": n, "type": "VEC4"}); attrs["JOINTS_0"] = len(acc) - 1
        f = [c for v in _norm_weights(mesh.weights) for c in v]
        acc.append({"bufferView": add(struct.pack(f"<{len(f)}B", *f), 34962), "componentType": 5121, "normalized": True, "count": n, "type": "VEC4"}); attrs["WEIGHTS_0"] = len(acc) - 1
    meshes, nodes, materials, images, gtex, mats = [], [], [], [], [], {}
    for name, mat, start, cnt in mesh.parts:
        ids = mesh.idx[start:start + cnt]
        if not ids: continue
        acc.append({"bufferView": add(struct.pack(f"<{len(ids)}I", *ids), 34963), "componentType": 5125, "count": len(ids), "type": "SCALAR"})
        if mat not in mats:
            mats[mat] = len(materials)
            pbr = {"metallicFactor": 0.0, "roughnessFactor": 0.8}
            md = {"name": mat.rsplit("/", 1)[-1] or "default", "pbrMetallicRoughness": pbr, "doubleSided": True}
            tex = textures.get(mat)
            if tex and tex.get("fur"):
                pbr["baseColorFactor"] = [0.045, 0.032, 0.024, 0.5]
                md["alphaMode"] = "BLEND"
                tex = None
            if tex:
                for key, slot in (("base", None), ("normal", "normalTexture"), ("orm", "orm")):
                    if key in tex:
                        png, mime = tex[key]
                        img = add(png); images.append({"bufferView": img, "mimeType": mime}); gtex.append({"source": len(images) - 1, "sampler": 0})
                        ref = {"index": len(gtex) - 1}
                        if key == "base": pbr["baseColorTexture"] = ref
                        elif key == "normal": md["normalTexture"] = ref
                        else:
                            pbr["metallicRoughnessTexture"] = ref; md["occlusionTexture"] = ref
                if "base" in tex: pbr["metallicFactor"] = 1.0 if "orm" in tex else 0.0; pbr["roughnessFactor"] = 1.0 if "orm" in tex else 0.8
                if tex.get("alpha") == "MASK": md["alphaMode"] = "MASK"; md["alphaCutoff"] = 0.35
            if extras and mat in extras: md["extras"] = extras[mat]
            materials.append(md)
        meshes.append({"name": name, "primitives": [{"attributes": attrs, "indices": len(acc) - 1, "mode": 4, "material": mats[mat]}]})
        nodes.append({"name": name, "mesh": len(meshes) - 1})
    g = {"asset": {"version": "2.0", "generator": "PoE Inspector"}, "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}],
         "nodes": nodes, "meshes": meshes, "materials": materials, "accessors": acc, "bufferViews": views, "buffers": [{"byteLength": len(buf)}]}
    if images: g.update({"images": images, "textures": gtex, "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]})
    j = json.dumps(g, separators=(",", ":")).encode(); j += b" " * (-len(j) % 4)
    b = bytes(buf) + b"\0" * (-len(buf) % 4)
    return struct.pack("<III", 0x46546C67, 2, 28 + len(j) + len(b)) + struct.pack("<II", len(j), 0x4E4F534A) + j + struct.pack("<II", len(b), 0x004E4942) + b
