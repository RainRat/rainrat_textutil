from pathlib import Path
import re
import argparse
import sys
from utils import load_yaml_config, read_file_best_effort, normalize_whitespace, remove_hex_pattern_lines


def load_config(config_file_path):
    """Load and validate configuration from the provided YAML file."""
    config = load_yaml_config(config_file_path)

    required_keys = [
        'SOURCE_FOLDER', 'OUTPUT_FOLDER', 'RECURSE_SUBFOLDERS', 'INCLUDE_MISMATCHED_FILES',
        'SOURCE_EXTENSIONS', 'HEADER_EXTENSIONS', 'SINGLE_OUTPUT_FILE', 'MAX_FILE_SIZE_MB',
        'SHRINK_METHODS'
    ]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        print(f"Error: Config file is missing required keys: {', '.join(missing_keys)}")
        sys.exit(1)

    if isinstance(config.get('SHRINK_METHODS'), dict):
        required_shrink_keys = [
            'remove_initial_comment', 'normalize_whitespace',
            'remove_hex_pattern_lines', 'regex_snips'
        ]
        missing_shrink_keys = [key for key in required_shrink_keys if key not in config['SHRINK_METHODS']]
        if missing_shrink_keys:
            print(f"Error: 'SHRINK_METHODS' section is missing keys: {', '.join(missing_shrink_keys)}")
            sys.exit(1)
    else:
        print("Error: 'SHRINK_METHODS' key must be a dictionary.")
        sys.exit(1)

    config['SOURCE_EXTENSIONS'] = tuple(config['SOURCE_EXTENSIONS'])
    config['HEADER_EXTENSIONS'] = tuple(config['HEADER_EXTENSIONS'])
    config['SINGLE_OUTPUT_FILENAME'] = config.get('SINGLE_OUTPUT_FILENAME', 'combined_output.txt')
    print("Configuration successfully loaded and validated.")
    return config


def content_shrink(content, config):
    """Shrink file content based on methods enabled in the configuration."""
    shrink_settings = config.get('SHRINK_METHODS', {})

    if shrink_settings.get('remove_initial_comment') and content.lstrip().startswith('/*'):
        end_index = content.find('*/', 2)
        if end_index != -1:
            content = content[:content.find('/*')].rstrip() + content[end_index + 2:].lstrip()

    for rule in shrink_settings.get('regex_snips', []):
        if rule.get('enabled') and 'pattern' in rule and 'replacement' in rule:
            try:
                content = re.sub(rule['pattern'], rule['replacement'], content)
            except re.error as e:
                print(f"Warning: Invalid regex pattern in config: '{rule['pattern']}'. Error: {e}")

    if shrink_settings.get('normalize_whitespace'):
        content = normalize_whitespace(content)

    if shrink_settings.get('remove_hex_pattern_lines'):
        content = remove_hex_pattern_lines(content)

    return content


def write_content(content, file_path, config):
    """Write content to a file, respecting the max file size limit and adding a truncation note if necessary."""
    max_size = config['MAX_FILE_SIZE_MB'] * 1024 * 1024
    encoded_content = content.encode('utf-8')

    if len(encoded_content) > max_size:
        print(f"Warning: Content for {file_path} exceeds max size limit. Truncating.")
        truncation_note = (
            f"\n\n--- CONTENT TRUNCATED ---\nThis file has been truncated to {config['MAX_FILE_SIZE_MB']} MB due to size limitations.\nSome content may be missing.\n"
        )
        note_size = len(truncation_note.encode('utf-8'))
        truncated_content = content.encode('utf-8')[:max_size - note_size].decode('utf-8', 'ignore')
        truncated_content = truncated_content.rsplit('\n', 1)[0]
        final_content = truncated_content + truncation_note
    else:
        final_content = content

    with file_path.open('w', encoding='utf-8') as f:
        f.write(final_content)


def combine_headers(config):
    """Combine source and header files based on configuration settings."""
    source_folder = Path(config['SOURCE_FOLDER'])
    output_folder = Path(config['OUTPUT_FOLDER'])
    output_folder.mkdir(exist_ok=True)

    processed_files = set()
    combined_content = ""

    traverse_method = source_folder.rglob if config['RECURSE_SUBFOLDERS'] else source_folder.glob

    for source_file in traverse_method('*'):
        if source_file.suffix in config['SOURCE_EXTENSIONS'] + config['HEADER_EXTENSIONS']:
            if source_file in processed_files:
                continue

            base_name = source_file.stem
            matching_file = None
            if source_file.suffix in config['SOURCE_EXTENSIONS']:
                for ext in config['HEADER_EXTENSIONS']:
                    potential_matching_file = source_file.with_suffix(ext)
                    if potential_matching_file.exists():
                        matching_file = potential_matching_file
                        break
            elif source_file.suffix in config['HEADER_EXTENSIONS']:
                for ext in config['SOURCE_EXTENSIONS']:
                    potential_matching_file = source_file.with_suffix(ext)
                    if potential_matching_file.exists():
                        matching_file = potential_matching_file
                        break

            shrunk_source = content_shrink(read_file_best_effort(source_file), config)
            content = f"{source_file.name}:\n```\n{shrunk_source}\n```\n\n"

            if matching_file:
                shrunk_header = content_shrink(read_file_best_effort(matching_file), config)
                content += f"{matching_file.name}:\n```\n{shrunk_header}\n```\n\n"
                processed_files.add(matching_file)
            elif not config['INCLUDE_MISMATCHED_FILES']:
                continue

            if config['SINGLE_OUTPUT_FILE']:
                combined_content += content
            else:
                output_file = output_folder / f"{base_name}.combined"
                write_content(content, output_file, config)

            processed_files.add(source_file)

    if config['SINGLE_OUTPUT_FILE']:
        single_output_file = output_folder / config['SINGLE_OUTPUT_FILENAME']
        write_content(combined_content, single_output_file, config)

    print("\nProcessing complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combines source/header files based on a YAML configuration.",
        epilog="Example: python combiner.py my_config.yml"
    )
    parser.add_argument('config_file', help='Path to the .yml configuration file.')

    args = parser.parse_args()
    config = load_config(args.config_file)
    combine_headers(config)
