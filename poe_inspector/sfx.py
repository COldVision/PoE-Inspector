"""On-demand rendering of the game's FMOD sound events to WAV (cached) and zip export of a monster's sounds."""
import hashlib, io, json, os, re, threading, zipfile
from . import fmodrender, monster

from .paths import DATA as ROOT
CACHE = os.path.join(ROOT, "cache", "sfx")
_lock = threading.Lock()   # one FMOD process at a time


def filename(event):
    parts = [x for x in re.split(r"[/:]+", event) if x and x.lower() != "event"]
    return re.sub(r"[^\w\-]+", "_", "_".join(parts[-3:])) + ".wav"


def render(store, event, banks):
    if not event.startswith("event:/"):
        return None
    names = monster._bank_names(store.game)
    banks = [names[b.lower()] for b in banks if b.lower() in names]
    if not banks:
        return None
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, hashlib.sha1((event + "|" + "|".join(banks)).encode()).hexdigest() + ".wav")
    if os.path.exists(out) and os.path.getsize(out) > 44:
        return out
    with _lock:
        if os.path.exists(out) and os.path.getsize(out) > 44:
            return out
        tmp = out + ".part"
        r = fmodrender.run(["render", store.game, tmp, event] + banks, timeout=90)
        if r.returncode != 0 or not os.path.exists(tmp):
            return None
        os.replace(tmp, out)
    return out


def zip_monster(store, row):
    d = json.load(open(os.path.join(ROOT, "cache", "monsters", f"{row}_m8.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "cache", "monsters", f"{row}_m8.json")) else monster.detail(store, row)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        used = set()
        for e in d["sfx"]["events"]:
            wav = render(store, e["path"], d["sfx"]["banks"])
            if wav:
                name = "sfx/" + filename(e["path"])
                while name in used:
                    name = name[:-4] + "_.wav"
                used.add(name); z.write(wav, name)
        for o in ((d["audio"].get("aggro") or {}).get("oggs") or []):
            data = store.read(o.lower())
            if data:
                z.writestr("voice/" + os.path.basename(o), data)
    return buf.getvalue()
