#!/usr/bin/env python3
"""Статистика Reels за последние N дней (скилл reels-daily-analyst).

По каждому ролику: просмотры, охват, средний просмотр, досмотр (ср. просмотр / длина), сохранения,
репосты, комментарии; по аккаунту — подписчики. Пишет stats/ГГГГ-ММ-ДД.json и stats/report.md
(лучшие сверху) в папку из config.dir. Длину ролика берёт из ffprobe по ссылке на видео.

    python3 stats.py [--days 21]

Сделано @igor_ekai · instagram.com/igor_ekai · t.me/eventstory_by
"""
import argparse, json, subprocess, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CFG = json.loads((Path.home() / ".reels-factory" / "config.json").read_text())
DIR = Path(CFG.get("dir", "~/.reels-factory")).expanduser(); OUT = DIR / "stats"
TOKEN = Path(CFG["token_file"]).expanduser().read_text().strip()
IG_ID, TZ = CFG["ig_user_id"], ZoneInfo(CFG.get("timezone", "Europe/Moscow"))
G = "https://graph.facebook.com/v23.0"


def get(path, **p):
    p["access_token"] = TOKEN
    try:
        with urllib.request.urlopen(f"{G}/{path}?{urllib.parse.urlencode(p)}", timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)[:200]}


def duration(url):
    if not url:
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", url],
                       capture_output=True, text=True, timeout=60)
    try:
        return round(float(r.stdout.strip()), 1)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=21); a = ap.parse_args()
    since = datetime.now(timezone.utc) - timedelta(days=a.days)
    media, r = [], get(f"{IG_ID}/media", fields="id,caption,media_product_type,timestamp,permalink,media_url", limit=50)
    while True:
        batch = [m for m in r.get("data", []) if datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")) >= since]
        media += [m for m in batch if m.get("media_product_type") == "REELS"]
        nxt = r.get("paging", {}).get("next")
        if not nxt or len(batch) < len(r.get("data", [])):
            break
        with urllib.request.urlopen(nxt, timeout=60) as resp:
            r = json.loads(resp.read())
    reels = []
    for m in media:
        ins = get(f"{m['id']}/insights", metric="views,reach,likes,comments,saved,shares,ig_reels_avg_watch_time")
        i = {x["name"]: x["values"][0]["value"] for x in ins.get("data", [])}
        dur, awt = duration(m.get("media_url")), i.get("ig_reels_avg_watch_time", 0) / 1000
        published = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
        reels.append({"id": m["id"], "permalink": m["permalink"], "published": published.astimezone(TZ).isoformat(timespec="minutes"),
                      "title": (m.get("caption") or "").split("\n")[0][:80], "duration_s": dur,
                      "views": i.get("views"), "reach": i.get("reach"), "likes": i.get("likes"), "comments": i.get("comments"),
                      "saved": i.get("saved"), "shares": i.get("shares"), "avg_watch_s": round(awt, 1),
                      "retention_pct": round(100 * awt / dur) if dur else None,
                      "hours_live": int((datetime.now(timezone.utc) - published).total_seconds() // 3600)})
    acc = get(IG_ID, fields="followers_count")
    OUT.mkdir(parents=True, exist_ok=True)
    day = datetime.now(TZ).strftime("%Y-%m-%d")
    json.dump({"account": {"followers": acc.get("followers_count")}, "reels": reels}, open(OUT / f"{day}.json", "w"), ensure_ascii=False, indent=1)
    rows = sorted(reels, key=lambda x: -(x["views"] or 0))
    md = [f"# Статистика на {day}", "", f"Подписчики: **{acc.get('followers_count')}** · роликов за {a.days} дн.: {len(reels)}", "",
          "| Опубликован | Ролик | Длина | Просм. | Ср. просм. | Досмотр | Сохр. | Репост | Комм. | Часов |", "|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        md.append(f"| {x['published'][:16]} | {x['title'][:60].replace('|', '/')} | {x['duration_s'] or '?'} | {x['views']} | {x['avg_watch_s']} | "
                  f"{x['retention_pct'] if x['retention_pct'] is not None else '?'} % | {x['saved']} | {x['shares']} | {x['comments']} | {x['hours_live']} |")
    (OUT / "report.md").write_text("\n".join(md + ["", "Сделано @igor_ekai · t.me/eventstory_by"]))
    print(f"ok — {len(reels)} роликов, подписчиков {acc.get('followers_count')}, {OUT / 'report.md'}")


if __name__ == "__main__":
    main()
