import os
import re
import argparse
from utils import load_yaml_config, read_file_best_effort, normalize_whitespace, remove_hex_pattern_lines


def load_config(config_path):
    """Load and validate the YAML configuration file."""
    config = load_yaml_config(config_path)
    filters = config.get('filters', {})
    exclusions = filters.get('exclusions', {})
    exclusions.setdefault('filenames', [])
    exclusions.setdefault('extensions', [])
    exclusions.setdefault('folders', [])
    return config


def remove_c_style_comments(text):
    """Remove all C-style block comments."""
    pattern = r'/\*.*?\*/'
    return re.sub(pattern, '', text, flags=re.DOTALL)


def process_file_content(buffer, config):
    """Apply various text processing rules from the config to the file content."""
    proc_opts = config.get('processing', {})
    if proc_opts.get('remove_first_c_style_comment') and buffer.lstrip().startswith('/*'):
        end_index = buffer.find('*/', 2)
        if end_index != -1:
            buffer = buffer[end_index + 2:].lstrip()
    if proc_opts.get('remove_all_c_style_comments'):
        buffer = remove_c_style_comments(buffer)
    if proc_opts.get('snip_pattern'):
        buffer = re.sub(proc_opts['snip_pattern'], r'\1', buffer, flags=re.DOTALL)
    if proc_opts.get('compact_whitespace'):
        buffer = normalize_whitespace(buffer)
    if proc_opts.get('remove_data_table'):
        placeholder = "[magic tables removed to save context space]"
        buffer = remove_hex_pattern_lines(buffer, placeholder)
    return buffer


def find_and_combine_files(config):
    """Find, filter, and combine files based on the provided configuration."""
    search_opts = config.get('search', {})
    filter_opts = config.get('filters', {})
    output_opts = config.get('output', {})

    output_file = output_opts.get('file', 'combined_files.txt')
    include_headers = output_opts.get('include_headers', True)
    no_header_separator = output_opts.get('no_header_separator', '\n\n')
    add_line_numbers_opt = output_opts.get('add_line_numbers', False)

    exclude_conf = filter_opts.get('exclusions', {})
    exclude_folders = set(exclude_conf.get('folders') or [])
    exclude_filenames = set(exclude_conf.get('filenames') or [])
    exclude_extensions = tuple(exclude_conf.get('extensions') or [])
    allowed_extensions = tuple(search_opts.get('allowed_extensions') or [])

    with open(output_file, 'w', encoding='utf8') as outfile:
        is_first_file = True
        for root_folder in search_opts.get('root_folders') or []:
            if not os.path.isdir(root_folder):
                print(f"Warning: Root folder '{root_folder}' does not exist. Skipping.")
                continue

            for root, dirs, files in os.walk(root_folder):
                if search_opts.get('recursive', True):
                    dirs[:] = [d for d in dirs if d not in exclude_folders]
                else:
                    dirs[:] = []

                for file in files:
                    if file in exclude_filenames:
                        continue
                    if exclude_extensions and file.endswith(exclude_extensions):
                        continue
                    if allowed_extensions and not file.endswith(allowed_extensions):
                        continue

                    file_path = os.path.join(root, file)

                    try:
                        file_size = os.path.getsize(file_path)
                        min_size = filter_opts.get('min_size_bytes', 0)
                        max_size = filter_opts.get('max_size_bytes', float('inf'))
                        if not (min_size <= file_size <= max_size):
                            continue
                    except OSError:
                        continue

                    print(f"Processing: {file_path}")
                    content = read_file_best_effort(file_path)
                    processed_content = process_file_content(content, config)

                    if add_line_numbers_opt:
                        lines = processed_content.splitlines()
                        numbered_lines = [f"{i+1}: {line}" for i, line in enumerate(lines)]
                        processed_content = "\n".join(numbered_lines)

                    if include_headers:
                        relative_path = os.path.relpath(file_path, root_folder)
                        outfile.write(f"{relative_path}:\n```\n")
                        outfile.write(processed_content)
                        outfile.write("\n```\n\n")
                    else:
                        if not is_first_file:
                            outfile.write(no_header_separator)
                        outfile.write(processed_content)
                        is_first_file = False


def main():
    """Main function to parse arguments and run the tool."""
    parser = argparse.ArgumentParser(description="Combine files into a single text file based on a YAML configuration.")
    parser.add_argument("config_file", help="Path to the YAML configuration file (e.g., config.yml)")
    args = parser.parse_args()

    config = load_config(args.config_file)
    find_and_combine_files(config)
    output_file = config.get('output', {}).get('file', 'combined_files.txt')
    print(f"\nDone. Combined files have been written to '{output_file}'.")


if __name__ == "__main__":
    main()
