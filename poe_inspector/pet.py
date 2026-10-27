"""Parser for .pet particle effect files (text format, measured from the campfire effect)."""
import re, shlex
from .catalog import text
from . import textures

GRAPHS = {"stretch", "up_acceleration_graph", "emit_scale", "scatter_cone_size", "particles_per_second", "emit_colour",
          "velocity_along", "velocity_up", "scale", "rotation_speed", "colour"}


def _graph(tokens):
    comps, n = int(tokens[0]), int(tokens[1])
    keys, p = [], 2
    for _ in range(n):
        t = float(tokens[p]); p += 1
        v = [float(x) for x in tokens[p:p + comps]]; p += comps
        interp = tokens[p].strip('"'); p += 1
        keys.append({"t": t, "v": v, "i": interp})
    return keys


def _parse_json(txt):
    """version 5 files: a JSON object with gpu_emitters; approximated as sprite emitters."""
    import json
    try:
        j = json.loads(txt[txt.index("{"):] if txt.lstrip().startswith("version") else txt)
    except Exception:
        i = txt.find("{")
        try:
            j = json.loads(txt[i:])
        except Exception:
            return []
    out = []
    for g in j.get("gpu_emitters", []) + j.get("emitters", []):
        mats = [r.get("render_material") for r in g.get("render_passes", []) if r.get("render_material")]
        mat = mats[0] if mats else g.get("update_material")
        if not mat:
            continue
        life = max(0.3, float(g.get("particle_duration_max") or g.get("particle_duration_min") or 1.0))
        burst = float(g.get("emit_burst") or 20)
        pps = min(60.0, max(4.0, burst / life))
        face = (g.get("render_passes") or [{}])[0].get("face_lock") or "None"
        out.append({"type": "gpu", "mat": mat, "mesh": g.get("particle_mesh") or "", "face_lock": face, "particle_duration": life, "blend_mode": "Additive", "face_type": "FaceCamera",
                    "rotation_lock_type": "Random", "emit_colour": [{"t": 0, "v": [1, 1, 1, 1], "i": "Flat"}],
                    "particles_per_second": [{"t": 0, "v": [pps], "i": "Flat"}],
                    "scale": [{"t": 0, "v": [40], "i": "Smooth"}, {"t": 1, "v": [12], "i": "Flat"}],
                    "colour": [{"t": 0, "v": [1, 1, 1, 0], "i": "Smooth"}, {"t": .2, "v": [1, 1, 1, .8], "i": "Smooth"}, {"t": 1, "v": [1, 1, 1, 0], "i": "Flat"}],
                    "velocity_up": [{"t": 0, "v": [18], "i": "Flat"}],
                    "scatter_cone_size": [{"t": 0, "v": [1.2], "i": "Flat"}],
                    "velocity_along": [{"t": 0, "v": [6], "i": "Flat"}],
                    "particle_duration_variance": 0.3, "scale_variance": 2})
    return out


def parse(txt):
    if '"gpu_emitters"' in txt or '"emitters"' in txt[:400]:
        return _parse_json(txt)
    emitters = []
    for block in re.findall(r"\{(.*?)\n\}", txt, re.S):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        e = {"type": lines[0], "mat": lines[1].strip('"')}
        for l in lines[2:]:
            try:
                tok = shlex.split(l, posix=True)
            except ValueError:
                continue
            if not tok:
                continue
            k, rest = tok[0], tok[1:]
            try:
                if k in GRAPHS:
                    e[k] = _graph(rest)
                elif len(rest) == 1:
                    try:
                        e[k] = float(rest[0])
                    except ValueError:
                        e[k] = rest[0]
                elif rest:
                    e[k] = rest
            except Exception:
                pass
        emitters.append(e)
    return emitters


def first_texture(store, mat):
    b = store.read(mat.lower())
    if b is None:
        return None
    import json
    try:
        j = json.loads(textures.mat_text(b))
    except Exception:
        return None
    for g in j.get("graphinstances", []):
        for cp in g.get("custom_parameters", []):
            if cp.get("name") in textures.BASE_ROLES or "tex" in cp.get("name", "").lower() or "colour" in cp.get("name", "").lower():
                for p in cp.get("parameters", []):
                    if "path" in p:
                        return p["path"]
    for t in j.get("textures", []):
        if t.get("filename"):
            return t["filename"]
    return None


def mat_params(store, mat):
    """Tint / HDR intensity / luminance-alpha range authored in a particle material."""
    import json
    out = {"tint": [1, 1, 1], "intensity": 1.0, "luma": None}
    b = store.read(mat.lower())
    if b is None:
        return out
    try:
        j = json.loads(textures.mat_text(b))
    except Exception:
        return out
    vals = {}
    parents = []
    for g in j.get("graphinstances", []):
        parents.append(g.get("parent", ""))
        for cp in g.get("custom_parameters", []):
            vals[cp.get("name", "")] = [p.get("value") for p in cp.get("parameters", []) if "value" in p]
    for k in ("Col_RGB_Mult", "- Hue", "- RGB Channel Boost"):
        v = vals.get(k)
        if v and isinstance(v[0], list) and len(v[0]) >= 3:
            out["tint"] = v[0][:3]
            break
    for k in ("- Intensity", "Multiplier"):
        v = vals.get(k)
        if v and isinstance(v[0], (int, float)):
            out["intensity"] = float(v[0])
            break
    if any("LuminanceAlphaSmoothStep" in p for p in parents):
        v = vals.get("05. Map SmoothStep")
        if v and isinstance(v[0], list):
            out["luma"] = v[0][:2]
        else:
            r = vals.get("- Range")
            out["luma"] = [0.3, 0.6] if not r else [max(0.0, r[0] - 0.25), min(1.0, r[0] + 0.25)]
    return out


def load(store, path):
    em = parse(text(store, path.lower()))
    for e in em:
        e["tex"] = first_texture(store, e["mat"])
        e["matp"] = mat_params(store, e["mat"])
        if e.get("type") == "gpu":
            e["matp"]["luma"] = [0.15, 0.6]; e["matp"]["intensity"] = max(e["matp"]["intensity"], 2.0)
    return em
