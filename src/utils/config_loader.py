import yaml
import os
from dotenv import load_dotenv

class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # Load environment variables from .env file
        load_dotenv()

        config_path = os.path.join(os.path.dirname(__file__), '../../config/agencies.yaml')
        try:
            with open(config_path, 'r') as file:
                raw_config = yaml.safe_load(file)
            self._config = self._substitute_env_vars(raw_config)
        except FileNotFoundError:
            print(f"Error: Configuration file not found at {config_path}")
            self._config = {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML configuration: {e}")
            self._config = {}

    def _substitute_env_vars(self, data):
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(elem) for elem in data]
        elif isinstance(data, str):
            # Substitute environment variables in string values
            return os.path.expandvars(data)
        return data

    def get_config(self):
        return self._config

    def get_setting(self, *keys):
        """
        Retrieves a setting from the loaded configuration using a sequence of keys.
        Example: get_setting('notification_settings', 'email', 'smtp_server')
        """
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None # Or raise an error, depending on desired behavior
        return current