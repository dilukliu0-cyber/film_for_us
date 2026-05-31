import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import async_session
from database.models import User, Movie
from tmdb_api import search_movie

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user

    # Сохраняем пользователя в БД
    async with async_session() as session:
        db_user = await session.get(User, user.id)
        if not db_user:
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            session.add(db_user)
            await session.commit()

    # Кнопка для открытия Mini App
    keyboard = [
        [InlineKeyboardButton(
            "📱 Открыть портфолио",
            web_app=WebAppInfo(url=f"{SERVER_URL}/miniapp?user_id={user.id}")
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу тебе вести портфолио фильмов, сериалов и аниме.\n\n"
        "📝 Просто напиши название и оценку:\n"
        "• Интерстеллар 10\n"
        "• Во все тяжкие 9.5\n"
        "• Атака титанов 10\n\n"
        "📱 Открой портфолио, чтобы увидеть все свои фильмы с обложками!",
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
            "❌ Не могу распознать формат.\n\n"
            "Напиши так: Название фильма Оценка\n"
            "Например: Интерстеллар 10"
        )
        return

    title = match.group(1).strip()
    rating = float(match.group(2))

    if rating < 0 or rating > 10:
        await update.message.reply_text("❌ Оценка должна быть от 0 до 10")
        return

    # Ищем фильм в TMDB
    await update.message.reply_text(f"🔍 Ищу '{title}'...")

    movie_data = await search_movie(title)

    if not movie_data:
        await update.message.reply_text(
            f"❌ Не нашел '{title}' в базе.\n"
            "Попробуй написать название по-другому или на английском."
        )
        return

    # Сохраняем в БД
    async with async_session() as session:
        movie = Movie(
            user_id=user.id,
            title=movie_data['title'],
            rating=rating,
            movie_type=movie_data['type'],
            poster_url=movie_data['poster_url'],
            tmdb_id=movie_data['tmdb_id'],
            year=movie_data['year']
        )
        session.add(movie)
        await session.commit()

    # Кнопка для открытия портфолио
    keyboard = [
        [InlineKeyboardButton(
            "📱 Открыть портфолио",
            web_app=WebAppInfo(url=f"{SERVER_URL}/miniapp?user_id={user.id}")
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Добавлено!\n\n"
        f"🎬 {movie_data['title']} ({movie_data['year']})\n"
        f"⭐ Твоя оценка: {rating}/10",
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
