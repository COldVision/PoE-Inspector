import os, sqlite3, threading
from . import bundle

class Store:
    def __init__(self, db_path):
        self._path = db_path
        self._local = threading.local()      # one SQLite connection per request thread (a shared one breaks under parallel requests)
        self.lock = threading.Lock()
        self.game = self.db.execute("select v from meta where k='game_dir'").fetchone()[0]
        self.bundles = {i: n for i, n in self.db.execute("select id,name from bundles")}
        self._cache = {}   # bundle id -> decompressed bytes (small LRU)

    @property
    def db(self):
        c = getattr(self._local, "c", None)
        if c is None:
            c = self._local.c = sqlite3.connect(self._path)
        return c

    def find(self, path):
        with self.lock:
            return self.db.execute("select bundle,offset,size from files where path=?", (path.lower(),)).fetchone()

    def read(self, path):
        r = self.find(path)
        if r is None: return None
        b, off, size = r
        f = os.path.join(self.game, "Bundles2", self.bundles[b] + ".bundle.bin")
        return bundle.unpack_range(f, off, size)

    def search(self, like, ext=None, limit=200):
        q, a = "select path,size from files where path like ?", [like]
        if ext: q += " and ext=?"; a.append(ext)
        with self.lock:
            return self.db.execute(q + " order by path limit ?", a + [limit]).fetchall()

    def listdir(self, d):
        """Immediate children of folder d ('' = root): ([(name, files_in_subtree_unknown->None)], [(name, size)]).
        Skip-scans the path index: one seek per subfolder, so huge trees stay fast."""
        d = d.strip("/").lower()
        pre = d + "/" if d else ""
        folders, files = [], []
        cur = pre
        db = self.db
        while True:
            r = db.execute("select path,size from files where path>=? limit 1", (cur,)).fetchone()
            if not r or not r[0].startswith(pre):
                break
            rest = r[0][len(pre):]
            if "/" in rest:
                name = rest.split("/", 1)[0]
                folders.append(name)
                cur = pre + name + "0"          # '0' sorts right after '/'
            else:
                files.append((rest, r[1]))
                cur = r[0] + "\0"
        return folders, files
