from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import get_session, init_db
from database.models import User, Movie, Portfolio

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
    """Отдаем Mini App"""
    with open("miniapp/templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

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
