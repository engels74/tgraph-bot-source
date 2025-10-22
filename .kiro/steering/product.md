# Product Overview

TGraph Bot is a Discord bot that integrates with Tautulli to automatically generate and post Plex Media Server statistics graphs to Discord channels. It provides comprehensive insights into server usage patterns, transcoding behavior, platform distribution, and user activity through customizable visualizations.

## Core Capabilities
- **Automated Scheduling**: Configurable intervals with fixed or random posting times
- **12 Graph Types**: Daily activity, day/hour patterns, top platforms/users, monthly trends, stream type analysis, resolution analysis, concurrent streams
- **Personal Statistics**: Users can view their own activity via `/my-stats` command
- **Web UI**: Browser-based configuration management alongside manual YAML editing
- **Privacy Controls**: Username censoring for public sharing
- **Localization**: Multi-language support (English, Danish)

## Key Integrations
- **Discord**: nextcord library for slash commands and automated posting
- **Tautulli**: API integration for Plex streaming data
- **Visualization**: matplotlib + seaborn for professional graph aesthetics

## Licensing
- Docker image: GPLv3
- Source code: AGPLv3
