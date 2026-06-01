import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from rapidfuzz import fuzz, process

load_dotenv()

VERSION = "2.4"  # Версия бота

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

def search_movie_tmdb(query: str):
    """Поиск фильма/сериала в TMDB с нечётким поиском через rapidfuzz"""
    # Нормализуем запрос: lower case + убираем лишние пробелы
    query_normalized = ' '.join(query.lower().split())

    # Определяем тип
    is_anime = any(word in query_normalized for word in ['аниме', 'anime'])
    is_cartoon = any(word in query_normalized for word in ['мультик', 'мультфильм', 'cartoon'])

    all_results = []
    seen_ids = set()

    # Собираем все результаты из TMDB
    for search_type in ['movie', 'tv']:
        # Русский поиск
        url = f"{TMDB_BASE_URL}/search/{search_type}"
        params = {
            "api_key": TMDB_API_KEY,
            "query": query,
            "language": "ru-RU",
            "include_adult": False
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for item in data['results']:
                if item['id'] not in seen_ids:
                    seen_ids.add(item['id'])

                    title = item.get('title' if search_type == 'movie' else 'name', '')
                    year = (item.get('release_date' if search_type == 'movie' else 'first_air_date', '') or '')[:4]

                    movie_type = 'anime' if is_anime else ('cartoon' if is_cartoon else ('movie' if search_type == 'movie' else 'tv'))

                    all_results.append({
                        'title': title,
                        'type': movie_type,
                        'poster_url': f"{TMDB_IMAGE_BASE}{item['poster_path']}" if item.get('poster_path') else None,
                        'tmdb_id': item['id'],
                        'year': year,
                        'year_int': int(year) if year else 0
                    })

        # Английский поиск
        params['language'] = 'en-US'
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for item in data['results']:
                if item['id'] not in seen_ids:
                    seen_ids.add(item['id'])

                    title = item.get('title' if search_type == 'movie' else 'name', '')
                    year = (item.get('release_date' if search_type == 'movie' else 'first_air_date', '') or '')[:4]

                    movie_type = 'anime' if is_anime else ('cartoon' if is_cartoon else ('movie' if search_type == 'movie' else 'tv'))

                    all_results.append({
                        'title': title,
                        'type': movie_type,
                        'poster_url': f"{TMDB_IMAGE_BASE}{item['poster_path']}" if item.get('poster_path') else None,
                        'tmdb_id': item['id'],
                        'year': year,
                        'year_int': int(year) if year else 0
                    })

    if not all_results:
        return None

    # Применяем fuzzy search через rapidfuzz.process.extractOne
    # Создаем список названий для сравнения
    titles_normalized = [' '.join(r['title'].lower().split()) for r in all_results]

    # Используем extractOne для поиска лучшего совпадения
    # scorer=fuzz.WRatio - самый умный алгоритм
    best_match = process.extractOne(
        query_normalized,
        titles_normalized,
        scorer=fuzz.WRatio,
        score_cutoff=70  # Порог 70
    )

    if not best_match:
        # Если не нашли с порогом 70, пробуем с порогом 60
        best_match = process.extractOne(
            query_normalized,
            titles_normalized,
            scorer=fuzz.WRatio,
            score_cutoff=60
        )

    if not best_match:
        # Если совсем не нашли - возвращаем топ-10 по популярности
        all_results.sort(key=lambda x: x['year_int'], reverse=True)
        return all_results[:10]

    # Нашли лучшее совпадение
    matched_title, score, matched_index = best_match

    # Добавляем score ко всем результатам
    for i, result in enumerate(all_results):
        title_norm = ' '.join(result['title'].lower().split())
        result['score'] = fuzz.WRatio(query_normalized, title_norm)

    # Сортируем: сначала по score, потом по году (новые первые)
    all_results.sort(key=lambda x: (x['score'], x['year_int']), reverse=True)

    # Фильтруем результаты с score >= 60
    filtered_results = [r for r in all_results if r['score'] >= 60]

    # Если нашли хорошие совпадения - возвращаем их
    if filtered_results:
        return filtered_results[:10]

    # Иначе возвращаем топ-10 по году
    all_results.sort(key=lambda x: x['year_int'], reverse=True)
    return all_results[:10]

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
        "Открой портфолио, чтобы увидеть все свои фильмы с обложками!\n\n"
        f"Версия бота: {VERSION}",
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

    movie_results = search_movie_tmdb(title)

    if not movie_results:
        await update.message.reply_text(
            f"Не нашел '{title}' в базе.\n"
            "Попробуй написать название по-другому или на английском."
        )
        return

    # Если один результат с очень высоким score - сразу добавляем
    if len(movie_results) == 1 or (movie_results[0]['score'] > 90 and len(movie_results) < 3):
        await save_movie(update, user, movie_results[0], rating)
        return

    # Если несколько результатов - показываем выбор
    keyboard = []
    for i, movie in enumerate(movie_results[:10]):
        button_text = f"{movie['title']}"
        if movie['year']:
            button_text += f" ({movie['year']})"

        # Сохраняем данные в callback_data
        callback_data = f"select_{i}_{rating}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Сохраняем результаты поиска в context для callback
    context.user_data['movie_results'] = movie_results

    await update.message.reply_text(
        "Нашел несколько вариантов. Выбери нужный:",
        reply_markup=reply_markup
    )

async def save_movie(update: Update, user, movie_data: dict, rating: float):
    """Сохранение фильма в базу"""
    try:
        # Конвертируем year в int если это строка
        year_value = None
        if movie_data.get('year'):
            try:
                year_value = int(movie_data['year'])
            except (ValueError, TypeError):
                year_value = None

        response = requests.post(
            f"{SERVER_URL}/api/movies",
            json={
                "user_id": user.id,
                "title": movie_data['title'],
                "rating": rating,
                "movie_type": movie_data['type'],
                "poster_url": movie_data['poster_url'],
                "tmdb_id": movie_data['tmdb_id'],
                "year": year_value
            },
            timeout=10
        )

        if response.status_code != 200:
            print(f"API error: {response.status_code} - {response.text}")
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

    message_text = (
        f"Добавлено!\n\n"
        f"{movie_data['title']}"
    )
    if movie_data.get('year'):
        message_text += f" ({movie_data['year']})"
    message_text += f"\nТвоя оценка: {rating}/10"

    # Проверяем откуда пришел вызов - из callback или из message
    if update.callback_query:
        # Сначала отвечаем на callback чтобы убрать "часики"
        await update.callback_query.answer()
        # Потом редактируем сообщение - кнопки исчезнут
        await update.callback_query.message.edit_text(
            message_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup
        )

async def handle_movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора фильма из списка"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    # Парсим callback_data: "select_0_8.5"
    parts = query.data.split('_')
    if len(parts) != 3 or parts[0] != 'select':
        await query.message.edit_text("Ошибка обработки выбора")
        return

    movie_index = int(parts[1])
    rating = float(parts[2])

    # Получаем сохраненные результаты поиска
    movie_results = context.user_data.get('movie_results', [])

    if movie_index >= len(movie_results):
        await query.message.edit_text("Ошибка: фильм не найден")
        return

    selected_movie = movie_results[movie_index]

    # Сохраняем выбранный фильм
    await save_movie(update, user, selected_movie, rating)

def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_movie_selection, pattern='^select_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"Bot started successfully! Version: {VERSION}")
    application.run_polling()

if __name__ == "__main__":
    main()
