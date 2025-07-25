"""Configuration schema for TGraph Bot using Pydantic."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import ClassVar


class TGraphBotConfig(BaseModel):
    """
    Configuration model for TGraph Bot.

    This model defines all configuration options with validation,
    type hints, and default values as specified in the PRD.
    """

    # Essential Settings
    TAUTULLI_API_KEY: str = Field(
        ...,
        description="API key for Tautulli access",
        min_length=1,
    )
    TAUTULLI_URL: str = Field(
        ...,
        description="Base URL for Tautulli API (e.g., http://localhost:8181/api/v2)",
        pattern=r"^https?://.*",
    )
    DISCORD_TOKEN: str = Field(
        ...,
        description="Discord bot token",
        min_length=1,
    )
    CHANNEL_ID: int = Field(
        ...,
        description="Discord channel ID for posting graphs",
        gt=0,
    )

    # Timing and Retention
    UPDATE_DAYS: Annotated[int, Field(ge=1, le=365)] = Field(
        default=7,
        description="Number of days between automatic updates",
    )
    FIXED_UPDATE_TIME: str = Field(
        default="XX:XX",
        description="Fixed time for updates in HH:MM format, or 'XX:XX' to disable",
        pattern=r"^(XX:XX|([01]?[0-9]|2[0-3]):[0-5][0-9])$",
    )
    KEEP_DAYS: Annotated[int, Field(ge=1, le=365)] = Field(
        default=7,
        description="Number of days to keep generated graphs",
    )
    TIME_RANGE_DAYS: Annotated[int, Field(ge=1, le=365)] = Field(
        default=30,
        description="Time range in days for graph data",
    )
    TIME_RANGE_MONTHS: Annotated[int, Field(ge=1, le=60)] = Field(
        default=12,
        description="Time range in months for monthly graph data",
    )
    LANGUAGE: str = Field(
        default="en",
        description="Language code for internationalization",
        pattern=r"^[a-z]{2}$",
    )

    # Discord Settings
    DISCORD_TIMESTAMP_FORMAT: Literal["t", "T", "d", "D", "f", "F", "R"] = Field(
        default="R",
        description="Discord timestamp format (t=short time, T=long time, d=short date, D=long date, f=short date/time, F=long date/time, R=relative time)",
    )

    # Graph Options
    CENSOR_USERNAMES: bool = Field(
        default=True,
        description="Whether to censor usernames in graphs",
    )
    GRAPH_WIDTH: Annotated[int, Field(ge=6, le=20)] = Field(
        default=12,
        description="Width of graphs in inches",
    )
    GRAPH_HEIGHT: Annotated[int, Field(ge=4, le=16)] = Field(
        default=8,
        description="Height of graphs in inches",
    )
    GRAPH_DPI: Annotated[int, Field(ge=72, le=300)] = Field(
        default=100,
        description="DPI (dots per inch) for graph image quality",
    )
    ENABLE_GRAPH_GRID: bool = Field(
        default=False,
        description="Whether to enable grid lines in graphs",
    )
    ENABLE_MEDIA_TYPE_SEPARATION: bool = Field(
        default=True,
        description="Whether to separate Movies and TV Series in graphs",
    )
    ENABLE_STACKED_BAR_CHARTS: bool = Field(
        default=True,
        description="Whether to use stacked bars when media type separation is enabled (applies to bar charts only)",
    )
    ENABLE_DAILY_PLAY_COUNT: bool = Field(
        default=True,
        description="Enable daily play count graph generation",
    )
    ENABLE_PLAY_COUNT_BY_DAYOFWEEK: bool = Field(
        default=True,
        description="Enable play count by day of week graph generation",
    )
    ENABLE_PLAY_COUNT_BY_HOUROFDAY: bool = Field(
        default=True,
        description="Enable play count by hour of day graph generation",
    )
    ENABLE_TOP_10_PLATFORMS: bool = Field(
        default=True,
        description="Enable top 10 platforms graph generation",
    )
    ENABLE_TOP_10_USERS: bool = Field(
        default=True,
        description="Enable top 10 users graph generation",
    )
    ENABLE_PLAY_COUNT_BY_MONTH: bool = Field(
        default=True,
        description="Enable play count by month graph generation",
    )

    # Graph Colors
    TV_COLOR: str = Field(
        default="#1f77b4",
        description="Color for TV shows in graphs",
    )
    MOVIE_COLOR: str = Field(
        default="#ff7f0e",
        description="Color for movies in graphs",
    )
    GRAPH_BACKGROUND_COLOR: str = Field(
        default="#ffffff",
        description="Background color for graphs",
    )
    ANNOTATION_COLOR: str = Field(
        default="#ff0000",
        description="Color for graph annotations",
    )
    ANNOTATION_OUTLINE_COLOR: str = Field(
        default="#000000",
        description="Outline color for graph annotations",
    )
    ENABLE_ANNOTATION_OUTLINE: bool = Field(
        default=True,
        description="Whether to enable annotation outlines",
    )
    ANNOTATION_FONT_SIZE: Annotated[int, Field(ge=6, le=24)] = Field(
        default=10,
        description="Font size for bar value annotations",
    )

    # Annotation Options
    ANNOTATE_DAILY_PLAY_COUNT: bool = Field(
        default=True,
        description="Enable annotations on daily play count graphs",
    )
    ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK: bool = Field(
        default=True,
        description="Enable annotations on day of week graphs",
    )
    ANNOTATE_PLAY_COUNT_BY_HOUROFDAY: bool = Field(
        default=True,
        description="Enable annotations on hour of day graphs",
    )
    ANNOTATE_TOP_10_PLATFORMS: bool = Field(
        default=True,
        description="Enable annotations on top platforms graphs",
    )
    ANNOTATE_TOP_10_USERS: bool = Field(
        default=True,
        description="Enable annotations on top users graphs",
    )
    ANNOTATE_PLAY_COUNT_BY_MONTH: bool = Field(
        default=True,
        description="Enable annotations on monthly graphs",
    )

    # Peak Annotation Options (separate from bar value annotations)
    ENABLE_PEAK_ANNOTATIONS: bool = Field(
        default=True,
        description="Whether to enable peak value annotations on graphs",
    )
    PEAK_ANNOTATION_COLOR: str = Field(
        default="#ffcc00",
        description="Background color for peak annotation boxes",
    )
    PEAK_ANNOTATION_TEXT_COLOR: str = Field(
        default="#000000",
        description="Text color for peak annotations",
    )

    # Command Cooldown Options
    CONFIG_COOLDOWN_MINUTES: Annotated[int, Field(ge=0, le=1440)] = Field(
        default=0,
        description="Per-user cooldown for config commands in minutes",
    )
    CONFIG_GLOBAL_COOLDOWN_SECONDS: Annotated[int, Field(ge=0, le=86400)] = Field(
        default=0,
        description="Global cooldown for config commands in seconds",
    )
    UPDATE_GRAPHS_COOLDOWN_MINUTES: Annotated[int, Field(ge=0, le=1440)] = Field(
        default=0,
        description="Per-user cooldown for update graphs commands in minutes",
    )
    UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS: Annotated[int, Field(ge=0, le=86400)] = (
        Field(
            default=0,
            description="Global cooldown for update graphs commands in seconds",
        )
    )
    MY_STATS_COOLDOWN_MINUTES: Annotated[int, Field(ge=0, le=1440)] = Field(
        default=5,
        description="Per-user cooldown for my stats commands in minutes",
    )
    MY_STATS_GLOBAL_COOLDOWN_SECONDS: Annotated[int, Field(ge=0, le=86400)] = Field(
        default=60,
        description="Global cooldown for my stats commands in seconds",
    )

    @field_validator(
        "TV_COLOR",
        "MOVIE_COLOR",
        "GRAPH_BACKGROUND_COLOR",
        "ANNOTATION_COLOR",
        "ANNOTATION_OUTLINE_COLOR",
    )
    @classmethod
    def validate_color_format(cls, v: str) -> str:
        """Validate that color values are in valid hex format."""
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError(f"Color must be in hex format (e.g., #1f77b4), got: {v}")
        return v.lower()

    @field_validator("DISCORD_TIMESTAMP_FORMAT")
    @classmethod
    def validate_discord_timestamp_format(cls, v: str) -> str:
        """Validate Discord timestamp format."""
        valid_formats = {"t", "T", "d", "D", "f", "F", "R"}
        if v not in valid_formats:
            raise ValueError(f"DISCORD_TIMESTAMP_FORMAT must be one of {sorted(valid_formats)}, got: {v}")
        return v

    @field_validator("TAUTULLI_URL")
    @classmethod
    def validate_tautulli_url(cls, v: str) -> str:
        """Validate and normalize Tautulli URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("TAUTULLI_URL must start with http:// or https://")

        # Remove trailing slash if present
        return v.rstrip("/")

    @field_validator("DISCORD_TOKEN")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        """Validate Discord token format."""
        # Allow shorter tokens for testing, but real Discord tokens are typically 70+ chars
        if len(v) < 10:  # Minimum reasonable length for testing
            raise ValueError("DISCORD_TOKEN appears to be too short")
        return v

    model_config: ClassVar[ConfigDict] = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        frozen=False,  # Allow modification for live config updates
    )
