# i18n.py
import os
import yaml

def load_translations(language):
    # Get the directory of the current script (i18n.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the absolute path to the language file
    file_path = os.path.join(current_dir, 'i18n', f'{language}.yml')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Warning: Translation file for {language} not found. Falling back to English.")
        # Fallback to English if the requested language file is not found
        fallback_path = os.path.join(current_dir, 'i18n', 'en.yml')
        with open(fallback_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)

# You might want to add a function to list available languages
def get_available_languages():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    i18n_dir = os.path.join(current_dir, 'i18n')
    return [f.split('.')[0] for f in os.listdir(i18n_dir) if f.endswith('.yml')]
