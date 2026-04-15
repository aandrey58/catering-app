# Контракт API

## 1. Назначение документа

Документ фиксирует публичный HTTP-контракт backend-сервиса на базе FastAPI. Контракт используется фронтендом SPA и внешними интеграциями для работы с авторизацией, меню, выбором блюд и обратной связью.

## 2. Общие положения

Сервис работает на FastAPI и по умолчанию доступен по адресу `http://127.0.0.1:8000`. Все маршруты, кроме `GET /health`, `POST /login` и `POST /sync_from_sheets`, требуют валидный JWT в заголовке `Authorization: Bearer <access_token>`.

При корректной настройке интеграции с Google Sheets backend при старте выполняет импорт снимка данных в SQLite (пользователи, меню, недели, выборы, обратная связь). Ручной импорт также доступен через `POST /sync_from_sheets` при заданном `SHEETS_SYNC_TOKEN`.

## 3. Базовые параметры

- URL локально по умолчанию: `http://127.0.0.1:8000`
- Тип контента для JSON: `application/json`
- CORS: настраивается (`*` в dev)
- Заголовок авторизации (защищённые маршруты): `Authorization: Bearer <access_token>`
- Срок жизни токена: **30 дней** по умолчанию (`JWT_EXPIRE_DAYS` на сервере)

## 4. Эндпоинты

### `GET /health`

- Ответ `200`: plain text `OK`

### `POST /login`

- Запрос:

```json
{
  "login": "user",
  "password": "secret"
}
```

- Ответ `200`:

```json
{
  "status": "ok",
  "login": "user",
  "note": "optional-note",
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

- Ответ `401` (FastAPI заворачивает ошибку в `detail`):

```json
{
  "detail": {
    "status": "error",
    "message": "Неверный логин или пароль"
  }
}
```

### `GET /me`

- Заголовки: `Authorization: Bearer ...`
- Ответ `200`:

```json
{
  "login": "user",
  "note": "optional-note"
}
```

### `GET /weeks`

- Заголовки: `Authorization: Bearer ...`
- Ответ `200`:

```json
{
  "current": "text",
  "next": "text",
  "week1_enabled": true,
  "week2_enabled": true
}
```

### `GET /menu`

- Заголовки: `Authorization: Bearer ...`
- Ответ `200`: как и раньше — массив строк (сетка меню из локальной БД настроек)

### `GET /menu_enabled`

- Заголовки: `Authorization: Bearer ...`
- Ответ `200`:

```json
{
  "enabled": true
}
```

### `POST /save`

- Заголовки: `Authorization: Bearer ...`
- Запрос (логин берётся из токена, в body не передаётся):

```json
{
  "day": "mon",
  "selections": {
    "breakfast": "",
    "soup": "",
    "hot": "",
    "side": "",
    "salad": "",
    "dessert": ""
  }
}
```

- Ответ `200`:

```json
{
  "success": true,
  "message": "Данные успешно сохранены"
}
```

### `POST /delete`

- Заголовки: `Authorization: Bearer ...`
- Запрос:

```json
{
  "day": "mon"
}
```

- Ответ `200`:

```json
{
  "deleted": true,
  "row": 7
}
```

### `POST /get_selections`

- Заголовки: `Authorization: Bearer ...`
- Запрос:

```json
{
  "day": "mon"
}
```

- Ответ `200`:

```json
{
  "selections": {
    "breakfast": "",
    "soup": "",
    "hot": "",
    "side": "",
    "salad": "",
    "dessert": ""
  }
}
```

- Если не найдено:

```json
{
  "selections": null
}
```

### `POST /save_feedback`

- Заголовки: `Authorization: Bearer ...`
- Запрос:

```json
{
  "rating": 5,
  "feedback_text": "Great!"
}
```

- Ответ `200`:

```json
{
  "success": true,
  "message": "Фидбэк успешно сохранён"
}
```

### `POST /get_feedback`

- Заголовки: `Authorization: Bearer ...`
- Тело запроса: **пустой JSON** `{}` (или можно без body, но для единообразия лучше `{}`)
- Ответ `200`:

```json
{
  "feedback": {
    "rating": 5,
    "feedback_text": "Great!"
  }
}
```

- Если не найдено:

```json
{
  "feedback": null
}
```

### `POST /delete_feedback`

- Заголовки: `Authorization: Bearer ...`
- Тело запроса: **пустой JSON** `{}`
- Ответ `200`:

```json
{
  "deleted": true,
  "row": 10
}
```

### `POST /sync_from_sheets`

- **Без** заголовка `Authorization: Bearer`.
- Заголовок: `X-Sheets-Sync-Token: <то же значение, что и SHEETS_SYNC_TOKEN в env бэкенда>`. Если `SHEETS_SYNC_TOKEN` не задан, маршрут вернёт **404** (синхронизация выключена).
- Тело запроса: необязательно, можно `{}`.
- Ответ `200`:

```json
{
  "synced": true
}
```

- `synced: false` означает, что импорт был пропущен (нет credentials / нет ID таблицы) или не удалось прочитать снимок (см. логи сервера).
- При успехе сбрасывается in-memory кэш чтений меню/недель.
