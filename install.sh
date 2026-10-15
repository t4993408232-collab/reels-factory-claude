#!/usr/bin/env bash
# Установка скиллов «Контент-завод Reels на Claude» в ~/.claude/skills.
#   ./install.sh              — все скиллы
#   ./install.sh reels-hooks-ru reels-trend-hunter   — только перечисленные
#   ./install.sh --force      — перезаписать уже установленные
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; DEST="$HOME/.claude/skills"; FORCE=0; NAMES=()
for a in "$@"; do case "$a" in --force) FORCE=1 ;; *) NAMES+=("$a") ;; esac; done
[ ${#NAMES[@]} -eq 0 ] && for d in "$ROOT"/skills/*/; do NAMES+=("$(basename "$d")"); done
mkdir -p "$DEST"
for n in "${NAMES[@]}"; do
  [ -d "$ROOT/skills/$n" ] || { echo "нет скилла: $n" >&2; exit 1; }
  if [ -e "$DEST/$n" ] && [ "$FORCE" -ne 1 ]; then echo "пропущен (уже есть, --force для замены): $n"; continue; fi
  rm -rf "${DEST:?}/$n"; cp -R "$ROOT/skills/$n" "$DEST/$n"; echo "установлен: $n"
done
echo
echo "Готово. Сделано @igor_ekai — Instagram: instagram.com/igor_ekai · Telegram: t.me/eventstory_by"
