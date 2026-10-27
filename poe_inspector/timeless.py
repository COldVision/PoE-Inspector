"""Timeless jewel data: AlternateTreeVersions / AlternatePassiveSkills / AlternatePassiveAdditions decoded by hand
(the community schema lags behind the game, so the columns are read at fixed offsets found by inspection)."""
import struct
from .dat import Dat, NULL
from .datrows import table


def _fk_rows(d, i, off):
    n, ref = struct.unpack_from("<QQ", d.data, 4 + i * d.width + off)
    if n == 0 or n > 1000 or ref >= len(d.data) - d.boundary:
        return []
    p = d.boundary + ref
    return [struct.unpack_from("<Q", d.data, p + k * 16)[0] for k in range(n)]


def _i32_arr(d, i, off):
    n, ref = struct.unpack_from("<QQ", d.data, 4 + i * d.width + off)
    if n == 0 or n > 1000 or ref >= len(d.data) - d.boundary:
        return []
    p = d.boundary + ref
    return list(struct.unpack_from("<" + "i" * n, d.data, p))


def _dat(store, name):
    return Dat(store.read(f"data/balance/{name}.datc64"))


def load(store):
    st = table(store, "stats")
    v = _dat(store, "AlternateTreeVersions")
    versions = []
    for i in range(v.rows):
        ints = [v.i32(i, o) for o in range(10, 38, 4)]
        versions.append({"id": v.str(i, 0), "attr_replaced": bool(v.u8(i, 8)), "normal_replaced": bool(v.u8(i, 9)),
                         "attr_add": ints[0:2], "notable_add": ints[2:4], "normal_add": ints[4:6], "notable_replace_weight": ints[6]})
    s = _dat(store, "AlternatePassiveSkills")
    skills = []
    for i in range(s.rows):
        stats = [st.get(r, "Id") for r in _fk_rows(s, i, 48)]
        rng = [(s.i32(i, 64 + 8 * k), s.i32(i, 68 + 8 * k)) for k in range(len(stats))]
        skills.append({"id": s.str(i, 0), "ver": s.i32(i, 8), "name": s.str(i, 24), "types": _i32_arr(s, i, 32), "stats": stats, "ranges": rng,
                       "weight": s.i32(i, 112), "conqueror": s.i32(i, 116), "random": [s.i32(i, 120), s.i32(i, 124)],
                       "flavour": s.str(i, 128), "icon": s.str(i, 136), "cver": s.i32(i, 160), "cweight": s.i32(i, 164)})
    a = _dat(store, "AlternatePassiveAdditions")
    adds = []
    for i in range(a.rows):
        stats = [st.get(r, "Id") for r in _fk_rows(a, i, 28)]
        rng = [(a.i32(i, 44 + 8 * k), a.i32(i, 48 + 8 * k)) for k in range(len(stats))]
        adds.append({"id": a.str(i, 0), "ver": a.i32(i, 8), "weight": a.i32(i, 24), "stats": stats, "ranges": rng, "types": _i32_arr(a, i, 68)})
    return {"versions": versions, "skills": skills, "adds": adds}


# ---- RNG: the game's mirrored TinyMT32 variant (read from PathOfExileSteam.exe: init at 0x14184c440, generator at 0x14184cb30),
# seeded with key [node id, jewel seed] by a trimmed init_by_array (no initial pre-step, 7 mixing rounds, 4 finishing rounds, 8 idle steps)
M32 = 0xFFFFFFFF
MAT1, MAT2, TMAT = 0x8F7011EE, 0xFC78FF1F, 0x3793FDFF
START = (0x40336050, 0xCFA3723C, 0x3CAC5F6F, 0x3793FDFF)


def _f1(x): return ((x ^ (x >> 27)) * 0x19660D) & M32
def _f2(x): return ((x ^ (x >> 27)) * 0x5D588B65) & M32


class TinyMT:
    def __init__(self, key):
        s = list(START); i = 1
        for j in range(7):
            r = _f1(s[i % 4] ^ s[(i + 1) % 4] ^ s[(i + 3) % 4]); s[(i + 1) % 4] = (s[(i + 1) % 4] + r) & M32
            r = (r + (key[j] if j < len(key) else 0) + i) & M32 if j < len(key) else (r + i) & M32
            s[(i + 2) % 4] = (s[(i + 2) % 4] + r) & M32; s[i % 4] = r; i = (i + 1) % 4
        for _ in range(4):
            r = _f2((s[i % 4] + s[(i + 1) % 4] + s[(i + 3) % 4]) & M32); s[(i + 1) % 4] ^= r
            r = (r - i) & M32; s[(i + 2) % 4] ^= r; s[i % 4] = r; i = (i + 1) % 4
        self.s = s
        for _ in range(8):
            self._step()

    def _step(self):
        s = self.s; x = ((s[0] & 0x7FFFFFFF) ^ s[1] ^ s[2]) & M32
        y1 = (s[3] ^ (s[3] << 1)) & M32; y = (x ^ (x >> 1) ^ y1) & M32; m = -(y & 1) & M32
        s[0], s[1], s[2], s[3] = s[1], s[2] ^ (m & MAT1), (y1 ^ (y << 10) ^ (m & MAT2)) & M32, y

    def next(self):
        self._step(); s = self.s
        t1 = (s[0] + (s[2] >> 8)) & M32; t0 = s[3] ^ t1
        if t1 & 1:
            t0 ^= TMAT
        return t0 & M32

    def below(self, n):   # unbiased value in [0, n): multiply-shift with rejection, as the game's bounded generator does
        r = self.next() * n
        if (r & M32) < n:
            thr = ((1 << 32) - n) % n
            while (r & M32) < thr:
                r = self.next() * n
        return r >> 32

    def gen(self, lo, hi): return lo + self.below(hi - lo + 1)
    def single(self, hi): return self.below(hi)
    def signed(self, lo, hi): return lo + self.below(hi - lo + 1)


# ---- replacement of one node.  kind: 1 small attribute, 2 small normal, 3 notable, 4 keystone
# Assumed order of rolls (PoE1 algorithm; to be confirmed with in-game examples):
#   notable: [replace roll gen(0,100) < weight unless weight is 0/100] -> one empty roll -> per candidate single(acc weight), last pass wins
#   then stat rolls for the chosen passive, then additions (count gen(min,max), each picked by weight)
def replace(data, ver, lord, seed, node_id, kind):
    v = data["versions"][ver]
    skills = [s for s in data["skills"] if s["ver"] == ver]
    if kind == 4:   # keystones are always swapped for the lord's own
        c = [s for s in skills if 4 in s["types"] and s["conqueror"] == lord and s["cweight"] > 0]
        return {"skill": c[0] if c else None, "values": [], "adds": []}
    rng = TinyMT([node_id, seed])
    replaced = {1: v["attr_replaced"], 2: v["normal_replaced"]}.get(kind)
    if kind == 3:
        w = v["notable_replace_weight"]
        replaced = w >= 100 or (w > 0 and rng.gen(0, 100) < w)
    out = {"skill": None, "values": [], "adds": []}
    if replaced:
        cand = [s for s in skills if kind in s["types"] and s["weight"] > 0 and s["cweight"] > 0]
        if kind == 3:
            rng.next()   # empty roll
        acc, pick = 0, None
        for s in cand:
            acc += s["weight"]
            if rng.single(acc) < s["weight"]:
                pick = s
        out["skill"] = pick
        if pick:
            out["values"] = [lo if lo == hi else rng.signed(lo, hi) for lo, hi in pick["ranges"]]
    lo, hi = {1: v["attr_add"], 2: v["normal_add"], 3: v["notable_add"]}[kind]
    n = rng.gen(lo, hi) if hi > lo else lo
    pool = [a for a in data["adds"] if a["ver"] == ver and kind in a["types"]]
    for _ in range(n):
        if not pool:
            break
        tot = sum(a["weight"] for a in pool); r = rng.single(tot) if tot else 0; acc = 0
        for a in pool:
            acc += a["weight"]
            if r < acc:
                out["adds"].append({"add": a, "values": [l if l == h else rng.signed(l, h) for l, h in a["ranges"]]}); break
    return out


# lord -> ConquerorIndex of its keystone (poe_inspector changelog 0.2.0: Olroth = Knightly Tenets, Medved = Circular Teachings, Vorana = Black Scythe Training;
# jewels made before that patch keep the old, mismatched keystone)
LORDS = {"Heroic Tragedy": {"Vorana": 1, "Medved": 2, "Olroth": 3}}
