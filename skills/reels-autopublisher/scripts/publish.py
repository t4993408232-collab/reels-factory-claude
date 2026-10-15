#!/usr/bin/env python3
"""Автопубликатор Reels по очереди (скилл reels-autopublisher).

Берёт из queue.json ролики, у которых подошло время (at — локальное время из config.timezone),
создаёт контейнер Reels через Instagram Graph API, ждёт обработки и публикует.
Пробные Reels (показ только не-подписчикам, Instagram сам переводит удачные в сетку) — по умолчанию.

Запуск раз в 15 минут (launchd/cron). Без файла APPROVED рядом с очередью ничего не публикует —
это предохранитель. --dry-run показывает очередь.

Сделано @igor_ekai · instagram.com/igor_ekai · t.me/eventstory_by
"""
import json, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CFG = json.loads((Path.home() / ".reels-factory" / "config.json").read_text())
DIR = Path(CFG.get("dir", "~/.reels-factory")).expanduser()
QUEUE, APPROVED, LOG = DIR / "queue.json", DIR / "APPROVED", DIR / "logs" / "publish.log"
TOKEN = Path(CFG["token_file"]).expanduser().read_text().strip()
IG_ID, TZ = CFG["ig_user_id"], ZoneInfo(CFG.get("timezone", "Europe/Moscow"))
G = "https://graph.facebook.com/v23.0"
MAX_ATTEMPTS, PER_RUN, PROCESS_TIMEOUT = 3, 1, 600
# Лимит API — 2200 символов, но кириллицу Instagram считает длиннее, чем len() (2011 → 2678, ошибка 2207010).
CAPTION_MAX = CFG.get("caption_max", 1600)


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now(TZ):%Y-%m-%d %H:%M} | {msg}"
    print(line)
    with LOG.open("a") as f:
        f.write(line + "\n")


def api(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{G}/{path}" + ("" if method == "POST" else "?" + data.decode())
    req = urllib.request.Request(url, data=data if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"error": {"message": f"HTTP {e.code}"}}
    except Exception as e:  # сеть/SSL — повторим в следующий запуск
        return {"error": {"message": str(e)[:200]}}


def publish(item):
    p = dict(media_type="REELS", video_url=item["video_url"], caption=item["caption"], share_to_feed="true")
    if item.get("cover_url"):
        p["cover_url"] = item["cover_url"]
    if item.get("trial", CFG.get("trial_by_default", True)):
        p["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})
    r = api("POST", f"{IG_ID}/media", **p)
    if "id" not in r:
        raise RuntimeError(f"контейнер: {r.get('error', r)}")
    cid, t0 = r["id"], time.time()
    while True:
        s = api("GET", cid, fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") in ("ERROR", "EXPIRED") or time.time() - t0 > PROCESS_TIMEOUT:
            raise RuntimeError(f"обработка: {s}")
        time.sleep(15)
    pub = api("POST", f"{IG_ID}/media_publish", creation_id=cid)
    if "id" not in pub:
        raise RuntimeError(f"публикация: {pub.get('error', pub)}")
    return pub["id"], api("GET", pub["id"], fields="permalink").get("permalink", "")


def main():
    q = json.loads(QUEUE.read_text())
    now = datetime.now(TZ)
    due = [i for i in q if not i.get("media_id") and i.get("attempts", 0) < MAX_ATTEMPTS
           and datetime.fromisoformat(i["at"]).replace(tzinfo=TZ) <= now]
    if "--dry-run" in sys.argv:
        for i in sorted(q, key=lambda x: x["at"]):
            mark = "✅" if i.get("media_id") else ("⏰" if i in due else "  ")
            print(f"{mark} {i['at']}  {'проб' if i.get('trial', True) else 'обыч'}  {i['title']}")
        print("APPROVED:", APPROVED.exists()); return
    if not due:
        return
    if not APPROVED.exists():
        log(f"ждёт одобрения (нет файла APPROVED): {len(due)} в очереди"); return
    for item in due[:PER_RUN]:
        if len(item["caption"]) > CAPTION_MAX:  # не тратим попытки — нужна ручная правка подписи
            item["attempts"], item["last_error"] = MAX_ATTEMPTS, f"подпись {len(item['caption'])} > {CAPTION_MAX}"
            log(f"ПРОПУЩЕН «{item['title']}»: {item['last_error']}")
        else:
            try:
                mid, link = publish(item)
                item.update(media_id=mid, permalink=link, published_at=datetime.now(TZ).isoformat(timespec="minutes"))
                item.pop("last_error", None)
                log(f"опубликован «{item['title']}» → {link}")
            except Exception as e:
                item["attempts"] = item.get("attempts", 0) + 1
                item["last_error"] = str(e)[:300]
                log(f"ОШИБКА «{item['title']}» (попытка {item['attempts']}): {e}")
        QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
