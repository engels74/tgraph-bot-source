# 📊 TGraph Bot (Tautulli Graph Bot)

<p align="center">
  <img src="tgraph-bot.svg" alt="base-image" style="width: 40%;"/>
</p>

<p align="center">
  <a href="https://github.com/engels74/tgraph-bot-source/releases"><img src="https://img.shields.io/github/v/tag/engels74/tgraph-bot-source?sort=semver" alt="GitHub tag (SemVer)"></a>
  <a href="https://github.com/engels74/tgraph-bot/blob/master/LICENSE"><img src="https://img.shields.io/badge/License%20(Image)-GPL--3.0-orange" alt="License (Image)"></a>
  <a href="https://github.com/engels74/tgraph-bot-source/blob/main/LICENSE"><img src="https://img.shields.io/badge/License%20(Source)-AGPL--3.0-orange" alt="License (Source)"></a>
  <a href="https://hub.docker.com/r/engels74/tgraph-bot"><img src="https://img.shields.io/docker/pulls/engels74/tgraph-bot.svg" alt="Docker Pulls"></a>
  <a href="https://github.com/engels74/tgraph-bot-source/stargazers"><img src="https://img.shields.io/github/stars/engels74/tgraph-bot-source.svg" alt="GitHub Stars"></a>
  <a href="https://deepwiki.com/engels74/tgraph-bot-source"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</p>

TGraph Bot is a modern Discord bot that automatically generates and posts beautiful Tautulli graphs to your Discord channels. Built with Python 3.13, it provides insights into your Plex Media Server's activity and performance with customizable visualizations and user-specific statistics.

## ✨ Features

### 📊 Graph Types
- **Daily Play Count** - Track daily media consumption patterns
- **Play Count by Day of Week** - Identify weekly viewing trends
- **Play Count by Hour of Day** - Discover peak usage hours
- **Play Count by Month** - Monitor long-term viewing patterns
- **Top 10 Users** - See most active Plex users
- **Top 10 Platforms** - Identify popular client platforms

### 🤖 Discord Integration
- **Slash Commands** - Modern Discord command interface
- **Automatic Scheduling** - Configurable update intervals with optional fixed times
- **Personal Statistics** - Users can request individual stats via DM
- **Admin Controls** - Server administrators can manually trigger updates
- **Rich Embeds** - Beautiful, informative graph presentations

### ⚙️ Configuration & Management
- **YAML Configuration** - Human-readable configuration with validation
- **Runtime Configuration Updates** - Modify settings via Discord commands
- **Internationalization** - Multi-language support (through Weblate)
- **Comprehensive Logging** - Detailed logging with structured output
- **Error Handling** - Graceful error recovery and user feedback

## � Quick Start

1. **Prerequisites**
   - Python 3.13+
   - Discord bot token
   - Tautulli server with API access

2. **Configuration**
   - Copy `config.yml.sample` to `data/config/config.yml`
   - Configure your Discord token, Tautulli API key, and channel ID
   - Customize graph settings and update schedules

3. **Installation & Running**
   ```bash
   # Install dependencies
   uv sync

   # Run the bot
   uv run tgraph-bot
   ```

## 🎮 Commands

### Slash Commands
- `/about` - Display bot information and version
- `/config edit <setting> <value>` - Modify configuration (Admin only)
- `/config view` - View current configuration (Admin only)
- `/my_stats <email>` - Get personal statistics via DM
- `/update_graphs` - Manually trigger graph generation (Admin only)
- `/uptime` - Show bot uptime and status

### Configuration Options
The bot supports extensive customization through YAML configuration:
- **Graph Types** - Enable/disable specific graph types
- **Scheduling** - Set update intervals and fixed times
- **Appearance** - Customize colors, grid lines, and media type separation
- **Permissions** - Configure command cooldowns and access control
- **Localization** - Choose language and formatting preferences

## 📚 Documentation

Comprehensive documentation will be available in the project wiki upon release.

## 🔧 Development

### Requirements
- Python 3.13+
- uv package manager

### Development Commands
```bash
# Install dependencies
uv sync --dev

# Run the bot
uv run tgraph-bot

# Run tests
uv run pytest tests/

# Type checking
uvx basedpyright
```

### Project Structure
- `src/tgraph_bot/` - Main application code
- `tests/` - Unit and integration tests
- `locale/` - Internationalization files
- `config.yml.sample` - Configuration template

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests. For major changes, please open an issue first to discuss what you would like to change.

## 💬 Support

If you encounter any issues or need help:

- 📋 [Create an issue](https://github.com/engels74/tgraph-bot-source/issues) on GitHub
- 💬 Check existing issues for solutions
- 📖 Refer to the project wiki documentation

## ⚖️ License

[![GNU GPLv3 Image](https://www.gnu.org/graphics/gplv3-127x51.png)](http://www.gnu.org/licenses/gpl-3.0.en.html)

The Docker image is licensed under the GPLv3 License. See the [LICENSE](https://github.com/engels74/tgraph-bot/blob/master/LICENSE) file for details.

[![GNU AGPLv3 Image](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.en.html)

The source code for the TGraph Bot scripts are licensed under the AGPLv3 License. See the [LICENSE](https://github.com/engels74/tgraph-bot-source/blob/main/LICENSE) file for details.
