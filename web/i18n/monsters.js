// English strings for the Monsters section.
(function () {
  const kvMap = { 'Тип': 'Type', 'Категория': 'Category', 'Босс': 'Boss', 'Основная рука': 'Main hand', 'Вторая рука': 'Off hand' };
  const kv = k => (m) => m.split(' · ').map(p => { const i = p.indexOf(': '); if (i > 0 && kvMap[p.slice(0, i)]) return kvMap[p.slice(0, i)] + p.slice(i); return kvMap[p] || p; }).join(' · ');
  I18N.add({
    'Скорость движения': 'Movement speed', 'Размер объекта': 'Object size', 'Масштаб модели, %': 'Model scale, %', 'Мин. дистанция атаки': 'Min. attack distance',
    'Макс. дистанция атаки': 'Max. attack distance', 'Опыт, %': 'Experience, %', 'Урон, %': 'Damage, %', 'Здоровье, %': 'Life, %', 'Скорость атаки, мс': 'Attack speed, ms',
    'Мин. дальность агро': 'Min. aggro range', 'Макс. дальность агро': 'Max. aggro range', 'Порог стойкости': 'Poise threshold', 'Шанс крита': 'Critical chance',
    'Обзор': 'Overview', 'Анимации': 'Animations', 'Озвучка': 'Audio',
    'Студия': 'Studio', 'Игровой вид': 'Game view', 'Земля, вид сверху': 'Ground, top view', 'Сцена': 'Scene',
    'Загрузка монстра…': 'Loading monster…', 'Воспроизвести': 'Play', 'Сохранить WAV': 'Save WAV', 'Сохранить': 'Save', 'Сохранить OGG': 'Save OGG',
    'Экспорт': 'Export', 'Жизнь': 'Life', 'Урон': 'Damage', 'Скорость': 'Speed', 'Опыт': 'Experience', 'Размер': 'Size', 'Дистанция атаки': 'Attack distance',
    'Оружие и снаряжение': 'Weapons and gear', 'показано на модели': 'shown on the model', 'не удалось прикрепить к скелету': 'could not be attached to the skeleton',
    'без отдельной модели': 'no separate model', 'Своего оружия в данных нет': 'No weapons of its own in the data', 'Параметры': 'Parameters',
    'провокация': 'taunt', 'Служебный эффект без описания': 'Internal effect with no description', 'У монстра нет собственных умений в данных': 'The monster has no skills of its own in the data',
    'Состояния → клипы': 'States → clips', 'Все клипы скелета': 'All skeleton clips', 'Нет клипов (у монстра нет собственного скелета)': 'No clips (the monster has no skeleton of its own)',
    '⬇ Скачать всё одним архивом': '⬇ Download everything as one archive', 'Банк звуков этого монстра не найден': 'No sound bank found for this monster',
    'Звуки по анимациям': 'Sounds by animation', 'Событий звука нет': 'No sound events',
    'Поведение (.act)': 'Behaviour (.act)', 'Объекты (.ao)': 'Objects (.ao)', 'Искусственный интеллект (.ais)': 'Artificial intelligence (.ais)', 'Модель, скелет, эффекты': 'Model, skeleton, effects',
    'Оружие 1': 'Weapon 1', 'Оружие 2': 'Weapon 2', 'Спина': 'Back', 'Шлем': 'Helmet',
    'Тип урона': 'Damage type', 'Шанс крита': 'Critical chance', 'Множитель урона': 'Damage multiplier', 'Урон за срабатывание': 'Damage per use', 'Время применения': 'Cast time',
    'Перезарядка': 'Cooldown', 'Заряды': 'Charges', 'Скорость атаки, %': 'Attack speed, %', 'Типы умения': 'Skill types', 'Физический (атака)': 'Physical (attack)',
    'Физический': 'Physical', 'Огонь': 'Fire', 'Холод': 'Cold', 'Молния': 'Lightning', 'Хаос': 'Chaos',
    'Для этого умения в данных нет клипа': 'No animation clip for this skill in the data', 'Звуков на этой анимации нет': 'No sounds on this animation',
    'Акт': 'Act', 'Все акты и зоны': 'All acts and zones', 'Акт 1': 'Act 1', 'Акт 2': 'Act 2', 'Акт 3': 'Act 3', 'Акт 4': 'Act 4', 'Акт 5 (в файлах)': 'Act 5 (in files)',
    'Интерлюдия': 'Interlude', 'Эндгейм': 'Endgame', 'Лиги': 'Leagues', 'Без зоны': 'No zone',
  }, [
    [/^Тип: .*$/, kv()], [/^Основная рука: .*$/, kv()], [/^Вторая рука: .*$/, kv()], [/^Категория: .*$/, kv()],
    [/^Босс( · .*)?$/, kv()],
    [/Акт \d|Без зоны|Эндгейм|Лиги|Интерлюдия/, m => m.replace(/Акт (\d)/g, 'Act $1').replace('(в файлах)', '(in files)').replace('Без зоны', 'No zone').replace('Эндгейм', 'Endgame').replace('Лиги', 'Leagues').replace('Интерлюдия', 'Interlude')],
    [/^Анимация \((\d+)\)$/, 'Animation ($1)'], [/^Звуки \((\d+)\)$/, 'Sounds ($1)'],
    [/^Одежда, волосы, броня \((\d+)\)$/, 'Clothes, hair, armour ($1)'], [/^показано на модели: (\d+)$/, 'shown on the model: $1'],
    [/^на теле$/, 'on the body'], [/^(.*) · на теле$/, '$1 · on the body'],
    [/^Время применения: (.*) с$/, 'Cast time: $1 s'], [/^· анимация: (.*)$/, '· animation: $1'], [/^(.*) · анимация: (.*)$/, '$1 · animation: $2'], [/^(.*)\bанимация: (.*)$/, '$1animation: $2'],
    [/^Время применения: (.*) · анимация: (.*)$/, 'Cast time: $1 · animation: $2'],
    [/^контакт: (.*) с$/, 'contact: $1 s'], [/^Тип звука оружия: (.*)$/, 'Weapon sound type: $1'],
    [/^Звуки монстра \((\d+)\)$/, 'Monster sounds ($1)'], [/^Реплики \((\d+)\)$/, 'Voice lines ($1)'],
    [/^Банки: (.*) · звук собирается из игрового банка FMOD при первом нажатии ▶\.$/, 'Banks: $1 · the sound is assembled from the game FMOD bank on first ▶ press.'],
    [/^([\w.]+) · ([\d.]+) с · (.*)$/, '$1 · $2 s · $3'], [/^(\d+(?:\.\d+)?) с · (.*)$/, '$1 s · $2'], [/^(\d+(?:\.\d+)?) с$/, '$1 s'],
    [/^Папка (.*)$/, 'Folder $1'], [/^(Поведение|Объекты|Искусственный интеллект|Модель, скелет, эффекты)(.*) \((\d+)\)$/, (m, a, b, n) => ({ 'Поведение': 'Behaviour', 'Объекты': 'Objects', 'Искусственный интеллект': 'Artificial intelligence', 'Модель, скелет, эффекты': 'Model, skeleton, effects' })[a] + b + ' (' + n + ')'],
  ]);
})();
