"""
Async test utilities for TGraph Bot tests.

This module provides reusable async testing utilities including base classes,
context managers, timeout helpers, and exception testing utilities. It consolidates
common async testing patterns found throughout the test suite.

All utilities are designed with type safety and proper error handling in mind,
following Python 3.13 best practices.
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, TypeVar
from unittest.mock import AsyncMock, MagicMock, patch

T = TypeVar('T')
P = TypeVar('P')

if TYPE_CHECKING:
    pass


class AsyncTestBase:
    """
    Base class for async test classes with common setup methods.
    
    This class provides standardized setup and teardown methods for async tests,
    along with utility methods for common async testing patterns. It eliminates
    duplication of async test setup code across different test classes.
    
    Example:
        >>> class TestMyAsyncFeature(AsyncTestBase):
        ...     async def test_async_operation(self) -> None:
        ...         # Test setup is handled by the base class
        ...         result = await self.run_with_timeout(some_async_operation())
        ...         assert result is not None
    """
    
    def __init__(self) -> None:
        """Initialize the test base with empty collections."""
        self._original_loop_policy: asyncio.AbstractEventLoopPolicy | None = None
        self._test_loop: asyncio.AbstractEventLoop | None = None
        self._background_tasks: set[asyncio.Task[object]] = set()
        self._cleanup_tasks: list[Coroutine[object, object, object]] = []
    
    def setup_method(self) -> None:
        """Set up test method with common async test configuration."""
        # Store original event loop policy for cleanup
        self._original_loop_policy = asyncio.get_event_loop_policy()
        
        # Create a new event loop for the test
        self._test_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._test_loop)
        
        # Initialize tracking for background tasks
        self._background_tasks = set()
        self._cleanup_tasks = []
    
    def teardown_method(self) -> None:
        """Clean up async resources after test method."""
        # Cancel any remaining background tasks
        for task in self._background_tasks:
            if not task.done():
                _ = task.cancel()
        
        # Run any cleanup tasks
        if self._cleanup_tasks and self._test_loop is not None:
            for cleanup_task in self._cleanup_tasks:
                try:
                    _ = self._test_loop.run_until_complete(cleanup_task)
                except Exception:
                    # Ignore cleanup errors during teardown
                    pass
        
        # Close the test event loop
        if self._test_loop and not self._test_loop.is_closed():
            self._test_loop.close()
        
        # Restore original event loop policy
        if hasattr(self, '_original_loop_policy'):
            _ = asyncio.set_event_loop_policy(self._original_loop_policy)
    
    def create_background_task(
        self,
        coro: Coroutine[object, object, T],
        *,
        name: str | None = None,
    ) -> asyncio.Task[T]:
        """
        Create a background task that will be automatically cleaned up.
        
        Args:
            coro: The coroutine to run as a background task
            name: Optional name for the task
            
        Returns:
            asyncio.Task: The created task
        """
        task = asyncio.create_task(coro, name=name)
        # Cast to match our set type
        task_cast = task  # type: ignore[assignment] # Task[T] -> Task[object] for storage
        self._background_tasks.add(task_cast)
        
        # Remove task from set when it completes
        def remove_task(task_ref: asyncio.Task[object]) -> None:
            self._background_tasks.discard(task_ref)
        
        _ = task.add_done_callback(remove_task)
        return task
    
    def add_cleanup_task(self, coro: Coroutine[object, object, object]) -> None:
        """
        Add a cleanup task to be run during teardown.
        
        Args:
            coro: The coroutine to run during cleanup
        """
        self._cleanup_tasks.append(coro)
    
    async def run_with_timeout(
        self,
        coro: Coroutine[object, object, T],
        timeout: float = 10.0,
    ) -> T:
        """
        Run a coroutine with a timeout.
        
        Args:
            coro: The coroutine to run
            timeout: Timeout in seconds (default: 10.0)
            
        Returns:
            The result of the coroutine
            
        Raises:
            asyncio.TimeoutError: If the coroutine times out
        """
        return await asyncio.wait_for(coro, timeout=timeout)
    
    async def assert_completes_within(
        self,
        coro: Coroutine[object, object, T],
        timeout: float,
        *,
        message: str | None = None,
    ) -> T:
        """
        Assert that a coroutine completes within a specified timeout.
        
        Args:
            coro: The coroutine to run
            timeout: Maximum allowed time in seconds
            message: Optional custom assertion message
            
        Returns:
            The result of the coroutine
            
        Raises:
            AssertionError: If the coroutine takes longer than the timeout
        """
        start_time = time.time()
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return result
        except asyncio.TimeoutError as e:
            elapsed = time.time() - start_time
            error_msg = (
                message or 
                f"Coroutine did not complete within {timeout}s (took {elapsed:.2f}s)"
            )
            raise AssertionError(error_msg) from e


@asynccontextmanager
async def async_mock_context(
    mock_target: str,
    *,
    return_value: object = None,
    side_effect: object = None,
    new_callable: Callable[[], object] = AsyncMock,
) -> AsyncGenerator[AsyncMock, None]:
    """
    Async context manager for patching with AsyncMock.
    
    This utility provides a standardized way to create async mocks within
    an async context manager, ensuring proper setup and cleanup.
    
    Args:
        mock_target: The target to mock (e.g., 'module.function')
        return_value: Return value for the mock
        side_effect: Side effect for the mock
        new_callable: Callable to create the mock (default: AsyncMock)
        
    Yields:
        AsyncMock: The created mock object
        
    Example:
        >>> async def test_async_function() -> None:
        ...     async with async_mock_context('discord.Client.start') as mock_start:
        ...         mock_start.return_value = None
        ...         # Use mock_start in test
        ...         await some_function_that_calls_start()
        ...         mock_start.assert_called_once()
    """
    with patch(mock_target, new_callable=new_callable) as mock_obj:
        if return_value is not None:
            mock_obj.return_value = return_value
        if side_effect is not None:
            mock_obj.side_effect = side_effect
        
        yield mock_obj


@asynccontextmanager
async def async_discord_bot_context(
    *,
    user_id: int = 123456789,
    user_name: str = "TestBot",
    guild_count: int = 2,
    start_side_effect: object = None,
    close_side_effect: object = None,
) -> AsyncGenerator[MagicMock, None]:
    """
    Async context manager for creating a Discord bot mock with async methods.
    
    This utility creates a standardized Discord bot mock with properly configured
    async methods (start, close, etc.) and handles common setup patterns.
    
    Args:
        user_id: Bot user ID (default: 123456789)
        user_name: Bot username (default: "TestBot")
        guild_count: Number of guilds (default: 2)
        start_side_effect: Side effect for the start method
        close_side_effect: Side effect for the close method
        
    Yields:
        MagicMock: A configured Discord bot mock
        
    Example:
        >>> async def test_bot_startup() -> None:
        ...     async with async_discord_bot_context() as mock_bot:
        ...         mock_bot.start.return_value = None
        ...         await some_function_that_starts_bot(mock_bot)
        ...         mock_bot.start.assert_called_once()
    """
    # Import here to avoid circular imports
    from tests.utils.test_helpers import create_mock_discord_bot
    
    # Create base bot mock
    mock_bot = create_mock_discord_bot(
        user_id=user_id,
        user_name=user_name,
        guild_count=guild_count,
    )
    
    # Add async method mocks
    mock_bot.start = AsyncMock(side_effect=start_side_effect)
    mock_bot.close = AsyncMock(side_effect=close_side_effect)
    mock_bot.setup_hook = AsyncMock()
    mock_bot.on_ready = AsyncMock()
    mock_bot.on_error = AsyncMock()
    mock_bot.on_disconnect = AsyncMock()
    mock_bot.on_resumed = AsyncMock()
    
    try:
        yield mock_bot
    finally:
        # Ensure all async methods are properly awaited/cancelled
        for attr_name in ['start', 'close', 'setup_hook', 'on_ready', 'on_error']:
            attr = getattr(mock_bot, attr_name, None)
            if isinstance(attr, AsyncMock):
                _ = attr.reset_mock()


async def assert_raises_async(
    expected_exception: type[Exception],
    coro: Coroutine[object, object, object],
    *,
    match: str | None = None,
    timeout: float = 5.0,
) -> Exception:
    """
    Assert that an async operation raises a specific exception.
    
    This utility provides a clean way to test that async operations raise
    expected exceptions, with optional pattern matching and timeout protection.
    
    Args:
        expected_exception: The expected exception type
        coro: The coroutine that should raise the exception
        match: Optional regex pattern to match in the exception message
        timeout: Timeout for the operation (default: 5.0 seconds)
        
    Returns:
        Exception: The caught exception for further inspection
        
    Raises:
        AssertionError: If the expected exception is not raised
        asyncio.TimeoutError: If the operation times out
        
    Example:
        >>> async def test_invalid_operation() -> None:
        ...     exception = await assert_raises_async(
        ...         ValueError,
        ...         invalid_async_operation(),
        ...         match="Invalid input"
        ...     )
        ...     assert "Invalid input" in str(exception)
    """
    import re
    
    try:
        _ = await asyncio.wait_for(coro, timeout=timeout)
        # If we get here, no exception was raised
        raise AssertionError(f"Expected {expected_exception.__name__} to be raised")
    except expected_exception as e:
        # Check pattern matching if specified
        if match is not None:
            if not re.search(match, str(e)):
                raise AssertionError(
                    f"Exception message '{e}' does not match pattern '{match}'"
                ) from e
        return e
    except Exception as e:
        # Wrong exception type was raised
        raise AssertionError(
            f"Expected {expected_exception.__name__}, got {type(e).__name__}: {e}"
        ) from e


async def wait_for_condition(
    condition: Callable[[], bool] | Callable[[], Awaitable[bool]],
    *,
    timeout: float = 5.0,
    check_interval: float = 0.1,
    description: str = "condition to be true",
) -> None:
    """
    Wait for a condition to become true with timeout.
    
    This utility repeatedly checks a condition until it becomes true or
    times out. Useful for testing async operations that may take time
    to complete or for waiting on state changes.
    
    Args:
        condition: Function that returns a boolean or awaitable boolean
        timeout: Maximum time to wait in seconds (default: 5.0)
        check_interval: Time between checks in seconds (default: 0.1)
        description: Description of the condition for error messages
        
    Raises:
        asyncio.TimeoutError: If the condition doesn't become true within timeout
        
    Example:
        >>> async def test_state_change() -> None:
        ...     state = {"ready": False}
        ...     
        ...     async def check_ready() -> bool:
        ...         return state["ready"]
        ...     
        ...     # Start async operation that will set ready to True
        ...     asyncio.create_task(set_ready_after_delay(state))
        ...     
        ...     # Wait for the state to change
        ...     await wait_for_condition(check_ready, description="state to be ready")
        ...     assert state["ready"] is True
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Handle both sync and async condition functions
            if asyncio.iscoroutinefunction(condition):
                result = await condition()  # type: ignore[misc] # condition is proven to be async callable  # pyright: ignore[reportAny] # condition result type
            else:
                result = condition()  # type: ignore[misc] # condition is proven to be sync callable
            
            if result:
                return
                
        except Exception:
            # If condition check fails, continue trying
            pass
        
        await asyncio.sleep(check_interval)
    
    elapsed = time.time() - start_time
    raise asyncio.TimeoutError(
        f"Timeout waiting for {description} (waited {elapsed:.2f}s)"
    )


def create_async_mock_with_delays(
    delays: list[float],
    *,
    return_values: list[object] | None = None,
    side_effects: list[Exception] | None = None,
) -> AsyncMock:
    """
    Create an AsyncMock that introduces realistic delays between calls.
    
    This utility is useful for testing async operations that need to simulate
    network delays, processing time, or other real-world timing scenarios.
    
    Args:
        delays: List of delays in seconds for each call
        return_values: Optional list of return values for each call
        side_effects: Optional list of exceptions to raise for each call
        
    Returns:
        AsyncMock: A mock that introduces delays
        
    Raises:
        ValueError: If lists have mismatched lengths
        
    Example:
        >>> async def test_with_delays() -> None:
        ...     # Create mock that takes 0.1s, then 0.2s, then 0.05s
        ...     mock_func = create_async_mock_with_delays(
        ...         delays=[0.1, 0.2, 0.05],
        ...         return_values=["result1", "result2", "result3"]
        ...     )
        ...     
        ...     start = time.time()
        ...     result1 = await mock_func()
        ...     assert time.time() - start >= 0.1
        ...     assert result1 == "result1"
    """
    if return_values is not None and len(return_values) != len(delays):
        msg = "return_values length must match delays length"
        raise ValueError(msg)
    
    if side_effects is not None and len(side_effects) != len(delays):
        msg = "side_effects length must match delays length"
        raise ValueError(msg)
    
    call_count = 0
    
    async def delayed_side_effect(*_args: object, **_kwargs: object) -> object:
        nonlocal call_count
        
        if call_count >= len(delays):
            # Default behavior after all delays are used
            await asyncio.sleep(0.01)
            return None
        
        # Introduce the delay
        await asyncio.sleep(delays[call_count])
        
        # Handle side effects (exceptions)
        if side_effects is not None and call_count < len(side_effects):
            exception = side_effects[call_count]
            call_count += 1
            raise exception
        
        # Handle return values
        if return_values is not None and call_count < len(return_values):
            result = return_values[call_count]
            call_count += 1
            return result
        
        call_count += 1
        return None
    
    return AsyncMock(side_effect=delayed_side_effect)


def async_timeout_test(timeout: float = 10.0) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator that adds timeout protection to async test functions.
    
    This decorator ensures that async test functions don't hang indefinitely,
    which can happen with misbehaving async code or infinite loops.
    
    Args:
        timeout: Maximum time allowed for the test in seconds (default: 10.0)
        
    Returns:
        Decorated function with timeout protection
        
    Raises:
        asyncio.TimeoutError: If the test function times out
        
    Example:
        >>> @async_timeout_test(timeout=5.0)
        ... async def test_quick_operation() -> None:
        ...     result = await quick_async_operation()
        ...     assert result is not None
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError as e:
                raise asyncio.TimeoutError(
                    f"Test {func.__name__} timed out after {timeout}s"
                ) from e
        
        return wrapper
    
    return decorator


async def cleanup_async_generators(*generators: AsyncGenerator[object, None]) -> None:
    """
    Clean up multiple async generators safely.
    
    This utility ensures that async generators are properly closed,
    which is important for resource cleanup in tests.
    
    Args:
        *generators: Async generators to clean up
        
    Example:
        >>> async def test_with_generators() -> None:
        ...     gen1 = async_data_generator()
        ...     gen2 = async_event_generator()
        ...     
        ...     try:
        ...         # Use generators in test
        ...         async for item in gen1:
        ...             process_item(item)
        ...     finally:
        ...         await cleanup_async_generators(gen1, gen2)
    """
    cleanup_tasks: list[Coroutine[object, object, object]] = []
    
    for gen in generators:
        cleanup_tasks.append(gen.aclose())
    
    if cleanup_tasks:
        _ = await asyncio.gather(*cleanup_tasks, return_exceptions=True) 