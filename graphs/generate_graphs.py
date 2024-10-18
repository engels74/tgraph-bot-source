# graphs/generate_graphs.py
import asyncio
import discord
import logging
import matplotlib.pyplot as plt
import os
import requests
import shutil
from datetime import datetime, timedelta
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator


def fetch_tautulli_data(cmd, params=None, config=None):
    now = datetime.now().astimezone()
    if params is None:
        params = {}
    start_date = now - timedelta(days=config["TIME_RANGE_DAYS"])
    params.update(
        {
            "apikey": config["TAUTULLI_API_KEY"],
            "cmd": cmd,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": now.strftime("%Y-%m-%d"),
        }
    )
    response = requests.get(config["TAUTULLI_URL"], params=params)
    return response.json()


def fetch_and_validate_data(api_action, params, config, error_message, translations, required_keys=None):
    data = fetch_tautulli_data(api_action, params, config)
    if data is None:
        logging.error(translations["error_fetching_data"])
        return None
    if not data or "response" not in data or "data" not in data["response"]:
        logging.error(translations[error_message])
        return None
    data_content = data["response"]["data"]
    if required_keys:
        for key in required_keys:
            if key not in data_content:
                logging.error(
                    translations["error_missing_key"].format(key=key, api_action=api_action)
                )
                return None
    return data_content


def fetch_all_data(config, translations):
    data = {}
    features = [
        (
            "ENABLE_DAILY_PLAY_COUNT",
            "daily_play_count",
            "get_plays_by_date",
            {"time_range": config["TIME_RANGE_DAYS"]},
            "error_fetch_daily_play_count",
            ["series"],
        ),
        (
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
            "play_count_by_dayofweek",
            "get_plays_by_dayofweek",
            {"time_range": config["TIME_RANGE_DAYS"]},
            "error_fetch_play_count_dayofweek",
            ["series"],
        ),
        (
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
            "play_count_by_hourofday",
            "get_plays_by_hourofday",
            {"time_range": config["TIME_RANGE_DAYS"]},
            "error_fetch_play_count_hourofday",
            ["series"],
        ),
        (
            "ENABLE_TOP_10_PLATFORMS",
            "top_10_platforms",
            "get_plays_by_top_10_platforms",
            {"time_range": config["TIME_RANGE_DAYS"]},
            "error_fetch_top_10_platforms",
            ["categories", "series"],
        ),
        (
            "ENABLE_TOP_10_USERS",
            "top_10_users",
            "get_plays_by_top_10_users",
            {"time_range": config["TIME_RANGE_DAYS"]},
            "error_fetch_top_10_users",
            ["categories", "series"],
        ),
        (
            "ENABLE_PLAY_COUNT_BY_MONTH",
            "play_count_by_month",
            "get_plays_per_month",
            {"time_range": 12, "y_axis": "plays"},
            "error_fetch_play_count_month",
            ["categories", "series"],
        ),
    ]
    for flag, key, cmd, params, error_msg, required_keys in features:
        if config[flag]:
            data[key] = fetch_and_validate_data(
                cmd, params, config, error_msg, translations, required_keys
            )
    return data


def get_series_color(series_name, TV_COLOR, MOVIE_COLOR):
    if series_name == "TV":
        return TV_COLOR
    elif series_name == "Movies":
        return MOVIE_COLOR
    else:
        return "#1f77b4"


def censor_username(username, should_censor):
    if not should_censor:
        return username
    length = len(username)
    if length <= 2:
        return "*" * length
    half_length = length // 2
    return username[:half_length] + "*" * (length - half_length)


def generate_graphs(data, folder, current_translations, current_config):
    config = current_config
    translations = current_translations

    TV_COLOR = config["TV_COLOR"].strip('"')
    MOVIE_COLOR = config["MOVIE_COLOR"].strip('"')
    ANNOTATION_COLOR = config["ANNOTATION_COLOR"].strip('"')

    if config["ENABLE_DAILY_PLAY_COUNT"]:
        generate_daily_play_count_graph(
            data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
        )

    if config["ENABLE_PLAY_COUNT_BY_DAYOFWEEK"]:
        generate_play_count_by_dayofweek_graph(
            data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
        )

    if config["ENABLE_PLAY_COUNT_BY_HOUROFDAY"]:
        generate_play_count_by_hourofday_graph(
            data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
        )

    if config["ENABLE_TOP_10_PLATFORMS"]:
        generate_top_10_platforms_graph(
            data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
        )

    if config["ENABLE_TOP_10_USERS"]:
        generate_top_10_users_graph(
            data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
        )

    if config["ENABLE_PLAY_COUNT_BY_MONTH"]:
        generate_play_count_by_month_graph(
            data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
        )


def generate_daily_play_count_graph(
    data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    daily_play_count = data["daily_play_count"]

    if not daily_play_count:
        logging.warning(translations["warning_empty_series_daily_play_count"])
        return

    series = daily_play_count["series"]

    end_date = datetime.now().astimezone()
    start_date = end_date - timedelta(days=config["TIME_RANGE_DAYS"] - 1)
    dates = [start_date + timedelta(days=i) for i in range(config["TIME_RANGE_DAYS"])]

    date_strs = [date.strftime("%Y-%m-%d") for date in dates]
    date_data_map = {date: 0 for date in date_strs}

    for serie in series:
        complete_data = [0] * len(dates)
        for date, value in zip(daily_play_count["categories"], serie["data"]):
            if date in date_data_map:
                date_data_map[date] = value
        complete_data = [date_data_map[date] for date in date_strs]
        color = get_series_color(serie["name"], TV_COLOR, MOVIE_COLOR)
        plt.plot(dates, complete_data, label=serie["name"], marker="o", color=color)

        if config["ANNOTATE_DAILY_PLAY_COUNT"]:
            for i, value in enumerate(complete_data):
                if value > 0:
                    plt.text(
                        dates[i],
                        value + 0.5,
                        f"{value}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color=ANNOTATION_COLOR,
                    )

    plt.xlabel(translations["daily_play_count_xlabel"], fontweight="bold")
    plt.ylabel(translations["daily_play_count_ylabel"], fontweight="bold")
    plt.title(
        translations["daily_play_count_title"].format(days=config["TIME_RANGE_DAYS"]),
        fontweight="bold",
    )

    ax = plt.gca()
    ax.set_xticks(dates)
    ax.set_xticklabels(date_strs, rotation=45, ha="right")
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plt.tight_layout(pad=3)
    save_and_post_graph(folder, "daily_play_count.png", translations)
    plt.close()


def generate_play_count_by_dayofweek_graph(
    data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    play_count_by_dayofweek = data["play_count_by_dayofweek"]

    if not play_count_by_dayofweek:
        logging.warning(translations["warning_empty_series_play_count_by_dayofweek"])
        return

    series = play_count_by_dayofweek["series"]

    days = list(range(7))
    day_labels = [translations[f"day_{i}"] for i in range(7)]

    for serie in series:
        color = get_series_color(serie["name"], TV_COLOR, MOVIE_COLOR)
        plt.plot(days, serie["data"], label=serie["name"], marker="o", color=color)
        if config["ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK"]:
            for i, value in enumerate(serie["data"]):
                if value > 0:
                    plt.text(
                        days[i],
                        value + 0.5,
                        f"{value}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color=ANNOTATION_COLOR,
                    )

    plt.xlabel(translations["play_count_by_dayofweek_xlabel"], fontweight="bold")
    plt.ylabel(translations["play_count_by_dayofweek_ylabel"], fontweight="bold")
    plt.title(
        translations["play_count_by_dayofweek_title"].format(
            days=config["TIME_RANGE_DAYS"]
        ),
        fontweight="bold",
    )
    plt.xticks(days, day_labels, ha="center")
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plt.tight_layout(pad=3)
    save_and_post_graph(folder, "play_count_by_dayofweek.png", translations)
    plt.close()


def generate_play_count_by_hourofday_graph(
    data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    play_count_by_hourofday = data["play_count_by_hourofday"]

    if not play_count_by_hourofday:
        logging.warning(translations["warning_empty_series_play_count_by_hourofday"])
        return

    series = play_count_by_hourofday["series"]

    hours = list(range(24))

    for serie in series:
        color = get_series_color(serie["name"], TV_COLOR, MOVIE_COLOR)
        plt.plot(hours, serie["data"], label=serie["name"], marker="o", color=color)
        if config["ANNOTATE_PLAY_COUNT_BY_HOUROFDAY"]:
            for i, value in enumerate(serie["data"]):
                if value > 0:
                    plt.text(
                        hours[i],
                        value + 0.5,
                        f"{value}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color=ANNOTATION_COLOR,
                    )

    plt.xlabel(translations["play_count_by_hourofday_xlabel"], fontweight="bold")
    plt.ylabel(translations["play_count_by_hourofday_ylabel"], fontweight="bold")
    plt.title(
        translations["play_count_by_hourofday_title"].format(
            days=config["TIME_RANGE_DAYS"]
        ),
        fontweight="bold",
    )
    plt.xticks(hours, ha="center")
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plt.tight_layout(pad=3)
    save_and_post_graph(folder, "play_count_by_hourofday.png", translations)
    plt.close()


def generate_top_10_platforms_graph(
    data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    top_10_platforms = data["top_10_platforms"]

    if not top_10_platforms:
        logging.warning(translations["warning_empty_series_top_10_platforms"])
        return

    platforms = top_10_platforms["categories"]
    series = top_10_platforms["series"]

    for serie in series:
        color = get_series_color(serie["name"], TV_COLOR, MOVIE_COLOR)
        plt.bar(platforms, serie["data"], label=serie["name"], color=color)
        if config["ANNOTATE_TOP_10_PLATFORMS"]:
            for i, v in enumerate(serie["data"]):
                plt.text(
                    i,
                    v + 0.5,
                    str(v),
                    color=ANNOTATION_COLOR,
                    fontweight="bold",
                    ha="center",
                    va="bottom",
                )

    plt.xlabel(translations["top_10_platforms_xlabel"], fontweight="bold")
    plt.ylabel(translations["top_10_platforms_ylabel"], fontweight="bold")
    plt.title(
        translations["top_10_platforms_title"].format(days=config["TIME_RANGE_DAYS"]),
        fontweight="bold",
    )
    plt.xticks(rotation=45, ha="right")
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plt.tight_layout(pad=3)
    save_and_post_graph(folder, "top_10_platforms.png", translations)
    plt.close()


def generate_top_10_users_graph(
    data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    top_10_users = data["top_10_users"]

    if not top_10_users:
        logging.warning(translations["warning_empty_series_top_10_users"])
        return

    users = top_10_users["categories"]
    series = top_10_users["series"]

    combined_data = []
    for i, user in enumerate(users):
        tv_plays = (
            series[0]["data"][i] if series[0]["name"] == "TV" else series[1]["data"][i]
        )
        movie_plays = (
            series[1]["data"][i]
            if series[1]["name"] == "Movies"
            else series[0]["data"][i]
        )
        total_plays = tv_plays + movie_plays
        combined_data.append((user, tv_plays, movie_plays, total_plays))

    combined_data.sort(key=lambda x: x[3], reverse=True)

    sorted_users = [item[0] for item in combined_data]
    sorted_tv_data = [item[1] for item in combined_data]
    sorted_movie_data = [item[2] for item in combined_data]

    censored_users = [
        censor_username(user, config["CENSOR_USERNAMES"]) for user in sorted_users
    ]

    plt.bar(censored_users, sorted_movie_data, label="Movies", color=MOVIE_COLOR)
    plt.bar(
        censored_users,
        sorted_tv_data,
        bottom=sorted_movie_data,
        label="TV",
        color=TV_COLOR,
    )

    if config["ANNOTATE_TOP_10_USERS"]:
        for i, (tv, movie) in enumerate(zip(sorted_tv_data, sorted_movie_data)):
            total = tv + movie
            plt.text(
                i,
                total + 0.5,
                str(total),
                color=ANNOTATION_COLOR,
                fontweight="bold",
                ha="center",
                va="bottom",
            )

    plt.xlabel(translations["top_10_users_xlabel"], fontweight="bold")
    plt.ylabel(translations["top_10_users_ylabel"], fontweight="bold")
    plt.title(
        translations["top_10_users_title"].format(days=config["TIME_RANGE_DAYS"]),
        fontweight="bold",
    )
    plt.xticks(rotation=45, ha="right")
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plt.tight_layout(pad=3)
    save_and_post_graph(folder, "top_10_users.png", translations)
    plt.close()


def generate_play_count_by_month_graph(
    data, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    play_count_by_month = data["play_count_by_month"]

    if not play_count_by_month:
        logging.warning(translations["warning_empty_data_play_count_by_month"])
        return

    months = play_count_by_month["categories"]
    series = play_count_by_month["series"]

    movie_data = [0] * len(months)
    tv_data = [0] * len(months)

    for serie in series:
        if serie["name"] == "Movies":
            movie_data = serie["data"]
        elif serie["name"] == "TV":
            tv_data = serie["data"]

    filtered_months = []
    filtered_movie_data = []
    filtered_tv_data = []

    for i in range(len(months)):
        if movie_data[i] > 0 or tv_data[i] > 0:
            filtered_months.append(months[i])
            filtered_movie_data.append(movie_data[i])
            filtered_tv_data.append(tv_data[i])

    if not filtered_months:
        logging.warning(translations["warning_no_play_data_play_count_by_month"])
        return

    bar_width = 0.4
    bar_positions = range(len(filtered_months))

    plt.bar(
        bar_positions,
        filtered_movie_data,
        width=bar_width,
        label="Movies",
        color=get_series_color("Movies", TV_COLOR, MOVIE_COLOR),
    )
    plt.bar(
        bar_positions,
        filtered_tv_data,
        width=bar_width,
        bottom=filtered_movie_data,
        label="TV",
        color=get_series_color("TV", TV_COLOR, MOVIE_COLOR),
    )

    if config["ANNOTATE_PLAY_COUNT_BY_MONTH"]:
        for i, v in enumerate(filtered_movie_data):
            plt.text(
                i,
                v + 0.5,
                str(v),
                color=ANNOTATION_COLOR,
                fontweight="bold",
                ha="center",
                va="bottom",
            )

        for i, v in enumerate(filtered_tv_data):
            plt.text(
                i,
                v + filtered_movie_data[i] + 0.5,
                str(v),
                color=ANNOTATION_COLOR,
                fontweight="bold",
                ha="center",
                va="bottom",
            )

    plt.xlabel(translations["play_count_by_month_xlabel"], fontweight="bold")
    plt.ylabel(translations["play_count_by_month_ylabel"], fontweight="bold")
    plt.title(translations["play_count_by_month_title"], fontweight="bold")
    plt.xticks(bar_positions, filtered_months, rotation=45, ha="right")
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plt.tight_layout(pad=3)
    save_and_post_graph(folder, "play_count_by_month.png", translations)
    plt.close()


def save_and_post_graph(folder, filename, translations):
    filepath = os.path.join(folder, filename)
    plt.savefig(filepath)
    plt.close()  # Close the figure to release memory
    logging.info(translations["log_posted_message"].format(filename=filename))


def ensure_folder_exists(folder, translations):
    if not os.path.exists(folder):
        os.makedirs(folder)
    logging.info(translations["log_ensured_folder_exists"])


def cleanup_old_folders(base_folder, keep_days, translations):
    folders = [
        f
        for f in os.listdir(base_folder)
        if os.path.isdir(os.path.join(base_folder, f))
    ]
    folders.sort(reverse=True)
    for folder in folders[keep_days:]:
        try:
            shutil.rmtree(os.path.join(base_folder, folder))
        except Exception as e:
            logging.error(f"Error deleting folder {folder}: {str(e)}")
    logging.info(translations["log_cleaned_up_old_folders"])


async def update_and_post_graphs(bot, current_translations, current_config):
    translations = current_translations
    config = current_config

    channel = bot.get_channel(config["CHANNEL_ID"])
    await delete_bot_messages(channel)

    try:
        ensure_folder_exists(bot.img_folder, translations)

        today = datetime.today().strftime("%Y-%m-%d")
        dated_folder = os.path.join(bot.img_folder, today)
        ensure_folder_exists(dated_folder, translations)

        data = fetch_all_data(config, translations)
        generate_graphs(data, dated_folder, translations, config)

        # Update the tracker before posting graphs
        bot.update_tracker.update()
        next_update = bot.update_tracker.next_update

        await post_graphs(channel, bot.img_folder, translations, next_update, config)
        next_update_log = bot.update_tracker.get_next_update_readable()
        logging.info(
            translations["log_graphs_updated_posted"].format(
                next_update=next_update_log
            )
        )
        cleanup_old_folders(bot.img_folder, config["KEEP_DAYS"], translations)
    except Exception as e:
        logging.error(translations["error_update_post_graphs"].format(error=str(e)))
        raise


async def post_graphs(channel, img_folder, translations, next_update, config):
    now = datetime.now().astimezone().strftime("%Y-%m-%d at %H:%M:%S")
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    next_update_discord = f"<t:{int(next_update.timestamp())}:R>"
    descriptions = {}

    if config["ENABLE_DAILY_PLAY_COUNT"]:
        descriptions["daily_play_count.png"] = {
            "title": translations["daily_play_count_title"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
            "description": translations["daily_play_count_description"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
        }

    if config["ENABLE_PLAY_COUNT_BY_DAYOFWEEK"]:
        descriptions["play_count_by_dayofweek.png"] = {
            "title": translations["play_count_by_dayofweek_title"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
            "description": translations["play_count_by_dayofweek_description"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
        }

    if config["ENABLE_PLAY_COUNT_BY_HOUROFDAY"]:
        descriptions["play_count_by_hourofday.png"] = {
            "title": translations["play_count_by_hourofday_title"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
            "description": translations["play_count_by_hourofday_description"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
        }

    if config["ENABLE_TOP_10_PLATFORMS"]:
        descriptions["top_10_platforms.png"] = {
            "title": translations["top_10_platforms_title"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
            "description": translations["top_10_platforms_description"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
        }

    if config["ENABLE_TOP_10_USERS"]:
        descriptions["top_10_users.png"] = {
            "title": translations["top_10_users_title"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
            "description": translations["top_10_users_description"].format(
                days=config["TIME_RANGE_DAYS"]
            ),
        }

    if config["ENABLE_PLAY_COUNT_BY_MONTH"]:
        descriptions["play_count_by_month.png"] = {
            "title": translations["play_count_by_month_title"],
            "description": translations["play_count_by_month_description"],
        }

    for filename, details in descriptions.items():
        file_path = os.path.join(img_folder, today, filename)
        embed = discord.Embed(
            title=details["title"],
            description=f"{details['description']}\n\n{translations['next_update'].format(next_update=next_update_discord)}",
            color=0x3498DB,
        )
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=translations["embed_footer"].format(now=now))
        with open(file_path, "rb") as f:
            await channel.send(file=discord.File(f, filename), embed=embed)


async def delete_bot_messages(channel):
    async for message in channel.history(limit=200):
        if message.author == channel.guild.me:
            await message.delete()
            await asyncio.sleep(1)
