import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import datetime
from database.db import SessionLocal
from database import crud



load_dotenv()
token = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {ctx.author.mention}')

@bot.tree.command(name="starttask", description="Name and start a task")
async def starttask(interaction: discord.Interaction, name: str):
    db = SessionLocal()
    crud.get_or_create_user(db, interaction.user.id, interaction.guild.id, interaction.user.name)
    ev = crud.start_task(db, interaction.user.id, interaction.guild.id, name)
    db.close()
    await interaction.response.send_message(f"Started task: **{name}**")

@bot.tree.command(name="stoptask", description="Stop your current running task")
async def stoptask(interaction: discord.Interaction):
    db = SessionLocal()
    ev = crud.stop_task(db, interaction.user.id, interaction.guild.id)
        
    if not ev:
        db.close()
        return await interaction.response.send_message("No running task found.")
        
    event_name = ev.event_name
    duration_seconds = ev.duration_seconds
    db.close()

    await interaction.response.send_message(f"Stopped **{event_name}**, duration: {duration_seconds} seconds.")

@bot.event
async def on_voice_state_update(member, before, after):
    db = SessionLocal()

    # Joined voice
    if before.channel is None and after.channel is not None:
        crud.voice_join(db, member.id, member.guild.id, after.channel.id)
        channel = bot.get_channel(after.channel.id)
        if channel is not None:
            await channel.send(f"{member.mention} joined the voice channel.")
        
    # Left voice
    if before.channel is not None and after.channel is None:
        ev = crud.voice_leave(db, member.id, member.guild.id, before.channel.id)
        channel = bot.get_channel(before.channel.id)
        if channel:
            await channel.send(f"{member.mention} left the voice channel, Duration {ev.duration_seconds} seconds.")

    db.close()

@bot.tree.command(name="addassignment", description="Add a new assignment")
@app_commands.describe(
    title="Assignment title",
    due_date="Due date in YYYY-MM-DD format",
    description="Assignment description (optional)"
)
async def addassignment(interaction: discord.Interaction, title: str, due_date: str, description: str = ""):
    db = SessionLocal()

    # Convert date string → datetime
    try:
        date = datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        db.close()
        return await interaction.response.send_message("Invalid date format. Use YYYY-MM-DD.")

    # Make sure user exists
    crud.get_or_create_user(db, interaction.user.id, interaction.guild.id, interaction.user.name)

    # Save assignment
    a = crud.add_assignment(
        db,
        user_id=interaction.user.id,
        guild_id=interaction.guild.id,
        title=title,
        description=description,
        due_date=date
    )

    assignment_title = a.title
    assignment_id = a.assignment_id
    db.close()
    await interaction.response.send_message(f"Assignment added: **{assignment_title}** (ID: {assignment_id})")

@bot.tree.command(name="assignments", description="List all your assignments")
async def assignments(interaction: discord.Interaction):
    db = SessionLocal()

    items = crud.list_assignments(db, interaction.user.id, interaction.guild.id)

    db.close()

    if not items:
        return await interaction.response.send_message("You have no assignments yet.")
    
    msg = "**Your Assignments:**\n\n"
    for a in items:
        status = "Completed!" if a.is_completed else "In Progress..."
        msg += f"ID {a.assignment_id} -- {a.title} (due {a.due_date.date()}) {status}\n"

    await interaction.response.send_message(msg)

@bot.tree.command(name="completeassignment", description="Mark an assignment as completed")
@app_commands.describe(assignment_id="Assignment ID")
async def completeassignment(interaction: discord.Interaction, assignment_id: int):
    db = SessionLocal()

    a = crud.complete_assignment(db, assignment_id)
    if not a:
        db.close()
        return await interaction.response.send_message("Assignment not found.")

    await interaction.response.send_message(f"Assignment **{a.assignment_id} -- {a.title}** marked as completed.")
    db.close()

@bot.tree.command(name="clearassignments", description="Clear all your assignments")
async def clearassignments(interaction: discord.Interaction):
    db = SessionLocal()

    crud.clear_assignments(db, interaction.user.id, interaction.guild.id)

    await interaction.response.send_message("All your assignments have been cleared.")

    db.close()

@bot.tree.command(name="mystats", description="Get your total stats")
async def mystats(interaction: discord.Interaction):
    db = SessionLocal()

    task_stats = crud.get_total_task_time(db, interaction.user.id, interaction.guild.id)
    voice_stats = crud.get_total_voice_time(db, interaction.user.id, interaction.guild.id)

    if not task_stats and not voice_stats:
        db.close()
        return await interaction.response.send_message("No stats found.")
    
    # Convert seconds to hours, minutes, seconds
    task_hours = task_stats // 3600
    task_minutes = (task_stats % 3600) // 60
    task_seconds = task_stats % 60
    
    voice_hours = voice_stats // 3600
    voice_minutes = (voice_stats % 3600) // 60
    voice_seconds = voice_stats % 60

    db.close()
    msg = (
        f"**Your Total Stats:**\n\n"
        f"Total Task Time: {task_hours}h {task_minutes}m {task_seconds}s\n\n"
        f"Total Study Channel Time: {voice_hours}h {voice_minutes}m {voice_seconds}s\n"
    )

    await interaction.response.send_message(msg)


@bot.tree.command(name="leaderboard", description="Show the leaderboard for top users by total study time")
async def leaderboard(interaction: discord.Interaction):
    db = SessionLocal()
    leaderboard = crud.get_guild_leaderboard(db, interaction.guild.id)
    if not leaderboard or len(leaderboard) == 0:
        db.close()
        return await interaction.response.send_message("No leaderboard data found.")
    msg = "**Leaderboard — Top Study Time:**\n\n"
    for idx, entry in enumerate(leaderboard, start=1):
        # Convert seconds to hours, minutes, seconds
        total_seconds = entry['total_time']
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        msg += f"{idx}. **{entry['discord_name']}** -- {hours}h {minutes}m {seconds}s\n"
    db.close()
    await interaction.response.send_message(msg)
bot.run(token)