import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import datetime
import requests

API_URL = "http://localhost:8000"


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
    requests.post(f"{API_URL}/start", json={
        "user_id": interaction.user.id,
        "guild_id": interaction.guild.id,
        "name": name,
        "discord_name": interaction.user.name
    })
    await interaction.response.send_message(f"Started task: **{name}**")

@bot.tree.command(name="stoptask", description="Stop your current running task")
async def stoptask(interaction: discord.Interaction):
    post_request = requests.post(f"{API_URL}/stop", json={
        "user_id": interaction.user.id,
        "guild_id": interaction.guild.id
    })

    seconds = post_request.json()["seconds"]
    event_name = post_request.json()["event_name"]

    await interaction.response.send_message(f"Stopped **{event_name}**, duration: {seconds} seconds.")

@bot.event
async def on_voice_state_update(member, before, after):
    # Joined voice
    if before.channel is None and after.channel is not None:
        requests.post(f"{API_URL}/voice/join", json={
            "user_id": member.id,
            "guild_id": member.guild.id,
            "channel_id": after.channel.id,
            "discord_name": member.name
        })

        channel = bot.get_channel(after.channel.id)
        if channel:
            await channel.send(f"{member.mention} joined the voice channel.")
        
    # Left voice
    if before.channel is not None and after.channel is None:
        r = requests.post(f"{API_URL}/voice/leave", json={
            "user_id": member.id,
            "guild_id": member.guild.id,
            "channel_id": before.channel.id,
            "discord_name": member.name
        })

        data = r.json()
        duration = data["duration_seconds"]

        channel = bot.get_channel(before.channel.id)
        if channel:
            await channel.send(
                f"{member.mention} left the voice channel. Duration: {duration} seconds."
            )

@bot.tree.command(name="addassignment", description="Add a new assignment")
@app_commands.describe(
    title="Assignment title",
    due_date="Due date in YYYY-MM-DD format",
    description="Assignment description (optional)"
)
async def addassignment(interaction: discord.Interaction, title: str, due_date: str, description: str = ""):
    try:
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        await interaction.response.send_message("Invalid date format. Use YYYY-MM-DD.")
        return
    
    post_request = requests.post(f"{API_URL}/assignments/add", json={
        "user_id": interaction.user.id,
        "guild_id": interaction.guild.id,
        "title": title,
        "description": description,
        "due_date": due_date
    })

    data = post_request.json()
    assignment_title = data["title"]
    assignment_id = data["assignment_id"]
    await interaction.response.send_message(f"Assignment added: **{assignment_title}** (ID: {assignment_id})")

@bot.tree.command(name="assignments", description="List all your assignments")
async def assignments(interaction: discord.Interaction):

    get_request = requests.post(f"{API_URL}/assignments/list", json={
        "user_id": interaction.user.id,
        "guild_id": interaction.guild.id
    })

    data = get_request.json()

    if "error" in data:
        await interaction.response.send_message(data["error"])
        return

    assignments = data["assignments"]

    msg = "**Your Assignments:**\n\n"
    for a in assignments:
        status = "Completed!" if a["is_completed"] else "In Progress..."
        msg += f"ID {a['assignment_id']} -- {a['title']} (due {a['due_date']}) {status}\n"

    await interaction.response.send_message(msg)

@bot.tree.command(name="completeassignment", description="Mark an assignment as completed")
@app_commands.describe(assignment_id="Assignment ID")
async def completeassignment(interaction: discord.Interaction, assignment_id: int):
    post_request = requests.post(f"{API_URL}/assignments/complete", json={
        "assignment_id": assignment_id
    })

    data = post_request.json()
    if "error" in data:
        await interaction.response.send_message(data["error"])
        return

    await interaction.response.send_message(f"Assignment **{data['assignment_id']} -- {data['title']}** marked as completed.")

@bot.tree.command(name="clearassignments", description="Clear all your assignments")
async def clearassignments(interaction: discord.Interaction):
    requests.post(f"{API_URL}/assignments/clear", json={
        "user_id": interaction.user.id,
        "guild_id": interaction.guild.id
    })

    await interaction.response.send_message("All your assignments have been cleared.")

@bot.tree.command(name="mystats", description="Get your total stats")
async def mystats(interaction: discord.Interaction):
    get_request = requests.get(f"{API_URL}/stats/{interaction.guild.id}/{interaction.user.id}")
    data = get_request.json()

    task_time = data["total_task_time"]
    voice_time = data["total_voice_time"]

    msg = (
        f"**Your Total Stats:**\n\n"
        f"Total Task Time: {task_time}\n"
        f"Total Study Channel Time: {voice_time}\n"
    )

    await interaction.response.send_message(msg)

@bot.tree.command(name="leaderboard", description="Show the leaderboard for top users by total study time")
async def leaderboard(interaction: discord.Interaction):

    post_request = requests.post(f"{API_URL}/leaderboard", json={
        "guild_id": interaction.guild.id,
        "limit": 10
    })

    data = post_request.json()

    if data["leaderboard"] == []:
        await interaction.response.send_message("No data for leaderboard.")
        return


    leaderboard = data["leaderboard"]

    msg = "**Leaderboard — Top Study Time:**\n\n"
    for idx, entry in enumerate(leaderboard, start=1):
        # Convert
        total_seconds = entry['total_seconds']
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        msg += f"{idx}. **{entry['discord_name']}** -- {hours}h {minutes}m {seconds}s\n"
    await interaction.response.send_message(msg)
bot.run(token)

