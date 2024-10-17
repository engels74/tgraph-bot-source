# bot/update_tracker.py
import json
import logging
import os
from datetime import datetime, timedelta


class UpdateTracker:
    def __init__(self, data_folder, config, translations):
        self.data_folder = data_folder
        self.config = config
        self.translations = translations
        self.tracker_file = os.path.join(data_folder, "update_tracker.json")
        self.last_update = None
        self.next_update = None
        self.load_tracker()
        logging.info(
            self.translations["update_tracker_initialized"].format(
                update_days=self.get_update_days(),
                fixed_time=self.get_fixed_update_time_str(),
            )
        )

    def get_update_days(self):
        update_days = self.config.get("UPDATE_DAYS", 7)  # Default to 7 if not found
        if update_days <= 0:
            raise ValueError("UPDATE_DAYS must be a positive integer")
        return update_days

    def get_fixed_update_time(self):
        fixed_time_str = self.config.get("FIXED_UPDATE_TIME")
        if fixed_time_str:
            try:
                fixed_time = datetime.strptime(fixed_time_str, "%H:%M").time()
                return fixed_time
            except ValueError:
                logging.error(f"Invalid FIXED_UPDATE_TIME format: {fixed_time_str}")
                return None
        return None

    def get_fixed_update_time_str(self):
        fixed_time = self.get_fixed_update_time()
        return (
            fixed_time.strftime("%H:%M")
            if fixed_time
            else self.translations["fixed_time_not_set"]
        )

    def load_tracker(self):
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, "r") as f:
                data = json.load(f)
                self.last_update = datetime.fromisoformat(data["last_update"])
                self.next_update = self.calculate_next_update(self.last_update)
            logging.info(
                self.translations["tracker_file_loaded"].format(
                    last_update=self.last_update, next_update=self.next_update
                )
            )
        else:
            self.reset()
            logging.info(self.translations["no_tracker_file_found"])

    def reset(self):
        self.last_update = datetime.now().replace(microsecond=0)
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()
        logging.info(
            self.translations["tracker_reset"].format(
                last_update=self.last_update, next_update=self.next_update
            )
        )

    def update(self):
        self.last_update = datetime.now().replace(microsecond=0)
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()

    def update_config(self, new_config):
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

    def calculate_next_update(self, from_date):
        update_days = self.get_update_days()
        fixed_time = self.get_fixed_update_time()

        next_update = from_date + timedelta(days=update_days)

        if fixed_time:
            next_update = next_update.replace(
                hour=fixed_time.hour, minute=fixed_time.minute, second=0, microsecond=0
            )

        # Ensure next_update is in the future
        while next_update <= datetime.now():
            next_update += timedelta(days=update_days)

        return next_update

    def get_next_update_readable(self):
        return self.next_update.strftime("%Y-%m-%d %H:%M:%S")

    def get_next_update_discord(self):
        return f"<t:{int(self.next_update.timestamp())}:R>"

    def is_update_due(self):
        now = datetime.now().replace(microsecond=0)
        is_due = now >= self.next_update
        logging.info(
            self.translations["update_due_check"].format(
                now=now, next_update=self.next_update, is_due=is_due
            )
        )
        return is_due

    def save_tracker(self):
        data = {
            "last_update": self.last_update.isoformat(),
            "next_update": self.next_update.isoformat(),
        }
        with open(self.tracker_file, "w") as f:
            json.dump(data, f)
        logging.info(
            self.translations["tracker_file_saved"].format(
                last_update=self.last_update, next_update=self.next_update
            )
        )


def create_update_tracker(data_folder, config, translations):
    return UpdateTracker(data_folder, config, translations)
