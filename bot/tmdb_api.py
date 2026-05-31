import os
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

async def search_movie(query: str):
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
