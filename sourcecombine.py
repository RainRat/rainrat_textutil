import argparse
from pathlib import Path
from utils import (
    read_file_best_effort,
    process_content,
    load_and_validate_config,
    ensure_dict,
    add_line_numbers,
)


def load_config(config_path):
    """Load and validate the YAML configuration file."""
    config = load_and_validate_config(config_path)
    filters = ensure_dict(config, 'filters')
    ensure_dict(filters, 'exclusions', {
        'filenames': [],
        'extensions': [],
        'folders': [],
    })
    inclusion_groups = ensure_dict(filters, 'inclusion_groups')
    for group in inclusion_groups.values():
        group.setdefault('enabled', False)
        group.setdefault('filenames', [])
    return config


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
    inclusion_groups = filter_opts.get('inclusion_groups', {})
    include_filenames = set()
    for group_conf in inclusion_groups.values():
        if group_conf.get('enabled'):
            include_filenames.update(group_conf.get('filenames') or [])

    with open(output_file, 'w', encoding='utf8') as outfile:
        is_first_file = True
        for root_folder in search_opts.get('root_folders') or []:
            root_path = Path(root_folder)
            if not root_path.is_dir():
                print(f"Warning: Root folder '{root_folder}' does not exist. Skipping.")
                continue

            iter_paths = (
                root_path.rglob('*')
                if search_opts.get('recursive', True)
                else root_path.glob('*')
            )

            for file_path in iter_paths:
                if not file_path.is_file():
                    continue
                if any(part in exclude_folders for part in file_path.relative_to(root_path).parts[:-1]):
                    continue
                file_name = file_path.name
                if file_name in exclude_filenames:
                    continue
                if exclude_extensions and file_path.suffix in exclude_extensions:
                    continue
                if allowed_extensions and file_path.suffix not in allowed_extensions:
                    continue
                if include_filenames and file_name not in include_filenames:
                    continue

                try:
                    file_size = file_path.stat().st_size
                    min_size = filter_opts.get('min_size_bytes', 0)
                    max_size = filter_opts.get('max_size_bytes', float('inf'))
                    if not (min_size <= file_size <= max_size):
                        continue
                except OSError:
                    continue

                print(f"Processing: {file_path}")
                content = read_file_best_effort(file_path)
                processed_content = process_content(content, config.get('processing', {}))

                if add_line_numbers_opt:
                    processed_content = add_line_numbers(processed_content)

                if include_headers:
                    relative_path = file_path.relative_to(root_path)
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
