"""Double-click launcher: starts the local server (if it is not already running) and opens PoE Inspector in its own app window."""
import glob, os, shutil, socket, subprocess, sys, time, webbrowser

FROZEN = getattr(sys, 'frozen', False)   # built into an exe by build_exe.bat: the project folder is the one next to the exe
ROOT = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
PORT = 8765
URL = f"http://127.0.0.1:{PORT}/"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def up():
    with socket.socket() as s:
        s.settimeout(.3)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def browser():
    pats = [r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe", r"%ProgramFiles%\Google\Chrome\Application\chrome.exe", r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe", r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"]
    for p in pats:
        g = glob.glob(os.path.expandvars(p))
        if g:
            return g[0]
    return None


def main():
    if not up():
        py = shutil.which("pythonw") if FROZEN else os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        log = open(os.path.join(ROOT, "server.log"), "ab")
        subprocess.Popen([py or shutil.which("python"), "run.py"], cwd=ROOT, stdout=log, stderr=log, creationflags=NOWIN)
        for _ in range(100):
            if up():
                break
            time.sleep(.3)
    b = browser()
    if b:   # own window without tabs / address bar and with its own profile, so it never touches the normal browser
        subprocess.Popen([b, f"--app={URL}", "--window-size=1600,950", "--user-data-dir=" + os.path.join(ROOT, "cache", "appwin")], creationflags=NOWIN)
    else:
        webbrowser.open(URL)


main()
