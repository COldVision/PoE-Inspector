"""Parsers for PoE2 .smd (skinned mesh v3) and .fmt (fixed mesh v9): LOD0 geometry only."""
import struct

class Mesh:
    def __init__(self):
        self.parts = []      # (name, material, indexStart, indexCount)
        self.pos = []; self.nrm = []; self.uv = []; self.idx = []; self.joints = []; self.weights = []; self.uv2 = []
        self.bbox = None; self.kind = ""; self.vformat = 0; self.lods = 0

def _stride(fmt):
    s = 0
    for bit, n in ((0x20, 12), (0x10, 8), (0x08, 4), (0x04, 8), (0x40, 4), (0x02, 4), (0x01, 4)):
        if fmt & bit: s += n
    return s

def _dolm(d, p, m, count=None):
    if d[p:p + 4] != b"DOLm": raise ValueError("DOLm marker not found")
    p += 4
    layout, _z, lods, nmesh, _z2, fmt = struct.unpack_from("<BBBBBI", d, p); p += 9
    if count is not None: nmesh = count
    lodinfo = list(struct.iter_unpack("<II", d[p:p + 8 * lods])); p += 8 * lods
    m.vformat, m.lods = fmt, lods
    stride = _stride(fmt)
    first = None
    for li, (tri, nv) in enumerate(lodinfo):
        ranges = list(struct.iter_unpack("<II", d[p:p + 8 * nmesh])); p += 8 * nmesh
        isz = 4 if nv > 65535 else 2
        ib = d[p:p + tri * 3 * isz]; p += tri * 3 * isz
        vb = d[p:p + nv * stride]; p += nv * stride
        if li == 0: first = (ranges, ib, isz, vb, nv)
    if layout >= 4: p += 4
    if first is None: return p, nmesh, []
    ranges, ib, isz, vb, nv = first
    m.idx = list(struct.unpack(f"<{len(ib)//isz}{'I' if isz == 4 else 'H'}", ib))
    off = {}; o = 0
    for bit, n, key in ((0x20, 12, "p"), (0x10, 8, "n"), (0x08, 4, "u"), (0x04, 8, "b"), (0x40, 4, "x"), (0x02, 4, "c"), (0x01, 4, "u2")):
        if fmt & bit: off[key] = o; o += n
    for i in range(nv):
        b = i * stride
        if "p" in off: m.pos.append(struct.unpack_from("<3f", vb, b + off["p"]))
        if "n" in off:
            x, y, z = struct.unpack_from("<3b", vb, b + off["n"]); m.nrm.append((x / 127, y / 127, z / 127))
        if "u" in off:
            m.uv.append(struct.unpack_from("<2e", vb, b + off["u"]))
        if "b" in off:
            m.joints.append(struct.unpack_from("<4B", vb, b + off["b"]))
            m.weights.append(struct.unpack_from("<4B", vb, b + off["b"] + 4))
    return p, nmesh, ranges

def parse_smd_legacy(d):
    """smd v1/v2 (docs 3.5): u8 ver; u32 tris; u32 verts; u8 b9; u8 meshes; u8 b11; u32 nameBytes; f32 bbox[6]; [v2: u32]; {u32 nameBytes; u32 triStart}[meshes];
    utf16 names; u16 indices; 32-byte vertices (flags 0x3c, biased normals)."""
    m = Mesh(); m.kind = "smd"
    ver = d[0]
    tri, nv = struct.unpack_from("<II", d, 1); mc = d[10]
    name_total = struct.unpack_from("<I", d, 12)[0]
    m.bbox = struct.unpack_from("<6f", d, 16)
    p = 40 + (4 if ver == 2 else 0)
    table = [struct.unpack_from("<II", d, p + 8 * i) for i in range(mc)]; p += 8 * mc
    names, q = [], p
    for nb, _t in table:
        names.append(d[q:q + nb].decode("utf-16-le", "replace").rstrip(chr(0))); q += nb
    p += name_total
    m.idx = list(struct.unpack_from(f"<{tri * 3}H", d, p)); p += tri * 6
    m.vformat, m.lods = 0x3c, 1
    for i in range(nv):
        b = p + i * 32
        m.pos.append(struct.unpack_from("<3f", d, b))
        nx, ny, nz = struct.unpack_from("<3B", d, b + 12); m.nrm.append(((nx - 128) / 127, (ny - 128) / 127, (nz - 128) / 127))
        m.uv.append(struct.unpack_from("<2e", d, b + 20))
        m.joints.append(struct.unpack_from("<4B", d, b + 24)); m.weights.append(struct.unpack_from("<4B", d, b + 28))
    starts = [t for _n, t in table] + [tri]
    m.parts = [(names[i] or f"mesh{i}", "", starts[i] * 3, (starts[i + 1] - starts[i]) * 3) for i in range(mc)]
    return m


def parse_smd(d):
    m = Mesh(); m.kind = "smd"
    ver = d[0]
    if ver in (1, 2): return parse_smd_legacy(d)
    if ver != 3: raise ValueError(f"smd version {ver} not supported (only v1-v3)")
    nm = struct.unpack_from("<H", d, 2)[0]
    m.bbox = struct.unpack_from("<6f", d, 8)
    p, nmesh, ranges = _dolm(d, 0x20, m)
    nb = struct.unpack_from(f"<{nmesh}I", d, p); p += 4 * nmesh
    names = []
    for n in nb:
        names.append(d[p:p + n].decode("utf-16-le", "replace")); p += n
    m.parts = [(names[i] if i < len(names) else f"mesh{i}", "", ranges[i][0], ranges[i][1]) for i in range(len(ranges))]
    return m

def parse_fmt_legacy(d):
    """fmt v4-v8: u8 ver; u32 tris; u32 verts; u8 meshes; f32 bbox[6] at 15; {u32 nameStart; u32 matOffset; u32 triStart}[meshes] at 39; [u32]; u16/u32 indices;
    24-byte vertices (pos f32x3, normal s8x3+pad, tangent 4, uv f16x2); utf16 text (names + .mat paths, offsets in chars)."""
    m = Mesh(); m.kind = "fmt"
    tris, nv = struct.unpack_from("<II", d, 1); mc = d[9]
    if len(d) < 60 or mc == 0 or tris == 0: raise ValueError("empty legacy fmt")
    m.bbox = struct.unpack_from("<6f", d, 15)
    isz = 4 if nv > 65535 else 2
    for base, extra in ((39, 4), (39, 0), (43, 0), (43, 4), (39, 8), (39, 12)):
        ent = [struct.unpack_from("<3I", d, base + 12 * i) for i in range(mc)]
        io = base + 12 * mc + extra; vo = io + tris * 3 * isz; to = vo + nv * 24
        if to > len(d): continue
        try: text = d[to:].decode("utf-16-le")
        except UnicodeDecodeError: continue
        if all(e[0] == 0 or text[e[0] - 1:e[0]] == "\0" for e in ent) and ent[0][0] == 0 and text.endswith("\0"): break
    else:
        raise ValueError(f"fmt version {d[0]}: layout not recognised")
    m.idx = list(struct.unpack_from(f"<{tris * 3}{'I' if isz == 4 else 'H'}", d, io))
    for i in range(nv):
        b = vo + 24 * i
        m.pos.append(struct.unpack_from("<3f", d, b))
        x, y, z = struct.unpack_from("<3b", d, b + 12); m.nrm.append((x / 127, y / 127, z / 127))
        m.uv.append(struct.unpack_from("<2e", d, b + 20))
    starts = [e[2] for e in ent] + [tris]
    parts = []
    for i, e in enumerate(ent):
        name = text[e[0]:].split("\0", 1)[0]
        mat = text[e[1]:].split("\0", 1)[0] if e[1] < len(text) else ""
        n = max(0, starts[i + 1] - starts[i]) * 3
        if n: parts.append((name or f"mesh{i}", mat if mat.lower().endswith(".mat") else "", starts[i] * 3, n))
    m.parts, m.vformat, m.lods = parts, 0x2b, 1
    return m


def parse_fmt(d):
    m = Mesh(); m.kind = "fmt"
    ver = d[0]
    if ver in (4, 5, 6, 7, 8): return parse_fmt_legacy(d)
    if ver != 9: raise ValueError(f"fmt version {ver} not supported")
    nmesh, lg, lp, extra = struct.unpack_from("<HBHB", d, 1)
    m.bbox = struct.unpack_from("<6f", d, 7)
    p, nmesh, ranges = _dolm(d, 0x1f, m)
    names, mats = [f"mesh{i}" for i in range(nmesh)], [""] * nmesh
    try:
        if m.vformat & 0x40: p += 36
        p += 4
        mat_offs, ends, q = [], [], p
        for i in range(nmesh):
            mat_offs.append(struct.unpack_from("<I", d, q)[0]); q += 4
            if i == nmesh - 1 and lg:
                q += 6 * lg + 12 * lp
            ends.append(struct.unpack_from("<I", d, q)[0]); q += 4
        text = d[q:q + ends[-1] * 2].decode("utf-16-le")
        prev = 0
        for i in range(nmesh):
            region = text[prev:ends[i]]; prev = ends[i]
            parts = region.split("\0")
            names[i] = parts[0] or names[i]
            if len(parts) > 1 and parts[1]: mats[i] = parts[1]
            elif mat_offs[i] < len(text):   # no material next to the name: the mesh shares one stored earlier, pointed to by offset
                s = text[mat_offs[i]:].split("\0", 1)[0]
                if s.lower().endswith(".mat"): mats[i] = s
    except Exception:
        pass
    m.parts = [(names[i], mats[i], ranges[i][0], ranges[i][1]) for i in range(len(ranges))]
    return m

def parse(path, data):
    return parse_smd(data) if path.endswith(".smd") else parse_fmt(data)
