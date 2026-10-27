"""Table viewer: optional dat-schema (schema.min.json) for names/types, heuristic fallback otherwise."""
import json, os, struct
from .dat import Dat, NULL

SIZES = {"bool": 1, "i8": 1, "u8": 1, "i16": 2, "u16": 2, "i32": 4, "u32": 4, "f32": 4, "enumrow": 4,
         "string": 8, "array": 16, "row": 8, "i64": 8, "u64": 8, "f64": 8, "foreignrow": 16}
FMT = {"i8": "<b", "u8": "<B", "i16": "<h", "u16": "<H", "i32": "<i", "u32": "<I", "f32": "<f",
       "enumrow": "<I", "i64": "<q", "u64": "<Q", "f64": "<d"}

_schema = None


def load_schema(path):
    global _schema
    if _schema is None:
        _schema = {}
        if os.path.exists(path):
            j = json.load(open(path, encoding="utf-8"))
            for t in j.get("tables", []):
                if t.get("validFor", 3) & 2:  # 2 = PoE 2
                    _schema[t["name"].lower()] = t["columns"]
    return _schema


def cols_from_schema(cols, width):
    out, off = [], 0
    for i, c in enumerate(cols):
        t, arr = c["type"], c.get("array")
        size = 16 if arr else SIZES.get(t, 0)
        out.append((c.get("name") or f"unk{i}", t, bool(arr), off, size))
        off += size
    return out if off == width else None


def guess_columns(d: Dat):
    """Find tightly packed string refs by testing every byte offset on a sample of rows."""
    if not d.rows:
        return []
    n = min(d.rows, 200)
    out = []
    o = 0
    while o <= d.width - 8:
        ok = tot = 0
        for i in range(n):
            v = d.u64(i, o)
            if v == NULL or v == 0:
                continue
            tot += 1
            s = None
            if v % 2 == 0 and v < 1 << 28 and v + d.boundary + 2 <= len(d.data):
                p = d.boundary + v
                # a real string starts right after the previous string's terminator (or at heap start)
                if v == 8 or d.data[p - 2:p] == b"\0\0":
                    s = d.string_at(v)
            if s and s.isprintable():
                ok += 1
        if tot >= max(3, n // 10) and ok >= tot * 0.9:
            out.append((f"str@{o}", "string", False, o, 8))
            o += 8
        else:
            o += 1
    return out


def describe(d: Dat, name, schema_path):
    sc = load_schema(schema_path).get(name.lower())
    cols = cols_from_schema(sc, d.width) if sc else None
    schema_used = cols is not None
    if cols is None:
        cols = guess_columns(d)
    return cols, schema_used


def cell(d: Dat, i, col):
    _n, t, arr, off, size = col
    try:
        if arr:
            cnt = d.u64(i, off)
            return f"[{cnt}]" if cnt else "[]"
        if t == "string":
            return d.str(i, off)
        if t == "bool":
            return bool(d.u8(i, off))
        if t in ("row", "foreignrow"):
            v = d.u64(i, off)
            return None if v == NULL else v
        if t in FMT:
            return struct.unpack_from(FMT[t], d.data, 4 + i * d.width + off)[0]
    except Exception:
        return None
    return None
