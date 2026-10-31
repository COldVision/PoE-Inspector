"""Generic reader for .datc64 tables."""
import struct
NULL = 0xFEFEFEFEFEFEFEFE

class Dat:
    def __init__(self, data: bytes):
        self.data = data
        self.rows = struct.unpack_from("<I", data, 0)[0]
        self.boundary = data.find(b"\xbb\xbb\xbb\xbb\xbb\xbb\xbb\xbb", 4)
        # boundary must sit on a row boundary
        while self.rows and self.boundary >= 0 and (self.boundary - 4) % self.rows:   # boundary -1 looped forever
            self.boundary = data.find(b"\xbb" * 8, self.boundary + 1)
        self.width = (self.boundary - 4) // self.rows if self.rows else 0
        self.heap = self.boundary  # refs are measured from boundary

    def row(self, i):
        o = 4 + i * self.width
        return self.data[o:o + self.width]

    def u8(self, i, off): return self.data[4 + i * self.width + off]
    def i32(self, i, off): return struct.unpack_from("<i", self.data, 4 + i * self.width + off)[0]
    def u32(self, i, off): return struct.unpack_from("<I", self.data, 4 + i * self.width + off)[0]
    def u64(self, i, off): return struct.unpack_from("<Q", self.data, 4 + i * self.width + off)[0]

    def string_at(self, ref):
        if ref == NULL or ref >= len(self.data) - self.boundary: return None
        p = self.boundary + ref
        e = p
        d = self.data
        while e + 1 < len(d) and (d[e] or d[e + 1]): e += 2
        try: return d[p:e].decode("utf-16-le")
        except UnicodeDecodeError: return None

    def str(self, i, off): return self.string_at(self.u64(i, off))

    def array(self, i, off, elem=8):
        n, ref = struct.unpack_from("<QQ", self.data, 4 + i * self.width + off)
        if n == 0 or n > 100000 or ref >= len(self.data) - self.boundary: return []
        p = self.boundary + ref
        return [struct.unpack_from("<Q", self.data, p + k * elem)[0] for k in range(n)] if elem == 8 else []

    def fk(self, i, off):
        v = self.u64(i, off)
        return None if v == NULL else v
