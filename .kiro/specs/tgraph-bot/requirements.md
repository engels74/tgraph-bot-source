# Requirements Document

## Introduction

TGraph Bot is a Discord bot that automatically generates and posts Tautulli graphs to Discord channels, providing insights into Plex Media Server activity and performance. The system integrates with Tautulli's API to collect streaming data, generates customizable visualizations using Python plotting libraries, and posts them to Discord channels on a configurable schedule. A web-based UI allows administrators to manage bot configuration without editing YAML files directly.

## Glossary

- **TGraph Bot**: The Discord bot application that generates and posts Tautulli graphs
- **Tautulli**: A monitoring and tracking application for Plex Media Server
- **Discord Bot**: An automated application that interacts with Discord servers via the Discord API
- **Web UI**: A web-based user interface for managing bot configuration
- **YAML Configuration**: A human-readable data serialization format used for bot settings
- **Graph**: A visual representation of Plex Media Server statistics (charts, plots)
- **Stream Type**: The method of media delivery (direct play, transcode, copy)
- **Media Type**: The category of content (movie, TV show/episode)
- **Ephemeral Message**: A Discord message visible only to the command user that auto-deletes
- **Rate Limiting**: Restriction on command usage frequency to prevent spam
- **Scheduled Update**: Automatic graph generation and posting at configured intervals
- **Palette**: A predefined color scheme for graph visualization
- **Annotation**: Numeric labels displayed on graph data points or bars
- **Resolution**: Video quality measurement (e.g., 1080p, 4K)
- **Platform**: The client application used to stream content (e.g., Plex for Android)

## Requirements

### Requirement 1: Discord Bot Integration

**User Story:** As a Plex server administrator, I want the bot to connect to Discord and respond to commands, so that I can interact with the bot through my Discord server.

#### Acceptance Criteria

1. WHEN the Bot receives valid Discord credentials, THE TGraph Bot SHALL establish a connection to the Discord API using the nextcord library
2. WHEN a user invokes a slash command, THE TGraph Bot SHALL process the command and respond within 3 seconds
3. WHEN the Bot loses connection to Discord, THE TGraph Bot SHALL attempt reconnection with exponential backoff up to 5 attempts
4. WHEN the Bot starts successfully, THE TGraph Bot SHALL log the connection status with timestamp to the console
5. THE TGraph Bot SHALL support slash commands for configuration management, graph updates, and personal statistics

### Requirement 2: Tautulli API Integration

**User Story:** As a Plex server administrator, I want the bot to retrieve data from Tautulli, so that it can generate accurate statistics and graphs.

#### Acceptance Criteria

1. WHEN the Bot receives valid Tautulli API credentials, THE TGraph Bot SHALL establish a connection to the Tautulli API endpoint
2. WHEN requesting play history data, THE TGraph Bot SHALL retrieve records for the configured time range (1-365 days)
3. IF the Tautulli API returns an error response, THEN THE TGraph Bot SHALL log the error details and notify the user via Discord
4. WHEN collecting streaming data, THE TGraph Bot SHALL extract media type, stream type, platform, resolution, and user information
5. THE TGraph Bot SHALL validate API responses against expected data structures before processing

### Requirement 3: YAML Configuration System

**User Story:** As a Plex server administrator, I want to configure the bot using a YAML file, so that I can customize behavior without modifying code.

#### Acceptance Criteria

1. WHEN the Bot starts, THE TGraph Bot SHALL load configuration from a YAML file located in the application directory
2. WHEN the configuration file contains invalid YAML syntax, THE TGraph Bot SHALL log specific parsing errors with line numbers and refuse to start
3. WHEN a required configuration field is missing, THE TGraph Bot SHALL log the missing field name and refuse to start
4. WHEN configuration values are outside valid ranges, THE TGraph Bot SHALL log validation errors with expected ranges and refuse to start
5. THE TGraph Bot SHALL support all configuration sections: services, automation, data_collection, system, graphs, and rate_limiting

### Requirement 4: Web UI for Configuration Management

**User Story:** As a Plex server administrator, I want a web interface to manage bot configuration, so that I can update settings without editing YAML files manually.

#### Acceptance Criteria

1. WHEN the Web UI starts, THE TGraph Bot SHALL bind to the configured IP address and port number
2. WHEN a user accesses the Web UI, THE TGraph Bot SHALL display all current configuration values organized by section
3. WHEN a user modifies a configuration value, THE TGraph Bot SHALL validate the input against allowed ranges and formats before saving
4. WHEN a user saves configuration changes, THE TGraph Bot SHALL write the updated values to the YAML file and reload the configuration
5. IF configuration validation fails, THEN THE TGraph Bot SHALL display specific error messages indicating which fields are invalid

### Requirement 5: Graph Generation System

**User Story:** As a Plex server administrator, I want the bot to generate various types of graphs, so that I can visualize different aspects of server usage.

#### Acceptance Criteria

1. WHEN graph generation is triggered, THE TGraph Bot SHALL create all enabled graph types as specified in the configuration
2. WHEN generating a graph, THE TGraph Bot SHALL apply the configured dimensions (width 6-20 inches, height 4-16 inches) and DPI (72-300)
3. WHEN a graph type has media type separation enabled, THE TGraph Bot SHALL render separate visual elements for movies and TV shows
4. WHEN a palette is specified for a graph, THE TGraph Bot SHALL apply the palette colors instead of base media type colors
5. THE TGraph Bot SHALL use seaborn for enhanced visual aesthetics, theme management, and statistical visualizations where appropriate
6. THE TGraph Bot SHALL support the following graph types: daily play count, play count by day of week, play count by hour of day, top 10 platforms, top 10 users, play count by month, daily play count by stream type, daily concurrent stream count by stream type, play count by source resolution, play count by stream resolution, play count by platform and stream type, and play count by user and stream type

### Requirement 6: Graph Visual Styling

**User Story:** As a Plex server administrator, I want to customize graph appearance, so that graphs match my preferences and are easy to read.

#### Acceptance Criteria

1. WHEN annotations are enabled for a graph, THE TGraph Bot SHALL display numeric values on data points or bars using the configured font size (6-24 points)
2. WHEN peak highlighting is enabled, THE TGraph Bot SHALL apply the configured highlight color to the highest value in each graph
3. WHEN a graph uses stacked bar charts, THE TGraph Bot SHALL render bars with segments stacked vertically instead of side-by-side
4. WHEN a background color is specified, THE TGraph Bot SHALL apply the color to the entire graph background
5. WHEN grid lines are enabled, THE TGraph Bot SHALL render grid lines on the graph axes
6. WHEN a seaborn style is configured, THE TGraph Bot SHALL apply the style (whitegrid, darkgrid, white, dark, ticks) to all graphs
7. WHEN a seaborn palette is configured, THE TGraph Bot SHALL use seaborn's color palette system for consistent color management

### Requirement 7: Automated Graph Posting

**User Story:** As a Plex server administrator, I want graphs to be posted automatically on a schedule, so that I receive regular updates without manual intervention.

#### Acceptance Criteria

1. WHEN the Bot starts, THE TGraph Bot SHALL schedule automatic graph updates based on the configured update interval (1-365 days)
2. WHEN a fixed update time is configured (format HH:MM), THE TGraph Bot SHALL generate and post graphs at that specific time daily
3. WHEN the fixed update time is set to 'XX:XX', THE TGraph Bot SHALL generate and post graphs at a random time within each update interval
4. WHEN scheduled generation completes, THE TGraph Bot SHALL post all generated graphs to the configured Discord channel
5. WHEN posting graphs to Discord, THE TGraph Bot SHALL include a timestamp in the configured format (t, T, d, D, f, F, or R)

### Requirement 8: Manual Graph Update Command

**User Story:** As a Plex server administrator, I want to manually trigger graph updates, so that I can get fresh statistics on demand.

#### Acceptance Criteria

1. WHEN a user invokes the update-graphs command, THE TGraph Bot SHALL generate all enabled graphs with current data
2. WHEN graph generation is in progress, THE TGraph Bot SHALL send an ephemeral message indicating processing status
3. WHEN graph generation completes successfully, THE TGraph Bot SHALL post the graphs to the configured channel and delete the ephemeral message
4. IF graph generation fails, THEN THE TGraph Bot SHALL send an error message to the user with failure details
5. WHILE rate limiting is active for the user, THE TGraph Bot SHALL reject the command and display the remaining cooldown time

### Requirement 9: Personal Statistics Command

**User Story:** As a Plex user, I want to view my personal viewing statistics, so that I can see my own usage patterns.

#### Acceptance Criteria

1. WHEN a user invokes the my-stats command, THE TGraph Bot SHALL generate graphs filtered to that user's activity only
2. WHEN privacy mode is enabled, THE TGraph Bot SHALL send personal statistics as an ephemeral message visible only to the requesting user
3. WHEN generating personal statistics, THE TGraph Bot SHALL include the same graph types as server-wide statistics but filtered by username
4. WHEN the user has no activity in the configured time range, THE TGraph Bot SHALL display a message indicating no data is available
5. WHILE rate limiting is active for the user, THE TGraph Bot SHALL reject the command and display the remaining cooldown time

### Requirement 10: Configuration Command

**User Story:** As a Plex server administrator, I want to view current configuration via Discord, so that I can verify settings without accessing the server.

#### Acceptance Criteria

1. WHEN a user invokes the config command, THE TGraph Bot SHALL display current configuration values organized by section
2. WHEN displaying sensitive values (API keys, tokens), THE TGraph Bot SHALL mask all but the last 4 characters
3. WHEN sending configuration information, THE TGraph Bot SHALL use an ephemeral message that auto-deletes after the configured timeout (1-3600 seconds)
4. WHEN configuration display exceeds Discord message limits, THE TGraph Bot SHALL split the output into multiple ephemeral messages
5. WHILE rate limiting is active for the user, THE TGraph Bot SHALL reject the command and display the remaining cooldown time

### Requirement 11: Rate Limiting System

**User Story:** As a Plex server administrator, I want to limit command usage frequency, so that users cannot spam commands and overload the server.

#### Acceptance Criteria

1. WHEN a user invokes a rate-limited command, THE TGraph Bot SHALL check both user-specific and global cooldown timers
2. WHEN a user cooldown is active, THE TGraph Bot SHALL reject the command and display the remaining cooldown time in minutes
3. WHEN a global cooldown is active, THE TGraph Bot SHALL reject the command and display the remaining cooldown time in seconds
4. WHEN a cooldown is set to 0, THE TGraph Bot SHALL disable that specific cooldown check
5. THE TGraph Bot SHALL track separate cooldowns for config commands (0-1440 minutes per user, 0-86400 seconds global), update-graphs commands (0-1440 minutes per user, 0-86400 seconds global), and my-stats commands (0-1440 minutes per user, 0-86400 seconds global)

### Requirement 12: Data Retention Management

**User Story:** As a Plex server administrator, I want old graph files to be automatically deleted, so that disk space is not consumed indefinitely.

#### Acceptance Criteria

1. WHEN the Bot performs cleanup, THE TGraph Bot SHALL identify graph files older than the configured retention period (1-365 days)
2. WHEN old graph files are identified, THE TGraph Bot SHALL delete them from the file system
3. WHEN cleanup completes, THE TGraph Bot SHALL log the number of files deleted and disk space reclaimed
4. THE TGraph Bot SHALL perform cleanup checks daily at midnight local time
5. IF file deletion fails, THEN THE TGraph Bot SHALL log the error details and continue with remaining files

### Requirement 13: Privacy and Username Censoring

**User Story:** As a Plex server administrator, I want to optionally censor usernames in graphs, so that I can share statistics publicly without revealing user identities.

#### Acceptance Criteria

1. WHEN username censoring is enabled, THE TGraph Bot SHALL replace usernames with anonymized labels (User 1, User 2, etc.) in all graphs
2. WHEN username censoring is disabled, THE TGraph Bot SHALL display actual usernames in graphs
3. WHEN generating personal statistics, THE TGraph Bot SHALL always display the requesting user's actual username regardless of the global censoring setting
4. WHEN censoring is enabled, THE TGraph Bot SHALL maintain consistent anonymized labels across all graphs in the same generation cycle
5. THE TGraph Bot SHALL apply the censoring setting from the privacy configuration section

### Requirement 14: Localization Support

**User Story:** As a Plex server administrator, I want to use the bot in my preferred language, so that messages and labels are displayed in a language I understand.

#### Acceptance Criteria

1. WHEN the Bot starts, THE TGraph Bot SHALL load language strings for the configured language code
2. WHEN displaying messages to users, THE TGraph Bot SHALL use translated strings from the loaded language file
3. WHEN generating graphs, THE TGraph Bot SHALL use translated labels for axes, legends, and titles
4. WHEN the configured language code is not supported, THE TGraph Bot SHALL fall back to English (en) and log a warning
5. THE TGraph Bot SHALL support English (en) and Danish (da) language codes at minimum

### Requirement 15: Error Handling and Logging

**User Story:** As a Plex server administrator, I want comprehensive error logging, so that I can troubleshoot issues when they occur.

#### Acceptance Criteria

1. WHEN an error occurs, THE TGraph Bot SHALL log the error message, stack trace, and timestamp to the console
2. WHEN a critical error prevents bot operation, THE TGraph Bot SHALL log the error and exit with a non-zero status code
3. WHEN API requests fail, THE TGraph Bot SHALL log the request URL, response status code, and error message
4. WHEN configuration validation fails, THE TGraph Bot SHALL log all validation errors with field names and expected values
5. THE TGraph Bot SHALL log informational messages for successful operations including bot startup, graph generation completion, and scheduled task execution

### Requirement 16: Stream Type Analysis

**User Story:** As a Plex server administrator, I want to analyze transcoding behavior, so that I can optimize server resources and identify users requiring transcoding.

#### Acceptance Criteria

1. WHEN generating stream type graphs, THE TGraph Bot SHALL categorize streams as direct play, transcode, or copy based on Tautulli data
2. WHEN stream type separation is enabled, THE TGraph Bot SHALL render separate visual elements for each stream type
3. WHEN generating concurrent stream graphs, THE TGraph Bot SHALL calculate peak concurrent streams for each stream type
4. WHEN peak highlighting is enabled for concurrent streams, THE TGraph Bot SHALL mark peak usage periods with the configured highlight color
5. THE TGraph Bot SHALL support stream type analysis for daily activity, concurrent streams, platform breakdown, and user breakdown graphs

### Requirement 17: Resolution Analysis

**User Story:** As a Plex server administrator, I want to analyze streaming resolutions, so that I can understand quality preferences and transcoding patterns.

#### Acceptance Criteria

1. WHEN generating resolution graphs, THE TGraph Bot SHALL extract resolution data from Tautulli stream records
2. WHEN resolution grouping is set to 'standard', THE TGraph Bot SHALL group resolutions into categories (4K, 1440p, 1080p, 720p, 480p, SD)
3. WHEN resolution grouping is set to 'detailed', THE TGraph Bot SHALL display exact resolution values (3840x2160, 1920x1080, etc.)
4. WHEN resolution grouping is set to 'simplified', THE TGraph Bot SHALL group resolutions into broad categories (SD, HD, FHD, UHD)
5. WHEN transcoding focus is enabled for stream resolution graphs, THE TGraph Bot SHALL emphasize transcoded content with distinct visual styling

### Requirement 18: Platform and User Limits

**User Story:** As a Plex server administrator, I want to limit the number of platforms and users shown in graphs, so that graphs remain readable and focused on top contributors.

#### Acceptance Criteria

1. WHEN generating top platforms graphs, THE TGraph Bot SHALL limit displayed platforms to the configured maximum (3-20)
2. WHEN generating top users graphs, THE TGraph Bot SHALL limit displayed users to the configured maximum (3-20)
3. WHEN platform grouping is enabled, THE TGraph Bot SHALL combine similar platform names (e.g., "Plex for Android" and "Plex for Android TV" become "Android")
4. WHEN the number of platforms or users exceeds the limit, THE TGraph Bot SHALL display only the top N by activity count
5. THE TGraph Bot SHALL sort platforms and users by total play count in descending order before applying limits

### Requirement 19: Modern Type System (PEP 695, TypeIs, Protocols)

**User Story:** As a developer, I want the codebase to use Python 3.14 modern type hints following `.claude/rules/python-pro.md` guidelines, so that type errors are caught before runtime and code is maintainable.

#### Acceptance Criteria

1. THE TGraph Bot SHALL use PEP 695 type parameter syntax (class[T], def[T]) for all generic classes and functions instead of TypeVar constructors
2. THE TGraph Bot SHALL use TypeIs[T] for type narrowing predicates instead of TypeGuard[T] to enable proper narrowing in both if and else branches
3. THE TGraph Bot SHALL use the type statement for type aliases instead of TypeAlias annotations
4. THE TGraph Bot SHALL use built-in generic syntax (list[str], dict[str, int], str | int | None) instead of typing module aliases (List, Dict, Union, Optional)
5. THE TGraph Bot SHALL define small composable Protocols with 1-3 methods for structural subtyping instead of inheritance where appropriate

### Requirement 20: Type Checking with basedpyright

**User Story:** As a developer, I want comprehensive type checking following `.claude/rules/python-pro.md` guidelines, so that type errors are detected during development.

#### Acceptance Criteria

1. THE TGraph Bot SHALL pass basedpyright type checking in recommended mode with failOnWarnings set to true
2. THE TGraph Bot SHALL use explicit rule-scoped type ignore comments (# pyright: ignore[rule]) instead of bare # type: ignore
3. THE TGraph Bot SHALL include type hints for all function parameters and return values
4. THE TGraph Bot SHALL use ReadOnly[type] for immutable TypedDict fields where appropriate

### Requirement 21: Build System and Modern Tooling

**User Story:** As a developer, I want to use modern Python 3.14 tooling following `.claude/rules/python-pro.md` guidelines, so that builds are fast and dependencies are managed efficiently.

#### Acceptance Criteria

1. THE TGraph Bot SHALL use uv as the build backend with version constraint uv_build>=0.9.5,<0.10.0 in pyproject.toml
2. THE TGraph Bot SHALL use ruff for code formatting and linting with target-version set to py314
3. THE TGraph Bot SHALL require Python 3.14 or higher as specified in requires-python field
4. THE TGraph Bot SHALL use nextcord library for Discord bot functionality
5. THE TGraph Bot SHALL declare all runtime dependencies in the pyproject.toml [project] dependencies array following PEP 621 format

### Requirement 22: Async Concurrency with TaskGroups

**User Story:** As a developer, I want to use structured concurrency following `.claude/rules/python-pro.md` guidelines, so that async operations are properly managed and cancelled.

#### Acceptance Criteria

1. WHEN performing concurrent async operations, THE TGraph Bot SHALL use asyncio.TaskGroup instead of asyncio.gather() or create_task()
2. WHEN a task in a TaskGroup fails, THE TGraph Bot SHALL automatically cancel all other tasks in the group
3. WHEN handling multiple exceptions from TaskGroups, THE TGraph Bot SHALL use ExceptionGroup and except* syntax
4. WHEN managing async resources, THE TGraph Bot SHALL use @asynccontextmanager for reliable cleanup
5. WHEN implementing timeouts, THE TGraph Bot SHALL use asyncio.timeout() context manager instead of wait_for()

### Requirement 23: Context Variables for Task-Local State

**User Story:** As a developer, I want to use context variables following `.claude/rules/python-pro.md` guidelines, so that task-local state is properly isolated.

#### Acceptance Criteria

1. WHEN storing task-local state, THE TGraph Bot SHALL use contextvars.ContextVar instead of threading.local()
2. WHEN creating new async tasks, THE TGraph Bot SHALL ensure context variables are automatically inherited from the parent task
3. WHEN accessing context variables, THE TGraph Bot SHALL provide sensible default values
4. THE TGraph Bot SHALL use context variables for request tracking, user identification, and operation correlation
5. THE TGraph Bot SHALL document all context variables with their purpose and expected types

### Requirement 24: Data Modeling with Dataclasses

**User Story:** As a developer, I want to use appropriate data modeling following `.claude/rules/python-pro.md` guidelines, so that data structures are efficient and type-safe.

#### Acceptance Criteria

1. WHEN defining simple data transfer objects, THE TGraph Bot SHALL use dataclasses with slots=True for 40% memory savings
2. WHEN defining configuration models requiring validation, THE TGraph Bot SHALL use Pydantic models at API boundaries only
3. WHEN defining internal data structures, THE TGraph Bot SHALL prefer dataclasses over Pydantic for zero-dependency simplicity
4. THE TGraph Bot SHALL use frozen=True for immutable data structures where appropriate
5. THE TGraph Bot SHALL include type hints for all dataclass fields

### Requirement 25: Code Quality with Ruff

**User Story:** As a developer, I want automated code formatting and linting following `.claude/rules/python-pro.md` guidelines, so that code style is consistent.

#### Acceptance Criteria

1. THE TGraph Bot SHALL configure ruff with line-length of 88 characters for Black compatibility
2. THE TGraph Bot SHALL enable ruff lint rules: E (pycodestyle errors), F (pyflakes), B (bugbear), I (isort), N (naming), UP (pyupgrade), C90 (complexity)
3. THE TGraph Bot SHALL configure ruff to auto-fix all fixable issues
4. THE TGraph Bot SHALL enable docstring-code-format in ruff formatter
5. THE TGraph Bot SHALL pass ruff check and ruff format with no errors or warnings

### Requirement 26: Security Best Practices

**User Story:** As a developer, I want to follow security best practices from `.claude/rules/python-pro.md` guidelines, so that the application is secure against common vulnerabilities.

#### Acceptance Criteria

1. WHEN handling user input, THE TGraph Bot SHALL validate all inputs using Pydantic models with Field constraints
2. WHEN storing sensitive configuration values, THE TGraph Bot SHALL load from environment variables instead of hardcoding
3. WHEN logging, THE TGraph Bot SHALL mask sensitive values (API keys, tokens) showing only the last 4 characters
4. THE TGraph Bot SHALL use parameterized queries or ORMs for any database operations to prevent SQL injection
5. THE TGraph Bot SHALL validate YAML configuration against expected schemas before loading

### Requirement 27: Error Handling with Exception Groups

**User Story:** As a developer, I want proper error handling following `.claude/rules/python-pro.md` guidelines, so that multiple concurrent errors are properly reported.

#### Acceptance Criteria

1. WHEN catching exceptions from TaskGroups, THE TGraph Bot SHALL use except* syntax to handle ExceptionGroup
2. WHEN multiple operations fail concurrently, THE TGraph Bot SHALL preserve all exception details without losing information
3. WHEN logging exception groups, THE TGraph Bot SHALL iterate through all exceptions and log each with context
4. THE TGraph Bot SHALL use specific exception types instead of bare except clauses
5. THE TGraph Bot SHALL include error context (operation name, parameters) in exception messages

### Requirement 28: Keyword-Only Arguments

**User Story:** As a developer, I want to use keyword-only arguments following `.claude/rules/python-pro.md` guidelines, so that function calls are readable and maintainable.

#### Acceptance Criteria

1. WHEN defining functions with boolean flags, THE TGraph Bot SHALL make them keyword-only by placing after * parameter
2. WHEN defining functions with optional parameters, THE TGraph Bot SHALL make them keyword-only for clarity
3. WHEN defining functions with more than 3 parameters, THE TGraph Bot SHALL make non-essential parameters keyword-only
4. THE TGraph Bot SHALL use keyword-only arguments for configuration options and feature flags
5. THE TGraph Bot SHALL document keyword-only parameters with clear descriptions in docstrings
