# bot/update_tracker.py
import os
import json
from datetime import datetime, timedelta
import logging

class UpdateTracker:
    def __init__(self, data_folder, config):
        self.data_folder = data_folder
        self.config = config
        self.tracker_file = os.path.join(data_folder, 'update_tracker.json')
        self.last_update = None
        self.next_update = None
        self.load_tracker()
        logging.info(f"UpdateTracker initialized with UPDATE_DAYS: {self.config['UPDATE_DAYS']}")

    def load_tracker(self):
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
                self.last_update = datetime.fromisoformat(data['last_update'])
                # Always recalculate next_update based on current UPDATE_DAYS
                self.next_update = self.calculate_next_update(self.last_update)
            logging.info(f"Loaded tracker file. Last update: {self.last_update}, Next update: {self.next_update}")
        else:
            self.reset()
            logging.info("No tracker file found. Reset to current time.")

    def reset(self):
        self.last_update = datetime.now()
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()
        logging.info(f"Reset tracker. Last update: {self.last_update}, Next update: {self.next_update}")

    def update(self):
        self.reset()

    def update_config(self, new_config):
        old_update_days = self.config['UPDATE_DAYS']
        self.config = new_config
        new_update_days = self.config['UPDATE_DAYS']
        logging.info(f"Config updated. UPDATE_DAYS changed from {old_update_days} to {new_update_days}")
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()
        logging.info(f"Next update recalculated: {self.next_update}")

    def calculate_next_update(self, from_date):
        next_update = from_date + timedelta(days=self.config['UPDATE_DAYS'])
        logging.info(f"Calculated next update: {next_update} (UPDATE_DAYS: {self.config['UPDATE_DAYS']})")
        return next_update

    def get_next_update_timestamp(self):
        # Always recalculate to ensure we're using the most recent UPDATE_DAYS
        self.next_update = self.calculate_next_update(self.last_update)
        timestamp = int(self.next_update.timestamp())
        logging.info(f"Getting next update timestamp: {timestamp}")
        return timestamp

    def is_update_due(self):
        now = datetime.now()
        is_due = now >= self.next_update
        logging.info(f"Checking if update is due. Now: {now}, Next update: {self.next_update}, Is due: {is_due}")
        return is_due

    def save_tracker(self):
        data = {
            'last_update': self.last_update.isoformat(),
            'next_update': self.next_update.isoformat()
        }
        with open(self.tracker_file, 'w') as f:
            json.dump(data, f)
        logging.info(f"Saved tracker file. Last update: {self.last_update}, Next update: {self.next_update}")

def create_update_tracker(data_folder, config):
    return UpdateTracker(data_folder, config)
