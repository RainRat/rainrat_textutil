import os
from pathlib import Path
import re
import yaml
import argparse
import sys

# The DEFAULT_CONFIG dictionary has been removed. All configuration
# now comes exclusively from the mandatory YAML file.

def load_config(config_file_path):
    """Loads and validates configuration from the provided YAML file."""
    print(f"Loading configuration from: {config_file_path}")
    try:
        with open(config_file_path, 'r') as f:
            config = yaml.safe_load(f)
            if not config:
                print(f"Error: Configuration file '{config_file_path}' is empty or invalid.")
                sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{config_file_path}'.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)

    # --- Configuration Validation ---
    # Ensure all required top-level keys are present in the YAML file.
    required_keys = [
        'SOURCE_FOLDER', 'OUTPUT_FOLDER', 'RECURSE_SUBFOLDERS', 'INCLUDE_MISMATCHED_FILES',
        'SOURCE_EXTENSIONS', 'HEADER_EXTENSIONS', 'SINGLE_OUTPUT_FILE', 'MAX_FILE_SIZE_MB',
        'SHRINK_METHODS'
    ]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        print(f"Error: Config file is missing required keys: {', '.join(missing_keys)}")
        sys.exit(1)
    
    # Ensure all required keys are present in the nested SHRINK_METHODS dictionary.
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

    # Ensure extension lists are tuples for the script to use
    config['SOURCE_EXTENSIONS'] = tuple(config['SOURCE_EXTENSIONS'])
    config['HEADER_EXTENSIONS'] = tuple(config['HEADER_EXTENSIONS'])
    print("Configuration successfully loaded and validated.")
    return config

def content_shrink(content, config):
    """Shrinks file content based on methods enabled in the configuration."""
    shrink_settings = config.get('SHRINK_METHODS', {})

    if shrink_settings.get('remove_initial_comment'):
        if content.lstrip().startswith('/*'):
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
        previous = None
        while previous != content:
            previous = content
            content=content.replace('    ', '\t').replace('\r', '\n')
            content=content.replace('\t ', '\t').replace(' \n', '\n').replace('\n\n\n', '\n\n').replace('\t\n', '\n').replace('  ', ' ').replace('\t=', ' =').replace(' \t', '\t')
            content=re.sub(r'(?<!\n|\t)\t', ' ', content)

    if shrink_settings.get('remove_hex_pattern_lines'):
        pattern = r"^\s*\w+\(0x[0-9a-fA-F]+,\s*0x[0-9a-fA-F]+\),\s*$"
        lines = content.splitlines()
        filtered_lines = [line for line in lines if not re.match(pattern, line)]
        content = "\n".join(filtered_lines)

    return content

# The rest of the functions (read_file_safe, write_content, combine_headers)
# remain the same as the previous version. They already correctly use the `config` object.

def read_file_safe(file_path):
    """Attempt to read a file with different encodings."""
    encodings = ['utf-8', 'latin-1', 'ascii', 'utf-16']
    for encoding in encodings:
        try:
            with file_path.open('r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    print(f"Warning: Could not decode {file_path} with any of the attempted encodings.")
    return ""

def write_content(content, file_path, config):
    """Write content to a file, respecting the max file size limit and adding a truncation note if necessary."""
    max_size = config['MAX_FILE_SIZE_MB'] * 1024 * 1024
    encoded_content = content.encode('utf-8')

    if len(encoded_content) > max_size:
        print(f"Warning: Content for {file_path} exceeds max size limit. Truncating.")
        truncation_note = f"\n\n--- CONTENT TRUNCATED ---\nThis file has been truncated to {config['MAX_FILE_SIZE_MB']} MB due to size limitations.\nSome content may be missing.\n"
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
            
            shrunk_source = content_shrink(read_file_safe(source_file), config)
            content = f"{source_file.name}:\n```\n{shrunk_source}\n```\n\n"

            if matching_file:
                shrunk_header = content_shrink(read_file_safe(matching_file), config)
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
        single_output_file = output_folder / "combined_output.txt"
        write_content(combined_content, single_output_file, config)
    
    print("\nProcessing complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combines source/header files based on a YAML configuration.",
        epilog="Example: python combiner.py my_config.yml"
    )
    # The config_file argument is now mandatory (no 'nargs=?' or 'default').
    parser.add_argument('config_file', help='Path to the .yml configuration file.')
    
    args = parser.parse_args()
    config = load_config(args.config_file)
    combine_headers(config)