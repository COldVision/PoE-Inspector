"""Updates from GitHub Releases. The release carries `app-update.zip` (the app folder without the Python runtime) and its SHA-256.
Nothing is installed without the user's click, the download is checked against the published SHA-256, and the new files are put in place on the next start
(app_main.pyw calls apply_pending() before importing the server), so a half-written update can never run."""
import hashlib, json, os, re, shutil, tempfile, threading, time, urllib.request, zipfile

from .paths import APP, DATA

CONFIG = os.path.join(APP, "update.json")            # {"repo": "owner/name"}  — empty or missing: updates are off
VERSION_FILE = os.path.join(APP, "VERSION")
PENDING = os.path.join(DATA, "update", "pending.zip")
KEEP = ("poe_inspector", "web", "schema.min.json", "app_main.pyw", "VERSION", "run.py")   # update.json (the user's repo setting) is never overwritten
state = {"phase": "idle", "latest": "", "notes": "", "url": "", "sha": "", "error": "", "checked": 0, "pct": 0}
_lock = threading.Lock()


def current():
    try:
        return open(VERSION_FILE, encoding="utf-8").read().strip() or "0"
    except OSError:
        return "0"


def repo():
    try:
        r = json.load(open(CONFIG, encoding="utf-8")).get("repo", "")
        return r if re.fullmatch(r"[\w.-]+/[\w.-]+", r or "") else ""
    except (OSError, ValueError):
        return ""


def _ver(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0")[:4]) or (0,)


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "PoE-Inspector-updater", "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def check():
    r = repo()
    state.update(error="", checked=int(time.time()))
    if not r:
        state.update(phase="off", latest="", error="")
        return status()
    try:
        d = json.load(_get(f"https://api.github.com/repos/{r}/releases/latest"))
        tag = d.get("tag_name", "")
        assets = {a["name"]: a["browser_download_url"] for a in d.get("assets", [])}
        zurl = assets.get("app-update.zip")
        sha = ""
        if "app-update.zip.sha256" in assets:
            sha = _get(assets["app-update.zip.sha256"]).read().decode().split()[0].lower()
        if zurl and sha and _ver(tag) > _ver(current()):
            state.update(phase="available", latest=tag.lstrip("v"), notes=(d.get("body") or "")[:2000], url=zurl, sha=sha)
        else:
            state.update(phase="uptodate", latest=tag.lstrip("v"), notes="", url="", sha="")
    except Exception as e:   # offline, rate limit, no release yet
        state.update(phase="error", error=f"{type(e).__name__}: {e}")
    return status()


def status():
    return {k: v for k, v in state.items() if k not in ("url", "sha")} | {"current": current(), "repo": repo()}


def _download():
    try:
        os.makedirs(os.path.dirname(PENDING), exist_ok=True)
        tmp = PENDING + ".part"; h = hashlib.sha256(); got = 0
        with _get(state["url"], 60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                f.write(b); h.update(b); got += len(b)
                state["pct"] = int(got * 100 / total) if total else 0
        if h.hexdigest() != state["sha"]:
            os.remove(tmp)
            raise ValueError("контрольная сумма не совпала, обновление отклонено")
        with zipfile.ZipFile(tmp) as z:
            names = z.namelist()
            if any(n.startswith(("/", "..")) or ".." in n.split("/") or ":" in n for n in names) or "VERSION" not in names:
                os.remove(tmp)
                raise ValueError("в архиве недопустимые пути")
        os.replace(tmp, PENDING)
        state["phase"] = "ready"
    except Exception as e:
        state.update(phase="error", error=f"{type(e).__name__}: {e}")


def download():
    with _lock:
        if state["phase"] != "available":
            return status()
        state.update(phase="downloading", pct=0)
        threading.Thread(target=_download, daemon=True).start()
    return status()


def apply_pending():
    """Called at startup before anything from the app is imported: unpack the downloaded update over the app folder."""
    if not os.path.isfile(PENDING):
        return False
    tmp = tempfile.mkdtemp(prefix="poe2upd_")
    try:
        with zipfile.ZipFile(PENDING) as z:
            z.extractall(tmp)
        for name in os.listdir(tmp):
            if name not in KEEP:
                continue
            src, dst = os.path.join(tmp, name), os.path.join(APP, name)
            if os.path.isdir(src):
                bak = dst + ".old"
                shutil.rmtree(bak, ignore_errors=True)
                if os.path.isdir(dst):
                    os.replace(dst, bak)
                shutil.copytree(src, dst)
                shutil.rmtree(bak, ignore_errors=True)
            else:
                shutil.copy2(src, dst)
        os.remove(PENDING)
        return True
    except Exception:
        try:
            os.remove(PENDING)   # a broken update must not be retried on every start
        except OSError:
            pass
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
