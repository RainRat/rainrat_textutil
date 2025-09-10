import argparse
from pathlib import Path
from contextlib import nullcontext
from utils import (
    read_file_best_effort,
    process_content,
    load_and_validate_config,
    add_line_numbers,
)


def load_config(config_path):
    """Load and validate the YAML configuration file."""
    defaults = {
        'filters': {
            'exclusions': {
                'filenames': [],
                'extensions': [],
                'folders': [],
            },
            'inclusion_groups': {},
        },
        'pairing': {
            'enabled': False,
            'source_extensions': [],
            'header_extensions': [],
            'include_mismatched': False,
        },
    }
    config = load_and_validate_config(config_path, defaults=defaults)
    for group in config['filters']['inclusion_groups'].values():
        group.setdefault('enabled', False)
        group.setdefault('filenames', [])
    return config


def find_and_combine_files(config, dry_run=False):
    """Find, filter, and combine files based on the provided configuration."""
    search_opts = config.get('search', {})
    filter_opts = config.get('filters', {})
    output_opts = config.get('output', {})
    pair_opts = config.get('pairing', {})

    output_file = output_opts.get('file', 'combined_files.txt')
    include_headers = output_opts.get('include_headers', True)
    no_header_separator = output_opts.get('no_header_separator', '\n\n')
    add_line_numbers_opt = output_opts.get('add_line_numbers', False)

    pairing_enabled = pair_opts.get('enabled')
    source_exts = tuple(pair_opts.get('source_extensions') or [])
    header_exts = tuple(pair_opts.get('header_extensions') or [])
    include_mismatched = pair_opts.get('include_mismatched', False)

    exclude_conf = filter_opts.get('exclusions', {})
    exclude_folders = set(exclude_conf.get('folders') or [])
    exclude_filenames = set(exclude_conf.get('filenames') or [])
    exclude_extensions = tuple(exclude_conf.get('extensions') or [])
    allowed_extensions = tuple(search_opts.get('allowed_extensions') or [])
    if pairing_enabled:
        allowed_extensions = source_exts + header_exts
    inclusion_groups = filter_opts.get('inclusion_groups', {})
    include_filenames = set()
    for group_conf in inclusion_groups.values():
        if group_conf.get('enabled'):
            include_filenames.update(group_conf.get('filenames') or [])

    def should_include(file_path, root_path):
        if not file_path.is_file():
            return False
        if any(part in exclude_folders for part in file_path.relative_to(root_path).parts[:-1]):
            return False
        file_name = file_path.name
        if file_name in exclude_filenames:
            return False
        if exclude_extensions and file_path.suffix in exclude_extensions:
            return False
        if allowed_extensions and file_path.suffix not in allowed_extensions:
            return False
        if include_filenames and file_name not in include_filenames:
            return False
        try:
            file_size = file_path.stat().st_size
            min_size = filter_opts.get('min_size_bytes', 0)
            max_size = filter_opts.get('max_size_bytes', float('inf'))
            if not (min_size <= file_size <= max_size):
                return False
        except OSError:
            return False
        return True

    def handle_file(file_path, root_path, outfile, is_first_file):
        if dry_run:
            print(file_path.resolve())
            return is_first_file

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
        return is_first_file

    outfile_ctx = nullcontext() if dry_run else open(output_file, 'w', encoding='utf8')

    with outfile_ctx as outfile:
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

            if pairing_enabled:
                file_map = {}
                for file_path in iter_paths:
                    if should_include(file_path, root_path):
                        file_map.setdefault(file_path.stem, {})[file_path.suffix] = file_path
                for stem_files in file_map.values():
                    src = next((stem_files.get(ext) for ext in source_exts if stem_files.get(ext)), None)
                    hdr = next((stem_files.get(ext) for ext in header_exts if stem_files.get(ext)), None)
                    paths = []
                    if src and hdr:
                        paths = [src, hdr]
                    elif include_mismatched and (src or hdr):
                        paths = [src or hdr]
                    for fpath in paths:
                        is_first_file = handle_file(fpath, root_path, outfile, is_first_file)
            else:
                for file_path in iter_paths:
                    if not should_include(file_path, root_path):
                        continue
                    is_first_file = handle_file(file_path, root_path, outfile, is_first_file)


def main():
    """Main function to parse arguments and run the tool."""
    parser = argparse.ArgumentParser(description="Combine files into a single text file based on a YAML configuration.")
    parser.add_argument("config_file", help="Path to the YAML configuration file (e.g., config.yml)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="List files to be processed without writing output")
    args = parser.parse_args()

    config = load_config(args.config_file)
    find_and_combine_files(config, dry_run=args.dry_run)
    if not args.dry_run:
        output_file = config.get('output', {}).get('file', 'combined_files.txt')
        print(f"\nDone. Combined files have been written to '{output_file}'.")
    else:
        print("\nDry run complete.")


if __name__ == "__main__":
    main()
