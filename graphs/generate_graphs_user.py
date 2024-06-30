# graphs/generate_graphs_user.py
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from matplotlib.ticker import MaxNLocator
from matplotlib.dates import DateFormatter
from matplotlib.font_manager import FontProperties
from graphs.generate_graphs import fetch_tautulli_data, ensure_folder_exists, censor_username
import logging
from i18n import load_translations

# Initialize translations globally
translations = None

def generate_user_graphs(user_id, img_folder, config, current_translations):
    global translations
    translations = current_translations

    graph_files = []
    today = datetime.today().strftime('%Y-%m-%d')
    user_folder = os.path.join(img_folder, today, f"user_{user_id}")
    ensure_folder_exists(user_folder)

    if config['ENABLE_DAILY_PLAY_COUNT']:
        graph_files.append(generate_daily_play_count(user_id, user_folder, config))
    
    if config['ENABLE_PLAY_COUNT_BY_DAYOFWEEK']:
        graph_files.append(generate_play_count_by_dayofweek(user_id, user_folder, config))
    
    if config['ENABLE_PLAY_COUNT_BY_HOUROFDAY']:
        graph_files.append(generate_play_count_by_hourofday(user_id, user_folder, config))
    
    if config['ENABLE_TOP_10_PLATFORMS']:
        graph_files.append(generate_top_10_platforms(user_id, user_folder, config))
    
    if config['ENABLE_PLAY_COUNT_BY_MONTH']:
        graph_files.append(generate_play_count_by_month(user_id, user_folder, config))

    return [file for file in graph_files if file is not None]

def generate_daily_play_count(user_id, folder, config):
    plt.figure(figsize=(14, 8))
    data = fetch_tautulli_data('get_plays_by_date', {'time_range': config['TIME_RANGE_DAYS'], 'user_id': user_id})
    
    if not data or 'data' not in data['response']:
        logging.error(translations['error_fetch_daily_play_count'].format(user_id=user_id))
        return None

    daily_play_count = data['response']['data']
    
    end_date = datetime.now().astimezone()
    start_date = end_date - timedelta(days=config['TIME_RANGE_DAYS'] - 1)
    dates = [start_date + timedelta(days=i) for i in range(config['TIME_RANGE_DAYS'])]
    
    date_strs = [date.strftime('%Y-%m-%d') for date in dates]
    date_data_map = {date: 0 for date in date_strs}
    
    series = daily_play_count['series']
    
    for serie in series:
        complete_data = [0] * len(dates)
        for date, value in zip(daily_play_count['categories'], serie['data']):
            if date in date_data_map:
                date_data_map[date] = value
        complete_data = [date_data_map[date] for date in date_strs]
        plt.plot(dates, complete_data, label=serie['name'], marker='o')
        
        if config['ANNOTATE_DAILY_PLAY_COUNT']:
            for i, value in enumerate(complete_data):
                if value > 0:
                    plt.text(dates[i], value + 0.5, f'{value}', ha='center', va='bottom', fontsize=8, color='red')
    
    plt.xlabel(translations['daily_play_count_xlabel'], fontweight='bold')
    plt.ylabel(translations['daily_play_count_ylabel'], fontweight='bold')
    plt.title(translations['daily_play_count_title'].format(days=config["TIME_RANGE_DAYS"]), fontweight='bold')
    
    ax = plt.gca()
    ax.set_xticks(dates)
    ax.set_xticklabels(date_strs, rotation=45, ha='right')
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plt.tight_layout(pad=3)
    
    filepath = os.path.join(folder, 'daily_play_count.png')
    plt.savefig(filepath)
    plt.close()
    return filepath

def generate_play_count_by_dayofweek(user_id, folder, config):
    plt.figure(figsize=(14, 8))
    data = fetch_tautulli_data('get_plays_by_dayofweek', {'time_range': config['TIME_RANGE_DAYS'], 'user_id': user_id})
    
    if not data or 'data' not in data['response']:
        logging.error(translations['error_fetch_play_count_dayofweek'].format(user_id=user_id))
        return None

    play_count_by_dayofweek = data['response']['data']
    days = list(range(7))
    day_labels = [translations[f'day_{i}'] for i in range(7)]
    series = play_count_by_dayofweek['series']
    
    for serie in series:
        plt.plot(days, serie['data'], label=serie['name'], marker='o')
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
    
    filepath = os.path.join(folder, 'play_count_by_dayofweek.png')
    plt.savefig(filepath)
    plt.close()
    return filepath

def generate_play_count_by_hourofday(user_id, folder, config):
    plt.figure(figsize=(14, 8))
    data = fetch_tautulli_data('get_plays_by_hourofday', {'time_range': config['TIME_RANGE_DAYS'], 'user_id': user_id})
    
    if not data or 'data' not in data['response']:
        logging.error(translations['error_fetch_play_count_hourofday'].format(user_id=user_id))
        return None

    play_count_by_hourofday = data['response']['data']
    hours = list(range(24))
    series = play_count_by_hourofday['series']
    
    for serie in series:
        plt.plot(hours, serie['data'], label=serie['name'], marker='o')
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
    
    filepath = os.path.join(folder, 'play_count_by_hourofday.png')
    plt.savefig(filepath)
    plt.close()
    return filepath

def generate_top_10_platforms(user_id, folder, config):
    plt.figure(figsize=(14, 8))
    data = fetch_tautulli_data('get_plays_by_top_10_platforms', {'time_range': config['TIME_RANGE_DAYS'], 'user_id': user_id})
    
    if not data or 'data' not in data['response']:
        logging.error(translations['error_fetch_top_10_platforms'].format(user_id=user_id))
        return None

    top_10_platforms = data['response']['data']
    platforms = top_10_platforms['categories']
    series = top_10_platforms['series']
    
    for serie in series:
        plt.bar(platforms, serie['data'], label=serie['name'])
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
    
    filepath = os.path.join(folder, 'top_10_platforms.png')
    plt.savefig(filepath)
    plt.close()
    return filepath

def generate_play_count_by_month(user_id, folder, config):
    plt.figure(figsize=(14, 8))
    data = fetch_tautulli_data('get_plays_per_month', {'time_range': 12, 'y_axis': 'plays', 'user_id': user_id})
    
    if not data or 'data' not in data['response']:
        logging.error(translations['error_fetch_play_count_month'].format(user_id=user_id))
        return None

    play_count_by_month = data['response']['data']

    months = play_count_by_month.get('categories', [])
    series = play_count_by_month.get('series', [])

    if not months or not series:
        logging.warning(translations['graphs_no_monthly_data'])
        return None

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

    bar_width = 0.4
    bar_positions = range(len(filtered_months))

    plt.bar(bar_positions, filtered_movie_data, width=bar_width, label='Movies')
    plt.bar(bar_positions, filtered_tv_data, width=bar_width, bottom=filtered_movie_data, label='TV')

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
    
    filepath = os.path.join(folder, 'play_count_by_month.png')
    plt.savefig(filepath)
    plt.close()
    return filepath
