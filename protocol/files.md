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
