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
    })
    response = requests.get(TAUTULLI_URL, params=params)
    return response.json()

# Fetch data
def fetch_all_data():
    data = {}
    data['daily_play_count'] = fetch_tautulli_data('get_plays_by_date', {'time_range': TIME_RANGE_DAYS})
    data['play_count_by_dayofweek'] = fetch_tautulli_data('get_plays_by_dayofweek', {'time_range': TIME_RANGE_DAYS})
    data['play_count_by_hourofday'] = fetch_tautulli_data('get_plays_by_hourofday', {'time_range': TIME_RANGE_DAYS})
    data['top_10_platforms'] = fetch_tautulli_data('get_plays_by_top_10_platforms', {'time_range': TIME_RANGE_DAYS})
    data['top_10_users'] = fetch_tautulli_data('get_plays_by_top_10_users', {'time_range': TIME_RANGE_DAYS})
    data['play_count_by_month'] = fetch_tautulli_data('get_plays_per_month', {'time_range': 12, 'y_axis': 'plays'})  # Last 12 months
    return data

# Censor usernames
def censor_username(username):
    length = len(username)
    if length <= 2:
        return '*' * length
    half_length = length // 2
    return username[:half_length] + '*' * (length - half_length)

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
    censored_users = [censor_username(user) for user in users]
    for serie in series:
        plt.bar(censored_users, serie['data'], label=serie['name'])
    plt.xlabel('User')
    plt.ylabel('Plays')
    plt.title(f'Play Count by Top 10 Users (Last {TIME_RANGE_DAYS} days)')
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels and align them to the right
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis has only whole numbers
    plt.legend()
    plt.tight_layout(pad=3)  # Ensure everything fits within the figure and add padding
    save_and_post_graph(folder, 'top_10_users.png')

    # Play Count by Month (Last 12 months)
    play_count_by_month = data['play_count_by_month']['response']['data']

    months = play_count_by_month.get('categories', [])
    series = play_count_by_month.get('series', [])
    
    if not months or not series:
        print("No data available for play_count_by_month")
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
    plt.figure(figsize=(14, 8))  # Increase figure size
    bar_width = 0.4  # Width of the bars
    bar_positions = range(len(filtered_months))

    plt.bar(bar_positions, filtered_movie_data, width=bar_width, label='Movies')
    plt.bar(bar_positions, filtered_tv_data, width=bar_width, bottom=filtered_movie_data, label='TV')

    plt.xlabel('Month')
    plt.ylabel('Total Plays')
    plt.title('Total Play Count by Month (Last 12 months)')
    plt.xticks(bar_positions, filtered_months, rotation=45, ha='right')  # Rotate x-axis labels and align them to the right
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis has only whole numbers
    plt.legend()
    plt.tight_layout(pad=3)  # Ensure everything fits within the figure and add padding
    save_and_post_graph(folder, 'play_count_by_month.png')

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
