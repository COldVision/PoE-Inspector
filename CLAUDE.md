# PoE Inspector — локальный просмотрщик ресурсов Path of Exile 2

Читает `Bundles2` из Steam-установки (`D:\SteamLibrary\steamapps\common\Path of Exile 2`), игру не изменяет. Python-сервер (`run.py`, порт 8765) + веб-интерфейс на three.js (`web/`). Язык общения с пользователем: русский.

## Запуск и перезапуск

- Старт: `python run.py` из папки проекта, страница http://127.0.0.1:8765/.
- Перезапуск сервера после правки `.py`: убить ТОЛЬКО процесс с `run.py` (PowerShell: `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.CommandLine -match 'run\.py'} | Stop-Process -Force`), затем `Start-Process python run.py -WorkingDirectory <папка проекта> -WindowStyle Hidden`. Не делать `taskkill /IM python.exe`: он убивает и фоновые сборки (экспорт умений и т.п.).
- Файлы `web/*.js` отдаются без кэша (`/static/*.js`), для них достаточно перезагрузки страницы. `index.html` тоже; кэш графики сцен лежит в `cache/`.
- Индекс и каталоги: `build_index.py` (после каждого патча игры), `build_catalog.py`, `build_uniques.py`, `build_skills.py` (экспорт в `skills_export.json`, ~7 минут, запускать в фоне).

## Устройство

- `poe_inspector/bundle.py` — Oodle (`oo2core.dll`, ctypes), `store.py` — поиск и чтение файлов (SQLite `poe2.db`; у каждого потока своё подключение), `server.py` — все эндпоинты `/api/*`.
- Таблицы: `dat.py`/`tables.py`/`datrows.py` (`table(store, name, lang=None)` даёт строки по именам колонок из `schema.min.json`; `lang='russian'` для русских текстов).
- Модели: `mesh.py` (.smd v3, .fmt v9, .tgm), `glb.py`, `textures.py` (материалы, DDS), `ast.py` (скелет и клипы), `actor.py` (персонажи, снаряжение, правила скрытия частей, пресеты классов).
- Данные игры: `catalog.py` (предметы, монстры), `uniques.py` (уникальные из таблиц игры + моды из Path of Building PoE2 в `%APPDATA%\Path of Building Community (PoE2)\Data`), `skills.py` (умения, анимации через `character.act`, эффекты), `monsterinfo.py`, `ground.py` (текстура земли).
- Остальные модули (`sections*.py`, `mods.py`, `tree.py`, `psg.py`, `effects.py`, `fmodrender.py`, `home.py`, `recsrv.py` и т.д.) и `launcher.pyw`, `*.bat`, `PoE Inspector.exe` сделаны в параллельных сессиях; перед правкой читай код, здесь они не описаны.
- Веб: `index.html` (вкладки, просмотрщик, стили на токенах палитры канала), `editor.js` + `editor_ui.js` (персонаж, слоты, анимации, свет), `skills_ui.js`, `monsters_ui.js`, `particles.js`; остальные `web/*.js` — из параллельных сессий. Сцены редактора: Студия, Игровой вид, Пустая сцена (сетка).

## Важные особенности

- Координаты игры: x, y по земле, z вверх; в three.js `(x, -z, y) * 0.01`.
- Анимации умений: клипы `*_stationary` и `*_moving` — аддитивные слои; играть нужно родительский клип (поле `parent` в `.ast`).
- Загрузка персонажа асинхронная: при смене вкладки загрузки отменяются через `Editor.gen`; новые асинхронные операции должны проверять, что блок страницы ещё существует.
- Сервер многопоточный: общие кэши в модулях — только простые dict; тяжёлые вычисления кэшируются файлами в `cache/`.
- Список уникальных: 448 (433 с полными данными PoB, 8 частичных из `Uniques/Special/Generated.lua`, 7 без модов). Вики PoE 2 закрыта от ботов, её не парсить.
- Скиллы оформления лежат в `D:\Claude\Premiere\channel style` (палитра `#FC4C70`, `#3E2D57`, `#1A162F`, `#030409`; кириллица — Cinzel, латиница — Optimus Princeps/Fontin). Интерфейс держать в этой палитре.

## Как работать

- Проверять интерфейс через DOM/запросы к API, без скриншотов (пользователь смотрит картинку сам).
- Правки больших файлов делать скриптами-патчами `patch_*.py` с `assert` на искомую строку; в Bash heredoc не использовать `\n` внутри строк Python (превращается в перевод строки) — писать патч-файл через Write.
- Скачивание файлов и запуск скачанного — только с явного разрешения пользователя; скачанное класть в отдельную папку (`pob_github` и т.п.).
- Незакрытое: проверить анимации монстров; оружие Aurelian стоит внутри модели; установщик (`PoE Inspector.exe`) собран в параллельной сессии, запуск не проверялся.
