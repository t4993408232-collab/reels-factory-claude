#!/usr/bin/env python3
"""Голос → вертикальный ролик с караоке-субтитрами (скилл reels-voice-to-video).

1) чистит голос: срез гула, нейросетевое шумоподавление ffmpeg arnndn (если есть модель), де-эссер, компрессия, громкость;
2) распознаёт слова с таймингом (mlx-whisper на Mac или faster-whisper);
3) режет текст на фразы по 2–4 слова и делает ASS-субтитры: сказанное слово — белое, *акцент* — цветом;
4) кладёт голос на фон (ваше видео/картинку или анимированный градиент) и музыку, которая приглушается под голос;
5) пишет 1080×1920 mp4.

    python3 voice_reel.py запись.m4a --out reel.mp4 [--bg фон.mp4|фон.png] [--music музыка.mp3] [--accent ChatGPT Claude]

Модель шумоподавления (std.rnnn) — https://github.com/richardpl/arnndn-models, путь в --rnnn или ~/.reels-factory/std.rnnn.

Сделано @igor_ekai · instagram.com/igor_ekai · t.me/eventstory_by
"""
import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-1500:])
    return r


def clean(src, dst, rnnn, mix):
    chain = ["highpass=f=75"]
    if rnnn and Path(rnnn).exists():
        chain.append(f"arnndn=m={rnnn}:mix={mix}")
    else:
        chain.append("afftdn=nf=-28:tn=1")
    chain += ["silenceremove=start_periods=1:start_threshold=-42dB:stop_periods=-1:stop_duration=0.4:stop_threshold=-42dB:stop_silence=0.28",
              "equalizer=f=280:t=q:w=1.2:g=-2", "equalizer=f=3200:t=q:w=1.5:g=1.5", "deesser=i=0.6:m=0.5:f=0.45:s=o",
              "acompressor=threshold=-24dB:ratio=3:attack=4:release=110:makeup=4", "loudnorm=I=-15:TP=-1.5:LRA=7"]
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "48000", "-af", ",".join(chain), dst)


GLOSSARY = "ChatGPT, Claude, Claude Code, GPT, Gemini, DeepSeek, Instagram, Reels, нейросеть, промпт, токен"
FIX = [(r"ч[аэ]рд?ж?и\s*п[еэ]тт?и|чат\s*джи\s*пи\s*ти|чат\s*gpt", "ChatGPT"), (r"\bклод[аеу]?\b", "Claude")]


def words(wav, lang, glossary=GLOSSARY):
    try:
        import mlx_whisper
        r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language=lang, word_timestamps=True, initial_prompt=glossary)
        ws = [(w["word"].strip(), w["start"], w["end"]) for s in r["segments"] for w in s.get("words", [])]
    except ImportError:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel("medium").transcribe(wav, language=lang, word_timestamps=True, initial_prompt=glossary)
        ws = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    text = " ".join(w for w, _, _ in ws)  # склеиваем «Чарджи Петти» → ChatGPT и т. п.
    for pat, rep in FIX:
        if re.search(pat, text, re.I):
            out, i = [], 0
            while i < len(ws):
                for n in (3, 2, 1):
                    seg = ws[i:i + n]
                    if len(seg) == n and re.fullmatch(pat, " ".join(w for w, _, _ in seg).strip(".,!?:;«»"), re.I):
                        tail = re.sub(r"^.*?([.,!?:;»]*)$", r"\1", seg[-1][0]); out.append((rep + tail, seg[0][1], seg[-1][2])); i += n; break
                else:
                    out.append(ws[i]); i += 1
            ws = out
    return ws


def chunks(ws):
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) >= 4 or (re.search(r"[.,!?:;—…]$", w[0]) and len(cur) >= 2):
            out.append(cur); cur = []
    return out + ([cur] if cur else [])


def ts(t):
    t = max(0, t); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ass(chs, accent, path, color):
    hexc = lambda c: "&H00%s%s%s" % (c[5:7], c[3:5], c[1:3])  # #RRGGBB → ASS BGR
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: W,Inter,86,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,5,3,5,60,60,0,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    acc = {a.lower() for a in accent}
    ev = []
    for i, c in enumerate(chs):
        a, b = c[0][1] - .05, (chs[i + 1][0][1] - .05) if i + 1 < len(chs) else c[-1][2] + .6
        for j, (w, ws, we) in enumerate(c):  # одно событие на каждое новое слово: сказанные яркие, остальные приглушены
            s0, s1 = (a if j == 0 else ws), (c[j + 1][1] if j + 1 < len(c) else b)
            parts = []
            for k, (w2, _, _) in enumerate(c):
                col = hexc(color) if re.sub(r"[^\wё]", "", w2.lower()) in acc else "&H00FFFFFF"
                parts.append(("{\\1c%s\\alpha&H00&}" % col if k <= j else "{\\1c&H00FFFFFF&\\alpha&HA0&}") + w2)
            ev.append(f"Dialogue: 0,{ts(s0)},{ts(s1)},W,,0,0,0,,{{\\pos(540,1330)}}" + " ".join(parts))
    Path(path).write_text(head + "\n".join(ev))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice"); ap.add_argument("--out", default="reel.mp4"); ap.add_argument("--bg"); ap.add_argument("--music")
    ap.add_argument("--accent", nargs="*", default=[]); ap.add_argument("--lang", default="ru"); ap.add_argument("--color", default="#5ee7ff")
    ap.add_argument("--rnnn", default=str(Path.home() / ".reels-factory" / "std.rnnn")); ap.add_argument("--mix", type=float, default=0.75)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(); v, v16, sub = f"{tmp}/voice.wav", f"{tmp}/v16.wav", f"{tmp}/sub.ass"
    clean(a.voice, v, a.rnnn, a.mix)
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", v, "-ac", "1", "-ar", "16000", v16)
    ws = words(v16, a.lang, GLOSSARY + (", " + ", ".join(a.accent) if a.accent else ""))
    if not ws:
        sys.exit("речь не распознана")
    ass(chunks(ws), a.accent, sub, a.color)
    T = ws[-1][2] + 1.2
    if a.bg and a.bg.lower().endswith((".mp4", ".mov")):
        bg = ["-stream_loop", "-1", "-i", a.bg]
    elif a.bg:
        bg = ["-loop", "1", "-i", a.bg]
    else:  # тёмно-синий градиент с медленным дрейфом
        bg = ["-f", "lavfi", "-i", f"gradients=s=1080x1920:c0=0x0d1236:c1=0x03040a:x0=540:y0=700:x1=540:y1=1920:speed=0.004:d={T}"]
    ins = bg + ["-i", v] + (["-stream_loop", "-1", "-i", a.music] if a.music else [])
    fv = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1," + f"subtitles={sub}[v]"
    fa = ("[1:a]asplit=2[va][vb];[2:a]volume=0.25[m];[m][va]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];[vb][md]amix=inputs=2:duration=first:normalize=0[a]"
          if a.music else "[1:a]anull[a]")
    sh("ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fv + ";" + fa, "-map", "[v]", "-map", "[a]", "-t", f"{T:.2f}",
       "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", a.out)
    print(f"готово: {a.out} ({T:.1f} с, слов: {len(ws)})")


if __name__ == "__main__":
    main()
