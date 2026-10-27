"""PoE Inspector desktop shell: runs the local server in this process and shows it in an embedded WebView2 window (no browser, no console)."""
import os, socket, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(HERE).lower() == "app":   # installed copy: code is read-only, data goes to the user's profile (a project checkout keeps data next to the code)
    os.environ.setdefault("POE_INSPECTOR_DATA", os.path.join(os.environ.get("LOCALAPPDATA", HERE), "PoE Inspector"))
sys.path.insert(0, HERE)
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ColdVision.PoEInspector")   # taskbar groups and draws the window as its own app, not as python
except Exception:
    pass
if os.environ.get("POE2_RESTART"):
    time.sleep(2.5)   # the previous instance is still shutting its server down
try:
    from poe_inspector import updater
    updater.apply_pending()   # a downloaded update is put in place before anything else is imported
except Exception:
    pass

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/"


def up():
    with socket.socket() as s:
        s.settimeout(.3)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def main():
    if not up():
        from poe_inspector import server
        threading.Thread(target=server.main, kwargs={"port": PORT}, daemon=True).start()
        for _ in range(100):
            if up():
                break
            time.sleep(.1)
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True
    data = os.environ.get("POE_INSPECTOR_DATA", HERE)
    webview.create_window("PoE Inspector", URL, width=1600, height=950, min_size=(1000, 650), background_color="#030409")
    icon = next((c for c in (os.path.join(HERE, "..", "poe_inspector.ico"), os.path.join(HERE, "web", "logo.ico")) if os.path.isfile(c)), None)   # installed: {app}\poe_inspector.ico; project: web\logo.ico
    webview.start(private_mode=False, storage_path=os.path.join(data, "webview"), icon=icon)


main()
