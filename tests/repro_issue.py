import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import load_and_validate_config, DEFAULT_CONFIG
import yaml

def test_defaults_applied():
    # Create a minimal config file without output.header_template
    config_data = {
        'search': {'root_folders': ['.']},
    }
    with open('temp_config.yml', 'w') as f:
        yaml.dump(config_data, f)

    try:
        config = load_and_validate_config('temp_config.yml', nested_required={'search': ['root_folders']})

        output_opts = config.get('output')
        print(f"Keys in output: {list(output_opts.keys())}")

        if 'header_template' in output_opts:
            print("header_template is present.")
            print(f"Value: {repr(output_opts['header_template'])}")
            print(f"Default: {repr(DEFAULT_CONFIG['output']['header_template'])}")
        else:
            print("header_template is MISSING!")

        if 'footer_template' in output_opts:
            print("footer_template is present.")
        else:
            print("footer_template is MISSING!")

    finally:
        if os.path.exists('temp_config.yml'):
            os.remove('temp_config.yml')

if __name__ == "__main__":
    test_defaults_applied()
