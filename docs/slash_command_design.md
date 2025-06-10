# Slash Command Interface Design

This document defines the design specifications for TGraph Bot's Discord slash commands, specifically `/update_graphs` and `/my_stats`.

## Command Overview

### `/update_graphs` Command

**Purpose**: Manually trigger server-wide graph generation and posting  
**Target Users**: Server administrators  
**Execution Context**: Public channels (results posted to configured channel)

#### Command Specification
- **Name**: `update_graphs`
- **Description**: "Manually trigger server-wide graph generation and posting"
- **Parameters**: None (simple trigger command)
- **Permissions**: Requires `manage_guild` permission (admin only)
- **Cooldowns**: 
  - Per-user: Configurable via `UPDATE_GRAPHS_COOLDOWN_MINUTES` (default: 0)
  - Global: Configurable via `UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS` (default: 0)

#### User Interaction Flow
1. **Command Invocation**: Admin uses `/update_graphs` in any channel
2. **Immediate Acknowledgment**: Ephemeral message with progress information
3. **Progress Updates**: Real-time progress feedback during generation
4. **Graph Generation**: Non-blocking generation using GraphManager
5. **Channel Posting**: Automatic posting to configured Discord channel
6. **Completion Feedback**: Success/failure notification to admin

#### Technical Implementation
- Uses `GraphManager` with async context manager pattern
- Implements `asyncio.to_thread()` for CPU-bound graph generation
- Progress tracking with user-friendly progress bars
- Comprehensive error handling with detailed feedback
- File validation and Discord upload management
- Configurable timeout protection (default: 300 seconds)

#### Error Handling
- **Configuration Errors**: Invalid channel ID, missing permissions
- **Generation Errors**: Data fetch failures, graph creation issues
- **Upload Errors**: File access problems, Discord API failures
- **Timeout Errors**: Generation exceeds configured timeout
- **User Feedback**: Detailed error messages with troubleshooting steps

### `/my_stats` Command

**Purpose**: Generate and deliver personal Plex statistics via DM  
**Target Users**: All server members  
**Execution Context**: Any channel (results sent privately)

#### Command Specification
- **Name**: `my_stats`
- **Description**: "Get your personal Plex statistics via DM"
- **Parameters**: 
  - `email` (required): User's Plex account email address
- **Permissions**: Available to all users (no restrictions)
- **Cooldowns**:
  - Per-user: Configurable via `MY_STATS_COOLDOWN_MINUTES` (default: 5)
  - Global: Configurable via `MY_STATS_GLOBAL_COOLDOWN_SECONDS` (default: 60)

#### User Interaction Flow
1. **Command Invocation**: User provides `/my_stats email:user@example.com`
2. **Email Validation**: Basic format validation before processing
3. **Immediate Acknowledgment**: Ephemeral message with request details
4. **Graph Generation**: Non-blocking generation using UserGraphManager
5. **DM Delivery**: Private delivery of personal graph images
6. **Completion Feedback**: Success/failure notification in original channel

#### Technical Implementation
- Uses `UserGraphManager` with async context manager pattern
- Email-based user identification for Plex statistics
- Implements `asyncio.to_thread()` for CPU-bound operations
- Private DM delivery with file attachment handling
- Comprehensive error handling for user-friendly experience
- Configurable timeout protection (default: 180 seconds)

#### Privacy & Security
- **Email Handling**: Secure email mapping for user identification
- **Data Privacy**: Personal statistics delivered only via private DM
- **Input Validation**: Email format validation and sanitization
- **Error Messages**: Generic error messages to protect user privacy

## Common Design Patterns

### Error Handling Strategy
- **Immediate Validation**: Input validation before processing
- **Graceful Degradation**: Partial success handling where applicable
- **User-Friendly Messages**: Clear, actionable error descriptions
- **Logging**: Comprehensive logging for debugging and monitoring
- **Recovery Guidance**: Specific troubleshooting steps for users

### Progress Feedback
- **Real-Time Updates**: Live progress updates during generation
- **Visual Indicators**: Progress bars and percentage completion
- **Time Estimates**: Elapsed time and estimated completion
- **Status Messages**: Clear descriptions of current operations

### Performance Considerations
- **Non-Blocking Execution**: All CPU-bound operations use `asyncio.to_thread()`
- **Timeout Protection**: Configurable timeouts prevent hanging operations
- **Resource Management**: Proper cleanup and resource disposal
- **Concurrent Handling**: Multiple users can request operations simultaneously

### Configuration Integration
- **Cooldown Management**: Respects configured rate limiting
- **Channel Configuration**: Uses configured Discord channel for posting
- **Feature Toggles**: Respects graph type enable/disable settings
- **Timeout Settings**: Configurable operation timeouts

## Implementation Status

### Completed Features
- ✅ Command structure and permission decorators
- ✅ Basic error handling and user feedback
- ✅ Integration with GraphManager and UserGraphManager
- ✅ Progress tracking and real-time updates
- ✅ File upload and Discord integration
- ✅ Comprehensive documentation and type annotations

### Pending Implementation
- ⏳ Cooldown decorator integration
- ⏳ Advanced rate limiting features
- ⏳ Enhanced progress tracking UI
- ⏳ Performance optimization
- ⏳ Comprehensive testing suite

## Testing Strategy

### Unit Testing
- Command parameter validation
- Error handling scenarios
- Progress callback functionality
- File upload mechanisms

### Integration Testing
- GraphManager integration
- UserGraphManager integration
- Discord API interactions
- Configuration management

### User Experience Testing
- Command discoverability
- Error message clarity
- Progress feedback effectiveness
- Performance under load

## Future Enhancements

### Planned Features
- **Advanced Progress UI**: Enhanced progress visualization
- **Batch Operations**: Multiple user statistics in single request
- **Scheduling Integration**: Integration with automated scheduling system
- **Analytics**: Usage statistics and performance metrics

### Potential Improvements
- **Caching**: Graph result caching for improved performance
- **Compression**: Image compression for faster uploads
- **Formats**: Multiple output formats (PNG, SVG, PDF)
- **Customization**: User-configurable graph options
