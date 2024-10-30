# config/modules/constants.py

"""
Constant definitions for TGraph Bot configuration.
Separates configuration structure definitions from processing logic.
"""

# Configuration sections with their headers and keys
CONFIG_SECTIONS = {
    "basic": {
        "header": "# Basic settings",
        "keys": [
            "TAUTULLI_API_KEY",
            "TAUTULLI_URL",
            "DISCORD_TOKEN",
            "CHANNEL_ID",
            "UPDATE_DAYS",
            "FIXED_UPDATE_TIME",
            "KEEP_DAYS",
            "TIME_RANGE_DAYS",
            "LANGUAGE",
        ],
    },
    "graph_options": {
        "header": "\n# Graph options",
        "keys": [
            "CENSOR_USERNAMES",
            "ENABLE_DAILY_PLAY_COUNT",
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
            "ENABLE_TOP_10_PLATFORMS",
            "ENABLE_TOP_10_USERS",
            "ENABLE_PLAY_COUNT_BY_MONTH",
        ],
    },
    "graph_colors": {
        "header": "\n# Graph colors",
        "keys": [
            "TV_COLOR",
            "MOVIE_COLOR",
            "ANNOTATION_COLOR",
            "ANNOTATION_OUTLINE_COLOR",
            "ENABLE_ANNOTATION_OUTLINE",
        ],
    },
    "annotation_options": {
        "header": "\n# Annotation options",
        "keys": [
            "ANNOTATE_DAILY_PLAY_COUNT",
            "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK",
            "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
            "ANNOTATE_TOP_10_PLATFORMS",
            "ANNOTATE_TOP_10_USERS",
            "ANNOTATE_PLAY_COUNT_BY_MONTH",
        ],
    },
    "cooldown_options": {
        "header": "\n# Command cooldown options",
        "keys": [
            "CONFIG_COOLDOWN_MINUTES",
            "CONFIG_GLOBAL_COOLDOWN_SECONDS",
            "UPDATE_GRAPHS_COOLDOWN_MINUTES",
            "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS",
            "MY_STATS_COOLDOWN_MINUTES",
            "MY_STATS_GLOBAL_COOLDOWN_SECONDS",
        ],
    },
}
