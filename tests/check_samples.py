"""Compare timeless.replace() with the in-game observations in timeless_samples.json (run: python tests/check_samples.py)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from poe_inspector.store import Store
from poe_inspector import timeless as t

d = t.load(Store(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "poe2.db")))
J = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "timeless_samples.json"), encoding="utf-8"))
ok = tot = 0
for s in J["samples"]:
    for n in s["nodes"]:
        r = t.replace(d, s["version"], 0, s["seed"], n["id"], 3)
        tot += 1; ok += bool(r["skill"] and r["skill"]["name"] == n["result"])
print(f"{ok}/{tot} observations reproduced")
