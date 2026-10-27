"""Cracked dry-sand ground tile from real game textures: tan coarse sand albedo darkened along the deep-desert crack map."""
import io
import numpy as np
from PIL import Image, ImageChops
from . import textures

G = "art/textures/environment/desert/groundmaterials/"
SIZE = 1024


def _load(store, name, size=SIZE):
    png = textures.dds_to_png(store, G + name, max_size=size, opaque=True)
    return Image.open(io.BytesIO(png)).convert("RGB").resize((size, size))


def colour(store):
    sand = np.asarray(_load(store, "sandcoarse_sgfodj1a_colour_bc7.dds"), dtype=np.float32) / 255
    crack = np.asarray(_load(store, "deepdesertcracks_colour_bc7.dds").convert("L"), dtype=np.float32) / 255
    lo, hi = np.percentile(crack, 2), np.percentile(crack, 98)
    c = np.clip((crack - lo) / max(hi - lo, 1e-3), 0, 1)
    out = np.clip(sand * (0.45 + 0.75 * c[..., None]), 0, 1)
    g = out.mean(axis=2, keepdims=True); out = np.clip((g + (out - g) * 0.6) * 1.08, 0, 1)
    b = io.BytesIO(); Image.fromarray((out * 255).astype(np.uint8)).save(b, "JPEG", quality=88)
    return b.getvalue()


def normal(store):
    a = np.asarray(_load(store, "deepdesertcracks_normal_bc7.dds"), dtype=np.float32) / 255 - 0.5
    b = np.asarray(_load(store, "sandcoarse_sgfodj1a_normal_dxt5.dds"), dtype=np.float32) / 255 - 0.5
    n = a + b * 0.7; n[..., 2] = 0.5 + np.abs(a[..., 2]) * 0.5
    bio = io.BytesIO(); Image.fromarray((np.clip(n + 0.5, 0, 1) * 255).astype(np.uint8)).save(bio, "JPEG", quality=88)
    return bio.getvalue()
