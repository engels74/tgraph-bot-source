# TGraph Bot (Tautulli Graph Bot)

<p align="center">
  <img src="https://i.imgur.com/L5Tj3nW.png" alt="TGraph Bot"/>
</p>

## Description

TGraph Bot is a script/bot for posting Tautulli graphs to a Discord webhook. This project is designed to run in a Docker container and provides an easy way to share your Plex Media Server statistics on Discord.

Tautulli Graph Bot automates the process of generating and posting graphical statistics from Tautulli to a Discord channel using a webhook. This integration helps you keep your community informed about your Plex Media Server's activity and performance.

## Features

- Automatically generates and posts Tautulli graphs to a Discord channel
- Supports multiple languages (English and Danish) using i18n
- Runs in a Docker container for easy deployment
- Configurable graph options
- Interactive Discord slash commands for bot management

## Preview
<img src="https://i.imgur.com/lHLWpc2.png" width="50%" alt="An example of how it looks">

## Installation

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

### Source Code for Docker Container

You can find the source code for the Docker Container here:
https://github.com/engels74/tgraph-bot

## Configuration

The bot is configured using the `config.yml` file. Create a `config.yml` file in the `/config` directory based on the provided `config.yml.sample` file. Update the values in the `config.yml` file with your specific settings:

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

- `ENABLE_DAILY_PLAY_COUNT`: Enable/disable daily play count graph (default is true)
- `ENABLE_PLAY_COUNT_BY_DAYOFWEEK`: Enable/disable play count by day of week graph (default is true)
- `ENABLE_PLAY_COUNT_BY_HOUROFDAY`: Enable/disable play count by hour of day graph (default is true)
- `ENABLE_TOP_10_PLATFORMS`: Enable/disable top 10 platforms graph (default is true)
- `ENABLE_TOP_10_USERS`: Enable/disable top 10 users graph (default is true)
- `ENABLE_PLAY_COUNT_BY_MONTH`: Enable/disable play count by month graph (default is true)

### Annotation Options

- `ANNOTATE_DAILY_PLAY_COUNT`: Enable/disable annotations on daily play count graph (default is true)
- `ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK`: Enable/disable annotations on play count by day of week graph (default is true)
- `ANNOTATE_PLAY_COUNT_BY_HOUROFDAY`: Enable/disable annotations on play count by hour of day graph (default is true)
- `ANNOTATE_TOP_10_PLATFORMS`: Enable/disable annotations on top 10 platforms graph (default is true)
- `ANNOTATE_TOP_10_USERS`: Enable/disable annotations on top 10 users graph (default is true)
- `ANNOTATE_PLAY_COUNT_BY_MONTH`: Enable/disable annotations on play count by month graph (default is true)

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

### Language Support

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
