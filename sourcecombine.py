import argparse
import sys
import os
import fnmatch
from pathlib import Path
from contextlib import nullcontext
from utils import (
    read_file_best_effort,
    process_content,
    load_and_validate_config,
    add_line_numbers,
    ConfigNotFoundError,
    InvalidConfigError,
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
        'output': {
            'file': 'combined_files.txt',
            'folder': '.',
        },
    }
    nested_required = {
        'search': ['root_folders'],
    }
    config = load_and_validate_config(
        config_path, defaults=defaults, nested_required=nested_required
    )
    if (
        config.get('pairing', {}).get('enabled')
        and config.get('search', {}).get('allowed_extensions')
    ):
        raise InvalidConfigError(
            "'allowed_extensions' is ignored when pairing is enabled; "
            "remove it or disable pairing."
        )
    return config


def _match_path(relative_path, patterns):
    """Return True if ``relative_path`` matches any glob ``patterns``."""
    if not patterns:
        return False
    rel_str = relative_path.as_posix()
    parts = relative_path.parts
    for pattern in patterns:
        if fnmatch.fnmatchcase(rel_str, pattern) or fnmatch.fnmatchcase(
            rel_str + '/', pattern
        ):
            return True
        if any(fnmatch.fnmatchcase(part, pattern) for part in parts):
            return True
    return False


def should_include(
    file_path,
    root_path,
    *,
    exclude_filenames,
    exclude_extensions,
    allowed_extensions,
    include_filenames,
    filter_opts,
):
    """Return ``True`` if ``file_path`` passes all filtering rules."""
    if not file_path.is_file():
        return False
    file_name = file_path.name
    if any(fnmatch.fnmatchcase(file_name, pattern) for pattern in exclude_filenames):
        return False
    suffix = file_path.suffix.lower()
    if exclude_extensions and suffix in exclude_extensions:
        return False
    if allowed_extensions and suffix not in allowed_extensions:
        return False
    if include_filenames and file_name not in include_filenames:
        return False
    try:
        file_size = file_path.stat().st_size
        min_size = filter_opts.get('min_size_bytes', 0)
        max_size = filter_opts.get('max_size_bytes') or float('inf')
        if not (min_size <= file_size <= max_size):
            return False
    except OSError:
        return False
    return True


def collect_file_paths(root_folder, recursive, exclude_folders):
    """Return all paths in ``root_folder`` while pruning excluded folders."""
    root_path = Path(root_folder)
    if not root_path.is_dir():
        print(f"Warning: Root folder '{root_folder}' does not exist. Skipping.")
        return [], None

    file_paths = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root_path):
            rel_dir = Path(dirpath).relative_to(root_path)
            dirnames[:] = [
                d
                for d in dirnames
                if not _match_path(rel_dir / d, exclude_folders)
            ]
            for name in filenames:
                file_paths.append(Path(dirpath) / name)
    else:
        for entry in root_path.iterdir():
            if entry.is_dir():
                if _match_path(entry.relative_to(root_path), exclude_folders):
                    continue
            if entry.is_file():
                file_paths.append(entry)
    return file_paths, root_path


def filter_and_pair_paths(
    file_paths,
    root_path,
    *,
    filter_opts,
    pair_opts,
    search_opts,
):
    """Apply filtering and optional pairing to ``file_paths``.

    ``filter_opts`` and ``pair_opts`` are sub-dictionaries of the main
    configuration and contain all options related to filtering and file
    pairing respectively.
    """

    pairing_enabled = pair_opts.get('enabled')
    source_exts = tuple(e.lower() for e in (pair_opts.get('source_extensions') or []))
    header_exts = tuple(e.lower() for e in (pair_opts.get('header_extensions') or []))
    include_mismatched = pair_opts.get('include_mismatched', False)

    allowed_extensions = tuple(
        e.lower() for e in (search_opts.get('allowed_extensions') or [])
    )
    if pairing_enabled:
        allowed_extensions = source_exts + header_exts

    exclude_conf = filter_opts.get('exclusions', {})
    exclude_filenames = exclude_conf.get('filenames') or []
    exclude_extensions = tuple(
        e.lower() for e in (exclude_conf.get('extensions') or [])
    )

    inclusion_groups = filter_opts.get('inclusion_groups', {})
    include_filenames = set()
    for group_conf in inclusion_groups.values():
        if group_conf.get('enabled'):
            include_filenames.update(group_conf.get('filenames') or [])

    filtered = [
        p
        for p in file_paths
        if should_include(
            p,
            root_path,
            exclude_filenames=exclude_filenames,
            exclude_extensions=exclude_extensions,
            allowed_extensions=allowed_extensions,
            include_filenames=include_filenames,
            filter_opts=filter_opts,
        )
    ]
    if not pairing_enabled:
        return filtered
    file_map = {}
    for file_path in filtered:
        file_map.setdefault(file_path.stem, {})[file_path.suffix.lower()] = file_path
    paired = {}
    for stem, stem_files in file_map.items():
        src = next((p for ext, p in stem_files.items() if ext in source_exts), None)
        hdr = next((p for ext, p in stem_files.items() if ext in header_exts), None)
        if src and hdr:
            paired[stem] = [src, hdr]
        elif include_mismatched and (src or hdr):
            paired[stem] = [src or hdr]
    return paired


def handle_file(
    file_path,
    root_path,
    outfile,
    is_first_file,
    *,
    output_opts,
    dry_run,
    config,
):
    """Read, process, and write a single file."""
    if dry_run:
        print(file_path.resolve())
        return is_first_file

    print(f"Processing: {file_path}")
    content = read_file_best_effort(file_path)
    processed_content = process_content(content, config.get('processing', {}))

    include_headers = output_opts.get('include_headers', True)
    no_header_separator = output_opts.get('no_header_separator', '\n\n')
    add_line_numbers_opt = output_opts.get('add_line_numbers', False)
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


def write_files(
    file_paths,
    root_path,
    outfile,
    *,
    config,
    dry_run,
    output_opts,
    is_first_file,
):
    """Iterate through ``file_paths`` and write their contents."""
    for file_path in file_paths:
        is_first_file = handle_file(
            file_path,
            root_path,
            outfile,
            is_first_file,
            output_opts=output_opts,
            dry_run=dry_run,
            config=config,
        )
    return is_first_file


def find_and_combine_files(config, output_path, dry_run=False):
    """Find, filter, and combine files based on the provided configuration."""
    search_opts = config.get('search', {})
    filter_opts = config.get('filters', {})
    output_opts = config.get('output', {})
    pair_opts = config.get('pairing', {})

    exclude_folders = filter_opts.get('exclusions', {}).get('folders') or []

    pairing_enabled = pair_opts.get('enabled')
    root_folders = search_opts.get('root_folders') or []
    recursive = search_opts.get('recursive', True)

    out_folder = None
    if pairing_enabled:
        out_folder = Path(output_path)
        if not dry_run:
            out_folder.mkdir(parents=True, exist_ok=True)

    outfile_ctx = nullcontext() if pairing_enabled or dry_run else open(output_path, 'w', encoding='utf8')
    with outfile_ctx as outfile:
        is_first_file = True
        for root_folder in root_folders:
            all_paths, root_path = collect_file_paths(
                root_folder, recursive, exclude_folders
            )
            if not all_paths:
                continue
            final_paths = filter_and_pair_paths(
                all_paths,
                root_path,
                filter_opts=filter_opts,
                pair_opts=pair_opts,
                search_opts=search_opts,
            )
            if pairing_enabled:
                for stem, paths in final_paths.items():
                    out_file = out_folder / f"{stem}.combined"
                    pair_ctx = nullcontext() if dry_run else open(out_file, 'w', encoding='utf8')
                    with pair_ctx as pair_out:
                        write_files(
                            paths,
                            root_path,
                            pair_out,
                            config=config,
                            dry_run=dry_run,
                            output_opts=output_opts,
                            is_first_file=True,
                        )
            else:
                is_first_file = write_files(
                    final_paths,
                    root_path,
                    outfile,
                    config=config,
                    dry_run=dry_run,
                    output_opts=output_opts,
                    is_first_file=is_first_file,
                )


def main():
    """Main function to parse arguments and run the tool."""
    parser = argparse.ArgumentParser(description="Combine files into a single text file based on a YAML configuration.")
    parser.add_argument("config_file", help="Path to the YAML configuration file (e.g., config.yml)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="List files to be processed without writing output")
    args = parser.parse_args()

    try:
        config = load_config(args.config_file)
    except (ConfigNotFoundError, InvalidConfigError) as e:
        print(e)
        sys.exit(1)

    pairing_enabled = config.get('pairing', {}).get('enabled')
    output_conf = config.get('output', {})
    if pairing_enabled:
        output_path = output_conf.get('folder', '.')
    else:
        output_path = output_conf.get('file', 'combined_files.txt')

    find_and_combine_files(config, output_path, dry_run=args.dry_run)
    if not args.dry_run:
        print(
            f"\nDone. Combined files have been written to '{output_path}'."
        )
    else:
        print("\nDry run complete.")


if __name__ == "__main__":
    main()
