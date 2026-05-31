# 🎬 Movie Bot - Telegram бот для портфолио фильмов

Telegram бот с Mini App для ведения личного портфолио фильмов, сериалов и аниме.

## 🚀 Возможности

- ✍️ Добавление фильмов через чат с ботом
- 🎨 Красивое портфолио с обложками в Mini App
- 📊 Статистика просмотров
- 🔍 Автоматический поиск обложек через TMDB
- 👥 Общие портфолио (в разработке)

## 📦 Установка

### 1. Установите Python 3.9+

### 2. Клонируйте проект и установите зависимости

```bash
cd movie-bot
pip install -r requirements.txt
```

### 3. Настройте переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

**Получение токенов:**

1. **Telegram Bot Token**: 
   - Напишите @BotFather в Telegram
   - Отправьте `/newbot`
   - Следуйте инструкциям
   - Скопируйте токен в `.env`

2. **TMDB API Key**:
   - Зарегистрируйтесь на https://www.themoviedb.org/
   - Перейдите в Settings → API
   - Скопируйте API Key в `.env`

### 4. Запустите проект

**Терминал 1 - API сервер:**
```bash
python api/main.py
```

**Терминал 2 - Telegram бот:**
```bash
python bot/bot.py
```

## 📱 Использование

1. Найдите своего бота в Telegram
2. Отправьте `/start`
3. Пишите название фильма и оценку:
   - `Интерстеллар 10`
   - `Во все тяжкие 9.5`
   - `Атака титанов 10`
4. Откройте портфолио через кнопку "📱 Открыть портфолио"

## 🏗️ Структура проекта

```
movie-bot/
├── bot/                    # Telegram бот
│   ├── bot.py             # Основной файл бота
│   └── tmdb_api.py        # Работа с TMDB API
├── api/                    # FastAPI сервер
│   └── main.py            # API endpoints
├── miniapp/               # Telegram Mini App
│   ├── templates/         # HTML шаблоны
│   └── static/            # CSS, JS, изображения
├── database/              # База данных
│   ├── models.py          # SQLAlchemy модели
│   └── database.py        # Подключение к БД
├── requirements.txt       # Зависимости Python
└── .env                   # Переменные окружения
```

## 🔧 Технологии

- **Backend**: Python, FastAPI
- **Bot**: python-telegram-bot
- **Database**: SQLite (SQLAlchemy)
- **Mini App**: Vanilla JS, HTML, CSS
- **API**: TMDB (The Movie Database)

## 📝 TODO

- [ ] Общие портфолио для совместного просмотра
- [ ] Фильтры по типу (фильмы/сериалы/аниме)
- [ ] Поиск по портфолио
- [ ] Экспорт в PDF
- [ ] Рекомендации на основе оценок

## 🤝 Разработка

Для локальной разработки:

1. Используйте ngrok для тестирования Mini App:
```bash
ngrok http 8000
```

2. Обновите `SERVER_URL` в `.env` на URL от ngrok

## 📄 Лицензия

MIT
