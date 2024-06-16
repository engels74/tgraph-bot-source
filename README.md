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

## Preview
<img src="https://i.imgur.com/lHLWpc2.png" width="50%" alt="An example of how it looks">

## Installation

To get started with Tautulli Graph Bot using Docker, follow these steps:

1. **Download the docker compose example:**
    ```sh
    curl -o /choose/path/to/docker-compose.tgraph.yml https://raw.githubusercontent.com/engels74/tgraph-bot-source/main/docker-compose.example01.yml
    ```

2. **Edit `docker-compose.yml` with your preferred editor:**
    ```sh
    nano /choose/path/to/docker-compose.tgraph.yml
    ```
    Replace the placeholder paths with your actual paths for the volume mounts:
    - `./logs:/logs`: The path where the log files will be stored on the host machine.
    - `./config/config.yml:/app/config/config.yml`: The path to the `config.yml` file on the host machine.
    - `./img:/app/img`: The path where the generated graph images will be stored on the host machine.

3. **Create a `config.yml` file:**
    - Download the `config.yml.sample` file:
        ```sh
        curl -o /choose/path/to/config.yml https://raw.githubusercontent.com/engels74/tgraph-bot-source/main/config/config.yml.sample
        ```
    - Edit the `config.yml` file and replace the placeholder values with your actual settings:
        - `TAUTULLI_API_KEY`: Your Tautulli API key.
        - `TAUTULLI_URL`: The URL to your Tautulli instance (e.g., `http://localhost:8181/api/v2`).
        - `DISCORD_TOKEN`: The token for your Discord bot.
        - `CHANNEL_ID`: The ID of the Discord channel where you want to post the graphs.
        - `UPDATE_DAYS`: The interval in days for how often to post the graph (default is 7 days).
        - `IMG_FOLDER`: The folder where images will be stored (default is `img`).
        - `KEEP_DAYS`: The number of days to keep the images (default is 7 days).
        - `TIME_RANGE_DAYS`: The time range in days for the graphs (default is 30 days).
        - `TZ`: The timezone to use (default is `Etc/UTC`).
        - `LANGUAGE`: The language to use for the bot (default is `en`). Supported languages: `en` (English), `da` (Danish).

4. **Build and run the Docker container using `docker-compose`:**
    ```sh
    docker-compose -f /choose/path/to/docker-compose.tgraph.yml build
    docker-compose -f /choose/path/to/docker-compose.tgraph.yml up -d
    ```

## Configuration

The bot is configured using the `config.yml` file. Create a `config.yml` file in the `/config` directory based on the provided `config.yml.sample` file. Update the values in the `config.yml` file with your specific settings.

### Language Support

Tautulli Graph Bot supports multiple languages using i18n. The available languages are defined in the `i18n` directory, with separate YAML files for each language:

- `en.yml`: English language translations
- `da.yml`: Danish language translations

To set the language for the bot, update the `LANGUAGE` value in the `config.yml` file to the desired language code (`en` for English or `da` for Danish).

## Docker Compose Configuration

Here's an example of how your `docker-compose.yml` file should be set up:

```yaml
services:
  tgraph-bot:
    build: https://github.com/engels74/tgraph-bot-source.git
    image: tgraph-bot:latest
    container_name: tgraph-bot
    volumes:
      - ./logs:/logs
      - ./config/config.yml:/app/config/config.yml
      - ./img:/app/img
    restart: unless-stopped
```

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
This project is licensed under the AGPLv3 License. See the [LICENSE] file for details.
