import argparse
from typing import Any, Mapping
from contextlib import nullcontext
import fnmatch
import io
import logging
import os
import re
import shutil
import sys
import json
from functools import lru_cache
from pathlib import Path, PurePath


try:  # Optional dependency for progress reporting
    from tqdm import tqdm as _tqdm
except ImportError:  # pragma: no cover - gracefully handle missing tqdm
    _tqdm = None


class _DevNull:
    """A file-like object that discards all writes."""
    def write(self, *args, **kwargs):
        pass

    def flush(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class _SilentProgress:
    """Fallback progress handler used when tqdm is unavailable or disabled."""

    def __init__(self, iterable=None):
        self.iterable = iterable or []

    def __iter__(self):
        yield from self.iterable

    def update(self, *_args, **_kwargs):
        return None

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _progress_enabled(dry_run):
    """Return ``True`` when progress bars should be displayed."""

    if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
        return False
    if dry_run:
        return False
    if os.getenv("CI"):
        return False
    return True


def _progress_bar(iterable=None, *, enabled=True, **kwargs):
    """Return a progress iterator/context manager with graceful fallback."""

    if not enabled or _tqdm is None:
        return _SilentProgress(iterable)
    return _tqdm(iterable, **kwargs)
import utils
from utils import (
    read_file_best_effort,
    process_content,
    load_and_validate_config,
    validate_config,
    add_line_numbers,
    estimate_tokens,
    ConfigNotFoundError,
    InvalidConfigError,
    FILENAME_PLACEHOLDER,
    DEFAULT_OUTPUT_FILENAME,
    _looks_binary,
    DEFAULT_CONFIG,
)


def _fnmatch_casefold(name, pattern):
    """Case-insensitive ``fnmatch`` using Unicode casefolding."""
    return fnmatch.fnmatchcase(name.casefold(), pattern.casefold())


def _normalize_patterns(patterns):
    if not patterns:
        return ()
    if isinstance(patterns, set):
        return tuple(sorted(patterns))
    return tuple(patterns)


@lru_cache(maxsize=4096)
def _matches_file_glob_cached(file_name, relative_path_str, patterns):
    if not patterns:
        return False
    return any(
        _fnmatch_casefold(file_name, pattern)
        or _fnmatch_casefold(relative_path_str, pattern)
        for pattern in patterns
    )


@lru_cache(maxsize=4096)
def _matches_folder_glob_cached(relative_path_str, parts, patterns):
    if not patterns:
        return False
    for pattern in patterns:
        if _fnmatch_casefold(relative_path_str, pattern):
            return True
        if any(_fnmatch_casefold(part, pattern) for part in parts):
            return True
    return False


def should_include(
    file_path: Path,
    relative_path: PurePath,
    filter_opts: Mapping[str, Any],
    search_opts: Mapping[str, Any],
    *,
    return_reason: bool = False,
) -> bool | tuple[bool, str | None]:
    """Return ``True`` if ``file_path`` passes all filtering rules.

    When ``return_reason`` is ``True``, a tuple of ``(bool, reason)`` is
    returned, where ``reason`` is ``'too_large'`` when the file exceeds
    ``max_size_bytes`` and ``None`` otherwise.
    """

    if not file_path.is_file():
        return (False, 'not_file') if return_reason else False

    file_name = file_path.name
    rel_str = relative_path.as_posix()

    exclusions = filter_opts.get('exclusions') or {}
    exclusion_filenames = _normalize_patterns(exclusions.get('filenames'))
    if exclusion_filenames and _matches_file_glob_cached(
        file_name, rel_str, exclusion_filenames
    ):
        return (False, 'excluded') if return_reason else False

    allowed_extensions = search_opts.get('effective_allowed_extensions') or ()
    suffix = file_path.suffix.lower()
    if allowed_extensions and suffix not in allowed_extensions:
        return (False, 'extension') if return_reason else False

    include_patterns = set()
    for group_conf in (filter_opts.get('inclusion_groups') or {}).values():
        if isinstance(group_conf, dict) and group_conf.get('enabled'):
            include_patterns.update(group_conf.get('filenames') or [])

    normalized_includes = _normalize_patterns(include_patterns)
    if normalized_includes and not _matches_file_glob_cached(
        file_name, rel_str, normalized_includes
    ):
        return (False, 'not_included') if return_reason else False

    if filter_opts.get('skip_binary'):
        if _looks_binary(file_path):
            return (False, 'binary') if return_reason else False

    try:
        file_size = file_path.stat().st_size
        min_size = filter_opts.get('min_size_bytes', 0)
        max_size = filter_opts.get('max_size_bytes')
        if max_size in (None, 0):
            max_size = float('inf')
        if not (min_size <= file_size <= max_size):
            reason = 'too_small' if file_size < min_size else 'too_large'
            return (False, reason) if return_reason else False
    except OSError:
        return (False, 'stat_error') if return_reason else False
    return (True, None) if return_reason else True


def collect_file_paths(root_folder, recursive, exclude_folders, progress=None):
    """Return all paths in ``root_folder`` while pruning excluded folders."""
    root_path = Path(root_folder)
    try:
        is_directory = root_path.is_dir()
    except OSError as exc:
        logging.warning(
            "Unable to access root folder '%s': %s. Skipping.", root_folder, exc
        )
        return [], None, 0

    if not is_directory:
        logging.warning("Root folder '%s' does not exist. Skipping.", root_folder)
        return [], None, 0

    file_paths = []
    excluded_folder_count = 0
    exclude_patterns = _normalize_patterns(exclude_folders)
    if progress is None:
        progress = _SilentProgress()

    def _folder_is_excluded(relative_path):
        if not exclude_patterns:
            return False
        rel_str = relative_path.as_posix()
        parts = tuple(relative_path.parts)
        return _matches_folder_glob_cached(rel_str, parts, exclude_patterns)

    if recursive:
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                rel_dir = Path(dirpath).relative_to(root_path)

                original_dir_count = len(dirnames)
                dirnames[:] = [
                    d
                    for d in dirnames
                    if not _folder_is_excluded(rel_dir / d)
                ]
                excluded_folder_count += original_dir_count - len(dirnames)

                for name in filenames:
                    file_paths.append(Path(dirpath) / name)
                    progress.update(1)
        except OSError as exc:
            logging.warning(
                "Error while traversing '%s': %s. Partial results returned.",
                root_folder,
                exc,
            )
    else:
        try:
            for entry in root_path.iterdir():
                if entry.is_dir():
                    if _folder_is_excluded(entry.relative_to(root_path)):
                        excluded_folder_count += 1
                        continue
                if entry.is_file():
                    file_paths.append(entry)
                    progress.update(1)
        except OSError as exc:
            logging.warning(
                "Error while listing '%s': %s. Partial results returned.",
                root_folder,
                exc,
            )
    return file_paths, root_path, excluded_folder_count


def filter_file_paths(
    file_paths,
    *,
    filter_opts,
    search_opts,
    root_path,
    record_size_exclusions=False,
    create_backups=False,
):
    """Apply filtering rules to ``file_paths`` and return the matches.

    When ``record_size_exclusions`` is ``True`` an additional list of paths
    excluded for exceeding ``max_size_bytes`` is returned.
    """
    filtered = []
    size_excluded = []
    for p in file_paths:
        if p.suffix.lower() == '.bak' and create_backups:
            continue
        if record_size_exclusions:
            include, reason = should_include(
                p,
                p.relative_to(root_path),
                filter_opts,
                search_opts,
                return_reason=True,
            )
        else:
            include = should_include(
                p,
                p.relative_to(root_path),
                filter_opts,
                search_opts,
            )
            reason = None
        if include:
            filtered.append(p)
        elif record_size_exclusions and reason == 'too_large':
            size_excluded.append(p)

    if record_size_exclusions:
        return filtered, size_excluded
    return filtered


_INVALID_SLUG_CHARS_RE = re.compile(r'[^0-9A-Za-z._-]+')


def _slugify_relative_dir(relative_dir):
    """Return a filesystem-safe slug for ``relative_dir`` preserving structure."""

    if relative_dir in ('', '.'):  # Treat the project root specially.
        return 'root'

    parts = relative_dir.split('/')
    slugged_parts = []
    for part in parts:
        cleaned = _INVALID_SLUG_CHARS_RE.sub('-', part.strip())
        cleaned = cleaned.casefold()
        cleaned = re.sub(r'-{2,}', '-', cleaned)
        cleaned = cleaned.strip('-')
        slugged_parts.append(cleaned or 'unnamed')
    return '/'.join(slugged_parts)


def _render_paired_filename(
    template: str,
    stem: str,
    source_path: Path | None,
    header_path: Path | None,
    relative_dir: PurePath,
) -> str:
    """Render the paired filename template with placeholders."""

    source_ext = source_path.suffix if source_path else ''
    header_ext = header_path.suffix if header_path else ''
    dir_value = relative_dir.as_posix()
    dir_slug = _slugify_relative_dir(dir_value)

    placeholders = {
        'STEM': stem,
        'SOURCE_EXT': source_ext,
        'HEADER_EXT': header_ext,
        'DIR': dir_value,
        'DIR_SLUG': dir_slug,
    }

    def _to_format_placeholder(match):
        name = match.group(1)
        if name not in placeholders:
            raise ValueError(
                f"Unknown placeholder '{{{{{name}}}}}' in paired filename template"
            )
        return '{' + name + '}'

    format_template = re.sub(r"{{(\w+)}}", _to_format_placeholder, template)

    try:
        rendered = format_template.format(**placeholders)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(
            f"Missing value for placeholder '{{{{{missing}}}}}' in paired filename template"
        ) from exc

    return rendered


def _path_without_suffix(file_path, root_path):
    try:
        relative = file_path.relative_to(root_path)
    except ValueError:
        relative = file_path
    return relative.with_suffix("")


def _group_paths_by_stem_suffix(file_paths, *, root_path):
    """Group ``file_paths`` by stem and suffix for pairing logic."""

    grouped = {}
    for file_path in file_paths:
        try:
            relative = file_path.relative_to(root_path)
        except ValueError:
            relative = None

        stem_path = (relative or file_path).with_suffix("")
        if relative is not None and len(stem_path.parts) > 1:
            stem_path = Path(*stem_path.parts[1:])

        stem = stem_path
        grouped.setdefault(stem, {}).setdefault(file_path.suffix.lower(), []).append(
            file_path
        )
    return grouped


def _select_preferred_path(ext_map, preferred_exts):
    """Return the path matching the first extension in ``preferred_exts``."""

    for ext in preferred_exts:
        if ext in ext_map:
            candidates = ext_map[ext]
            if len(candidates) == 1:
                return candidates[0]
            continue
    return None


def _pair_files(filtered_paths, source_exts, header_exts, include_mismatched, *, root_path):
    """Return a mapping of stems to paired file paths."""

    file_map = _group_paths_by_stem_suffix(filtered_paths, root_path=root_path)
    paired = {}
    for pairing_key, stem_files in file_map.items():
        src = _select_preferred_path(stem_files, source_exts)
        hdr = _select_preferred_path(stem_files, header_exts)
        if src and hdr:
            pair = []
            for path in (src, hdr):
                if path not in pair:
                    pair.append(path)
            pair_key = _path_without_suffix(src or hdr, root_path)
            paired[pair_key] = pair
        elif include_mismatched and (src or hdr):
            lone = [p for p in (src or hdr,) if p]
            if lone:
                pair_key = _path_without_suffix(lone[0], root_path)
                paired[pair_key] = lone
    return paired


def _process_paired_files(
    paired_paths,
    *,
    template,
    source_exts,
    header_exts,
    root_path,
    out_folder,
    processor,
    processing_bar,
    dry_run,
    estimate_tokens=False,
    size_excluded=None,
    global_header=None,
    global_footer=None,
):
    """Process paired files and write combined outputs."""

    size_excluded_set = set(size_excluded or [])
    for pairing_key, paths in paired_paths.items():
        stem = Path(pairing_key).name
        ext_map = {p.suffix.lower(): [p] for p in paths}
        source_path = _select_preferred_path(ext_map, source_exts)
        header_path = _select_preferred_path(ext_map, header_exts)

        primary_path = source_path or header_path or paths[0]
        try:
            relative_dir = primary_path.relative_to(root_path).parent
        except ValueError:
            relative_dir = primary_path.parent

        out_filename = _render_paired_filename(
            template,
            stem,
            source_path,
            header_path,
            relative_dir=relative_dir,
        )
        out_path = Path(out_filename)
        if out_path.is_absolute():
            raise InvalidConfigError(
                "Paired filename template must produce a relative path"
            )

        if out_folder:
            out_file = out_folder / out_path
        else:
            out_file = primary_path.parent / out_path

        if dry_run:
            logging.info("[PAIR %s] -> %s", stem, out_file)
            for path in paths:
                try:
                    rel_path = path.relative_to(root_path)
                except ValueError:
                    rel_path = path
                logging.info("  - %s", rel_path)
            continue

        if estimate_tokens:
            pair_out_ctx = _DevNull()
        else:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            pair_out_ctx = open(out_file, 'w', encoding='utf8')

        with pair_out_ctx as pair_out:
            if global_header and not estimate_tokens:
                pair_out.write(global_header)

            if primary_path in size_excluded_set:
                processor.write_max_size_placeholder(primary_path, root_path, pair_out)
                if processing_bar:
                    processing_bar.update(len(paths))
            else:
                for file_path in paths:
                    if file_path in size_excluded_set:
                        processor.write_max_size_placeholder(
                            file_path, root_path, pair_out
                        )
                    else:
                        processor.process_and_write(
                            file_path,
                            root_path,
                            pair_out,
                        )
                    if processing_bar:
                        processing_bar.update(1)

            if global_footer and not estimate_tokens:
                pair_out.write(global_footer)


class FileProcessor:
    """Process files according to configuration and write them to an output.

    Parameters
    ----------
    config : dict
        Parsed configuration mapping containing ``processing`` and output
        settings used to drive file handling.
    output_opts : dict
        Options that control how processed content is emitted, including
        header/footer templates and whether to include line numbers.
    dry_run : bool, optional
        When ``True``, only log the files that would be processed without
        performing any writes.
    """

    def __init__(self, config, output_opts, dry_run=False, estimate_tokens=False):
        self.config = config
        self.output_opts = output_opts or {}
        self.dry_run = dry_run
        self.estimate_tokens = estimate_tokens
        self.processing_opts = config.get('processing', {}) or {}
        self.apply_in_place = bool(self.processing_opts.get('apply_in_place'))
        if self.apply_in_place:
            self.create_backups = bool(
                self.processing_opts.get('create_backups', True)
            )
        else:
            self.create_backups = False

    def _make_bar(self, **kwargs):
        return _progress_bar(enabled=_progress_enabled(self.dry_run), **kwargs)

    def _write_with_templates(self, outfile, content, relative_path):
        """Write ``content`` with configured header/footer templates."""

        header_template = self.output_opts.get(
            'header_template', utils.DEFAULT_CONFIG['output']['header_template']
        )
        footer_template = self.output_opts.get(
            'footer_template', utils.DEFAULT_CONFIG['output']['footer_template']
        )

        if header_template not in (None, ""):
            header_text = header_template.replace(
                FILENAME_PLACEHOLDER, str(relative_path)
            )
            outfile.write(header_text)

        outfile.write(content)

        if footer_template not in (None, ""):
            footer_text = footer_template.replace(
                FILENAME_PLACEHOLDER, str(relative_path)
            )
            outfile.write(footer_text)
    def _backup_file(self, file_path):
        """Create a ``.bak`` backup for ``file_path`` when backups are enabled.

        The backup mirrors the original file using :func:`shutil.copy2` to
        preserve metadata. If ``create_backups`` is ``False`` no action is
        taken. Failures to copy raise :class:`InvalidConfigError` so callers
        can halt processing before overwriting the original content.
        """

        if not self.create_backups:
            return

        backup_path = Path(f"{file_path}.bak")
        try:
            shutil.copy2(file_path, backup_path)
        except OSError as exc:
            raise InvalidConfigError(
                f"Failed to create backup for '{file_path}': {exc}"
            ) from exc

    def process_and_write(self, file_path, root_path, outfile, output_format='text'):
        """Read, process, and write a single file.

        Returns
        -------
        tuple[int, bool]
            A tuple containing (token_count, is_approximate) for the written content.
        """
        if self.dry_run:
            logging.info(file_path.resolve())
            return 0, True

        logging.debug("Processing: %s", file_path)
        content = read_file_best_effort(file_path)
        processed_content = process_content(content, self.processing_opts)
        if self.apply_in_place and processed_content != content and not self.estimate_tokens:
            logging.info("Updating in place: %s", file_path)
            self._backup_file(file_path)
            file_path.write_text(processed_content, encoding='utf8')

        relative_path = file_path.relative_to(root_path)

        if not self.estimate_tokens:
            if output_format == 'json':
                entry = {
                    "path": relative_path.as_posix(),
                    "content": processed_content
                }
                json.dump(entry, outfile)
            else:
                if self.output_opts.get('add_line_numbers', False):
                    processed_content = add_line_numbers(processed_content)
                self._write_with_templates(outfile, processed_content, relative_path)

        # Estimate tokens on the final processed content
        return estimate_tokens(processed_content)

    def write_max_size_placeholder(self, file_path, root_path, outfile, output_format='text'):
        """Write the placeholder for files skipped for exceeding max size.

        Returns
        -------
        tuple[int, bool]
            A tuple containing (token_count, is_approximate) for the placeholder.
        """

        if self.dry_run:
            return 0, True

        placeholder = self.output_opts.get('max_size_placeholder')
        if not placeholder:
            return 0, True

        relative_path = file_path.relative_to(root_path)
        rendered = placeholder.replace(FILENAME_PLACEHOLDER, str(relative_path))

        if not self.estimate_tokens:
            if output_format == 'json':
                entry = {
                    "path": relative_path.as_posix(),
                    "content": rendered
                }
                json.dump(entry, outfile)
            else:
                self._write_with_templates(outfile, rendered, relative_path)

        return estimate_tokens(rendered)


def find_and_combine_files(config, output_path, dry_run=False, clipboard=False, output_format='text', estimate_tokens=False):
    """Find, filter, and combine files based on the provided configuration."""
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'total_tokens': 0,
        'token_count_is_approx': False
    }
    search_opts = config.get('search', {})
    filter_opts = config.get('filters', {})
    output_opts = config.get('output', {})
    pair_opts = config.get('pairing', {})

    exclude_folders = filter_opts.get('exclusions', {}).get('folders') or []

    pairing_enabled = pair_opts.get('enabled')
    root_folders = search_opts.get('root_folders') or []
    recursive = search_opts.get('recursive', True)

    if clipboard and pairing_enabled:
        raise InvalidConfigError("Clipboard mode is only available when pairing is disabled.")

    if output_format == 'json' and pairing_enabled:
        raise InvalidConfigError("JSON format is not compatible with paired output.")

    if not pairing_enabled and not dry_run and not estimate_tokens and not clipboard and output_path is None:
        raise InvalidConfigError(
            "'output.file' must be set when pairing is disabled and clipboard mode is off."
        )

    out_folder = None
    if pairing_enabled and output_path:
        out_folder = Path(output_path)
        if not dry_run and not estimate_tokens:
            out_folder.mkdir(parents=True, exist_ok=True)

    clipboard_buffer = io.StringIO() if clipboard else None

    if estimate_tokens:
        outfile_ctx = _DevNull()
    else:
        outfile_ctx = (
            nullcontext(clipboard_buffer)
            if pairing_enabled or dry_run or clipboard
            else open(output_path, 'w', encoding='utf8')
        )

    # We only want true dry-run behavior (skipping reading) if we are NOT estimating tokens.
    processor_dry_run = dry_run and not estimate_tokens
    processor = FileProcessor(config, output_opts, dry_run=processor_dry_run, estimate_tokens=estimate_tokens)

    total_excluded_folders = 0
    with outfile_ctx as outfile:
        global_header = output_opts.get('global_header_template')
        global_footer = output_opts.get('global_footer_template')

        # Only write global headers for text output
        if not pairing_enabled and not dry_run and not estimate_tokens and global_header and output_format == 'text':
            outfile.write(global_header)

        if not pairing_enabled and not dry_run and not estimate_tokens and output_format == 'json':
            outfile.write('[')

        first_item = True

        for root_folder in root_folders:
            discovery_bar = processor._make_bar(
                desc=f"Discovering in {root_folder}",
                unit="file",
                leave=False,
            )
            try:
                all_paths, root_path, excluded_count = collect_file_paths(
                    root_folder, recursive, exclude_folders, progress=discovery_bar
                )
            finally:
                discovery_bar.close()
            total_excluded_folders += excluded_count
            if not all_paths:
                continue

            source_exts = tuple(
                e.lower() for e in (pair_opts.get('source_extensions') or [])
            )
            header_exts = tuple(
                e.lower() for e in (pair_opts.get('header_extensions') or [])
            )
            record_size_exclusions = bool(
                output_opts.get('max_size_placeholder')
            ) and not dry_run

            filtered_result = filter_file_paths(
                all_paths,
                filter_opts=filter_opts,
                search_opts=search_opts,
                root_path=root_path,
                record_size_exclusions=record_size_exclusions,
                create_backups=processor.create_backups,
            )
            if record_size_exclusions:
                filtered_paths, size_excluded = filtered_result
            else:
                filtered_paths = filtered_result
                size_excluded = []
            if processor.create_backups:
                filtered_paths = [
                    p for p in filtered_paths if p.suffix.lower() != '.bak'
                ]
                size_excluded = [
                    p for p in size_excluded if p.suffix.lower() != '.bak'
                ]
            processing_bar = processor._make_bar(
                total=(
                    len(filtered_paths) + len(size_excluded)
                    if (filtered_paths or size_excluded)
                    else None
                ),
                desc="Processing files",
                unit="file",
            )
            for p in filtered_paths:
                stats['total_files'] += 1
                try:
                    stats['total_size_bytes'] += p.stat().st_size
                except OSError:
                    pass
                ext = p.suffix.lower() or '.no_extension'
                stats['files_by_extension'][ext] = stats['files_by_extension'].get(ext, 0) + 1

            if pairing_enabled:
                include_mismatched = pair_opts.get('include_mismatched', False)
                pairing_inputs = filtered_paths
                if record_size_exclusions:
                    pairing_inputs = [*filtered_paths, *size_excluded]
                paired_paths = _pair_files(
                    pairing_inputs,
                    source_exts,
                    header_exts,
                    include_mismatched,
                    root_path=root_path,
                )
                template = (
                    output_opts.get('paired_filename_template')
                    or '{{STEM}}.combined'
                )
                _process_paired_files(
                    paired_paths,
                    template=template,
                    source_exts=source_exts,
                    header_exts=header_exts,
                    root_path=root_path,
                    out_folder=out_folder,
                    processor=processor,
                    processing_bar=processing_bar,
                    dry_run=dry_run,
                    estimate_tokens=estimate_tokens,
                    size_excluded=size_excluded,
                    global_header=global_header,
                    global_footer=global_footer,
                )
            else:
                if record_size_exclusions:
                    filtered_set = set(filtered_paths)
                    size_excluded_set = set(size_excluded)
                    ordered_paths = [
                        p
                        for p in all_paths
                        if p in filtered_set or p in size_excluded_set
                    ]
                else:
                    ordered_paths = filtered_paths

                for file_path in ordered_paths:
                    if output_format == 'json' and not dry_run and not estimate_tokens:
                        if not first_item:
                            outfile.write(',')
                        first_item = False

                    token_count = 0
                    is_approx = True
                    if record_size_exclusions and file_path in size_excluded_set:
                        try:
                            rel_path = file_path.relative_to(root_path)
                        except ValueError:
                            rel_path = file_path
                        logging.debug(
                            "File exceeds max size; writing placeholder: %s", rel_path
                        )
                        token_count, is_approx = processor.write_max_size_placeholder(
                            file_path, root_path, outfile, output_format=output_format
                        )
                    else:
                        token_count, is_approx = processor.process_and_write(
                            file_path,
                            root_path,
                            outfile,
                            output_format=output_format
                        )

                    if not dry_run or estimate_tokens:
                        stats['total_tokens'] += token_count
                        if is_approx:
                            stats['token_count_is_approx'] = True

                    processing_bar.update(1)

            processing_bar.close()

        # Write global footer only for text output
        if not pairing_enabled and not dry_run and not estimate_tokens and global_footer and output_format == 'text':
            outfile.write(global_footer)

        if not pairing_enabled and not dry_run and not estimate_tokens and output_format == 'json':
            outfile.write(']')

    stats['excluded_folder_count'] = total_excluded_folders

    if clipboard and clipboard_buffer is not None:
        import pyperclip

        combined_output = clipboard_buffer.getvalue()
        pyperclip.copy(combined_output)
        logging.info("Copied combined output to clipboard.")

    return stats


def main():
    """Main function to parse arguments and run the tool."""
    parser = argparse.ArgumentParser(
        description=(
            "Combine source code files into a single document or organized pairs. "
            "Great for LLM context, documentation, or code review."
        )
    )

    # Positional arguments (standard)
    parser.add_argument(
        "config_file",
        nargs="?",
        help="The YAML file with your settings (e.g., config.yml) OR a directory path to scan using defaults.",
    )

    # Configuration Group
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--init",
        action="store_true",
        help="Generate a default configuration file (sourcecombine.yml) in the current directory.",
    )
    config_group.add_argument(
        "--exclude-file",
        action="append",
        default=[],
        help="Exclude a file (glob pattern). Can be used multiple times. Overrides/appends to config.",
    )
    config_group.add_argument(
        "--exclude-folder",
        action="append",
        default=[],
        help="Exclude a folder (glob pattern). Can be used multiple times. Overrides/appends to config.",
    )

    # Output Options Group
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output",
        "-o",
        help="Save to a specific file or folder, ignoring the setting in your config file.",
    )
    output_group.add_argument(
        "--clipboard",
        "-c",
        action="store_true",
        help="Copy the result to your clipboard instead of saving to a file. (Single-file mode only)",
    )
    output_group.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Choose the output format. 'json' produces a JSON array of file objects. (Single-file mode only)",
    )

    # Runtime Options Group
    runtime_group = parser.add_argument_group("Runtime Options")
    runtime_group.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="See what files will be processed without actually writing anything.",
    )
    runtime_group.add_argument(
        "--estimate-tokens",
        "-e",
        action="store_true",
        help="Calculate token counts without writing output files (slower than dry-run).",
    )
    runtime_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show extra details to help solve problems.",
    )

    args = parser.parse_args()

    # Configure logging *immediately* based on -v.
    # This ensures logging is set up *before* load_and_validate_config (which logs)
    # is called, preventing a race condition that locks the log level at WARNING.
    prelim_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=prelim_level, format='%(levelname)s: %(message)s')

    if args.init:
        target_config = Path("sourcecombine.yml")
        if target_config.exists():
            logging.error("Config file '%s' already exists. Aborting init.", target_config)
            sys.exit(1)

        template_path = Path(__file__).resolve().parent / "config.template.yml"
        if template_path.exists():
            try:
                shutil.copy2(template_path, target_config)
                logging.info("Created default configuration at %s", target_config.resolve())
            except OSError as exc:
                logging.error("Failed to copy template: %s", exc)
                sys.exit(1)
        else:
            logging.warning("Template not found at %s; creating minimal config.", template_path)
            try:
                with open(target_config, 'w', encoding='utf-8') as f:
                    import yaml
                    f.write("# Default SourceCombine Configuration\n")
                    yaml.dump(utils.DEFAULT_CONFIG, f, sort_keys=False)
                logging.info("Created minimal configuration at %s", target_config.resolve())
            except OSError as exc:
                logging.error("Failed to write config: %s", exc)
                sys.exit(1)
        sys.exit(0)

    config_path = args.config_file
    config = None
    nested_required = {
        'search': ['root_folders'],
    }

    if config_path and Path(config_path).is_dir():
        # Directory mode: Construct config in-memory
        logging.info("Using directory '%s' as root with default settings.", config_path)
        config = {'search': {'root_folders': [config_path]}}
        try:
            validate_config(
                config,
                defaults=DEFAULT_CONFIG,
                nested_required=nested_required,
                source="<directory-arg>"
            )
        except InvalidConfigError as e:
            logging.error("Invalid configuration: %s", e)
            logging.debug("Configuration validation traceback:", exc_info=True)
            sys.exit(1)
    else:
        # Config file mode (explicit or auto-discovered)
        if not config_path:
            # Auto-discovery
            defaults = ['sourcecombine.yml', 'sourcecombine.yaml', 'config.yml', 'config.yaml']
            for default in defaults:
                if Path(default).is_file():
                    config_path = default
                    logging.info("Auto-discovered config file: %s", config_path)
                    break

            if not config_path:
                # Fallback to current directory if no config found
                logging.info(
                    "No config file found (checked: %s). Scanning current directory '.' with default settings.",
                    ", ".join(defaults),
                )
                config_path = "."
                # Redirect flow to directory mode logic
                # Since we are modifying config_path to '.', we need to handle it
                # similar to the 'directory mode' block above, but we are already past it.
                # So we construct the config here.
                config = {'search': {'root_folders': [config_path]}}
                try:
                    validate_config(
                        config,
                        defaults=DEFAULT_CONFIG,
                        nested_required=nested_required,
                        source="<default-cwd>"
                    )
                except InvalidConfigError as e:
                    logging.error("Invalid configuration: %s", e)
                    logging.debug("Configuration validation traceback:", exc_info=True)
                    sys.exit(1)

        if config is None:
            try:
                config = load_and_validate_config(
                    config_path, nested_required=nested_required
                )
            except ConfigNotFoundError as e:
                logging.error(
                    "Could not find the configuration file '%s'. "
                    "Check the filename and your current working directory: %s",
                    config_path,
                    Path.cwd(),
                )
                logging.debug("Missing configuration details:", exc_info=True)
                sys.exit(1)
            except InvalidConfigError as e:
                logging.error("Invalid configuration: %s", e)
                logging.debug("Configuration validation traceback:", exc_info=True)
                sys.exit(1)

    # Re-configure level based on config, *unless* -v was used.
    # The -v (DEBUG) flag always overrides the config file's setting.
    if not args.verbose:
        level_str = config.get('logging', {}).get('level', 'INFO')
        log_level = getattr(logging, level_str.upper(), logging.INFO)
        # Set the level on the *root logger* since basicConfig was already called
        logging.getLogger().setLevel(log_level)

    # Inject CLI exclusions into config
    if args.exclude_file or args.exclude_folder:
        filters = config.setdefault('filters', {})
        exclusions = filters.setdefault('exclusions', {})

        if args.exclude_file:
            filenames = exclusions.setdefault('filenames', [])
            for pattern in args.exclude_file:
                # Validate/sanitize the pattern
                sanitized = utils.validate_glob_pattern(pattern, context="CLI --exclude-file")
                filenames.append(sanitized)
            logging.debug("Added CLI file exclusions: %s", args.exclude_file)

        if args.exclude_folder:
            folders = exclusions.setdefault('folders', [])
            for pattern in args.exclude_folder:
                sanitized = utils.validate_glob_pattern(pattern, context="CLI --exclude-folder")
                folders.append(sanitized)
            logging.debug("Added CLI folder exclusions: %s", args.exclude_folder)

    pairing_conf = config.get('pairing') or {}
    output_conf = config.get('output') or {}
    config['pairing'] = pairing_conf
    config['output'] = output_conf

    if args.output:
        if pairing_conf.get('enabled'):
            output_conf['folder'] = args.output
        else:
            output_conf['file'] = args.output

    pairing_enabled = pairing_conf.get('enabled')
    if pairing_enabled:
        output_path = output_conf.get('folder')
    else:
        output_path = output_conf.get('file', DEFAULT_OUTPUT_FILENAME)

    # Determine output description before the main loop
    if args.clipboard:
        destination_desc = "to clipboard"
    elif pairing_enabled:
        destination_desc = (
            "alongside their source files"
            if output_path is None
            else f"to '{output_path}'"
        )
    else:
        destination_desc = f"to '{output_path}'"

    mode_desc = "Pairing" if pairing_enabled else "Single File"
    logging.info("SourceCombine starting. Mode: %s", mode_desc)
    if args.estimate_tokens:
        logging.info("Output: Token estimation only (no files will be written)")
    else:
        logging.info("Output: Writing %s", destination_desc)

    try:
        stats = find_and_combine_files(
            config,
            output_path,
            dry_run=args.dry_run,
            clipboard=args.clipboard,
            output_format=args.format,
            estimate_tokens=args.estimate_tokens,
        )
    except InvalidConfigError as exc:
        logging.error(exc, exc_info=True)
        sys.exit(1)

    if args.dry_run:
        logging.info("Dry run complete.")
    else:
        logging.info("Done.")

    if stats:
        total_files = stats['total_files']
        total_size_mb = stats['total_size_bytes'] / (1024 * 1024)
        ext_summary = ", ".join(
            f"{ext}: {count}"
            for ext, count in sorted(stats['files_by_extension'].items())
        )
        excluded_folders = stats.get('excluded_folder_count', 0)

        if args.dry_run:
            summary_title = "Dry-Run Summary"
        elif args.estimate_tokens:
            summary_title = "Token Estimation Summary"
        else:
            summary_title = "Execution Summary"

        print(f"\n--- {summary_title} ---", file=sys.stderr)
        print(f"  Total Files:      {total_files}", file=sys.stderr)
        print(f"  Total Size:       {total_size_mb:.2f} MB", file=sys.stderr)

        # Show token counts for single-file mode OR if estimate_tokens was requested
        if not pairing_enabled and (not args.dry_run or args.estimate_tokens):
            token_count = stats.get('total_tokens', 0)
            is_approx = stats.get('token_count_is_approx', False)
            approx_indicator = "~" if is_approx else ""
            print(f"  Token Count:      {approx_indicator}{token_count}", file=sys.stderr)
            if is_approx:
                print("    (Install 'tiktoken' for accurate counts)", file=sys.stderr)

        if ext_summary:
            print(f"  Extensions:       {ext_summary}", file=sys.stderr)

        if excluded_folders > 0:
            print(f"  Excluded Folders: {excluded_folders}", file=sys.stderr)
        print("-" * (len(summary_title) + 8), file=sys.stderr)


if __name__ == "__main__":
    main()
