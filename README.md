# Контент-завод Reels на Claude

Набор скиллов для Claude Code, на которых работает контент-завод Instagram-аккаунта [@igor_ekai](https://www.instagram.com/igor_ekai/) — «Нейросети простыми словами». Всё на русском, всё проверено на живом аккаунте: от поиска трендов до автопубликации и ежедневной аналитики.

> Мы не продаём курс. Мы выложили то, чем пользуемся сами каждый день.

## Что внутри

| Скилл | Что делает | Нужно |
|---|---|---|
| [`reels-trend-hunter`](skills/reels-trend-hunter/SKILL.md) | Собирает свежие Reels по хэштегам и аккаунтам, находит ролики-выбросы (относительно медианы автора, без закреплённых и старых), показывает хук первых секунд | [Apify](https://apify.com) (бесплатного тарифа хватает) |
| [`reels-hooks-ru`](skills/reels-hooks-ru/SKILL.md) | Формулы хуков и чек-лист первых 3 секунд — по разбору 167 трендовых русских и мировых Reels про ИИ (октябрь 2026) | — |
| [`reels-voice-to-video`](skills/reels-voice-to-video/SKILL.md) | Запись с диктофона → чистый голос (нейросетевое шумоподавление) → караоке-субтитры по словам → готовый вертикальный ролик | ffmpeg, Python |
| [`reels-iso-story`](skills/reels-iso-story/SKILL.md) | Рецепт роликов «история с героем»: структура сюжета, карточка факта, изометрическая графика, фразовые субтитры | — |
| [`reels-autopublisher`](skills/reels-autopublisher/SKILL.md) | Автопубликация по очереди через Instagram Graph API: пробные Reels, проверка длины подписи, защита от дублей, расписание | Instagram Business + приложение Meta |
| [`reels-daily-analyst`](skills/reels-daily-analyst/SKILL.md) | Ежедневная статистика роликов и ИИ-аналитик, который сам пишет выводы и обновляет стратегию | токен Instagram |
| [`reels-dm-keyword`](skills/reels-dm-keyword/SKILL.md) | «Напиши слово — получи подарок»: автоответ в директ через ManyChat за 15 минут, бесплатно | ManyChat |

## Установка

```bash
git clone https://github.com/t4993408232-collab/reels-factory-claude.git
cd reels-factory-claude && ./install.sh
```

Скиллы скопируются в `~/.claude/skills`. Дальше просто скажите Claude, например: «найди, что сейчас вирусится по хэштегам #нейросети #claude» или «сделай ролик из этой записи голоса».

Настройки (для публикатора и аналитика) — в `~/.reels-factory/config.json`, пример: [`config.example.json`](config.example.json). Токены храните в отдельных файлах с правами `600` и никогда не публикуйте.

## Что мы узнали, пока строили завод

- **Голос с первой секунды.** Ролики «текст на экране + музыка» в 2026 году не досматривают: у нас средний просмотр упал до 6 секунд. У всех лидеров в нише рассказчик начинает говорить на 0,0–0,3 с.
- **Количество не спасает.** 15 похожих роликов в день дали медиану ~150 просмотров. Три разных — лучше пятнадцати одинаковых.
- **Одна вещь на ролик:** один приём, одна фишка, один герой. И конкретный подарок за кодовое слово.
- **Подпись Reels длиннее ~1500 символов кириллицей** Instagram отклоняет (лимит 2200 он считает по-своему) — публикатор это проверяет заранее.

## Хорошие скиллы других авторов

Мы ими пользуемся и рекомендуем (лицензии MIT, все права у авторов):
- instagram-research, video-content-analyzer, tiktok-research, youtube-research — автор bradautomates
- [anatomy](https://github.com/wheresryan22/anatomy) — изометрические фигуры (кит, на котором построена графика в `reels-iso-story`)
- HyperFrames — монтаж видео кодом (HeyGen)
- набор Content Skills (trend-spotter, viral-hook-writer, reel-scripter, caption-and-hashtags и др.) — Ootto

## Лицензия

MIT — пользуйтесь, меняйте, делитесь. Ссылка на нас приветствуется 🙂

---
**Сделано [Игорем Ивановым](https://www.instagram.com/igor_ekai/)** — «Нейросети простыми словами».
Instagram: [@igor_ekai](https://www.instagram.com/igor_ekai/) · Telegram: [t.me/eventstory_by](https://t.me/eventstory_by) · Книга про ИИ (240 страниц, бесплатно): [@Operator_book_bot](https://t.me/Operator_book_bot)
