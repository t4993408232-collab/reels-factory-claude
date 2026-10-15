---
name: reels-autopublisher
description: Автопубликация Instagram Reels по расписанию через Graph API — очередь, пробные Reels, проверка подписи, повторы, запуск раз в 15 минут на Mac (launchd) или Linux (cron). Используй, когда просят «выкладывай ролики сам», «поставь в очередь», «автопостинг Reels», «опубликуй пробным», «расписание публикаций».
---

# Автопубликатор Reels

## Нужно (делает владелец аккаунта, Claude подсказывает)
1. Instagram **Business** или **Creator**, привязанный к странице Facebook.
2. Приложение на developers.facebook.com с продуктом «Instagram Graph API» и правами `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` (для аналитики ещё `instagram_manage_insights`).
3. Токен: Graph API Explorer → выбрать приложение и права → Generate Access Token → «Продлить маркер доступа» (Access Token Debugger) → `me/accounts` → токен страницы (бессрочный). Сохранить в файл `~/.reels-factory/ig_token` с правами 600. **Никогда не вставляйте токен в чат, код или репозиторий.**
4. ID Instagram-аккаунта: `GET me/accounts?fields=instagram_business_account`.
5. `~/.reels-factory/config.json` по образцу `config.example.json` из репозитория.

## Очередь `~/.reels-factory/queue.json`
```json
[{"title": "Чем ChatGPT обязан метеорологу", "at": "2026-10-16T12:00",
  "video_url": "https://…/reel.mp4", "cover_url": "https://…/cover.jpg",
  "caption": "Первая строка — хук с ключевым словом…", "trial": true}]
```
- `video_url` — публичная прямая ссылка на mp4 (например, raw-ссылка из GitHub-репозитория или любое файловое хранилище). Instagram скачивает ролик сам.
- `at` — время в часовом поясе из config. Скрипт публикует 1 ролик за запуск.
- `trial: true` — пробный Reels (по умолчанию).

## Запуск
```bash
python3 scripts/publish.py --dry-run     # посмотреть очередь
touch ~/.reels-factory/APPROVED          # предохранитель: без него ничего не уходит
```
Расписание на Mac — LaunchAgent с `StartInterval` 900 и `python3 …/publish.py`. **Никогда не запускайте публикатор на двух компьютерах с одной очередью** — каждый ролик выйдет дважды.

## Ошибки, которые мы встретили
| Ошибка | Что значит | Что делать |
|---|---|---|
| 2207010 «Слишком длинная подпись» | кириллицу Instagram считает длиннее | держать подпись ≤1500 символов; скрипт пропускает >1600 без траты попыток |
| 2207078 «Превышен лимит пробных Reels» | суточный лимит пробных (~15) | переносить на завтра |
| «User is performing too many actions» | слишком частые действия | реже публиковать, повтор через 15 мин |
| пустой ответ / «не JSON» | сбой сети или API | скрипт повторит в следующий запуск |

## Правила
- Публикации вне очереди, удаление роликов, сообщения — только с явного согласия владельца.
- Сначала пробные Reels: Instagram сам переведёт удачные в сетку профиля.
- Три разных ролика в день лучше пятнадцати похожих.

---
**Сделано [Игорем Ивановым](https://www.instagram.com/igor_ekai/)** — «Нейросети простыми словами».
Instagram: [@igor_ekai](https://www.instagram.com/igor_ekai/) · Telegram: [t.me/eventstory_by](https://t.me/eventstory_by) · Книга про ИИ (240 страниц, бесплатно): [@Operator_book_bot](https://t.me/Operator_book_bot)
