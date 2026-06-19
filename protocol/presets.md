# Пресеты: аватары, стикеры, эмодзи

MAX предоставляет API для получения предустановленных аватаров,
стикеров и эмодзи.

## GET_PRESET_AVATARS (opcode 25)

Получение списка предустановленных аватаров для профиля.

### Запрос

```json
{}
```

Payload может быть пустым объектом. Поля `count` и `offset` игнорируются —
всегда возвращается полный список.

### Ответ

```json
{
  "presetAvatars": [
    {
      "name": "Антро",
      "avatars": [
        {
          "url": "https://i.oneme.ru/i?r=...",
          "id": 3778498
        },
        {
          "url": "https://i.oneme.ru/i?r=...",
          "id": 3722368
        }
      ]
    }
  ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `presetAvatars` | array | Массив категорий аватаров |
| `presetAvatars[].name` | string | Название категории (например, "Антро") |
| `presetAvatars[].avatars` | array | Массив аватаров в категории |
| `avatars[].url` | string | URL изображения аватара |
| `avatars[].id` | int | ID аватара |

### Особенности

- Изображения хранятся на `i.oneme.ru`
- Категории включают различные темы: "Антро" (антропоморфные),
  животные, абстракции и т.д.
- ID аватара можно использовать для установки аватара профиля

## STICKER_SYNC (opcode 26)

Пагинированная синхронизация наборов стикеров. Возвращает список ID
наборов (sticker sets) с маркером для дозагрузки.

### Запрос

```json
{
  "sectionId": "NEW_STICKER_SETS",
  "from": 5,
  "count": 100
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `sectionId` | string | ID секции (например, `"NEW_STICKER_SETS"`) |
| `from` | int | Смещение (начальная позиция) |
| `count` | int | Количество элементов на странице |

### Ответ

```json
{
  "stickerSets": [216398, 216910, ...
  ],
  "marker": 105
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `stickerSets` | array[int] | ID наборов стикеров |
| `marker` | int | Маркер для следующей страницы. `0` = конец |

### Пагинация

- `marker != 0` → есть ещё страницы. Передать `from: marker` в следующий запрос.
- `marker = 0` → конец списка.
- Всего ~274 набора, загружаются за 3 запроса (100+100+69).

### Пример пагинации

| Запрос `from` | Ответ `marker` |
|---------------|----------------|
| 5 | 105 |
| 105 | 205 |
| 205 | 0 (конец) |

## STICKER_DATA (opcode 27)

Загрузка данных стикеров и анимодзи. Имеет 4 подтипа, запрашиваемых
последовательно.

### Общий формат запроса

```json
{
  "type": "STICKER",
  "sync": 0
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | string | Тип данных (см. таблицу подтипов) |
| `sync` | int | `0` — полная загрузка. При повторных запросах — timestamp из предыдущего ответа (дельта-обновление) |

### Подтипы

| Тип | Назначение | Ключевые поля ответа |
|-----|------------|----------------------|
| `STICKER` | Наборы стикеров | `stickersOrder[]`, `sections[]` (STICKER_SETS + RECENTS), `stickersUpdates` |
| `FAVORITE_STICKER` | Избранные стикеры | `stickersOrder[]`, `sections[]` (пустые), `stickerSetsUpdates` |
| `REACTION` | Реакции и анимодзи | `sections[{reactions[], updateTime}]`, `animojiUpdates{}` |
| `ANIMOJI_SET` | Наборы анимодзи | `sections[{animojiSetIds[]}]`, `animojiSetUpdates{}` |

### Пример ответа (STICKER)

```json
{
  "stickersOrder": [],
  "sections": [
    {
      "stickerSets": [216654, 218958, ...],
      "marker": 5,
      "collapsed": true,
      "id": "NEW_STICKER_SETS",
      "type": "STICKER_SETS",
      "title": "Новые наборы",
      "totalCount": 274
    },
    {
      "stickerSets": [],
      "recentsList": [],
      "emojiList": [],
      "recentEmojiList": [{ "type": "unicode", "value": "🔥" }],
      "id": "RECENTS",
      "type": "RECENTS",
      "title": "Часто используемые"
    }
  ],
  "sync": 1775042080790
}
```

### Поля секции STICKER_SETS

| Поле | Тип | Описание |
|------|-----|----------|
| `stickerSets` | array[int] | ID наборов стикеров в этой секции |
| `marker` | int | Маркер внутри секции (детальная пагинация) |
| `collapsed` | bool | Секция свёрнута в UI |
| `id` | string | ID секции |
| `type` | string | `"STICKER_SETS"` или `"RECENTS"` |
| `title` | string | Отображаемое название |
| `totalCount` | int | Общее количество наборов |

### Пример ответа (REACTION)

```json
{
  "sections": [
    {
      "reactions": [1, 2, 3, ...],
      "updateTime": 1761577200000,
      "id": "section_reactions",
      "title": "Реакции"
    }
  ],
  "animojiUpdates": {
    "1": 1761577200000,
    "125": 1761577200000,
    "7": 1761577200000
  }
}
```

### Механизм дельта-обновлений

Поле `sync` в ответе содержит timestamp. При следующем запросе его
можно передать как `sync` — сервер вернёт только изменения с этого
момента. Работает для всех 4 подтипов.

## ANIMOJI_AND_STICKER_GET (opcode 28)

Получение полных объектов анимодзи и стикеров по их ID.
Загружаются только те объекты, которые ещё не скачаны
(определяется по `animojiUpdates` из opcode 27).

### Запрос

```json
{
  "type": "ANIMOJI",
  "ids": [1, 125, 7, 31, 3, 20]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | string | Тип объекта: `"ANIMOJI"` или `"STICKER"` |
| `ids` | array[int] | ID объектов для загрузки |

### Формат ANIMOJI-объекта

```json
{
  "id": 1,
  "emoji": "👍",
  "setId": 1,
  "updateTime": 1761577200000,
  "iconUrl": "https://i.oneme.ru/sticker/...",
  "lottieUrl": "https://cdn.oneme.ru/sticker/...",
  "lottiePlayUrl": "https://cdn.oneme.ru/sticker/..."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID анимодзи |
| `emoji` | string | Соответствующий emoji-символ |
| `setId` | int | ID набора анимодзи |
| `updateTime` | int | Timestamp последнего обновления |
| `iconUrl` | string | URL статической иконки |
| `lottieUrl` | string | URL Lottie-анимации |
| `lottiePlayUrl` | string | URL Lottie-анимации для воспроизведения |

### Формат STICKER-объекта

```json
{
  "id": 476341,
  "setId": 63157,
  "type": "LOTTIE",
  "fileId": 77335,
  "authorType": "USER",
  "width": 170,
  "height": 170,
  "tags": ["👋"],
  "url": "https://i.oneme.ru/sticker/...",
  "lottieUrl": "https://cdn.oneme.ru/sticker/..."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID стикера |
| `setId` | int | ID набора стикеров |
| `type` | string | Тип стикера: `"LOTTIE"`, `"IMAGE"`, `"WEBP"`, `"ANIMATED_WEBP"` |
| `fileId` | int | ID файла на сервере |
| `authorType` | string | `"USER"` или `"OFFICIAL"` |
| `width` | int | Ширина в пикселях |
| `height` | int | Высота в пикселях |
| `tags` | array[string] | Теги/эмодзи для поиска |
| `url` | string | URL статического изображения |
| `lottieUrl` | string | URL Lottie-анимации |

### Полный поток загрузки стикеров

1. **opcode 27 (type: STICKER)** — получить структуру разделов
2. **opcode 26** — пагинированная синхронизация ID наборов
3. **opcode 27 (type: REACTION)** — получить `animojiUpdates`
4. **opcode 27 (type: ANIMOJI_SET)** — получить `animojiSetUpdates`
5. **opcode 27 (type: FAVORITE_STICKER)** — получить избранные
6. **opcode 28 (type: ANIMOJI)** — загрузить нескачанные анимодзи
7. **opcode 28 (type: STICKER)** — загрузить нескачанные стикеры

На практике в HAR: opcode 27 (4 типа) → opcode 26 (3 запроса) →
opcode 28 (74 animoji + 1 дозапрос + 1 sticker).
