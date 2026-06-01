from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Таблица для связи многие-ко-многим (общие портфолио)
shared_portfolios = Table(
    'shared_portfolios',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('portfolio_id', Integer, ForeignKey('portfolios.id'))
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    movies = relationship("Movie", back_populates="user")
    portfolios = relationship("Portfolio", secondary=shared_portfolios, back_populates="users")

class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=True)

    title = Column(String, nullable=False)
    rating = Column(Float, nullable=False)
    movie_type = Column(String, nullable=True)  # фильм, сериал, аниме, мультик
    poster_url = Column(String, nullable=True)
    tmdb_id = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="movies")
    portfolio = relationship("Portfolio", back_populates="movies")

class Portfolio(Base):
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_shared = Column(Integer, default=0)  # 0 - личное, 1 - общее

    # Связи
    users = relationship("User", secondary=shared_portfolios, back_populates="portfolios")
    movies = relationship("Movie", back_populates="portfolio")

class EpisodeRating(Base):
    __tablename__ = 'episode_ratings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    episode = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="episode_ratings")
    review = Column(String, nullable=True)  # Текстовый отзыв
