# 🌐 Unekov.help — AI OSINT Analytical Bot

> Production-ready Telegram бот для поиска и анализа данных с AI.
> Stack: Python 3.12 · aiogram 3.x · FastAPI · PostgreSQL · Redis · Docker

---

## 🚀 Быстрый старт

### 1. Клонировать и настроить

```bash
cp .env.example .env
# Заполнить .env: BOT_TOKEN, OPENAI_API_KEY, SECRET_KEY
```

### 2. Запуск через Docker (рекомендуется)

```bash
docker-compose up -d --build
```

### 3. Локальный запуск (dev)

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

pip install -r requirements.txt

# Запустить PostgreSQL и Redis локально, затем:
alembic upgrade head
python main.py
```

---

## 📁 Структура проекта

```
osint-ai-bot/
├── bot/
│   ├── handlers/          # Telegram handlers
│   │   ├── start.py       # /start, главное меню
│   │   ├── search.py      # Поиск данных
│   │   ├── tools.py       # Раздел Tools
│   │   ├── tg_users.py    # Раздел TelegramUsers
│   │   ├── databases.py   # Раздел Databases (BD)
│   │   ├── profile.py     # Профиль, баланс, история
│   │   ├── mode.py        # Режимы работы
│   │   └── export.py      # Экспорт JSON/PDF
│   ├── keyboards/         # Inline клавиатуры
│   ├── middlewares/       # Auth, Rate Limit
│   └── ui_texts.py        # Все тексты (cyberpunk стиль)
├── core/
│   ├── ai/                # OpenAI сервис
│   ├── search/            # UniversalSearch, FileScanner, Fuzzy
│   └── tokens/            # Система токенов
├── db/
│   ├── models/            # SQLAlchemy модели
│   ├── repositories/      # Repository pattern
│   └── migrations/        # Alembic миграции
├── api/
│   └── routers/           # FastAPI endpoints
├── config/                # Настройки
├── docker/                # Dockerfile, nginx.conf
├── docker-compose.yml
└── main.py                # Entry point
```

---

## 🗄️ Разделы бота

| Раздел | Описание |
|--------|----------|
| 🔍 Поиск | Поиск по всем БД: имя, username, email, телефон, TG ID |
| 🤖 AI Анализ | Анализ результатов, confidence score, связи |
| 🗄️ Databases (BD) | Подключённые базы данных, загрузка файлов |
| 🛠️ Tools | Инструменты: TG Search, Email/Phone Lookup, File Scanner, Export |
| ✈️ TelegramUsers | Поиск в базе Telegram пользователей |
| 📜 История | История запросов с результатами |
| 👤 Профиль | ID, статистика, баланс, подписка |
| 💎 Подписка | Free / Premium / Enterprise |
| 🎮 Режим | Lite / Standard / Deep Scan / Ultra AI |
| 🪙 Баланс | Токены, транзакции, дневной бонус |

---

## 🎮 Режимы работы

| Режим | Стоимость | Описание |
|-------|-----------|----------|
| ⚡ Lite | 5 токенов | Быстрый поиск |
| 🔵 Standard | 10 токенов | Баланс качества |
| 🟣 Deep Scan | 25 токенов | Расширенный анализ + semantic |
| 🔴 Ultra AI | 50 токенов | Multi-step reasoning |

---

## 💎 Тарифы

| Тариф | Токены/мес | Режимы | Цена |
|-------|-----------|--------|------|
| Free | 100 | Lite, Standard | 0$ |
| Premium | 2000 | + Deep Scan | 9.99$/мес |
| Enterprise | 10000 | + Ultra AI | 49.99$/мес |

---

## 🔍 Как работает AI Поиск

Главная кнопка **🤖 AI Поиск** — пишешь любой запрос, бот:

1. Ищет во **всех** подключённых источниках одновременно:
   - `TelegramUsers DB` — отдельная таблица TG пользователей
   - `IndexedRecords` — все проиндексированные файлы:
     - `bif BD/` — Telegram EyeOfGod 774k, Госуслуги ЕСИА, Convoy Donations, Sberbank, и др.
     - `Telegram Users/` — 520k пользователей
     - `Telegram_Chats_2022_63kk/` — 63 млн записей чатов
   - Загруженные пользователем файлы (CSV/JSON/TXT)
2. **Fuzzy matching** (rapidfuzz) ранжирует по релевантности
3. **Semantic re-ranking** (OpenAI embeddings) для Deep/Ultra режимов
4. **AI анализ** (GPT-4o-mini) формирует отчёт с confidence score, связями, risk level
5. Результат сохраняется в историю, токены списываются

## 📦 Индексация файлов

### Автоматически при старте (через /admin_index):
```
/admin_index  — запустить индексацию (только для admin)
```

### Вручную через скрипт:
```bash
cd osint-ai-bot
python scripts/index_files.py
```

Скрипт индексирует все файлы из папок рядом с проектом:
- `../bif BD/` — CSV, XLSX, TXT, SQL файлы
- `../Telegram Users/` — TXT файлы
- `../Telegram_Chats_2022_63kk/` — папки с данными чатов

---

## 🛠️ Инструменты (Tools)

- **Telegram User Search** — поиск по username/ID/имени/телефону
- **Group/Channel Scanner** — анализ участников (Premium)
- **Email Lookup** — поиск по email
- **Phone Lookup** — поиск по телефону
- **Cross-Database Search** — поиск во всех БД (Premium)
- **AI Profile Builder** — AI профиль сущности (Premium)
- **Connection Mapper** — карта связей (Enterprise)
- **File Scanner** — поиск в загруженных файлах
- **Export JSON/PDF** — экспорт отчётов

---

## ⚙️ ENV переменные

```env
BOT_TOKEN=           # Telegram Bot Token
WEBHOOK_URL=         # https://yourdomain.com (для production)
DATABASE_URL=        # postgresql+asyncpg://...
REDIS_URL=           # redis://redis:6379/0
OPENAI_API_KEY=      # OpenAI API Key
SECRET_KEY=          # JWT secret (min 32 chars)
ADMIN_IDS=           # Telegram IDs через запятую
```

---

## 📡 API Endpoints

```
GET  /health                    — статус
POST /webhook                   — Telegram webhook
GET  /api/v1/users/me           — профиль (JWT)
GET  /api/v1/users/history      — история (JWT)
POST /api/v1/search/            — поиск (JWT)
GET  /api/v1/admin/users        — список юзеров (admin)
POST /api/v1/admin/tokens/grant — выдать токены (admin)
POST /api/v1/admin/users/{id}/ban — бан (admin)
```

---

## 📦 Добавление данных в TelegramUsers

```python
# Пример импорта данных
from db.database import AsyncSessionLocal
from db.models import TelegramUser

async with AsyncSessionLocal() as session:
    user = TelegramUser(
        tg_id=123456789,
        username="example",
        first_name="John",
        phone="+79001234567",
        source="public_group",
        source_group="@some_group",
    )
    session.add(user)
    await session.commit()
```

---

## 🔒 Безопасность

- Rate limiting через Redis (2 сек между запросами, 10/мин)
- JWT авторизация для API
- Audit logs всех действий
- Бан система
- Шифрование секретов через ENV
- Поиск только в разрешённых источниках
