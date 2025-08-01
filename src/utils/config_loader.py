import yaml
import os
from dotenv import load_dotenv
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
        """Loads configuration from YAML file and environment variables."""
        load_dotenv() # Load .env file
        
        config_path = os.path.join(os.path.dirname(__file__), '../../config/agencies.yaml')
        try:
            with open(config_path, 'r') as f:
                ConfigLoader._config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            self._process_env_variables()
        except FileNotFoundError:
            logger.error(f"Configuration file not found at {config_path}")
            ConfigLoader._config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration file: {e}")
            ConfigLoader._config = {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading config: {e}")
            ConfigLoader._config = {}

    def _process_env_variables(self):
        """Replaces placeholder values in config with environment variables."""
        if not ConfigLoader._config:
            return

        # Recursively replace placeholders in dictionaries and lists
        def replace_placeholders(item):
            if isinstance(item, dict):
                for key, value in item.items():
                    item[key] = replace_placeholders(value)
            elif isinstance(item, list):
                item = [replace_placeholders(elem) for elem in item]
            elif isinstance(item, str) and item.startswith('${') and item.endswith('}'):
                env_var_name = item[2:-1]
                env_value = os.getenv(env_var_name)
                if env_value is not None:
                    logger.debug(f"Replacing config placeholder {item} with environment variable {env_var_name}")
                    return env_value
                else:
                    logger.warning(f"Environment variable {env_var_name} not found for config placeholder {item}")
            return item
        
        ConfigLoader._config = replace_placeholders(ConfigLoader._config)

    def get_config(self):
        """Returns the entire loaded configuration."""
        return ConfigLoader._config

    def get_setting(self, key, default=None):
        """Retrieves a specific setting from the configuration."""
        keys = key.split('.')
        value = ConfigLoader._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                logger.warning(f"Configuration key '{key}' not found. Returning default: {default}")
                return default
        return value