from pathlib import Path
import argparse
from utils import (
    read_file_best_effort,
    process_content,
    load_and_validate_config,
    add_line_numbers,
)


def load_config(config_file_path):
    """Load and validate configuration from the provided YAML file."""
    required_keys = [
        'SOURCE_FOLDER', 'OUTPUT_FOLDER', 'RECURSE_SUBFOLDERS', 'INCLUDE_MISMATCHED_FILES',
        'SOURCE_EXTENSIONS', 'HEADER_EXTENSIONS', 'SINGLE_OUTPUT_FILE', 'MAX_FILE_SIZE_MB',
        'SHRINK_METHODS',
    ]
    nested_required = {
        'SHRINK_METHODS': [
            'remove_initial_comment',
            'normalize_whitespace',
            'remove_hex_pattern_lines',
            'regex_snips',
        ]
    }
    defaults = {
        'SINGLE_OUTPUT_FILENAME': 'combined_output.txt',
        'ADD_LINE_NUMBERS': False,
    }
    config = load_and_validate_config(
        config_file_path,
        required_keys=required_keys,
        defaults=defaults,
        nested_required=nested_required,
    )

    config['SOURCE_EXTENSIONS'] = tuple(config['SOURCE_EXTENSIONS'])
    config['HEADER_EXTENSIONS'] = tuple(config['HEADER_EXTENSIONS'])
    print("Configuration successfully loaded and validated.")
    return config


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

            shrunk_source = process_content(read_file_best_effort(source_file), config['SHRINK_METHODS'])
            if config['ADD_LINE_NUMBERS']:
                shrunk_source = add_line_numbers(shrunk_source)
            content = f"{source_file.name}:\n```\n{shrunk_source}\n```\n\n"

            if matching_file:
                shrunk_header = process_content(read_file_best_effort(matching_file), config['SHRINK_METHODS'])
                if config['ADD_LINE_NUMBERS']:
                    shrunk_header = add_line_numbers(shrunk_header)
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
        epilog="Example: python concatcpph.py my_config.yml"
    )
    parser.add_argument('config_file', help='Path to the .yml configuration file.')

    args = parser.parse_args()
    config = load_config(args.config_file)
    combine_headers(config)
