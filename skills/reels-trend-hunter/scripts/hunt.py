#!/usr/bin/env python3
"""Охотник за трендами Reels (скилл reels-trend-hunter).

Собирает свежие Reels через Apify по хэштегам и/или аккаунтам, отбрасывает закреплённые
и старые ролики, считает «выброс» — во сколько раз ролик набрал больше медианы своего автора,
и пишет отчёт report.md + top.json. С --hooks скачивает лидеров и распознаёт первые 15 секунд
речи (mlx-whisper или faster-whisper, если установлены) — видно, есть ли голос с 0-й секунды.

    APIFY_TOKEN=... python3 hunt.py --tags нейросети claude --days 14 --out trends/
    APIFY_TOKEN=... python3 hunt.py --accounts soratnik levkudrin --days 30 --hooks 5

Нужно: pip install "apify-client" (работают версии 1.x и 2.x). Токен Apify — в переменной APIFY_TOKEN.

Сделано @igor_ekai · instagram.com/igor_ekai · t.me/eventstory_by
"""
import argparse, json, os, re, statistics, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def run_actor(client, actor, inp):
    try:
        run = client.actor(actor).call(run_input=inp, logger=None)  # без потока логов актёра
    except TypeError:
        run = client.actor(actor).call(run_input=inp)
    ds = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id  # apify-client 1.x / 2.x
    return list(client.dataset(ds).iterate_items())


views = lambda i: i.get("videoPlayCount") or i.get("videoViewCount") or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="*", default=[], help="хэштеги без #")
    ap.add_argument("--accounts", nargs="*", default=[], help="аккаунты без @")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--limit", type=int, default=40, help="роликов на хэштег/аккаунт")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--hooks", type=int, default=0, help="распознать первые 15 с у N лидеров")
    ap.add_argument("--out", default="trends")
    a = ap.parse_args()
    if not (a.tags or a.accounts):
        sys.exit("укажите --tags и/или --accounts")
    token = os.environ.get("APIFY_TOKEN") or sys.exit("нет APIFY_TOKEN")
    from apify_client import ApifyClient
    c = ApifyClient(token)
    items = []
    if a.tags:
        items += run_actor(c, "apify/instagram-hashtag-scraper", {"hashtags": a.tags, "resultsType": "reels", "resultsLimit": a.limit})
    if a.accounts:
        items += run_actor(c, "apify/instagram-scraper", {"directUrls": [f"https://www.instagram.com/{u}/" for u in a.accounts],
                                                          "resultsType": "posts", "resultsLimit": a.limit})
    since = (datetime.now(timezone.utc) - timedelta(days=a.days)).isoformat()[:10]
    seen, fresh = set(), []
    for i in items:  # свежие, не закреплённые, видео, без дублей
        sc = i.get("shortCode")
        if sc in seen or i.get("isPinned") or not views(i) or (i.get("timestamp") or "")[:10] < since:
            continue
        seen.add(sc); fresh.append(i)
    by = {}
    for i in fresh:
        by.setdefault(i.get("ownerUsername"), []).append(i)
    for u, xs in by.items():  # выброс = просмотры / медиана автора (если у автора ≥3 роликов в выборке)
        med = statistics.median(views(x) for x in xs) if len(xs) >= 3 else None
        for x in xs:
            x["_x"] = round(views(x) / med, 1) if med else None
    fresh.sort(key=lambda i: -views(i))
    top = fresh[: a.top]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    json.dump(top, open(out / "top.json", "w"), ensure_ascii=False)
    hooks = {}
    if a.hooks:
        hooks = transcribe([i for i in top if i.get("videoUrl")][: a.hooks])
    lines = [f"# Тренды Reels — {datetime.now():%d.%m.%Y}", "",
             f"Источники: {' '.join('#' + t for t in a.tags)} {' '.join('@' + u for u in a.accounts)} · за {a.days} дн. · свежих роликов: {len(fresh)}", "",
             "| # | Просмотры | ×медиана | Автор | Длина | Подпись | Ссылка |", "|---|---|---|---|---|---|---|"]
    for n, i in enumerate(top, 1):
        cap = re.sub(r"\s+", " ", (i.get("caption") or ""))[:70].replace("|", "/")
        lines.append(f"| {n} | {views(i):,} | {i['_x'] or '—'} | @{i.get('ownerUsername')} | {int(i.get('videoDuration') or 0)} с | {cap} | {i.get('url')} |".replace(",", " "))
    if hooks:
        lines += ["", "## Что звучит в первые 15 секунд", ""]
        for sc, txt in hooks.items():
            lines.append(f"- **{sc}**: {txt or '— голоса нет (только музыка/текст)'}")
    lines += ["", "---", "Сделано @igor_ekai · instagram.com/igor_ekai · t.me/eventstory_by"]
    (out / "report.md").write_text("\n".join(lines))
    print("\n".join(lines[:a.top + 6]))


def transcribe(xs):
    """Первые 15 с речи. Галлюцинации whisper на музыке («Субтитры …», «Продолжение следует») считаем отсутствием голоса."""
    try:
        import mlx_whisper as W; mode = "mlx"
    except ImportError:
        try:
            from faster_whisper import WhisperModel; W = WhisperModel("small"); mode = "fw"
        except ImportError:
            print("для --hooks установите mlx-whisper (Mac) или faster-whisper", file=sys.stderr); return {}
    res, tmp = {}, tempfile.mkdtemp()
    for i in xs:
        v, w = f"{tmp}/{i['shortCode']}.mp4", f"{tmp}/{i['shortCode']}.wav"
        subprocess.run(["curl", "-sL", "-m", "90", "-o", v, i["videoUrl"]])
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-t", "15", "-i", v, "-ac", "1", "-ar", "16000", w])
        if mode == "mlx":
            text = W.transcribe(w, path_or_hf_repo="mlx-community/whisper-large-v3-turbo")["text"]
        else:
            text = " ".join(s.text for s in W.transcribe(w)[0])
        junk = re.search(r"субтитр|продолжение следует|DimaTorzok|подписывайтесь на канал", text, re.I)
        res[i["shortCode"]] = "" if junk else text.strip()
    return res


if __name__ == "__main__":
    main()
