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
    FILENAME_PLACEHOLDER,
    DEFAULT_OUTPUT_FILENAME,
)


def _fnmatch_casefold(name, pattern):
    """Case-insensitive ``fnmatch`` using Unicode casefolding."""
    return fnmatch.fnmatchcase(name.casefold(), pattern.casefold())


def load_config(config_path):
    """Load and validate the YAML configuration file."""
    nested_required = {
        'search': ['root_folders'],
    }
    return load_and_validate_config(config_path, nested_required=nested_required)


def _match_path(relative_path, patterns):
    """Return True if ``relative_path`` matches any glob ``patterns``."""
    if not patterns:
        return False
    rel_str = relative_path.as_posix()
    parts = relative_path.parts
    for pattern in patterns:
        if _fnmatch_casefold(rel_str, pattern):
            return True
        if any(_fnmatch_casefold(part, pattern) for part in parts):
            return True
    return False


def should_include(file_path, relative_path, filter_config):
    """Return ``True`` if ``file_path`` passes all filtering rules."""
    if not file_path.is_file():
        return False
    file_name = file_path.name
    exclude_filenames = filter_config.get('exclude_filenames', [])
    if any(_fnmatch_casefold(file_name, pattern) for pattern in exclude_filenames):
        return False
    suffix = file_path.suffix.lower()
    exclude_extensions = filter_config.get('exclude_extensions')
    if exclude_extensions and suffix in exclude_extensions:
        return False
    allowed_extensions = filter_config.get('allowed_extensions')
    if allowed_extensions and suffix not in allowed_extensions:
        return False
    include_patterns = filter_config.get('include_patterns')
    if include_patterns:
        rel_str = relative_path.as_posix()
        if not any(
            _fnmatch_casefold(file_name, pattern)
            or _fnmatch_casefold(rel_str, pattern)
            for pattern in include_patterns
        ):
            return False
    try:
        file_size = file_path.stat().st_size
        min_size = filter_config.get('min_size_bytes', 0)
        max_size = filter_config.get('max_size_bytes') or float('inf')
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
    *,
    filter_opts,
    pair_opts,
    search_opts,
    root_path,
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
    include_patterns = set()
    for group_conf in inclusion_groups.values():
        if group_conf.get('enabled'):
            include_patterns.update(group_conf.get('filenames') or [])

    filter_config = {
        'exclude_filenames': exclude_filenames,
        'exclude_extensions': exclude_extensions,
        'allowed_extensions': allowed_extensions,
        'include_patterns': include_patterns,
        'min_size_bytes': filter_opts.get('min_size_bytes', 0),
        'max_size_bytes': filter_opts.get('max_size_bytes'),
    }

    filtered = [
        p
        for p in file_paths
        if should_include(p, p.relative_to(root_path), filter_config)
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
    *,
    output_opts,
    dry_run,
    config,
):
    """Read, process, and write a single file."""
    if dry_run:
        print(file_path.resolve())
        return

    print(f"Processing: {file_path}")
    content = read_file_best_effort(file_path)
    processed_content = process_content(content, config.get('processing', {}))

    add_line_numbers_opt = output_opts.get('add_line_numbers', False)
    if add_line_numbers_opt:
        processed_content = add_line_numbers(processed_content)

    relative_path = file_path.relative_to(root_path)
    header_template = output_opts.get(
        'header_template', f"{FILENAME_PLACEHOLDER}:\n```\n"
    )
    footer_template = output_opts.get(
        'footer_template', "\n```\n\n"
    )
    if header_template:
        header_text = header_template.replace(
            FILENAME_PLACEHOLDER, str(relative_path)
        )
        outfile.write(header_text)
    outfile.write(processed_content)
    if footer_template:
        footer_text = footer_template.replace(
            FILENAME_PLACEHOLDER, str(relative_path)
        )
        outfile.write(footer_text)


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
    if pairing_enabled and output_path:
        out_folder = Path(output_path)
        if not dry_run:
            out_folder.mkdir(parents=True, exist_ok=True)

    outfile_ctx = nullcontext() if pairing_enabled or dry_run else open(output_path, 'w', encoding='utf8')
    with outfile_ctx as outfile:
        for root_folder in root_folders:
            all_paths, root_path = collect_file_paths(
                root_folder, recursive, exclude_folders
            )
            if not all_paths:
                continue
            final_paths = filter_and_pair_paths(
                all_paths,
                filter_opts=filter_opts,
                pair_opts=pair_opts,
                search_opts=search_opts,
                root_path=root_path,
            )
            if pairing_enabled:
                for stem, paths in final_paths.items():
                    out_file = (
                        out_folder / f"{stem}.combined"
                        if out_folder
                        else paths[0].with_suffix('.combined')
                    )
                    if dry_run:
                        print(f"[PAIR {stem}] -> {out_file}")
                        for path in paths:
                            rel_path = path.relative_to(root_path)
                            print(f"  - {rel_path}")
                        continue
                    with open(out_file, 'w', encoding='utf8') as pair_out:
                        for file_path in paths:
                            handle_file(
                                file_path,
                                root_path,
                                pair_out,
                                output_opts=output_opts,
                                dry_run=dry_run,
                                config=config,
                            )
            else:
                for file_path in final_paths:
                    handle_file(
                        file_path,
                        root_path,
                        outfile,
                        output_opts=output_opts,
                        dry_run=dry_run,
                        config=config,
                    )


def main():
    """Main function to parse arguments and run the tool."""
    parser = argparse.ArgumentParser(
        description=(
            "Combine files into one output or pair source/header files into "
            "separate outputs based on a YAML configuration. Use --dry-run "
            "to preview the files and destinations without writing them."
        )
    )
    parser.add_argument(
        "config_file",
        help="Path to the YAML configuration file (e.g., config.yml)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="List files and planned outputs without writing files",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config_file)
    except (ConfigNotFoundError, InvalidConfigError) as e:
        print(e)
        sys.exit(1)

    pairing_enabled = config.get('pairing', {}).get('enabled')
    output_conf = config.get('output', {})
    if pairing_enabled:
        output_path = output_conf.get('folder')
    else:
        output_path = output_conf.get('file', DEFAULT_OUTPUT_FILENAME)

    # Determine output description before the main loop
    if pairing_enabled:
        destination_desc = (
            "alongside their source files"
            if output_path is None
            else f"to '{output_path}'"
        )
    else:
        destination_desc = f"to '{output_path}'"

    find_and_combine_files(config, output_path, dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry run complete.")
    else:
        print(f"\nDone. Combined files have been written {destination_desc}.")


if __name__ == "__main__":
    main()
