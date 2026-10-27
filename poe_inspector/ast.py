"""Skeleton + animation clip reader for .ast (versions 11/12, layout per docs/FORMATS.md section 8)."""
import struct
from . import bundle

_cache = {}


class Ast:
    def __init__(self, data: bytes):
        d = data
        self.version, nb, _b2, na = d[0], d[1], d[2], d[3] | (d[4] << 8)
        nl = d[7]
        p = 8
        self.bones = []
        for _ in range(nb):
            sib, ch = d[p], d[p + 1]
            m = struct.unpack_from("<16f", d, p + 2)
            nlen = d[p + 66]
            name = d[p + 68:p + 68 + nlen].decode("latin-1")
            self.bones.append({"name": name, "sib": sib, "child": ch, "m": m, "parent": -1})
            p += 68 + nlen
        # parents from child/sibling links
        for i, b in enumerate(self.bones):
            c = b["child"]
            while c != 255 and c < nb:
                self.bones[c]["parent"] = i
                c = self.bones[c]["sib"]
        for _ in range(nl):
            nlen = d[p]
            p += 2 + 48 + 4 + 4 + 2 + nlen
        self.clips = []
        for _ in range(na):
            bc = struct.unpack_from("<H", d, p)[0]
            fps, flags = d[p + 2], d[p + 3]
            nlen, plen = d[p + 5], d[p + 6]
            off, size = struct.unpack_from("<II", d, p + 7)
            p += 15
            name = d[p:p + nlen].decode("latin-1")
            p += nlen
            parent = d[p:p + plen].decode("latin-1")
            p += plen
            self.clips.append({"name": name, "fps": fps, "off": off, "size": size, "parent": parent})
        self._tail = d[p:]
        self._raw = None

    def raw(self):
        if self._raw is None:
            self._raw = bundle.unpack(self._tail) if self._tail else b""
        return self._raw

    def clip_tracks(self, name):
        c = next((c for c in self.clips if c["name"] == name), None)
        if c is None:
            return None
        q = self.raw()[c["off"]:c["off"] + c["size"]]
        fps = c["fps"] or 30
        tracks = []
        o = 0
        while o + 33 <= len(q):
            bi, ns, nr, npo = struct.unpack_from("<4I", q, o + 1)
            o += 33
            if ns > 100000 or nr > 100000 or npo > 100000:
                break
            sc = struct.unpack_from(f"<{4 * ns}f", q, o); o += 16 * ns
            ro = struct.unpack_from(f"<{5 * nr}f", q, o); o += 20 * nr
            po = struct.unpack_from(f"<{4 * npo}f", q, o); o += 16 * npo
            tracks.append({"bone": bi, "scale": [x / fps if k % 4 == 0 else x for k, x in enumerate(sc)],
                           "rot": [x / fps if k % 5 == 0 else x for k, x in enumerate(ro)],
                           "pos": [x / fps if k % 4 == 0 else x for k, x in enumerate(po)]})
        return {"name": name, "fps": fps, "tracks": tracks}


def load(store, path):
    key = path.lower()
    if key not in _cache:
        d = store.read(key)
        if d is None:
            return None
        _cache[key] = Ast(d)
        if len(_cache) > 12:
            _cache.pop(next(iter(_cache)))
    return _cache[key]
