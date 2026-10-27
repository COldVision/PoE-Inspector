"""Passive skill graph (.psg): groups with a centre, nodes on orbits around it, edges between nodes.
Layout (version 3): u8 version, u8 kind, u8 norbits, u8 orbit sizes[], u32 nroots, {u32 id, u32 0}[], u32 ngroups,
group {f32 x, f32 y, u32 assoc, u32 background, u8 jewel_ref, u32 nnodes, node {u32 id, u32 orbit, u32 orbit_index, u32 nconn, {u32 id, i32 weight}[]}[]}[]"""
import math, struct

ORBIT_RADIUS = [0, 82, 162, 335, 493, 662, 846, 251, 1080, 1322]


def parse(data):
    p = 0
    ver, kind, no = data[0], data[1], data[2]; p = 3
    sizes = list(data[p:p + no]); p += no
    nroot = struct.unpack_from("<I", data, p)[0]; p += 4
    roots = []
    for _ in range(nroot):
        roots.append(struct.unpack_from("<I", data, p)[0]); p += 8
    ng = struct.unpack_from("<I", data, p)[0]; p += 4
    nodes, edges, centres, backs = {}, set(), {}, {}
    for gi in range(ng):
        x, y = struct.unpack_from("<ff", data, p); p += 8; centres[gi] = (round(x, 1), round(y, 1))
        _assoc, _bg = struct.unpack_from("<II", data, p); p += 8
        if _bg:
            backs[gi] = _bg
        jewel = data[p]; p += 1
        nn = struct.unpack_from("<I", data, p)[0]; p += 4
        for _ in range(nn):
            nid, orbit, idx, nc = struct.unpack_from("<IIII", data, p); p += 16
            conns = []
            for _c in range(nc):
                cid, w = struct.unpack_from("<Ii", data, p); p += 8
                conns.append((cid, w))
            size = sizes[orbit] if orbit < len(sizes) else 1
            r = ORBIT_RADIUS[orbit] if orbit < len(ORBIT_RADIUS) else 0
            a = 2 * math.pi * idx / max(1, size)
            nodes[nid] = {"id": nid, "g": gi, "x": round(x + r * math.sin(a), 1), "y": round(y - r * math.cos(a), 1), "orbit": orbit, "idx": idx, "jewel_ref": bool(jewel)}
            for cid, _w in conns:
                edges.add((min(nid, cid), max(nid, cid)))
    if p != len(data):
        raise ValueError(f"psg: {len(data) - p} bytes left")
    return {"version": ver, "kind": kind, "orbits": sizes, "roots": roots, "nodes": nodes, "edges": sorted(edges), "groups": ng, "centres": centres, "backs": backs}
