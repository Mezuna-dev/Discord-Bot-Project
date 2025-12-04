from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Guild(Base):
    __tablename__ = "Guild"
    guild_id = Column(Integer, primary_key=True, index=True)
    guild_name = Column(String, nullable=True)

class User(Base):
    __tablename__ = "User"
    user_id = Column(Integer, primary_key=True, nullable=False)
    guild_id = Column(Integer, ForeignKey("Guild.guild_id"), primary_key=True, nullable=False)
    discord_name = Column(String, nullable=True)

class VoiceSession(Base):
    __tablename__ = "VoiceSession"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    guild_id = Column(Integer, nullable=False)
    channel_id = Column(Integer, nullable=False)

    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer)

class UserEvent(Base):
    __tablename__ = "UserEvent"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    guild_id = Column(Integer, nullable=False)

    event_type = Column(String, nullable=False)
    event_name = Column(String, nullable=False)

    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer)

class Assignment(Base):
    __tablename__ = "Assignment"

    assignment_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    guild_id = Column(Integer, nullable=False)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    is_completed = Column(Integer, default=0)