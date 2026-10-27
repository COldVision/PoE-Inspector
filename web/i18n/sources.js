// Sources section: where unique items drop from. Source names (bosses, content, areas) come from the data in both languages (sources_ui.js picks by I18N.lang).
I18N.add({
  // type filter / source types
  'Все типы': 'All types', 'Босс': 'Boss', 'Испытание': 'Trial', 'Контент лиги': 'League content', 'Карта / локация': 'Map / location',
  'Лига (добавлено в)': 'League (added in)', 'Больше не добывается': 'No longer obtainable', 'Источник неизвестен': 'Source unknown',
  // provenance labels
  'Подтверждено': 'Confirmed', 'Косвенно': 'Indirect', 'Предположение': 'Assumption', 'Справка': 'Info', 'Без данных': 'No data', 'Список': 'List',
  'подтверждено игроком (проверено в игре)': 'confirmed by a player (checked in game)', 'подтверждено (Path of Building)': 'confirmed (Path of Building)',
  'подтверждено (таблица клиента)': 'confirmed (game client table)', 'косвенно (арт гнезда в дереве)': 'indirect (socket art in the tree)',
  'предположение': 'assumption', 'лига добавления, не источник дропа': 'league of introduction, not a drop source', 'нет данных': 'no data',
  'Path of Building или таблица клиента игры': 'Path of Building or a game client table',
  'по данным клиента, но не прямое указание дропа': 'from client data, but not a direct drop statement',
  'угадано по названию или тексту предмета, не проверено': 'guessed from the item name or text, not verified',
  // unique card block
  'Откуда падает': 'Drops from',
  // area names
  'Храм Ваал': 'Vaal Temple', 'Хранилище Атзири': "Atziri's Vault",
  // notes
  'Путь получения убран из игры (по данным Path of Building).': 'This way of obtaining the item was removed from the game (according to Path of Building).',
  'Мастер испытаний в Испытании Хаоса.': 'The Trialmaster in the Trial of Chaos.',
  'Связь по арту гнезда уникального самоцвета (PassiveJewelUniqueArt); точный источник дропа в клиенте не указан.':
    'Linked by the passive tree socket art of the unique jewel (PassiveJewelUniqueArt); the client does not state the exact drop source.',
  'Таблица Expedition2OlrothsLegacyRuneClient перечисляет уникальные, которые связаны с руной Наследия Олрота. Механизм (дроп или превращение) таблица не описывает.':
    "The Expedition2OlrothsLegacyRuneClient table lists uniques tied to the Olroth's Legacy rune. The table does not say how (drop or transformation).",
  'Эти уникальные улучшаются в Храме Атзири с помощью указанного флакона (IncursionUniqueUpgradeComponents).':
    "These uniques are upgraded in the Temple of Atziri with the listed vial (IncursionUniqueUpgradeComponents).",
  'В файлах игры и данных Path of Building нет сведений об источнике. Серверные таблицы дропа клиенту недоступны; вики PoE 2 не используется.':
    'Neither the game files nor the Path of Building data say where this comes from. Server-side drop tables are not available to the client; the PoE 2 wiki is not used.',
  // reasons
  'Выпадает с Rogue Exiles, убитых в контенте Abyss (проверено игроком)': 'Drops from Rogue Exiles killed in Abyss content (checked in game by a player)',
  'Нет данных об источнике': 'No source data',
  'нет данных об источнике': 'no source data',
  // misc
  'Ничего не найдено': 'Nothing found',
}, [
  [/^(Подтверждено|Косвенно|Предположение|Справка|Без данных|Список) · (\d+)$/, (m, a, n) => (({ 'Подтверждено': 'Confirmed', 'Косвенно': 'Indirect', 'Предположение': 'Assumption', 'Справка': 'Info', 'Без данных': 'No data', 'Список': 'List' })[a]) + ' · ' + n],
  [/^Уникальных: (\d+) · подтверждено (\d+)$/, 'Uniques: $1 · confirmed $2'],
  [/^Уникальных: (\d+)$/, 'Uniques: $1'],
  [/^Источников: (\d+)\. Уникальных с известным источником: (\d+) из (\d+)$/, 'Sources: $1. Uniques with a known source: $2 of $3'],
  [/^(.*) — (\d+) уник\.$/, '$1 — $2 uniq.'],
  [/^Изгнанники, убитые в контенте Бездна \(в клиенте их (\d+): (.*)\)\. Что именно они дропают, клиент не говорит; связи ниже взяты из проверки в игре\.$/,
    'Exiles killed in Abyss content ($1 in the client: $2). The client does not say what exactly they drop; the links below come from an in-game check.'],
  [/^IncursionUniqueUpgradeComponents: улучшение флаконом «(.*)»$/, 'IncursionUniqueUpgradeComponents: upgrade with the $1 vial'],
  [/^Арт гнезда в дереве: (.*)$/, 'Socket art in the tree: $1'],
]);
