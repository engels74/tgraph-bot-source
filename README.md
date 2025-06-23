# 📊 TGraph Bot (Tautulli Graph Bot)

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

> **🚧 Complete Rewrite in Progress**
> TGraph Bot has undergone a complete ground-up rewrite with modern Python 3.13, enhanced architecture, and comprehensive testing. Work on v1.0.0 is actively ongoing. The new version features async operations, slash commands, live configuration reloading, and much more.

TGraph Bot is a modern Discord bot that automatically generates and posts beautiful Tautulli graphs to your Discord channels. It provides insights into your Plex Media Server's activity and performance with customizable visualizations and user-specific statistics.

## ✨ Key Features

- 🤖 **Modern Discord Integration** - Slash commands with permission-based access control
- 📈 **Beautiful Graphs** - Professional Seaborn-styled visualizations with customizable themes
- ⚡ **Async Architecture** - Non-blocking operations that won't freeze your bot
- 🔄 **Live Configuration** - Update settings without restarting the bot
- 🌍 **Multi-language Support** - Built-in internationalization (English & Danish)
- 👤 **Personal Statistics** - Users can generate their own viewing statistics
- 🎨 **Highly Customizable** - Extensive configuration options for colors, annotations, and graph types
- 🧪 **Production Ready** - Comprehensive testing and type safety with Python 3.13

## 📊 Graph Types

- **Daily Play Count** - Track daily viewing activity with optional media type separation
- **Day of Week Analysis** - Discover viewing patterns by weekday
- **Hourly Activity** - 24-hour activity heatmaps
- **Monthly Trends** - Long-term usage patterns and trends
- **Top Users** - Leaderboards of most active users (with privacy options)
- **Top Platforms** - Most popular client platforms and devices

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Discord Bot Token
- Tautulli API Access
- UV package manager (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/engels74/tgraph-bot-source.git
   cd tgraph-bot-source
   ```

2. **Install dependencies**
   ```bash
   # Install uv if not already installed
   pip install uv

   # Install project dependencies
   uv sync
   ```

3. **Configure the bot**
   ```bash
   # Copy the sample configuration
   cp config.yml.sample config.yml

   # Edit config.yml with your settings
   nano config.yml
   ```

4. **Run the bot**
   ```bash
   uv run python main.py
   ```

## ⚙️ Configuration

The bot uses a comprehensive YAML configuration file with validation. Key settings include:

- **Essential Settings**: Tautulli API key, Discord token, channel ID
- **Graph Options**: Enable/disable specific graph types, colors, annotations
- **Timing**: Update intervals, data retention, time ranges
- **Permissions**: Command cooldowns and access control
- **Localization**: Language selection and formatting

See `config.yml.sample` for a complete configuration template with detailed comments.

## 🔧 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Type checking
uvx basedpyright
```

### Code Quality

- **Type Safety**: 100% type coverage with basedpyright
- **Testing**: Comprehensive unit and integration tests
- **Code Style**: Consistent formatting with ruff
- **Documentation**: Complete docstring coverage

## 📚 Documentation

WIP

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests. For major changes, please open an issue first to discuss what you would like to change.

## 💬 Support

If you encounter any issues or need help:

- 📋 [Create an issue](https://github.com/engels74/tgraph-bot-source/issues) on GitHub
- 💬 Check existing issues for solutions
- 📖 Refer to the upcoming Wiki documentation

## ⚖️ License

[![GNU GPLv3 Image](https://www.gnu.org/graphics/gplv3-127x51.png)](http://www.gnu.org/licenses/gpl-3.0.en.html)

The Docker image is licensed under the GPLv3 License. See the [LICENSE](https://github.com/engels74/tgraph-bot/blob/master/LICENSE) file for details.

[![GNU AGPLv3 Image](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.en.html)

The source code for the TGraph Bot scripts are licensed under the AGPLv3 License. See the [LICENSE](https://github.com/engels74/tgraph-bot-source/blob/main/LICENSE) file for details.
