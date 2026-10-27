// English strings for the section: I18N.add({ 'Русский текст': 'English text' }, [[/^(\d+) шт\.$/, '$1 pcs']]);
// Editor tab: editor.js, editor_ui.js, scenepanel.js, recorder.js (statuses are whole strings, so the composed ones are regexp rules).
const _SLOT = { 'Шлем': 'Helmet', 'Броня': 'Body armour', 'Перчатки': 'Gloves', 'Обувь': 'Boots', 'Оружие': 'Weapon', 'Вторая рука': 'Off-hand' };
const _ERR = {
  'Нет модели': 'No model', 'Нет кадров': 'No frames',
  'Анимация не выбрана — выберите «По кнопке Стоп»': 'No animation selected — choose “On Stop button”',
  'WebM не поддерживается браузером': 'WebM is not supported by this browser',
  'Нужен браузер с WebCodecs (Chrome / Edge)': 'A browser with WebCodecs is required (Chrome / Edge)',
  'Не удалось загрузить мультиплексор MP4 (нужен интернет)': 'Could not load the MP4 muxer (internet connection required)',
};
const _d = {
  // character list, slots, animations
  'Персонаж': 'Character', 'Поиск': 'Search', 'Поиск персонажа': 'Search character', 'Тип персонажа': 'Character type',
  'Все': 'All', 'Игроки': 'Players', 'игрок': 'player',
  'Экипировка': 'Equipment', '— выбрать —': '— select —', 'Снять': 'Remove', 'Закрыть': 'Close',
  'Экипировка доступна для игровых персонажей': 'Equipment is available for player characters only',
  'Только уникальные': 'Unique only', 'Только NPC (оружие и щиты монстров)': 'NPC only (monster weapons and shields)',
  'Ничего не найдено': 'Nothing found', 'Нет анимаций': 'No animations', 'Фильтр': 'Filter', 'скорость': 'speed',
  'Анимации': 'Animations', 'Анимации этого персонажа': 'Animations of this character',
  // scene and light
  'Сцена': 'Scene', 'Сцена и свет': 'Scene and light', 'Студия': 'Studio', 'Игровой вид (тусклый свет, пол)': 'In-game view (dim light, floor)',
  'Игровой вид': 'In-game view', 'Пустая сцена (сетка, вид сверху)': 'Empty scene (grid, top view)', 'Пустая сцена': 'Empty scene',
  'Сцена: сетка': 'Scene: grid', 'Сцена: игровой вид': 'Scene: in-game view', 'Сцена: студия': 'Scene: studio',
  'Загрузка персонажа…': 'Loading character…', 'Загрузка сцены…': 'Loading scene…',
  'Контраст': 'Contrast', 'Контраст в студии, % (100 = без изменений)': 'Studio contrast, % (100 = unchanged)', 'Контраст, %': 'Contrast, %',
  'Блеск': 'Shine', 'Угол': 'Angle', 'Высота': 'Height', 'Положение света: угол': 'Light position: angle', 'Положение света: высота': 'Light position: height',
  'Тени от персонажа': 'Character shadows', 'Тени от модели': 'Model shadows',
  'Показывать источник света (можно перетаскивать)': 'Show light source (draggable)', 'Показывать источник света': 'Show light source',
  'Угол света': 'Light angle', 'Высота света': 'Light height', 'Яркость света': 'Light brightness', 'Яркость света, %': 'Light brightness, %',
  'Сбросить': 'Reset', 'Окружение': 'Environment',
  // export
  'Экспорт': 'Export', 'Экспорт в Blender (.glb)': 'Export to Blender (.glb)', 'Какие анимации экспортировать': 'Which animations to export',
  'Основные (бег, атаки, уклон…)': 'Main (run, attacks, dodge…)', 'Только выбранная': 'Selected only',
  'Все (файл может быть очень большим)': 'All (the file can be very large)', 'Без анимаций': 'No animations',
  'Подготовка…': 'Preparing…',
  // recorder
  'Запись окна': 'Record viewport', 'Запись окна (с прозрачным фоном)': 'Record viewport (with transparent background)',
  'Формат': 'Format', 'Формат записи': 'Recording format',
  'WebM VP9 с прозрачностью (для Premiere с плагином)': 'WebM VP9 with transparency (for Premiere with a plugin)',
  'PNG-последовательность (ZIP, с прозрачностью)': 'PNG sequence (ZIP, with transparency)',
  'MP4 H.264 (для Premiere, без прозрачности)': 'MP4 H.264 (for Premiere, no transparency)',
  'WebM (видео, не для монтажа)': 'WebM (video, not for editing)',
  'Конец': 'End', 'Когда остановить': 'When to stop', 'Конец анимации': 'End of animation', 'По кнопке «Стоп»': 'On Stop button',
  'Кадров/с': 'Frames/s', 'Частота кадров': 'Frame rate', 'Размер': 'Size', 'Разрешение записи': 'Recording resolution', 'Как окно': 'Same as window',
  'Персонаж на весь кадр': 'Fit character to frame', 'Прозрачный фон (без галочки фон записывается)': 'Transparent background (unchecked: the background is recorded)',
  'Начать запись': 'Start recording', 'Стоп': 'Stop', 'Завершаю кодирование…': 'Finishing encoding…',
  'Сохранено видео WebM. Для Premiere выберите MP4 или PNG-последовательность': 'WebM video saved. For Premiere choose MP4 or a PNG sequence',
  'Сохранено видео WebM (альфа зависит от плеера). Для Premiere выберите MP4 или PNG-последовательность': 'WebM video saved (alpha depends on the player). For Premiere choose MP4 or a PNG sequence',
};
for (const [ru, en] of Object.entries(_SLOT)) { _d[ru] = en; _d['Поиск: ' + ru] = 'Search: ' + en; }
for (const [ru, en] of Object.entries(_ERR)) { _d[ru] = en; _d['Ошибка: ' + ru] = 'Error: ' + en; _d['Ошибка экспорта: ' + ru] = 'Export error: ' + en; }
const _num = '(\\d+(?:\\.\\d+)?)';
I18N.add(_d, [
  [/^(?:Ошибка: )?H\.264 (\S+) не поддерживается этим браузером$/, (m, wh) => (/^Ошибка/.test(m) ? 'Error: ' : '') + `H.264 ${wh} is not supported by this browser`],
  [/^Готово: (.+) МБ\. В Blender: File → Import → glTF 2\.0$/, 'Done: $1 MB. In Blender: File → Import → glTF 2.0'],
  [/^Загрузка анимаций (\d+)\/(\d+)$/, 'Loading animations $1/$2'],
  [/^Загрузка (.+)…$/, 'Loading $1…'],
  [/^Анимации для оружия: (.+)$/, 'Animations for weapon: $1'],
  [/^Анимация: (.+)$/, 'Animation: $1'],
  [/^Ошибка сцены: (.+)$/, 'Scene error: $1'],
  [/^Ошибка экспорта: (.+)$/, 'Export error: $1'],
  [/^Ошибка: (.+)$/, 'Error: $1'],
  [/^Уникальный · (.+)$/, 'Unique · $1'],
  [new RegExp('^Запись: ' + _num + ' c$'), 'Recording: $1 s'],
  [/^Кадров: (\d+)((?: \/ \d+)?) · (\d+) МБ( — лимит памяти, останавливаю)?$/, (m, a, b, c, d) => `Frames: ${a}${b} · ${c} MB${d ? ' — memory limit, stopping' : ''}`],
  [/^Кадров: (\d+)((?: \/ \d+)?) \(кодирование идёт параллельно\)$/, 'Frames: $1$2 (encoding in parallel)'],
  [/^Кадров: (\d+)((?: \/ \d+)?)$/, 'Frames: $1$2'],
  [/^Сохранено (\d+) кадров \((.+)\), PNG с альфа-каналом$/, 'Saved $1 frames ($2), PNG with alpha channel'],
  [/^Сохранено (\d+) кадров \((.+)\), PNG с фоном сцены$/, 'Saved $1 frames ($2), PNG with scene background'],
  [/^Сохранён MP4 (\S+), (\d+) к\/с, (\d+) кадров, H\.264( \(в MP4 нет прозрачности: фон записан; для прозрачного фона выберите PNG-последовательность\))?$/,
    (m, wh, fps, n, t) => `Saved MP4 ${wh}, ${fps} fps, ${n} frames, H.264${t ? ' (MP4 has no transparency: the background is recorded; for a transparent background choose a PNG sequence)' : ''}`],
  [/^Сохранён (.+): (\d+) кадров, (.+) МБ, WebM VP9( с прозрачностью)?, (\d+) к\/с \(постоянная частота, с длительностью и индексом\)$/,
    (m, name, n, mb, t, fps) => `Saved ${name}: ${n} frames, ${mb} MB, WebM VP9${t ? ' with transparency' : ''}, ${fps} fps (constant frame rate, with duration and index)`],
]);
