// English strings of the "Skills" section (skills_ui.js). The names, descriptions, tags and stat lines of the game data are not here: skills_ui.js picks their English fields itself.
(function () {
  const WEAPON = { 'Безоружный': 'Unarmed', 'Мечи': 'Swords', 'Топоры': 'Axes', 'Булавы': 'Maces', 'Кинжалы': 'Daggers', 'Когти': 'Claws', 'Посохи': 'Staves', 'Жезлы': 'Wands', 'Копья': 'Spears', 'Цепы': 'Flails', 'Луки': 'Bows', 'Арбалеты': 'Crossbows', 'Щиты': 'Shields', 'Любое оружие ближнего боя': 'Any melee weapon', 'Без требований к оружию': 'No weapon requirement' };
  const ATTR = { 'Сила': 'Strength', 'Ловкость': 'Dexterity', 'Интеллект': 'Intelligence' };
  const KINDS = { 'Активные': 'Active', 'Spirit': 'Spirit', 'Поддержки': 'Support', 'Династические': 'Lineage', 'От предметов': 'Item skills', 'Прочие умения': 'Other skills', 'Все': 'All' };
  const CLASSES = { 'Амулеты': 'Amulets', 'Жезлы': 'Wands', 'Посохи': 'Staves', 'Скипетры': 'Sceptres', 'Щиты': 'Shields', 'Баклеры': 'Bucklers', 'прочее': 'other' };
  const TOKENS = { 'Двуручный меч': 'Two-Handed Sword', 'Меч': 'Sword', 'Кинжал': 'Dagger', 'Посох': 'Staff', 'Лук': 'Bow', 'Арбалет': 'Crossbow', 'Двуручная булава': 'Two-Handed Mace', 'Скипетр': 'Sceptre', 'Жезл': 'Wand', 'Копьё': 'Spear', 'Цеп': 'Flail', 'Когти': 'Claws', 'Безоружный': 'Unarmed', 'Баклер': 'Buckler', 'Щит': 'Shield', 'Общие': 'Generic' };
  const FORMS = { 'Медведь': 'Bear', 'Волк': 'Wolf', 'Виверна': 'Wyvern' };
  const alt = o => Object.keys(o).sort((a, b) => b.length - a.length).join('|');
  const word = o => k => o[k] || k;

  const dict = Object.assign({}, WEAPON, ATTR, KINDS, TOKENS, FORMS, {
    // filters and layout
    'Поиск умения или камня': 'Search skill or gem', 'Тип': 'Type', 'Тег': 'Tag', 'Любой тег': 'Any tag', 'Только с анимацией': 'With animation only',
    'Класс оружия': 'Weapon class', 'Ширина столбца категорий (двойной щелчок — сбросить)': 'Category column width (double-click to reset)',
    'Загрузка персонажа…': 'Loading character…', 'Загрузка…': 'Loading…', 'Ничего не найдено': 'Nothing found', 'Нет анимации': 'No animation',
    'Без уровня': 'No level', 'Показать все камни с этим тегом': 'Show all gems with this tag',
    // gem kinds
    'умение': 'skill', 'поддержка': 'support', 'династич.': 'lineage', 'предмет': 'item', 'прочее': 'other',
    'Камень умения': 'Skill Gem', 'Камень Spirit': 'Spirit Gem', 'Поддерживающий камень': 'Support Gem', 'Династическая поддержка': 'Lineage Support', 'Умение': 'Skill', 'Поддержка': 'Support',
    'Поддерживающие камни': 'Support Gems', 'Династические поддержки': 'Lineage Supports', 'Умение от предмета': 'Item Skill', 'Умение без камня': 'Skill without a gem',
    // card labels
    'Категория': 'Category', 'Выпадает с:': 'Dropped by:', 'Даёт предмет:': 'Granted by item:', 'Открыть в разделе предметов': 'Open in the Items section', 'Множитель расхода ресурсов': 'Resource Cost Multiplier', 'Требуется:': 'Requires:', 'Уровень:': 'Level:', 'Резерв:': 'Reservation:', 'Расход ресурсов:': 'Cost:',
    'Множитель расхода маны:': 'Mana Cost Multiplier:', 'Скорость атаки:': 'Attack Speed:', 'Урон от атаки:': 'Attack Damage:', 'Урон:': 'Damage:', 'Шанс крита:': 'Critical Hit Chance:',
    'Требуется атрибут:': 'Requires Attribute:', 'Требуется уровень:': 'Requires Level:', 'Время применения:': 'Cast Time:', 'Перезарядка:': 'Cooldown:', 'Требования камней поддержки': 'Support Gem Requirements',
    'духа': 'Spirit', 'маны': 'mana', 'от базовой': 'of base', 'с': 's', 'c': 's',
    'Дополнительно при качестве 20%:': 'Additional effects from 20% quality:', 'Качество 20%:': 'Quality 20%:',
    'Вставьте в гнездо для камня поддержки в окне умений, чтобы применить эффекты камня к выбранному умению. Нельзя использовать несколько камней поддержки одной и той же категории на одном умении.': 'Place into an item socket in the skills screen to apply the gem’s effects to the selected skill. You cannot use more than one Support Gem of the same category on a skill.',
    'Подходящие поддержки': 'Compatible supports', 'Подходит умениям': 'Fits skills',
    'Нет подходящих умений': 'No compatible skills', 'Для этого умения нет подходящих поддержек': 'No compatible supports for this skill',
    // sounds
    'Воспроизвести': 'Play', 'Сохранить WAV': 'Save WAV', 'нет в банках': 'not in banks', 'Звуки вместе с анимацией': 'Sounds with the animation',
    'У этой анимации звуков в таймлайне нет': 'This animation has no sounds in its timeline', 'Эффекты умения': 'Skill effects', 'эфф.': 'fx',
    'Остальное в банке умения': 'Rest of the skill bank', 'Загрузка звуков из игровых банков…': 'Loading sounds from the game banks…',
    // curve and table
    'Урон от атаки по уровню камня': 'Attack damage by gem level', 'Множитель': 'Multiplier', 'Урон по уровню камня (средний)': 'Damage by gem level (average)', 'Стоимость маны по уровню камня': 'Mana cost by gem level', 'Резерв Spirit по уровню камня': 'Spirit reservation by gem level', 'Уровень персонажа по уровню камня': 'Character level by gem level',
    'Урон': 'Damage', 'Мана': 'Mana', 'Резерв': 'Reservation', 'Ур. персонажа': 'Char. level', 'Ур.': 'Lv.', 'ур.': 'lv.', 'Уровень камня': 'Gem level',
    'Spirit / мана': 'Spirit / mana', 'Параметры умения не зависят от уровня камня.': 'The skill’s parameters do not depend on gem level.', 'Только 1–20': 'Levels 1–20 only', 'Нет описания параметров': 'No stat description',
    'оружие персонажа': 'character’s weapon',
  });

  const W = alt(WEAPON) + '|' + alt(ATTR);
  const rules = [
    [new RegExp('^((?:' + W + ')(?:, (?:' + W + '))*)$'), (m, a) => a.split(', ').map(x => WEAPON[x] || ATTR[x] || x).join(', ')],
    [new RegExp('^(' + alt(KINDS) + ') (\\d+)$'), (m, a, n) => KINDS[a] + ' ' + n],
    [/^Камни от уровня (\d+)$/, 'Gems from level $1'], [/^от уровня (\d+)$/, 'from level $1'],
    [new RegExp('^Умения предметов: (' + alt(CLASSES) + ')$'), (m, a) => 'Item skills: ' + CLASSES[a]],
    [/^Ур\. (\d+)$/, 'Lv. $1'],
    [/^Уровень (\d+)$/, 'Level $1'],
    [/^Ошибка персонажа: (.*)$/, 'Character error: $1'], [/^Ошибка: (.*)$/, 'Error: $1'], [/^Анимация: (.*)$/, 'Animation: $1'], [/^Звуки недоступны: (.*)$/, 'Sounds unavailable: $1'],
    [new RegExp('^Форма: (' + alt(FORMS) + ')$'), (m, a) => 'Form: ' + FORMS[a]],
    [/^и ещё (\d+)$/, 'and $1 more'],
    [/^за каждый 1% качества:\s*(.*)$/, 'per 1% quality: $1'], [/^\(на 20%; за 1% — (.*)\)$/, '(at 20%; per 1% — $1)'],
    [/^(Подходящие поддержки|Подходит умениям) · (\d+)( из (\d+))?$/, (m, a, n, x, t) => (a === 'Подходит умениям' ? 'Fits skills' : 'Compatible supports') + ' · ' + n + (t ? ' of ' + t : '')],
    [/^(Династические|Прочие|Все) (\d+)$/, (m, a, n) => ({ 'Династические': 'Lineage', 'Прочие': 'Other', 'Все': 'All' })[a] + ' ' + n],
    [/^(Династические|Прочие) · (\d+)$/, (m, a, n) => ({ 'Династические': 'Lineage', 'Прочие': 'Other' })[a] + ' · ' + n],
    [/^Анимация (.+)$/, 'Animation $1'],
    [/^([\d.]+) [cс]$/, '$1 s'],
    [new RegExp('^(' + alt(TOKENS) + ') — оружие персонажа$'), (m, a) => TOKENS[a] + ' — character’s weapon'],
    [/^Кривая: (.+) по уровням камня$/, (m, a) => 'Curve: ' + ({ 'Множитель': 'Attack damage', 'Урон': 'Damage', 'Мана': 'Mana', 'Резерв': 'Reservation', 'Ур. персонажа': 'Char. level' })[a] + ' by gem level'],
    [/^Клик по графику выбирает уровень · уровни 1–(\d+)$/, 'Click the chart to pick a level · levels 1–$1'], [/^Клик по графику выбирает уровень · уровни 1–20$/, 'Click the chart to pick a level · levels 1–20'],
    [/^Таблица уровней \((\d+) из (\d+)\)$/, 'Level table ($1 of $2)'],
    [/^(.*) \((\d+) из (\d+)\)$/, '$1 ($2 of $3)'],
    [/^Показать все (\d+)$/, 'Show all $1'],
    [/^резерв (\d+)( · (.*))?$/, (m, r, x, c) => 'reservation ' + r + (c ? ' · ' + c : '')],
    [/^(Сила|Ловкость|Интеллект) (\d+)%$/, (m, a, n) => ATTR[a] + ' ' + n + '%'],
    [/^Требуется (?:уровень|Уровень) (\d+)$/, 'Requires level $1'],
  ];
  I18N.add(dict, rules);
})();
