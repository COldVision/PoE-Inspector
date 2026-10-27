"""Skill database built from the game's dat tables: names/descriptions (en+ru), icon, tags, per-level stats, stat texts
(.csd), animation state -> clips/timeline (character.act/.atl), and visual effects (SkillArtVariations -> .ao/.pet)."""
import json, os, re
from .datrows import table
from .catalog import text

ACT = "metadata/characters/character.act"
_idx = {}


def _s(v):
    return v if isinstance(v, str) else None


def stat_ids(store):
    if "stats" not in _idx:
        t = table(store, "stats"); _idx["stats"] = [t.get(i, "Id") for i in range(len(t))]
    return _idx["stats"]


def lists(store):
    if "ge_by_as" not in _idx:
        ge = table(store, "grantedeffects"); by_as = {}; by_id = {}
        for i in range(len(ge)):
            a = ge.get(i, "ActiveSkill")
            if a is not None:
                by_as.setdefault(a, []).append(i)
            by_id[ge.get(i, "Id")] = i
        _idx["ge_by_as"] = by_as; _idx["ge_by_id"] = by_id
        # gem effects: granted effect row -> (gem effect row)
        gem = table(store, "gemeffects"); gmap = {}
        for i in range(len(gem)):
            g = gem.get(i, "GrantedEffect")
            if g is not None:
                gmap.setdefault(g, []).append(i)
        _idx["gem_by_ge"] = gmap
    return _idx


def skill_list(store):
    """Compact list of all active skills."""
    if "list" in _idx:
        return _idx["list"]
    a, ru = table(store, "activeskills"), table(store, "activeskills", "russian")
    L = lists(store); out = []; wt = table(store, "activeskillweaponrequirement")
    for i in range(len(a)):
        r = a.row(i)
        if not r["Id"] or not r["DisplayedName"]:
            continue
        wr = r.get("WeaponRequirements"); wr = wt.get(wr, "Id") if wr is not None and wr < len(wt) else ""
        ge = L["ge_by_as"].get(i, [])
        has = False
        if ge:
            try:
                defs = act_defs(store)
                has = any(defs.get(st) and any(p for p, _t in expand_state(defs, defs[st])) for st in anim_chain(store, ge[0]))
            except Exception:
                has = False
        out.append({"anim": has, "i": i, "id": r["Id"], "name": r["DisplayedName"], "ru": ru.get(i, "DisplayedName") or "",
                    "icon": r["Icon_DDSFile"] or "", "gem": bool(r["IsGem"]), "ge": len(ge), "wr": wr, "aura": 38 in (r["ActiveSkillTypes"] or [])})
    _idx["list"] = out
    return out


# ---- stat descriptions (.csd) --------------------------------------------------------------------
_csd_cache = {}


def parse_csd(store, path, seen=None):
    k = path.lower()
    if seen is None and k in _csd_cache:
        return _csd_cache[k]
    r = _parse_csd(store, path, seen)
    if seen is None:
        _csd_cache[k] = r
    return r


def _parse_csd(store, path, seen=None):
    """Return {stat_id: [(stat_ids, [(conditions, text_en, text_ru)])]} lookup keyed by first stat id."""
    seen = seen or set(); path = path.lower()
    if path in seen:
        return {}
    seen.add(path)
    raw = store.read(path)
    if raw is None:
        return {}
    t = raw.decode("utf-16", "replace").lstrip("\ufeff") if raw[:2] in (b"\xff\xfe",) or (len(raw) > 1 and raw[1] == 0) else raw.decode("utf-8", "replace")
    out = {}
    for m in re.finditer(r'^include\s+"([^"]+)"', t, re.M):
        for k, v in parse_csd(store, m.group(1), seen).items():
            out.setdefault(k, v)
    blocks = re.split(r"^description\b.*$", t, flags=re.M)[1:]
    for b in blocks:
        lines = [l for l in b.split("\n") if l.strip()]
        if not lines:
            continue
        head = lines[0].split()
        try:
            n = int(head[0])
        except ValueError:
            continue
        ids = head[1:1 + n]
        lang = "en"; variants = {"en": [], "Russian": []}; i = 1
        while i < len(lines):
            l = lines[i].strip()
            m = re.match(r'lang "([^"]+)"', l)
            if m:
                lang = m.group(1); i += 1; continue
            if re.fullmatch(r"\d+", l):
                cnt = int(l); i += 1
                for _ in range(cnt):
                    if i >= len(lines):
                        break
                    ln = lines[i].strip(); i += 1
                    mm = re.match(r'^((?:\S+\s+){%d})"((?:[^"\\]|\\.)*)"(.*)$' % n, ln + " ")
                    if mm and lang in variants:
                        variants[lang].append((mm.group(1).split(), mm.group(2), mm.group(3).split()))
                continue
            i += 1
        out.setdefault(ids[0], []).append((ids, variants))
    return out


def _cond(c, v):
    if c == "#":
        return True
    if "|" in c:
        lo, hi = c.split("|")
        return (lo == "#" or v >= int(lo)) and (hi == "#" or v <= int(hi))
    if c.startswith("!"):
        return v != int(c[1:])
    try:
        return v == int(c)
    except ValueError:
        return True


def _handlers(v, hs):
    """Apply value handlers (subset); returns a string."""
    f = float(v)
    for h in hs:
        if h in ("divide_by_ten_1dp_if_required", "divide_by_ten_1dp"):
            f /= 10
        elif h == "divide_by_one_hundred" or h == "divide_by_one_hundred_2dp_if_required" or h == "divide_by_one_hundred_2dp":
            f /= 100
        elif h in ("milliseconds_to_seconds", "milliseconds_to_seconds_0dp", "milliseconds_to_seconds_1dp", "milliseconds_to_seconds_2dp", "milliseconds_to_seconds_2dp_if_required"):
            f /= 1000
        elif h == "divide_by_one_thousand":
            f /= 1000
        elif h == "negate":
            f = -f
        elif h in ("per_minute_to_per_second", "per_minute_to_per_second_2dp_if_required", "per_minute_to_per_second_0dp"):
            f /= 60
        elif h == "multiply_by_four":
            f *= 4
        elif h == "double":
            f *= 2
        elif h == "divide_by_two_0dp":
            f /= 2
        elif h == "divide_by_three":
            f /= 3
        elif h == "divide_by_four":
            f /= 4
        elif h == "divide_by_six":
            f /= 6
        elif h == "divide_by_ten_0dp":
            f /= 10
    return ("%.2f" % f).rstrip("0").rstrip(".") if abs(f - round(f)) > 1e-9 else str(int(round(f)))


def render_stat(csd, sid, values, lang="en", markup=False):
    """Render the text of one stat (values: dict stat_id->int). Returns None when no description exists."""
    for ids, variants in csd.get(sid, []):
        vs = [values.get(x, 0) for x in ids]
        for conds, txt, hs in variants.get(lang if lang in variants else "en", []) or variants["en"]:
            if all(_cond(c, v) for c, v in zip(conds, vs)):
                out = txt.replace("\\n", "\n")
                hh = {}
                k = 0
                toks = hs
                # handler tokens look like: name idx name idx ...
                while k + 1 < len(toks):
                    hh.setdefault(int(toks[k + 1]) if toks[k + 1].isdigit() else 0, []).append(toks[k]); k += 2
                for idx, v in enumerate(vs):
                    out = out.replace("{%d}" % idx, _handlers(v, hh.get(idx + 1, [])))
                    out = re.sub(r"\{%d:\+?d\}" % idx, lambda m: ("+" if v >= 0 and "+d" in m.group(0) else "") + _handlers(v, hh.get(idx + 1, [])), out)
                keep = (lambda g: "\u27e6" + g + "\u27e7") if markup else (lambda g: g)
                out = re.sub(r"\[([^\]|]+)\|([^\]]+)\]", lambda m: keep(m.group(2)), out)
                out = re.sub(r"\[([^\]]+)\]", lambda m: keep(m.group(1)), out)
                return out
    return None


# ---- animation states (character.act) ------------------------------------------------------------
def act_text(store):
    if "act" not in _idx:
        _idx["act"] = text(store, ACT)
    return _idx["act"]


def _strip_comments(t):
    return re.sub(r"//[^\n]*", "", t)


def act_defs(store):
    if "actdefs" in _idx:
        return _idx["actdefs"]
    t = _strip_comments(act_text(store)); defs = {}
    for m in re.finditer(r"^[ \t]*((?:Template::)?[\w:]+)\s*=\s*(.*?);", t, re.M | re.S):
        defs.setdefault(m.group(1), m.group(2).strip())
    _idx["actdefs"] = defs
    return defs


def expand_state(defs, rhs, subs=None, depth=0):
    """Expand a state definition into [(clip_patterns, timeline)]; subs = {KEY: value}."""
    subs = dict(subs or {}); out = []
    if depth > 6:
        return out
    for part in re.split(r"\bthen\b", rhs):
        part = part.strip()
        m = re.match(r"Template::(\w+)((?:\s+replace\s+\w+\s+\"[^\"]*\")*)", part)
        if m:
            s2 = dict(subs)
            for k, v in re.findall(r'replace\s+(\w+)\s+"([^"]*)"', m.group(2)):
                s2[k] = v
            body = defs.get("Template::" + m.group(1))
            if body:
                out += expand_state(defs, body, s2, depth + 1)
            continue
        q = re.match(r'"([^"]*)"(?:\s+timeline\s+"([^"]+)")?', part, re.S)
        if q:
            body = q.group(1); tl = q.group(2) or ""
            for k, v in subs.items():
                body = body.replace(k, v); tl = tl.replace(k, v)
            pats = []
            for ent in body.split(","):
                ent = ent.strip()
                if not ent:
                    continue
                pats.append(ent.split(":")[0].strip().split()[0])
            out.append((pats, tl))
    return out


def anim_clips_for(store, state_ids):
    """Resolve animation-state names to clip patterns + matching clips in anim_clips."""
    defs = act_defs(store); res = []
    for sid in state_ids:
        rhs = defs.get(sid)
        if not rhs:
            continue
        for pats, tl in expand_state(defs, rhs):
            clips = []
            for p in pats:
                rx = "^" + re.escape(p).replace(r"\*", "[a-z0-9_]+") + "$"   # weapon clips carry two tokens: attack_sword_unarmed_01a
                rows = store.db.execute("select ast,clip from anim_clips where clip like ? limit 3000", (p.replace("*", "%").replace("_", "\\_") if False else p.replace("*", "%"),)).fetchall()
                for ast, clip in rows:
                    if re.match(rx, clip):
                        clips.append({"ast": ast, "clip": clip})
            res.append({"state": sid, "patterns": pats, "timeline": tl, "clips": clips[:600]})
    return res


def anim_chain(store, ge_row):
    """GrantedEffect.Animation -> [state ids] following Mainhand/Offhand animation keys."""
    an = table(store, "animation"); ge = table(store, "grantedeffects")
    a = ge.get(ge_row, "Animation")
    if a is None:
        return []
    ids, seen, stack = [], set(), [a]
    while stack:
        x = stack.pop(0)
        if x is None or x in seen or x >= len(an):
            continue
        seen.add(x); r = an.row(x)
        if r["Id"]:
            ids.append(r["Id"])
        stack += [r.get("Mainhand_AnimationKey"), r.get("Offhand_AnimationKey")]
    return ids


def timeline_events(store, path):
    t = text(store, path.lower()) if path else ""
    if not t:
        return None
    try:
        j = json.loads(t)
    except Exception:
        return None
    anims = []
    for a in j.get("animations", []):
        ev = [{"t": e.get("time"), "end": e.get("end_time"), "name": e.get("name") or e.get("type"), "data": e.get("data")} for e in a.get("events", []) if e.get("name") or e.get("type")]
        cl = [{"t": e.get("time"), "end": e.get("end_time"), "name": e.get("name") or e.get("type")} for e in a.get("client_events", [])]
        anims.append({"name": a.get("name"), "view": (a.get("view") or {}).get("of"), "events": ev, "client_events": cl})
    return {"extends": j.get("extends"), "animations": anims}


# ---- effects --------------------------------------------------------------------------------------
ART_TABLES = [("AnimatedArt", "miscanimatedartvariations", "Animation", "miscanimated", "AOFile"),
              ("ProjectileArt", "projectilesartvariations", "Projectiles", "projectiles", "AOFiles"),
              ("BeamArt", "miscbeamsartvariations", "MiscAnimated", "miscanimated", "AOFile"),
              ("EffectPacksArt", "misceffectpacksartvariations", None, None, None),
              ("ObjectArt", "miscobjectsartvariations", None, None, None),
              ("MiscParticleArt", "miscparticlesartvariations", None, None, None),
              ("MiscProjectileArt", "miscprojectilemodartvariations", None, None, None),
              ("BuffVisuals", "buffvisualsartvariations", None, None, None),
              ("SkillWeaponEffectsArt", "skillweaponeffectsartvariations", None, None, None)]


def _files_in(row):
    """All game-file strings of a row (recursively through its own string/array columns)."""
    out = []
    for k, v in row.items():
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str) and re.search(r"\.(ao|pet|epk|ecf|aoc|ao2|fmt|sm|smd|mat|dds)$", x, re.I):
                out.append(x)
    return out


def effects_for(store, as_row):
    sa = table(store, "skillartvariations"); rows = []
    for i in range(len(sa)):
        if as_row in (sa.get(i, "ActiveSkill") or []):
            rows.append(i)
    out = []
    for i in rows:
        r = sa.row(i)
        grp = {"id": r["Id"], "variants": r["Variants"], "monster": r["Monster"], "items": []}
        for col, tname, sub, subt, subcol in ART_TABLES:
            ids = r.get(col) or []
            if not ids:
                continue
            try:
                t = table(store, tname)
            except Exception:
                continue
            for k in ids:
                if k is None or k >= len(t):
                    continue
                tr = t.row(k)
                files = _files_in(tr)
                # follow nested foreign rows to the table holding the actual file name
                for c in t.cols:
                    if c[1] in ("foreignrow", "row") and c[0] and c[0] in tr:
                        pass
                item = {"kind": col, "id": tr.get("Id"), "files": files}
                if sub and subt:
                    try:
                        st = table(store, subt)
                        subs = tr.get(sub); subs = subs if isinstance(subs, list) else [subs]
                        for sk in subs:
                            if sk is not None and sk < len(st):
                                item["files"] = item["files"] + _files_in(st.row(sk))
                    except Exception:
                        pass
                grp["items"].append(item)
        out.append(grp)
    return out


def ao_refs(store, path):
    """Particle/effect files an .ao references."""
    t = text(store, path.lower()) if path else ""
    refs = []
    for m in re.finditer(r'"([^"\s]+\.(?:pet|epk|ao|ecf|fmt|sm|smd|mat))"', t, re.I):
        refs.append(m.group(1))
    return list(dict.fromkeys(refs))[:60]


# ---- detail -----------------------------------------------------------------------------------------
def detail(store, i):
    a, ru = table(store, "activeskills"), table(store, "activeskills", "russian")
    r = a.row(i); rr = ru.row(i)
    L = lists(store)
    d = {"i": i, "id": r["Id"], "name": r["DisplayedName"], "ru": rr["DisplayedName"],
         "description": r["Description"], "description_ru": rr["Description"],
         "short": r["ShortDescription"], "short_ru": rr["ShortDescription"],
         "website": r["WebsiteDescription"], "website_ru": rr["WebsiteDescription"],
         "icon": r["Icon_DDSFile"], "video": r["VideoClip"], "ai": r["AIFile"], "stat_description": r["StatDescription"]}
    ty = table(store, "activeskilltype")
    d["types"] = [ty.get(k, "Id") for k in (r["ActiveSkillTypes"] or []) if k is not None and k < len(ty)]
    wr = r.get("WeaponRequirements")
    if wr is not None:
        w = table(store, "activeskillweaponrequirement"); d["weapons"] = w.get(wr, "Id") if wr < len(w) else None
    ges = L["ge_by_as"].get(i, []); ge = table(store, "grantedeffects"); d["effects"] = []
    for g in ges:
        gr = ge.row(g)
        e = {"row": g, "id": gr["Id"], "cast_time": gr["CastTime"], "support": gr["IsSupport"], "animation": anim_chain(store, g)}
        gem = L["gem_by_ge"].get(g, [])
        if gem:
            gt = table(store, "gemeffects"); gtags = table(store, "gemtags")
            e["gem"] = gt.get(gem[0], "Name")
            e["tags"] = [x for x in (gtags.get(k, "Name") for k in (gt.get(gem[0], "GemTags") or []) if k is not None) if x]
        e["levels"] = levels_for(store, g)
        e["stats"] = stats_for(store, g, r["StatDescription"])
        d["effects"].append(e)
    d["anim"] = []
    for e in d["effects"][:1]:
        d["anim"] = anim_clips_for(store, e["animation"])
        for a_ in d["anim"]:
            tl = timeline_events(store, a_["timeline"]) if a_.get("timeline") else None
            a_["timeline_events"] = tl
            views = list(dict.fromkeys(x["view"] for x in (tl or {}).get("animations", []) if x.get("view")))
            seen = {(c["ast"], c["clip"]) for c in a_["clips"]}
            for v in views:
                for ast, clip in store.db.execute("select ast,clip from anim_clips where clip=?", (v,)).fetchall():
                    if (ast, clip) not in seen:
                        a_["clips"].append({"ast": ast, "clip": clip}); seen.add((ast, clip))
    if "crossbow" in (d.get("weapons") or "").lower() and d["anim"]:   # the crossbow's own attack clips are not in the skill's animation states
        cl = [{"ast": ast, "clip": clip} for ast, clip in store.db.execute("select ast,clip from anim_clips where clip like 'attack_hip_crossbow_0%'").fetchall() if re.fullmatch(r"attack_hip_crossbow_0\d", clip)]
        if cl:
            d["anim"].insert(0, {"state": "CrossbowAttack", "patterns": ["attack_hip_crossbow_*"], "timeline": "", "clips": cl})
    # *_stationary / *_moving variants are additive layers: play their absolute parent clip instead
    from . import ast as astmod
    for a_ in d["anim"]:
        out, seen = [], set()
        for c in a_["clips"]:
            name = c["clip"]
            try:
                ast_ = astmod.load(store, c["ast"]); me = next((x for x in ast_.clips if x["name"] == name), None); par = me["parent"] if me else ""
                pc = next((x for x in ast_.clips if x["name"] == par), None) if par else None
                # the parent clip is the full animation unless it is only a stub (a few poses): throw_flask_*_01 is ~12 KB while its _stationary / _moving layers are ~95 KB
                if pc and me and pc["size"] >= 0.5 * me["size"]:
                    name = par
                if name.endswith("_additive") and any(x["name"] == name[:-9] for x in ast_.clips):   # the additive layer of a bow attack: play the full clip
                    name = name[:-9]
            except Exception:
                pass
            if (c["ast"], name) not in seen:
                seen.add((c["ast"], name)); out.append({"ast": c["ast"], "clip": name, "state": c.get("state")})
        a_["clips"] = out
    try:
        from . import forms
        d["form"] = forms.for_skill(store, ges[0], r["DisplayedName"]) if ges else None
    except Exception:
        d["form"] = None
    d["art"] = effects_for(store, i)
    for grp in d["art"]:
        for it in grp["items"]:
            it["refs"] = {f: ao_refs(store, f) for f in it["files"] if f.lower().endswith(".ao")}
    return d


def levels_for(store, ge_row):
    if "lv" not in _idx:
        t = table(store, "grantedeffectsperlevel"); m = {}
        for i in range(len(t)):
            g = t.get(i, "GrantedEffect")
            if g is not None:
                m.setdefault(g, []).append(i)
        _idx["lv"] = m
    t = table(store, "grantedeffectsperlevel"); out = []
    for i in _idx["lv"].get(ge_row, []):
        r = t.row(i)
        out.append({"level": r["Level"], "cooldown": r["Cooldown"], "uses": r["StoredUses"], "cost": r["CostAmounts"], "atk_time": r["AttackTime"],
                    "reservation": r["Reservation"], "actor_level": r["ActorLevel"], "cost_mult": r["CostMultiplier"], "atk_speed": r.get("AttackSpeedMultiplier")})
    out.sort(key=lambda x: x["level"] if x["level"] is not None else 0)
    return out


def stats_for(store, ge_row, csd_path):
    ge = table(store, "grantedeffects"); ids = stat_ids(store)
    sets = [ge.get(ge_row, "StatSet")] + list(ge.get(ge_row, "AdditionalStatSets") or [])
    st = table(store, "grantedeffectstatsets"); lv = table(store, "grantedeffectstatsetsperlevel")
    if "sl" not in _idx:
        m = {}
        for i in range(len(lv)):
            s_ = lv.get(i, "StatSet")
            if s_ is not None:
                m.setdefault(s_, []).append(i)
        _idx["sl"] = m
    if "basecsd" not in _idx:
        base = {}
        for p in ("data/statdescriptions/skill_stat_descriptions.csd", "data/statdescriptions/active_skill_gem_stat_descriptions.csd"):
            for k, v in parse_csd(store, p).items():
                base.setdefault(k, v)
        _idx["basecsd"] = base
    csd = dict(_idx["basecsd"])
    if csd_path:
        for k, v in parse_csd(store, csd_path).items():
            csd[k] = v
    out = []
    for s_ in sets:
        if s_ is None or s_ >= len(st):
            continue
        sr = st.row(s_)
        cs = [ids[k] for k in (sr["ConstantStats"] or []) if k is not None and k < len(ids)]
        cv = sr["ConstantStatsValues"] or []
        const = dict(zip(cs, cv)); levels = []
        for li in _idx["sl"].get(s_, []):
            r = lv.row(li)
            ad = [ids[k] for k in (r["AdditionalStats"] or []) if k is not None and k < len(ids)]
            av = r["AdditionalStatsValues"] or []
            fl = [ids[k] for k in (r["FloatStats"] or []) if k is not None and k < len(ids)]
            fv = r["FloatStatsValues"] or []
            br = r.get("BaseResolvedValues") or []
            if br and len(br) == len(fl):   # FloatStats hold the damage multiplier; the value the game shows for this gem level is the resolved one
                fv = br
            vals = dict(const); vals.update(zip(ad, av)); vals.update(zip(fl, fv))
            lines, lines_ru = [], []
            for sid in list(vals.keys()):
                tx = render_stat(csd, sid, vals, "en", True)
                if tx:
                    lines.append(tx); lines_ru.append(render_stat(csd, sid, vals, "Russian", True) or tx)
            dmg = 0.0; hit = False
            for sid, v in vals.items():
                m = re.fullmatch(r"(spell|attack|secondary)_minimum_base_(\w+)_damage", sid)
                if m and isinstance(v, (int, float)):
                    hi = vals.get(f"{m.group(1)}_maximum_base_{m.group(2)}_damage")
                    if isinstance(hi, (int, float)):
                        dmg += (v + hi) / 2; hit = True
            levels.append({"dmg": round(dmg, 1) if hit else None, "level": r["GemLevel"], "crit": r["SpellCritChance"] or r["AttackCritChance"], "mult": r["BaseMultiplier"],
                           "actor_level": r["ActorLevel"], "stats": dict(zip(ad, av)), "text": lines, "text_ru": lines_ru})
        levels.sort(key=lambda x: x["level"] if x["level"] is not None else 0)
        out.append({"set": sr["Id"], "const": const, "levels": levels})
    return out
