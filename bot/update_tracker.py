# bot/update_tracker.py

"""
Improved update tracker for TGraph Bot with standardized error handling.
Handles scheduling and tracking of update times with robust error handling and validation.
"""

from config.modules.constants import ConfigKeyError
from datetime import datetime, timedelta, time
from typing import Dict, Any, Optional, Tuple
import contextlib
import json
import logging
import os

class UpdateTrackerError(Exception):
    """Base exception for update tracker related errors."""
    pass

class TimeValidationError(UpdateTrackerError):
    """Raised when time validation fails."""
    pass

class ConfigError(UpdateTrackerError):
    """Raised when configuration validation fails."""
    pass

class FileOperationError(UpdateTrackerError):
    """Raised when file operations fail."""
    pass

class StateError(UpdateTrackerError):
    """Raised when tracker state is invalid."""
    pass

class UpdateTracker:
    """Handles tracking and scheduling of updates with enhanced error handling."""

    def __init__(self, data_folder: str, config: Dict[str, Any], translations: Dict[str, str]):
        """
        Initialize the update tracker with validation.
        
        Args:
            data_folder: Path to data storage folder
            config: Configuration dictionary
            translations: Translation strings dictionary
            
        Raises:
            ConfigError: If configuration is invalid
            FileOperationError: If data folder is invalid
        """
        try:
            if not isinstance(data_folder, str) or not data_folder.strip():
                raise ConfigError("Data folder path cannot be empty")
                
            if not isinstance(config, dict):
                raise ConfigError("Configuration must be a dictionary")
                
            if not isinstance(translations, dict):
                raise ConfigError("Translations must be a dictionary")

            self.data_folder = data_folder
            self.config = config
            self.translations = translations
            self.tracker_file = os.path.join(self.data_folder, "update_tracker.json")
            
            # Ensure data folder exists
            os.makedirs(self.data_folder, exist_ok=True)
            
            self.last_update: Optional[datetime] = None
            self.next_update: Optional[datetime] = None
            self.last_check: Optional[datetime] = None
            self.last_log_time: Optional[datetime] = None
            self.log_threshold = timedelta(hours=1)
            
            # Load tracker data or initialize new state
            self._load_tracker()
            
            logging.info(
                self.translations.get(
                    "update_tracker_initialized",
                    "UpdateTracker initialized with UPDATE_DAYS: {update_days}, FIXED_UPDATE_TIME: {fixed_time}"
                ).format(
                    update_days=self.get_update_days(),
                    fixed_time=self.get_fixed_update_time_str()
                )
            )
            
        except (ConfigError, FileOperationError):
            raise
        except Exception as e:
            error_msg = "Failed to initialize update tracker"
            logging.error(f"{error_msg}: {str(e)}")
            raise UpdateTrackerError(error_msg) from e

    @classmethod
    def from_state(
        cls,
        state: Dict[str, Any],
        data_folder: str,
        config: Dict[str, Any],
        translations: Dict[str, str]
    ) -> 'UpdateTracker':
        """
        Create a new UpdateTracker instance from a state dictionary.
        
        Args:
            state: State dictionary from get_state()
            data_folder: Path to data storage folder
            config: Configuration dictionary
            translations: Translation strings dictionary
            
        Returns:
            New UpdateTracker instance with the given state
            
        Raises:
            StateError: If state is invalid or cannot be applied
        """
        try:
            tracker = cls(data_folder, config, translations)
            tracker.restore_state(state)
            return tracker
        except Exception as e:
            error_msg = f"Failed to create tracker from state: {str(e)}"
            logging.error(error_msg)
            raise StateError(error_msg) from e

    def get_state(self) -> Dict[str, Any]:
        """
        Get current tracker state for backup/restore purposes.
        
        Returns:
            Dict containing current tracker state
            
        Raises:
            StateError: If tracker state cannot be retrieved
        """
        try:
            # Validate required state components
            if self.last_update is None:
                raise StateError("Cannot get state: last_update is None")
            if self.next_update is None:
                raise StateError("Cannot get state: next_update is None")
                
            # Ensure timezone awareness for all datetime objects
            def ensure_timezone(dt: Optional[datetime]) -> Optional[datetime]:
                if dt is not None and dt.tzinfo is None:
                    return dt.astimezone()
                return dt
                
            # Create state dictionary with validated components
            state = {
                'last_update': ensure_timezone(self.last_update),
                'next_update': ensure_timezone(self.next_update),
                'last_check': ensure_timezone(self.last_check),
                'last_log_time': ensure_timezone(self.last_log_time)
            }
            
            # Log state for debugging
            logging.debug(
                "Got tracker state - Last update: %s, Next update: %s",
                state['last_update'].isoformat() if state['last_update'] else "None",
                state['next_update'].isoformat() if state['next_update'] else "None"  
            )
            
            return state
                
        except Exception as e:
            error_msg = f"Failed to get tracker state: {str(e)}"
            logging.error(error_msg)
            raise StateError(error_msg) from e

    def create_temporary_tracker(self) -> 'UpdateTracker':
        """
        Create a temporary tracker instance with current state.
        
        Returns:
            New UpdateTracker instance with copy of current state
            
        Raises:
            StateError: If temporary tracker cannot be created
        """
        try:
            current_state = self.get_state()
            return self.from_state(current_state, self.data_folder, self.config, self.translations)
        except Exception as e:
            error_msg = f"Failed to create temporary tracker: {str(e)}"
            logging.error(error_msg)
            raise StateError(error_msg) from e

    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        Restore tracker to a previous state with enhanced validation.
        
        Args:
            state: Previously saved state from get_state()
            
        Raises:
            StateError: If state restoration fails
        """
        try:
            if not isinstance(state, dict):
                raise StateError(f"Invalid state type: expected dict, got {type(state)}")
                
            # Basic validation of required fields
            required_fields = {'last_update', 'next_update'}
            missing_fields = required_fields - set(state.keys())
            if missing_fields:
                raise StateError(f"Missing required fields: {missing_fields}")

            # Get current time in system timezone for validation
            now = datetime.now().astimezone()
            max_future = now + timedelta(days=self.config.get("TIME_RANGE_DAYS", 365))
            min_past = now - timedelta(days=365 * 2)  # 2 years back as reasonable limit

            # Validate required datetime fields
            for key in required_fields:
                value = state[key]
                if value is not None:
                    if not isinstance(value, datetime):
                        raise StateError(
                            f"Invalid type for {key}: expected datetime, got {type(value)}"
                        )
                    
                    # Ensure timezone awareness
                    if value.tzinfo is None:
                        value = value.astimezone()  # Use system timezone if none specified
                    
                    # Validate time bounds
                    if value > max_future:
                        raise StateError(f"{key} is too far in the future (max: {max_future})")
                    if value < min_past:
                        raise StateError(f"{key} is too far in the past (min: {min_past})")
            
            # Apply the state after all validation passes
            self.last_update = state['last_update']
            self.next_update = state['next_update']
            self.last_check = state.get('last_check')
            self.last_log_time = state.get('last_log_time')
            
            logging.debug(
                "Restored tracker state - Last update: %s, Next update: %s",
                self.last_update.isoformat() if self.last_update else "None",
                self.next_update.isoformat() if self.next_update else "None"
            )
            
        except Exception as e:
            if isinstance(e, StateError):
                raise
            error_msg = f"Failed to restore tracker state: {str(e)}"
            logging.error(error_msg)
            raise StateError(error_msg) from e

    def save_state(self) -> None:
        """
        Save current state to disk.
        
        Raises:
            FileOperationError: If save fails
        """
        try:
            self.save_tracker()
            logging.debug(
                "Saved tracker state - Last update: %s, Next update: %s",
                self.last_update.isoformat() if self.last_update else "None",
                self.next_update.isoformat() if self.next_update else "None"
            )
        except Exception as e:
            error_msg = f"Failed to save tracker state: {str(e)}"
            logging.error(error_msg)
            raise FileOperationError(error_msg) from e

    def validate_update_days(self) -> int:
        """
        Validate and return update days configuration.
        
        Returns:
            int: Validated update days value
            
        Raises:
            ConfigError: If UPDATE_DAYS is invalid
        """
        try:
            update_days = self.config.get("UPDATE_DAYS")
            if update_days is None:
                raise ConfigError("UPDATE_DAYS not found in configuration")
                
            if isinstance(update_days, str):
                update_days = int(float(update_days))
            elif not isinstance(update_days, (int, float)):
                raise ConfigError(f"Invalid UPDATE_DAYS type: {type(update_days)}")
                
            update_days = int(update_days)
            if update_days <= 0:
                raise ConfigError("UPDATE_DAYS must be positive")
                
            return update_days
            
        except ValueError as e:
            raise ConfigError(f"Invalid UPDATE_DAYS value: {str(e)}") from e

    def get_update_days(self) -> int:
        """
        Get validated update days value with error handling.
        
        Returns:
            int: Validated update days
            
        Raises:
            ConfigError: If validation fails
        """
        try:
            return self.validate_update_days()
        except Exception as e:
            if isinstance(e, ConfigError):
                raise
            error_msg = "Failed to get update days"
            logging.error(f"{error_msg}: {str(e)}")
            raise ConfigError(error_msg) from e

    def validate_fixed_time(self, time_str: str) -> Optional[time]:
        """
        Validate fixed time string format.
        
        Args:
            time_str: Time string to validate
            
        Returns:
            Optional[time]: Parsed time object or None if disabled
            
        Raises:
            TimeValidationError: If time format is invalid
        """
        if not isinstance(time_str, str):
            raise TimeValidationError("Fixed time must be a string")
            
        time_str = time_str.strip().strip("'\"").upper()
        if time_str == "XX:XX":
            return None
            
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError as e:
            raise TimeValidationError(f"Invalid time format: {str(e)}") from e

    def get_fixed_update_time(self) -> Optional[time]:
        """
        Get validated fixed update time.
        
        Returns:
            Optional[time]: Validated time object or None if disabled
            
        Raises:
            TimeValidationError: If time validation fails
        """
        try:
            fixed_time = self.config.get("FIXED_UPDATE_TIME")
            if fixed_time is None:
                return None
                
            if isinstance(fixed_time, time):
                return fixed_time
                
            return self.validate_fixed_time(str(fixed_time))
            
        except Exception as e:
            if isinstance(e, TimeValidationError):
                raise
            error_msg = "Failed to get fixed update time"
            logging.error(f"{error_msg}: {str(e)}")
            raise TimeValidationError(error_msg) from e

    def get_fixed_update_time_str(self) -> str:
        """Get string representation of fixed update time."""
        try:
            fixed_time = self.get_fixed_update_time()
            return fixed_time.strftime("%H:%M") if fixed_time else "XX:XX"
        except TimeValidationError:
            return "XX:XX"

    def _load_tracker(self) -> None:
        """
        Load tracker data from file with error handling.
        Recalculates next_update based on current configuration.
        
        Raises:
            FileOperationError: If file operations fail
        """
        try:
            if not os.path.exists(self.tracker_file):
                self._reset_state()
                logging.info(self.translations.get(
                    "no_tracker_file_found",
                    "No tracker file found. Reset to current time."
                ))
                return

            with open(self.tracker_file, "r", encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    self.last_update = datetime.fromisoformat(data["last_update"])
                    saved_next_update = datetime.fromisoformat(data["next_update"])
                    
                    # Log the loaded values
                    logging.info(self.translations.get(
                        "tracker_file_loaded",
                        "Loaded tracker file. Last update: {last_update}, Saved next update: {next_update}"
                    ).format(
                        last_update=self.last_update,
                        next_update=saved_next_update
                    ))

                    # Recalculate next_update based on current config
                    self.next_update = self.calculate_next_update(self.last_update)
                    
                    # If the calculated time differs from saved time, log it and save
                    if self.next_update != saved_next_update:
                        logging.info(
                            "Recalculated next update time based on current configuration. "
                            f"Changed from {saved_next_update} to {self.next_update}"
                        )
                        self.save_tracker()
                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    error_msg = f"Invalid tracker file format: {str(e)}"
                    logging.error(error_msg)
                    self._reset_state()
                    
        except OSError as e:
            error_msg = f"Failed to read tracker file: {str(e)}"
            logging.error(error_msg)
            raise FileOperationError(error_msg) from e

    def _reset_state(self) -> None:
        """
        Reset tracker state to default values.
        
        Raises:
            StateError: If state reset fails
        """
        try:
            self.last_update = datetime.now().replace(microsecond=0)
            self.next_update = self.calculate_next_update(self.last_update)
            self.save_tracker()
            
            logging.info(self.translations.get(
                "tracker_reset",
                "Reset tracker. Last update: {last_update}, Next update: {next_update}"
            ).format(
                last_update=self.last_update,
                next_update=self.next_update
            ))
            
        except Exception as e:
            error_msg = "Failed to reset tracker state"
            logging.error(f"{error_msg}: {str(e)}")
            raise StateError(error_msg) from e

    def calculate_next_update(self, from_date: datetime) -> datetime:
        """
        Calculate next update time based on configuration.
        
        Args:
            from_date: Base date for calculation
            
        Returns:
            datetime: Calculated next update time
            
        Raises:
            TimeValidationError: If time calculation fails
        """
        try:
            if not isinstance(from_date, datetime):
                raise TimeValidationError("Base date must be a datetime object")
                
            update_days = self.get_update_days()
            fixed_time = self.get_fixed_update_time()
            now = datetime.now().replace(microsecond=0)

            # Calculate base date
            next_update = from_date + timedelta(days=update_days)
            next_update = next_update.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Apply fixed time if set
            if fixed_time:
                next_update = next_update.replace(
                    hour=fixed_time.hour,
                    minute=fixed_time.minute
                )

            if next_update <= now:
                days_difference = (now - next_update).days + 1
                next_update += timedelta(days=days_difference)

            logging.debug(
                f"Next update calculation: Input {from_date}, "
                f"Days {update_days}, Fixed time {fixed_time}, "
                f"Result {next_update}"
            )
            
            return next_update
            
        except Exception as e:
            if isinstance(e, (TimeValidationError, ConfigError)):
                raise TimeValidationError(str(e)) from e
            error_msg = "Failed to calculate next update time"
            logging.error(f"{error_msg}: {str(e)}")
            raise TimeValidationError(error_msg) from e

    def update(self) -> None:
        """
        Update tracker state with current time.
        
        Raises:
            StateError: If update fails
        """
        try:
            self.last_update = datetime.now().replace(microsecond=0)
            self.next_update = self.calculate_next_update(self.last_update)
            self.save_tracker()
        except Exception as e:
            error_msg = "Failed to update tracker state"
            logging.error(f"{error_msg}: {str(e)}")
            raise StateError(error_msg) from e

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update tracker configuration with validation.
        
        Args:
            new_config: New configuration dictionary
            
        Raises:
            ConfigError: If new configuration is invalid
        """
        try:
            if not isinstance(new_config, dict):
                raise ConfigError("New configuration must be a dictionary")

            # Store old values for logging
            old_update_days = self.get_update_days()
            old_fixed_time = self.get_fixed_update_time_str()
            
            # Update config and recalculate
            self.config = new_config
            new_update_days = self.get_update_days()
            new_fixed_time = self.get_fixed_update_time_str()
            
            logging.info(self.translations.get(
                "config_updated_days_and_time",
                "Configuration updated. UPDATE_DAYS changed from {update_days_old} to "
                "{update_days_new}, FIXED_UPDATE_TIME changed from {fixed_time_old} "
                "to {fixed_time_new}"
            ).format(
                update_days_old=old_update_days,
                update_days_new=new_update_days,
                fixed_time_old=old_fixed_time,
                fixed_time_new=new_fixed_time,
            ))
            
            self.next_update = self.calculate_next_update(self.last_update)
            self.save_tracker()
            
        except Exception as e:
            if isinstance(e, (ConfigError, TimeValidationError, ConfigKeyError)):
                raise ConfigError(str(e)) from e
            error_msg = "Failed to update configuration"
            logging.error(f"{error_msg}: {str(e)}")
            raise ConfigError(error_msg) from e

    def get_next_update_readable(self) -> str:
        """Get human-readable next update time."""
        if self.next_update is None:
            return self.translations.get(
                "fixed_time_not_set",
                "Update time not set"
            )
        return self.next_update.strftime("%Y-%m-%d %H:%M:%S")

    def get_next_update_discord(self) -> str:
        """
        Get Discord-formatted timestamp for next update.
        
        Returns:
            str: Discord timestamp format string
            
        Raises:
            StateError: If next update time is invalid
        """
        try:
            if self.next_update is None:
                error_msg = "Next update time not set"
                logging.error(error_msg)
                return self.translations.get(
                    "fixed_time_not_set",
                    "Update time not set"
                )
                
            timestamp = int(self.next_update.timestamp())
            test_time = datetime.fromtimestamp(timestamp)
            
            # Debug timestamp conversion
            logging.debug("Discord timestamp debug:")
            logging.debug(f" - Next update datetime: {self.next_update}")
            logging.debug(f" - Calculated timestamp: {timestamp}")
            logging.debug(f" - Test conversion back: {test_time}")
            
            return f"<t:{timestamp}:R>"
            
        except Exception as e:
            error_msg = "Failed to generate Discord timestamp"
            logging.error(f"{error_msg}: {str(e)}")
            raise StateError(error_msg) from e

    def _validate_logging_state(self, now: datetime) -> Tuple[bool, str]:
        """
        Validate logging state and determine if logging is needed.
        
        Args:
            now: Current time for validation
            
        Returns:
            Tuple of (should_log, reason)
            
        Raises:
            StateError: If validation fails
        """
        try:
            if self.next_update is None:
                return False, "Next update time not set"
                
            if self.last_log_time is None:
                return True, "First log entry"
                
            time_until_update = self.next_update - now
            
            # Determine logging frequency based on time until update
            if time_until_update <= self.log_threshold:
                if (now - self.last_log_time) >= timedelta(minutes=15):
                    return True, "Within threshold, 15-minute interval"
                    
            elif time_until_update > timedelta(days=1):
                if (now - self.last_log_time) >= timedelta(days=1):
                    return True, "Daily log for distant updates"
                    
            else:
                if (now - self.last_log_time) >= timedelta(hours=1):
                    return True, "Hourly log for upcoming updates"
                    
            return False, "Within logging interval"
            
        except Exception as e:
            error_msg = "Failed to validate logging state"
            logging.error(f"{error_msg}: {str(e)}")
            raise StateError(error_msg) from e

    def should_log_check(self, now: datetime) -> bool:
        """
        Check if update status should be logged.
        
        Args:
            now: Current time
            
        Returns:
            bool: True if should log, False otherwise
            
        Raises:
            StateError: If check fails
        """
        try:
            should_log, reason = self._validate_logging_state(now)
            if should_log:
                logging.debug(f"Logging check passed: {reason}")
            return should_log
            
        except Exception as e:
            if isinstance(e, StateError):
                raise
            error_msg = "Failed to check logging state"
            logging.error(f"{error_msg}: {str(e)}")
            raise StateError(error_msg) from e

    def is_update_due(self) -> bool:
        """
        Check if an update is due.
        
        Returns:
            bool: True if update is due, False otherwise
            
        Raises:
            StateError: If check fails
        """
        try:
            now = datetime.now().replace(microsecond=0)
            
            if self.next_update is None:
                error_msg = "Next update time not set"
                logging.error(error_msg)
                return False
                
            is_due = now >= self.next_update

            if self.should_log_check(now):
                time_until_update = self.next_update - now
                log_msg = self.translations.get(
                    "update_due_check",
                    "Checking if update is due. Now: {now}, Next update: {next_update}, Is due: {is_due}"
                ).format(
                    now=now,
                    next_update=self.next_update,
                    is_due=is_due
                )
                
                # Use appropriate log level based on proximity
                if time_until_update > timedelta(days=1):
                    logging.debug(log_msg)
                else:
                    logging.info(log_msg)
                    
                self.last_log_time = now

            return is_due
            
        except Exception as e:
            if isinstance(e, StateError):
                raise
            error_msg = "Failed to check if update is due"
            logging.error(f"{error_msg}: {str(e)}")
            raise StateError(error_msg) from e

    def save_tracker(self) -> None:
        """
        Save tracker state to file.
        
        Raises:
            FileOperationError: If save operation fails
            StateError: If tracker state is invalid
        """
        try:
            if self.last_update is None or self.next_update is None:
                raise StateError("Cannot save invalid tracker state")

            data = {
                "last_update": self.last_update.isoformat(),
                "next_update": self.next_update.isoformat(),
            }
            
            # Use atomic write operation
            temp_file = f"{self.tracker_file}.tmp"
            try:
                with open(temp_file, "w", encoding='utf-8') as f:
                    json.dump(data, f)
                os.replace(temp_file, self.tracker_file)
                    
            except OSError as e:
                if os.path.exists(temp_file):
                    with contextlib.suppress(OSError):
                        os.remove(temp_file)
                raise FileOperationError(f"Failed to save tracker file: {str(e)}") from e
                
            logging.info(self.translations.get(
                "tracker_file_saved",
                "Saved tracker file. Last update: {last_update}, Next update: {next_update}"
            ).format(
                last_update=self.last_update,
                next_update=self.next_update
            ))
            
        except Exception as e:
            if isinstance(e, (FileOperationError, StateError)):
                raise
            error_msg = "Failed to save tracker state"
            logging.error(f"{error_msg}: {str(e)}")
            raise FileOperationError(error_msg) from e

def create_update_tracker(
    data_folder: str,
    config: Dict[str, Any],
    translations: Dict[str, str]
) -> UpdateTracker:
    """
    Create an UpdateTracker instance with error handling.
    
    Args:
        data_folder: Path to data storage folder
        config: Configuration dictionary
        translations: Translation strings dictionary
        
    Returns:
        UpdateTracker: Initialized tracker instance
        
    Raises:
        UpdateTrackerError: If creation fails
    """
    try:
        return UpdateTracker(data_folder, config, translations)
    except Exception as e:
        if isinstance(e, UpdateTrackerError):
            raise
        error_msg = "Failed to create update tracker"
        logging.error(f"{error_msg}: {str(e)}")
        raise UpdateTrackerError(error_msg) from e
