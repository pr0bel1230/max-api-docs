# Файлы: загрузка и отправка

MAX поддерживает отправку файлов через два последовательных этапа:
HTTP-загрузка на файловое хранилище → прикрепление к сообщению.

## Полный цикл загрузки

```
1. FILE_UPLOAD (87)   → получить URL для загрузки
2. HTTP POST          → загрузить файл по полученному URL
3. NOTIF_ATTACH (136) → дождаться подтверждения загрузки
4. MSG_SEND (64)      → отправить сообщение с attached файлом
```

## 1. FILE_UPLOAD (opcode 87)

Запрос на получение URL для загрузки файла.

### Запрос

```json
{
  "name": "photo.jpg",
  "size": 1048576,
  "ext": "jpg",
  "count": 1
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Имя файла с расширением |
| `size` | int | Размер в байтах |
| `ext` | string | Расширение файла без точки |
| `count` | int | Количество файлов (обычно 1) |

### Ответ

```json
{
  "info": [
    {
      "url": "https://file-ms.oneme.ru/upload/...",
      "fileId": "UUID строки",
      "token": "токен для прикрепления",
      "name": "photo.jpg"
    }
  ]
}
```

| Поле | Описание |
|------|----------|
| `url` | URL для HTTP-загрузки файла |
| `fileId` | ID файла на сервере |
| `token` | Токен для последующего прикрепления к сообщению |

## 2. HTTP Upload

Загрузка файла на полученный URL через multipart/form-data POST:

```python
import requests

resp = requests.post(upload_url, files={
    "file": (file_name, open(file_path, "rb"), "application/octet-stream")
})
```

Успешная загрузка: HTTP 200.

## 3. NOTIF_ATTACH (opcode 136)

После успешной загрузки сервер присылает push-уведомление:

```
cmd=0 opcode=136
```

Это подтверждение, что файл закреплён за сессией и готов
к прикреплению в сообщение.

**Важно:** Уведомление приходит асинхронно. Нужно читать входящие
сообщения из сокета и ждать opcode 136.

```python
deadline = time.time() + 30
while time.time() < deadline:
    resp = recv()
    if resp.get("opcode") == 136:
        break  # файл готов
```

## 4. MSG_SEND с аттачем

После получения NOTIF_ATTACH можно отправлять сообщение с вложением:

```json
{
  "chatId": 7268926,
  "message": {
    "text": "Смотри файл",
    "cid": 1734567890123,
    "elements": [],
    "attaches": [{
      "_type": "FILE",
      "fileId": "UUID из FILE_UPLOAD",
      "token": "токен из FILE_UPLOAD",
      "name": "photo.jpg",
      "size": 1048576
    }]
  },
  "notify": true
}
```

### Поле attaches

| Поле | Тип | Описание |
|------|-----|----------|
| `_type` | string | Тип вложения: `FILE` |
| `fileId` | string | UUID файла из FILE_UPLOAD |
| `token` | string | Токен из FILE_UPLOAD |
| `name` | string | Имя файла |
| `size` | int | Размер в байтах |

## UNSUPPORTED-вложения (голосовые сообщения)

Голосовые сообщения приходят в истории с `_type: "UNSUPPORTED"`.
**Важно:** тип вложения — именно `UNSUPPORTED`, а не `AUDIO`.

```json
{
  "_type": "UNSUPPORTED",
  "duration": 94760,
  "wave": "data:image/webp;base64,ZXho...",
  "audioId": 1524997357593,
  "token": "f9LHodD0cOL7Wb-jd-9JPg46oS1ukLzEMJnrVS7dObsDQXzNFaS_WqqD2R8YQHqH7pP_vQU5l64RNu0JGFzc"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `_type` | string | Всегда `"UNSUPPORTED"` |
| `duration` | int | Длительность в миллисекундах |
| `wave` | string | WebP-изображение波形 (визуализация звука) |
| `audioId` | int | ID аудиофайла |
| `token` | string | Токен для доступа к аудио |

### Особенности

- Тип `AUDIO` в attachTypes GET_MEDIA (51) существует, но в реальных
  сообщениях не встречен — голосовые сообщения передаются как `UNSUPPORTED`
- `wave` — это не аудио, а визуализация волны в формате WebP (base64)
- `duration` даётся в миллисекундах (94760 мс ≈ 1.5 минуты)
- Полный цикл воспроизведения голосового сообщения не исследован
  (требуется GET_VIDEO_URL? или другой endpoint)

## Формат в GET_HISTORY

В истории сообщений файлы отображаются в поле `attaches`:

```json
{
  "attaches": [
    {
      "fileName": "photo.jpg",
      "fileUrl": "https://...",
      "fileSize": 1048576,
      "_type": "FILE",
      "fileId": "UUID"
    }
  ]
}
```

Формат может отличаться от запроса — после загрузки сервер
заполняет дополнительные поля (fileUrl и т.д.).

## CONTROL-вложения

Системные события передаются в виде вложений с `_type: "CONTROL"`
внутри обычных `USER`-сообщений. Типы `SERVICE` и `SYSTEM` не существуют.

### Пример: botStarted

При старте бота в чате приходит `USER`-сообщение с CONTROL-вложением:

```json
{
  "id": 116777777777777777,
  "type": "USER",
  "text": "",
  "attaches": [
    {
      "_type": "CONTROL",
      "action": "botStarted",
      "deleted": true
    }
  ],
  "deleted": true
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `_type` | string | Всегда `"CONTROL"` |
| `action` | string | Тип события (например, `"botStarted"`) |
| `deleted` | bool | Признак, что это служебное событие (всегда `true`) |

**Особенности:**
- Сообщение с CONTROL имеет пустой `text`
- Наличие `deleted: true` не означает, что сообщение удалено — это
  маркер того, что оно служебное и не должно отображаться как обычное
- Тип сообщения остаётся `USER` — не `SERVICE` и не `SYSTEM`
- При удалении CONTROL-сообщения срабатывает тот же MSG_DELETE (66)

## CALL-вложения (звонки)

Звонковые события (начало, завершение, пропущенный звонок) передаются
в виде вложений с `_type: "CALL"` внутри обычных USER-сообщений.

### Пример (в истории сообщений)

```json
{
  "_type": "CALL",
  "callType": "AUDIO",
  "conversationId": "8774B04E-6436-4F47-A145-2043555F4E18",
  "duration": 25289,
  "hangupType": "HUNGUP",
  "contactIds": [6236697]
}
```

### Поля CALL

| Поле | Тип | Описание |
|------|-----|----------|
| `_type` | string | Всегда `"CALL"` |
| `callType` | string | `"AUDIO"` или `"VIDEO"` |
| `conversationId` | string | UUID звонка |
| `duration` | int | Длительность в секундах (0 для пропущенных) |
| `hangupType` | string | Причина завершения: `"HUNGUP"`, `"REJECTED"`, `"CANCELED"`, `"TIMEOUT"` |
| `contactIds` | array[int] | Участники звонка |

### Значения hangupType

| Значение | Описание |
|----------|----------|
| `HUNGUP` | Звонок завершён нормально (кто-то положил трубку) |
| `REJECTED` | Вызов отклонён |
| `CANCELED` | Вызов отменён инициатором |
| `TIMEOUT` | Вызов не принят (таймаут) |

### Получение истории звонков

Опкод 79 (CALL_HISTORY) возвращает только сообщения с CALL-вложениями
из указанного чата — см. [calls.md](calls.md).

## GET_VIDEO_URL (opcode 83)

Получение URL для просмотра видео из сообщения.

### Запрос

```json
{
  "videoId": 16508201099037,
  "token": "f9LHodD0cOJn7Q01...",
  "chatId": -72842705805946,
  "messageId": "116765909829571763"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `videoId` | int | ID видео |
| `token` | string | Токен видео (опционально) |
| `chatId` | int | ID чата |
| `messageId` | string | ID сообщения с видео |

### Ответ

```json
{
  "EXTERNAL": "https://m.ok.ru/video/...",
  "cache": true,
  "MP4_720": "https://maxvd652.okcdn.ru/?expires=...&type=3&sig=..."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `EXTERNAL` | string | Ссылка на внешний плеер (m.ok.ru) |
| `cache` | bool | Флаг кеширования |
| `MP4_720` | string | Прямая ссылка на MP4 (HD 720p), CDN okcdn.ru |

### Особенности

- Поле `token` может быть пустым — сервер всё равно возвращает ссылки
- `MP4_720` — прямая ссылка на файл с ограничением по времени (`expires`)
- `EXTERNAL` ведёт на веб-плеер m.ok.ru (OK.ru)
- CDN — `maxvd652.okcdn.ru` (суффикс может меняться)
