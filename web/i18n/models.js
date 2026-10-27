// English strings for the section «Модели» (3D model viewer: .smd / .fmt list, info panel).
I18N.add({
  'Загрузка…': 'Loading…',
  'Скачать .glb': 'Download .glb',
  'исходный файл': 'source file',
  'Модели с текстурами': 'Textured models',
}, [
  [/^(\d+) вершин · (\d+) треугольников · LOD: (\d+)$/, '$1 vertices · $2 triangles · LOD: $3'],
  [/^Не удалось открыть модель: (.*)$/, 'Failed to open the model: $1'],
  [/^3D-модель: (.*)$/, '3D model: $1'],
]);
