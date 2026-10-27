"""Export every skill (descriptions en/ru, icon path, tags, levels, stats text, animations, effects) to skills_export.json."""
import json, sys, time
from poe_inspector.store import Store
from poe_inspector import skills

s = Store("poe2.db"); out = []; t = time.time()
for n, x in enumerate(skills.skill_list(s)):
    if n % 50 == 0: print(n, round(time.time() - t), flush=True)
    if not x["ge"] or x["aura"]:
        continue
    try:
        d = skills.detail(s, x["i"])
        for a in d["anim"]:
            a.pop("timeline_events", None)
        out.append(d)
    except Exception as e:
        print("skip", x["id"], e)
json.dump(out, open("skills_export.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(out), "skills", round(time.time() - t), "s")
