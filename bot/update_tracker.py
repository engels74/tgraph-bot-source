# bot/update_tracker.py
import os
import json
from datetime import datetime, timedelta
import logging

class UpdateTracker:
    def __init__(self, data_folder, config, translations):
        self.data_folder = data_folder
        self.config = config
        self.translations = translations
        self.tracker_file = os.path.join(data_folder, 'update_tracker.json')
        self.last_update = None
        self.next_update = None
        self.load_tracker()
        logging.info(self.translations['update_tracker_initialized'].format(update_days=self.get_update_days()))

    def get_update_days(self):
        return self.config.get('UPDATE_DAYS', 7)  # Default to 7 if not found

    def load_tracker(self):
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, 'r') as f:
                data = json.load(f)
                self.last_update = datetime.fromisoformat(data['last_update'])
                self.next_update = self.calculate_next_update(self.last_update)
            logging.info(self.translations['tracker_file_loaded'].format(last_update=self.last_update, next_update=self.next_update))
        else:
            self.reset()
            logging.info(self.translations['no_tracker_file_found'])

    def reset(self):
        self.last_update = datetime.now()
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()
        logging.info(self.translations['tracker_reset'].format(last_update=self.last_update, next_update=self.next_update))

    def update(self):
        self.reset()

    def update_config(self, new_config):
        old_value = self.get_update_days()
        self.config = new_config
        new_value = self.get_update_days()
        logging.info(self.translations['config_updated'].format(key='UPDATE_DAYS', old_value=old_value, new_value=new_value))
        self.next_update = self.calculate_next_update(self.last_update)
        self.save_tracker()

    def calculate_next_update(self, from_date):
        next_update = from_date + timedelta(days=self.get_update_days())
        return next_update

    def get_next_update_readable(self):
        return self.next_update.strftime('%Y-%m-%d %H:%M:%S')

    def get_next_update_discord(self):
        return f"<t:{int(self.next_update.timestamp())}:R>"

    def is_update_due(self):
        now = datetime.now()
        is_due = now >= self.next_update
        logging.info(self.translations['update_due_check'].format(now=now, next_update=self.next_update, is_due=is_due))
        return is_due

    def save_tracker(self):
        data = {
            'last_update': self.last_update.isoformat(),
            'next_update': self.next_update.isoformat()
        }
        with open(self.tracker_file, 'w') as f:
            json.dump(data, f)
        logging.info(self.translations['tracker_file_saved'].format(last_update=self.last_update, next_update=self.next_update))

def create_update_tracker(data_folder, config, translations):
    return UpdateTracker(data_folder, config, translations)
