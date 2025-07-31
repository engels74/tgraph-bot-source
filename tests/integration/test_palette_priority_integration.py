"""
Comprehensive integration tests for the palette priority system.

This module tests the end-to-end functionality of the palette priority system
that resolves conflicts between custom palette configurations and media type separation.
The priority system ensures:
1. Highest Priority: Non-empty *_PALETTE configurations override everything
2. Medium Priority: ENABLE_MEDIA_TYPE_SEPARATION with MOVIE_COLOR/TV_COLOR
3. Lowest Priority: Default system colors
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.tgraph_bot.graphs.graph_modules.core.graph_type_registry import (
    GraphTypeRegistry,
)
from src.tgraph_bot.graphs.graph_modules.core.palette_resolver import (
    ColorStrategy,
)
from tests.utils.graph_helpers import (
    create_graph_factory_with_config,
    matplotlib_cleanup,
)
from tests.utils.test_helpers import create_test_config_custom

if TYPE_CHECKING:
    pass


class TestPalettePriorityIntegration:
    """Integration tests for the palette priority system across all graph types."""

    def test_palette_overrides_media_type_separation_all_graphs(self) -> None:
        """Test that custom palettes override media type separation across all graph types."""
        with matplotlib_cleanup():
            # Create config with both palette and media type separation enabled
            config = create_test_config_custom(
                services_overrides={
                    "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                    "discord": {"token": "test_token", "channel_id": 123456789}
                },
                graphs_overrides={
                    "features": {"media_type_separation": True},
                    "appearance": {
                        "colors": {"tv": "#ff0000", "movie": "#00ff00"},
                        "palettes": {
                            "daily_play_count": "viridis",
                            "play_count_by_dayofweek": "plasma",
                            "play_count_by_hourofday": "inferno",
                            "play_count_by_month": "magma",
                            "top_10_platforms": "cividis",
                            "top_10_users": "turbo"
                        }
                    }
                }
            )

            factory = create_graph_factory_with_config(config)
            registry = GraphTypeRegistry()
            graph_types = registry.get_all_type_names()
            
            # Filter to only graphs that have palette configurations
            # Import the PaletteResolver to check which graphs have palette mappings
            from src.tgraph_bot.graphs.graph_modules.core.palette_resolver import PaletteResolver
            resolver = PaletteResolver()
            
            # Map registry names to class names for palette resolver lookup
            registry_to_class_name = {
                "daily_play_count": "DailyPlayCountGraph",
                "play_count_by_dayofweek": "PlayCountByDayOfWeekGraph", 
                "play_count_by_hourofday": "PlayCountByHourOfDayGraph",
                "play_count_by_month": "PlayCountByMonthGraph",
                "top_10_platforms": "Top10PlatformsGraph",
                "top_10_users": "Top10UsersGraph",
            }

            for graph_type in graph_types:
                # Only test graphs that have palette configurations
                class_name = registry_to_class_name.get(graph_type)
                if class_name is None or class_name not in resolver.GRAPH_TYPE_TO_PALETTE_KEY:
                    continue
                    
                graph = factory.create_graph_by_type(graph_type)
                
                # Get the resolved color strategy
                resolution = graph.get_resolved_color_strategy()
                
                # Verify that palette strategy takes precedence
                assert resolution.strategy == ColorStrategy.PALETTE, (
                    f"Graph {graph_type} should use PALETTE strategy, got {resolution.strategy}"
                )
                assert resolution.use_palette is True, (
                    f"Graph {graph_type} should use palette, got use_palette={resolution.use_palette}"
                )
                assert resolution.palette_name is not None, (
                    f"Graph {graph_type} should have a palette name"
                )
                assert resolution.palette_colors is not None, (
                    f"Graph {graph_type} should have palette colors"
                )
                
                # Verify that media type colors are available as fallback
                assert resolution.fallback_colors is not None, (
                    f"Graph {graph_type} should have fallback colors"
                )
                
                graph.cleanup()

    def test_media_type_separation_when_no_palette_configured(self) -> None:
        """Test that media type separation works when no custom palettes are configured."""
        with matplotlib_cleanup():
            # Create config with only media type separation enabled
            config = create_test_config_custom(
                services_overrides={
                    "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                    "discord": {"token": "test_token", "channel_id": 123456789}
                },
                graphs_overrides={
                    "features": {"media_type_separation": True},
                    "appearance": {"colors": {"tv": "#ff0000", "movie": "#00ff00"}}
                }
            )

            factory = create_graph_factory_with_config(config)
            registry = GraphTypeRegistry()
            graph_types = registry.get_all_type_names()

            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)
                
                # Get the resolved color strategy
                resolution = graph.get_resolved_color_strategy()
                
                # Verify that separation strategy is used
                assert resolution.strategy == ColorStrategy.SEPARATION, (
                    f"Graph {graph_type} should use SEPARATION strategy, got {resolution.strategy}"
                )
                assert resolution.use_palette is False, (
                    f"Graph {graph_type} should not use palette, got use_palette={resolution.use_palette}"
                )
                assert resolution.media_type_colors is not None, (
                    f"Graph {graph_type} should have media type colors"
                )
                
                # Verify the correct media colors
                assert resolution.media_type_colors["tv"] == "#ff0000", (
                    f"Graph {graph_type} should have correct TV color"
                )
                assert resolution.media_type_colors["movie"] == "#00ff00", (
                    f"Graph {graph_type} should have correct movie color"
                )
                
                graph.cleanup()

    def test_default_colors_when_nothing_configured(self) -> None:
        """Test that default colors are used when no palettes or separation are configured."""
        with matplotlib_cleanup():
            # Create minimal config with no color customizations
            config = create_test_config_custom(
                services_overrides={
                    "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                    "discord": {"token": "test_token", "channel_id": 123456789}
                }
            )

            factory = create_graph_factory_with_config(config)
            registry = GraphTypeRegistry()
            graph_types = registry.get_all_type_names()

            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)
                
                # Get the resolved color strategy
                resolution = graph.get_resolved_color_strategy()
                
                # Since ENABLE_MEDIA_TYPE_SEPARATION defaults to True, should use separation
                # But with default colors
                assert resolution.strategy == ColorStrategy.SEPARATION, (
                    f"Graph {graph_type} should use SEPARATION strategy (default), got {resolution.strategy}"
                )
                assert resolution.use_palette is False, (
                    f"Graph {graph_type} should not use palette, got use_palette={resolution.use_palette}"
                )
                assert resolution.media_type_colors is not None, (
                    f"Graph {graph_type} should have media type colors"
                )
                
                graph.cleanup()

    def test_empty_palette_falls_back_to_separation(self) -> None:
        """Test that empty/invalid palettes fall back to media type separation."""
        with matplotlib_cleanup():
            # Create config with empty palettes and media type separation
            config = create_test_config_custom(
                services_overrides={
                    "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                    "discord": {"token": "test_token", "channel_id": 123456789}
                },
                graphs_overrides={
                    "features": {"media_type_separation": True},
                    "appearance": {
                        "colors": {"tv": "#ff0000", "movie": "#00ff00"},
                        "palettes": {
                            "daily_play_count": "",
                            "play_count_by_dayofweek": "   ",
                            "play_count_by_hourofday": "invalid_palette_name"
                        }
                    }
                }
            )

            factory = create_graph_factory_with_config(config)
            
            # Test empty palette
            graph = factory.create_graph_by_type("daily_play_count")
            resolution = graph.get_resolved_color_strategy()
            assert resolution.strategy == ColorStrategy.SEPARATION
            graph.cleanup()
            
            # Test whitespace-only palette
            graph = factory.create_graph_by_type("play_count_by_dayofweek")
            resolution = graph.get_resolved_color_strategy()
            assert resolution.strategy == ColorStrategy.SEPARATION
            graph.cleanup()
            
            # Test invalid palette name
            graph = factory.create_graph_by_type("play_count_by_hourofday")
            resolution = graph.get_resolved_color_strategy()
            assert resolution.strategy == ColorStrategy.SEPARATION
            graph.cleanup()

    def test_palette_validation_consistency(self) -> None:
        """Test that palette validation is consistent across all graph types."""
        with matplotlib_cleanup():
            # Test with various palette names
            valid_palettes = ["viridis", "plasma", "inferno", "magma", "Set1", "tab10"]
            invalid_palettes = ["", "   ", "not_a_palette", "123invalid"]
            
            for palette in valid_palettes:
                config = create_test_config_custom(
                    services_overrides={
                        "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                        "discord": {"token": "test_token", "channel_id": 123456789}
                    },
                    graphs_overrides={
                        "appearance": {"palettes": {"daily_play_count": palette}}
                    }
                )
                
                factory = create_graph_factory_with_config(config)
                graph = factory.create_graph_by_type("daily_play_count")
                resolution = graph.get_resolved_color_strategy()
                
                assert resolution.strategy == ColorStrategy.PALETTE, (
                    f"Valid palette '{palette}' should use PALETTE strategy"
                )
                assert resolution.palette_name == palette, (
                    f"Palette name should be '{palette}'"
                )
                
                graph.cleanup()
            
            for palette in invalid_palettes:
                config = create_test_config_custom(
                    services_overrides={
                        "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                        "discord": {"token": "test_token", "channel_id": 123456789}
                    },
                    graphs_overrides={
                        "features": {"media_type_separation": True},
                        "appearance": {"palettes": {"daily_play_count": palette}}
                    }
                )
                
                factory = create_graph_factory_with_config(config)
                graph = factory.create_graph_by_type("daily_play_count")
                resolution = graph.get_resolved_color_strategy()
                
                assert resolution.strategy == ColorStrategy.SEPARATION, (
                    f"Invalid palette '{palette}' should fall back to SEPARATION strategy"
                )
                
                graph.cleanup()

    def test_backward_compatibility_with_existing_configs(self) -> None:
        """Test that existing configurations without palettes continue to work."""
        with matplotlib_cleanup():
            # Simulate old configuration style (before palette priority system)
            old_style_config = create_test_config_custom(
                services_overrides={
                    "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                    "discord": {"token": "test_token", "channel_id": 123456789}
                },
                graphs_overrides={
                    "features": {"media_type_separation": True},
                    "appearance": {"colors": {"tv": "#1f77b4", "movie": "#ff7f0e"}}
                }
            )
            
            factory = create_graph_factory_with_config(old_style_config)
            registry = GraphTypeRegistry()
            graph_types = registry.get_all_type_names()
            
            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)
                
                # Should work exactly as before - using media type separation
                resolution = graph.get_resolved_color_strategy()
                assert resolution.strategy == ColorStrategy.SEPARATION
                assert resolution.use_palette is False
                assert resolution.media_type_colors is not None
                assert resolution.media_type_colors["tv"] == "#1f77b4"
                assert resolution.media_type_colors["movie"] == "#ff7f0e"
                
                graph.cleanup()

    def test_visual_color_consistency_across_strategies(self) -> None:
        """Test that color resolution provides consistent visual output."""
        with matplotlib_cleanup():
            # Test that the same graph type produces consistent colors
            # across different configurations
            
            configs = {
                "palette": create_test_config_custom(
                    services_overrides={
                        "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                        "discord": {"token": "test_token", "channel_id": 123456789}
                    },
                    graphs_overrides={
                        "appearance": {"palettes": {"daily_play_count": "Set1"}}
                    }
                ),
                "separation": create_test_config_custom(
                    services_overrides={
                        "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                        "discord": {"token": "test_token", "channel_id": 123456789}
                    },
                    graphs_overrides={
                        "features": {"media_type_separation": True},
                        "appearance": {"colors": {"tv": "#ff0000", "movie": "#00ff00"}}
                    }
                ),
                "default": create_test_config_custom(
                    services_overrides={
                        "tautulli": {"api_key": "test_key", "url": "http://test.local"},
                        "discord": {"token": "test_token", "channel_id": 123456789}
                    },
                    graphs_overrides={
                        "features": {"media_type_separation": False}
                    }
                ),
            }
            
            for config_type, config in configs.items():
                factory = create_graph_factory_with_config(config)
                graph = factory.create_graph_by_type("daily_play_count")
                
                effective_colors = graph.palette_resolver.get_effective_colors("DailyPlayCountGraph")
                
                # Verify that effective colors are always non-empty
                assert len(effective_colors) > 0, (
                    f"Config type '{config_type}' should provide effective colors"
                )
                
                # Verify that all colors are valid hex colors
                for color in effective_colors:
                    assert isinstance(color, str), (
                        f"Color should be string, got {type(color)}"
                    )
                    assert color.startswith("#"), (
                        f"Color '{color}' should be hex format"
                    )
                    assert len(color) == 7, (
                        f"Color '{color}' should be 7 characters long"
                    )
                
                graph.cleanup()