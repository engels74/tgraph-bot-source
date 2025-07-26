"""
State persistence management for the scheduling system.

This module handles saving and loading scheduler state to/from disk,
including atomic operations and error recovery.
"""

import json
import logging
import tempfile
from pathlib import Path

from .types import ScheduleState, SchedulingConfig, PersistentScheduleData
from ...utils.cli.paths import get_path_config
from ...utils.time import get_system_now

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent state storage and recovery for the scheduler."""

    def __init__(self, state_file_path: Path | None = None) -> None:
        """
        Initialize state manager.

        Args:
            state_file_path: Path to state file, defaults to data/scheduler_state.json
        """
        if state_file_path is None:
            # Use PathConfig to get the scheduler state path
            path_config = get_path_config()
            self.state_file_path: Path = path_config.get_scheduler_state_path()
        else:
            self.state_file_path = state_file_path

        # Ensure parent directory exists
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"StateManager initialized with state file: {self.state_file_path}"
        )

    def save_state(
        self, state: ScheduleState, config: SchedulingConfig | None = None
    ) -> None:
        """
        Save scheduler state to persistent storage with atomic operation.

        Args:
            state: Current scheduler state
            config: Current scheduling configuration
        """
        try:
            # Prepare data for persistence
            config_dict = None
            if config:
                config_dict = {
                    "update_days": config.update_days,
                    "fixed_update_time": config.fixed_update_time,
                }

            persistent_data = PersistentScheduleData(
                state=state.to_dict(), config=config_dict
            )

            # Atomic save using temporary file
            temp_file = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.state_file_path.parent,
                    prefix=f".{self.state_file_path.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as temp_file:
                    json.dump(
                        persistent_data.to_dict(),
                        temp_file,
                        indent=2,
                        ensure_ascii=False,
                    )
                    temp_file.flush()
                    temp_path = Path(temp_file.name)

                # Atomic move
                _ = temp_path.replace(self.state_file_path)
                logger.debug(f"State saved successfully to {self.state_file_path}")

            except Exception as e:
                # Clean up temporary file if it exists
                if temp_file and Path(temp_file.name).exists():
                    Path(temp_file.name).unlink(missing_ok=True)
                raise OSError(
                    f"Failed to save state to {self.state_file_path}: {e}"
                ) from e

        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")
            raise

    def load_state(self) -> tuple[ScheduleState, SchedulingConfig | None]:
        """
        Load scheduler state from persistent storage.

        Returns:
            Tuple of (state, config) or (default_state, None) if no valid state found
        """
        try:
            if not self.state_file_path.exists():
                logger.debug("No state file found, returning default state")
                return ScheduleState(), None

            with self.state_file_path.open("r", encoding="utf-8") as f:
                data: dict[str, object] = json.load(f)  # pyright: ignore[reportAny]

            persistent_data = PersistentScheduleData.from_dict(data)

            # Validate version compatibility
            if persistent_data.version != "1.0":
                logger.warning(
                    f"State file version {persistent_data.version} may not be compatible"
                )

            # Restore state
            state = ScheduleState.from_dict(persistent_data.state)

            # Restore configuration if available
            config = None
            if persistent_data.config:
                config = SchedulingConfig(
                    update_days=int(persistent_data.config["update_days"]),
                    fixed_update_time=str(persistent_data.config["fixed_update_time"]),
                )

            logger.info(f"State loaded successfully from {self.state_file_path}")
            logger.debug(
                f"Loaded state: last_update={state.last_update}, next_update={state.next_update}"
            )

            return state, config

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to load state file (corrupted): {e}")
            logger.info(
                "Creating backup of corrupted state file and returning default state"
            )
            self._backup_corrupted_state()
            return ScheduleState(), None

        except Exception as e:
            logger.error(f"Unexpected error loading state: {e}")
            return ScheduleState(), None

    def _backup_corrupted_state(self) -> None:
        """Create a backup of corrupted state file for debugging."""
        try:
            if self.state_file_path.exists():
                backup_path = self.state_file_path.with_suffix(
                    f".corrupted.{get_system_now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                _ = self.state_file_path.rename(backup_path)
                logger.info(f"Corrupted state file backed up to: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted state file: {e}")

    def delete_state(self) -> None:
        """Delete the persistent state file."""
        try:
            if self.state_file_path.exists():
                self.state_file_path.unlink()
                logger.info(f"State file deleted: {self.state_file_path}")
        except Exception as e:
            logger.error(f"Failed to delete state file: {e}")

    def state_exists(self) -> bool:
        """Check if a state file exists."""
        return self.state_file_path.exists()