"""Generate the activity panel (cards/activity*.svg) from the GitHub API. Run daily by .github/workflows/activity.yml.

Needs GH_TOKEN in the environment. Nothing is written unless every request succeeds, so a failed run keeps the last good cards.
Every number on the panel comes from the API; trophy tiers are the thresholds in TROPHIES below.
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from outlines import measure, text_path

USER = "guisba"
OUT = Path(__file__).resolve().parent.parent / "cards"
CRIMSON, CARBON, BONE, SIGNAL, MUTED, LINE = "#9E0B22", "#141012", "#F2ECE6", "#FF5A6A", "#B8A9A6", "#46343A"
EASE = "cubic-bezier(.16,1,.3,1)"

T = {
    "en": {"title": "Activity", "days": "current streak, days", "longest": "longest streak, days", "year_s": "in the last year", "total": "contributions, all time",
           "year": "contributions in the last year", "commits": "commits", "prs": "pull requests", "issues": "issues", "stars": "stars", "repos": "public repos",
           "langs": "Languages, by bytes in public repos", "other": "Other", "dec": ".", "trophies": "Trophies"},
    "pt": {"title": "Atividade", "days": "sequência atual, dias", "longest": "maior sequência, dias", "year_s": "no último ano", "total": "contribuições, no total",
           "year": "contribuições no último ano", "commits": "commits", "prs": "pull requests", "issues": "issues", "stars": "estrelas", "repos": "repos públicos",
           "langs": "Linguagens, por bytes em repos públicos", "other": "Outras", "dec": ",", "trophies": "Troféus"},
}
TIERS = ["C", "B", "A", "S", "SS", "SSS"]
TROPHIES = [("commits", (1, 10, 100, 500, 1000, 5000)), ("prs", (1, 5, 20, 50, 100, 500)), ("issues", (1, 5, 20, 50, 100, 500)),
            ("stars", (1, 10, 50, 100, 500, 1000)), ("repos", (1, 5, 10, 30, 50, 100)), ("total", (1, 50, 200, 1000, 5000, 10000))]


# ── Data ───────────────────────────────────────────────────────────────────
def gql(query):
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "User-Agent": USER})
    body = json.load(urllib.request.urlopen(req, timeout=60))
    if body.get("errors"):
        sys.exit(f"GitHub API: {body['errors']}")
    return body["data"]["user"]


def fetch():
    now = datetime.now(timezone.utc)
    u = gql(f"""{{user(login:"{USER}"){{createdAt pullRequests{{totalCount}} issues{{totalCount}}
      repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){{totalCount nodes{{stargazerCount
        languages(first:20,orderBy:{{field:SIZE,direction:DESC}}){{edges{{size node{{name}}}}}}}}}}}}}}""")
    # contributionsCollection spans at most one year, so walk back from today to the account's creation
    start = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    spans, end = [], now
    while end > start:
        spans.append((max(start, end - timedelta(days=364)), end))
        end = spans[-1][0] - timedelta(seconds=1)
    q = " ".join(f'y{i}:contributionsCollection(from:"{a:%Y-%m-%dT%H:%M:%SZ}",to:"{b:%Y-%m-%dT%H:%M:%SZ}"){{totalCommitContributions '
                 "contributionCalendar{weeks{contributionDays{date contributionCount}}}}"
                 for i, (a, b) in enumerate(spans))
    c = gql(f'{{user(login:"{USER}"){{{q}}}}}')
    days, commits = {}, 0
    for i in range(len(spans)):
        commits += c[f"y{i}"]["totalCommitContributions"]
        for w in c[f"y{i}"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in c["y0"]["contributionCalendar"]["weeks"]]
    # streaks: today with no contribution yet does not break the current one
    order = sorted(days)
    longest = run = 0
    for k in order:
        run = run + 1 if days[k] else 0
        longest = max(longest, run)
    current = 0
    for k in reversed(order):
        if days[k]:
            current += 1
        elif k != order[-1]:
            break
    langs = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    repos = u["repositories"]
    return {"weeks": weeks, "current": current, "longest": longest, "total": sum(days.values()), "commits": commits,
            "year": sum(n for w in weeks for _, n in w), "prs": u["pullRequests"]["totalCount"], "issues": u["issues"]["totalCount"],
            "stars": sum(r["stargazerCount"] for r in repos["nodes"]), "repos": repos["totalCount"], "langs": langs}


# ── Drawing ────────────────────────────────────────────────────────────────
def mix(a, b, t):
    A, B = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in (a, b)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(A, B))


def cube(cx, cy, r, cls=""):
    k = r * 0.866
    return (f'<g{cls}><polygon fill="{SIGNAL}" points="{cx:.1f},{cy - r:.1f} {cx + k:.1f},{cy - r / 2:.1f} {cx:.1f},{cy:.1f} {cx - k:.1f},{cy - r / 2:.1f}"/>'
            f'<polygon fill="#C9132F" points="{cx - k:.1f},{cy - r / 2:.1f} {cx:.1f},{cy:.1f} {cx:.1f},{cy + r:.1f} {cx - k:.1f},{cy + r / 2:.1f}"/>'
            f'<polygon fill="#6E0716" points="{cx:.1f},{cy:.1f} {cx + k:.1f},{cy - r / 2:.1f} {cx + k:.1f},{cy + r / 2:.1f} {cx:.1f},{cy + r:.1f}"/></g>')


def skyline(weeks, x0, y0, width):
    """Isometric contribution city: weeks climb to the right, days descend. Returns (svg, height)."""
    n = len(weeks)
    c = width / ((n + 7) * 0.866)
    cw, ch, tall = c * 0.866, c * 0.5, c * 4.6
    oy = y0 + tall + n * ch
    top = max(cnt for w in weeks for _, cnt in w) or 1
    tile = lambda sx, sy: f"M{sx:.1f} {sy:.1f}L{sx + cw:.1f} {sy - ch:.1f}L{sx + 2 * cw:.1f} {sy:.1f}L{sx + cw:.1f} {sy + ch:.1f}Z"
    flats, bars = [], []
    for w, days in enumerate(weeks):
        for dow, (_, cnt) in enumerate(days):
            sx, sy = x0 + (w + dow) * cw, oy + (dow - w) * ch
            if not cnt:
                flats.append(tile(sx, sy))
            else:
                bars.append((dow - w, w, sx, sy, cnt))
    o = [f'<path fill="#231A1D" stroke="{CARBON}" stroke-width=".8" d="{"".join(flats)}"/>']
    for _, w, sx, sy, cnt in sorted(bars):
        v = (cnt / top) ** 0.6
        h = 5 + tall * v
        col = mix(CRIMSON, SIGNAL, v)
        tp = sy - h
        f = lambda p: " ".join(f"{a:.1f},{b:.1f}" for a, b in p)
        o.append(f'<g class="bar" style="transform-origin:{sx + cw:.1f}px {sy + ch:.1f}px;animation-delay:{0.3 + w * 0.018:.2f}s">'
                 f'<polygon fill="{mix(col, "#000000", .45)}" points="{f([(sx, tp), (sx + cw, tp + ch), (sx + cw, sy + ch), (sx, sy)])}"/>'
                 f'<polygon fill="{mix(col, "#000000", .68)}" points="{f([(sx + cw, tp + ch), (sx + 2 * cw, tp), (sx + 2 * cw, sy), (sx + cw, sy + ch)])}"/>'
                 f'<path fill="{col}" d="{tile(sx, tp)}"/>'
                 f'<path class="wave" style="animation-delay:{3 + w * 0.09:.2f}s" fill="#FFE3E6" d="{tile(sx, tp)}"/></g>')
    return "".join(o), tall + (n + 7) * ch + 2 * ch


def stat(value, label, x, y, size, fill=BONE, lab=20, delay=.5):
    return (f'<g class="d" style="animation-delay:{delay:.2f}s">{text_path(str(value), x, y, size, fill, 900, 112)}'
            f'{text_path(label, x, y + lab * 1.35, lab, MUTED, 500)}</g>')


def lang_bar(langs, t, x, y, width, size):
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])
    shown = [kv for kv in top if kv[1] / total >= 0.015][:5]
    rest = total - sum(v for _, v in shown)
    if rest:
        shown.append((t["other"], rest))
    o = [text_path(t["langs"], x, y, size, BONE, 700)]
    y += size * 0.8
    bx, bh = x, size * 0.75
    tones = [SIGNAL, "#D42A42", CRIMSON, "#6E0716", MUTED, LINE]
    for i, (_, v) in enumerate(shown):
        w = width * v / total
        o.append(f'<rect class="grow" style="animation-delay:{.6 + i * .08:.2f}s" x="{bx:.1f}" y="{y:.1f}" width="{max(w - 2, 2):.1f}" height="{bh:.1f}" fill="{tones[i]}"/>')
        bx += w
    y += bh + size * 1.5
    lx, ls = x, size * 0.9
    for i, (name, v) in enumerate(shown):
        label = f"{name} {v / total * 100:.1f}%".replace(".", t["dec"])
        w = measure(label, ls, wght=500) + ls * 2.1
        if lx + w > x + width:
            lx, y = x, y + ls * 1.6
        o.append(f'<rect x="{lx:.1f}" y="{y - ls * .75:.1f}" width="{ls * .8:.1f}" height="{ls * .8:.1f}" fill="{tones[i]}"/>'
                 + text_path(label, lx + ls * 1.15, y, ls, BONE, 500))
        lx += w
    return "".join(o), y


def medal(cx, cy, r, tier, level, delay):
    """A faceted hexagonal coin: six lit wedges around a flat table, turning on its axis now and then."""
    L = (-0.5, 0.7)
    pts = [(cx + r * math.sin(i * math.pi / 3), cy - r * math.cos(i * math.pi / 3)) for i in range(6)]
    base = mix(CRIMSON, SIGNAL, level / 5)
    o = []
    for i in range(6):
        a, b = pts[i], pts[(i + 1) % 6]
        ang = (i + 0.5) * math.pi / 3
        lit = 0.5 + 0.5 * (math.sin(ang) * L[0] + math.cos(ang) * L[1])
        col = mix(mix(base, "#1A0307", 0.72), mix(base, "#FFE3E6", 0.35), lit)
        o.append(f'<polygon fill="{col}" points="{cx:.1f},{cy:.1f} {a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f}"/>')
    inner = " ".join(f"{cx + .68 * (x - cx):.1f},{cy + .68 * (y - cy):.1f}" for x, y in pts)
    o.append(f'<polygon fill="{mix(base, "#000000", .3)}" stroke="{BONE}" stroke-opacity=".35" points="{inner}"/>')
    size = r * (0.62 if len(tier) == 1 else 0.46 if len(tier) == 2 else 0.36)
    o.append(text_path(tier, cx, cy + size * 0.36, size, BONE, 900, 112, anchor="middle"))
    return f'<g class="coin" style="animation-delay:{delay:.2f}s">{"".join(o)}</g>'


def trophies(data, t, x, y, width, cols):
    earned = []
    for key, limits in TROPHIES:
        level = sum(data[key] >= v for v in limits) - 1
        if level >= 0:
            earned.append((key, level))
    cw = width / cols
    r = min(cw * 0.26, 44)
    o = []
    rows = 0
    for i, (key, level) in enumerate(earned):
        rows = i // cols
        cx, cy = x + cw * (i % cols) + cw / 2, y + r + rows * (r * 2 + 92)
        o.append(medal(cx, cy, r, TIERS[level], level, 4 + i * .35))
        o.append(text_path(f"{data[key]}", cx, cy + r + 32, 24, BONE, 800, 100, anchor="middle"))
        label = t["total"].split(",")[0] if key == "total" else t[key]
        o.append(text_path(label, cx, cy + r + 58, 18, MUTED, 500, 100, anchor="middle"))
    return "".join(o), y + (rows + 1) * (r * 2 + 92) - 24


def panel(data, lang, narrow):
    t = T[lang]
    W = 720 if narrow else 1200
    P = 40 if narrow else 52
    inner = W - 2 * P
    o = []
    title = 64 if narrow else 54
    o.append(cube(P + title * .5, P + title * .45, title * .5, ' class="d"'))
    o.append(text_path(t["title"], P + title * 1.25, P + title * .78, title, BONE, 900, 125, cls="d", track=-.01))
    top = P + title + 28
    sky_w = inner if narrow else 640
    city, sky_h = skyline(data["weeks"], P, top, sky_w)
    o.append(city)
    if narrow:
        y, cx = top + sky_h + 56, P
        col_w, big, small, step = inner, 84, 54, 120
    else:
        y, cx = top + 64, P + sky_w + 44
        col_w, big, small, step = W - P - cx, 72, 40, 104
    o.append(stat(data["current"], t["days"], cx, y, big, SIGNAL, 24 if narrow else 20, .4))
    o.append(stat(data["longest"], t["longest"], cx + col_w / 2, y, big, BONE, 24 if narrow else 20, .5))
    y += step + (10 if narrow else 6)
    o.append(stat(data["total"], t["total"], cx, y, small, BONE, 22 if narrow else 18, .6))
    o.append(stat(data["year"], t["year_s"], cx + col_w / 2, y, small, BONE, 22 if narrow else 18, .65))
    y += step - 12
    bars, ly = lang_bar(data["langs"], t, cx, y, col_w, 24 if narrow else 19)
    o.append(bars)
    ty = max(ly, top + sky_h - 10) + (56 if narrow else 44)
    o.append(text_path(t["trophies"], P, ty, 33 if narrow else 25, BONE, 700))
    medals, end = trophies(data, t, P, ty + 26, inner, 3 if narrow else 6)
    o.append(medals)
    H = round(end + P)
    style = (f".d{{animation:rise 1.1s {EASE} backwards}}@keyframes rise{{from{{opacity:0;transform:translateY(14px)}}}}"
             f".bar{{animation:up 1.2s {EASE} backwards}}@keyframes up{{from{{transform:scaleY(0)}}}}"
             ".wave{opacity:0;animation:wave 11s linear infinite}@keyframes wave{0%,100%{opacity:0}2%{opacity:.75}9%{opacity:0}}"
             f".grow{{transform-box:fill-box;transform-origin:0 50%;animation:grow 1s {EASE} backwards}}@keyframes grow{{from{{transform:scaleX(0)}}}}"
             ".coin{transform-box:fill-box;transform-origin:center;animation:turn 12s cubic-bezier(.45,0,.25,1) infinite}"
             "@keyframes turn{0%,88%{transform:scaleX(1)}94%{transform:scaleX(.04)}100%{transform:scaleX(1)}}"
             "@media (prefers-reduced-motion: reduce){*{animation:none!important}.wave{opacity:0}}")
    title_txt = (f"{t['title']}: {data['current']} {t['days']}; {data['longest']} {t['longest']}; {data['total']} {t['total']}; "
                 f"{data['year']} {t['year']}; {data['commits']} {t['commits']}; {data['prs']} {t['prs']}; {data['issues']} {t['issues']}; "
                 f"{data['stars']} {t['stars']}; {data['repos']} {t['repos']}.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{title_txt}">'
            f'<title>{title_txt}</title><style>{style}</style><defs><radialGradient id="pg" cx=".82" cy="0" r=".95"><stop offset="0" stop-color="{CRIMSON}" stop-opacity=".42"/><stop offset="1" stop-color="{CRIMSON}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="pe" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SIGNAL}" stop-opacity=".6"/><stop offset=".6" stop-color="{LINE}" stop-opacity=".5"/></linearGradient></defs>'
            f'<rect width="{W}" height="{H}" rx="22" fill="{CARBON}"/><rect width="{W}" height="{H}" rx="22" fill="url(#pg)"/>'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="22" fill="none" stroke="url(#pe)" stroke-width="1.5"/>{"".join(o)}</svg>\n')


def main():
    data = fetch()
    OUT.mkdir(exist_ok=True)
    for lang, sfx in (("en", ""), ("pt", "-pt")):
        for narrow, n in ((False, ""), (True, "-narrow")):
            (OUT / f"activity{sfx}{n}.svg").write_text(panel(data, lang, narrow))
    print({k: v for k, v in data.items() if k not in ("weeks", "langs")})


if __name__ == "__main__":
    main()
