### TGraph Bot Project Overview

#### Introduction

TGraph Bot is a Discord bot designed to automatically generate and post Tautulli graphs to a specified Discord channel. It provides insightful visualizations and statistics about your Plex Media Server's activity and performance. The project emphasizes modern Python 3.13 features, a test-driven development approach, comprehensive internationalization support, and robust, non-blocking performance using the `discord.py` library.

#### Key Features

TGraph Bot offers:

-   **High-Quality Statistical Graphing:** Automated generation and scheduled posting of Tautulli graphs, using **Seaborn** on top of Matplotlib to create clean, modern, and aesthetically pleasing visualizations.
-   **Customization:** Customizable graph options including colors, grid settings, and annotations.
-   **Discord Integration:** Interactive Discord slash commands (e.g., `/about`, `/config`, `/my_stats`, `/update_graphs`, and `/uptime`) managed via a permission system, built using `discord.py`.
-   **User-Specific Statistics:** Generation of personal statistics with direct messaging support.
-   **Modern Configuration:** A robust configuration system powered by Pydantic for validation, typing, and default management.
-   **Internationalization:** Full i18n support using gettext-based translation files and Weblate integration.
-   **Resilience and Error Handling:** Proactive handling of API-related issues, including Tautulli API downtime and Discord rate limits, with graceful fallbacks.
-   **Test-Driven:** A commitment to extensive testing with pytest and best practices from modern Python.

#### Project Directory Structure

Below is a representative tree structure of the repository:

```
.
├── LICENSE
├── README.md
├── pyproject.toml
├── i18n.py
├── main.py
├── .weblate
├── bot/
│   ├── __init__.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── about.py
│   │   ├── config.py
│   │   ├── my_stats.py
│   │   ├── update_graphs.py
│   │   └── uptime.py
│   ├── extensions.py
│   ├── permission_checker.py
│   └── update_tracker.py
├── config/
│   ├── __init__.py
│   ├── manager.py
│   ├── config.yml.sample
│   └── schema.py
├── graphs/
│   ├── graph_manager.py
│   ├── user_graph_manager.py
│   └── graph_modules/
│       ├── __init__.py
│       ├── base_graph.py
│       ├── daily_play_count_graph.py
│       ├── data_fetcher.py
│       ├── graph_factory.py
│       ├── play_count_by_dayofweek_graph.py
│       ├── play_count_by_hourofday_graph.py
│       ├── play_count_by_month_graph.py
│       ├── top_10_platforms_graph.py
│       ├── top_10_users_graph.py
│       └── utils.py
├── locale/
│   ├── en/
│   │   └── LC_MESSAGES/
│   │       └── messages.po
│   └── messages.pot
└── utils/
    ├── __init__.py
    └── command_utils.py
```

#### File and Directory Descriptions

Below is an integrated description of each key module and file in the project:

---

##### Root Directory

-   **LICENSE:** Contains the license information for the project (e.g., MIT, GPL).
-   **README.md:** Provides an overview of the project, setup instructions, usage examples, and other relevant documentation.
-   **pyproject.toml:** The standardized project definition file. It contains metadata, lists dependencies (like `discord.py`, `pydantic`, `matplotlib`, `seaborn`, `httpx`), and configures tools like `pytest`. It makes the project installable (e.g., via `pip install -e .`).
-   **i18n.py:** Handles internationalization (i18n) by loading gettext translation files from the `locale` directory and providing functions to retrieve translated strings based on the configured language.
-   **main.py:** The main entry point for the bot. Initializes the bot, loads configuration and translations, sets up logging, loads extensions (commands), manages the main event loop, background tasks (like scheduled graph updates), and handles overall bot lifecycle and error management.
-   **.weblate:** Configuration file for Weblate integration, defining project settings, components, and file paths.

---

##### `bot/` Module

-   **bot/\_\_init\_\_.py:** Marks the `bot` directory as a Python package.
-   **bot/extensions.py:** Contains utility functions for managing (loading, unloading, reloading) the bot's command extensions (Cogs).
-   **bot/permission_checker.py:** Handles checking and logging Discord command permissions for the bot across all guilds it's in, ensuring commands have appropriate access controls.
-   **bot/update_tracker.py:** Manages the scheduling and tracking of when the server-wide graphs should be automatically updated, based on configuration (`UPDATE_DAYS`, `FIXED_UPDATE_TIME`).

---

##### `bot/commands/` Submodule

-   **bot/commands/\_\_init\_\_.py:** Initializes the `commands` package, importing and making available all the command Cogs (AboutCog, ConfigCog, etc.).
-   **bot/commands/about.py:** Defines the `/about` slash command, which displays information about the bot (description, GitHub link, license).
-   **bot/commands/config.py:** Defines the `/config` slash command group (`/config view`, `/config edit`) for viewing and modifying bot configuration settings.
-   **bot/commands/my_stats.py:** Defines the `/my_stats` slash command, allowing users to request their personal Plex statistics (graphs) via DM by providing their Plex email.
-   **bot/commands/update_graphs.py:** Defines the `/update_graphs` slash command, allowing administrators to manually trigger the regeneration and posting of server-wide statistics graphs.
-   **bot/commands/uptime.py:** Defines the `/uptime` slash command, which displays how long the bot has been running since its last start.

---

##### `config/` Module

-   **config/\_\_init\_\_.py:** Exposes the main configuration object to the rest of the application, making it easy to import and access settings.
-   **config/manager.py:** The core of the configuration system. It handles loading the `config.yml` file, parsing it into the Pydantic `Settings` model defined in `schema.py`, saving changes back to the file atomically (preserving comments), and managing the live configuration state.
-   **config/schema.py:** Defines the application's configuration structure using a Pydantic `BaseModel`. This single file is the source of truth for all settings, their types, default values, and validation rules (e.g., using `Field` validators for value ranges or formats).
-   **config/config.yml.sample:** A sample configuration file showing the expected structure, keys, and example values for the `config.yml` file that the user needs to create.

---

##### `graphs/` Module

-   **graphs/graph_manager.py:** Acts as the central orchestrator for server-wide graph generation. It uses the `GraphFactory` to create graph instances, fetches data via `DataFetcher`, and triggers generation. **Crucially, it runs the blocking Matplotlib/Seaborn graph creation code in a separate thread using `asyncio.to_thread()` to prevent freezing the bot's event loop.** It then posts the resulting images to Discord and manages old messages.
-   **graphs/user_graph_manager.py:** Handles graph generation for the `/my_stats` command. Like the main manager, **it uses `asyncio.to_thread()` to execute the CPU-bound graph generation**, ensuring the bot remains responsive while creating personalized graphs for a user.

---

##### `graphs/graph_modules/` Submodule

-   **graphs/graph_modules/\_\_init\_\_.py:** Marks the `graph_modules` directory as a Python package.
-   **graphs/graph_modules/base_graph.py:** An abstract base class defining the common interface for all graph types. It uses Matplotlib to handle the core figure and axes setup (e.g., size, background color, titles), providing a canvas for the high-level Seaborn library to draw onto.
-   **graphs/graph_modules/data_fetcher.py:** Responsible for fetching data from the Tautulli API. **It exclusively uses a modern, async-native HTTP client like `httpx` to perform all API requests**, ensuring that no I/O operations block the bot's event loop. It includes robust error handling for API timeouts, connection issues, and invalid responses, as well as caching results.
-   **graphs/graph_modules/graph_factory.py:** A factory class that creates instances of specific graph classes based on the enabled settings in the configuration.
-   **graphs/graph_modules/daily_play_count_graph.py:** Inherits from `BaseGraph` and uses the **Seaborn** library to implement the logic to plot daily play counts. This approach simplifies the plotting code and produces a more aesthetically pleasing result.
-   **graphs/graph_modules/play_count_by_dayofweek_graph.py:** Inherits from `BaseGraph` and uses **Seaborn** to plot play counts by day of the week, resulting in a cleaner implementation and superior visual output.
-   **graphs/graph_modules/play_count_by_hourofday_graph.py:** Inherits from `BaseGraph` and uses **Seaborn** to plot play counts by hour of the day.
-   **graphs/graph_modules/play_count_by_month_graph.py:** Inherits from `BaseGraph` and uses **Seaborn** to plot play counts by month.
-   **graphs/graph_modules/top_10_platforms_graph.py:** Inherits from `BaseGraph` and uses **Seaborn** to plot the top 10 platforms.
-   **graphs/graph_modules/top_10_users_graph.py:** Inherits from `BaseGraph` and uses **Seaborn** to plot the top 10 users.
-   **graphs/graph_modules/utils.py:** Contains utility functions used by the graph modules, such as date formatting, folder management, and username censoring.

---

##### `locale/` Module

-   **locale/messages.pot:** The template file containing all translatable strings.
-   **locale/en/LC_MESSAGES/messages.po:** Contains the English translations.

---

##### `utils/` Module

-   **utils/\_\_init\_\_.py:** Marks the `utils` directory as a Python package.
-   **utils/command_utils.py:** Contains utility functions specifically related to Discord commands, such as formatting command output or complex argument parsing.

---

## Config Options

The config file should have the following options available (+ default values), which will be defined in `config/schema.py`:

```yaml
# config/config.yml.sample
TAUTULLI_API_KEY: your_tautulli_api_key
TAUTULLI_URL: http://your_tautulli_ip:port/api/v2
DISCORD_TOKEN: your_discord_bot_token
CHANNEL_ID: your_channel_id
UPDATE_DAYS: 7
FIXED_UPDATE_TIME: "XX:XX"  # Set to HH:MM format, or leave as "XX:XX" to disable
KEEP_DAYS: 7
TIME_RANGE_DAYS: 30
LANGUAGE: en

# Graph options
CENSOR_USERNAMES: true
ENABLE_GRAPH_GRID: false
ENABLE_DAILY_PLAY_COUNT: true
ENABLE_PLAY_COUNT_BY_DAYOFWEEK: true
ENABLE_PLAY_COUNT_BY_HOUROFDAY: true
ENABLE_TOP_10_PLATFORMS: true
ENABLE_TOP_10_USERS: true
ENABLE_PLAY_COUNT_BY_MONTH: true

# Graph colors
TV_COLOR: "#1f77b4"
MOVIE_COLOR: "#ff7f0e"
GRAPH_BACKGROUND_COLOR: "#ffffff"
ANNOTATION_COLOR: "#ff0000"
ANNOTATION_OUTLINE_COLOR: "#000000"
ENABLE_ANNOTATION_OUTLINE: true

# Annotation options
ANNOTATE_DAILY_PLAY_COUNT: true
ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK: true
ANNOTATE_PLAY_COUNT_BY_HOUROFDAY: true
ANNOTATE_TOP_10_PLATFORMS: true
ANNOTATE_TOP_10_USERS: true
ANNOTATE_PLAY_COUNT_BY_MONTH: true

# Command cooldown options
CONFIG_COOLDOWN_MINUTES: 0
CONFIG_GLOBAL_COOLDOWN_SECONDS: 0
UPDATE_GRAPHS_COOLDOWN_MINUTES: 0
UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS: 0
MY_STATS_COOLDOWN_MINUTES: 5
MY_STATS_GLOBAL_COOLDOWN_SECONDS: 60
```

---

#### Python 3.13 Best Practices

The project employs several modern Python techniques, including:

-   **Type Hints and Pydantic:** Every function includes type annotations, and Pydantic models are used for configuration, ensuring data integrity and clarity.
-   **High-Level Libraries:** Uses libraries like **Seaborn** to produce better results with less, more readable code.
-   **Match Statements:** Used for streamlined control flow in command processing and data handling.
-   **Async/Await:** Leverages asynchronous programming with `discord.py` and `httpx` to handle all I/O without blocking.
-   **Non-Blocking Execution:** CPU-bound tasks like graph generation are properly delegated to separate threads to keep the bot responsive.

---

#### Test-Driven Development Approach

The project is built using a test-driven development (TDD) methodology:

1.  **Write tests first:** Tests defined with `pytest` specify the expected behavior.
2.  **Observe failing tests:** Confirming that the features have not yet been implemented.
3.  **Implement the features:** Code is then written to make tests pass.
4.  **Refactor:** After passing tests, code quality is improved while ensuring all tests continue to succeed.

---

#### Internationalization and Weblate Integration

The bot's internationalization system follows Weblate best practices, using the GNU gettext format, automated string extraction, and CI validation to ensure high-quality, continuous localization.
