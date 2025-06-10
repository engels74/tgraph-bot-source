# Graph Troubleshooting Guide

This guide provides detailed troubleshooting steps for common issues with TGraph Bot's graph generation and customization features.

## Table of Contents

- [Configuration Issues](#configuration-issues)
- [Graph Generation Problems](#graph-generation-problems)
- [Customization Not Working](#customization-not-working)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)
- [Discord Integration Problems](#discord-integration-problems)
- [Debugging Tools](#debugging-tools)

## Configuration Issues

### Invalid Configuration Values

**Symptoms:**
- Bot fails to start
- Configuration validation errors
- Unexpected default values being used

**Common Causes and Solutions:**

1. **Invalid Color Formats**
   ```yaml
   # ❌ Wrong
   TV_COLOR: red123
   MOVIE_COLOR: #gggggg
   
   # ✅ Correct
   TV_COLOR: '#ff0000'
   MOVIE_COLOR: '#00ff00'
   ```

2. **Incorrect Boolean Values**
   ```yaml
   # ❌ Wrong
   ENABLE_GRAPH_GRID: yes
   CENSOR_USERNAMES: 1
   
   # ✅ Correct
   ENABLE_GRAPH_GRID: true
   CENSOR_USERNAMES: false
   ```

3. **Invalid Numeric Ranges**
   ```yaml
   # ❌ Wrong
   UPDATE_DAYS: 0      # Must be 1-365
   KEEP_DAYS: 400      # Must be 1-365
   
   # ✅ Correct
   UPDATE_DAYS: 7
   KEEP_DAYS: 14
   ```

### Configuration Not Loading

**Symptoms:**
- All settings use default values
- Changes to config.yml have no effect

**Solutions:**
1. Verify config.yml is in the correct location (project root)
2. Check file permissions (must be readable)
3. Validate YAML syntax using an online YAML validator
4. Restart the bot after making changes

## Graph Generation Problems

### No Graphs Generated

**Symptoms:**
- Bot runs but no graph files are created
- Empty graph directory

**Diagnostic Steps:**
1. Check if any graph types are enabled:
   ```yaml
   ENABLE_DAILY_PLAY_COUNT: true
   ENABLE_TOP_10_USERS: true
   # At least one must be true
   ```

2. Verify Tautulli connection:
   - Test API key and URL
   - Check Tautulli is running and accessible
   - Verify network connectivity

3. Check logs for error messages:
   ```bash
   # Look for graph generation errors
   grep -i "graph" bot.log
   grep -i "error" bot.log
   ```

### Empty or Incomplete Graphs

**Symptoms:**
- Graphs are generated but show no data
- Graphs show "No data available" message

**Solutions:**
1. **Insufficient Data Range**
   ```yaml
   # Increase time range if no recent activity
   TIME_RANGE_DAYS: 30  # Try 60 or 90
   ```

2. **Tautulli Data Issues**
   - Verify Tautulli is collecting data
   - Check Tautulli's activity history
   - Ensure users have recent activity

3. **Filter Issues**
   - Check if data filters are too restrictive
   - Verify user permissions in Tautulli

### Graph Generation Errors

**Symptoms:**
- Error messages in logs
- Partial graph generation
- Bot crashes during graph creation

**Common Error Patterns:**

1. **Memory Issues**
   ```
   Error: MemoryError during graph generation
   ```
   - Reduce TIME_RANGE_DAYS
   - Disable unused graph types
   - Increase system memory

2. **Permission Errors**
   ```
   Error: Permission denied writing to graphs/
   ```
   - Check directory permissions
   - Ensure bot has write access
   - Verify disk space

3. **Data Processing Errors**
   ```
   Error: Invalid data format from Tautulli
   ```
   - Update Tautulli to latest version
   - Check API response format
   - Verify API key permissions

## Customization Not Working

### Colors Not Applied

**Symptoms:**
- Graphs use default colors despite configuration
- Color changes not visible

**Solutions:**
1. **Verify Color Format**
   ```yaml
   # Use quotes for hex colors
   TV_COLOR: '#ff0000'
   MOVIE_COLOR: '#00ff00'
   ```

2. **Check Color Contrast**
   - Ensure colors are visible against background
   - Test with different background colors

3. **Clear Graph Cache**
   ```bash
   # Remove old graphs to force regeneration
   rm -rf graphs/output/*
   ```

### Annotations Missing

**Symptoms:**
- Value labels not showing on graphs
- Annotation settings ignored

**Diagnostic Steps:**
1. **Check Annotation Settings**
   ```yaml
   # Enable annotations for specific graphs
   ANNOTATE_DAILY_PLAY_COUNT: true
   ANNOTATE_TOP_10_USERS: true
   
   # Enable annotation outlines for visibility
   ENABLE_ANNOTATION_OUTLINE: true
   ```

2. **Verify Color Visibility**
   ```yaml
   # Ensure annotation colors contrast with background
   ANNOTATION_COLOR: '#000000'
   ANNOTATION_OUTLINE_COLOR: '#ffffff'
   GRAPH_BACKGROUND_COLOR: '#f0f0f0'
   ```

### Grid Lines Not Visible

**Symptoms:**
- Grid setting enabled but no grid lines appear

**Solutions:**
1. **Enable Grid Setting**
   ```yaml
   ENABLE_GRAPH_GRID: true
   ```

2. **Check Graph Type Support**
   - Not all graph types may support grids
   - Verify with sample graphs

## Performance Issues

### Slow Graph Generation

**Symptoms:**
- Long delays before graphs appear
- Bot appears unresponsive during generation

**Optimization Steps:**
1. **Reduce Data Range**
   ```yaml
   TIME_RANGE_DAYS: 7  # Reduce from 30
   ```

2. **Disable Unused Graphs**
   ```yaml
   ENABLE_PLAY_COUNT_BY_HOUROFDAY: false
   ENABLE_PLAY_COUNT_BY_MONTH: false
   ```

3. **Optimize Annotations**
   ```yaml
   # Disable annotations for faster generation
   ANNOTATE_DAILY_PLAY_COUNT: false
   ANNOTATE_TOP_10_USERS: false
   ```

### High Memory Usage

**Symptoms:**
- System memory consumption increases
- Out of memory errors

**Solutions:**
1. **Enable Resource Cleanup**
   - Verify automatic cleanup is working
   - Monitor memory usage over time

2. **Reduce Concurrent Operations**
   - Generate graphs sequentially
   - Limit simultaneous graph types

## Data Issues

### Inconsistent Data

**Symptoms:**
- Graph data doesn't match Tautulli dashboard
- Missing recent activity

**Solutions:**
1. **Check Tautulli Sync**
   - Verify Tautulli is up to date
   - Check for sync delays

2. **Validate Time Zones**
   - Ensure consistent time zone settings
   - Check for daylight saving time issues

### User Privacy Concerns

**Symptoms:**
- Usernames visible when they should be censored
- Privacy settings not working

**Solutions:**
1. **Enable Username Censoring**
   ```yaml
   CENSOR_USERNAMES: true
   ```

2. **Disable User Graphs**
   ```yaml
   ENABLE_TOP_10_USERS: false
   ```

## Discord Integration Problems

### Graphs Not Posted

**Symptoms:**
- Graphs generated but not sent to Discord
- Discord bot appears offline

**Solutions:**
1. **Verify Discord Configuration**
   ```yaml
   DISCORD_TOKEN: 'your_valid_token_here'
   CHANNEL_ID: 123456789012345678
   ```

2. **Check Bot Permissions**
   - Verify bot has send message permissions
   - Ensure bot can attach files
   - Check channel access permissions

### Image Upload Failures

**Symptoms:**
- Error messages about file uploads
- Graphs generated but upload fails

**Solutions:**
1. **Check File Size Limits**
   - Discord has 8MB file size limit
   - Reduce graph resolution if needed

2. **Verify File Permissions**
   - Ensure graph files are readable
   - Check file system permissions

## Debugging Tools

### Enable Debug Logging

Add to your configuration:
```yaml
# Enable detailed logging
LOG_LEVEL: DEBUG
```

### Test Individual Components

1. **Test Configuration Loading**
   ```bash
   python -c "from config.manager import ConfigManager; print(ConfigManager.load_config('config.yml'))"
   ```

2. **Test Graph Generation**
   ```bash
   python -c "from graphs.graph_factory import GraphFactory; factory = GraphFactory({}); print(factory.get_enabled_graph_types())"
   ```

3. **Test Tautulli Connection**
   ```bash
   curl -X GET "http://localhost:8181/api/v2?apikey=YOUR_API_KEY&cmd=get_activity"
   ```

### Common Log Patterns

Look for these patterns in logs:

- `ERROR`: Critical issues requiring immediate attention
- `WARNING`: Potential problems that may affect functionality
- `INFO`: Normal operation messages
- `DEBUG`: Detailed execution information

### Getting Help

If issues persist:

1. Check the [GitHub Issues](https://github.com/your-repo/issues)
2. Review recent changes in the changelog
3. Verify you're using the latest version
4. Provide detailed error logs when reporting issues

## Prevention Tips

1. **Regular Backups**
   - Backup working configurations
   - Document custom settings

2. **Gradual Changes**
   - Test one setting at a time
   - Keep notes of what works

3. **Monitor Resources**
   - Watch memory and disk usage
   - Set up log rotation

4. **Stay Updated**
   - Keep dependencies current
   - Review release notes for breaking changes
