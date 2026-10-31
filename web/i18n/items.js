// English strings for the section: I18N.add({ 'Русский текст': 'English text' }, [[/^(\d+) шт\.$/, '$1 pcs']]);
I18N.add({
  'Уникальные': 'Uniques', 'только с моделью': 'with model only', 'Все классы': 'All classes', 'Ничего не найдено': 'Nothing found',
  'Загрузка…': 'Loading…', 'босс': 'boss', 'Скачать .glb': 'Download .glb', 'исходный файл': 'source file',
  'Сборка сцены из файлов игры… (первый раз до 15 секунд)': 'Building the scene from game files… (up to 15 seconds the first time)',
  '(показаны первые': '(showing the first'
}, [
  [/^Скрыто одинаковых вариантов: (\d+)$/, 'Identical variants hidden: $1'],
  [/^Не удалось открыть модель: (.*)$/, 'Could not open the model: $1'],
  [/^(.*) — модели нет$/, '$1 — no model'],
  [/^(\d+) вершин · (\d+) треугольников · LOD: (\d+)$/, '$1 vertices · $2 triangles · LOD: $3'],
  [/^Найдено: (\d+)$/, 'Found: $1'],
  [/^(.*) · 3D$/, '$1 · 3D']
]);
I18N.add({ 'К списку': 'Back to list' });
I18N.add({
  'Источники': 'Sources', 'DNT · не исп.': 'DNT · unused',
  'Помечен [DNT-UNUSED]: в игре не используется': 'Marked [DNT-UNUSED]: not used in the game',
  'Помечен [DNT]: служебное название разработчиков': 'Marked [DNT]: developer placeholder name'
}, [
  [/^Не удалось открыть карточку: (.*)$/, 'Could not open the card: $1'],
  [/^Основа для уникальных предметов: (.*)$/, 'Base for unique items: $1'],
  [/^Помечен \[DNT(-UNUSED)?\]: (.*) \((.*)\)$/, 'Marked [DNT$1]: $2 ($3)']
]);
I18N.add({ 'Предметы с пометкой [DNT] / [UNUSED] в названии': 'Items marked [DNT] / [UNUSED] in the name' });
