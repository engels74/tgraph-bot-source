"""Configuration models using Pydantic for validation.

This module defines all configuration models for TGraph Bot using Pydantic
for runtime validation and type safety.

These are stub implementations to support test development (TDD approach).
Full implementation will be added in task 4.
"""

from pydantic import BaseModel, Field


class TautulliConfig(BaseModel):
    """Tautulli service configuration."""

    api_key: str = Field(min_length=32)
    url: str = Field(pattern=r"^https?://.+")


class DiscordConfig(BaseModel):
    """Discord service configuration."""

    token: str = Field(min_length=50)
    channel_id: int = Field(gt=0)
    timestamp_format: str = Field(pattern=r"^[tTdDfFR]$")
    ephemeral_message_delete_after: float = Field(ge=1.0, le=3600.0)


class ServicesConfig(BaseModel):
    """Services configuration section."""

    tautulli: TautulliConfig
    discord: DiscordConfig


class AutomationConfig(BaseModel):
    """Automation configuration section."""

    enabled: bool
    update_interval_days: int = Field(ge=1, le=365)
    fixed_update_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$|^XX:XX$")


class DataCollectionConfig(BaseModel):
    """Data collection configuration section."""

    history_days: int = Field(ge=1, le=365)
    max_records_per_request: int = Field(ge=100, le=10000)


class PrivacyConfig(BaseModel):
    """Privacy configuration section."""

    censor_usernames: bool


class SystemConfig(BaseModel):
    """System configuration section."""

    language: str
    log_level: str
    output_directory: str
    keep_graphs_days: int = Field(ge=1, le=365)
    privacy: PrivacyConfig


class GraphDimensions(BaseModel):
    """Graph dimensions configuration."""

    width: int = Field(ge=6, le=20)
    height: int = Field(ge=4, le=16)
    dpi: int = Field(ge=72, le=300)


class GraphColors(BaseModel):
    """Graph color configuration."""

    tv: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    movie: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    background: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class GridConfig(BaseModel):
    """Grid configuration."""

    enabled: bool
    alpha: float


class AnnotationConfig(BaseModel):
    """Annotation configuration."""

    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    outline_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    enable_outline: bool
    font_size: int = Field(ge=6, le=24)


class SeabornConfig(BaseModel):
    """Seaborn styling configuration."""

    style: str = Field(pattern=r"^(whitegrid|darkgrid|white|dark|ticks)$")
    context: str = Field(pattern=r"^(paper|notebook|talk|poster)$")
    palette: str


class GraphAppearanceConfig(BaseModel):
    """Graph appearance configuration."""

    dimensions: GraphDimensions
    colors: GraphColors
    grid: GridConfig
    annotations: AnnotationConfig
    palettes: dict[str, str]
    seaborn: SeabornConfig


class GraphConfig(BaseModel):
    """Individual graph configuration."""

    enabled: bool
    media_type_separation: bool
    palette: str
    annotations_enabled: bool
    peak_highlighting_enabled: bool
    stacked: bool


class TopGraphConfig(GraphConfig):
    """Configuration for top N graphs (platforms, users)."""

    limit: int = Field(ge=3, le=20)


class GraphsConfig(BaseModel):
    """Graphs configuration section."""

    appearance: GraphAppearanceConfig
    daily_play_count: GraphConfig
    play_count_by_day_of_week: GraphConfig
    play_count_by_hour_of_day: GraphConfig
    top_platforms: (
        TopGraphConfig | dict[str, object]
    )  # Allow dict for flexibility in tests
    top_users: TopGraphConfig | dict[str, object]  # Allow dict for flexibility in tests
    play_count_by_month: GraphConfig
    daily_play_count_by_stream_type: GraphConfig
    daily_concurrent_stream_count_by_stream_type: GraphConfig
    play_count_by_source_resolution: GraphConfig
    play_count_by_stream_resolution: GraphConfig
    play_count_by_platform_and_stream_type: GraphConfig
    play_count_by_user_and_stream_type: GraphConfig


class CommandLimits(BaseModel):
    """Command rate limit configuration."""

    user_cooldown_minutes: int = Field(ge=0, le=1440)
    global_cooldown_seconds: int = Field(ge=0, le=86400)


class RateLimitingConfig(BaseModel):
    """Rate limiting configuration section."""

    config: CommandLimits
    update_graphs: CommandLimits
    my_stats: CommandLimits


class BotConfig(BaseModel):
    """Complete bot configuration."""

    services: ServicesConfig
    automation: AutomationConfig
    data_collection: DataCollectionConfig
    system: SystemConfig
    graphs: GraphsConfig
    rate_limiting: RateLimitingConfig
