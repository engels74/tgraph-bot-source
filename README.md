# TGraph Bot (Tautulli Graph Bot)

A script/bot for posting Tautulli graphs to a Discord webhook. This project is designed to run in a Docker container and provides an easy way to share your Plex Media Server statistics on Discord.

## Description

Tautulli Graph Bot automates the process of generating and posting graphical statistics from Tautulli to a Discord channel using a webhook. This integration helps you keep your community informed about your Plex Media Server's activity and performance.

## Installation

To get started with Tautulli Graph Bot using Docker, follow these steps:

1. **Download the docker compose example:**
    ```sh
    curl -o /choose/path/to/docker-compose.tgraph.yml https://raw.githubusercontent.com/engels74/tgraph-bot-source/main/docker-compose.example.yml
    ```

2. **Edit `docker-compose.yml` with your preferred editor:**
    ```sh
    nano /choose/path/to/docker-compose.tgraph.yml
    ```
    Replace the placeholder values with your actual settings:
    - `TAUTULLI_API_KEY`: Your Tautulli API key.
    - `TAUTULLI_URL`: The URL to your Tautulli instance (e.g., `http://localhost:8181/api/v2`).
    - `DISCORD_TOKEN`: The token for your Discord bot.
    - `CHANNEL_ID`: The ID of the Discord channel where you want to post the graphs.
    - `UPDATE_DAYS`: The interval in days for how often to post the graph (default is 7 days).
    - `IMG_FOLDER`: The folder where images will be stored (default is `img`).
    - `KEEP_DAYS`: The number of days to keep the images (default is 7 days).
    - `TIME_RANGE_DAYS`: The time range in days for the graphs (default is 30 days).
    - `TZ`: The timezone to use (default is `Etc/UTC`).

4. **Build and run the Docker container using `docker-compose`:**
    ```sh
    docker-compose -f /choose/path/to/docker-compose.tgraph.yml build
    docker-compose -f /choose/path/to/docker-compose.tgraph.yml up -d
    ```

## Environment Variables

The bot uses several environment variables for configuration. Set these variables directly in the `docker-compose.yml` file.

- `DISCORD_TOKEN`: The token for your Discord bot.
- `CHANNEL_ID`: The ID of the Discord channel where you want to post the graphs.
- `TAUTULLI_API_KEY`: Your Tautulli API key.
- `TAUTULLI_URL`: The URL to your Tautulli instance (e.g., `http://localhost:8181/api/v2`).
- `UPDATE_DAYS`: The interval in days for how often to post the graph (default is 7 days).
- `IMG_FOLDER`: The folder where images will be stored (default is `img`).
- `KEEP_DAYS`: The number of days to keep the images (default is 7 days).
- `TIME_RANGE_DAYS`: The time range in days for the graphs (default is 30 days).
- `TZ`: The timezone to use (default is `Etc/UTC`).

## Docker Compose Configuration

Here is an example of how your `docker-compose.yml` file should look:

```yaml
services:
  tgraph-bot:
    build: https://github.com/engels74/tgraph-bot-source.git
    image: tgraph-bot:latest
    container_name: tgraph-bot
    environment:
      - TAUTULLI_API_KEY=your_tautulli_api_key
      - TAUTULLI_URL=http://your_tautulli_ip:port/api/v2
      - DISCORD_TOKEN=your_discord_bot_token
      - CHANNEL_ID=your_channel_id
      - UPDATE_DAYS=7
      - IMG_FOLDER=img
      - KEEP_DAYS=7
      - TIME_RANGE_DAYS=30
      - TZ=Etc/UTC
    volumes:
      - ./logs:/logs
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
    - Use this token as the value for `DISCORD_TOKEN` in your `docker-compose.yml` file.

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