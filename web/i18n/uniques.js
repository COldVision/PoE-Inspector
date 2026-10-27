// English strings for the section: I18N.add({ 'Русский текст': 'English text' }, [[/^(\d+) шт\.$/, '$1 pcs']]);
I18N.add({
  'Откуда падает': 'Where it drops',
  'PoB собирает моды этого предмета кодом, поэтому показаны только постоянные строки (без вариантов)': 'Path of Building builds this item\'s mods in code, so only the fixed lines are shown (no variants)',
  'Моды не найдены в Path of Building — показаны только данные из игры': 'Mods not found in Path of Building — only game data is shown'
}, [
  [/^Уникальный · (.*)$/, 'Unique · $1'],
  [/^Источник: (.*)$/, 'Source: $1']
]);
