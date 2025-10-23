"""Tests for rate limiting system.

This test suite validates the rate limiting functionality including:
- User cooldown tracking and expiration
- Global cooldown tracking
- Cooldown calculations with various time intervals
- cleanup_expired method functionality
- Disabled cooldowns (0 value configuration)

Requirements tested: 11.1, 11.2, 11.3, 11.4
"""

# pyright: reportPrivateUsage=false, reportAny=false, reportUnusedVariable=false

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest

from tgraph_bot.config.models import CommandLimits, RateLimitingConfig
from tgraph_bot.rate_limiting.rate_limiter import RateLimiter


@pytest.fixture
def basic_rate_limiting_config() -> RateLimitingConfig:
    """Fixture providing basic rate limiting configuration."""
    return RateLimitingConfig(
        config=CommandLimits(user_cooldown_minutes=5, global_cooldown_seconds=60),
        update_graphs=CommandLimits(
            user_cooldown_minutes=10, global_cooldown_seconds=120
        ),
        my_stats=CommandLimits(user_cooldown_minutes=3, global_cooldown_seconds=30),
    )


@pytest.fixture
def disabled_cooldowns_config() -> RateLimitingConfig:
    """Fixture with all cooldowns disabled (0 value)."""
    return RateLimitingConfig(
        config=CommandLimits(user_cooldown_minutes=0, global_cooldown_seconds=0),
        update_graphs=CommandLimits(
            user_cooldown_minutes=0, global_cooldown_seconds=0
        ),
        my_stats=CommandLimits(user_cooldown_minutes=0, global_cooldown_seconds=0),
    )


@pytest.fixture
def partially_disabled_config() -> RateLimitingConfig:
    """Fixture with some cooldowns disabled."""
    return RateLimitingConfig(
        config=CommandLimits(
            user_cooldown_minutes=0, global_cooldown_seconds=60  # User disabled
        ),
        update_graphs=CommandLimits(
            user_cooldown_minutes=10, global_cooldown_seconds=0  # Global disabled
        ),
        my_stats=CommandLimits(user_cooldown_minutes=3, global_cooldown_seconds=30),
    )


@pytest.fixture
def rate_limiter(basic_rate_limiting_config: RateLimitingConfig) -> RateLimiter:
    """Fixture providing a RateLimiter instance with basic config."""
    return RateLimiter(config=basic_rate_limiting_config)


class TestRateLimiterInitialization:
    """Tests for RateLimiter initialization."""

    def test_initialization_with_valid_config(
        self, basic_rate_limiting_config: RateLimitingConfig
    ) -> None:
        """Test RateLimiter initializes correctly with valid configuration."""
        limiter = RateLimiter(config=basic_rate_limiting_config)

        assert limiter.config == basic_rate_limiting_config
        assert isinstance(limiter._user_cooldowns, dict)
        assert isinstance(limiter._global_cooldowns, dict)
        assert len(limiter._user_cooldowns) == 0
        assert len(limiter._global_cooldowns) == 0

    def test_initialization_with_disabled_cooldowns(
        self, disabled_cooldowns_config: RateLimitingConfig
    ) -> None:
        """Test RateLimiter initializes correctly with disabled cooldowns."""
        limiter = RateLimiter(config=disabled_cooldowns_config)

        assert limiter.config == disabled_cooldowns_config
        assert isinstance(limiter._user_cooldowns, dict)
        assert isinstance(limiter._global_cooldowns, dict)


class TestUserCooldownTracking:
    """Tests for user-specific cooldown tracking.

    Requirements tested: 11.1, 11.2
    """

    def test_no_cooldown_on_first_use(self, rate_limiter: RateLimiter) -> None:
        """Test that first command use has no cooldown."""
        result = rate_limiter.check_cooldown("config", user_id=123)
        assert result is None

    def test_user_cooldown_after_usage(self, rate_limiter: RateLimiter) -> None:
        """Test that user cooldown is active immediately after command usage."""
        user_id = 123
        command = "config"

        # Record usage
        rate_limiter.record_usage(command, user_id)

        # Check cooldown immediately after
        result = rate_limiter.check_cooldown(command, user_id)

        assert result is not None
        assert result["is_user_cooldown"] is True
        assert result["remaining_seconds"] > 0
        # Should be approximately 5 minutes (300 seconds)
        assert 299 <= result["remaining_seconds"] <= 300

    def test_different_users_independent_cooldowns(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that different users have independent user cooldowns.

        Note: User 2 will still be affected by the global cooldown set by user 1.
        """
        user1_id = 123
        user2_id = 456
        command = "config"

        # User 1 uses command
        rate_limiter.record_usage(command, user1_id)

        # User 1 should be on cooldown (user cooldown)
        result1 = rate_limiter.check_cooldown(command, user1_id)
        assert result1 is not None
        assert result1["is_user_cooldown"] is True

        # User 2 should be on GLOBAL cooldown (not user cooldown)
        result2 = rate_limiter.check_cooldown(command, user2_id)
        assert result2 is not None
        assert result2["is_user_cooldown"] is False  # Global, not user

    def test_different_commands_independent_cooldowns(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that different commands have independent cooldowns for same user."""
        user_id = 123

        # Use config command
        rate_limiter.record_usage("config", user_id)

        # Config should be on cooldown
        result_config = rate_limiter.check_cooldown("config", user_id)
        assert result_config is not None

        # update_graphs should NOT be on cooldown
        result_graphs = rate_limiter.check_cooldown("update_graphs", user_id)
        assert result_graphs is None

    def test_user_cooldown_expiration(self, rate_limiter: RateLimiter) -> None:
        """Test that user cooldown expires after the configured time."""
        user_id = 123
        command = "my_stats"  # 3 minute cooldown

        # Mock current time
        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage(command, user_id)

            # Check at T=2 minutes (should still be on cooldown)
            mock_datetime.now.return_value = now + timedelta(minutes=2)
            result = rate_limiter.check_cooldown(command, user_id)
            assert result is not None
            assert result["is_user_cooldown"] is True
            assert 59 <= result["remaining_seconds"] <= 61  # ~1 minute remaining

            # Check at T=3 minutes (should be expired)
            mock_datetime.now.return_value = now + timedelta(minutes=3)
            result = rate_limiter.check_cooldown(command, user_id)
            assert result is None

    @pytest.mark.parametrize(
        "command,cooldown_minutes,user_id",
        [
            ("config", 5, 100),
            ("update_graphs", 10, 200),
            ("my_stats", 3, 300),
            ("config", 5, 999),  # Same command, different user
        ],
    )
    def test_user_cooldown_for_various_commands(
        self,
        basic_rate_limiting_config: RateLimitingConfig,
        command: str,
        cooldown_minutes: int,
        user_id: int,
    ) -> None:
        """Test user cooldown tracking for various commands and users."""
        limiter = RateLimiter(config=basic_rate_limiting_config)

        # Record usage
        limiter.record_usage(command, user_id)

        # Check cooldown
        result = limiter.check_cooldown(command, user_id)

        assert result is not None
        assert result["is_user_cooldown"] is True
        # Verify cooldown duration matches configuration
        expected_seconds = cooldown_minutes * 60
        assert expected_seconds - 1 <= result["remaining_seconds"] <= expected_seconds


class TestGlobalCooldownTracking:
    """Tests for global cooldown tracking.

    Requirements tested: 11.1, 11.3
    """

    def test_global_cooldown_affects_all_users(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that global cooldown affects all users."""
        command = "config"
        user1_id = 123
        user2_id = 456

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # User 1 uses command at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage(command, user1_id)

            # User 2 tries to use command at T=30 seconds (within global cooldown)
            mock_datetime.now.return_value = now + timedelta(seconds=30)
            result = rate_limiter.check_cooldown(command, user2_id)

            assert result is not None
            assert result["is_user_cooldown"] is False  # Global cooldown, not user
            # Should have ~30 seconds remaining
            assert 29 <= result["remaining_seconds"] <= 31

    def test_global_cooldown_expiration(self, rate_limiter: RateLimiter) -> None:
        """Test that global cooldown expires after configured time."""
        command = "config"  # 60 second global cooldown
        user_id = 123

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage(command, user_id)

            # Check at T=30 seconds (should still be on cooldown)
            mock_datetime.now.return_value = now + timedelta(seconds=30)
            # Check different user to test global cooldown
            result = rate_limiter.check_cooldown(command, user_id=999)
            assert result is not None
            assert result["is_user_cooldown"] is False

            # Check at T=60 seconds (should be expired)
            mock_datetime.now.return_value = now + timedelta(seconds=60)
            result = rate_limiter.check_cooldown(command, user_id=999)
            assert result is None

    def test_user_vs_global_cooldown_priority(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that user cooldown is checked before global cooldown."""
        command = "config"
        user_id = 123

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # User uses command at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage(command, user_id)

            # Check same user at T=10 seconds
            # Both user and global cooldowns are active, should report user cooldown
            mock_datetime.now.return_value = now + timedelta(seconds=10)
            result = rate_limiter.check_cooldown(command, user_id)

            assert result is not None
            assert result["is_user_cooldown"] is True  # User cooldown has priority
            # Should have ~290 seconds remaining (5 minutes - 10 seconds)
            assert 289 <= result["remaining_seconds"] <= 291

    @pytest.mark.parametrize(
        "command,global_cooldown_seconds",
        [
            ("config", 60),
            ("update_graphs", 120),
            ("my_stats", 30),
        ],
    )
    def test_global_cooldown_for_various_commands(
        self,
        basic_rate_limiting_config: RateLimitingConfig,
        command: str,
        global_cooldown_seconds: int,
    ) -> None:
        """Test global cooldown tracking for various commands."""
        limiter = RateLimiter(config=basic_rate_limiting_config)

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # User 1 uses command
            mock_datetime.now.return_value = now
            limiter.record_usage(command, user_id=100)

            # User 2 tries to use command immediately
            # (within global cooldown, but no user cooldown)
            mock_datetime.now.return_value = now + timedelta(seconds=1)
            result = limiter.check_cooldown(command, user_id=200)

            assert result is not None
            assert result["is_user_cooldown"] is False
            # Verify global cooldown duration
            assert (
                global_cooldown_seconds - 2
                <= result["remaining_seconds"]
                <= global_cooldown_seconds
            )


class TestCooldownCalculations:
    """Tests for cooldown time calculations with various intervals.

    Requirements tested: 11.1, 11.2, 11.3
    """

    @pytest.mark.parametrize(
        "elapsed_seconds,expected_remaining",
        [
            (0, 300),  # Just recorded, full cooldown
            (30, 270),  # 30 seconds elapsed
            (60, 240),  # 1 minute elapsed
            (150, 150),  # 2.5 minutes elapsed
            (299, 1),  # Almost expired
            (300, 0),  # Exactly at expiration (should be None)
            (301, 0),  # Past expiration (should be None)
        ],
    )
    def test_remaining_time_calculations(
        self,
        rate_limiter: RateLimiter,
        elapsed_seconds: int,
        expected_remaining: int,
    ) -> None:
        """Test accurate calculation of remaining cooldown time."""
        command = "config"  # 5 minute user cooldown
        user_id = 123

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage(command, user_id)

            # Check at T=elapsed_seconds
            mock_datetime.now.return_value = now + timedelta(seconds=elapsed_seconds)
            result = rate_limiter.check_cooldown(command, user_id)

            if expected_remaining > 0:
                assert result is not None
                assert (
                    expected_remaining - 1
                    <= result["remaining_seconds"]
                    <= expected_remaining + 1
                )
            else:
                assert result is None

    def test_fractional_seconds_in_remaining_time(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that remaining time can include fractional seconds."""
        command = "config"
        user_id = 123

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage(command, user_id)

            # Check at T=0.5 seconds
            mock_datetime.now.return_value = now + timedelta(milliseconds=500)
            result = rate_limiter.check_cooldown(command, user_id)

            assert result is not None
            # Should be approximately 299.5 seconds remaining
            assert 299.4 <= result["remaining_seconds"] <= 299.6

    @pytest.mark.parametrize(
        "cooldown_config,command,expected_user_seconds,expected_global_seconds",
        [
            # Test various cooldown durations
            (
                {
                    "user_cooldown_minutes": 1,
                    "global_cooldown_seconds": 10,
                },
                "config",
                60,
                10,
            ),
            (
                {
                    "user_cooldown_minutes": 30,
                    "global_cooldown_seconds": 300,
                },
                "update_graphs",
                1800,
                300,
            ),
            (
                {
                    "user_cooldown_minutes": 1440,  # Max: 24 hours
                    "global_cooldown_seconds": 86400,  # Max: 24 hours
                },
                "my_stats",
                86400,
                86400,
            ),
        ],
    )
    def test_various_cooldown_durations(
        self,
        cooldown_config: dict[str, Any],  # pyright: ignore[reportExplicitAny]
        command: str,
        expected_user_seconds: int,
        expected_global_seconds: int,
    ) -> None:
        """Test cooldown calculations with various configured durations."""
        config = RateLimitingConfig(
            config=CommandLimits(**cooldown_config),
            update_graphs=CommandLimits(**cooldown_config),
            my_stats=CommandLimits(**cooldown_config),
        )
        limiter = RateLimiter(config=config)

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage
            mock_datetime.now.return_value = now
            limiter.record_usage(command, user_id=100)

            # Check user cooldown immediately
            mock_datetime.now.return_value = now + timedelta(milliseconds=100)
            result_user = limiter.check_cooldown(command, user_id=100)
            assert result_user is not None
            assert result_user["is_user_cooldown"] is True
            assert (
                expected_user_seconds - 1
                <= result_user["remaining_seconds"]
                <= expected_user_seconds
            )

            # Check global cooldown for different user
            result_global = limiter.check_cooldown(command, user_id=200)
            assert result_global is not None
            assert result_global["is_user_cooldown"] is False
            assert (
                expected_global_seconds - 1
                <= result_global["remaining_seconds"]
                <= expected_global_seconds
            )


class TestCleanupExpired:
    """Tests for cleanup_expired method.

    Requirements tested: 11.1
    """

    def test_cleanup_removes_expired_user_cooldowns(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that cleanup removes expired user cooldowns."""
        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record multiple usages at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage("config", user_id=100)
            rate_limiter.record_usage("config", user_id=200)
            rate_limiter.record_usage("update_graphs", user_id=100)

            # Verify all are in cooldowns dict
            assert len(rate_limiter._user_cooldowns) == 3

            # Move to T=6 minutes (config cooldowns expired, update_graphs not)
            mock_datetime.now.return_value = now + timedelta(minutes=6)
            rate_limiter.cleanup_expired()

            # Should have 1 entry left (update_graphs for user 100)
            assert len(rate_limiter._user_cooldowns) == 1
            assert ("update_graphs", 100) in rate_limiter._user_cooldowns

    def test_cleanup_removes_expired_global_cooldowns(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that cleanup removes expired global cooldowns."""
        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record multiple command usages at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage("config", user_id=100)  # 60s global
            rate_limiter.record_usage("my_stats", user_id=200)  # 30s global

            # Verify both global cooldowns exist
            assert len(rate_limiter._global_cooldowns) == 2

            # Move to T=45 seconds (my_stats expired, config not)
            mock_datetime.now.return_value = now + timedelta(seconds=45)
            rate_limiter.cleanup_expired()

            # Should have 1 entry left (config)
            assert len(rate_limiter._global_cooldowns) == 1
            assert "config" in rate_limiter._global_cooldowns

    def test_cleanup_keeps_active_cooldowns(self, rate_limiter: RateLimiter) -> None:
        """Test that cleanup does not remove active cooldowns."""
        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usages at T=0
            mock_datetime.now.return_value = now
            rate_limiter.record_usage("config", user_id=100)
            rate_limiter.record_usage("update_graphs", user_id=200)

            # Move to T=30 seconds (all still active)
            mock_datetime.now.return_value = now + timedelta(seconds=30)
            rate_limiter.cleanup_expired()

            # All should still be present
            assert len(rate_limiter._user_cooldowns) == 2
            assert len(rate_limiter._global_cooldowns) == 2

    def test_cleanup_handles_empty_cooldowns(self) -> None:
        """Test that cleanup works correctly with no cooldowns."""
        config = RateLimitingConfig(
            config=CommandLimits(user_cooldown_minutes=5, global_cooldown_seconds=60),
            update_graphs=CommandLimits(
                user_cooldown_minutes=10, global_cooldown_seconds=120
            ),
            my_stats=CommandLimits(
                user_cooldown_minutes=3, global_cooldown_seconds=30
            ),
        )
        limiter = RateLimiter(config=config)

        # Call cleanup with no cooldowns recorded
        limiter.cleanup_expired()  # Should not raise any errors

        assert len(limiter._user_cooldowns) == 0
        assert len(limiter._global_cooldowns) == 0

    def test_cleanup_with_mixed_expired_and_active(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test cleanup with a mix of expired and active cooldowns."""
        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usages at different times
            mock_datetime.now.return_value = now
            rate_limiter.record_usage("my_stats", user_id=100)  # 3 min - expires at T=3

            mock_datetime.now.return_value = now + timedelta(minutes=2)
            rate_limiter.record_usage("config", user_id=200)  # 5 min - expires at T=7

            mock_datetime.now.return_value = now + timedelta(minutes=4)
            rate_limiter.record_usage("update_graphs", user_id=300)  # 10 min - expires at T=14

            # At T=5: my_stats expired (T=3), config active (expires T=7), update_graphs active (expires T=14)
            mock_datetime.now.return_value = now + timedelta(minutes=5)
            rate_limiter.cleanup_expired()

            # Should have 2 user cooldowns left (config and update_graphs)
            assert len(rate_limiter._user_cooldowns) == 2
            assert ("config", 200) in rate_limiter._user_cooldowns
            assert ("update_graphs", 300) in rate_limiter._user_cooldowns


class TestDisabledCooldowns:
    """Tests for disabled cooldowns (0 value configuration).

    Requirements tested: 11.4
    """

    def test_zero_user_cooldown_always_allows(
        self, disabled_cooldowns_config: RateLimitingConfig
    ) -> None:
        """Test that 0 user cooldown allows unlimited usage."""
        limiter = RateLimiter(config=disabled_cooldowns_config)

        user_id = 123
        command = "config"

        # Record multiple usages
        for _ in range(10):
            limiter.record_usage(command, user_id)
            result = limiter.check_cooldown(command, user_id)
            # Should always be None since cooldown is disabled
            assert result is None

    def test_zero_global_cooldown_allows_all_users(
        self, disabled_cooldowns_config: RateLimitingConfig
    ) -> None:
        """Test that 0 global cooldown allows all users."""
        limiter = RateLimiter(config=disabled_cooldowns_config)

        command = "config"

        # Record usage from user 1
        limiter.record_usage(command, user_id=100)

        # Multiple other users should be able to use immediately
        for user_id in [200, 300, 400, 500]:
            result = limiter.check_cooldown(command, user_id)
            assert result is None

    def test_partially_disabled_user_cooldown(
        self, partially_disabled_config: RateLimitingConfig
    ) -> None:
        """Test command with user cooldown disabled but global enabled."""
        limiter = RateLimiter(config=partially_disabled_config)

        command = "config"  # User cooldown disabled, global enabled
        user_id = 123

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage
            mock_datetime.now.return_value = now
            limiter.record_usage(command, user_id)

            # Same user should not have user cooldown
            result_same_user = limiter.check_cooldown(command, user_id)
            # But should have global cooldown
            assert result_same_user is not None
            assert result_same_user["is_user_cooldown"] is False

    def test_partially_disabled_global_cooldown(
        self, partially_disabled_config: RateLimitingConfig
    ) -> None:
        """Test command with global cooldown disabled but user enabled."""
        limiter = RateLimiter(config=partially_disabled_config)

        command = "update_graphs"  # Global disabled, user enabled
        user_id = 123

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage from user 1
            mock_datetime.now.return_value = now
            limiter.record_usage(command, user_id=100)

            # User 2 should be able to use (no global cooldown)
            result_user2 = limiter.check_cooldown(command, user_id=200)
            assert result_user2 is None

            # But user 1 should have user cooldown
            result_user1 = limiter.check_cooldown(command, user_id=100)
            assert result_user1 is not None
            assert result_user1["is_user_cooldown"] is True

    @pytest.mark.parametrize(
        "user_cooldown,global_cooldown,should_have_user_cd,should_have_global_cd",
        [
            (0, 0, False, False),  # Both disabled
            (0, 60, False, True),  # Only user disabled
            (5, 0, True, False),  # Only global disabled
            (5, 60, True, True),  # Both enabled
        ],
    )
    def test_various_disabled_combinations(
        self,
        user_cooldown: int,
        global_cooldown: int,
        should_have_user_cd: bool,
        should_have_global_cd: bool,
    ) -> None:
        """Test various combinations of enabled/disabled cooldowns."""
        config = RateLimitingConfig(
            config=CommandLimits(
                user_cooldown_minutes=user_cooldown,
                global_cooldown_seconds=global_cooldown,
            ),
            update_graphs=CommandLimits(
                user_cooldown_minutes=user_cooldown,
                global_cooldown_seconds=global_cooldown,
            ),
            my_stats=CommandLimits(
                user_cooldown_minutes=user_cooldown,
                global_cooldown_seconds=global_cooldown,
            ),
        )
        limiter = RateLimiter(config=config)

        command = "config"
        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # User 1 uses command
            mock_datetime.now.return_value = now
            limiter.record_usage(command, user_id=100)

            # Check user 1 (should have user cooldown if enabled)
            mock_datetime.now.return_value = now + timedelta(milliseconds=100)
            result_user1 = limiter.check_cooldown(command, user_id=100)

            if should_have_user_cd:
                assert result_user1 is not None
                assert result_user1["is_user_cooldown"] is True
            elif should_have_global_cd:
                assert result_user1 is not None
                assert result_user1["is_user_cooldown"] is False
            else:
                assert result_user1 is None

            # Check user 2 (should have global cooldown if enabled)
            result_user2 = limiter.check_cooldown(command, user_id=200)

            if should_have_global_cd:
                assert result_user2 is not None
                assert result_user2["is_user_cooldown"] is False
            else:
                assert result_user2 is None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_same_user_multiple_commands_independently(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that same user can use different commands independently."""
        user_id = 123

        # Use all three commands
        rate_limiter.record_usage("config", user_id)
        rate_limiter.record_usage("update_graphs", user_id)
        rate_limiter.record_usage("my_stats", user_id)

        # Each should be on cooldown
        assert rate_limiter.check_cooldown("config", user_id) is not None
        assert rate_limiter.check_cooldown("update_graphs", user_id) is not None
        assert rate_limiter.check_cooldown("my_stats", user_id) is not None

    def test_very_large_user_ids(self, rate_limiter: RateLimiter) -> None:
        """Test with very large Discord user IDs."""
        large_user_id = 999999999999999999  # 18 digits (max Discord ID)

        rate_limiter.record_usage("config", large_user_id)
        result = rate_limiter.check_cooldown("config", large_user_id)

        assert result is not None
        assert result["is_user_cooldown"] is True

    def test_cooldown_expiration_at_exact_boundary(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test cooldown behavior exactly at expiration time."""
        command = "my_stats"  # 3 minute cooldown
        user_id = 123

        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage
            mock_datetime.now.return_value = now
            rate_limiter.record_usage(command, user_id)

            # Check exactly at 3 minutes
            mock_datetime.now.return_value = now + timedelta(minutes=3, microseconds=0)
            result = rate_limiter.check_cooldown(command, user_id)

            # Should be expired (None or very close to 0)
            if result is not None:
                assert result["remaining_seconds"] < 0.01

    def test_multiple_cleanup_calls(self, rate_limiter: RateLimiter) -> None:
        """Test that multiple cleanup calls work correctly."""
        now = datetime.now()

        with patch("tgraph_bot.rate_limiting.rate_limiter.datetime") as mock_datetime:
            # Record usage
            mock_datetime.now.return_value = now
            rate_limiter.record_usage("config", user_id=100)

            # Call cleanup multiple times at different intervals
            mock_datetime.now.return_value = now + timedelta(seconds=30)
            rate_limiter.cleanup_expired()
            assert len(rate_limiter._user_cooldowns) == 1

            mock_datetime.now.return_value = now + timedelta(minutes=3)
            rate_limiter.cleanup_expired()
            assert len(rate_limiter._user_cooldowns) == 1

            mock_datetime.now.return_value = now + timedelta(minutes=6)
            rate_limiter.cleanup_expired()
            assert len(rate_limiter._user_cooldowns) == 0

    def test_concurrent_usage_by_many_users(self, rate_limiter: RateLimiter) -> None:
        """Test rate limiter with many concurrent users."""
        command = "config"

        # Simulate 100 users using the command
        for user_id in range(100):
            rate_limiter.record_usage(command, user_id)

        # Verify all users have cooldowns
        assert len(rate_limiter._user_cooldowns) == 100

        # Verify each user is on cooldown
        for user_id in range(100):
            result = rate_limiter.check_cooldown(command, user_id)
            assert result is not None

        # Cleanup should not affect active cooldowns
        rate_limiter.cleanup_expired()
        assert len(rate_limiter._user_cooldowns) == 100
