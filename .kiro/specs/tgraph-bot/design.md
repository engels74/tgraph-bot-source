# Design Document

## Overview

TGraph Bot is a Discord bot application that integrates with Tautulli to generate and post Plex Media Server statistics graphs. The system consists of four main subsystems:

1. **Discord Bot Layer**: Handles Discord API interactions, slash commands, and message posting using nextcord
2. **Tautulli Integration Layer**: Retrieves streaming data from Tautulli API and transforms it for analysis
3. **Graph Generation Engine**: Creates customizable visualizations using matplotlib with configurable styling
4. **Web UI Management Interface**: Provides a web-based configuration editor using a lightweight async web framework

The application follows modern Python 3.14 development practices as specified in `.claude/rules/python-pro.md`, including:
- PEP 695 type parameter syntax and TypeIs for type narrowing
- Structured concurrency with asyncio.TaskGroup
- Context variables for task-local state
- Dataclasses with slots for data modeling
- basedpyright type checking in recommended mode
- uv build backend and ruff for code quality

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        TGraph Bot                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │   Discord    │      │   Web UI     │                     │
│  │   Bot Layer  │      │   Server     │                     │
│  └──────┬───────┘      └──────┬───────┘                     │
│         │                     │                              │
│         │  ┌──────────────────┴──────────────┐              │
│         │  │   Configuration Manager         │              │
│         │  │  (YAML Load/Save/Validate)      │              │
│         │  └──────────────┬──────────────────┘              │
│         │                 │                                  │
│  ┌──────┴─────────────────┴──────────────┐                  │
│  │      Command Handler & Scheduler       │                  │
│  └──────┬─────────────────┬───────────────┘                  │
│         │                 │                                  │
│  ┌──────┴───────┐  ┌──────┴──────────┐                      │
│  │  Tautulli    │  │  Graph          │                      │
│  │  API Client  │  │  Generator      │                      │
│  └──────────────┘  └─────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
   ┌──────────┐              ┌──────────────┐
   │ Tautulli │              │   Discord    │
   │   API    │              │     API      │
   └──────────┘              └──────────────┘
```


### Layered Architecture

The application follows a layered architecture pattern:

**Presentation Layer**:
- Discord command handlers (slash commands)
- Web UI HTTP handlers
- Response formatting and ephemeral message management

**Application Layer**:
- Command orchestration and rate limiting
- Scheduled task management
- Graph generation coordination
- Configuration validation and management

**Domain Layer**:
- Graph generation logic and styling
- Data transformation and aggregation
- Privacy and anonymization logic
- Localization string management

**Infrastructure Layer**:
- Tautulli API client
- Discord API client (nextcord)
- YAML configuration persistence
- File system operations for graph storage

## Components and Interfaces

### 1. Configuration Manager

**Purpose**: Load, validate, and persist YAML configuration with type-safe access.

**Key Classes**:

```python
from dataclasses import dataclass
from typing import Protocol, ReadOnly
from pydantic import BaseModel, Field

# Configuration models using Pydantic for validation at boundaries
class TautulliConfig(BaseModel):
    api_key: str = Field(min_length=32)
    url: str = Field(pattern=r'^https?://.+')

class DiscordConfig(BaseModel):
    token: str = Field(min_length=50)
    channel_id: int = Field(gt=0)
    timestamp_format: str = Field(pattern=r'^[tTdDfFR]$')
    ephemeral_message_delete_after: float = Field(ge=1.0, le=3600.0)

class ServicesConfig(BaseModel):
    tautulli: TautulliConfig
    discord: DiscordConfig

# Full configuration schema
class BotConfig(BaseModel):
    services: ServicesConfig
    automation: AutomationConfig
    data_collection: DataCollectionConfig
    system: SystemConfig
    graphs: GraphsConfig
    rate_limiting: RateLimitingConfig

# Configuration manager protocol
class ConfigLoader(Protocol):
    def load(self, path: str) -> BotConfig: ...
    def save(self, config: BotConfig, path: str) -> None: ...
    def validate(self, config: BotConfig) -> list[str]: ...
```

**Responsibilities**:
- Load YAML file and parse into Pydantic models
- Validate all configuration values against constraints
- Provide type-safe access to configuration values
- Save updated configuration back to YAML
- Handle configuration reload without restart

**Error Handling**:
- Raise ConfigurationError with specific field and validation message
- Log all validation errors before refusing to start
- Provide helpful error messages with expected ranges/formats


### 2. Discord Bot Layer

**Purpose**: Handle Discord API interactions, command registration, and message posting.

**Key Classes**:

```python
import nextcord
from nextcord.ext import commands
from contextlib import asynccontextmanager
from typing import TypeIs

class TGraphBot(commands.Bot):
    """Main bot class extending nextcord.Bot"""
    
    def __init__(self, config: BotConfig):
        intents = nextcord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limiting)
        self.scheduler = TaskScheduler(config.automation)
    
    async def on_ready(self) -> None:
        """Called when bot successfully connects to Discord"""
        ...

# Command handlers using slash commands
class GraphCommands(commands.Cog):
    """Cog containing graph-related slash commands"""
    
    @nextcord.slash_command(name="update-graphs", description="Generate and post new graphs")
    async def update_graphs(self, interaction: nextcord.Interaction) -> None:
        ...
    
    @nextcord.slash_command(name="my-stats", description="View your personal statistics")
    async def my_stats(self, interaction: nextcord.Interaction) -> None:
        ...
    
    @nextcord.slash_command(name="config", description="View current configuration")
    async def config(self, interaction: nextcord.Interaction) -> None:
        ...
```

**Responsibilities**:
- Establish and maintain Discord API connection with reconnection logic
- Register slash commands and handle interactions
- Post graphs to configured channel with timestamps
- Send ephemeral messages for user-specific responses
- Handle rate limiting checks before command execution

**Error Handling**:
- Implement exponential backoff for reconnection (up to 5 attempts)
- Catch Discord API errors and send user-friendly error messages
- Log all Discord API errors with request context
- Handle message size limits by splitting large responses


### 3. Tautulli API Client

**Purpose**: Retrieve streaming data from Tautulli API with proper error handling.

**Key Classes**:

```python
from dataclasses import dataclass
import httpx
from typing import TypedDict, ReadOnly

# Response models using TypedDict with ReadOnly fields
class TautulliStreamRecord(TypedDict):
    date: ReadOnly[int]  # Unix timestamp
    media_type: ReadOnly[str]  # "movie" or "episode"
    stream_type: ReadOnly[str]  # "direct play", "transcode", "copy"
    platform: ReadOnly[str]
    user: ReadOnly[str]
    stream_video_resolution: ReadOnly[str]
    stream_video_full_resolution: ReadOnly[str]

@dataclass(slots=True, frozen=True)
class TautulliClient:
    """Client for Tautulli API interactions"""
    api_key: str
    base_url: str
    timeout: float = 30.0
    
    async def get_history(
        self,
        *,
        days: int,
        length: int = 1000
    ) -> list[TautulliStreamRecord]:
        """Retrieve play history for specified number of days"""
        ...
    
    async def get_user_history(
        self,
        *,
        username: str,
        days: int
    ) -> list[TautulliStreamRecord]:
        """Retrieve play history for specific user"""
        ...
```

**Responsibilities**:
- Make HTTP requests to Tautulli API endpoints
- Parse JSON responses into typed data structures
- Handle API authentication with API key
- Implement request timeouts and retries
- Extract relevant fields from Tautulli responses

**Error Handling**:
- Raise TautulliAPIError for HTTP errors with status code and message
- Implement retry logic with exponential backoff for transient failures
- Validate response structure before parsing
- Log all API requests and responses for debugging


### 4. Graph Generation Engine

**Purpose**: Transform Tautulli data into customizable matplotlib visualizations.

**Key Classes**:

```python
from dataclasses import dataclass
from typing import Protocol
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import seaborn as sns

# Graph type protocol
class GraphGenerator(Protocol):
    """Protocol for graph generation implementations"""
    
    def generate(
        self,
        data: list[TautulliStreamRecord],
        *,
        config: GraphConfig
    ) -> Figure:
        """Generate matplotlib figure from data"""
        ...

@dataclass(slots=True)
class GraphStyling:
    """Manages graph visual styling with seaborn integration"""
    
    def apply_theme(self, *, style: str = "darkgrid", palette: str = "muted") -> None:
        """Apply seaborn theme for consistent styling"""
        sns.set_theme(style=style, palette=palette)
    
    def get_palette(self, palette_name: str, n_colors: int) -> list[str]:
        """Get seaborn color palette"""
        if not palette_name:
            return []
        return sns.color_palette(palette_name, n_colors=n_colors).as_hex()

@dataclass(slots=True)
class DailyPlayCountGraph:
    """Generates daily play count over time graph"""
    
    def generate(
        self,
        data: list[TautulliStreamRecord],
        *,
        config: GraphConfig
    ) -> Figure:
        # Aggregate data by date
        # Apply media type separation if enabled
        # Use seaborn lineplot for cleaner multi-line charts
        # Apply palette or base colors via seaborn
        # Add annotations if enabled
        # Highlight peaks if enabled
        ...

@dataclass(slots=True)
class GraphFactory:
    """Factory for creating graph generators"""
    
    def create_generator(self, graph_type: str) -> GraphGenerator:
        """Create appropriate graph generator for type"""
        ...

@dataclass(slots=True)
class GraphRenderer:
    """Orchestrates graph generation and file saving"""
    styling: GraphStyling
    
    async def render_all_graphs(
        self,
        data: list[TautulliStreamRecord],
        *,
        config: GraphsConfig,
        output_dir: str
    ) -> list[str]:
        """Generate all enabled graphs and return file paths"""
        # Apply seaborn theme before generating graphs
        self.styling.apply_theme(
            style=config.appearance.seaborn.style,
            palette=config.appearance.seaborn.palette
        )
        ...
```

**Responsibilities**:
- Aggregate and transform Tautulli data for each graph type
- Apply visual styling (colors, palettes, dimensions, DPI)
- Add annotations and peak highlighting based on configuration
- Handle media type separation and stacked bar charts
- Save figures to disk as PNG files
- Apply privacy settings (username censoring)

**Graph Types Supported**:
1. Daily play count (line chart)
2. Play count by day of week (bar chart)
3. Play count by hour of day (bar chart)
4. Top 10 platforms (horizontal bar chart)
5. Top 10 users (horizontal bar chart)
6. Play count by month (line chart)
7. Daily play count by stream type (line chart)
8. Daily concurrent stream count by stream type (line chart)
9. Play count by source resolution (bar chart)
10. Play count by stream resolution (bar chart)
11. Play count by platform and stream type (stacked bar chart)
12. Play count by user and stream type (stacked bar chart)

**Styling System**:
- Seaborn theme integration for professional aesthetics
- Base colors for TV/Movie when media type separation enabled
- Palette override system using seaborn's palette management (viridis, plasma, inferno, magma, muted, deep, pastel, etc.)
- Configurable seaborn style (whitegrid, darkgrid, white, dark, ticks)
- Configurable dimensions (width, height, DPI)
- Annotation styling (color, outline, font size)
- Peak highlighting with custom colors
- Grid line toggle
- Background color customization


### 5. Task Scheduler

**Purpose**: Manage automated graph generation and posting on configured schedule.

**Key Classes**:

```python
from dataclasses import dataclass
import asyncio
from datetime import datetime, time, timedelta
from contextlib import asynccontextmanager

@dataclass(slots=True)
class TaskScheduler:
    """Manages scheduled graph updates"""
    config: AutomationConfig
    _task: asyncio.Task[None] | None = None
    
    async def start(self) -> None:
        """Start the scheduler task"""
        self._task = asyncio.create_task(self._schedule_loop())
    
    async def stop(self) -> None:
        """Stop the scheduler task"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _schedule_loop(self) -> None:
        """Main scheduling loop"""
        while True:
            next_run = self._calculate_next_run()
            await asyncio.sleep((next_run - datetime.now()).total_seconds())
            await self._execute_update()
    
    def _calculate_next_run(self) -> datetime:
        """Calculate next scheduled run time"""
        # If fixed_update_time is 'XX:XX', use random time
        # Otherwise use fixed time
        ...
    
    async def _execute_update(self) -> None:
        """Execute scheduled graph update"""
        ...

@asynccontextmanager
async def managed_scheduler(scheduler: TaskScheduler):
    """Context manager for scheduler lifecycle"""
    await scheduler.start()
    try:
        yield scheduler
    finally:
        await scheduler.stop()
```

**Responsibilities**:
- Calculate next run time based on update interval and fixed time
- Sleep until next scheduled run
- Trigger graph generation and posting
- Handle errors during scheduled execution
- Support graceful shutdown with task cancellation

**Scheduling Logic**:
- If `fixed_update_time` is 'XX:XX': random time within update interval
- If `fixed_update_time` is 'HH:MM': daily at that specific time
- Update interval in days (1-365)
- Persist last run time to avoid duplicate runs on restart


### 6. Rate Limiter

**Purpose**: Prevent command spam with per-user and global cooldowns.

**Key Classes**:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypedDict
import contextvars

# Context variable for current user
current_user_id = contextvars.ContextVar[int]('current_user_id')

class CooldownInfo(TypedDict):
    remaining_seconds: float
    is_user_cooldown: bool

@dataclass(slots=True)
class RateLimiter:
    """Manages command rate limiting"""
    config: RateLimitingConfig
    _user_cooldowns: dict[tuple[str, int], datetime]
    _global_cooldowns: dict[str, datetime]
    
    def check_cooldown(
        self,
        command: str,
        user_id: int
    ) -> CooldownInfo | None:
        """Check if command is on cooldown, return info if so"""
        # Check user cooldown
        # Check global cooldown
        # Return None if no cooldown active
        ...
    
    def record_usage(self, command: str, user_id: int) -> None:
        """Record command usage for cooldown tracking"""
        now = datetime.now()
        # Record user cooldown
        # Record global cooldown
        ...
    
    def cleanup_expired(self) -> None:
        """Remove expired cooldown entries"""
        ...
```

**Responsibilities**:
- Track per-user cooldowns with command and user ID
- Track global cooldowns per command
- Calculate remaining cooldown time
- Clean up expired cooldown entries periodically
- Support disabling cooldowns (0 value)

**Cooldown Types**:
- User cooldown: minutes (0-1440)
- Global cooldown: seconds (0-86400)
- Separate tracking for each command type


### 7. Web UI Server

**Purpose**: Provide web-based configuration management interface that works alongside manual YAML editing.

**Key Classes**:

```python
from dataclasses import dataclass
from aiohttp import web
import aiohttp_jinja2
import jinja2
from pathlib import Path

@dataclass(slots=True)
class WebUIServer:
    """Web server for configuration management"""
    config_manager: ConfigLoader
    config_path: Path
    host: str
    port: int
    bot_instance: TGraphBot  # Reference to bot for reload
    
    async def start(self) -> None:
        """Start the web server"""
        app = web.Application()
        
        # Setup Jinja2 templates
        aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader('templates')
        )
        
        # Register routes
        app.router.add_get('/', self.index)
        app.router.add_get('/api/config', self.get_config)
        app.router.add_post('/api/config', self.update_config)
        app.router.add_post('/api/config/reload', self.reload_config)
        app.router.add_get('/api/config/file-modified', self.check_file_modified)
        app.router.add_static('/static', 'static')
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
    
    @aiohttp_jinja2.template('index.html')
    async def index(self, request: web.Request) -> dict[str, object]:
        """Render main configuration page"""
        return {
            'config_path': str(self.config_path),
            'last_modified': self.config_path.stat().st_mtime
        }
    
    async def get_config(self, request: web.Request) -> web.Response:
        """API endpoint to get current configuration from file"""
        # Always read from file to get latest state
        config = self.config_manager.load(str(self.config_path))
        
        # Mask sensitive values
        config_dict = config.model_dump()
        config_dict = self._mask_sensitive_values(config_dict)
        
        return web.json_response({
            'config': config_dict,
            'file_modified': self.config_path.stat().st_mtime
        })
    
    async def update_config(self, request: web.Request) -> web.Response:
        """API endpoint to update configuration"""
        data = await request.json()
        
        # Check if file was modified since user loaded it
        client_timestamp = data.get('file_modified')
        current_timestamp = self.config_path.stat().st_mtime
        
        if client_timestamp and client_timestamp < current_timestamp:
            return web.json_response({
                'error': 'Configuration file was modified externally. Please reload.',
                'conflict': True
            }, status=409)
        
        try:
            # Validate new configuration
            new_config = BotConfig(**data['config'])
            
            # Save to YAML file (preserving format)
            self.config_manager.save(new_config, str(self.config_path))
            
            # Trigger bot reload
            await self.bot_instance.reload_configuration()
            
            return web.json_response({
                'success': True,
                'message': 'Configuration saved and reloaded'
            })
            
        except Exception as e:
            return web.json_response({
                'error': str(e)
            }, status=400)
    
    async def reload_config(self, request: web.Request) -> web.Response:
        """API endpoint to reload configuration from file"""
        try:
            await self.bot_instance.reload_configuration()
            return web.json_response({
                'success': True,
                'message': 'Configuration reloaded from file'
            })
        except Exception as e:
            return web.json_response({
                'error': str(e)
            }, status=500)
    
    async def check_file_modified(self, request: web.Request) -> web.Response:
        """Check if config file was modified externally"""
        client_timestamp = float(request.query.get('timestamp', 0))
        current_timestamp = self.config_path.stat().st_mtime
        
        return web.json_response({
            'modified': current_timestamp > client_timestamp,
            'current_timestamp': current_timestamp
        })
    
    def _mask_sensitive_values(self, config: dict) -> dict:
        """Mask sensitive configuration values"""
        if 'services' in config:
            if 'discord' in config['services']:
                config['services']['discord']['token'] = self._mask(
                    config['services']['discord']['token']
                )
            if 'tautulli' in config['services']:
                config['services']['tautulli']['api_key'] = self._mask(
                    config['services']['tautulli']['api_key']
                )
        return config
    
    def _mask(self, value: str) -> str:
        """Mask all but last 4 characters"""
        if len(value) <= 4:
            return '****'
        return '*' * (len(value) - 4) + value[-4:]
```

**Responsibilities**:
- Serve HTML/CSS/JS for configuration interface
- Provide REST API for configuration CRUD operations
- Always read latest file state (support manual edits)
- Detect external file modifications and warn user
- Validate configuration changes before saving
- Preserve YAML formatting and comments when saving
- Mask sensitive values in UI (API keys, tokens)
- Trigger configuration reload after updates

**UI Features**:
- Organized sections matching YAML structure
- Input validation with helpful error messages
- Real-time validation feedback
- Sensitive value masking with reveal option
- Save and reload functionality
- Warning when file modified externally
- Display path to config file for manual editing
- Reload button to refresh from file

**Workflow Support**:

1. **User edits YAML manually**:
   - Edit `config.yaml` with text editor
   - Click "Reload" button in Web UI (or restart bot)
   - Changes take effect immediately

2. **User edits via Web UI**:
   - Web UI reads current file state
   - Make changes in browser
   - Click "Save" - validates and writes to YAML
   - Bot automatically reloads configuration

3. **Concurrent editing detection**:
   - Web UI tracks file modification timestamp
   - If file changed externally while editing, show warning
   - User can choose to reload (lose changes) or overwrite

**Technology Stack**:
- aiohttp for async web server
- Jinja2 for HTML templating
- ruamel.yaml for format-preserving YAML editing
- Vanilla JavaScript for frontend interactivity
- CSS for styling (no heavy frameworks)


### 8. Localization System

**Purpose**: Support multiple languages for bot messages and graph labels.

**Key Classes**:

```python
from dataclasses import dataclass
from typing import TypedDict
import json

class LocalizedStrings(TypedDict):
    """Type-safe localized string dictionary"""
    command_update_graphs_description: str
    command_my_stats_description: str
    command_config_description: str
    error_rate_limited: str
    error_tautulli_connection: str
    # ... more strings

@dataclass(slots=True, frozen=True)
class Localizer:
    """Manages localized strings"""
    language: str
    strings: LocalizedStrings
    
    @classmethod
    def load(cls, language: str) -> 'Localizer':
        """Load localized strings for language"""
        # Load from JSON file: locales/{language}.json
        # Fall back to 'en' if language not found
        ...
    
    def get(self, key: str, **kwargs: object) -> str:
        """Get localized string with optional formatting"""
        template = self.strings.get(key, key)
        return template.format(**kwargs)
```

**Responsibilities**:
- Load language files from JSON
- Provide type-safe access to localized strings
- Support string formatting with parameters
- Fall back to English if translation missing
- Support graph labels and axis titles

**Supported Languages**:
- English (en) - default
- Danish (da)
- Extensible for additional languages

**String Categories**:
- Command descriptions
- Error messages
- Success messages
- Graph labels and titles
- Time format strings


### 9. Data Retention Manager

**Purpose**: Clean up old graph files to manage disk space.

**Key Classes**:

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

@dataclass(slots=True)
class DataRetentionManager:
    """Manages graph file cleanup"""
    output_dir: Path
    keep_days: int
    
    async def cleanup_old_files(self) -> tuple[int, int]:
        """Remove files older than keep_days, return (count, bytes)"""
        cutoff = datetime.now() - timedelta(days=self.keep_days)
        deleted_count = 0
        deleted_bytes = 0
        
        for file_path in self.output_dir.glob('*.png'):
            if file_path.stat().st_mtime < cutoff.timestamp():
                deleted_bytes += file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
        
        return deleted_count, deleted_bytes
    
    async def schedule_daily_cleanup(self) -> None:
        """Run cleanup daily at midnight"""
        while True:
            # Calculate seconds until next midnight
            now = datetime.now()
            tomorrow = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            await asyncio.sleep((tomorrow - now).total_seconds())
            
            count, bytes_freed = await self.cleanup_old_files()
            # Log cleanup results
```

**Responsibilities**:
- Identify graph files older than retention period
- Delete old files and track space reclaimed
- Run cleanup daily at midnight
- Log cleanup operations
- Handle file deletion errors gracefully


## Data Models

### Configuration Models

All configuration models use Pydantic for validation at API boundaries:

```python
from pydantic import BaseModel, Field

class GraphDimensions(BaseModel):
    width: int = Field(ge=6, le=20)
    height: int = Field(ge=4, le=16)
    dpi: int = Field(ge=72, le=300)

class GraphColors(BaseModel):
    tv: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    movie: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    background: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')

class AnnotationConfig(BaseModel):
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    outline_color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    enable_outline: bool
    font_size: int = Field(ge=6, le=24)

class SeabornConfig(BaseModel):
    style: str = Field(pattern=r'^(whitegrid|darkgrid|white|dark|ticks)$', default='darkgrid')
    context: str = Field(pattern=r'^(paper|notebook|talk|poster)$', default='notebook')
    palette: str = Field(default='muted')

class GraphAppearanceConfig(BaseModel):
    dimensions: GraphDimensions
    colors: GraphColors
    grid: GridConfig
    annotations: AnnotationConfig
    palettes: dict[str, str]
    seaborn: SeabornConfig
```

### Domain Models

Internal domain models use dataclasses with slots:

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(slots=True, frozen=True)
class StreamRecord:
    """Processed stream record from Tautulli"""
    timestamp: datetime
    media_type: str  # "movie" or "tv"
    stream_type: str  # "direct_play", "transcode", "copy"
    platform: str
    user: str
    source_resolution: str
    stream_resolution: str

@dataclass(slots=True)
class AggregatedData:
    """Aggregated data for graph generation"""
    dates: list[datetime]
    counts: list[int]
    labels: list[str]
    
@dataclass(slots=True)
class GraphMetadata:
    """Metadata about generated graph"""
    graph_type: str
    file_path: str
    generated_at: datetime
    data_range_days: int
```


## Error Handling

### Exception Hierarchy

```python
class TGraphBotError(Exception):
    """Base exception for all TGraph Bot errors"""
    pass

class ConfigurationError(TGraphBotError):
    """Configuration validation or loading errors"""
    pass

class TautulliAPIError(TGraphBotError):
    """Tautulli API communication errors"""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

class GraphGenerationError(TGraphBotError):
    """Graph generation and rendering errors"""
    pass

class RateLimitError(TGraphBotError):
    """Command rate limit exceeded"""
    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after
```

### Error Handling Strategy

**Configuration Errors**:
- Fail fast on startup with detailed error messages
- Log all validation errors with field names and expected values
- Exit with non-zero status code

**API Errors**:
- Retry transient errors (5xx, timeouts) with exponential backoff
- Log all API errors with request/response details
- Send user-friendly error messages to Discord
- Don't retry client errors (4xx)

**Graph Generation Errors**:
- Log full stack trace for debugging
- Send error message to Discord with graph type
- Continue with other graphs if one fails
- Include error count in completion message

**Discord API Errors**:
- Implement reconnection logic with exponential backoff
- Log connection state changes
- Queue messages during disconnection
- Retry failed message posts

### Structured Concurrency Error Handling

Using TaskGroup and ExceptionGroup for concurrent operations:

```python
async def generate_all_graphs(
    data: list[StreamRecord],
    *,
    config: GraphsConfig
) -> list[GraphMetadata]:
    """Generate all enabled graphs concurrently"""
    results: list[GraphMetadata] = []
    
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(generate_graph(graph_type, data, config))
                for graph_type in enabled_graph_types(config)
            ]
    except* GraphGenerationError as eg:
        # Log each graph generation error
        for exc in eg.exceptions:
            logger.error(f"Graph generation failed: {exc}")
        # Continue with successfully generated graphs
    
    return results
```


## Testing Strategy

### Unit Testing

**Test Framework**: pytest with fixtures and parametrization

**Coverage Areas**:
1. Configuration validation (Pydantic models)
2. Data transformation and aggregation logic
3. Rate limiter cooldown calculations
4. Localization string loading and formatting
5. Graph data preparation (without rendering)
6. Privacy/anonymization logic
7. Schedule calculation logic

**Example Test Structure**:

```python
import pytest
from datetime import datetime, timedelta

class TestRateLimiter:
    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        config = RateLimitingConfig(
            commands={
                'update_graphs': CommandLimits(
                    user_cooldown_minutes=5,
                    global_cooldown_seconds=60
                )
            }
        )
        return RateLimiter(config)
    
    def test_no_cooldown_on_first_use(self, rate_limiter: RateLimiter) -> None:
        result = rate_limiter.check_cooldown('update_graphs', user_id=123)
        assert result is None
    
    @pytest.mark.parametrize("elapsed_seconds,should_be_limited", [
        (30, True),   # 30 seconds < 5 minutes
        (300, False), # 5 minutes = cooldown period
        (400, False), # > 5 minutes
    ])
    def test_user_cooldown(
        self,
        rate_limiter: RateLimiter,
        elapsed_seconds: int,
        should_be_limited: bool
    ) -> None:
        # Test cooldown behavior
        ...
```

### Integration Testing

**Test Areas**:
1. Tautulli API client with mock server
2. Discord bot command handling with mock interactions
3. Configuration loading and saving
4. Web UI API endpoints
5. End-to-end graph generation pipeline

**Mock Strategy**:
- Mock external APIs (Tautulli, Discord)
- Use in-memory configuration for tests
- Mock file system operations where appropriate
- Use pytest-asyncio for async tests

### Type Checking

**Tools**:
- basedpyright in recommended mode with failOnWarnings=true
- Run in CI pipeline before tests

**Configuration**:
```toml
[tool.basedpyright]
typeCheckingMode = "recommended"
failOnWarnings = true
pythonVersion = "3.14"
pythonPlatform = "All"
```

### Code Quality

**Tools**:
- ruff for linting and formatting
- Run in CI pipeline

**Configuration**:
```toml
[tool.ruff]
line-length = 88
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "B", "I", "N", "UP", "C90"]
ignore = ["E501"]
fixable = ["ALL"]

[tool.ruff.format]
docstring-code-format = true
```

### Test Execution

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/tgraph_bot --cov-report=html

# Type checking
uv run basedpyright

# Linting and formatting
uv run ruff check .
uv run ruff format .
```


## Security Considerations

### Input Validation

**Configuration Validation**:
- Use Pydantic Field constraints for all numeric ranges
- Validate regex patterns for string formats (hex colors, time formats)
- Validate URL formats for Tautulli endpoint
- Validate Discord IDs are positive integers

**User Input Validation**:
- Discord slash commands have built-in type validation
- Web UI validates all inputs client-side and server-side
- Sanitize any user-provided strings before logging

### Secrets Management

**API Keys and Tokens**:
- Load from environment variables as primary method
- Support YAML configuration as fallback
- Mask sensitive values in logs (show only last 4 characters)
- Mask sensitive values in Web UI with reveal option
- Never include secrets in error messages

**Example**:
```python
import os
from dotenv import load_dotenv

def load_config() -> BotConfig:
    load_dotenv()
    
    # Override YAML with environment variables
    config = BotConfig.from_yaml('config.yaml')
    
    if discord_token := os.getenv('DISCORD_TOKEN'):
        config.services.discord.token = discord_token
    
    if tautulli_key := os.getenv('TAUTULLI_API_KEY'):
        config.services.tautulli.api_key = tautulli_key
    
    return config

def mask_sensitive(value: str) -> str:
    """Mask all but last 4 characters"""
    if len(value) <= 4:
        return '****'
    return '*' * (len(value) - 4) + value[-4:]
```

### HTTP Security

**Tautulli API Client**:
- Use HTTPS for production deployments
- Validate SSL certificates
- Set reasonable timeouts (30 seconds)
- Implement request size limits

**Web UI Server**:
- Bind to localhost by default (127.0.0.1)
- Support configurable IP binding for Docker deployments
- Implement CORS headers if needed
- Add rate limiting for API endpoints
- Use secure session management if authentication added

### Dependency Security

**Supply Chain Security**:
- Pin exact versions in production
- Use uv for fast dependency resolution
- Regular dependency updates
- Monitor for security advisories

**Example pyproject.toml**:
```toml
[project]
dependencies = [
    "nextcord>=2.6.0,<3.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "httpx>=0.27.0,<1.0.0",
    "matplotlib>=3.8.0,<4.0.0",
    "seaborn>=0.13.0,<1.0.0",
    "aiohttp>=3.9.0,<4.0.0",
    "pyyaml>=6.0.0,<7.0.0",
]
```

### Privacy

**Username Censoring**:
- Apply censoring consistently across all graphs
- Maintain consistent anonymized labels within generation cycle
- Never log uncensored usernames when censoring enabled
- Personal stats always show actual username to requesting user

**Data Retention**:
- Automatically delete old graph files
- Don't persist Tautulli data beyond graph generation
- Clear in-memory data after graph generation


## Deployment Architecture

### Application Structure

```
tgraph-bot/
├── src/
│   └── tgraph_bot/
│       ├── __init__.py
│       ├── __main__.py              # Entry point
│       ├── bot.py                   # Discord bot class
│       ├── config/
│       │   ├── __init__.py
│       │   ├── models.py            # Pydantic config models
│       │   └── loader.py            # YAML loading/saving
│       ├── api/
│       │   ├── __init__.py
│       │   └── tautulli.py          # Tautulli API client
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── graphs.py            # Graph commands
│       │   └── config.py            # Config command
│       ├── graphs/
│       │   ├── __init__.py
│       │   ├── generator.py         # Graph generation logic
│       │   ├── types/               # Individual graph types
│       │   │   ├── __init__.py
│       │   │   ├── daily_play_count.py
│       │   │   ├── play_by_dayofweek.py
│       │   │   └── ...
│       │   └── styling.py           # Visual styling logic
│       ├── scheduler/
│       │   ├── __init__.py
│       │   └── tasks.py             # Task scheduling
│       ├── rate_limiting/
│       │   ├── __init__.py
│       │   └── limiter.py           # Rate limiter
│       ├── web/
│       │   ├── __init__.py
│       │   ├── server.py            # Web UI server
│       │   ├── templates/           # Jinja2 templates
│       │   │   └── index.html
│       │   └── static/              # CSS/JS
│       │       ├── style.css
│       │       └── app.js
│       ├── localization/
│       │   ├── __init__.py
│       │   ├── localizer.py
│       │   └── locales/
│       │       ├── en.json
│       │       └── da.json
│       └── utils/
│           ├── __init__.py
│           ├── logging.py           # Logging setup
│           └── retention.py         # Data retention
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_rate_limiter.py
│   ├── test_graphs.py
│   └── ...
├── config.yaml                      # Default configuration
├── pyproject.toml
├── README.md
└── .python-version
```

### Startup Sequence

1. Load configuration from YAML and environment variables
2. Validate configuration (fail fast if invalid)
3. Initialize logging system
4. Create Discord bot instance
5. Register command handlers (cogs)
6. Initialize Tautulli API client
7. Start task scheduler
8. Start data retention manager
9. Start Web UI server
10. Connect Discord bot to API
11. Log successful startup

### Shutdown Sequence

1. Receive shutdown signal (SIGTERM/SIGINT)
2. Stop accepting new commands
3. Cancel scheduled tasks gracefully
4. Wait for in-progress graph generation to complete
5. Disconnect from Discord API
6. Stop Web UI server
7. Cleanup temporary files
8. Log shutdown completion
9. Exit with status code 0

### Configuration Management

**Default Configuration Location**: `./config.yaml`

**Environment Variable Overrides**:
- `DISCORD_TOKEN`: Override Discord bot token
- `TAUTULLI_API_KEY`: Override Tautulli API key
- `TAUTULLI_URL`: Override Tautulli URL
- `WEB_UI_HOST`: Override Web UI bind address
- `WEB_UI_PORT`: Override Web UI port

**Dual Configuration Interface**:

The system supports both manual YAML editing and Web UI configuration management:

1. **Manual YAML Editing**:
   - Users can edit `config.yaml` directly with any text editor
   - Changes take effect on next bot restart OR via reload command
   - YAML comments and formatting are preserved
   - Validation occurs on load with clear error messages

2. **Web UI Configuration**:
   - Web UI reads current `config.yaml` on page load
   - Changes are validated before saving
   - Saves back to `config.yaml` preserving structure
   - Automatically triggers configuration reload

3. **File Watching for Auto-Reload** (Optional Enhancement):
   - Bot can optionally watch `config.yaml` for external changes
   - Automatically reload when file modified externally
   - Validate before applying changes
   - Log reload events

**Configuration Reload Process**:
```python
async def reload_configuration(self, new_config_path: str | None = None) -> None:
    """Reload configuration from YAML file"""
    try:
        # Load and validate new configuration
        new_config = self.config_loader.load(new_config_path or self.config_path)
        
        # Validate before applying
        errors = self.config_loader.validate(new_config)
        if errors:
            raise ConfigurationError(f"Invalid configuration: {errors}")
        
        # Apply new configuration
        old_config = self.config
        self.config = new_config
        
        # Update components that need reconfiguration
        if new_config.automation != old_config.automation:
            await self.scheduler.reconfigure(new_config.automation)
        
        if new_config.rate_limiting != old_config.rate_limiting:
            self.rate_limiter.reconfigure(new_config.rate_limiting)
        
        # Note: Rate limiter preserves existing cooldowns
        # Note: Discord connection doesn't need restart for most changes
        
        logger.info("Configuration reloaded successfully")
        
    except Exception as e:
        logger.error(f"Configuration reload failed: {e}")
        # Keep old configuration on failure
        raise
```

**YAML Preservation Strategy**:

When Web UI saves configuration, it preserves YAML structure:
```python
import ruamel.yaml

def save_config_preserving_format(
    config: BotConfig,
    path: str
) -> None:
    """Save configuration while preserving YAML comments and formatting"""
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    
    # Load existing YAML to preserve comments
    with open(path, 'r') as f:
        yaml_data = yaml.load(f)
    
    # Update values from Pydantic model
    updated_data = config.model_dump()
    
    # Merge while preserving structure
    merge_preserving_comments(yaml_data, updated_data)
    
    # Write back
    with open(path, 'w') as f:
        yaml.dump(yaml_data, f)
```

**Conflict Resolution**:
- Web UI always reads latest file state on page load
- If file changed externally while editing in Web UI, show warning on save
- Provide option to reload or overwrite
- Log all configuration changes with timestamp and source (manual/web UI)

**No Restart Required For**:
- Graph styling changes (colors, dimensions, annotations)
- Rate limiting adjustments
- Schedule timing changes
- Localization language changes
- Data retention period changes

**Restart Required For**:
- Discord token changes
- Tautulli API URL/key changes (or use reload command)
- Web UI host/port changes


## Performance Considerations

### Async I/O Optimization

**Concurrent Operations**:
- Use TaskGroup for parallel graph generation
- Fetch Tautulli data concurrently for multiple time ranges
- Post multiple graphs to Discord concurrently
- Use httpx async client for all HTTP requests

**Example**:
```python
async def generate_and_post_graphs() -> None:
    """Generate all graphs concurrently and post to Discord"""
    
    # Fetch data
    data = await tautulli_client.get_history(days=30)
    
    # Generate graphs concurrently
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(generate_graph(graph_type, data))
                for graph_type in enabled_graph_types
            ]
    except* GraphGenerationError as eg:
        logger.error(f"Some graphs failed: {eg}")
    
    # Post to Discord concurrently
    async with asyncio.TaskGroup() as tg:
        for graph_path in graph_paths:
            tg.create_task(post_graph(graph_path))
```

### Memory Management

**Data Structures**:
- Use dataclasses with slots=True for 40% memory savings
- Use frozen=True for immutable data structures
- Clear large data structures after processing
- Stream large API responses instead of loading entirely

**Graph Generation**:
- Generate graphs one at a time if memory constrained
- Close matplotlib figures after saving
- Use appropriate DPI (100 default, not 300)
- Limit graph dimensions to reasonable sizes

### Caching Strategy

**Configuration Caching**:
- Cache parsed configuration in memory
- Reload only when explicitly requested
- Share configuration across components

**Localization Caching**:
- Load language files once at startup
- Cache in memory for fast access
- No need to reload during runtime

**No Data Caching**:
- Don't cache Tautulli data (always fetch fresh)
- Don't cache generated graphs (regenerate on demand)
- Rely on Tautulli's own caching

### Rate Limiting Performance

**Efficient Cooldown Tracking**:
- Use dict with tuple keys for O(1) lookups
- Periodically cleanup expired entries
- Don't persist cooldowns (in-memory only)

**Cleanup Strategy**:
```python
async def periodic_cleanup(self) -> None:
    """Clean up expired cooldowns every hour"""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        self.cleanup_expired()
```


## Logging and Monitoring

### Logging Strategy

**Log Levels**:
- DEBUG: Detailed information for debugging (API requests/responses, data transformations)
- INFO: General operational messages (startup, graph generation, scheduled tasks)
- WARNING: Unexpected but handled situations (missing translations, API retries)
- ERROR: Errors that prevent specific operations (graph generation failures, API errors)
- CRITICAL: Errors that prevent bot operation (configuration errors, connection failures)

**Log Format**:
```
[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s
```

**Structured Logging**:
```python
import logging
from typing import Any

logger = logging.getLogger(__name__)

def log_api_request(
    method: str,
    url: str,
    *,
    status_code: int | None = None,
    error: str | None = None
) -> None:
    """Log API request with structured data"""
    extra: dict[str, Any] = {
        'method': method,
        'url': url,
    }
    
    if status_code:
        extra['status_code'] = status_code
    
    if error:
        logger.error(f"API request failed: {method} {url}", extra=extra)
    else:
        logger.info(f"API request: {method} {url}", extra=extra)
```

### Monitoring Metrics

**Key Metrics to Track**:
1. Graph generation time per type
2. Tautulli API response times
3. Discord API response times
4. Command usage frequency
5. Rate limit hits
6. Error rates by type
7. Scheduled task execution times

**Implementation**:
```python
from dataclasses import dataclass
from datetime import datetime
import contextvars

# Context variable for operation tracking
operation_id = contextvars.ContextVar[str]('operation_id')

@dataclass(slots=True)
class OperationMetrics:
    """Track metrics for an operation"""
    operation: str
    start_time: datetime
    end_time: datetime | None = None
    success: bool = True
    error: str | None = None
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

# Usage
async def generate_graph_with_metrics(graph_type: str) -> None:
    metrics = OperationMetrics(
        operation=f"generate_{graph_type}",
        start_time=datetime.now()
    )
    
    try:
        await generate_graph(graph_type)
        metrics.success = True
    except Exception as e:
        metrics.success = False
        metrics.error = str(e)
        raise
    finally:
        metrics.end_time = datetime.now()
        logger.info(
            f"Graph generation completed: {graph_type}",
            extra={
                'duration': metrics.duration_seconds,
                'success': metrics.success
            }
        )
```

### Health Checks

**Health Check Endpoint**:
```python
async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint for monitoring"""
    health = {
        'status': 'healthy',
        'discord_connected': bot.is_ready(),
        'tautulli_reachable': await check_tautulli_connection(),
        'last_graph_generation': last_generation_time.isoformat(),
        'uptime_seconds': (datetime.now() - start_time).total_seconds()
    }
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return web.json_response(health, status=status_code)
```


## Future Enhancements

### Potential Features (Not in Initial Implementation)

1. **Database Persistence**:
   - Store historical metrics for trend analysis
   - Cache Tautulli data to reduce API calls
   - Persist rate limit state across restarts

2. **Advanced Graph Types**:
   - Heatmaps for viewing patterns
   - Comparison graphs (week-over-week, month-over-month)
   - User-specific platform preferences
   - Geographic distribution (if available from Tautulli)

3. **Interactive Graphs**:
   - Discord buttons for graph type selection
   - Date range selection via slash command options
   - User filtering via command parameters

4. **Notification System**:
   - Alert on unusual activity patterns
   - Notify on transcoding spikes
   - Report on storage usage trends

5. **Multi-Server Support**:
   - Support multiple Tautulli instances
   - Post to different Discord channels per server
   - Aggregate statistics across servers

6. **Authentication for Web UI**:
   - User login system
   - Role-based access control
   - Audit log for configuration changes

7. **Export Capabilities**:
   - Export raw data as CSV/JSON
   - Generate PDF reports
   - Email scheduled reports

8. **Advanced Scheduling**:
   - Multiple schedules per graph type
   - Cron-like scheduling expressions
   - Timezone support

9. **Plugin System**:
   - Custom graph types via plugins
   - Custom data sources beyond Tautulli
   - Custom styling themes

10. **Performance Optimizations**:
    - Graph caching with TTL
    - Incremental data updates
    - Background pre-generation

## Design Decisions and Rationales

### Why nextcord over discord.py?

nextcord is an actively maintained fork of discord.py with:
- Better slash command support
- Active development and bug fixes
- Modern Python async patterns
- Good documentation and community

### Why Pydantic for Configuration?

Pydantic provides:
- Runtime validation with clear error messages
- Type-safe configuration access
- Automatic conversion of types
- JSON schema generation for documentation
- Integration with modern Python type hints

### Why matplotlib + seaborn over plotly/altair?

matplotlib with seaborn offers:
- Mature and stable library ecosystem
- Extensive customization options
- Professional aesthetics out of the box (seaborn)
- No JavaScript dependencies
- Smaller file sizes for PNG output
- Better control over styling
- Statistical visualization capabilities (seaborn)
- Excellent color palette management (seaborn)

### Why aiohttp for Web UI?

aiohttp provides:
- Native async support matching bot architecture
- Lightweight compared to Django/Flask
- Good performance for simple UI
- Built-in WebSocket support for future features
- Jinja2 integration for templating

### Why YAML over JSON/TOML?

YAML is:
- More human-readable for large configurations
- Supports comments for documentation
- Common in DevOps/Docker environments
- Easier to edit manually
- Better for hierarchical data

### Why In-Memory Rate Limiting?

In-memory rate limiting:
- Simpler implementation
- No external dependencies
- Sufficient for single-instance deployment
- Acceptable to reset on restart
- Can be upgraded to Redis if needed

