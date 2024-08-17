# graphs/generate_graphs.py
import os
import discord
import logging
import shutil
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from matplotlib.ticker import MaxNLocator
from matplotlib.dates import DateFormatter
from matplotlib.font_manager import FontProperties
from config.config import load_config, CONFIG_PATH
from i18n import load_translations

# Load configuration
config = load_config(CONFIG_PATH)

# Initialize translations globally
translations = load_translations(config['LANGUAGE'])

# Define consistent colors
TV_COLOR = 'blue'
MOVIE_COLOR = 'orange'

# Helper function to fetch data from Tautulli
def fetch_tautulli_data(cmd, params={}):
    now = datetime.now().astimezone()
    start_date = now - timedelta(days=config['TIME_RANGE_DAYS'])
    params.update({
        'apikey': config['TAUTULLI_API_KEY'],
        'cmd': cmd,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': now.strftime('%Y-%m-%d'),
    })
    response = requests.get(config['TAUTULLI_URL'], params=params)
    return response.json()

# Fetch data
def fetch_all_data():
    data = {}
    if config['ENABLE_DAILY_PLAY_COUNT']:
        data['daily_play_count'] = fetch_tautulli_data('get_plays_by_date', {'time_range': config['TIME_RANGE_DAYS']})
    if config['ENABLE_PLAY_COUNT_BY_DAYOFWEEK']:
        data['play_count_by_dayofweek'] = fetch_tautulli_data('get_plays_by_dayofweek', {'time_range': config['TIME_RANGE_DAYS']})
    if config['ENABLE_PLAY_COUNT_BY_HOUROFDAY']:
        data['play_count_by_hourofday'] = fetch_tautulli_data('get_plays_by_hourofday', {'time_range': config['TIME_RANGE_DAYS']})
    if config['ENABLE_TOP_10_PLATFORMS']:
        data['top_10_platforms'] = fetch_tautulli_data('get_plays_by_top_10_platforms', {'time_range': config['TIME_RANGE_DAYS']})
    if config['ENABLE_TOP_10_USERS']:
        data['top_10_users'] = fetch_tautulli_data('get_plays_by_top_10_users', {'time_range': config['TIME_RANGE_DAYS']})
    if config['ENABLE_PLAY_COUNT_BY_MONTH']:
        data['play_count_by_month'] = fetch_tautulli_data('get_plays_per_month', {'time_range': 12, 'y_axis': 'plays'})  # Last 12 months
    return data

# Censor usernames
def censor_username(username, should_censor):
    if not should_censor:
        return username
    length = len(username)
    if length <= 2:
        return '*' * length
    half_length = length // 2
    return username[:half_length] + '*' * (length - half_length)

# Generate graphs
def generate_graphs(data, folder, current_translations):
    global config, translations
    translations = current_translations
    config = load_config(CONFIG_PATH, reload=True)
    
    if config['ENABLE_DAILY_PLAY_COUNT']:
        plt.figure(figsize=(14, 8))
        # Daily Play Count by Media Type
        daily_play_count = data['daily_play_count']['response']['data']
        
        # Calculate date range
        end_date = datetime.now().astimezone()
        start_date = end_date - timedelta(days=config['TIME_RANGE_DAYS'] - 1)  # Include the end date
        dates = [start_date + timedelta(days=i) for i in range(config['TIME_RANGE_DAYS'])]
        
        # Map Tautulli data to this date range
        date_strs = [date.strftime('%Y-%m-%d') for date in dates]
        date_data_map = {date: 0 for date in date_strs}
        
        series = daily_play_count['series']
        
        for serie in series:
            complete_data = [0] * len(dates)
            for date, value in zip(daily_play_count['categories'], serie['data']):
                if date in date_data_map:
                    date_data_map[date] = value
            complete_data = [date_data_map[date] for date in date_strs]
            color = TV_COLOR if serie['name'] == 'TV' else MOVIE_COLOR
            plt.plot(dates, complete_data, label=serie['name'], marker='o', color=color)
            
            # Adding annotations for the top value of each day
            if config['ANNOTATE_DAILY_PLAY_COUNT']:
                for i, value in enumerate(complete_data):
                    if value > 0:  # Only annotate days with plays
                        plt.text(dates[i], value + 0.5, f'{value}', ha='center', va='bottom', fontsize=8, color='red')
        
        plt.xlabel(translations['daily_play_count_xlabel'], fontweight='bold')
        plt.ylabel(translations['daily_play_count_ylabel'], fontweight='bold')
        plt.title(translations['daily_play_count_title'].format(days=config["TIME_RANGE_DAYS"]), fontweight='bold')
        
        # Set x-axis tick positions and labels
        ax = plt.gca()
        ax.set_xticks(dates)
        ax.set_xticklabels(date_strs, rotation=45, ha='right')
        ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.legend()
        plt.tight_layout(pad=3)
        save_and_post_graph(folder, 'daily_play_count.png')
        plt.close()

    if config['ENABLE_PLAY_COUNT_BY_DAYOFWEEK']:
        plt.figure(figsize=(14, 8))
        # Play Count by Day of Week
        play_count_by_dayofweek = data['play_count_by_dayofweek']['response']['data']
        days = list(range(7))
        day_labels = [translations[f'day_{i}'] for i in range(7)]
        series = play_count_by_dayofweek['series']
        for serie in series:
            color = TV_COLOR if serie['name'] == 'TV' else MOVIE_COLOR
            plt.plot(days, serie['data'], label=serie['name'], marker='o', color=color)
            if config['ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK']:
                for i, value in enumerate(serie['data']):
                    if value > 0:
                        plt.text(days[i], value + 0.5, f'{value}', ha='center', va='bottom', fontsize=8, color='red')
        plt.xlabel(translations['play_count_by_dayofweek_xlabel'], fontweight='bold')
        plt.ylabel(translations['play_count_by_dayofweek_ylabel'], fontweight='bold')
        plt.title(translations['play_count_by_dayofweek_title'].format(days=config["TIME_RANGE_DAYS"]), fontweight='bold')
        plt.xticks(days, day_labels, ha='center')
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.legend()
        plt.tight_layout(pad=3)
        save_and_post_graph(folder, 'play_count_by_dayofweek.png')
        plt.close()

    if config['ENABLE_PLAY_COUNT_BY_HOUROFDAY']:
        plt.figure(figsize=(14, 8))
        # Play Count by Hour of Day
        play_count_by_hourofday = data['play_count_by_hourofday']['response']['data']
        hours = list(range(24))
        series = play_count_by_hourofday['series']
        for serie in series:
            color = TV_COLOR if serie['name'] == 'TV' else MOVIE_COLOR
            plt.plot(hours, serie['data'], label=serie['name'], marker='o', color=color)
            if config['ANNOTATE_PLAY_COUNT_BY_HOUROFDAY']:
                for i, value in enumerate(serie['data']):
                    if value > 0:
                        plt.text(hours[i], value + 0.5, f'{value}', ha='center', va='bottom', fontsize=8, color='red')
        plt.xlabel(translations['play_count_by_hourofday_xlabel'], fontweight='bold')
        plt.ylabel(translations['play_count_by_hourofday_ylabel'], fontweight='bold')
        plt.title(translations['play_count_by_hourofday_title'].format(days=config["TIME_RANGE_DAYS"]), fontweight='bold')
        plt.xticks(hours, ha='center')
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.legend()
        plt.tight_layout(pad=3)
        save_and_post_graph(folder, 'play_count_by_hourofday.png')
        plt.close()

    if config['ENABLE_TOP_10_PLATFORMS']:
        plt.figure(figsize=(14, 8))
        # Play Count by Top 10 Platforms
        top_10_platforms = data['top_10_platforms']['response']['data']
        platforms = top_10_platforms['categories']
        series = top_10_platforms['series']
        for serie in series:
            color = TV_COLOR if serie['name'] == 'TV' else MOVIE_COLOR
            plt.bar(platforms, serie['data'], label=serie['name'], color=color)
            if config['ANNOTATE_TOP_10_PLATFORMS']:
                for i, v in enumerate(serie['data']):
                    plt.text(i, v + 0.5, str(v), color='red', fontweight='bold', ha='center', va='bottom')
        plt.xlabel(translations['top_10_platforms_xlabel'], fontweight='bold')
        plt.ylabel(translations['top_10_platforms_ylabel'], fontweight='bold')
        plt.title(translations['top_10_platforms_title'].format(days=config["TIME_RANGE_DAYS"]), fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.legend()
        plt.tight_layout(pad=3)
        save_and_post_graph(folder, 'top_10_platforms.png')
        plt.close()

    if config['ENABLE_TOP_10_USERS']:
        plt.figure(figsize=(14, 8))
        # Play Count by Top 10 Users
        top_10_users = data['top_10_users']['response']['data']
        users = top_10_users['categories']
        series = top_10_users['series']

        # Combine TV and movie play counts for each user
        combined_data = []
        for i, user in enumerate(users):
            tv_plays = series[0]['data'][i] if series[0]['name'] == 'TV' else series[1]['data'][i]
            movie_plays = series[1]['data'][i] if series[1]['name'] == 'Movies' else series[0]['data'][i]
            total_plays = tv_plays + movie_plays
            combined_data.append((user, tv_plays, movie_plays, total_plays))

        # Sort users by total play count, descending
        combined_data.sort(key=lambda x: x[3], reverse=True)

        # Reconstruct data for plotting
        sorted_users = [item[0] for item in combined_data]
        sorted_tv_data = [item[1] for item in combined_data]
        sorted_movie_data = [item[2] for item in combined_data]

        censored_users = [censor_username(user, config['CENSOR_USERNAMES']) for user in sorted_users]

        # Plot the sorted data
        plt.bar(censored_users, sorted_movie_data, label='Movies', color=MOVIE_COLOR)  # Movies at the bottom
        plt.bar(censored_users, sorted_tv_data, bottom=sorted_movie_data, label='TV', color=TV_COLOR)  # TV on top

        if config['ANNOTATE_TOP_10_USERS']:
            for i, (tv, movie) in enumerate(zip(sorted_tv_data, sorted_movie_data)):
                total = tv + movie
                plt.text(i, total + 0.5, str(total), color='red', fontweight='bold', ha='center', va='bottom')

        plt.xlabel(translations['top_10_users_xlabel'], fontweight='bold')
        plt.ylabel(translations['top_10_users_ylabel'], fontweight='bold')
        plt.title(translations['top_10_users_title'].format(days=config["TIME_RANGE_DAYS"]), fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.legend()
        plt.tight_layout(pad=3)
        save_and_post_graph(folder, 'top_10_users.png')
        plt.close()

    if config['ENABLE_PLAY_COUNT_BY_MONTH']:
        plt.figure(figsize=(14, 8))
        # Play Count by Month (Last 12 months)
        play_count_by_month = data['play_count_by_month']['response']['data']

        months = play_count_by_month.get('categories', [])
        series = play_count_by_month.get('series', [])

        if not months or not series:
            print(translations['no_data_available'])
            return

        # Prepare data for the stacked bar chart
        movie_data = [0] * len(months)
        tv_data = [0] * len(months)

        for serie in series:
            if serie['name'] == 'Movies':
                movie_data = serie['data']
            elif serie['name'] == 'TV':
                tv_data = serie['data']

        filtered_months = []
        filtered_movie_data = []
        filtered_tv_data = []

        for i in range(len(months)):
            if movie_data[i] > 0 or tv_data[i] > 0:
                filtered_months.append(months[i])
                filtered_movie_data.append(movie_data[i])
                filtered_tv_data.append(tv_data[i])

        # Plot the stacked bar chart
        bar_width = 0.4
        bar_positions = range(len(filtered_months))

        plt.bar(bar_positions, filtered_movie_data, width=bar_width, label='Movies', color=MOVIE_COLOR)
        plt.bar(bar_positions, filtered_tv_data, width=bar_width, bottom=filtered_movie_data, label='TV', color=TV_COLOR)

        if config['ANNOTATE_PLAY_COUNT_BY_MONTH']:
            for i, v in enumerate(filtered_movie_data):
                plt.text(i, v + 0.5, str(v), color='red', fontweight='bold', ha='center', va='bottom')

            for i, v in enumerate(filtered_tv_data):
                plt.text(i, v + filtered_movie_data[i] + 0.5, str(v), color='red', fontweight='bold', ha='center', va='bottom')

        plt.xlabel(translations['play_count_by_month_xlabel'], fontweight='bold')
        plt.ylabel(translations['play_count_by_month_ylabel'], fontweight='bold')
        plt.title(translations['play_count_by_month_title'], fontweight='bold')
        plt.xticks(bar_positions, filtered_months, rotation=45, ha='right')
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.legend()
        plt.tight_layout(pad=3)
        save_and_post_graph(folder, 'play_count_by_month.png')
        plt.close()

# Save and post graph to Discord
def save_and_post_graph(folder, filename):
    filepath = os.path.join(folder, filename)
    plt.savefig(filepath)
    plt.clf()  # Clear the current figure
    logging.info(translations['log_posted_message'].format(filename=filename))

# Ensure the image folder exists
def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    logging.info(translations['log_ensured_folder_exists'])

# Cleanup old folders
def cleanup_old_folders(base_folder, keep_days):
    folders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
    folders.sort(reverse=True)
    for folder in folders[keep_days:]:
        shutil.rmtree(os.path.join(base_folder, folder))
    logging.info(translations['log_cleaned_up_old_folders'])

# Function to update and post graphs
async def update_and_post_graphs(bot, current_translations):
    global config, translations
    translations = current_translations
    config = load_config(CONFIG_PATH, reload=True)
    
    channel = bot.get_channel(config['CHANNEL_ID'])
    await delete_bot_messages(channel)

    try:
        ensure_folder_exists(bot.img_folder)

        today = datetime.today().strftime('%Y-%m-%d')
        dated_folder = os.path.join(bot.img_folder, today)
        ensure_folder_exists(dated_folder)

        data = fetch_all_data()
        generate_graphs(data, dated_folder, translations)

        # Update the tracker before posting graphs
        bot.update_tracker.update()
        next_update = bot.update_tracker.next_update

        await post_graphs(channel, bot.img_folder, translations, next_update)
        next_update_log = bot.update_tracker.get_next_update_readable()
        logging.info(translations['log_graphs_updated_posted'].format(next_update=next_update_log))
        cleanup_old_folders(bot.img_folder, config['KEEP_DAYS'])
    except Exception as e:
        logging.error(translations['error_update_post_graphs'].format(error=str(e)))
        raise

# Function to post graphs
async def post_graphs(channel, img_folder, translations, next_update):
    now = datetime.now().astimezone().strftime('%Y-%m-%d at %H:%M:%S')
    today = datetime.today().strftime('%Y-%m-%d')
    next_update_discord = f"<t:{int(next_update.timestamp())}:R>"
    descriptions = {}

    if config['ENABLE_DAILY_PLAY_COUNT']:
        descriptions['daily_play_count.png'] = {
            'title': translations['daily_play_count_title'].format(days=config["TIME_RANGE_DAYS"]),
            'description': translations['daily_play_count_description'].format(days=config["TIME_RANGE_DAYS"])
        }

    if config['ENABLE_PLAY_COUNT_BY_DAYOFWEEK']:
        descriptions['play_count_by_dayofweek.png'] = {
            'title': translations['play_count_by_dayofweek_title'].format(days=config["TIME_RANGE_DAYS"]),
            'description': translations['play_count_by_dayofweek_description'].format(days=config["TIME_RANGE_DAYS"])
        }

    if config['ENABLE_PLAY_COUNT_BY_HOUROFDAY']:
        descriptions['play_count_by_hourofday.png'] = {
            'title': translations['play_count_by_hourofday_title'].format(days=config["TIME_RANGE_DAYS"]),
            'description': translations['play_count_by_hourofday_description'].format(days=config["TIME_RANGE_DAYS"])
        }

    if config['ENABLE_TOP_10_PLATFORMS']:
        descriptions['top_10_platforms.png'] = {
            'title': translations['top_10_platforms_title'].format(days=config["TIME_RANGE_DAYS"]),
            'description': translations['top_10_platforms_description'].format(days=config["TIME_RANGE_DAYS"])
        }

    if config['ENABLE_TOP_10_USERS']:
        descriptions['top_10_users.png'] = {
            'title': translations['top_10_users_title'].format(days=config["TIME_RANGE_DAYS"]),
            'description': translations['top_10_users_description'].format(days=config["TIME_RANGE_DAYS"])
        }

    if config['ENABLE_PLAY_COUNT_BY_MONTH']:
        descriptions['play_count_by_month.png'] = {
            'title': translations['play_count_by_month_title'],
            'description': translations['play_count_by_month_description']
        }

    for filename, details in descriptions.items():
        file_path = os.path.join(img_folder, today, filename)
        embed = discord.Embed(
            title=details['title'],
            description=f"{details['description']}\n\n{translations['next_update'].format(next_update=next_update_discord)}",
            color=0x3498db
        )
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=translations['embed_footer'].format(now=now))
        with open(file_path, 'rb') as f:
            await channel.send(file=discord.File(f, filename), embed=embed)

# Function to delete bot messages
async def delete_bot_messages(channel):
    async for message in channel.history(limit=200):
        if message.author == channel.guild.me:
            await message.delete()
