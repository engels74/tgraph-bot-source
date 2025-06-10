# Graph Customization Guide

This guide provides comprehensive information about customizing TGraph Bot's graph appearance, behavior, and features. All customization options are configured through the `config.yml` file.

## Table of Contents

- [Feature Toggles](#feature-toggles)
- [Color Customization](#color-customization)
- [Annotation Settings](#annotation-settings)
- [Grid and Layout Options](#grid-and-layout-options)
- [Privacy Settings](#privacy-settings)
- [Troubleshooting](#troubleshooting)
- [Configuration Examples](#configuration-examples)

## Feature Toggles

Control which graph types are generated and displayed:

### Available Graph Types

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_DAILY_PLAY_COUNT` | `true` | Daily play count over time |
| `ENABLE_PLAY_COUNT_BY_DAYOFWEEK` | `true` | Play count by day of week |
| `ENABLE_PLAY_COUNT_BY_HOUROFDAY` | `true` | Play count by hour of day |
| `ENABLE_PLAY_COUNT_BY_MONTH` | `true` | Monthly play count trends |
| `ENABLE_TOP_10_PLATFORMS` | `true` | Top 10 most used platforms |
| `ENABLE_TOP_10_USERS` | `true` | Top 10 most active users |

### Example Configuration

```yaml
# Enable only specific graphs
ENABLE_DAILY_PLAY_COUNT: true
ENABLE_PLAY_COUNT_BY_DAYOFWEEK: true
ENABLE_PLAY_COUNT_BY_HOUROFDAY: false
ENABLE_PLAY_COUNT_BY_MONTH: true
ENABLE_TOP_10_PLATFORMS: false
ENABLE_TOP_10_USERS: true
```

## Color Customization

Customize the appearance of your graphs with hex color codes:

### Available Color Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TV_COLOR` | `#1f77b4` | Color for TV show data |
| `MOVIE_COLOR` | `#ff7f0e` | Color for movie data |
| `GRAPH_BACKGROUND_COLOR` | `#ffffff` | Background color for graphs |
| `ANNOTATION_COLOR` | `#ff0000` | Color for value annotations |
| `ANNOTATION_OUTLINE_COLOR` | `#000000` | Outline color for annotations |

### Color Format Requirements

- Use hex format: `#RRGGBB`
- Examples: `#ff0000` (red), `#00ff00` (green), `#0000ff` (blue)
- Named colors are also supported: `red`, `green`, `blue`, etc.

### Example Configuration

```yaml
# Custom color scheme
TV_COLOR: '#2E86AB'        # Blue for TV shows
MOVIE_COLOR: '#A23B72'     # Purple for movies
GRAPH_BACKGROUND_COLOR: '#F18F01'  # Orange background
ANNOTATION_COLOR: '#C73E1D'       # Red annotations
ANNOTATION_OUTLINE_COLOR: '#000000' # Black outlines
```

## Annotation Settings

Control value annotations displayed on graphs:

### Global Annotation Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_ANNOTATION_OUTLINE` | `true` | Enable outlines around annotations |

### Per-Graph Annotation Controls

| Setting | Default | Description |
|---------|---------|-------------|
| `ANNOTATE_DAILY_PLAY_COUNT` | `true` | Show values on daily graphs |
| `ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK` | `true` | Show values on day-of-week graphs |
| `ANNOTATE_PLAY_COUNT_BY_HOUROFDAY` | `true` | Show values on hour-of-day graphs |
| `ANNOTATE_TOP_10_PLATFORMS` | `true` | Show values on platform graphs |
| `ANNOTATE_TOP_10_USERS` | `true` | Show values on user graphs |
| `ANNOTATE_PLAY_COUNT_BY_MONTH` | `true` | Show values on monthly graphs |

### Example Configuration

```yaml
# Disable annotations on specific graphs
ANNOTATE_DAILY_PLAY_COUNT: true
ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK: false
ANNOTATE_PLAY_COUNT_BY_HOUROFDAY: true
ANNOTATE_TOP_10_PLATFORMS: false
ANNOTATE_TOP_10_USERS: true
ANNOTATE_PLAY_COUNT_BY_MONTH: true

# Customize annotation appearance
ENABLE_ANNOTATION_OUTLINE: true
ANNOTATION_COLOR: '#ff0000'
ANNOTATION_OUTLINE_COLOR: '#ffffff'
```

## Grid and Layout Options

Control the visual layout and grid appearance:

### Grid Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_GRAPH_GRID` | `false` | Show grid lines on graphs |

### Example Configuration

```yaml
# Enable grid lines for better readability
ENABLE_GRAPH_GRID: true
```

## Privacy Settings

Control how user information is displayed:

### Username Privacy

| Setting | Default | Description |
|---------|---------|-------------|
| `CENSOR_USERNAMES` | `true` | Censor usernames in graphs (e.g., "u****r") |

### Example Configuration

```yaml
# Show full usernames (less private)
CENSOR_USERNAMES: false

# Censor usernames for privacy (recommended)
CENSOR_USERNAMES: true
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Graphs Not Generating

**Problem**: No graphs are being created.

**Solutions**:
- Check that at least one `ENABLE_*` setting is `true`
- Verify Tautulli API connection is working
- Check logs for error messages

#### 2. Invalid Color Errors

**Problem**: Configuration validation fails with color errors.

**Solutions**:
- Ensure colors use hex format: `#RRGGBB`
- Use valid named colors: `red`, `green`, `blue`, etc.
- Check for typos in color values

#### 3. Annotations Not Showing

**Problem**: Value annotations are missing from graphs.

**Solutions**:
- Verify the specific `ANNOTATE_*` setting is `true`
- Check that `ANNOTATION_COLOR` is visible against background
- Ensure data contains values to annotate

#### 4. Grid Lines Not Visible

**Problem**: Grid lines don't appear even when enabled.

**Solutions**:
- Confirm `ENABLE_GRAPH_GRID` is set to `true`
- Check that grid color contrasts with background
- Verify graph type supports grid display

### Configuration Validation

The bot validates all configuration options on startup. Common validation errors:

- **Invalid color format**: Use `#RRGGBB` format or valid named colors
- **Invalid boolean values**: Use `true` or `false` (lowercase)
- **Missing required settings**: Ensure all required API keys are provided

## Configuration Examples

### Minimal Configuration

```yaml
# Basic setup with defaults
TAUTULLI_API_KEY: your_api_key_here
TAUTULLI_URL: http://localhost:8181/api/v2
DISCORD_TOKEN: your_discord_token_here
CHANNEL_ID: 123456789012345678
```

### Privacy-Focused Configuration

```yaml
# Enhanced privacy settings
CENSOR_USERNAMES: true
ENABLE_TOP_10_USERS: false  # Disable user graphs entirely
ANNOTATE_TOP_10_USERS: false
```

### High-Contrast Theme

```yaml
# Dark theme with high contrast
GRAPH_BACKGROUND_COLOR: '#2b2b2b'
TV_COLOR: '#00ff00'
MOVIE_COLOR: '#ff6600'
ANNOTATION_COLOR: '#ffffff'
ANNOTATION_OUTLINE_COLOR: '#000000'
ENABLE_GRAPH_GRID: true
```

### Performance-Optimized Configuration

```yaml
# Reduce graph generation load
ENABLE_DAILY_PLAY_COUNT: true
ENABLE_PLAY_COUNT_BY_DAYOFWEEK: false
ENABLE_PLAY_COUNT_BY_HOUROFDAY: false
ENABLE_PLAY_COUNT_BY_MONTH: true
ENABLE_TOP_10_PLATFORMS: false
ENABLE_TOP_10_USERS: true

# Disable annotations for cleaner look
ANNOTATE_DAILY_PLAY_COUNT: false
ANNOTATE_TOP_10_USERS: false
ANNOTATE_PLAY_COUNT_BY_MONTH: false
```

## Best Practices

1. **Start with defaults**: Begin with the sample configuration and modify as needed
2. **Test changes**: Use the `/config` command to test configuration changes
3. **Consider accessibility**: Choose colors with sufficient contrast
4. **Balance privacy and utility**: Consider your audience when setting privacy options
5. **Monitor performance**: Disable unused graph types to improve performance

For more information, see the [Graph Development Guide](graph_development_guide.md) for technical details about extending the graph system.
