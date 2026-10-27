"""Parse _.index.bin into SQLite: bundles + files (with generated paths)."""
import os, sqlite3, struct, sys, time
from . import bundle

M = 0xFFFFFFFFFFFFFFFF
MUL = 0xC6A4A7935BD1E995


def murmur64a(b: bytes, seed=0x1337B33F) -> int:
    h = (seed ^ (len(b) * MUL)) & M
    n8 = len(b) // 8
    for k, in struct.iter_unpack("<Q", b[:n8 * 8]):
        k = (k * MUL) & M; k ^= k >> 47; k = (k * MUL) & M
        h ^= k; h = (h * MUL) & M
    rem = b[n8 * 8:]
    if rem:
        h ^= int.from_bytes(rem, "little"); h = (h * MUL) & M
    h ^= h >> 47; h = (h * MUL) & M; h ^= h >> 47
    return h


def gen_paths(spec: bytes, off: int, size: int):
    out, base, base_phase = [], [], False
    p, end = off, off + size
    while p <= end - 4:
        idx = int.from_bytes(spec[p:p + 4], "little"); p += 4
        if idx == 0:
            base_phase = not base_phase
            if base_phase: base = []
            continue
        z = spec.index(b"\0", p); s = spec[p:z].decode("utf-8"); p = z + 1
        if idx - 1 < len(base): s = base[idx - 1] + s
        (base if base_phase else out).append(s)
    return out


def build(game_dir: str, db_path: str, log=print):
    t0 = time.time()
    b2 = os.path.join(game_dir, "Bundles2")
    raw = bundle.unpack(open(os.path.join(b2, "_.index.bin"), "rb").read())
    pos = 0
    n = struct.unpack_from("<I", raw, pos)[0]; pos += 4
    bundles = []
    for _ in range(n):
        l = struct.unpack_from("<I", raw, pos)[0]; pos += 4
        name = raw[pos:pos + l].decode(); pos += l
        usz = struct.unpack_from("<I", raw, pos)[0]; pos += 4
        bundles.append((name, usz))
    fc = struct.unpack_from("<I", raw, pos)[0]; pos += 4
    recs = list(struct.iter_unpack("<QIII", raw[pos:pos + fc * 20])); pos += fc * 20
    dc = struct.unpack_from("<I", raw, pos)[0]; pos += 4
    dirs = list(struct.iter_unpack("<QIII", raw[pos:pos + dc * 20])); pos += dc * 20
    spec = bundle.unpack(raw[pos:])
    log(f"bundles={n} files={fc} dirs={dc} spec={len(spec)} ({time.time()-t0:.1f}s)")
    byhash = {r[0]: r for r in recs}
    rows = []
    matched = set()
    for _h, so, ss, _rs in dirs:
        for path in gen_paths(spec, so, ss):
            h = murmur64a(path.lower().encode())
            r = byhash.get(h)
            if r is not None:
                rows.append((path.lower(), r[1], r[2], r[3])); matched.add(h)
    log(f"paths matched={len(rows)} of {fc} ({time.time()-t0:.1f}s)")
    if os.path.exists(db_path): os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.executescript("""
      CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
      CREATE TABLE bundles(id INTEGER PRIMARY KEY, name TEXT, usize INTEGER);
      CREATE TABLE files(path TEXT PRIMARY KEY, bundle INTEGER, offset INTEGER, size INTEGER, ext TEXT) WITHOUT ROWID;
    """)
    db.executemany("INSERT INTO bundles VALUES(?,?,?)", [(i, a, b) for i, (a, b) in enumerate(bundles)])
    db.executemany("INSERT OR IGNORE INTO files VALUES(?,?,?,?,?)",
                   [(p, b, o, s, os.path.splitext(p)[1][1:]) for p, b, o, s in rows])
    db.execute("CREATE INDEX files_ext ON files(ext)")
    db.execute("INSERT INTO meta VALUES('game_dir',?)", (game_dir,))
    db.commit(); db.close()
    log(f"done ({time.time()-t0:.1f}s)")
