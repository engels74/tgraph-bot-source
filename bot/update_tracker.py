# bot/update_tracker.py
import os
import json
from datetime import datetime, timedelta

class UpdateTracker:
    def __init__(self, data_folder, config):
        self.data_folder = data_folder
        self.config = config
        self.tracker_file = os.path.join(data_folder, 'update_tracker.json')
        self.last_update = None
        self.next_update = None
        self.load_tracker()

    def load_tracker(self):
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
                self.last_update = datetime.fromisoformat(data['last_update'])
                # Recalculate next_update based on current UPDATE_DAYS
                self.next_update = self.last_update + timedelta(days=self.config['UPDATE_DAYS'])
        else:
            self.reset()

    def reset(self):
        self.last_update = datetime.now()
        self.next_update = self.last_update + timedelta(days=self.config['UPDATE_DAYS'])
        self.save_tracker()

    def update(self):
        self.reset()

    def update_config(self, new_config):
        self.config = new_config
        self.reset()  # This will use the new config to calculate the next update time

    def get_next_update_timestamp(self):
        return int(self.next_update.timestamp())

    def is_update_due(self):
        # Always check against current time and UPDATE_DAYS
        return datetime.now() >= self.last_update + timedelta(days=self.config['UPDATE_DAYS'])

    def save_tracker(self):
        data = {
            'last_update': self.last_update.isoformat(),
            'next_update': self.next_update.isoformat()
        }
        with open(self.tracker_file, 'w') as f:
            json.dump(data, f)

def create_update_tracker(data_folder, config):
    return UpdateTracker(data_folder, config)
