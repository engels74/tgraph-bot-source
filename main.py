import os
import logging
import discord
from discord.ext import commands, tasks
from discord import File, Embed
from datetime import datetime
from config.config import DISCORD_TOKEN, CHANNEL_ID, UPDATE_DAYS, IMG_FOLDER, KEEP_DAYS, TIME_RANGE_DAYS, timezone
from graphs.generate_graphs import fetch_all_data, generate_graphs, ensure_folder_exists, cleanup_old_folders

# Set up logging
log_directory = '/logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(
    filename=os.path.join(log_directory, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Function to print log messages with timestamps
def log(message):
    logger.info(message)
    timestamp = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {message}")

# Post an embed to Discord with the graphs
async def post_graphs(channel):
    now = datetime.now(timezone).strftime('%Y-%m-%d at %H:%M:%S')
    today = datetime.today().strftime('%Y-%m-%d')
    descriptions = {
        'daily_play_count.png': {
            'title': 'Daily Play Count by Media Type',
            'description': f'Displays the daily play count for different media types over the last {TIME_RANGE_DAYS} days.'
        },
        'play_count_by_dayofweek.png': {
            'title': 'Play Count by Day of Week',
            'description': f'Shows the play count distribution by day of the week for the last {TIME_RANGE_DAYS} days.'
        },
        'play_count_by_hourofday.png': {
            'title': 'Play Count by Hour of Day',
            'description': f'Illustrates the play count distribution by hour of the day over the last {TIME_RANGE_DAYS} days.'
        },
        'top_10_platforms.png': {
            'title': 'Play Count by Top 10 Platforms',
            'description': f'Highlights the play count for the top 10 platforms over the last {TIME_RANGE_DAYS} days.'
        },
        'top_10_users.png': {
            'title': 'Play Count by Top 10 Users',
            'description': f'Displays the play count for the top 10 users over the last {TIME_RANGE_DAYS} days.'
        },
        'play_count_by_month.png': {
            'title': 'Total Play Count by Month',
            'description': f'Shows the total play count by month for the last 12 months, excluding months with zero plays.'
        }
    }

    for filename, details in descriptions.items():
        file_path = os.path.join(IMG_FOLDER, today, filename)
        embed = Embed(title=details['title'], description=details['description'], color=0x3498db)
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"Posted on {now}")
        with open(file_path, 'rb') as f:
            await channel.send(file=File(f, filename), embed=embed)
            log(f"Posted {filename} to Discord")

# Delete the bot's messages from the channel
async def delete_bot_messages(channel):
    log("Detecting old messages")
    async for message in channel.history(limit=200):
        if message.author == bot.user:
            await message.delete()
            log("Deleted a message")

# Task to update graphs
@tasks.loop(seconds=UPDATE_DAYS*24*60*60)  # Convert days to seconds
async def update_graphs():
    channel = bot.get_channel(CHANNEL_ID)
    await delete_bot_messages(channel)

    ensure_folder_exists(IMG_FOLDER)
    log("Ensured image folder exists")

    today = datetime.today().strftime('%Y-%m-%d')
    dated_folder = os.path.join(IMG_FOLDER, today)
    ensure_folder_exists(dated_folder)
    log(f"Created dated folder: {dated_folder}")

    data = fetch_all_data()
    generate_graphs(data, dated_folder)
    log("Generated graphs")

    await post_graphs(channel)
    cleanup_old_folders(IMG_FOLDER, KEEP_DAYS)
    log("Cleaned up old folders")

@bot.event
async def on_ready():
    log(f'Logged in as {bot.user.name}')
    update_graphs.start()

# Run the bot
bot.run(DISCORD_TOKEN)