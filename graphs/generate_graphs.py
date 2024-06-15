import os
import shutil
import requests
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.ticker import MaxNLocator
from config.config import TAUTULLI_API_KEY, TAUTULLI_URL, TIME_RANGE_DAYS

# Helper function to fetch data from Tautulli
def fetch_tautulli_data(cmd, params={}):
    params.update({
        'apikey': TAUTULLI_API_KEY,
        'cmd': cmd,
        'time_range': TIME_RANGE_DAYS  # Set time range based on the configuration
    })
    response = requests.get(TAUTULLI_URL, params=params)
    return response.json()

# Fetch data
def fetch_all_data():
    data = {}
    data['daily_play_count'] = fetch_tautulli_data('get_plays_by_date')
    data['play_count_by_dayofweek'] = fetch_tautulli_data('get_plays_by_dayofweek')
    data['play_count_by_hourofday'] = fetch_tautulli_data('get_plays_by_hourofday')
    data['top_10_platforms'] = fetch_tautulli_data('get_plays_by_top_10_platforms')
    data['top_10_users'] = fetch_tautulli_data('get_plays_by_top_10_users')
    return data

# Generate graphs
def generate_graphs(data, folder):
    plt.figure(figsize=(14, 8))  # Increase figure size
    
    # Daily Play Count by Media Type
    daily_play_count = data['daily_play_count']['response']['data']
    dates = daily_play_count['categories']
    series = daily_play_count['series']
    for serie in series:
        plt.plot(dates, serie['data'], label=serie['name'])
    plt.xlabel('Date')
    plt.ylabel('Plays')
    plt.title(f'Daily Play Count by Media Type (Last {TIME_RANGE_DAYS} days)')
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels and align them to the right
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis has only whole numbers
    plt.legend()
    plt.tight_layout(pad=3)  # Ensure everything fits within the figure and add padding
    save_and_post_graph(folder, 'daily_play_count.png')
    
    plt.figure(figsize=(14, 8))  # Reset figure size for next plot
    
    # Play Count by Day of Week
    play_count_by_dayofweek = data['play_count_by_dayofweek']['response']['data']
    days = play_count_by_dayofweek['categories']
    series = play_count_by_dayofweek['series']
    for serie in series:
        plt.plot(days, serie['data'], label=serie['name'])
    plt.xlabel('Day of Week')
    plt.ylabel('Plays')
    plt.title(f'Play Count by Day of Week (Last {TIME_RANGE_DAYS} days)')
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels and align them to the right
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis has only whole numbers
    plt.legend()
    plt.tight_layout(pad=3)  # Ensure everything fits within the figure and add padding
    save_and_post_graph(folder, 'play_count_by_dayofweek.png')
    
    plt.figure(figsize=(14, 8))  # Reset figure size for next plot
    
    # Play Count by Hour of Day
    play_count_by_hourofday = data['play_count_by_hourofday']['response']['data']
    hours = play_count_by_hourofday['categories']
    series = play_count_by_hourofday['series']
    for serie in series:
        plt.plot(hours, serie['data'], label=serie['name'])
    plt.xlabel('Hour of Day')
    plt.ylabel('Plays')
    plt.title(f'Play Count by Hour of Day (Last {TIME_RANGE_DAYS} days)')
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels and align them to the right
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis has only whole numbers
    plt.legend()
    plt.tight_layout(pad=3)  # Ensure everything fits within the figure and add padding
    save_and_post_graph(folder, 'play_count_by_hourofday.png')
    
    plt.figure(figsize=(14, 8))  # Reset figure size for next plot
    
    # Play Count by Top 10 Platforms
    top_10_platforms = data['top_10_platforms']['response']['data']
    platforms = top_10_platforms['categories']
    series = top_10_platforms['series']
    for serie in series:
        plt.bar(platforms, serie['data'], label=serie['name'])
    plt.xlabel('Platform')
    plt.ylabel('Plays')
    plt.title(f'Play Count by Top 10 Platforms (Last {TIME_RANGE_DAYS} days)')
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels and align them to the right
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis has only whole numbers
    plt.legend()
    plt.tight_layout(pad=3)  # Ensure everything fits within the figure and add padding
    save_and_post_graph(folder, 'top_10_platforms.png')
    
    plt.figure(figsize=(14, 8))  # Reset figure size for next plot
    
    # Play Count by Top 10 Users
    top_10_users = data['top_10_users']['response']['data']
    users = top_10_users['categories']
    series = top_10_users['series']
    for serie in series:
        plt.bar(users, serie['data'], label=serie['name'])
    plt.xlabel('User')
    plt.ylabel('Plays')
    plt.title(f'Play Count by Top 10 Users (Last {TIME_RANGE_DAYS} days)')
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels and align them to the right
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis has only whole numbers
    plt.legend()
    plt.tight_layout(pad=3)  # Ensure everything fits within the figure and add padding
    save_and_post_graph(folder, 'top_10_users.png')

# Save and post graph to Discord
def save_and_post_graph(folder, filename):
    filepath = os.path.join(folder, filename)
    plt.savefig(filepath)
    plt.clf()  # Clear the current figure

# Ensure the image folder exists
def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

# Cleanup old folders
def cleanup_old_folders(base_folder, keep_days):
    folders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
    folders.sort(reverse=True)
    for folder in folders[keep_days:]:
        shutil.rmtree(os.path.join(base_folder, folder))
