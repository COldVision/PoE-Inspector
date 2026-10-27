"""Frame-exact recording to WebM (VP9 + alpha) for editing programs: the browser renders PNG frames, the server pipes them into ffmpeg.
The result has a proper duration, a seek index (cues) and a constant frame rate, unlike the live MediaRecorder output."""
import glob, os, re, shutil, subprocess, threading, uuid
from .datrows import ROOT

OUT = os.path.join(ROOT, "cache", "recordings")
_sessions = {}
_lock = threading.Lock()


def ffmpeg_path():
    p = shutil.which("ffmpeg")
    if p:
        return p
    for pat in (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*FFmpeg*\*\bin\ffmpeg.exe"), r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"):
        g = glob.glob(pat)
        if g:
            return g[0]
    return None


def start(fps, alpha, name, crf=20):
    ff = ffmpeg_path()
    if not ff:
        raise RuntimeError("ffmpeg не найден: установите его (winget install Gyan.FFmpeg) и перезапустите сервер")
    os.makedirs(OUT, exist_ok=True)
    sid = uuid.uuid4().hex[:10]
    safe = re.sub(r"[^\w.-]+", "_", name or "record")[:60] or "record"
    out = os.path.join(OUT, f"{safe}_{sid}.webm")
    fmt = "yuva420p" if alpha else "yuv420p"
    cmd = [ff, "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-",
           "-vf", f"crop=trunc(iw/2)*2:trunc(ih/2)*2,scale=out_color_matrix=bt709:out_range=tv,format={fmt}", "-c:v", "libvpx-vp9", "-pix_fmt", fmt, "-auto-alt-ref", "0", "-b:v", "0", "-crf", str(crf),
           "-row-mt", "1", "-deadline", "good", "-cpu-used", "3", "-g", str(max(2, fps * 2)), "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", str(fps), out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    s = {"p": p, "out": out, "n": 0, "err": [], "name": f"{safe}.webm"}
    threading.Thread(target=lambda: [s["err"].append(l) for l in iter(p.stderr.readline, b"")], daemon=True).start()
    with _lock:
        _sessions[sid] = s
    return sid


def frame(sid, data):
    s = _sessions[sid]
    if s["p"].poll() is not None:
        raise RuntimeError("ffmpeg завершился: " + b"".join(s["err"]).decode("utf-8", "replace")[-300:])
    s["p"].stdin.write(data); s["p"].stdin.flush(); s["n"] += 1


def finish(sid):
    s = _sessions[sid]
    try:
        s["p"].stdin.close()
    except OSError:
        pass
    rc = s["p"].wait()
    if rc != 0 or not os.path.exists(s["out"]):
        raise RuntimeError("ffmpeg: " + b"".join(s["err"]).decode("utf-8", "replace")[-400:])
    return {"n": s["n"], "size": os.path.getsize(s["out"]), "file": f"/api/rec/file?id={sid}", "name": s["name"]}


def cancel(sid):
    s = _sessions.pop(sid, None)
    if s:
        try:
            s["p"].kill()
        except OSError:
            pass
        try:
            os.remove(s["out"])
        except OSError:
            pass


def path_of(sid):
    s = _sessions.get(sid)
    return (s["out"], s["name"]) if s else (None, None)
