# Implementation Plan

- [x] 1. Set up project structure and development tools
  - Create directory structure for all modules (config, api, commands, graphs, scheduler, rate_limiting, web, localization, utils, tests)
  - Add project dependencies to pyproject.toml (nextcord, pydantic, httpx, matplotlib, seaborn, aiohttp, aiohttp-jinja2, ruamel.yaml, python-dotenv)
  - Add dev dependencies (pytest, pytest-asyncio, pytest-cov, httpx for mocking)
  - Configure ruff with line-length 88, target py314, and lint rules (E, F, B, I, N, UP, C90)
  - Configure basedpyright with recommended mode and failOnWarnings=true
  - Add pytest configuration for test discovery
  - Set up .gitignore for Python projects
  - _Requirements: 20.1, 20.2, 21.1, 21.3, 21.4, 21.5, 25.1, 25.2, 25.3, 25.4, 25.5_

- [x] 2. Implement logging and error handling infrastructure
  - Set up structured logging with appropriate format and levels
  - Create custom exception hierarchy (TGraphBotError, ConfigurationError, TautulliAPIError, GraphGenerationError, RateLimitError)
  - Implement sensitive value masking for logs
  - Add context variable for operation tracking
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 23.1, 23.3, 26.3_

- [x] 3. Write tests for configuration validation
  - Write tests for Pydantic model validation (invalid values, missing fields, type errors)
  - Write tests for YAML loading with valid and invalid files
  - Write tests for environment variable overrides
  - Write tests for configuration error messages
  - Use pytest fixtures for test configuration data
  - _Requirements: 3.2, 3.3, 3.4_

- [x] 4. Implement configuration system
  - Implement Pydantic configuration models for all sections (services, automation, data_collection, system, graphs, rate_limiting) with Field constraints
  - Create YAML configuration loader using ruamel.yaml for format preservation
  - Implement configuration validation with detailed error messages
  - Add environment variable override support for sensitive values
  - Verify all tests pass
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 21.1, 21.5, 26.2_

- [x] 5. Write tests for data transformation and privacy
  - Write tests for StreamRecord creation from Tautulli responses
  - Write tests for data aggregation functions (by date, day of week, hour, platform, user, month)
  - Write tests for username anonymization logic with consistent labels
  - Write tests for edge cases (empty data, single record, duplicate timestamps)
  - Use pytest parametrization for multiple input scenarios
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 6. Implement data transformation and domain models
  - Create StreamRecord dataclass with slots=True and frozen=True
  - Implement data transformation from Tautulli responses to StreamRecord
  - Create aggregation functions for different graph types
  - Implement privacy/anonymization logic for username censoring
  - Create AggregatedData and GraphMetadata dataclasses
  - Verify all tests pass
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 24.1, 24.3, 24.4_

- [ ] 7. Write tests for Tautulli API client
  - Write tests using httpx mock for successful API responses
  - Write tests for API error handling (timeouts, 4xx, 5xx errors)
  - Write tests for retry logic with exponential backoff
  - Write tests for get_history and get_user_history methods
  - Use pytest-asyncio for async test support
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 8. Implement Tautulli API client
  - Implement async HTTP client using httpx with timeout configuration
  - Create TypedDict models for Tautulli API responses with ReadOnly fields
  - Implement get_history method with days parameter
  - Implement get_user_history method for personal statistics
  - Add retry logic with exponential backoff for transient failures
  - Implement comprehensive error handling and logging for API requests
  - Verify all tests pass
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 19.4, 20.4_

- [ ] 9. Write tests for rate limiting system
  - Write tests for user cooldown tracking and expiration
  - Write tests for global cooldown tracking
  - Write tests for cooldown calculations with various time intervals
  - Write tests for cleanup_expired method
  - Write tests for disabled cooldowns (0 value)
  - Use pytest parametrization for different cooldown scenarios
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 10. Implement rate limiting system
  - Create RateLimiter class with user and global cooldown tracking
  - Implement check_cooldown method returning CooldownInfo or None
  - Implement record_usage method for tracking command usage
  - Add cleanup_expired method for removing old cooldown entries
  - Implement periodic cleanup task running every hour
  - Use context variables for current user tracking
  - Verify all tests pass
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 23.1, 23.2, 23.3_

- [ ] 11. Write tests for localization system
  - Write tests for loading English and Danish localization files
  - Write tests for fallback to English when translation missing
  - Write tests for string formatting with keyword arguments
  - Write tests for handling missing localization files
  - _Requirements: 14.1, 14.2, 14.4_

- [ ] 12. Implement localization system
  - Create Localizer class with language loading from JSON files
  - Implement LocalizedStrings TypedDict for type-safe string access
  - Create English (en) localization file with all required strings
  - Create Danish (da) localization file with all required strings
  - Implement fallback to English for missing translations
  - Add string formatting support with keyword arguments
  - Verify all tests pass
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 28.1, 28.2_

- [ ] 13. Write tests for task scheduler
  - Write tests for schedule calculation (fixed time vs random time)
  - Write tests for next run time calculation
  - Write tests for graceful shutdown and task cancellation
  - Use pytest-asyncio for async scheduler tests
  - Mock asyncio.sleep for faster test execution
  - _Requirements: 7.1, 7.2, 7.5_

- [ ] 14. Implement task scheduler for automated updates
  - Create TaskScheduler class with start/stop methods
  - Implement schedule calculation logic (fixed time vs random time)
  - Create main scheduling loop with asyncio.sleep
  - Implement execute_update method for triggering graph generation
  - Add graceful shutdown with task cancellation
  - Use asynccontextmanager for scheduler lifecycle management
  - Verify all tests pass
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 22.1, 22.2, 22.4_

- [ ] 15. Write tests for graph generation engine
  - Write tests for seaborn theme application (style, palette, context)
  - Write tests for graph styling application (colors, dimensions, palettes)
  - Write tests for seaborn palette retrieval and color management
  - Write tests for annotation system (basic and peak highlighting)
  - Write tests for media type separation logic
  - Write tests for GraphFactory creating correct generator types
  - Use sample data for graph generation tests
  - _Requirements: 5.1, 5.2, 5.3, 5.5, 6.1, 6.2, 6.6, 6.7_

- [ ] 16. Build graph generation engine core
  - Create GraphGenerator protocol with generate method
  - Implement GraphStyling class with seaborn theme management
  - Integrate seaborn for enhanced aesthetics and color palette system
  - Configure seaborn default styling (darkgrid style for Discord compatibility)
  - Implement GraphFactory for creating graph generators
  - Create base graph styling system (colors, dimensions, DPI, palettes via seaborn)
  - Implement annotation system (basic annotations and peak highlighting)
  - Create GraphRenderer orchestrator for generating all enabled graphs with seaborn theme application
  - Verify all tests pass
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 19.1, 19.5_

- [ ] 17. Write tests for individual graph types (basic set)
  - Write tests for DailyPlayCountGraph data preparation
  - Write tests for PlayCountByDayOfWeekGraph aggregation
  - Write tests for PlayCountByHourOfDayGraph aggregation
  - Write tests for TopPlatformsGraph limiting and grouping
  - Write tests for TopUsersGraph limiting
  - Write tests for PlayCountByMonthGraph data preparation
  - _Requirements: 5.5, 5.6, 18.1, 18.2, 18.3, 18.4, 18.5_

- [ ] 18. Implement individual graph types (basic set)
  - Implement DailyPlayCountGraph using sns.lineplot() for cleaner multi-line charts
  - Implement PlayCountByDayOfWeekGraph using sns.barplot() with stacked option
  - Implement PlayCountByHourOfDayGraph using sns.barplot() with stacked option
  - Implement TopPlatformsGraph using sns.barplot() for horizontal bars with platform limit and grouping
  - Implement TopUsersGraph using sns.barplot() for horizontal bars with user limit
  - Implement PlayCountByMonthGraph using sns.lineplot() with media type separation
  - Verify all tests pass
  - _Requirements: 5.5, 5.6, 18.1, 18.2, 18.3, 18.4, 18.5_

- [ ] 19. Write tests for stream type analysis graphs
  - Write tests for stream type separation logic
  - Write tests for resolution grouping (standard, detailed, simplified)
  - Write tests for concurrent stream counting
  - Write tests for peak highlighting logic
  - Write tests for transcoding focus emphasis
  - _Requirements: 16.1, 16.2, 16.3, 17.1, 17.2, 17.3, 17.4_

- [ ] 20. Implement stream type analysis graph types
  - Implement DailyPlayCountByStreamTypeGraph using sns.lineplot() with stream type separation
  - Implement DailyConcurrentStreamCountByStreamTypeGraph using sns.lineplot() with peak highlighting
  - Implement PlayCountBySourceResolutionGraph using sns.countplot() for categorical resolution data with grouping
  - Implement PlayCountByStreamResolutionGraph using sns.barplot() with transcoding focus emphasis
  - Implement PlayCountByPlatformAndStreamTypeGraph using sns.barplot() with stacked option
  - Implement PlayCountByUserAndStreamTypeGraph using sns.barplot() with stacked option and privacy mode
  - Verify all tests pass
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 17.1, 17.2, 17.3, 17.4, 17.5_

- [ ] 21. Implement data retention manager
  - Create DataRetentionManager class with cleanup_old_files method
  - Implement file age checking based on keep_days configuration
  - Add daily cleanup scheduling at midnight
  - Track and log deleted file count and bytes reclaimed
  - Handle file deletion errors gracefully
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 22. Create Discord bot core and command infrastructure
  - Implement TGraphBot class extending nextcord.Bot
  - Set up bot initialization with configuration and intents
  - Implement on_ready event handler with connection logging
  - Add reconnection logic with exponential backoff (up to 5 attempts)
  - Create GraphCommands cog for graph-related slash commands
  - Implement command registration and error handling
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 19.2, 19.4_

- [ ] 23. Implement Discord slash commands
  - Implement /update-graphs command with rate limiting check
  - Add ephemeral message for processing status
  - Implement graph generation orchestration using TaskGroup
  - Add graph posting to Discord channel with timestamp formatting
  - Implement /my-stats command for personal statistics
  - Add user filtering for personal stats graphs
  - Implement /config command for viewing configuration
  - Add sensitive value masking for config display
  - Handle message size limits by splitting large responses
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 22.1, 22.3, 27.1, 27.2_

- [ ] 24. Write tests for Web UI API endpoints
  - Write tests for GET /api/config endpoint
  - Write tests for POST /api/config with validation
  - Write tests for conflict detection (file modified externally)
  - Write tests for POST /api/config/reload endpoint
  - Write tests for sensitive value masking
  - Use aiohttp test client for endpoint testing
  - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [ ] 25. Build Web UI server with aiohttp
  - Create WebUIServer class with aiohttp application setup
  - Set up Jinja2 templating with templates directory
  - Implement index route serving main configuration page
  - Add static file serving for CSS/JS
  - Implement health check endpoint
  - Verify all tests pass
  - _Requirements: 4.1, 21.2_

- [ ] 26. Implement Web UI API endpoints
  - Implement GET /api/config endpoint reading from YAML file
  - Add file modification timestamp tracking
  - Implement POST /api/config endpoint with validation
  - Add conflict detection for concurrent edits
  - Implement POST /api/config/reload endpoint
  - Add GET /api/config/file-modified endpoint for polling
  - Implement sensitive value masking in API responses
  - Verify all tests pass
  - _Requirements: 4.2, 4.3, 4.4, 4.5, 26.3_

- [ ] 27. Create Web UI frontend
  - Create HTML template with configuration form organized by sections
  - Implement CSS styling for clean, readable interface
  - Add JavaScript for form validation and API communication
  - Implement real-time validation feedback
  - Add sensitive value masking with reveal toggle
  - Implement save functionality with conflict detection
  - Add reload button to refresh from file
  - Display current config file path
  - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [ ] 28. Implement configuration reload system
  - Add reload_configuration method to TGraphBot
  - Implement configuration validation before applying
  - Add component reconfiguration (scheduler, rate limiter)
  - Preserve rate limiter cooldowns during reload
  - Add comprehensive logging for reload events
  - Handle reload failures gracefully (keep old config)
  - _Requirements: 3.4, 15.1, 15.5_

- [ ] 29. Create main application entry point
  - Implement __main__.py with startup sequence
  - Add configuration loading with environment variable overrides
  - Initialize all components (bot, scheduler, web UI, retention manager)
  - Implement graceful shutdown handling (SIGTERM/SIGINT)
  - Add startup logging and error handling
  - Use asynccontextmanager for component lifecycle
  - _Requirements: 1.1, 1.4, 15.1, 15.2, 22.4, 22.5_

- [ ] 30. Create default configuration file
  - Create config.yaml with all sections and default values
  - Add comprehensive comments explaining each configuration option
  - Include all graph types with sensible defaults
  - Set default colors, dimensions, and styling options
  - Configure default rate limiting values
  - Add example values for required fields (API keys, tokens)
  - _Requirements: 3.1, 3.5_

- [ ] 31. Run comprehensive type checking and code quality
  - Run basedpyright on entire codebase and fix all type errors
  - Run ruff check and fix all linting issues
  - Run ruff format to ensure consistent formatting
  - Verify all functions have type hints
  - Check for proper use of keyword-only arguments
  - Ensure PEP 695 syntax used throughout
  - _Requirements: 19.1, 19.2, 20.1, 20.2, 25.1, 25.2, 25.5, 28.1, 28.2, 28.3_

- [ ] 32. Integration and end-to-end testing
  - Test complete startup sequence with valid configuration
  - Test Discord bot connection and command handling
  - Test scheduled graph generation and posting
  - Test Web UI configuration editing and reload
  - Test manual YAML editing and reload
  - Test error handling for invalid configuration
  - Test error handling for Tautulli API failures
  - Verify all graph types generate correctly
  - Run full test suite with coverage report
  - _Requirements: 1.1, 1.2, 3.1, 4.1, 5.1, 7.1, 8.1, 15.1_

- [ ] 33. Write comprehensive documentation
  - Create comprehensive README with project overview
  - Document installation instructions using uv
  - Add configuration guide explaining all YAML options
  - Document Discord bot setup (creating bot, getting token, inviting to server)
  - Document Tautulli API key retrieval
  - Add Web UI usage guide
  - Include troubleshooting section
  - Add examples of common configuration scenarios
  - Document testing and development workflow
  - _Requirements: 1.1, 2.1, 3.1, 4.1_
