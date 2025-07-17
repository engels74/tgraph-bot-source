"""
Tests for Discord file upload utilities in TGraph Bot.

This module tests file validation, Discord file creation, and upload functionality
for both channel and DM uploads with comprehensive error handling scenarios.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open, Mock

import discord
import pytest

from src.tgraph_bot.bot.update_tracker import get_local_timezone
from src.tgraph_bot.utils.discord.discord_file_utils import (
    DISCORD_FILE_SIZE_LIMIT_NITRO,
    DISCORD_FILE_SIZE_LIMIT_REGULAR,
    SUPPORTED_IMAGE_FORMATS,
    TimestampStyle,
    calculate_next_update_time,
    create_discord_file_safe,
    create_graph_specific_embed,
    ensure_timezone_aware,
    format_file_size,
    format_next_update_timestamp,
    upload_files_to_channel,
    upload_files_to_user_dm,
    validate_file_for_discord,
)


class TestFileValidation:
    """Test cases for file validation functionality."""

    def test_validate_nonexistent_file(self) -> None:
        """Test validation of non-existent file."""
        result = validate_file_for_discord("/nonexistent/file.png")

        assert result.valid is False
        assert result.error_message is not None
        assert "does not exist" in result.error_message
        assert result.file_size is None

    def test_validate_directory_as_file(self, tmp_path: Path) -> None:
        """Test validation when path points to directory."""
        directory = tmp_path / "test_dir"
        directory.mkdir()

        result = validate_file_for_discord(directory)

        assert result.valid is False
        assert result.error_message is not None
        assert "not a file" in result.error_message

    def test_validate_empty_file(self, tmp_path: Path) -> None:
        """Test validation of empty file."""
        empty_file = tmp_path / "empty.png"
        empty_file.touch()

        result = validate_file_for_discord(empty_file)

        assert result.valid is False
        assert result.error_message is not None
        assert "empty" in result.error_message
        assert result.file_size == 0

    def test_validate_oversized_file_regular_limits(self, tmp_path: Path) -> None:
        """Test validation of file exceeding regular Discord limits."""
        large_file = tmp_path / "large.png"
        # Create file larger than 8MB
        _ = large_file.write_bytes(b"x" * (DISCORD_FILE_SIZE_LIMIT_REGULAR + 1))

        result = validate_file_for_discord(large_file, use_nitro_limits=False)

        assert result.valid is False
        assert result.error_message is not None
        assert "too large" in result.error_message
        assert "8MB" in result.error_message
        assert result.file_size == DISCORD_FILE_SIZE_LIMIT_REGULAR + 1

    def test_validate_oversized_file_nitro_limits(self, tmp_path: Path) -> None:
        """Test validation of file exceeding Nitro Discord limits."""
        large_file = tmp_path / "large.png"
        # Create file larger than 25MB
        _ = large_file.write_bytes(b"x" * (DISCORD_FILE_SIZE_LIMIT_NITRO + 1))

        result = validate_file_for_discord(large_file, use_nitro_limits=True)

        assert result.valid is False
        assert result.error_message is not None
        assert "too large" in result.error_message
        assert "25MB" in result.error_message

    def test_validate_unsupported_format(self, tmp_path: Path) -> None:
        """Test validation of unsupported file format."""
        txt_file = tmp_path / "test.txt"
        _ = txt_file.write_text("test content")

        result = validate_file_for_discord(txt_file)

        assert result.valid is False
        assert result.error_message is not None
        assert "Unsupported file format" in result.error_message
        assert ".txt" in result.error_message

    def test_validate_valid_png_file(self, tmp_path: Path) -> None:
        """Test validation of valid PNG file."""
        png_file = tmp_path / "test.png"
        # Create a small PNG file (1KB)
        _ = png_file.write_bytes(b"x" * 1024)

        result = validate_file_for_discord(png_file)

        assert result.valid is True
        assert result.error_message is None
        assert result.file_size == 1024
        assert result.file_format == ".png"

    def test_validate_all_supported_formats(self, tmp_path: Path) -> None:
        """Test validation of all supported image formats."""
        for format_ext in SUPPORTED_IMAGE_FORMATS:
            test_file = tmp_path / f"test{format_ext}"
            _ = test_file.write_bytes(b"x" * 1024)

            result = validate_file_for_discord(test_file)

            assert result.valid is True, f"Format {format_ext} should be valid"
            assert result.file_format == format_ext


class TestDiscordFileCreation:
    """Test cases for Discord file object creation."""

    def test_create_discord_file_valid(self, tmp_path: Path) -> None:
        """Test creating Discord file object from valid file."""
        test_file = tmp_path / "test.png"
        _ = test_file.write_bytes(b"test image data")

        with patch('discord.File') as mock_discord_file:
            mock_file_obj = MagicMock()
            mock_discord_file.return_value = mock_file_obj

            result = create_discord_file_safe(test_file)

            assert result == mock_file_obj
            mock_discord_file.assert_called_once()

    def test_create_discord_file_invalid(self) -> None:
        """Test creating Discord file object from invalid file."""
        result = create_discord_file_safe("/nonexistent/file.png")

        assert result is None

    def test_create_discord_file_custom_filename(self, tmp_path: Path) -> None:
        """Test creating Discord file object with custom filename."""
        test_file = tmp_path / "test.png"
        _ = test_file.write_bytes(b"test image data")

        with patch('discord.File') as mock_discord_file:
            mock_file_obj = MagicMock()
            mock_discord_file.return_value = mock_file_obj

            result = create_discord_file_safe(test_file, filename="custom.png")

            assert result == mock_file_obj
            # Verify the custom filename was used
            call_args = mock_discord_file.call_args
            assert call_args is not None
            _, kwargs = call_args  # pyright: ignore[reportAny]
            assert kwargs.get('filename') == "custom.png"  # pyright: ignore[reportAny]


class TestChannelUpload:
    """Test cases for channel file upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_files_to_channel_success(self, tmp_path: Path) -> None:
        """Test successful file upload to channel."""
        # Create test files
        test_files: list[str] = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.png"
            _ = test_file.write_bytes(b"test image data")
            test_files.append(str(test_file))

        # Mock Discord channel
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = MagicMock()
        mock_message.id = 12345
        mock_channel.send.return_value = mock_message  # pyright: ignore[reportAny]

        # Mock Discord file creation
        with patch('src.tgraph_bot.utils.discord.discord_file_utils.create_discord_file_safe') as mock_create_file:
            mock_files = [MagicMock(spec=discord.File) for _ in range(3)]
            mock_create_file.side_effect = mock_files

            result = await upload_files_to_channel(
                channel=mock_channel,
                file_paths=test_files
            )

            assert result.success is True
            assert result.files_uploaded == 3
            assert result.message_id == 12345
            # Use pyright ignore for mock method call
            mock_channel.send.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_upload_files_to_channel_no_files(self) -> None:
        """Test upload with no files provided."""
        mock_channel = AsyncMock(spec=discord.TextChannel)

        result = await upload_files_to_channel(
            channel=mock_channel,
            file_paths=[]
        )

        assert result.success is False
        assert result.error_message is not None
        assert "No files provided" in result.error_message

    @pytest.mark.asyncio
    async def test_upload_files_to_channel_validation_failure(self, tmp_path: Path) -> None:
        """Test upload with file validation failures."""
        # Create invalid file (too large)
        large_file = tmp_path / "large.png"
        _ = large_file.write_bytes(b"x" * (DISCORD_FILE_SIZE_LIMIT_REGULAR + 1))

        mock_channel = AsyncMock(spec=discord.TextChannel)

        result = await upload_files_to_channel(
            channel=mock_channel,
            file_paths=[str(large_file)]
        )

        assert result.success is False
        assert result.error_message is not None
        assert "No valid files" in result.error_message

    @pytest.mark.asyncio
    async def test_upload_files_to_channel_discord_error(self, tmp_path: Path) -> None:
        """Test upload with Discord HTTP error."""
        test_file = tmp_path / "test.png"
        _ = test_file.write_bytes(b"test image data")

        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_channel.send.side_effect = discord.HTTPException(MagicMock(), "Upload failed")  # pyright: ignore[reportAny]

        with patch('src.tgraph_bot.utils.discord.discord_file_utils.create_discord_file_safe') as mock_create_file:
            mock_create_file.return_value = MagicMock(spec=discord.File)

            result = await upload_files_to_channel(
                channel=mock_channel,
                file_paths=[str(test_file)]
            )

            assert result.success is False
            assert result.error_message is not None
            assert "Discord upload failed" in result.error_message


class TestUserDMUpload:
    """Test cases for user DM file upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_files_to_user_dm_success(self, tmp_path: Path) -> None:
        """Test successful file upload to user DM."""
        test_file = tmp_path / "test.png"
        _ = test_file.write_bytes(b"test image data")

        mock_user = AsyncMock(spec=discord.User)
        mock_message = MagicMock()
        mock_message.id = 67890
        mock_user.send.return_value = mock_message  # pyright: ignore[reportAny]

        with patch('src.tgraph_bot.utils.discord.discord_file_utils.create_discord_file_safe') as mock_create_file:
            mock_create_file.return_value = MagicMock(spec=discord.File)

            result = await upload_files_to_user_dm(
                user=mock_user,
                file_paths=[str(test_file)]
            )

            assert result.success is True
            assert result.files_uploaded == 1
            assert result.message_id == 67890
            mock_user.send.assert_called_once()  # pyright: ignore[reportAny]

    @pytest.mark.asyncio
    async def test_upload_files_to_user_dm_with_embed(self, tmp_path: Path) -> None:
        """Test file upload to user DM with embed."""
        test_file = tmp_path / "test.png"
        _ = test_file.write_bytes(b"test image data")

        mock_user = AsyncMock(spec=discord.User)
        mock_message = MagicMock()
        mock_message.id = 67890
        mock_user.send.return_value = mock_message  # pyright: ignore[reportAny]

        test_embed = discord.Embed(title="Test Embed")

        with patch('src.tgraph_bot.utils.discord.discord_file_utils.create_discord_file_safe') as mock_create_file:
            mock_create_file.return_value = MagicMock(spec=discord.File)

            result = await upload_files_to_user_dm(
                user=mock_user,
                file_paths=[str(test_file)],
                embed=test_embed
            )

            assert result.success is True
            # Verify embed was passed to send method
            call_args = mock_user.send.call_args  # pyright: ignore[reportAny]
            assert call_args is not None
            _, kwargs = call_args  # pyright: ignore[reportAny]
            assert kwargs.get('embed') == test_embed  # pyright: ignore[reportAny]


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_format_file_size_bytes(self) -> None:
        """Test file size formatting for bytes."""
        assert format_file_size(512) == "512 B"
        assert format_file_size(1023) == "1023 B"

    def test_format_file_size_kilobytes(self) -> None:
        """Test file size formatting for kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 1024 - 1) == "1024.0 KB"

    def test_format_file_size_megabytes(self) -> None:
        """Test file size formatting for megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(int(1024 * 1024 * 2.5)) == "2.5 MB"
        assert format_file_size(DISCORD_FILE_SIZE_LIMIT_REGULAR) == "8.0 MB"
        assert format_file_size(DISCORD_FILE_SIZE_LIMIT_NITRO) == "25.0 MB"


class TestTimestampHandling:
    """Test cases for timestamp handling functions."""

    def test_ensure_timezone_aware_with_naive_datetime(self) -> None:
        """Test ensure_timezone_aware with naive datetime."""
        naive_dt = datetime(2025, 1, 15, 12, 30, 0)

        result = ensure_timezone_aware(naive_dt)

        assert result.tzinfo is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 0

    def test_ensure_timezone_aware_with_aware_datetime(self) -> None:
        """Test ensure_timezone_aware with already timezone-aware datetime."""
        import datetime as dt

        aware_dt = datetime(2025, 1, 15, 12, 30, 0, tzinfo=dt.timezone.utc)

        result = ensure_timezone_aware(aware_dt)

        assert result.tzinfo is not None
        assert result == aware_dt  # Should return the same object

    def test_format_next_update_timestamp_default_style(self) -> None:
        """Test format_next_update_timestamp with default relative style."""
        import datetime as dt

        test_dt = datetime(2025, 1, 15, 12, 30, 0, tzinfo=dt.timezone.utc)

        with patch('discord.utils.format_dt') as mock_format_dt:
            mock_format_dt.return_value = "<t:1737027000:R>"

            result = format_next_update_timestamp(test_dt)

            mock_format_dt.assert_called_once()
            call_args = mock_format_dt.call_args
            assert call_args is not None
            args, kwargs = call_args  # pyright: ignore[reportAny]
            assert len(args) == 1  # pyright: ignore[reportAny]
            assert args[0].tzinfo is not None  # pyright: ignore[reportAny] # Ensure timezone-aware
            assert kwargs.get('style') == 'R'  # pyright: ignore[reportAny]
            assert result == "<t:1737027000:R>"

    def test_format_next_update_timestamp_custom_style(self) -> None:
        """Test format_next_update_timestamp with custom style."""
        import datetime as dt

        test_dt = datetime(2025, 1, 15, 12, 30, 0, tzinfo=dt.timezone.utc)

        with patch('discord.utils.format_dt') as mock_format_dt:
            mock_format_dt.return_value = "<t:1737027000:F>"

            result = format_next_update_timestamp(test_dt, style="F")

            mock_format_dt.assert_called_once()
            call_args = mock_format_dt.call_args
            assert call_args is not None
            _args, kwargs = call_args  # pyright: ignore[reportAny]
            assert kwargs.get('style') == 'F'  # pyright: ignore[reportAny]
            assert result == "<t:1737027000:F>"

    def test_format_next_update_timestamp_with_naive_datetime(self) -> None:
        """Test format_next_update_timestamp converts naive datetime to timezone-aware."""
        naive_dt = datetime(2025, 1, 15, 12, 30, 0)

        with patch('discord.utils.format_dt') as mock_format_dt:
            mock_format_dt.return_value = "<t:1737027000:R>"

            result = format_next_update_timestamp(naive_dt)

            mock_format_dt.assert_called_once()
            call_args = mock_format_dt.call_args
            assert call_args is not None
            args, _kwargs = call_args  # pyright: ignore[reportAny]
            # Verify the datetime passed to format_dt is timezone-aware
            assert args[0].tzinfo is not None  # pyright: ignore[reportAny]
            assert result == "<t:1737027000:R>"

    def test_timestamp_style_literal_type(self) -> None:
        """Test that TimestampStyle literal type works correctly."""
        # Test all valid timestamp styles
        valid_styles: list[TimestampStyle] = ['f', 'F', 'd', 'D', 't', 'T', 'R']

        import datetime as dt
        test_dt = datetime(2025, 1, 15, 12, 30, 0, tzinfo=dt.timezone.utc)

        for style in valid_styles:
            with patch('discord.utils.format_dt') as mock_format_dt:
                mock_format_dt.return_value = f"<t:1737027000:{style}>"

                result = format_next_update_timestamp(test_dt, style=style)

                mock_format_dt.assert_called_once()
                call_args = mock_format_dt.call_args
                assert call_args is not None
                _args, kwargs = call_args  # pyright: ignore[reportAny]
                assert kwargs.get('style') == style  # pyright: ignore[reportAny]
                assert result == f"<t:1737027000:{style}>"


class TestCalculateNextUpdateTime:
    """Test cases for next update time calculation."""

    def test_interval_based_update(self) -> None:
        """Test interval-based update calculation."""
        # Test with interval-based updates (XX:XX)
        with patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now:
            mock_now = datetime(2025, 1, 15, 12, 30, 0, tzinfo=get_local_timezone())
            mock_get_local_now.return_value = mock_now

            result = calculate_next_update_time(7, "XX:XX")

            assert result is not None
            # Verify it's timezone-aware
            assert result.tzinfo is not None

            # Should be exactly 7 days from the mocked current time
            expected = mock_now + timedelta(days=7)
            assert result == expected
        
    def test_fixed_time_update_future_today_no_state(self) -> None:
        """Test fixed time update when time hasn't passed today and no scheduler state."""
        # Mock no state file exists and mock get_local_now
        with (
            patch('pathlib.Path.exists', return_value=False),
            patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now
        ):
            # Use a fixed time for predictable testing
            mock_now = datetime(2025, 1, 15, 14, 30, 0, tzinfo=get_local_timezone())
            mock_get_local_now.return_value = mock_now

            # Use a time that's in the future today (18:00)
            time_str = "18:00"

            result = calculate_next_update_time(1, time_str)

            assert result is not None
            # Verify it's timezone-aware
            assert result.tzinfo is not None

            # Should be today at 18:00 in local timezone
            expected = mock_now.replace(hour=18, minute=0, second=0, microsecond=0)
            assert result == expected
        
    def test_fixed_time_update_past_today_no_state(self) -> None:
        """Test fixed time update when time has already passed today and no scheduler state."""
        # Mock no state file exists and mock get_local_now
        with (
            patch('src.tgraph_bot.utils.discord.discord_file_utils.Path') as mock_path_class,
            patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now
        ):
            # Create a properly typed mock Path instance
            mock_path_instance = Mock(spec=Path)
            mock_path_instance.exists = Mock(return_value=False)
            mock_path_class.return_value = mock_path_instance

            # Mock the current time to be 15:30 (3:30 PM) in local timezone
            mock_now = datetime(2025, 6, 28, 15, 30, 0, tzinfo=get_local_timezone())
            mock_get_local_now.return_value = mock_now

            # Use a time that has definitely passed today (10:00 AM)
            time_str = "10:00"

            result = calculate_next_update_time(1, time_str)

            assert result is not None
            # Verify it's timezone-aware
            assert result.tzinfo is not None
            # Should be tomorrow at 10:00 in local timezone
            expected = datetime(2025, 6, 29, 10, 0, 0, tzinfo=get_local_timezone())
            assert result == expected

    def test_fixed_time_with_scheduler_state_respects_interval(self) -> None:
        """Test fixed time calculation respects scheduler state last_update and update_days."""
        # Create a scenario where fixed time has passed today, but we need to respect update_days interval
        mock_now = datetime(2025, 6, 28, 15, 30, 0, tzinfo=get_local_timezone())  # 3:30 PM local time

        # Last update was yesterday at 14:30 (1 day and 1 hour ago)
        last_update = mock_now - timedelta(days=1, hours=1)

        scheduler_state = {
            "state": {
                "last_update": last_update.isoformat(),
                "next_update": (mock_now + timedelta(days=1)).isoformat()
            }
        }

        mock_state_content = json.dumps(scheduler_state)

        with (
            patch('src.tgraph_bot.utils.discord.discord_file_utils.Path') as mock_path_class,
            patch('builtins.open', mock_open(read_data=mock_state_content)),  # pyright: ignore[reportAny]
            patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now
        ):
            # Create a properly typed mock Path instance
            mock_path_instance = Mock(spec=Path)
            mock_path_instance.exists = Mock(return_value=True)
            mock_path_class.return_value = mock_path_instance

            # Mock get_local_now
            mock_get_local_now.return_value = mock_now

            # Use a time that has passed today (10:00 AM)
            time_str = "10:00"

            result = calculate_next_update_time(1, time_str)  # 1 day interval

            assert result is not None
            # Verify it's timezone-aware
            assert result.tzinfo is not None
            # Should be tomorrow at 10:00 in local timezone (respecting 1-day interval from last update)
            expected = datetime(2025, 6, 29, 10, 0, 0, tzinfo=get_local_timezone())
            assert result == expected

    def test_fixed_time_with_scheduler_state_longer_interval(self) -> None:
        """Test fixed time calculation with longer update interval from scheduler state."""
        from pathlib import Path

        # Use timezone-aware datetime for consistent testing
        now = datetime(2025, 1, 15, 16, 30, 0, tzinfo=get_local_timezone())
        past_time = now - timedelta(hours=2)  # 14:30 local time
        time_str = past_time.strftime("%H:%M")  # "14:30"

        # Last update was 2 days ago
        last_update = now - timedelta(days=2)

        # Use the correct scheduler state format that matches the actual implementation
        scheduler_state = {
            "state": {
                "last_update": last_update.isoformat(),
                "next_update": (now + timedelta(days=5)).isoformat()
            }
        }

        # Create a temporary scheduler state file for this test
        state_dir = Path("data")
        state_file = state_dir / "scheduler_state.json"

        # Ensure directory exists
        state_dir.mkdir(exist_ok=True)

        # Create temporary state file
        with state_file.open('w') as f:
            json.dump(scheduler_state, f)

        try:
            with patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now:
                mock_get_local_now.return_value = now

                result = calculate_next_update_time(7, time_str)  # 7 day interval

                assert result is not None
                # Verify it's timezone-aware
                assert result.tzinfo is not None

                # The result should respect the minimum interval from last update
                min_next_update = last_update + timedelta(days=7)

                # The result should be at or after the minimum next update time
                assert result >= min_next_update

                # The result should be at the correct fixed time (same hour/minute)
                assert result.hour == past_time.hour
                assert result.minute == past_time.minute
                assert result.second == 0
                assert result.microsecond == 0
        finally:
            # Clean up the temporary file
            if state_file.exists():
                state_file.unlink()

    def test_fixed_time_with_malformed_scheduler_state(self) -> None:
        """Test fixed time calculation with malformed scheduler state file."""
        # Mock malformed JSON in state file
        with (
            patch('src.tgraph_bot.utils.discord.discord_file_utils.Path') as mock_path_class,
            patch('builtins.open', mock_open(read_data="invalid json")),  # pyright: ignore[reportAny]
            patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now
        ):
            # Create a properly typed mock Path instance
            mock_path_instance = Mock(spec=Path)
            mock_path_instance.exists = Mock(return_value=True)
            mock_path_class.return_value = mock_path_instance

            # Mock the current time to be 15:30 (3:30 PM) local time
            mock_now = datetime(2025, 6, 28, 15, 30, 0, tzinfo=get_local_timezone())
            mock_get_local_now.return_value = mock_now

            # Use a time that has definitely passed today (10:00 AM)
            time_str = "10:00"

            result = calculate_next_update_time(1, time_str)

            assert result is not None
            # Verify it's timezone-aware
            assert result.tzinfo is not None
            # Should fall back to simple logic: tomorrow at 10:00 local time
            expected = datetime(2025, 6, 29, 10, 0, 0, tzinfo=get_local_timezone())
            assert result == expected

    def test_fixed_time_with_missing_last_update_in_state(self) -> None:
        """Test fixed time calculation when scheduler state lacks last_update."""
        mock_now = datetime(2025, 6, 28, 15, 30, 0, tzinfo=get_local_timezone())  # 3:30 PM local time

        scheduler_state = {
            "state": {
                "next_update": (mock_now + timedelta(days=1)).isoformat()
                # Missing last_update field
            }
        }

        mock_state_content = json.dumps(scheduler_state)

        with (
            patch('src.tgraph_bot.utils.discord.discord_file_utils.Path') as mock_path_class,
            patch('builtins.open', mock_open(read_data=mock_state_content)),  # pyright: ignore[reportAny]
            patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now
        ):
            # Create a properly typed mock Path instance
            mock_path_instance = Mock(spec=Path)
            mock_path_instance.exists = Mock(return_value=True)
            mock_path_class.return_value = mock_path_instance

            # Mock get_local_now
            mock_get_local_now.return_value = mock_now

            # Use a time that has definitely passed today (10:00 AM)
            time_str = "10:00"

            result = calculate_next_update_time(1, time_str)

            assert result is not None
            # Verify it's timezone-aware
            assert result.tzinfo is not None
            # Should fall back to simple logic: tomorrow at 10:00 local time
            expected = datetime(2025, 6, 29, 10, 0, 0, tzinfo=get_local_timezone())
            assert result == expected

    def test_fixed_time_with_file_read_error(self) -> None:
        """Test fixed time calculation when scheduler state file cannot be read."""
        with (
            patch('src.tgraph_bot.utils.discord.discord_file_utils.Path') as mock_path_class,
            patch('builtins.open', side_effect=IOError("Permission denied")),
            patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now
        ):
            # Create a properly typed mock Path instance
            mock_path_instance = Mock(spec=Path)
            mock_path_instance.exists = Mock(return_value=True)
            mock_path_class.return_value = mock_path_instance

            # Mock the current time to be 15:30 (3:30 PM) local time
            mock_now = datetime(2025, 6, 28, 15, 30, 0, tzinfo=get_local_timezone())
            mock_get_local_now.return_value = mock_now

            # Use a time that has definitely passed today (10:00 AM)
            time_str = "10:00"

            result = calculate_next_update_time(1, time_str)

            assert result is not None
            # Verify it's timezone-aware
            assert result.tzinfo is not None
            # Should fall back to simple logic: tomorrow at 10:00 local time
            expected = datetime(2025, 6, 29, 10, 0, 0, tzinfo=get_local_timezone())
            assert result == expected

    def test_invalid_time_format(self) -> None:
        """Test handling of invalid time formats."""
        result = calculate_next_update_time(7, "invalid")
        assert result is None
        
        result = calculate_next_update_time(7, "25:00")
        assert result is None
        
        result = calculate_next_update_time(7, "12:60")
        assert result is None


class TestCreateGraphSpecificEmbed:
    """Test cases for graph-specific embed creation."""
    
    def test_daily_play_count_embed(self) -> None:
        """Test embed creation for daily play count graph."""
        embed = create_graph_specific_embed("path/to/daily_play_count_20240115.png")
        
        assert embed.title == "📈 Daily Play Count"
        assert embed.description is not None
        assert "number of plays per day" in embed.description
        assert embed.color == discord.Color.blue()
        # Verify the image is set to reference the attachment
        assert embed.image.url == "attachment://daily_play_count_20240115.png"
        
    def test_play_count_by_dayofweek_embed(self) -> None:
        """Test embed creation for play count by day of week graph."""
        embed = create_graph_specific_embed("play_count_by_dayofweek.png")
        
        assert embed.title == "📊 Play Count by Day of Week"
        assert embed.description is not None
        assert "play activity patterns" in embed.description
        assert embed.color == discord.Color.blue()
        # Verify the image is set to reference the attachment
        assert embed.image.url == "attachment://play_count_by_dayofweek.png"
        
    def test_unknown_graph_type_embed(self) -> None:
        """Test embed creation for unknown graph types."""
        embed = create_graph_specific_embed("unknown_graph.png")

        assert embed.title == "📊 Graph"
        assert embed.description is not None
        assert "Statistical visualization" in embed.description
        assert embed.color == discord.Color.blue()
        # Verify the image is set to reference the attachment
        assert embed.image.url == "attachment://unknown_graph.png"
        
    def test_embed_with_next_update_time(self) -> None:
        """Test embed creation with next update time included."""
        # Mock get_local_now to ensure predictable behavior
        with patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now:
            mock_now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=get_local_timezone())
            mock_get_local_now.return_value = mock_now

            embed = create_graph_specific_embed(
                "daily_play_count.png",
                update_days=7,
                fixed_update_time="14:00"
            )

            assert embed.title == "📈 Daily Play Count"
            assert embed.description is not None
            assert "Next update:" in embed.description
            # Should contain Discord timestamp format from discord.utils.format_dt
            # We can't easily test the exact content since it depends on current time
            assert len(embed.description.split("\n")) >= 2  # Original + next update line
        
    def test_embed_with_interval_update(self) -> None:
        """Test embed creation with interval-based updates."""
        # Mock get_local_now to ensure predictable behavior
        with patch('src.tgraph_bot.utils.discord.discord_file_utils.get_local_now') as mock_get_local_now:
            mock_now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=get_local_timezone())
            mock_get_local_now.return_value = mock_now

            embed = create_graph_specific_embed(
                "daily_play_count.png",
                update_days=3,
                fixed_update_time="XX:XX"
            )

            assert embed.description is not None
            assert "Next update:" in embed.description
        
    def test_embed_without_update_config(self) -> None:
        """Test embed creation without update configuration."""
        embed = create_graph_specific_embed("daily_play_count.png")
        
        assert embed.description is not None
        assert "Next update:" not in embed.description
        
    def test_embed_with_invalid_update_config(self) -> None:
        """Test embed creation with invalid update configuration."""
        embed = create_graph_specific_embed(
            "daily_play_count.png",
            update_days=7,
            fixed_update_time="invalid"
        )
        
        assert embed.description is not None
        assert "Next update:" not in embed.description  # Should not add invalid timestamp
