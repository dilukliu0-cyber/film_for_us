import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

def search_movie_tmdb(query: str):
    """Поиск фильма/сериала в TMDB"""
    # Сначала ищем в фильмах
    url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "ru-RU"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['results']:
            movie = data['results'][0]
            return {
                'title': movie.get('title', query),
                'type': 'movie',
                'poster_url': f"{TMDB_IMAGE_BASE}{movie['poster_path']}" if movie.get('poster_path') else None,
                'tmdb_id': movie['id'],
                'year': movie.get('release_date', '')[:4] if movie.get('release_date') else None
            }

    # Если не нашли в фильмах, ищем в сериалах
    url = f"{TMDB_BASE_URL}/search/tv"
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['results']:
            show = data['results'][0]
            return {
                'title': show.get('name', query),
                'type': 'tv',
                'poster_url': f"{TMDB_IMAGE_BASE}{show['poster_path']}" if show.get('poster_path') else None,
                'tmdb_id': show['id'],
                'year': show.get('first_air_date', '')[:4] if show.get('first_air_date') else None
            }

    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user

    # Кнопка для открытия Mini App
    keyboard = [
        [InlineKeyboardButton(
            "Открыть портфолио",
            web_app=WebAppInfo(url=f"{SERVER_URL}/miniapp?user_id={user.id}")
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        "Я помогу тебе вести портфолио фильмов, сериалов и аниме.\n\n"
        "Просто напиши название и оценку:\n"
        "- Интерстеллар 10\n"
        "- Во все тяжкие 9.5\n"
        "- Атака титанов 10\n\n"
        "Открой портфолио, чтобы увидеть все свои фильмы с обложками!",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений с фильмами"""
    text = update.message.text
    user = update.effective_user

    # Парсим сообщение: "Название фильма 8.5" или "Название фильма 8"
    pattern = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*$'
    match = re.match(pattern, text.strip())

    if not match:
        await update.message.reply_text(
            "Не могу распознать формат.\n\n"
            "Напиши так: Название фильма Оценка\n"
            "Например: Интерстеллар 10"
        )
        return

    title = match.group(1).strip()
    rating = float(match.group(2))

    if rating < 0 or rating > 10:
        await update.message.reply_text("Оценка должна быть от 0 до 10")
        return

    # Ищем фильм в TMDB
    await update.message.reply_text(f"Ищу '{title}'...")

    movie_data = search_movie_tmdb(title)

    if not movie_data:
        await update.message.reply_text(
            f"Не нашел '{title}' в базе.\n"
            "Попробуй написать название по-другому или на английском."
        )
        return

    # Отправляем данные на API
    try:
        response = requests.post(
            f"{SERVER_URL}/api/movies",
            json={
                "user_id": user.id,
                "title": movie_data['title'],
                "rating": rating,
                "movie_type": movie_data['type'],
                "poster_url": movie_data['poster_url'],
                "tmdb_id": movie_data['tmdb_id'],
                "year": movie_data['year']
            },
            timeout=10
        )

        if response.status_code != 200:
            await update.message.reply_text("Ошибка при сохранении. Попробуй еще раз.")
            return

    except Exception as e:
        print(f"Error saving movie: {e}")
        await update.message.reply_text("Ошибка при сохранении. Попробуй еще раз.")
        return

    # Кнопка для открытия портфолио
    keyboard = [
        [InlineKeyboardButton(
            "Открыть портфолио",
            web_app=WebAppInfo(url=f"{SERVER_URL}/miniapp?user_id={user.id}")
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Добавлено!\n\n"
        f"{movie_data['title']} ({movie_data['year']})\n"
        f"Твоя оценка: {rating}/10",
        reply_markup=reply_markup
    )

def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot started successfully!")
    application.run_polling()

if __name__ == "__main__":
    main()
