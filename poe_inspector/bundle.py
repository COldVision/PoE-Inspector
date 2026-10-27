"""Oodle-compressed PoE2 bundle reader (own implementation, format per docs/FORMATS.md)."""
import ctypes, os, struct

_HERE = os.path.dirname(os.path.abspath(__file__))
_oo = ctypes.WinDLL(os.path.join(_HERE, "oo2core.dll"))
_oo.OodleLZ_Decompress.restype = ctypes.c_int64
_oo.OodleLZ_Decompress.argtypes = [
    ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
    ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,
    ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_int64, ctypes.c_int32]


def decompress_block(comp: bytes, raw_len: int) -> bytes:
    out = ctypes.create_string_buffer(raw_len + 64)
    n = _oo.OodleLZ_Decompress(comp, len(comp), out, raw_len, 1, 0, 0, None, 0, None, None, None, 0, 3)
    if n != raw_len:
        raise IOError(f"oodle decode failed ({n} != {raw_len})")
    return out.raw[:raw_len]


def unpack(data: bytes) -> bytes:
    """Decompress a whole bundle held in memory."""
    usize, _total, head, _enc, _u10 = struct.unpack_from("<5I", data, 0)
    _us2, _ts2, nblocks, gran = struct.unpack_from("<QQII", data, 20)
    sizes = struct.unpack_from(f"<{nblocks}I", data, 60)
    pos = 12 + head
    out = bytearray()
    for i, s in enumerate(sizes):
        raw_len = gran if i < nblocks - 1 else usize - gran * (nblocks - 1)
        out += decompress_block(data[pos:pos + s], raw_len)
        pos += s
    return bytes(out)


def unpack_range(path: str, offset: int, size: int) -> bytes:
    """Read only the blocks of a bundle file that cover [offset, offset+size)."""
    with open(path, "rb") as f:
        hdr = f.read(60)
        usize, _total, head, _enc, _u10 = struct.unpack_from("<5I", hdr, 0)
        _us2, _ts2, nblocks, gran = struct.unpack_from("<QQII", hdr, 20)
        f.seek(60)
        sizes = struct.unpack(f"<{nblocks}I", f.read(4 * nblocks))
        first, last = offset // gran, (offset + size - 1) // gran
        pos = 12 + head + sum(sizes[:first])
        f.seek(pos)
        out = bytearray()
        for i in range(first, last + 1):
            raw_len = gran if i < nblocks - 1 else usize - gran * (nblocks - 1)
            out += decompress_block(f.read(sizes[i]), raw_len)
        start = offset - first * gran
        return bytes(out[start:start + size])
