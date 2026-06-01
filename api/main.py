from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import get_session, init_db
from database.models import User, Movie, Portfolio, EpisodeRating

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "b9f7111dac996c0b5ecc7d34437d1786")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

class MovieCreate(BaseModel):
    user_id: int
    title: str
    rating: float
    movie_type: Optional[str] = None
    poster_url: Optional[str] = None
    tmdb_id: Optional[int] = None
    year: Optional[int] = None

app = FastAPI(title="Movie Bot API")

# Static files will be added later when needed

@app.on_event("startup")
async def startup():
    """Инициализация БД при запуске"""
    await init_db()
    print("Database initialized successfully")

@app.get("/")
async def root():
    return {"message": "Movie Bot API is running"}

@app.get("/miniapp")
async def miniapp(user_id: int):
    """Отдаем новый Mini App"""
    with open("miniapp/templates/index_new.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/api/search")
async def search_movies(query: str):
    """Поиск фильмов через TMDB API"""
    results = []

    # Поиск фильмов
    response = requests.get(
        f"{TMDB_BASE_URL}/search/movie",
        params={"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    )
    if response.status_code == 200:
        data = response.json()
        for item in data['results'][:5]:
            results.append({
                "tmdb_id": item['id'],
                "title": item.get('title', ''),
                "year": (item.get('release_date', '') or '')[:4],
                "poster_url": f"{TMDB_IMAGE_BASE}{item['poster_path']}" if item.get('poster_path') else None,
                "type": "movie"
            })

    # Поиск сериалов
    response = requests.get(
        f"{TMDB_BASE_URL}/search/tv",
        params={"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    )
    if response.status_code == 200:
        data = response.json()
        for item in data['results'][:5]:
            results.append({
                "tmdb_id": item['id'],
                "title": item.get('name', ''),
                "year": (item.get('first_air_date', '') or '')[:4],
                "poster_url": f"{TMDB_IMAGE_BASE}{item['poster_path']}" if item.get('poster_path') else None,
                "type": "tv"
            })

    return {"results": results}

@app.get("/api/episodes/{tmdb_id}")
async def get_episodes(tmdb_id: int):
    """Получить информацию о сезонах и сериях"""
    response = requests.get(
        f"{TMDB_BASE_URL}/tv/{tmdb_id}",
        params={"api_key": TMDB_API_KEY, "language": "ru-RU"}
    )

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="TV show not found")

    data = response.json()

    return {
        "tmdb_id": tmdb_id,
        "title": data.get('name', ''),
        "seasons": [
            {
                "season_number": season['season_number'],
                "episode_count": season['episode_count']
            }
            for season in data.get('seasons', [])
            if season['season_number'] > 0  # Пропускаем "Сезон 0" (спецвыпуски)
        ]
    }

class EpisodeRatingData(BaseModel):
    user_id: int
    tmdb_id: int
    season: int
    episode: int
    rating: int

@app.post("/api/episode-rating")
async def save_episode_rating(rating_data: EpisodeRatingData, session: AsyncSession = Depends(get_session)):
    """Сохранить оценку серии"""
    # Проверяем есть ли уже оценка
    result = await session.execute(
        select(EpisodeRating).where(
            EpisodeRating.user_id == rating_data.user_id,
            EpisodeRating.tmdb_id == rating_data.tmdb_id,
            EpisodeRating.season == rating_data.season,
            EpisodeRating.episode == rating_data.episode
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Обновляем существующую оценку
        existing.rating = rating_data.rating
    else:
        # Создаем новую оценку
        new_rating = EpisodeRating(
            user_id=rating_data.user_id,
            tmdb_id=rating_data.tmdb_id,
            season=rating_data.season,
            episode=rating_data.episode,
            rating=rating_data.rating
        )
        session.add(new_rating)

    await session.commit()
    return {"message": "Rating saved"}

@app.post("/api/movies")
async def create_movie(movie_data: MovieCreate, session: AsyncSession = Depends(get_session)):
    """Создать новый фильм"""
    # Создаем или получаем пользователя
    user = await session.get(User, movie_data.user_id)
    if not user:
        user = User(telegram_id=movie_data.user_id)
        session.add(user)
        await session.flush()

    # Создаем фильм
    movie = Movie(
        user_id=movie_data.user_id,
        title=movie_data.title,
        rating=movie_data.rating,
        movie_type=movie_data.movie_type,
        poster_url=movie_data.poster_url,
        tmdb_id=movie_data.tmdb_id,
        year=movie_data.year
    )
    session.add(movie)
    await session.commit()

    return {"message": "Movie created", "id": movie.id}

@app.get("/api/user/{telegram_id}/movies")
async def get_user_movies(telegram_id: int, session: AsyncSession = Depends(get_session)):
    """Получить все фильмы пользователя"""
    result = await session.execute(
        select(Movie).where(Movie.user_id == telegram_id).order_by(Movie.added_at.desc())
    )
    movies = result.scalars().all()

    return {
        "movies": [
            {
                "id": movie.id,
                "title": movie.title,
                "rating": movie.rating,
                "type": movie.movie_type,
                "poster_url": movie.poster_url,
                "year": movie.year,
                "added_at": movie.added_at.isoformat()
            }
            for movie in movies
        ]
    }

@app.delete("/api/movies/{movie_id}")
async def delete_movie(movie_id: int, session: AsyncSession = Depends(get_session)):
    """Удалить фильм"""
    movie = await session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    await session.delete(movie)
    await session.commit()

    return {"message": "Movie deleted"}

@app.get("/api/user/{telegram_id}/stats")
async def get_user_stats(telegram_id: int, session: AsyncSession = Depends(get_session)):
    """Статистика пользователя"""
    result = await session.execute(
        select(Movie).where(Movie.user_id == telegram_id)
    )
    movies = result.scalars().all()

    if not movies:
        return {
            "total": 0,
            "average_rating": 0,
            "by_type": {}
        }

    total = len(movies)
    avg_rating = sum(m.rating for m in movies) / total

    by_type = {}
    for movie in movies:
        movie_type = movie.movie_type or "unknown"
        if movie_type not in by_type:
            by_type[movie_type] = 0
        by_type[movie_type] += 1

    return {
        "total": total,
        "average_rating": round(avg_rating, 2),
        "by_type": by_type
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
