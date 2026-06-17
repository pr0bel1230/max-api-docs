# Контакты и профиль пользователя

Информация о пользователях и контактах.

## Профиль пользователя

Данные текущего пользователя возвращаются в ответе LOGIN (opcode 19)
в поле `profile`:

```json
{
  "profile": {
    "contact": {
      "id": 3260455,
      "names": [
        {"name": "Имя Фамилия", "type": "FULL_NAME"}
      ],
      "about": "статус пользователя",
      "phones": [
        {"number": "+71234567890", "type": "MOBILE"}
      ],
      "picture": {
        "url": "https://...",
        "base": "..."
      },
      "registrationDate": "..."
    },
    "settings": {
      "notifications": true,
      "theme": "light",
      ...
    },
    "subscription": {
      "expires": "...",
      "active": true,
      ...
    }
  }
}
```

### Contact

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Уникальный ID пользователя |
| `names` | array | Массив имён с типами |
| `names[].name` | string | Имя |
| `names[].type` | string | `FULL_NAME`, `FIRST_NAME`, `LAST_NAME` |
| `about` | string | Статус ("недоступен" и т.д.) |
| `phones` | array | Номера телефонов |
| `picture` | object | Аватар: url и base64 миниатюра |

## GET_CONTACTS (opcode 32)

Получение информации о контактах по их ID.

### Запрос

```json
{
  "contactIds": [3260455, 3260456, 3260457]
}
```

### Ответ

```json
{
  "contacts": [
    {
      "id": 3260455,
      "names": [{"name": "Имя", "type": "FULL_NAME"}],
      "about": "статус",
      "phones": [{"number": "+71234567890", "type": "MOBILE"}],
      "picture": {"url": "https://...", "base": "..."}
    }
  ]
}
```

### Особенности

- Можно запрашивать несколько контактов за раз
- Если контакт не найден — вероятно, просто отсутствует в ответе
- Формат каждого контакта совпадает с форматом `contact` в профиле
