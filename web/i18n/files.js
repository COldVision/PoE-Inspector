// English strings for the Files section.
I18N.add({
  'Поиск файла по пути…': 'Search files by path…',
  'папка': 'folder', 'на уровень выше': 'up one level', 'Пусто': 'Empty', 'Ничего не найдено': 'Nothing found',
  'скачать': 'download', 'скачать исходный файл': 'download original file',
  'Просмотр файлов игры': 'Browse game files',
  'Просмотр изображения': 'Image viewer', 'Канал': 'Channel', 'Фон': 'Background',
  'RGB + альфа': 'RGB + alpha', 'RGB (без альфы)': 'RGB (no alpha)', 'Альфа': 'Alpha',
  'Шахматка': 'Checkerboard', 'Тёмный': 'Dark', 'Светлый': 'Light', 'Пурпурный': 'Magenta',
  'Вписать': 'Fit', 'Вписать в окно': 'Fit to window', 'Масштаб 100%': 'Zoom 100%',
  'Сохранить PNG': 'Save PNG', 'Сохранить изображение в PNG (выбранный канал и полное разрешение)': 'Save image as PNG (selected channel, full resolution)',
  'Загрузка…': 'Loading…',
  'Не удалось показать изображение (формат не поддерживается)': 'Cannot display the image (unsupported format)',
}, [
  [/^Результаты поиска: (\d+\+?)\. Очистите строку, чтобы вернуться к папкам\.$/, 'Search results: $1. Clear the search box to return to folders.'],
  [/^(.*) · (\d+(?:\.\d+)?) (Б|КБ|МБ)$/, (m, a, n, u) => a + ' · ' + n + ' ' + ({ 'Б': 'B', 'КБ': 'KB', 'МБ': 'MB' })[u]],
  [/^(\d+(?:\.\d+)?) (Б|КБ|МБ)$/, (m, n, u) => n + ' ' + ({ 'Б': 'B', 'КБ': 'KB', 'МБ': 'MB' })[u]],
  [/^(\d+) Б ·$/, '$1 B ·'],
  [/^· колесо — масштаб, перетаскивание — сдвиг, двойной щелчок — вписать$/, '· wheel to zoom, drag to pan, double-click to fit'],
  [/^Ошибка: (.*)$/, 'Error: $1'],
]);
