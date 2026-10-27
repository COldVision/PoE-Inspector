"""Official Path of Exile 2 news for the home page: Grinding Gear Games forum (announcements, patch notes) and Steam announcements.
Fetched by the server (the browser never talks to those sites), cached in cache/news.json; a stale cache is served when the network is down."""
import html, json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from .paths import DATA as ROOT
CACHE = os.path.join(ROOT, "cache", "news.json")
TTL = 1800
UA = {"User-Agent": "Mozilla/5.0 PoEInspector"}
FORUMS = [(2211, "Анонсы"), (2212, "Патчноуты")]
STEAM = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=2694490&count=8&maxlength=900&format=json"
_lock = {}


def _get(url, timeout=15):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8", "replace")


def _plain(s, n=420):
    s = re.sub(r"(?is)<(script|style).*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</div>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\[/?[a-z*][^\]]*\]|\{STEAM_CLAN_IMAGE\}\S*", "", html.unescape(s), flags=re.I)
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def _date(s):
    try:
        return int(datetime.strptime(s.strip(" ,"), "%b %d, %Y, %I:%M:%S %p").timestamp())
    except ValueError:
        return 0


def _thread_text(tid):
    """(excerpt, image url) of the opening post: news posts are a `newsPost` row, ordinary threads start with a contentStart block."""
    try:
        h = _get(f"https://www.pathofexile.com/forum/view-thread/{tid}")
        m = re.search(r'<tr class="newsPost">(.*?)</tr>', h, re.S)
        if m:
            img = re.search(r'<img src="(https://web\.poecdn\.com/[^"]+)"', m.group(1))
            return _plain(re.sub(r"(?is)<h3>(.*?)</h3>", lambda g: g.group(1) + ": ", m.group(1))), img.group(1) if img else ""
        m = re.search(r'class="contentStart"></div>\s*<div class="content">(.*?)</div>\s*<div class="signature">', h, re.S)
        return (_plain(m.group(1)) if m else ""), ""
    except Exception:
        return "", ""


def _forum(fid, label):
    h = _get(f"https://www.pathofexile.com/forum/view-forum/{fid}")
    out = []
    for m in re.finditer(r'<td class="thread">.*?<a href="/forum/view-thread/(\d+)">\s*(.*?)\s*</a>.*?post_by_account[^>]*><a[^>]*>(.*?)</a>.*?<span class="post_date">(.*?)</span>', h, re.S):
        tid, title, by, d = m.groups()
        out.append({"src": "pathofexile.com", "cat": label, "title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(), "url": f"https://www.pathofexile.com/forum/view-thread/{tid}",
                    "by": html.unescape(by), "time": _date(d), "tid": tid})
    out = out[:8]
    with ThreadPoolExecutor(4) as ex:
        for r, (t, img) in zip(out, ex.map(lambda r: _thread_text(r["tid"]), out)):
            r["text"] = t
            if img:
                r["img"] = img
    return out


def _steam():
    d = json.loads(_get(STEAM))["appnews"]["newsitems"]
    return [{"src": "Steam", "cat": "Steam", "title": x["title"], "url": f"https://store.steampowered.com/news/app/2694490/view/{x['gid']}", "by": x.get("author", ""),
             "time": x["date"], "text": _plain(x.get("contents", ""))} for x in d]


def get(force=False):
    try:
        c = json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        c = {"time": 0, "items": []}
    if not force and time.time() - c["time"] < TTL and c["items"]:
        return c
    items = []; errs = []
    jobs = [lambda f=f, l=l: _forum(f, l) for f, l in FORUMS] + [_steam]
    for j in jobs:
        try:
            items += j()
        except Exception as e:
            errs.append(str(e))
    if items:
        seen = set(); uniq = []
        forum_titles = {x["title"].lower() for x in items if x["src"] != "Steam"}
        for x in sorted(items, key=lambda x: -x["time"]):   # a Steam copy of a forum post is dropped
            if x["url"] not in seen and not (x["src"] == "Steam" and x["title"].lower() in forum_titles):
                seen.add(x["url"]); uniq.append(x)
        c = {"time": int(time.time()), "items": uniq[:30], "errors": errs}
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    else:
        c["errors"] = errs or ["нет данных"]; c["stale"] = True
    return c
