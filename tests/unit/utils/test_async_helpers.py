"""
Tests for async test utilities.

This module tests the async helper utilities to ensure they work correctly
and provide the expected functionality for async testing patterns.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock

from tests.utils.async_helpers import (
    AsyncTestBase,
    async_mock_context,
    async_discord_bot_context,
    assert_raises_async,
    wait_for_condition,
    create_async_mock_with_delays,
    async_timeout_test,
    cleanup_async_generators,
)


class TestAsyncTestBase:
    """Test the AsyncTestBase class functionality."""

    def test_async_test_base_initialization(self) -> None:
        """Test that AsyncTestBase initializes correctly."""
        base = AsyncTestBase()
        base.setup_method()

        assert isinstance(base._background_tasks, set)  # pyright: ignore[reportPrivateUsage] # testing internal state
        assert isinstance(base._cleanup_tasks, list)  # pyright: ignore[reportPrivateUsage] # testing internal state
        assert len(base._background_tasks) == 0  # pyright: ignore[reportPrivateUsage] # testing internal state
        assert len(base._cleanup_tasks) == 0  # pyright: ignore[reportPrivateUsage] # testing internal state

    def test_setup_method(self) -> None:
        """Test setup_method creates event loop."""
        base = AsyncTestBase()
        base.setup_method()

        # Check that loop policy and test loop are set
        assert base._original_loop_policy is not None  # pyright: ignore[reportPrivateUsage] # testing internal state
        assert base._test_loop is not None  # pyright: ignore[reportPrivateUsage] # testing internal state
        assert not base._test_loop.is_closed()  # pyright: ignore[reportPrivateUsage] # testing internal state

        # Clean up
        base.teardown_method()

    def test_teardown_method(self) -> None:
        """Test teardown_method cleans up resources."""
        base = AsyncTestBase()
        base.setup_method()

        # Add a cleanup task
        async def dummy_cleanup() -> None:
            pass

        base.add_cleanup_task(dummy_cleanup())

        # Teardown should complete without errors
        base.teardown_method()

    @pytest.mark.asyncio
    async def test_create_background_task(self) -> None:
        """Test background task creation and cleanup."""

        async def dummy_task() -> str:
            await asyncio.sleep(0.01)
            return "completed"

        base = AsyncTestBase()
        base.setup_method()

        try:
            # Create background task
            task = base.create_background_task(dummy_task(), name="test_task")

            task_name = task.get_name()
            assert task_name == "test_task"
            assert task in base._background_tasks  # pyright: ignore[reportPrivateUsage] # testing internal state

            # Wait for completion
            result = await task
            assert result == "completed"

            # Task should be removed from set when done
            await asyncio.sleep(0.01)  # Give callback time to run
            assert task not in base._background_tasks  # pyright: ignore[reportPrivateUsage] # testing internal state

        finally:
            base.teardown_method()

    @pytest.mark.asyncio
    async def test_run_with_timeout(self) -> None:
        """Test run_with_timeout utility."""

        async def quick_task() -> str:
            await asyncio.sleep(0.01)
            return "success"

        base = AsyncTestBase()

        # Should complete successfully
        result = await base.run_with_timeout(quick_task(), timeout=1.0)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_run_with_timeout_expires(self) -> None:
        """Test run_with_timeout with timeout."""

        async def slow_task() -> str:
            await asyncio.sleep(1.0)
            return "too_slow"

        base = AsyncTestBase()

        with pytest.raises(asyncio.TimeoutError):
            _ = await base.run_with_timeout(slow_task(), timeout=0.01)

    @pytest.mark.asyncio
    async def test_assert_completes_within(self) -> None:
        """Test assert_completes_within utility."""

        async def quick_task() -> str:
            await asyncio.sleep(0.01)
            return "success"

        base = AsyncTestBase()

        # Should complete successfully
        result = await base.assert_completes_within(quick_task(), 1.0)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_assert_completes_within_fails(self) -> None:
        """Test assert_completes_within with timeout."""

        async def slow_task() -> str:
            await asyncio.sleep(1.0)
            return "too_slow"

        base = AsyncTestBase()

        with pytest.raises(AssertionError, match="did not complete within"):
            _ = await base.assert_completes_within(slow_task(), 0.01)


class TestAsyncMockContext:
    """Test async mock context manager."""

    @pytest.mark.asyncio
    async def test_async_mock_context(self) -> None:
        """Test async_mock_context functionality."""
        async with async_mock_context("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None

            # Use the mock
            await asyncio.sleep(0.1)

            # Verify mock was called
            mock_sleep.assert_called_once_with(0.1)

    @pytest.mark.asyncio
    async def test_async_mock_context_with_side_effect(self) -> None:
        """Test async_mock_context with side effect."""
        async with async_mock_context(
            "asyncio.sleep", side_effect=ValueError("Test error")
        ) as mock_sleep:
            with pytest.raises(ValueError, match="Test error"):
                await asyncio.sleep(0.1)

            mock_sleep.assert_called_once_with(0.1)


class TestAsyncDiscordBotContext:
    """Test Discord bot async context manager."""

    @pytest.mark.asyncio
    async def test_async_discord_bot_context(self) -> None:
        """Test async_discord_bot_context functionality."""
        async with async_discord_bot_context(
            user_name="TestBot", guild_count=3
        ) as mock_bot:
            # Verify bot structure
            assert mock_bot.user.name == "TestBot"  # pyright: ignore[reportAny] # mock object attribute
            assert len(mock_bot.guilds) == 3  # pyright: ignore[reportAny] # mock object attribute
            assert isinstance(mock_bot.start, AsyncMock)  # pyright: ignore[reportAny] # mock object attribute
            assert isinstance(mock_bot.close, AsyncMock)  # pyright: ignore[reportAny] # mock object attribute

            # Test async methods
            await mock_bot.start("fake_token")
            mock_bot.start.assert_called_once_with("fake_token")


class TestAsyncExceptionTesting:
    """Test async exception testing utilities."""

    @pytest.mark.asyncio
    async def test_assert_raises_async(self) -> None:
        """Test assert_raises_async utility."""

        async def failing_operation() -> None:
            raise ValueError("Test error message")

        # Should catch the expected exception
        exception = await assert_raises_async(
            ValueError, failing_operation(), match="Test error"
        )

        assert isinstance(exception, ValueError)
        assert "Test error message" in str(exception)

    @pytest.mark.asyncio
    async def test_assert_raises_async_wrong_exception(self) -> None:
        """Test assert_raises_async with wrong exception type."""

        async def failing_operation() -> None:
            raise ValueError("Wrong type")

        with pytest.raises(
            AssertionError, match="Expected RuntimeError, got ValueError"
        ):
            _ = await assert_raises_async(RuntimeError, failing_operation())

    @pytest.mark.asyncio
    async def test_assert_raises_async_no_exception(self) -> None:
        """Test assert_raises_async when no exception is raised."""

        async def successful_operation() -> None:
            return None

        with pytest.raises(AssertionError, match="Expected ValueError to be raised"):
            _ = await assert_raises_async(ValueError, successful_operation())


class TestWaitForCondition:
    """Test wait_for_condition utility."""

    @pytest.mark.asyncio
    async def test_wait_for_condition_sync(self) -> None:
        """Test wait_for_condition with sync condition function."""
        state = {"ready": False}

        # Start task that will set ready to True after short delay
        async def set_ready_later() -> None:
            await asyncio.sleep(0.05)
            state["ready"] = True

        _ = asyncio.create_task(set_ready_later())

        # Wait for condition
        await wait_for_condition(
            lambda: state["ready"], timeout=1.0, description="state to be ready"
        )

        assert state["ready"] is True

    @pytest.mark.asyncio
    async def test_wait_for_condition_async(self) -> None:
        """Test wait_for_condition with async condition function."""
        state = {"counter": 0}

        async def increment_counter() -> None:
            while state["counter"] < 5:
                await asyncio.sleep(0.01)
                state["counter"] += 1

        async def check_counter() -> bool:
            return state["counter"] >= 3

        # Start counter task
        _ = asyncio.create_task(increment_counter())

        # Wait for condition
        await wait_for_condition(
            check_counter, timeout=1.0, description="counter to reach 3"
        )

        assert state["counter"] >= 3

    @pytest.mark.asyncio
    async def test_wait_for_condition_timeout(self) -> None:
        """Test wait_for_condition timeout."""

        def never_true() -> bool:
            return False

        with pytest.raises(asyncio.TimeoutError, match="Timeout waiting for condition"):
            await wait_for_condition(
                never_true, timeout=0.01, description="condition to be true"
            )


class TestAsyncMockWithDelays:
    """Test async mock with delays utility."""

    @pytest.mark.asyncio
    async def test_create_async_mock_with_delays(self) -> None:
        """Test async mock with realistic delays."""
        import time

        mock_func = create_async_mock_with_delays(
            delays=[0.05, 0.1], return_values=["first", "second"]
        )

        # First call
        start_time = time.time()
        result1 = await mock_func()  # pyright: ignore[reportAny] # mock function return
        elapsed1 = time.time() - start_time

        assert result1 == "first"
        assert elapsed1 >= 0.05

        # Second call
        start_time = time.time()
        result2 = await mock_func()  # pyright: ignore[reportAny] # mock function return
        elapsed2 = time.time() - start_time

        assert result2 == "second"
        assert elapsed2 >= 0.1

    @pytest.mark.asyncio
    async def test_create_async_mock_with_side_effects(self) -> None:
        """Test async mock with side effects (exceptions)."""
        mock_func = create_async_mock_with_delays(
            delays=[0.01], side_effects=[ValueError("Test error")]
        )

        with pytest.raises(ValueError, match="Test error"):
            _ = await mock_func()  # pyright: ignore[reportAny] # mock function return


class TestAsyncTimeoutDecorator:
    """Test async timeout decorator."""

    @pytest.mark.asyncio
    async def test_async_timeout_test_decorator(self) -> None:
        """Test async_timeout_test decorator functionality."""

        @async_timeout_test(timeout=1.0)
        async def quick_test() -> str:
            await asyncio.sleep(0.01)
            return "success"

        result = await quick_test()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_timeout_test_decorator_timeout(self) -> None:
        """Test async_timeout_test decorator with timeout."""

        @async_timeout_test(timeout=0.01)
        async def slow_test() -> str:
            await asyncio.sleep(1.0)
            return "too_slow"

        with pytest.raises(asyncio.TimeoutError, match="timed out after"):
            _ = await slow_test()


class TestAsyncGeneratorCleanup:
    """Test async generator cleanup utility."""

    @pytest.mark.asyncio
    async def test_cleanup_async_generators(self) -> None:
        """Test cleanup_async_generators utility."""
        from collections.abc import AsyncGenerator

        async def sample_generator() -> AsyncGenerator[str, None]:
            try:
                for i in range(10):
                    yield f"item_{i}"
                    await asyncio.sleep(0.01)
            except GeneratorExit:
                # Handle cleanup
                pass

        # Create generators
        gen1 = sample_generator()
        gen2 = sample_generator()

        # Get first item from each to start them
        item1 = await gen1.__anext__()
        item2 = await gen2.__anext__()

        assert item1 == "item_0"
        assert item2 == "item_0"

        # Clean up generators
        await cleanup_async_generators(gen1, gen2)

        # Generators should be closed
        with pytest.raises(StopAsyncIteration):
            _ = await gen1.__anext__()

        with pytest.raises(StopAsyncIteration):
            _ = await gen2.__anext__()
