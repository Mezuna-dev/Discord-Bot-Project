# api.py
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from database import crud
from database.db import SessionLocal

app = FastAPI()




# Request Models



class StartEvent(BaseModel):
    user_id: int
    guild_id: int
    name: str
    discord_name: str


class StopEvent(BaseModel):
    user_id: int
    guild_id: int


class VoiceEvent(BaseModel):
    user_id: int
    guild_id: int
    channel_id: int
    discord_name: str | None = None


class AssignmentCreate(BaseModel):
    user_id: int
    guild_id: int
    title: str
    description: str | None = ""
    due_date: str   # YYYY-MM-DD

class AssignmentList(BaseModel):
    user_id: int
    guild_id: int

class AssignmentComplete(BaseModel):
    assignment_id: int

class AssignmentClear(BaseModel):
    user_id: int
    guild_id: int

class LeaderboardRequest(BaseModel):
    guild_id: int
    limit: int = 10


# Endpoints


@app.post("/start")
def start_event(body: StartEvent):
    db = SessionLocal()
    crud.get_or_create_user(db, body.user_id, body.guild_id, body.discord_name)
    crud.start_task(db, body.user_id, body.guild_id, body.name)
    db.close()
    return {"ok": True}


@app.post("/stop")
def stop_event(body: StopEvent):
    db = SessionLocal()
    ev = crud.stop_task(db, body.user_id, body.guild_id)
    
    if not ev:
        db.close()
        return {"seconds": 0, "event_name": "No active task"}

    event_name = ev.event_name
    seconds = ev.duration_seconds

    db.close()
    return {"seconds": seconds, "event_name": event_name}

@app.get("/stats/{guild_id}/{user_id}")
def get_stats(guild_id: int, user_id: int):
    db = SessionLocal()
    task_stats = crud.get_total_task_time(db, user_id, guild_id)
    voice_stats = crud.get_total_voice_time(db, user_id, guild_id)

    if not task_stats and not voice_stats:
        db.close()
        return {"total_task_seconds": 0, "total_voice_seconds": 0}
    
    task_hours = task_stats // 3600
    task_minutes = (task_stats % 3600) // 60
    task_seconds = task_stats % 60

    voice_hours = voice_stats // 3600
    voice_minutes = (voice_stats % 3600) // 60
    voice_seconds = voice_stats % 60

    db.close()

    return {
        "total_task_time": f"{task_hours}h {task_minutes}m {task_seconds}s",
        "total_voice_time": f"{voice_hours}h {voice_minutes}m {voice_seconds}s"
    }

@app.post("/voice/join")
def voice_join_api(body: VoiceEvent):
    db = SessionLocal()
    crud.get_or_create_user(db, body.user_id, body.guild_id, body.discord_name)
    crud.voice_join(db, body.user_id, body.guild_id, body.channel_id)
    db.close()
    return {"ok": True}

@app.post("/voice/leave")
def voice_leave_api(body: VoiceEvent):
    db = SessionLocal()
    crud.get_or_create_user(db, body.user_id, body.guild_id, body.discord_name)
    ev = crud.voice_leave(db, body.user_id, body.guild_id, body.channel_id)

    if not ev:
        return {"duration_seconds": 0}

    duration = ev.duration_seconds 


    db.close()
    return {"duration_seconds": duration}

@app.post("/assignments/add")
def add_assignment_api(body: AssignmentCreate):
    db = SessionLocal()

    try:
        date = datetime.strptime(body.due_date, "%Y-%m-%d")
    except ValueError:
        db.close()
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    crud.get_or_create_user(db, body.user_id, body.guild_id)

    a = crud.add_assignment(
        db,
        user_id=body.user_id,
        guild_id=body.guild_id,
        title=body.title,
        description=body.description or "",
        due_date=date
    )

    assignment_id = a.assignment_id
    title = a.title
    db.close()

    return {
        "ok": True,
        "assignment_id": assignment_id,
        "title": title,
        "due_date": body.due_date
    }

@app.post("/assignments/list")
def list_assignments_api(body: AssignmentList):
    db = SessionLocal()

    items = crud.list_assignments(db, body.user_id, body.guild_id)


    if not items:
        return {"error": "You have no assignments yet."}
    
    assignments = [
        {
            "assignment_id": item.assignment_id,
            "title": item.title,
            "description": item.description,
            "due_date": item.due_date.strftime("%Y-%m-%d"),
            "is_completed": item.is_completed
        }
        for item in items
    ]

    db.close()
    return {"assignments": assignments}

@app.post("/assignments/complete")
def complete_assignment_api(body: AssignmentComplete):
    db = SessionLocal()
    a = crud.complete_assignment(db, body.assignment_id)
    if not a:
        db.close()
        return {"error": "Assignment not found."}
    
    assignment_id = a.assignment_id
    title = a.title
    db.close()

    return {
        "ok": True,
        "assignment_id": assignment_id,
        "title": title
    }

@app.post("/assignments/clear")
def clear_assignments_api(body: AssignmentClear):
    db = SessionLocal()
    crud.clear_assignments(db, body.user_id, body.guild_id)
    db.close()
    return {"ok": True}

@app.post("/leaderboard")
def guild_leaderboard_api(body: LeaderboardRequest):
    db = SessionLocal()
    leaderboard = crud.get_guild_leaderboard(db, body.guild_id)

    if not leaderboard or len(leaderboard) == 0:
        db.close()
        return {"leaderboard": []}
    
    leaderboard_entries = []
    for idx, entry in enumerate(leaderboard, start=1):
        leaderboard_entries.append({
            "rank": idx,
            "discord_name": entry['discord_name'],
            "total_seconds": entry['total_time']
        })

    db.close()
    return {"leaderboard": leaderboard_entries}
