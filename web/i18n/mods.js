// English strings for the section "Свойства" (Properties). Game data (mod texts, names, tags, classes, bases, currency) is switched by I18N.lang inside mods_ui.js.
I18N.add({
  'Все области': 'All domains', 'Префикс/суффикс…': 'Prefix/suffix…', 'Любой тег': 'Any tag',
  'нет характеристик': 'no stats', 'Уровень предмета': 'Item level', 'Тиров в группе': 'Tiers in group', 'Тип': 'Type', 'Область': 'Domain',
  'Префикс': 'Prefix', 'Суффикс': 'Suffix', 'Название': 'Name', 'Свойство': 'Property', 'Ур.': 'Lvl',
  'Где выпадает (вес)': 'Where it drops (weight)', 'не выпадает на предметах': 'does not drop on items', 'Характеристики': 'Stats',
  'Семейства и теги': 'Families and tags', 'Выберите тип предмета слева': 'Choose an item type on the left',
  'Всего': 'Total', 'Получение:': 'Obtained with:', 'Ничего не найдено': 'Nothing found', 'тиров': 'tiers',
  'уровень предмета топ-тира': 'item level of the top tier', 'min–max': 'min–max', 'Свойства': 'Properties'
}, [
  [/^Тиры этой группы \((\d+)\)$/, 'Tiers of this group ($1)'],
  [/^(.+) · (\d+) тиров в группе$/, '$1 · $2 tiers in group'],
  [/^(.+) · (.+) · (.+) · уровень предмета (\d+)(?: \(до (\d+)\))? · тип (.+)$/, '$1 · $2 · $3 · item level $4 · type $6'],
  [/^(.+): (\d+) групп свойств$/, '$1: $2 property groups'],
  [/^Базовый (Префикс|Суффикс)$/, 'Base $1']
]);
