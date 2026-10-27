"""First run: find the game folder and build the local database from it (file index, item/monster catalog, uniques). Nothing from the game is shipped with the app."""
import glob, os, re, threading, time, traceback

from .paths import DB

state = {"phase": "idle", "step": 0, "steps": 3, "msg": "", "log": [], "error": "", "started": 0}
_lock = threading.Lock()


def find_games():
    """Steam installs of Path of Exile 2 (default library, libraryfolders.vdf, other drives' SteamLibrary)."""
    libs = []
    for base in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), os.environ.get("ProgramFiles", r"C:\Program Files")):
        vdf = os.path.join(base, "Steam", "steamapps", "libraryfolders.vdf")
        libs.append(os.path.join(base, "Steam"))
        if os.path.isfile(vdf):
            libs += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf-8", errors="replace").read())]
    for d in "CDEFGHIJ":
        libs += [f"{d}:\\SteamLibrary", f"{d}:\\Steam", f"{d}:\\Games\\Steam"]
    out = []
    for lb in libs:
        for name in ("Path of Exile 2", "Path of Exile 2 Beta"):
            g = os.path.join(lb, "steamapps", "common", name)
            if os.path.isfile(os.path.join(g, "Bundles2", "_.index.bin")) and g not in out:
                out.append(g)
    for g in glob.glob(r"C:\Program Files*\Grinding Gear Games\Path of Exile 2"):
        if os.path.isfile(os.path.join(g, "Bundles2", "_.index.bin")) and g not in out:
            out.append(g)
    return out


def _log(m):
    state["msg"] = m; state["log"].append(m); state["log"] = state["log"][-40:]


def _run(game):
    from . import server, index, store as st, catalog, uniques
    try:
        state.update(phase="running", error="", log=[], started=time.time())
        state["step"] = 1; _log("Индекс файлов игры (около минуты)…")
        index.build(game, DB, _log)
        s = st.Store(DB)
        state["step"] = 2; _log("Каталог предметов и монстров…")
        catalog.build(s, _log)
        state["step"] = 3; _log("Уникальные предметы…")
        uniques.build(s, _log)
        server.store = s
        state["phase"] = "done"; _log("Готово")
    except Exception as e:
        state.update(phase="error", error=f"{type(e).__name__}: {e}")
        state["log"].append(traceback.format_exc()[-600:])
        try:
            if os.path.exists(DB):
                os.remove(DB)   # never leave a half-built database: the next start would take it for a finished one
        except OSError:
            pass


def start(game):
    from . import home
    r = home.check_dir(game)
    if not r["ok"]:
        raise ValueError("В этой папке нет Bundles2/_.index.bin: выберите папку Path of Exile 2")
    with _lock:
        if state["phase"] == "running":
            return state
        threading.Thread(target=_run, args=(r["path"],), daemon=True).start()
        state["phase"] = "running"
    return state
