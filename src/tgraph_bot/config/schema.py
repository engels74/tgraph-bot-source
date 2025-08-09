"""Configuration schema for TGraph Bot using nested Pydantic models."""

import re
from typing import Annotated, Literal, ClassVar

from pydantic import BaseModel, Field, field_validator, ConfigDict


class TautulliConfig(BaseModel):
    """Tautulli service configuration."""

    api_key: str = Field(
        ...,
        description="API key for Tautulli access",
        min_length=1,
    )
    url: str = Field(
        ...,
        description="Base URL for Tautulli API (e.g., http://localhost:8181/api/v2)",
        pattern=r"^https?://.*",
    )

    @field_validator("url")
    @classmethod
    def validate_tautulli_url(cls, v: str) -> str:
        """Validate and normalize Tautulli URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Tautulli URL must start with http:// or https://")
        return v.rstrip("/")


class DiscordConfig(BaseModel):
    """Discord service configuration."""

    token: str = Field(
        ...,
        description="Discord bot token",
        min_length=1,
    )
    channel_id: int = Field(
        ...,
        description="Discord channel ID for posting graphs",
        gt=0,
    )
    timestamp_format: Literal["t", "T", "d", "D", "f", "F", "R"] = Field(
        default="R",
        description="Discord timestamp format (t=short time, T=long time, d=short date, D=long date, f=short date/time, F=long date/time, R=relative time)",
    )
    ephemeral_message_delete_after: Annotated[float, Field(gt=0, le=3600)] = Field(
        default=30.0,
        description="Time in seconds after which ephemeral Discord messages are automatically deleted",
    )

    @field_validator("token")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        """Validate Discord token format."""
        if len(v) < 10:
            raise ValueError("Discord token appears to be too short")
        return v


class ServicesConfig(BaseModel):
    """External services configuration."""

    tautulli: TautulliConfig
    discord: DiscordConfig


class SchedulingConfig(BaseModel):
    """Scheduling configuration for automation."""

    update_days: Annotated[int, Field(ge=1, le=365)] = Field(
        default=7,
        description="Number of days between automatic updates",
    )
    fixed_update_time: str = Field(
        default="XX:XX",
        description="Fixed time for updates in HH:MM format, or 'XX:XX' to disable",
        pattern=r"^(XX:XX|([01]?[0-9]|2[0-3]):[0-5][0-9])$",
    )


class DataRetentionConfig(BaseModel):
    """Data retention configuration."""

    keep_days: Annotated[int, Field(ge=1, le=365)] = Field(
        default=7,
        description="Number of days to keep generated graphs",
    )


class AutomationConfig(BaseModel):
    """Automation and scheduling configuration."""

    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)
    data_retention: DataRetentionConfig = Field(default_factory=DataRetentionConfig)


class TimeRangesConfig(BaseModel):
    """Time range configuration for data collection."""

    days: Annotated[int, Field(ge=1, le=365)] = Field(
        default=30,
        description="Time range in days for graph data",
    )
    months: Annotated[int, Field(ge=1, le=60)] = Field(
        default=12,
        description="Time range in months for monthly graph data",
    )


class PrivacyConfig(BaseModel):
    """Privacy configuration for data collection."""

    censor_usernames: bool = Field(
        default=True,
        description="Whether to censor usernames in graphs",
    )


class DataCollectionConfig(BaseModel):
    """Data collection configuration."""

    time_ranges: TimeRangesConfig = Field(default_factory=TimeRangesConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


class LocalizationConfig(BaseModel):
    """Localization configuration."""

    language: str = Field(
        default="en",
        description="Language code for internationalization",
        pattern=r"^[a-z]{2}$",
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate and normalize language code."""
        return v.lower()


class SystemConfig(BaseModel):
    """System configuration."""

    localization: LocalizationConfig = Field(default_factory=LocalizationConfig)


class EnabledTypesConfig(BaseModel):
    """Configuration for enabled graph types."""

    daily_play_count: bool = Field(
        default=True,
        description="Enable daily play count graph generation",
    )
    play_count_by_dayofweek: bool = Field(
        default=True,
        description="Enable play count by day of week graph generation",
    )
    play_count_by_hourofday: bool = Field(
        default=True,
        description="Enable play count by hour of day graph generation",
    )
    top_10_platforms: bool = Field(
        default=True,
        description="Enable top 10 platforms graph generation",
    )
    top_10_users: bool = Field(
        default=True,
        description="Enable top 10 users graph generation",
    )
    play_count_by_month: bool = Field(
        default=True,
        description="Enable play count by month graph generation",
    )

    # Stream Type Graphs
    daily_play_count_by_stream_type: bool = Field(
        default=True,
        description="Enable daily play count by stream type graph generation",
    )
    daily_concurrent_stream_count_by_stream_type: bool = Field(
        default=True,
        description="Enable daily concurrent stream count by stream type graph generation",
    )
    play_count_by_source_resolution: bool = Field(
        default=True,
        description="Enable play count by source resolution graph generation",
    )
    play_count_by_stream_resolution: bool = Field(
        default=True,
        description="Enable play count by stream resolution graph generation",
    )
    play_count_by_platform_and_stream_type: bool = Field(
        default=True,
        description="Enable play count by platform and stream type graph generation",
    )
    play_count_by_user_and_stream_type: bool = Field(
        default=True,
        description="Enable play count by user and stream type graph generation",
    )


class PerGraphSettingsConfig(BaseModel):
    """Configuration for individual graph settings."""

    media_type_separation: bool = Field(
        default=True,
        description="Whether to separate Movies and TV Series in this graph",
    )
    stacked_bar_charts: bool = Field(
        default=True,
        description="Whether to use stacked bars when media type separation is enabled (applies to bar charts only)",
    )


class ResolutionGroupingConfig(BaseModel):
    """Configuration for resolution grouping in analytics graphs."""

    resolution_grouping: str = Field(
        default="standard",
        description="How to group resolutions: 'standard', 'detailed', 'simplified'",
        pattern=r"^(standard|detailed|simplified)$",
    )


class PlayCountBySourceResolutionConfig(ResolutionGroupingConfig):
    """Configuration for Play Count by Source Resolution graph."""

    pass


class PlayCountByStreamResolutionConfig(ResolutionGroupingConfig):
    """Configuration for Play Count by Stream Resolution graph."""

    transcoding_focus: bool = Field(
        default=True,
        description="Emphasize transcoded vs non-transcoded content",
    )


class PerGraphConfig(BaseModel):
    """Per-graph configuration settings."""

    daily_play_count: PerGraphSettingsConfig = Field(
        default_factory=PerGraphSettingsConfig
    )
    play_count_by_dayofweek: PerGraphSettingsConfig = Field(
        default_factory=PerGraphSettingsConfig
    )
    play_count_by_hourofday: PerGraphSettingsConfig = Field(
        default_factory=PerGraphSettingsConfig
    )
    top_10_platforms: PerGraphSettingsConfig = Field(
        default_factory=PerGraphSettingsConfig
    )
    top_10_users: PerGraphSettingsConfig = Field(default_factory=PerGraphSettingsConfig)
    play_count_by_month: PerGraphSettingsConfig = Field(
        default_factory=PerGraphSettingsConfig
    )
    play_count_by_source_resolution: PlayCountBySourceResolutionConfig = Field(
        default_factory=PlayCountBySourceResolutionConfig
    )
    play_count_by_stream_resolution: PlayCountByStreamResolutionConfig = Field(
        default_factory=PlayCountByStreamResolutionConfig
    )


class GraphFeaturesConfig(BaseModel):
    """Graph features configuration."""

    enabled_types: EnabledTypesConfig = Field(default_factory=EnabledTypesConfig)
    media_type_separation: bool = Field(
        default=True,
        description="Whether to separate Movies and TV Series in graphs (deprecated - use per_graph settings)",
    )
    stacked_bar_charts: bool = Field(
        default=True,
        description="Whether to use stacked bars when media type separation is enabled (deprecated - use per_graph settings)",
    )


class DimensionsConfig(BaseModel):
    """Graph dimensions configuration."""

    width: Annotated[int, Field(ge=6, le=20)] = Field(
        default=14,
        description="Width of graphs in inches",
    )
    height: Annotated[int, Field(ge=4, le=16)] = Field(
        default=8,
        description="Height of graphs in inches",
    )
    dpi: Annotated[int, Field(ge=72, le=300)] = Field(
        default=100,
        description="DPI (dots per inch) for graph image quality",
    )


class ColorsConfig(BaseModel):
    """Graph colors configuration."""

    tv: str = Field(
        default="#1f77b4",
        description="Color for TV shows in graphs",
    )
    movie: str = Field(
        default="#ff7f0e",
        description="Color for movies in graphs",
    )
    background: str = Field(
        default="#ffffff",
        description="Background color for graphs",
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(
        validate_assignment=True,
    )

    @field_validator("tv", "movie", "background")
    @classmethod
    def validate_color_format(cls, v: str) -> str:
        """Validate that color values are in valid hex format."""
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError(f"Color must be in hex format (e.g., #1f77b4), got: {v}")
        return v.lower()


class GridConfig(BaseModel):
    """Graph grid configuration."""

    enabled: bool = Field(
        default=False,
        description="Whether to enable grid lines in graphs",
    )


class BasicAnnotationsConfig(BaseModel):
    """Basic annotations configuration."""

    color: str = Field(
        default="#ff0000",
        description="Color for graph annotations",
    )
    outline_color: str = Field(
        default="#000000",
        description="Outline color for graph annotations",
    )
    enable_outline: bool = Field(
        default=True,
        description="Whether to enable annotation outlines",
    )
    font_size: Annotated[int, Field(ge=6, le=24)] = Field(
        default=10,
        description="Font size for bar value annotations",
    )

    @field_validator("color", "outline_color")
    @classmethod
    def validate_color_format(cls, v: str) -> str:
        """Validate that color values are in valid hex format."""
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError(f"Color must be in hex format (e.g., #1f77b4), got: {v}")
        return v.lower()


class EnabledOnConfig(BaseModel):
    """Configuration for which graphs have annotations enabled."""

    daily_play_count: bool = Field(
        default=True,
        description="Enable annotations on daily play count graphs",
    )
    play_count_by_dayofweek: bool = Field(
        default=True,
        description="Enable annotations on day of week graphs",
    )
    play_count_by_hourofday: bool = Field(
        default=True,
        description="Enable annotations on hour of day graphs",
    )
    top_10_platforms: bool = Field(
        default=True,
        description="Enable annotations on top platforms graphs",
    )
    top_10_users: bool = Field(
        default=True,
        description="Enable annotations on top users graphs",
    )
    play_count_by_month: bool = Field(
        default=True,
        description="Enable annotations on monthly graphs",
    )
    
    # Stream Type Graphs
    daily_play_count_by_stream_type: bool = Field(
        default=True,
        description="Enable annotations on daily play count by stream type graphs",
    )
    daily_concurrent_stream_count_by_stream_type: bool = Field(
        default=True,
        description="Enable annotations on daily concurrent stream count by stream type graphs",
    )
    play_count_by_source_resolution: bool = Field(
        default=True,
        description="Enable annotations on play count by source resolution graphs",
    )
    play_count_by_stream_resolution: bool = Field(
        default=True,
        description="Enable annotations on play count by stream resolution graphs",
    )
    play_count_by_platform_and_stream_type: bool = Field(
        default=True,
        description="Enable annotations on play count by platform and stream type graphs",
    )
    play_count_by_user_and_stream_type: bool = Field(
        default=True,
        description="Enable annotations on play count by user and stream type graphs",
    )


class PeaksConfig(BaseModel):
    """Peak annotations configuration."""

    enabled: bool = Field(
        default=True,
        description="Whether to enable peak value annotations on graphs",
    )
    color: str = Field(
        default="#ffcc00",
        description="Background color for peak annotation boxes",
    )
    text_color: str = Field(
        default="#000000",
        description="Text color for peak annotations",
    )

    @field_validator("color", "text_color")
    @classmethod
    def validate_color_format(cls, v: str) -> str:
        """Validate that color values are in valid hex format."""
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError(f"Color must be in hex format (e.g., #1f77b4), got: {v}")
        return v.lower()


class AnnotationsConfig(BaseModel):
    """Annotations configuration."""

    basic: BasicAnnotationsConfig = Field(default_factory=BasicAnnotationsConfig)
    enabled_on: EnabledOnConfig = Field(default_factory=EnabledOnConfig)
    peaks: PeaksConfig = Field(default_factory=PeaksConfig)


class PalettesConfig(BaseModel):
    """Graph color palettes configuration."""

    play_count_by_hourofday: str = Field(
        default="",
        description="Color palette for hourly play count graph (viridis, plasma, inferno, magma, or leave blank for default)",
    )
    top_10_users: str = Field(
        default="",
        description="Color palette for top users graph (viridis, plasma, inferno, magma, or leave blank for default)",
    )
    daily_play_count: str = Field(
        default="",
        description="Color palette for daily play count graph (viridis, plasma, inferno, magma, or leave blank for default)",
    )
    play_count_by_dayofweek: str = Field(
        default="",
        description="Color palette for day of week play count graph (viridis, plasma, inferno, magma, or leave blank for default)",
    )
    top_10_platforms: str = Field(
        default="",
        description="Color palette for top platforms graph (viridis, plasma, inferno, magma, or leave blank for default)",
    )
    play_count_by_month: str = Field(
        default="",
        description="Color palette for monthly play count graph (viridis, plasma, inferno, magma, or leave blank for default)",
    )


class GraphAppearanceConfig(BaseModel):
    """Graph appearance configuration."""

    dimensions: DimensionsConfig = Field(default_factory=DimensionsConfig)
    colors: ColorsConfig = Field(default_factory=ColorsConfig)
    grid: GridConfig = Field(default_factory=GridConfig)
    annotations: AnnotationsConfig = Field(default_factory=AnnotationsConfig)
    palettes: PalettesConfig = Field(default_factory=PalettesConfig)


class GraphsConfig(BaseModel):
    """Graphs configuration."""

    features: GraphFeaturesConfig = Field(default_factory=GraphFeaturesConfig)
    appearance: GraphAppearanceConfig = Field(default_factory=GraphAppearanceConfig)
    per_graph: PerGraphConfig = Field(default_factory=PerGraphConfig)


class CommandCooldownConfig(BaseModel):
    """Individual command cooldown configuration."""

    user_cooldown_minutes: Annotated[int, Field(ge=0, le=1440)] = Field(
        default=0,
        description="Per-user cooldown in minutes",
    )
    global_cooldown_seconds: Annotated[int, Field(ge=0, le=86400)] = Field(
        default=0,
        description="Global cooldown in seconds",
    )


class CommandsConfig(BaseModel):
    """Commands cooldown configuration."""

    config: CommandCooldownConfig = Field(default_factory=CommandCooldownConfig)
    update_graphs: CommandCooldownConfig = Field(default_factory=CommandCooldownConfig)
    my_stats: CommandCooldownConfig = Field(
        default_factory=lambda: CommandCooldownConfig(
            user_cooldown_minutes=5,
            global_cooldown_seconds=60,
        )
    )


class RateLimitingConfig(BaseModel):
    """Rate limiting configuration."""

    commands: CommandsConfig = Field(default_factory=CommandsConfig)


class TGraphBotConfig(BaseModel):
    """
    Configuration model for TGraph Bot with nested structure.

    This model defines all configuration options with validation,
    type hints, and default values using a modern nested approach.
    """

    services: ServicesConfig
    automation: AutomationConfig = Field(default_factory=AutomationConfig)
    data_collection: DataCollectionConfig = Field(default_factory=DataCollectionConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    graphs: GraphsConfig = Field(default_factory=GraphsConfig)
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)

    model_config: ClassVar[ConfigDict] = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        frozen=False,
    )
