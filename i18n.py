# i18n.py
import os
import yaml

def load_translations(language):
    file_path = os.path.join('i18n', f'{language}.yml')
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)
