#!/usr/bin/env python3
"""Тренды Reddit с прогнозом: какие свежие ветки разгонятся в ближайшие сутки.

Скорость = апвоуты / часы^0.8 — свежий пост с быстрым ростом выше старого «топа».
Прогноз = скорость поста / медианная скорость постов этого сабреддита (top day + rising + hot).
Источник: публичный JSON Reddit (без входа); если он закрыт — OpenCLI (`opencli reddit ...`).

  python3 reddit_trends.py ChatGPT ClaudeAI singularity artificial --hours 24 --top 15 --out trends/reddit.md
"""
import argparse, json, statistics, subprocess, sys, time, urllib.request

UA = {'User-Agent': 'reels-reddit-trends/1.0 (research script)'}


def fetch_json(sub, kind, limit=50, t=None):
    url = f'https://www.reddit.com/r/{sub}/{kind}.json?limit={limit}' + (f'&t={t}' if t else '')
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return [c['data'] for c in json.load(r)['data']['children']]


def fetch_opencli(sub, kind, limit=50):
    cmd = ['opencli', 'reddit', 'subreddit', sub, '--sort', kind, '--limit', str(limit), '-f', 'json'] + (['--time', 'day'] if kind == 'top' else [])
    rows = json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=180).stdout or '[]')
    return [dict(title=x.get('title', ''), score=int(x.get('upvotes') or 0), num_comments=int(x.get('comments') or 0),
                 created_utc=x.get('created_utc') or time.time(), permalink=x.get('url', ''), stickied=False,
                 selftext=(x.get('selftext') or '')[:600], media=x.get('url_overridden_by_dest', '')) for x in rows]


def get(sub, kind, t=None):
    try: return fetch_json(sub, kind, t=t)
    except Exception as e:
        print(f'  r/{sub}/{kind}: JSON недоступен ({e}), пробую OpenCLI', file=sys.stderr)
        try: return fetch_opencli(sub, kind)
        except Exception as e2: print(f'  OpenCLI тоже не сработал: {e2}', file=sys.stderr); return []


def vel(p, now):
    h = max(.5, (now - p['created_utc']) / 3600); return p['score'] / h ** .8, h


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('subs', nargs='+'); ap.add_argument('--hours', type=float, default=24)
    ap.add_argument('--top', type=int, default=15); ap.add_argument('--out'); a = ap.parse_args()
    now = time.time(); rows = []
    for s in a.subs:
        allp = [p for p in get(s, 'top', 'day') + get(s, 'rising') + get(s, 'hot') if not p.get('stickied')]
        base = statistics.median([vel(p, now)[0] for p in allp]) if allp else 1  # обычная скорость в этом сабреддите
        seen = set()
        for p in allp:
            if p.get('stickied') or p['title'] in seen: continue
            seen.add(p['title']); v, h = vel(p, now)
            if h > a.hours: continue
            rows.append(dict(sub=s, title=p['title'], up=p['score'], com=p['num_comments'], h=round(h, 1),
                             x=round(v / max(base, 1e-6), 2), talk=round(p['num_comments'] / max(1, p['score']), 2),
                             url='https://reddit.com' + p.get('permalink', '') if p.get('permalink', '').startswith('/') else p.get('permalink', ''),
                             text=p.get('selftext', '')[:600], media=p.get('media') or p.get('url_overridden_by_dest', '')))
        time.sleep(1)
    rows.sort(key=lambda r: -r['x'])
    xs = sorted(r['x'] for r in rows); p90 = xs[int(len(xs) * .9)] if xs else 0; p70 = xs[int(len(xs) * .7)] if xs else 0
    rows = rows[:a.top]
    lines = ['| прогноз | ▲ | 💬 | часов | ветка |', '|---|---|---|---|---|']
    for r in rows:
        tag = '🔥 разгонится' if r['x'] >= p90 else ('↑ растёт' if r['x'] >= p70 else '')
        lines.append(f"| ×{r['x']} {tag} | {r['up']} | {r['com']}{' спор' if r['talk'] > .4 else ''} | {r['h']} | r/{r['sub']} · [{r['title'][:90]}]({r['url']}) |")
    md = '\n'.join(lines); print(md)
    if a.out:
        open(a.out, 'w').write(f'# Reddit-тренды {time.strftime("%Y-%m-%d %H:%M")}\n\n' + md + '\n')
        open(a.out.rsplit('.', 1)[0] + '.json', 'w').write(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == '__main__': main()
