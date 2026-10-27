// Header, navigation and common controls.
I18N.add({
  'Редактор': 'Editor', 'Умения': 'Skills', 'Предметы': 'Items', 'Монстры': 'Monsters', 'Источники': 'Sources', 'Свойства': 'Properties',
  'Справочник': 'Reference', 'Дерево': 'Tree', 'Атлас': 'Atlas', 'Модели': 'Models', 'Таблицы': 'Tables', 'Файлы': 'Files', 'Главная': 'Home',
  'Разделы': 'Sections', 'На главную': 'Home', 'PoE Inspector — на главную': 'PoE Inspector — home',
  'Громкость': 'Volume', 'Громкость всех звуков': 'Volume of all sounds',
  'Масштаб интерфейса': 'Interface scale', 'Масштаб интерфейса: размер шрифтов, вкладок и отступов': 'Interface scale: font, tab and spacing size',
  'Качество текстур': 'Texture quality', 'Качество текстур моделей (применяется при следующей загрузке модели)': 'Model texture quality (applies on the next model load)',
  'Текстуры 1024': 'Textures 1024', 'Текстуры 2048': 'Textures 2048', 'Текстуры 4096': 'Textures 4096',
  'Поиск…': 'Search…', 'Поиск': 'Search', 'Класс предмета': 'Item class',
  'Ширина левой панели (двойной щелчок — сбросить)': 'Left panel width (double-click to reset)',
  'Ширина профиля умения (двойной щелчок — сбросить)': 'Skill profile width (double-click to reset)',
  'Высота нижней панели (двойной щелчок — сбросить)': 'Bottom panel height (double-click to reset)',
  'Дерево пассивных умений': 'Passive skill tree', 'Профиль умения': 'Skill profile',
  'Загрузка…': 'Loading…', 'Ничего не найдено': 'Nothing found', 'Закрыть': 'Close', 'Назад': 'Back', 'Сбросить': 'Reset', 'Применить': 'Apply',
  'Да': 'Yes', 'Нет': 'No', 'Все': 'All', 'Любой': 'Any', 'Название': 'Name', 'Описание': 'Description', 'Тип': 'Type', 'Уровень': 'Level', 'Теги': 'Tags',
}, [
  [/^Ошибка: (.*)$/, 'Error: $1'],
  // monster list sub-line: "Акт 1 · Эндгейм · 3D"
  [/^(?:(?:Акт \d+(?: \(в файлах\))?|Интерлюдия|Эндгейм|Лиги|Без зоны|DNT) · )*(?:Акт \d+(?: \(в файлах\))?|Интерлюдия|Эндгейм|Лиги|Без зоны|DNT|3D)$/,
    m => m.split(' · ').map(p => p.replace(/^Акт (\d+)(?: \(в файлах\))?$/, (_m, n, _o, str) => 'Act ' + n + (/в файлах/.test(p) ? ' (in files)' : '')).replace('Интерлюдия', 'Interlude').replace('Эндгейм', 'Endgame').replace('Лиги', 'Leagues').replace('Без зоны', 'No zone')).join(' · ')],
  [/\(Атзири до превращения\)/, '(Atziri before transformation)'],
]);
