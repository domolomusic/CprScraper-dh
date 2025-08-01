import yaml
import os
import logging

logger = logging.getLogger(__name__)

def load_config(config_file='config/agencies.yaml'):
    """
    Loads the YAML configuration from the specified file.
    """
    # Determine the absolute path to the config file
    # This assumes config_loader.py is in src/utils/ and config/ is in the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    full_config_path = os.path.join(project_root, config_file)

    if not os.path.exists(full_config_path):
        logger.error(f"Configuration file not found: {full_config_path}")
        raise FileNotFoundError(f"Configuration file not found: {full_config_path}")

    try:
        with open(full_config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded successfully from {full_config_path}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {full_config_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading config from {full_config_path}: {e}")
        raise

if __name__ == '__main__':
    # Example usage for testing
    try:
        config = load_config()
        print("Config loaded successfully:")
        # print(yaml.dump(config, indent=2)) # Uncomment to print full config
        print(f"Number of federal agencies: {len(config.get('federal', {}))}")
        print(f"Number of state agencies: {len(config.get('states', {}))}")
    except Exception as e:
        print(f"Failed to load config: {e}")