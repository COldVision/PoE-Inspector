// English strings for the Tables section.
I18N.add({
  'фильтр по строкам': 'filter rows',
  'Колонки взяты из dat-schema.': 'Columns are taken from the dat schema.',
  'Файл schema.min.json не найден: показаны только угаданные строковые колонки.': 'schema.min.json not found: only guessed string columns are shown.',
}, [
  [/^(\d+) КБ$/, '$1 KB'],
  [/^(\d+) строк · ширина (\d+) Б · схема$/, '$1 rows · row width $2 B · schema'],
  [/^(\d+) строк · ширина (\d+) Б · колонки угаданы$/, '$1 rows · row width $2 B · columns guessed'],
  [/^(\d+)[–-](\d+) из (\d+)$/, '$1–$2 of $3'],
]);
