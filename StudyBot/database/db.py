from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./discord_bot.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

Base = declarative_base()
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine)