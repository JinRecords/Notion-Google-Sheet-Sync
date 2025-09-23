# config_loader.py
import json

class ConfigLoader:
    """
    Loads and validates the configuration from a JSON file.
    """
    def __init__(self, config_file='config.json'):
        self.config_file = config_file

    def load_config(self):
        """
        Loads and validates the configuration from the config.json file.
        
        Returns:
            dict: A dictionary containing the configuration settings.
            None: If the file is not found, invalid, or missing required keys.
        """
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: {self.config_file} not found. Please create it.")
            return None
        except json.JSONDecodeError:
            print(f"Error: {self.config_file} is not a valid JSON file.")
            return None
