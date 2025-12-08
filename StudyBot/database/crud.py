from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from .models import User, Guild, VoiceSession, UserEvent, Assignment



# Guild & User

def get_or_create_guild(db: Session, guild_id: int, guild_name: str = None):
    guild = db.query(Guild).filter(Guild.guild_id == guild_id).first()
    if guild:
        return guild
    guild = Guild(guild_id=guild_id, guild_name=guild_name)
    db.add(guild)
    db.commit()
    return guild


def get_or_create_user(db: Session, user_id: int, guild_id: int, discord_name: str = None):
    user = db.query(User).filter(User.user_id == user_id, User.guild_id == guild_id).first()

    if user:
        # Update discord_name if it's currently None and we have a new name
        if user.discord_name is None and discord_name is not None:
            user.discord_name = discord_name
            db.commit()
        return user

    user = User(user_id=user_id, guild_id=guild_id, discord_name=discord_name)
    db.add(user)
    db.commit()
    return user


# Task Events

def start_task(db: Session, user_id: int, guild_id: int, task_name: str):
    ev = UserEvent(
        user_id=user_id,
        guild_id=guild_id,
        event_type="task",
        event_name=task_name,
        start_time=datetime.utcnow(),
    )
    db.add(ev)
    db.commit()
    return ev


def stop_task(db: Session, user_id: int, guild_id: int):
    ev = db.query(UserEvent).filter(UserEvent.user_id == user_id, UserEvent.guild_id == guild_id, UserEvent.event_type == "task", UserEvent.end_time.is_(None)).order_by(UserEvent.start_time.desc()).first()

    if not ev:
        return None

    ev.end_time = datetime.utcnow()
    ev.duration_seconds = int((ev.end_time - ev.start_time).total_seconds())

    db.commit()
    return ev


# Voice Sessions

def voice_join(db: Session, user_id: int, guild_id: int, channel_id: int):
    vs = VoiceSession(
        user_id=user_id,
        guild_id=guild_id,
        channel_id=channel_id,
        start_time=datetime.utcnow()
    )
    db.add(vs)
    db.commit()
    return vs


def voice_leave(db: Session, user_id: int, guild_id: int, channel_id: int):
    vs = db.query(VoiceSession).filter(VoiceSession.user_id == user_id, VoiceSession.guild_id == guild_id, VoiceSession.channel_id == channel_id, VoiceSession.end_time.is_(None)).order_by(VoiceSession.start_time.desc()).first()

    if not vs:
        return None

    vs.end_time = datetime.utcnow()
    vs.duration_seconds = int((vs.end_time - vs.start_time).total_seconds())
    db.commit()
    return vs


# Assignments

def add_assignment(db: Session, user_id: int, guild_id: int, title: str, description: str, due_date):
    a = Assignment(
        user_id=user_id,
        guild_id=guild_id,
        title=title,
        description=description,
        due_date=due_date,
        is_completed=0
    )
    db.add(a)
    db.commit()
    return a


def list_assignments(db: Session, user_id: int, guild_id: int):
    return (
        db.query(Assignment).filter(Assignment.user_id == user_id, Assignment.guild_id == guild_id).order_by(Assignment.due_date.asc()).all()
    )

def complete_assignment(db, assignment_id: int):
    a = db.query(Assignment).filter(Assignment.assignment_id == assignment_id).first()
    if not a:
        return None
    a.is_completed = 1
    db.commit()
    return a

def clear_assignments(db, user_id: int, guild_id: int):
    db.query(Assignment).filter(Assignment.user_id == user_id, Assignment.guild_id == guild_id).delete()
    db.commit()

# Stats

def get_total_task_time(db: Session, user_id: int, guild_id: int):   
    # Get total task time
    total_time_seconds = db.query(func.sum(UserEvent.duration_seconds)).filter(UserEvent.user_id == user_id, UserEvent.guild_id == guild_id, UserEvent.event_type == "task", UserEvent.duration_seconds.is_not(None))

    return total_time_seconds.scalar() or 0


def get_total_voice_time(db: Session, user_id: int, guild_id: int):

    total_voice_seconds = db.query(func.sum(VoiceSession.duration_seconds)).filter(VoiceSession.user_id == user_id, VoiceSession.guild_id == guild_id, VoiceSession.duration_seconds.is_not(None))

    return total_voice_seconds.scalar() or 0

def get_guild_leaderboard(db: Session, guild_id: int):
    """Get all users in a guild with their total study time"""
    from sqlalchemy import func
    
    # Get all users in the guild
    users = db.query(User).filter(User.guild_id == guild_id).all()
    
    leaderboard = []
    for user in users:
        task_time = get_total_task_time(db, user.user_id, guild_id)
        voice_time = get_total_voice_time(db, user.user_id, guild_id)
        total_time = task_time + voice_time
        
        leaderboard.append({
            'user_id': user.user_id,
            'discord_name': user.discord_name,
            'task_time': task_time,
            'voice_time': voice_time,
            'total_time': total_time
        })
    
    # Sort by total time descending
    leaderboard.sort(key=lambda x: x['total_time'], reverse=True)
    
    return leaderboard