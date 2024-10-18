# graphs/generate_graphs_user.py
import logging
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
from graphs.generate_graphs import fetch_tautulli_data, ensure_folder_exists
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator


def fetch_and_validate_data(api_action, params, config, error_message, translations):
    data = fetch_tautulli_data(api_action, params, config)
    if not data or "data" not in data["response"]:
        logging.error(error_message)
        return None
    return data["response"]["data"]


def generate_user_graphs(user_id, img_folder, config, current_translations):
    graph_files = []
    today = datetime.today().strftime("%Y-%m-%d")
    user_folder = os.path.join(img_folder, today, f"user_{user_id}")
    ensure_folder_exists(user_folder)

    # Define colors
    TV_COLOR = config["TV_COLOR"].strip('"')
    MOVIE_COLOR = config["MOVIE_COLOR"].strip('"')
    ANNOTATION_COLOR = config["ANNOTATION_COLOR"].strip('"')

    if config["ENABLE_DAILY_PLAY_COUNT"]:
        graph_files.append(
            generate_daily_play_count(
                user_id,
                user_folder,
                config,
                TV_COLOR,
                MOVIE_COLOR,
                ANNOTATION_COLOR,
                current_translations,
            )
        )

    if config["ENABLE_PLAY_COUNT_BY_DAYOFWEEK"]:
        graph_files.append(
            generate_play_count_by_dayofweek(
                user_id,
                user_folder,
                config,
                TV_COLOR,
                MOVIE_COLOR,
                ANNOTATION_COLOR,
                current_translations,
            )
        )

    if config["ENABLE_PLAY_COUNT_BY_HOUROFDAY"]:
        graph_files.append(
            generate_play_count_by_hourofday(
                user_id,
                user_folder,
                config,
                TV_COLOR,
                MOVIE_COLOR,
                ANNOTATION_COLOR,
                current_translations,
            )
        )

    if config["ENABLE_TOP_10_PLATFORMS"]:
        graph_files.append(
            generate_top_10_platforms(
                user_id,
                user_folder,
                config,
                TV_COLOR,
                MOVIE_COLOR,
                ANNOTATION_COLOR,
                current_translations,
            )
        )

    if config["ENABLE_PLAY_COUNT_BY_MONTH"]:
        graph_files.append(
            generate_play_count_by_month(
                user_id,
                user_folder,
                config,
                TV_COLOR,
                MOVIE_COLOR,
                ANNOTATION_COLOR,
                current_translations,
            )
        )

    return [file for file in graph_files if file is not None]


def generate_daily_play_count(
    user_id, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    daily_play_count = fetch_and_validate_data(
        "get_plays_by_date",
        {"time_range": config["TIME_RANGE_DAYS"], "user_id": user_id},
        config,
        translations["error_fetch_daily_play_count_user"].format(user_id=user_id),
        translations,
    )
    if daily_play_count is None:
        return None

    if "series" not in daily_play_count:
        logging.error(
            translations["error_missing_series_daily_play_count"].format(
                user_id=user_id
            )
        )
        return None

    series = daily_play_count["series"]

    if not series:
        logging.warning(
            translations["warning_empty_series_daily_play_count"].format(
                user_id=user_id
            )
        )
        return None

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
        color = TV_COLOR if serie["name"] == "TV" else MOVIE_COLOR
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

    filepath = os.path.join(folder, "daily_play_count.png")
    plt.savefig(filepath)
    plt.close()
    return filepath


def generate_play_count_by_dayofweek(
    user_id, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    play_count_by_dayofweek = fetch_and_validate_data(
        "get_plays_by_dayofweek",
        {"time_range": config["TIME_RANGE_DAYS"], "user_id": user_id},
        config,
        translations["error_fetch_play_count_dayofweek_user"].format(user_id=user_id),
        translations,
    )
    if play_count_by_dayofweek is None:
        return None

    if "series" not in play_count_by_dayofweek:
        logging.error(
            translations["error_missing_series_play_count_by_dayofweek"].format(
                user_id=user_id
            )
        )
        return None

    days = list(range(7))
    day_labels = [translations[f"day_{i}"] for i in range(7)]
    series = play_count_by_dayofweek["series"]

    if not series:
        logging.warning(
            translations["warning_empty_series_play_count_by_dayofweek"].format(
                user_id=user_id
            )
        )
        return None

    for serie in series:
        color = TV_COLOR if serie["name"] == "TV" else MOVIE_COLOR
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

    filepath = os.path.join(folder, "play_count_by_dayofweek.png")
    plt.savefig(filepath)
    plt.close()
    return filepath


def generate_play_count_by_hourofday(
    user_id, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    play_count_by_hourofday = fetch_and_validate_data(
        "get_plays_by_hourofday",
        {"time_range": config["TIME_RANGE_DAYS"], "user_id": user_id},
        config,
        translations["error_fetch_play_count_hourofday_user"].format(user_id=user_id),
        translations,
    )
    if play_count_by_hourofday is None:
        return None

    if "series" not in play_count_by_hourofday:
        logging.error(
            translations["error_missing_series_play_count_by_hourofday"].format(
                user_id=user_id
            )
        )
        return None

    hours = list(range(24))
    series = play_count_by_hourofday["series"]

    if not series:
        logging.warning(
            translations["warning_empty_series_play_count_by_hourofday"].format(
                user_id=user_id
            )
        )
        return None

    for serie in series:
        color = TV_COLOR if serie["name"] == "TV" else MOVIE_COLOR
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

    filepath = os.path.join(folder, "play_count_by_hourofday.png")
    plt.savefig(filepath)
    plt.close()
    return filepath


def generate_top_10_platforms(
    user_id, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    top_10_platforms = fetch_and_validate_data(
        "get_plays_by_top_10_platforms",
        {"time_range": config["TIME_RANGE_DAYS"], "user_id": user_id},
        config,
        translations["error_fetch_top_10_platforms_user"].format(user_id=user_id),
        translations,
    )
    if top_10_platforms is None:
        return None

    if "categories" not in top_10_platforms or "series" not in top_10_platforms:
        logging.error(
            translations["error_missing_data_top_10_platforms"].format(user_id=user_id)
        )
        return None

    platforms = top_10_platforms["categories"]
    series = top_10_platforms["series"]

    if not series:
        logging.warning(
            translations["warning_empty_series_top_10_platforms"].format(
                user_id=user_id
            )
        )
        return None

    for serie in series:
        color = TV_COLOR if serie["name"] == "TV" else MOVIE_COLOR
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

    filepath = os.path.join(folder, "top_10_platforms.png")
    plt.savefig(filepath)
    plt.close()
    return filepath


def generate_play_count_by_month(
    user_id, folder, config, TV_COLOR, MOVIE_COLOR, ANNOTATION_COLOR, translations
):
    plt.figure(figsize=(14, 8))
    play_count_by_month = fetch_and_validate_data(
        "get_plays_per_month",
        {"time_range": 12, "y_axis": "plays", "user_id": user_id},
        config,
        translations["error_fetch_play_count_month_user"].format(user_id=user_id),
        translations,
    )
    if play_count_by_month is None:
        return None

    if "categories" not in play_count_by_month or "series" not in play_count_by_month:
        logging.error(
            translations["error_missing_data_play_count_by_month"].format(
                user_id=user_id
            )
        )
        return None

    months = play_count_by_month["categories"]
    series = play_count_by_month["series"]

    if not months or not series:
        logging.warning(
            translations["warning_empty_data_play_count_by_month"].format(
                user_id=user_id
            )
        )
        return None

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
        logging.warning(
            translations["warning_no_play_data_play_count_by_month"].format(
                user_id=user_id
            )
        )
        return None

    bar_width = 0.4
    bar_positions = range(len(filtered_months))

    plt.bar(
        bar_positions,
        filtered_movie_data,
        width=bar_width,
        label="Movies",
        color=MOVIE_COLOR,
    )
    plt.bar(
        bar_positions,
        filtered_tv_data,
        width=bar_width,
        bottom=filtered_movie_data,
        label="TV",
        color=TV_COLOR,
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

    filepath = os.path.join(folder, "play_count_by_month.png")
    plt.savefig(filepath)
    plt.close()
    return filepath
