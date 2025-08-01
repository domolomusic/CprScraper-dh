import yaml
import os
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'agencies.yaml')
        try:
            with open(config_path, 'r') as f:
                ConfigLoader._config = yaml.safe_load(f)
            logger.info(f"Configuration loaded successfully from {config_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file not found at {config_path}")
            ConfigLoader._config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration file: {e}")
            ConfigLoader._config = {}

    def get_config(self):
        return ConfigLoader._config

    def get_setting(self, key, default=None):
        parts = key.split('.')
        current = self._config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current