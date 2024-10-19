# bot/update_tracker.py
import json
import logging
import os
from datetime import datetime, timedelta, time
from typing import Dict, Any, Optional

class UpdateTracker:
    def __init__(self, data_folder: str, config: Dict[str, Any], translations: Dict[str, str]):
        self.data_folder = data_folder
        self.config = config
        self.translations = translations
        self.tracker_file = os.path.join(self.data_folder, "update_tracker.json")
        self.last_update: Optional[datetime] = None
        self.next_update: Optional[datetime] = None
        self.last_check: Optional[datetime] = None
        self.last_log_time: Optional[datetime] = None
        self.log_threshold = timedelta(hours=1)
        self.load_tracker()
        logging.info(
            self.translations["update_tracker_initialized"].format(
                update_days=self.get_update_days(),
                fixed_time=self.get_fixed_update_time_str(),
            )
        )

    def get_update_days(self) -> int:
        update_days = self.config.get("UPDATE_DAYS", 7)
        try:
            update_days = int(update_days)
        except (TypeError, ValueError) as err:
            raise ValueError("UPDATE_DAYS must be an integer") from err
        if update_days <= 0:
            raise ValueError("UPDATE_DAYS must be a positive integer")
        return update_days

    def get_fixed_update_time(self) -> Optional[time]:
        fixed_time = self.config.get("FIXED_UPDATE_TIME")
        if isinstance(fixed_time, time):
            return fixed_time
        elif isinstance(fixed_time, str):
            fixed_time = fixed_time.strip()
            if fixed_time.startswith(("'", '"')) and fixed_time.endswith(("'", '"')):
                fixed_time = fixed_time[1:-1]
            if fixed_time.upper() == "XX:XX":
                return None
            try:
                return datetime.strptime(fixed_time, "%H:%M").time()
            except ValueError:
                logging.error(self.translations["error_invalid_fixed_time"].format(value=fixed_time))
        return None

    def get_fixed_update_time_str(self) -> str:
        fixed_time = self.get_fixed_update_time()
        return fixed_time.strftime("%H:%M") if fixed_time else "XX:XX"

    def load_tracker(self) -> None:
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, "r") as f:
                try:
                    data = json.load(f)
                    self.last_update = datetime.fromisoformat(data["last_update"])
                    self.next_update = datetime.fromisoformat(data["next_update"])
                    logging.info(
                        self.translations["tracker_file_loaded"].format(
                            last_update=self.last_update,
                            next_update=self.next_update
                        )
                    )
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logging.error(f"Error loading tracker data: {e}")
                    self.reset()
        else:
            self.reset()
            logging.info(self.translations["no_tracker_file_found"])

    def reset(self) -> None:
        self.last_update = datetime.now().replace(microsecond=0)
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()
        logging.info(
            self.translations["tracker_reset"].format(
                last_update=self.last_update,
                next_update=self.next_update
            )
        )

    def calculate_next_update(self, from_date: datetime) -> datetime:
        update_days = self.get_update_days()
        fixed_time = self.get_fixed_update_time()
        now = datetime.now().replace(microsecond=0)

        # Calculate base date (from last update plus update days)
        next_update = from_date + timedelta(days=update_days)
        next_update = next_update.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Set the fixed time
        if fixed_time:
            next_update = next_update.replace(
                hour=fixed_time.hour,
                minute=fixed_time.minute
            )
            # If the calculated time is in the past, add one more day
            while next_update <= now:
                next_update += timedelta(days=1)

        # Debug the calculation
        logging.info(f"Next update calculation: Input {from_date}, Days {update_days}, Fixed time {fixed_time}, Result {next_update}")
        
        return next_update

    def update(self) -> None:
        self.last_update = datetime.now().replace(microsecond=0)
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        old_update_days = self.get_update_days()
        old_fixed_time = self.get_fixed_update_time_str()
        self.config = new_config
        new_update_days = self.get_update_days()
        new_fixed_time = self.get_fixed_update_time_str()
        logging.info(
            self.translations["config_updated_days_and_time"].format(
                update_days_old=old_update_days,
                update_days_new=new_update_days,
                fixed_time_old=old_fixed_time,
                fixed_time_new=new_fixed_time,
            )
        )
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()

    def get_next_update_readable(self) -> str:
        if self.next_update is None:
            return "Update time not set"
        return self.next_update.strftime("%Y-%m-%d %H:%M:%S")

    def get_next_update_discord(self) -> str:
        """Get Discord timestamp for next update."""
        if self.next_update is None:
            logging.error("next_update is None in get_next_update_discord")
            return "Update time not set"
        timestamp = int(self.next_update.timestamp())
        test_time = datetime.fromtimestamp(timestamp)
        logging.debug("Discord timestamp debug:")
        logging.debug(f" - Next update datetime: {self.next_update}")
        logging.debug(f" - Calculated timestamp: {timestamp}")
        logging.debug(f" - Test conversion back: {test_time}")
        return f"<t:{timestamp}:R>"

    def should_log_check(self, now: datetime) -> bool:
        if self.last_log_time is None:
            return True
        if self.next_update is None:
            logging.error("next_update is None in should_log_check")
            return False
        time_until_update = self.next_update - now
        
        if time_until_update <= self.log_threshold:
            return (now - self.last_log_time) >= timedelta(minutes=15)
        
        if time_until_update > timedelta(days=1):
            return (now - self.last_log_time) >= timedelta(days=1)
        
        return (now - self.last_log_time) >= timedelta(hours=1)

    def is_update_due(self) -> bool:
        now = datetime.now().replace(microsecond=0)
        if self.next_update is None:
            logging.error("next_update is None in is_update_due")
            return False
        is_due = now >= self.next_update

        if self.should_log_check(now):
            time_until_update = self.next_update - now
            if time_until_update > timedelta(days=1):
                logging.debug(
                    self.translations["update_due_check"].format(
                        now=now,
                        next_update=self.next_update,
                        is_due=is_due
                    )
                )
            else:
                logging.info(
                    self.translations["update_due_check"].format(
                        now=now,
                        next_update=self.next_update,
                        is_due=is_due
                    )
                )
            self.last_log_time = now

        return is_due

    def save_tracker(self) -> None:
        data = {
            "last_update": self.last_update.isoformat(),
            "next_update": self.next_update.isoformat(),
        }
        with open(self.tracker_file, "w") as f:
            json.dump(data, f)
        logging.info(
            self.translations["tracker_file_saved"].format(
                last_update=self.last_update,
                next_update=self.next_update
            )
        )

def create_update_tracker(data_folder: str, config: Dict[str, Any], translations: Dict[str, str]) -> UpdateTracker:
    return UpdateTracker(data_folder, config, translations)
