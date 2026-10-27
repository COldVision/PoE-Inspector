"""Play the game's own FMOD Studio banks offline (the game's fmod.dll / fmodstudio.dll + its .bank files, read from the install).
Each call runs in its own process: `python -m poe_inspector.fmodrender list <game> <bank>...` / `render <game> <out.wav> <event> <bank>... `.
The libraries are never copied; sound events are rendered to a WAV on demand."""
import ctypes, json, os, subprocess, sys, time
from ctypes import byref, c_char_p, c_int, c_uint, c_void_p, create_string_buffer

VER = 0x00020311          # FMOD 2.03.11 header version (matches the game's DLLs)
MASTER = ["Master Bank.bank", "Master Bank.strings.bank"]


def _ck(r, what):
    if r != 0:
        raise RuntimeError(f"{what}: FMOD error {r}")


def _open(game, out=None):
    os.add_dll_directory(game)
    core = ctypes.WinDLL(os.path.join(game, "fmod.dll"))
    st = ctypes.WinDLL(os.path.join(game, "fmodstudio.dll"))
    sysp, cs = c_void_p(), c_void_p()
    _ck(st.FMOD_Studio_System_Create(byref(sysp), VER), "create")
    _ck(st.FMOD_Studio_System_GetCoreSystem(sysp, byref(cs)), "core")
    # 4 = NOSOUND_NRT (just listing), 5 = WAVWRITER_NRT (offline render into `out`)
    _ck(core.FMOD_System_SetOutput(cs, 5 if out else 4), "output")
    _ck(st.FMOD_Studio_System_Initialize(sysp, 128, 2, 3, c_char_p(out.encode()) if out else None), "init")
    return st, sysp


def _load(st, sysp, game, banks):
    d = os.path.join(game, "FMOD", "Desktop")
    loaded = []
    for name in MASTER + list(banks):
        b = c_void_p()
        _ck(st.FMOD_Studio_System_LoadBankFile(sysp, os.path.join(d, name).encode(), 0, byref(b)), "load " + name)
        loaded.append((name, b))
    return loaded


def list_events(game, banks):
    st, sysp = _open(game)
    out = []
    for name, b in _load(st, sysp, game, banks):
        if name in MASTER:
            continue
        n = c_int(); _ck(st.FMOD_Studio_Bank_GetEventCount(b, byref(n)), "count")
        if not n.value:
            continue
        arr = (c_void_p * n.value)(); got = c_int()
        _ck(st.FMOD_Studio_Bank_GetEventList(b, arr, n.value, byref(got)), "list")
        for i in range(got.value):
            buf = create_string_buffer(512); r = c_int(); ln = c_int(0)
            st.FMOD_Studio_EventDescription_GetPath(arr[i], buf, 512, byref(r))
            st.FMOD_Studio_EventDescription_GetLength(arr[i], byref(ln))
            out.append({"path": buf.value.decode(), "ms": ln.value, "bank": name})
    out.sort(key=lambda e: e["path"])
    return out


def render(game, out, event, banks, max_sec=8.0):
    st, sysp = _open(game, out)
    _load(st, sysp, game, banks)
    desc = c_void_p()
    _ck(st.FMOD_Studio_System_GetEvent(sysp, event.encode(), byref(desc)), "event " + event)
    ln = c_int(0); st.FMOD_Studio_EventDescription_GetLength(desc, byref(ln))
    _ck(st.FMOD_Studio_EventDescription_LoadSampleData(desc), "sample data")
    _ck(st.FMOD_Studio_System_FlushSampleLoading(sysp), "flush")
    inst = c_void_p()
    _ck(st.FMOD_Studio_EventDescription_CreateInstance(desc, byref(inst)), "instance")
    _ck(st.FMOD_Studio_EventInstance_Start(inst), "start")
    limit = min(max_sec, (ln.value / 1000.0 + 0.6) if ln.value > 0 else max_sec)
    step = 1024 / 48000.0
    t, stopped = 0.0, False
    while t < limit + 2.0:
        _ck(st.FMOD_Studio_System_Update(sysp), "update")
        time.sleep(0.001)
        t += step
        state = c_int(0); st.FMOD_Studio_EventInstance_GetPlaybackState(inst, byref(state))
        if state.value == 2:
            break
        if t > limit and not stopped:
            st.FMOD_Studio_EventInstance_Stop(inst, 0); stopped = True
    for _ in range(8):   # flush the tail
        st.FMOD_Studio_System_Update(sysp)
    st.FMOD_Studio_EventInstance_Release(inst)
    st.FMOD_Studio_System_Release(sysp)


def run(args, timeout=60):
    """Run one helper command in a child process (a crash in the DLL then cannot take the web server down)."""
    return subprocess.run([sys.executable, "-m", "poe_inspector.fmodrender"] + args, capture_output=True, timeout=timeout,
                          cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        print(json.dumps(list_events(sys.argv[2], sys.argv[3:]), ensure_ascii=False))
    elif cmd == "render":
        render(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
        print("ok")
