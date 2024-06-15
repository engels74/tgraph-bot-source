import os
import shutil
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from matplotlib.ticker import MaxNLocator

# Configuration
TAUTULLI_API_KEY = 'your_tautulli_api_key'
TAUTULLI_URL = 'http://your_tautulli_ip:port/api/v2'
DISCORD_WEBHOOK_URL = 'your_discord_webhook_url'
IMG_FOLDER = 'img'
KEEP_DAYS = 7  # Number of days of subfolders to keep
TIME_RANGE_DAYS = 30  # Time range for fetching data in days

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
    post_to_discord(filepath)

# Post an image to Discord
def post_to_discord(filepath):
    with open(filepath, 'rb') as f:
        response = requests.post(DISCORD_WEBHOOK_URL, files={'file': f})
    if response.status_code in [200, 204]:
        print(f'Successfully posted {os.path.basename(filepath)} to Discord')
    else:
        print(f'Failed to post {os.path.basename(filepath)} to Discord: {response.status_code}')

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

# Main function
def main():
    # Ensure base folder exists
    ensure_folder_exists(IMG_FOLDER)
    
    # Create dated subfolder
    today = datetime.today().strftime('%Y-%m-%d')
    dated_folder = os.path.join(IMG_FOLDER, today)
    ensure_folder_exists(dated_folder)
    
    # Fetch data and generate graphs
    data = fetch_all_data()
    generate_graphs(data, dated_folder)
    
    # Cleanup old folders
    cleanup_old_folders(IMG_FOLDER, KEEP_DAYS)

if __name__ == '__main__':
    main()

# Tautulli Graph Bot
# <https://github.com/engels74/tautulli-graph-bot
# A script/bot for posting Tautulli graphs to a Discord webhook.
# Copyright (C) 2024 - engels74
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Contact: engels74@marx.ps