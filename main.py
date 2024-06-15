import os
import discord
from discord.ext import commands, tasks
from discord import File, Embed
from datetime import datetime
from config.config import DISCORD_TOKEN, CHANNEL_ID, UPDATE_DAYS, IMG_FOLDER, KEEP_DAYS, TIME_RANGE_DAYS
from graphs.generate_graphs import fetch_all_data, generate_graphs, ensure_folder_exists, cleanup_old_folders

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Post an embed to Discord with the graphs
async def post_graphs(channel):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    descriptions = {
        'daily_play_count.png': f'Daily play count by media type for the last {TIME_RANGE_DAYS} days.',
        'play_count_by_dayofweek.png': f'Play count by day of the week for the last {TIME_RANGE_DAYS} days.',
        'play_count_by_hourofday.png': f'Play count by hour of the day for the last {TIME_RANGE_DAYS} days.',
        'top_10_platforms.png': f'Play count by the top 10 platforms for the last {TIME_RANGE_DAYS} days.',
        'top_10_users.png': f'Play count by the top 10 users for the last {TIME_RANGE_DAYS} days.'
    }

    today = datetime.today().strftime('%Y-%m-%d')
    for filename, description in descriptions.items():
        file_path = os.path.join(IMG_FOLDER, today, filename)
        embed = Embed(description=description, color=0x3498db)
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"Posted on {now}")
        with open(file_path, 'rb') as f:
            await channel.send(file=File(f, filename), embed=embed)

# Delete the bot's messages from the channel
async def delete_bot_messages(channel):
    async for message in channel.history(limit=200):
        if message.author == bot.user:
            await message.delete()

# Task to update graphs
@tasks.loop(seconds=UPDATE_DAYS*24*60*60)  # Convert days to seconds
async def update_graphs():
    channel = bot.get_channel(CHANNEL_ID)
    await delete_bot_messages(channel)

    ensure_folder_exists(IMG_FOLDER)

    today = datetime.today().strftime('%Y-%m-%d')
    dated_folder = os.path.join(IMG_FOLDER, today)
    ensure_folder_exists(dated_folder)

    data = fetch_all_data()
    generate_graphs(data, dated_folder)

    await post_graphs(channel)
    cleanup_old_folders(IMG_FOLDER, KEEP_DAYS)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    update_graphs.start()

# Run the bot
bot.run(DISCORD_TOKEN)
