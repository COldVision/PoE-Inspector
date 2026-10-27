"""Named-column row access for .datc64 tables (schema.min.json)."""
import struct, os
from .dat import Dat, NULL
from . import tables

from .paths import DATA as ROOT, SCHEMA   # ROOT = writable data dir (caches); SCHEMA = shipped with the app
ESIZE = {"string": 8, "foreignrow": 16, "row": 8, "i32": 4, "u32": 4, "f32": 4, "enumrow": 4, "bool": 1, "i16": 2, "u16": 2, "i64": 8, "u64": 8, "u8": 1, "i8": 1, "f64": 8, "array": 16}
_cache = {}


class Table:
    def __init__(self, store, name, lang=None):
        path = f"data/balance/{lang + '/' if lang else ''}{name}.datc64"
        b = store.read(path)
        if b is None:
            raise KeyError(path)
        self.d = Dat(b); self.name = name
        sc = tables.load_schema(SCHEMA).get(name.lower())
        cols = tables.cols_from_schema(sc, self.d.width) if sc else None
        if cols is None and sc:
            # the community schema lags behind the game: Mods.StatNValue became a (min, max) pair
            import re as _re
            wide = []
            for c in sc:
                if c.get("name") and _re.fullmatch(r"Stat\d+Value", c["name"]) and not c.get("array"):
                    wide += [dict(c, name=c["name"][:-5] + "Min"), dict(c, name=c["name"][:-5] + "Max")]
                else:
                    wide.append(c)
            cols = tables.cols_from_schema(wide, self.d.width)
        if cols is None:
            raise ValueError(f"{name}: schema mismatch")
        self.cols = cols
        self.idx = {}
        for c in cols:
            self.idx.setdefault(c[0], c)

    def _arr(self, i, col):
        _n, t, _a, off, _s = col
        d = self.d
        n, ref = struct.unpack_from("<QQ", d.data, 4 + i * d.width + off)
        if n == 0 or n > 100000 or ref >= len(d.data) - d.boundary:
            return []
        es = ESIZE.get(t, 8); p = d.boundary + ref; out = []
        for k in range(n):
            o = p + k * es
            if t == "string":
                out.append(d.string_at(struct.unpack_from("<Q", d.data, o)[0]))
            elif t in ("foreignrow", "row"):
                v = struct.unpack_from("<Q", d.data, o)[0]; out.append(None if v == NULL else v)
            elif t == "f32": out.append(struct.unpack_from("<f", d.data, o)[0])
            elif t in ("i32",): out.append(struct.unpack_from("<i", d.data, o)[0])
            elif t in ("u32", "enumrow"): out.append(struct.unpack_from("<I", d.data, o)[0])
            elif t == "bool": out.append(bool(d.data[o]))
            else: out.append(None)
        return out

    def get(self, i, name):
        c = self.idx[name]
        return self._arr(i, c) if c[2] else tables.cell(self.d, i, c)

    def row(self, i):
        return {c[0]: (self._arr(i, c) if c[2] else tables.cell(self.d, i, c)) for c in self.cols if not c[0].startswith("unk")}

    def __len__(self): return self.d.rows


def table(store, name, lang=None):
    k = (name, lang)
    if k not in _cache:
        _cache[k] = Table(store, name, lang)
    return _cache[k]
