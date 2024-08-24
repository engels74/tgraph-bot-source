# TGraph Bot (Tautulli Graph Bot)

<p align="center">
  <img src="https://i.imgur.com/L5Tj3nW.png" alt="TGraph Bot"/>
</p>

<p align="center">
  <a href="https://github.com/engels74/tgraph-bot-source/releases"><img src="https://img.shields.io/github/v/tag/engels74/tgraph-bot-source?sort=semver" alt="GitHub tag (SemVer)"></a>
  <a href="https://github.com/engels74/tgraph-bot/blob/master/LICENSE"><img src="https://img.shields.io/badge/License%20(Image)-GPL--3.0-orange" alt="License (Image)"></a>
  <a href="https://github.com/engels74/tgraph-bot-source/blob/main/LICENSE"><img src="https://img.shields.io/badge/License%20(Source)-AGPL--3.0-orange" alt="License (Source)"></a>
  <a href="https://hub.docker.com/r/engels74/tgraph-bot"><img src="https://img.shields.io/docker/pulls/engels74/tgraph-bot.svg" alt="Docker Pulls"></a>
  <a href="https://github.com/engels74/tgraph-bot-source/stargazers"><img src="https://img.shields.io/github/stars/engels74/tgraph-bot-source.svg" alt="GitHub Stars"></a>
  <a href="https://endsoftwarepatents.org/innovating-without-patents"><img style="height: 20px;" src="https://static.fsf.org/nosvn/esp/logos/patent-free.svg"></a>
</p>

## 📋 Table of Contents
- [Description](#description)
- [Features](#features)
- [Preview](#preview)
- [Installation](#installation)
  - [Docker Compose](#docker-compose)
  - [Unraid Community Application](#unraid-community-application)
- [Configuration](#configuration)
  - [Bot Options](#bot-options)
  - [Graph Options](#graph-options)
  - [Graph Colors](#graph-colors)
  - [Annotation Options](#annotation-options)
  - [My Stats Options](#my-stats-options)
- [Slash Commands](#slash-commands)
  - [Rate Limiting](#rate-limiting)
- [Managing Bot Permissions](#managing-bot-permissions)
- [Language Support](#language-support)
- [Creating a Discord Bot](#creating-a-discord-bot)
- [License](#license)

## Description

TGraph Bot is a script/bot for posting Tautulli graphs to a Discord channel. It's designed to run in a Docker container and provides an easy way to share your Plex Media Server statistics on Discord.

Tautulli Graph Bot automates the process of generating and posting graphical statistics from Tautulli to a Discord channel of your choice. This integration helps you keep your community informed about your Plex Media Server's activity and performance.

## Features

- Automatically generates and posts Tautulli graphs to a Discord channel
- Annotation options for each graph type
- Configurable graph options with ability to enable/disable specific graphs
- Customizable update intervals and data retention periods
- Interactive Discord slash commands for bot management and user statistics
- Runs in a Docker container for easy deployment
- Supports multiple languages (currently English and Danish) using i18n
- User-specific graph generation (with rate limiting options)

## Preview
<img src="https://i.imgur.com/UmzyUgW.png" width="50%" alt="An example of how it looks">

## Installation

### Docker Compose

To get started with Tautulli Graph Bot using Docker, follow these steps:

1. **Use this Docker Compose example**
    ```yaml
    services:
      tgraph-bot:
        container_name: tgraph-bot
        image: ghcr.io/engels74/tgraph-bot:latest
        environment:
          - PUID=1000
          - PGID=1000
          - UMASK=002
          - TZ=Etc/UTC
        volumes:
          - /<host_folder_config>:/config
    ```

2. **Create a `config.yml` file:**
    - Download the `config.yml.sample` file:
        ```sh
        curl -o /<host_folder_config>/config.yml https://raw.githubusercontent.com/engels74/tgraph-bot-source/main/config/config.yml.sample
        ```
    - Edit the `config.yml` file and replace the placeholder values with your actual settings.

3. **Run the Docker container using `docker-compose`:**
    ```sh
    docker-compose -f /choose/path/to/docker-compose.tgraph.yml up -d
    ```

### Unraid Community Application

TGraph Bot is also available as an Unraid Community Application, making it easy to install and manage on Unraid systems:

1. Open the Unraid Apps tab.
2. Search for "TGraph Bot" in the available applications.
3. Click on the TGraph Bot application.
4. Click "Install" to add TGraph Bot to your Unraid system.

You can find the TGraph Bot application in the Unraid Community Applications here:
[TGraph Bot on Unraid Community Apps](https://unraid.net/community/apps?q=tgraph#r)

### Source Code for Docker Container

You can find the source code for the Docker Container here:
https://github.com/engels74/tgraph-bot

## Configuration

The bot is configured using the `config.yml` file. Create a `config.yml` file in the `/config` directory based on the provided `config.yml.sample` file. Update the values in the `config.yml` file with your specific settings:

### Bot Options

- `TAUTULLI_API_KEY`: Your Tautulli API key.
- `TAUTULLI_URL`: The URL to your Tautulli instance (e.g., `http://localhost:8181/api/v2`).
- `DISCORD_TOKEN`: The token for your Discord bot.
- `CHANNEL_ID`: The ID of the Discord channel where you want to post the graphs.
- `UPDATE_DAYS`: The interval in days for how often to post the graph (default is 7 days).
- `IMG_FOLDER`: The folder where images will be stored (default is `img`).
- `KEEP_DAYS`: The number of days to keep the images (default is 7 days).
- `TIME_RANGE_DAYS`: The time range in days for the graphs (default is 30 days).
- `LANGUAGE`: The language to use for the bot (default is `en`). Supported languages: `en` (English), `da` (Danish).

### Graph Options

- `CENSOR_USERNAMES`: Enable/disable censoring of usernames in the top 10 users graph (default is true).
- `ENABLE_DAILY_PLAY_COUNT`: Enable/disable daily play count graph (default is true)
- `ENABLE_PLAY_COUNT_BY_DAYOFWEEK`: Enable/disable play count by day of week graph (default is true)
- `ENABLE_PLAY_COUNT_BY_HOUROFDAY`: Enable/disable play count by hour of day graph (default is true)
- `ENABLE_TOP_10_PLATFORMS`: Enable/disable top 10 platforms graph (default is true)
- `ENABLE_TOP_10_USERS`: Enable/disable top 10 users graph (default is true)
- `ENABLE_PLAY_COUNT_BY_MONTH`: Enable/disable play count by month graph (default is true)

### Graph Colors
- `TV_COLOR`: The color to use for TV shows in graphs (default is "#1f77b4", a shade of blue).
- `MOVIE_COLOR`: The color to use for movies in graphs (default is "#ff7f0e", a shade of orange).
- `ANNOTATION_COLOR`: The color to use for number annotations on graphs (default is "#ff0000", red).
- See [here](https://matplotlib.org/stable/users/explain/colors/colors.html) for more options. 

### Annotation Options

- `ANNOTATE_DAILY_PLAY_COUNT`: Enable/disable annotations on daily play count graph (default is true)
- `ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK`: Enable/disable annotations on play count by day of week graph (default is true)
- `ANNOTATE_PLAY_COUNT_BY_HOUROFDAY`: Enable/disable annotations on play count by hour of day graph (default is true)
- `ANNOTATE_TOP_10_PLATFORMS`: Enable/disable annotations on top 10 platforms graph (default is true)
- `ANNOTATE_TOP_10_USERS`: Enable/disable annotations on top 10 users graph (default is true)
- `ANNOTATE_PLAY_COUNT_BY_MONTH`: Enable/disable annotations on play count by month graph (default is true)

### My Stats Options

- `MY_STATS_COOLDOWN_MINUTES`: The cooldown period in minutes for individual users using the `/my_stats` command (default is 5 minutes)
- `MY_STATS_GLOBAL_COOLDOWN_SECONDS`: The global cooldown period in seconds between any two uses of the `/my_stats` command (default is 60 seconds)

## Slash Commands

TGraph Bot supports the following slash commands:

- `/about`: Displays information about the bot, including its description, GitHub repository, and license.
- `/update_graphs`: Manually triggers the bot to update and post the graphs.
- `/uptime`: Shows how long the bot has been running.
- `/config`: Allows viewing or editing the bot's configuration.
  - Usage: `/config <action> [key] [value]`
  - Actions:
    - `view`: Shows all configuration options or a specific key if provided.
    - `edit`: Edits a specific configuration key with the provided value.
- `/my_stats`: Generates and sends personalized graphs based on the user's Tautulli data.
  - Usage: `/my_stats <email>`
  - This command generates graphs specific to the user and sends them via direct message.
  - The `<email>` parameter should match the email associated with the user's Plex account in Tautulli.

To use these commands, simply type them in any channel where the bot is present. The bot will respond with the requested information or action.

Note: The `/config` command responses are only visible to the user who issued the command to protect sensitive information. The `/my_stats` command sends the graphs via direct message to ensure user privacy.

### Rate Limiting

The `/my_stats` command is subject to rate limiting to prevent abuse:

- There's a cooldown period for each user after using the command.
- There's also a global cooldown that affects all users.

If a user attempts to use the command too frequently, they will receive a message indicating when they can use the command again.

## Managing Bot Permissions

TGraph Bot uses Discord's built-in Integrations system for managing command permissions and includes an automatic permission checker. This allows server administrators to control access to sensitive commands like `/config` and `/update_graphs` directly through Discord's interface, while also providing insights into the current permission setup. Here's how it works:

1. **Automatic Permission Checking**:
   - Upon startup, the bot checks and logs the current permission settings for all commands across all servers it's in.
   - This helps identify any potential security risks, such as sensitive commands being accessible to all users.
   - It looks like this: [Preview Image](https://i.imgur.com/VIzl1ne.png)

2. **Permission Reports**:
   - The bot generates detailed reports of command permissions, which are logged to the console and logfile.
   - These reports show which roles or users have access to each command, helping to ensure proper access control.

3. **Setting Up Permissions**:
   - Access your Discord server settings and navigate to the Integrations section.
   - Find TGraph Bot in the list and click to expand its settings.
   - In the "Command Permissions" section, you can specify which roles or users have permission to use each command.
   - It's recommended to restrict sensitive commands like `/config`, `/my_stats` and `/update_graphs` to trusted roles only.

**Note:** If no specific permissions are set for a command, it will be accessible to all users who can see and use slash commands in the server. Always ensure sensitive commands are properly restricted.

## Language Support

Tautulli Graph Bot supports multiple languages using i18n. The available languages are defined in the `i18n` directory, with separate YAML files for each language:

- `en.yml`: English language translations
- `da.yml`: Danish language translations

To set the language for the bot, update the `LANGUAGE` value in the `config.yml` file to the desired language code (`en` for English or `da` for Danish).

## Creating a Discord Bot

To post messages to Discord, you need to create a bot and obtain its token.

1. **Open the Discord Developer Portal:** Go to [Discord Developer Portal](https://discord.com/developers/applications).

2. **Create a New Application:**
    - Click on `New Application`.
    - Name your application and click `Create`.

3. **Create a Bot:**
    - Navigate to the `Bot` section on the left sidebar.
    - Click `Add Bot`, then `Yes, do it!`.

4. **Get Your Bot Token:**
    - Under the `Token` section, click `Copy` to copy your bot token.
    - Use this token as the value for `DISCORD_TOKEN` in your `config.yml` file.

5. **Invite Your Bot to Your Server:**
    - Go to the `OAuth2` section.
    - Under `OAuth2 URL Generator`, select `bot` under `SCOPES` and the following permissions under `BOT PERMISSIONS`:
        - Read Messages/View Channels
        - Send Messages
        - Embed Links
        - Attach Files
        - Manage Messages
    - Copy the generated URL and paste it into your browser to invite the bot to your server.

## License
This project is licensed under the AGPLv3 License. See the [LICENSE](LICENSE) file for details.
