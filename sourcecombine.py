import argparse
import time
from typing import Any, Mapping
from contextlib import nullcontext
import copy
import fnmatch
import io
import logging
import os
import re
import shutil
import sys
import json
import textwrap
from xml.sax.saxutils import escape as xml_escape
from functools import lru_cache
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath


__version__ = "0.5.0"


class _LazyColor:
    """A helper for ANSI colors that respects isatty and NO_COLOR."""

    def __init__(self, code):
        self.code = code

    def __str__(self):
        # We check isatty and NO_COLOR on every string conversion so it
        # works correctly even if sys.stdout/stderr is redirected mid-run or
        # in tests.
        stream = sys.stderr if sys.stderr.isatty() else sys.stdout
        if stream.isatty() and not os.getenv("NO_COLOR"):
            return self.code
        return ""

    def __format__(self, format_spec):
        return format(str(self), format_spec)


C_BOLD = _LazyColor("\033[1m")
C_DIM = _LazyColor("\033[90m")
C_GREEN = _LazyColor("\033[32m")
C_YELLOW = _LazyColor("\033[33m")
C_RED = _LazyColor("\033[31m")
C_CYAN = _LazyColor("\033[36m")
C_RESET = _LazyColor("\033[0m")

# Regex for stripping ANSI escape codes to calculate display width accurately
_ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class CLILogFormatter(logging.Formatter):
    """A clean logging formatter for the CLI.

    Removes the 'INFO:' prefix for standard messages and adds semantic colors
    to WARNING and ERROR levels.
    """

    def format(self, record):
        if record.levelno == logging.WARNING:
            prefix = f"{C_YELLOW}WARNING:{C_RESET} "
        elif record.levelno >= logging.ERROR:
            prefix = f"{C_RED}ERROR:{C_RESET} "
        elif record.levelno == logging.DEBUG:
            prefix = f"{C_DIM}DEBUG:{C_RESET} "
        else:
            prefix = ""

        # For multi-line messages, ensure the prefix is only on the first line
        message = record.getMessage()
        if "\n" in message and prefix:
            # Strip ANSI from prefix for correct indentation calculation
            raw_prefix = _ANSI_ESCAPE.sub('', str(prefix))
            indent = " " * len(raw_prefix)
            lines = message.splitlines()
            return f"{prefix}{lines[0]}\n" + "\n".join(f"{indent}{line}" for line in lines[1:])

        return f"{prefix}{message}"


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


def _get_rel_path(path, root_path):
    """Return ``path`` relative to ``root_path`` with fallback to original."""
    try:
        return path.relative_to(root_path)
    except ValueError:
        return path


def _format_metadata_summary(meta: Mapping[str, Any]) -> str:
    """Return a formatted string representing file or folder metadata."""
    parts = []
    if 'files' in meta:
        count = meta['files']
        parts.append(f"{count} {'file' if count == 1 else 'files'}")
    if 'size' in meta:
        parts.append(utils.format_size(meta['size']))
    if 'lines' in meta and meta['lines'] > 0:
        parts.append(f"{meta['lines']:,} {'line' if meta['lines'] == 1 else 'lines'}")
    if 'tokens' in meta and meta['tokens'] > 0:
        parts.append(f"{meta['tokens']:,} tokens")

    return f" ({', '.join(parts)})" if parts else ""


@lru_cache(maxsize=128)
def _get_replacement_pattern(keys):
    """Compile a regex pattern from a tuple of keys, sorted by length."""
    return re.compile("|".join(re.escape(k) for k in keys))


def _render_single_pass(template, replacements):
    """Replace many placeholders in a template in a single pass.

    Placeholders are matched in order of descending length to ensure that
    longer, more specific markers (like {{DIR_SLUG}}) are preferred over
    shorter prefixes (like {{DIR}}).
    """
    if not template or not replacements:
        return template or ""

    # Sort keys by length descending to prevent partial prefix matching
    sorted_keys = tuple(sorted(replacements.keys(), key=len, reverse=True))
    pattern = _get_replacement_pattern(sorted_keys)
    return pattern.sub(lambda m: str(replacements[m.group(0)]), template)


def _render_template(template, relative_path, size=None, tokens=None, lines=None, escape_func=None):
    """Replace placeholders in a template with file metadata.

    The placeholders include FILENAME, EXT, STEM, DIR, DIR_SLUG, SIZE,
    TOKENS, and LINE_COUNT.
    """
    if not template:
        return ""

    filename = relative_path.as_posix()
    ext = relative_path.suffix.lstrip(".") or ""
    stem = relative_path.stem
    parent_dir = relative_path.parent.as_posix()
    dir_slug = _slugify_relative_dir(parent_dir)

    if escape_func:
        filename = escape_func(filename)
        ext = escape_func(ext)
        stem = escape_func(stem)
        parent_dir = escape_func(parent_dir)

    replacements = {
        FILENAME_PLACEHOLDER: filename,
        "{{EXT}}": ext,
        "{{STEM}}": stem,
        "{{DIR}}": parent_dir,
        "{{DIR_SLUG}}": dir_slug,
    }

    if size is not None:
        replacements["{{SIZE}}"] = utils.format_size(size)
    if tokens is not None:
        replacements["{{TOKENS}}"] = f"{tokens:,}"
    if lines is not None:
        replacements["{{LINE_COUNT}}"] = f"{lines:,}"

    return _render_single_pass(template, replacements)


def _render_global_template(template, stats):
    """Replace placeholders in a global template with project metadata.

    The placeholders include FILE_COUNT, TOTAL_SIZE, TOTAL_TOKENS, and TOTAL_LINES.
    """
    if not template:
        return ""

    file_count = stats.get('total_files', 0)
    total_size = utils.format_size(stats.get('total_size_bytes', 0))
    total_tokens = stats.get('total_tokens', 0)
    total_lines = stats.get('total_lines', 0)
    is_approx = stats.get('token_count_is_approx', False)
    token_str = f"{'~' if is_approx else ''}{total_tokens:,}"

    replacements = {
        "{{FILE_COUNT}}": str(file_count),
        "{{TOTAL_SIZE}}": total_size,
        "{{TOTAL_TOKENS}}": token_str,
        "{{TOTAL_LINES}}": f"{total_lines:,}",
    }

    return _render_single_pass(template, replacements)


def _normalize_patterns(patterns):
    if not patterns:
        return ()
    return tuple(sorted({p.casefold() for p in patterns}))


@lru_cache(maxsize=4096)
def _matches_file_glob_cached(file_name, relative_path_str, patterns):
    file_name_cf = file_name.casefold()
    rel_path_cf = relative_path_str.casefold()
    return any(
        fnmatch.fnmatchcase(file_name_cf, p)
        or fnmatch.fnmatchcase(rel_path_cf, p)
        for p in patterns
    )


@lru_cache(maxsize=4096)
def _matches_folder_glob_cached(relative_path_str, parts, patterns):
    rel_path_cf = relative_path_str.casefold()
    parts_cf = tuple(p.casefold() for p in parts)
    for pattern in patterns:
        if fnmatch.fnmatchcase(rel_path_cf, pattern):
            return True
        if any(fnmatch.fnmatchcase(p_cf, pattern) for p_cf in parts_cf):
            return True
    return False


def should_include(
    file_path: Path | None,
    relative_path: PurePath,
    filter_opts: Mapping[str, Any],
    search_opts: Mapping[str, Any],
    *,
    return_reason: bool = False,
    abs_output_path: Path = None,
    virtual_content: str | bytes | None = None,
) -> bool | tuple[bool, str | None]:
    """Return ``True`` if ``file_path`` (or ``relative_path``) passes filtering rules.

    When ``return_reason`` is ``True``, it returns a tuple of ``(bool, reason)``.
    Possible reason codes include: 'not_file', 'output_file', 'excluded',
    'extension', 'not_included', 'binary', 'too_small', 'too_large', and
    'stat_error'.
    """

    if file_path is not None and not file_path.is_file():
        return (False, 'not_file') if return_reason else False

    # Automatically exclude the tool's own output file to prevent recursion.
    if file_path is not None and abs_output_path and file_path.resolve() == abs_output_path:
        return (False, 'output_file') if return_reason else False

    file_name = relative_path.name
    rel_str = relative_path.as_posix()

    exclusions = filter_opts.get('exclusions') or {}
    exclusion_filenames = _normalize_patterns(exclusions.get('filenames'))
    if exclusion_filenames and _matches_file_glob_cached(
        file_name, rel_str, exclusion_filenames
    ):
        return (False, 'excluded') if return_reason else False

    exclusion_folders = _normalize_patterns(exclusions.get('folders'))
    if exclusion_folders and _matches_folder_glob_cached(
        rel_str, relative_path.parts, exclusion_folders
    ):
        return (False, 'excluded') if return_reason else False

    allowed_extensions = search_opts.get('effective_allowed_extensions') or ()
    suffix = relative_path.suffix.lower()
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
        if file_path is not None:
            if _looks_binary(file_path):
                return (False, 'binary') if return_reason else False
        elif virtual_content is not None:
            sample_bytes = (
                virtual_content
                if isinstance(virtual_content, bytes)
                else virtual_content.encode('utf-8', errors='replace')
            )
            if _looks_binary(sample=sample_bytes):
                return (False, 'binary') if return_reason else False

    try:
        file_size = None
        if file_path is not None:
            file_size = file_path.stat().st_size
        elif virtual_content is not None:
            file_size = (
                len(virtual_content)
                if isinstance(virtual_content, bytes)
                else len(virtual_content.encode('utf-8', errors='replace'))
            )

        if file_size is not None:
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
    """Return all paths in ``root_folder`` while pruning excluded folders.

    If ``root_folder`` is a file, it returns a list containing only that file.
    """
    root_path = Path(root_folder)
    try:
        if root_path.is_file():
            if progress is not None:
                progress.update(1)
            return [root_path], root_path.parent, 0
        is_directory = root_path.is_dir()
    except OSError as exc:
        logging.warning(
            "Could not access the folder '%s': %s. Skipping.", root_folder, exc
        )
        return [], None, 0

    if not is_directory:
        logging.warning("The folder '%s' was not found. Skipping.", root_folder)
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
        parts = relative_path.parts
        excluded = _matches_folder_glob_cached(rel_str, parts, exclude_patterns)
        if excluded:
            logging.debug("Skipping folder: %s", rel_str)
        return excluded

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

                # Sort for deterministic output
                dirnames.sort()
                filenames.sort()

                for name in filenames:
                    file_paths.append(Path(dirpath) / name)
                    progress.update(1)
        except OSError as exc:
            logging.warning(
                "An error occurred while scanning '%s': %s. Some files may be missing from the output.",
                root_folder,
                exc,
            )
    else:
        try:
            entries = sorted(root_path.iterdir(), key=lambda e: e.name)
            for entry in entries:
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
    stats=None,
    abs_output_path=None,
):
    """Apply filtering rules to ``file_paths`` and return the matches.

    When ``record_size_exclusions`` is ``True`` an additional list of paths
    excluded for exceeding ``max_size_bytes`` is returned.
    """
    filtered = []
    size_excluded = []
    reasons = stats.get('filter_reasons') if stats is not None else None

    for p in file_paths:
        if p.suffix.lower() == '.bak' and create_backups:
            if reasons is not None:
                reasons['excluded_bak'] = reasons.get('excluded_bak', 0) + 1
            continue
        rel_p = _get_rel_path(p, root_path)

        include, reason = should_include(
            p,
            rel_p,
            filter_opts,
            search_opts,
            return_reason=True,
            abs_output_path=abs_output_path,
        )

        if include:
            filtered.append(p)
        else:
            if reason:
                logging.debug("Skipping %s: %s", rel_p, reason)
                if reasons is not None:
                    reasons[reason] = reasons.get(reason, 0) + 1
            if record_size_exclusions and reason == 'too_large':
                size_excluded.append(p)

    if record_size_exclusions:
        return filtered, size_excluded
    return filtered


_INVALID_SLUG_CHARS_RE = re.compile(r'[^0-9A-Za-z._-]+')


def _slugify_relative_dir(relative_dir):
    """Return a filesystem-safe simplified name for ``relative_dir`` preserving structure."""

    if relative_dir in ('', '.'):  # Treat the project root specially.
        return 'root'

    parts = relative_dir.split('/')
    slugged_parts = []
    for part in parts:
        cleaned = _INVALID_SLUG_CHARS_RE.sub('-', part.strip())
        cleaned = cleaned.casefold()
        cleaned = re.sub(r'-{2,}', '-', cleaned)
        cleaned = cleaned.strip('-')

        if cleaned == '.':
            cleaned = 'dot'
        elif cleaned == '..':
            cleaned = 'dot-dot'

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
            pair = [src]
            if hdr != src:
                pair.append(hdr)
            pair_key = _get_rel_path(src, root_path).with_suffix("")
            paired[pair_key] = pair
        elif include_mismatched and (src or hdr):
            path = src or hdr
            pair_key = _get_rel_path(path, root_path).with_suffix("")
            paired[pair_key] = [path]
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
    stats=None,
):
    """Process paired files and write combined outputs."""

    size_excluded_set = set(size_excluded or [])
    for pairing_key, paths in paired_paths.items():
        stem = Path(pairing_key).name
        ext_map = {p.suffix.lower(): [p] for p in paths}
        source_path = _select_preferred_path(ext_map, source_exts)
        header_path = _select_preferred_path(ext_map, header_exts)

        primary_path = source_path or header_path or paths[0]
        relative_dir = _get_rel_path(primary_path, root_path).parent

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
                rel_path = _get_rel_path(path, root_path)
                logging.info("  - %s", rel_path)
                if stats is not None:
                    stats['top_files'].append((0, path.stat().st_size if path.exists() else 0, rel_path.as_posix()))
            continue

        if estimate_tokens:
            pair_out_ctx = _DevNull()
        else:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            pair_out_ctx = open(out_file, 'w', encoding='utf8', newline='')

        with pair_out_ctx as pair_out:
            if global_header and not estimate_tokens:
                pair_out.write(global_header)

            if primary_path in size_excluded_set:
                token_count, is_approx, line_count = processor.write_max_size_placeholder(primary_path, root_path, pair_out)
                if stats is not None:
                    stats['total_tokens'] = stats.get('total_tokens', 0) + token_count
                    stats['total_lines'] = stats.get('total_lines', 0) + line_count
                    if is_approx:
                        stats['token_count_is_approx'] = True
                    stats['top_files'].append((token_count, primary_path.stat().st_size if primary_path.exists() else 0, _get_rel_path(primary_path, root_path).as_posix()))
                if processing_bar:
                    processing_bar.update(len(paths))
            else:
                for file_path in paths:
                    if file_path in size_excluded_set:
                        token_count, is_approx, line_count = processor.write_max_size_placeholder(
                            file_path, root_path, pair_out
                        )
                    else:
                        token_count, is_approx, line_count = processor.process_and_write(
                            file_path,
                            root_path,
                            pair_out,
                        )
                    if stats is not None:
                        stats['total_tokens'] = stats.get('total_tokens', 0) + token_count
                        stats['total_lines'] = stats.get('total_lines', 0) + line_count
                        if is_approx:
                            stats['token_count_is_approx'] = True
                        stats['top_files'].append((token_count, file_path.stat().st_size if file_path.exists() else 0, _get_rel_path(file_path, root_path).as_posix()))
                    if processing_bar:
                        processing_bar.update(1)

            if global_footer and not estimate_tokens:
                pair_out.write(global_footer)


def _update_file_stats(stats, file_path):
    stats['total_files'] += 1
    try:
        stats['total_size_bytes'] += file_path.stat().st_size
    except OSError:
        pass
    ext = file_path.suffix.lower() or '.no_extension'
    stats['files_by_extension'][ext] = stats['files_by_extension'].get(ext, 0) + 1


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

    def __init__(self, config, output_opts, dry_run=False, estimate_tokens=False, output_format='text'):
        self.config = config
        self.output_opts = output_opts or {}
        self.dry_run = dry_run
        self.estimate_tokens = estimate_tokens
        self.output_format = output_format
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

    def _write_with_templates(self, outfile, content, relative_path, size=None, tokens=None, lines=None):
        """Write ``content`` with configured header/footer templates."""

        header_template = self.output_opts.get(
            'header_template', utils.DEFAULT_CONFIG['output']['header_template']
        )
        footer_template = self.output_opts.get(
            'footer_template', utils.DEFAULT_CONFIG['output']['footer_template']
        )

        escape_func = xml_escape if self.output_format == 'xml' else None

        outfile.write(_render_template(header_template, relative_path, size=size, tokens=tokens, lines=lines, escape_func=escape_func))
        outfile.write(content)
        outfile.write(_render_template(footer_template, relative_path, size=size, tokens=tokens, lines=lines, escape_func=escape_func))
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

    def process_and_write(self, file_path, root_path, outfile, cached_content=None):
        """Read, process, and write a single file.

        Returns
        -------
        tuple[int, bool, int]
            A tuple containing (token_count, is_approximate, line_count) for the written content.
        """
        if self.dry_run:
            logging.info(_get_rel_path(file_path, root_path))
            return 0, True, 0

        logging.debug("Processing: %s", file_path)
        if cached_content is not None:
            processed_content = cached_content
        else:
            content = read_file_best_effort(file_path)
            processed_content = process_content(content, self.processing_opts)
            if self.apply_in_place and processed_content != content and not self.estimate_tokens:
                logging.info("Updating in place: %s", file_path)
                self._backup_file(file_path)
                file_path.write_text(processed_content, encoding='utf8', newline='')

        relative_path = _get_rel_path(file_path, root_path)
        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Estimate tokens on the final processed content
        token_count, is_approx = utils.estimate_tokens(processed_content)
        line_count = utils.count_lines(processed_content)

        if not self.estimate_tokens:
            if self.output_format in ('json', 'jsonl'):
                entry = {
                    "path": relative_path.as_posix(),
                    "size_bytes": file_size,
                    "tokens": token_count,
                    "tokens_is_approx": is_approx,
                    "lines": line_count,
                    "content": processed_content
                }
                json.dump(entry, outfile)
                if self.output_format == 'jsonl':
                    outfile.write('\n')
            else:
                if self.output_opts.get('add_line_numbers', False):
                    processed_content = add_line_numbers(processed_content)
                if self.output_format == 'xml':
                    processed_content = xml_escape(processed_content)
                self._write_with_templates(outfile, processed_content, relative_path, size=file_size, tokens=token_count, lines=line_count)

        return token_count, is_approx, line_count

    def write_max_size_placeholder(self, file_path, root_path, outfile):
        """Write the placeholder for files skipped for exceeding max size.

        Returns
        -------
        tuple[int, bool, int]
            A tuple containing (token_count, is_approximate, line_count) for the placeholder.
        """

        if self.dry_run:
            logging.info(_get_rel_path(file_path, root_path))
            return 0, True, 0

        placeholder = self.output_opts.get('max_size_placeholder')
        if not placeholder:
            return 0, True, 0

        relative_path = _get_rel_path(file_path, root_path)
        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Estimate tokens on the placeholder content (but the placeholder itself might have tokens placeholder)
        # For max_size_placeholder, it's a bit tricky because we don't know the token count of the placeholder
        # until it's rendered. But we want to support {{SIZE}} in it.
        rendered = _render_template(placeholder, relative_path, size=file_size)

        token_count, is_approx = utils.estimate_tokens(rendered)
        line_count = utils.count_lines(rendered)

        if not self.estimate_tokens:
            if self.output_format in ('json', 'jsonl'):
                entry = {
                    "path": relative_path.as_posix(),
                    "size_bytes": file_size,
                    "tokens": token_count,
                    "tokens_is_approx": is_approx,
                    "lines": line_count,
                    "content": rendered
                }
                json.dump(entry, outfile)
                if self.output_format == 'jsonl':
                    outfile.write('\n')
            else:
                if self.output_format == 'xml':
                    rendered = xml_escape(rendered)
                self._write_with_templates(outfile, rendered, relative_path, size=file_size, tokens=token_count, lines=line_count)

        return token_count, is_approx, line_count


def _generate_tree_string(paths, root_path, output_format='text', include_header=True, metadata=None):
    """Generate a tree structure string of file paths."""
    # Convert to relative paths
    try:
        rel_paths = [p.relative_to(root_path) for p in paths]
    except ValueError:
        # Fallback if any path is not relative to root (should ideally not happen)
        rel_paths = paths

    # Map relative paths back to original paths for metadata lookup
    rel_to_orig = {p_rel: p_orig for p_rel, p_orig in zip(rel_paths, paths)}

    # Build the tree dictionary
    # { 'folder': { 'subfolder': { 'file.txt': {} } } }
    tree = {}
    for p in rel_paths:
        parts = p.parts
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    # Pre-calculate folder-level statistics
    folder_metadata = {}
    if metadata:
        for rel_p, orig_p in rel_to_orig.items():
            file_meta = metadata.get(orig_p)
            if not file_meta:
                continue
            for parent in rel_p.parents:
                if parent not in folder_metadata:
                    folder_metadata[parent] = {'size': 0, 'tokens': 0, 'lines': 0, 'files': 0}
                folder_metadata[parent]['size'] += file_meta.get('size', 0)
                folder_metadata[parent]['tokens'] += file_meta.get('tokens', 0)
                folder_metadata[parent]['lines'] += file_meta.get('lines', 0)
                folder_metadata[parent]['files'] += 1

    lines = []
    if include_header:
        if output_format == 'markdown':
            lines.append("## Project Structure")
            lines.append("```text")
        else:
            lines.append("Project Structure:")

    def _add_node(node, prefix="", rel_parts=()):
        items = sorted(node.keys())
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "

            current_rel_parts = rel_parts + (item,)
            current_rel_path = Path(*current_rel_parts)
            children = node[item]

            meta_str = ""
            if metadata:
                if children:
                    # It's a folder - show totals
                    if current_rel_path in folder_metadata:
                        meta_str = f"{C_DIM}{_format_metadata_summary(folder_metadata[current_rel_path])}{C_RESET}"
                elif current_rel_path in rel_to_orig:
                    # It's a file - show individual stats
                    orig_path = rel_to_orig[current_rel_path]
                    file_meta = metadata.get(orig_path)
                    if file_meta:
                        meta_str = f"{C_DIM}{_format_metadata_summary(file_meta)}{C_RESET}"

            lines.append(f"{prefix}{connector}{item}{meta_str}")

            # If the item has children (it's a folder), recurse
            if children:
                extension = "    " if is_last else "│   "
                _add_node(children, prefix + extension, current_rel_parts)

    # Add the root folder name first
    root_meta_str = ""
    if metadata and Path('.') in folder_metadata:
        root_meta_str = f"{C_DIM}{_format_metadata_summary(folder_metadata[Path('.')])}{C_RESET}"

    lines.append(f"{root_path.name or str(root_path)}/{root_meta_str}")
    _add_node(tree)

    if include_header:
        if output_format == 'markdown':
            lines.append("```\n")
        else:
            lines.append("-" * 20 + "\n")

    return "\n".join(lines)


def _generate_table_of_contents(files, output_format='text', metadata=None):
    """Generate a Table of Contents string for the provided files.

    files: List of (Path, Path) tuples representing (file_path, root_path).
    """
    if not files:
        return ""

    toc_lines = []

    if output_format == 'markdown':
        toc_lines.append("## Table of Contents")
        for file_path, root_path in files:
            rel_path = _get_rel_path(file_path, root_path)
            posix_rel_path = rel_path.as_posix()

            meta_str = ""
            if metadata and file_path in metadata:
                meta_str = _format_metadata_summary(metadata[file_path])

            # Create a basic anchor link.
            slug = re.sub(r'[^a-z0-9 _-]', '', posix_rel_path.lower()).replace(' ', '-')

            toc_lines.append(f"- [{posix_rel_path}](#{slug}){meta_str}")
        toc_lines.append("")

    else: # text
        toc_lines.append("Table of Contents:")
        for file_path, root_path in files:
            rel_path = _get_rel_path(file_path, root_path)

            meta_str = ""
            if metadata and file_path in metadata:
                meta_str = _format_metadata_summary(metadata[file_path])

            toc_lines.append(f"- {rel_path.as_posix()}{meta_str}")
        toc_lines.append("\n" + "-" * 20 + "\n")

    return "\n".join(toc_lines)


def find_and_combine_files(
    config,
    output_path,
    dry_run=False,
    clipboard=False,
    output_format='text',
    estimate_tokens=False,
    list_files=False,
    tree_view=False,
    explicit_files=None,
):
    """Find, filter, and combine files based on the provided configuration."""
    stats = {
        'total_discovered': 0,
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'total_tokens': 0,
        'total_lines': 0,
        'token_count_is_approx': False,
        'budget_exceeded': False,
        'top_files': [],
        'max_total_tokens': config.get('filters', {}).get('max_total_tokens', 0),
        'filter_reasons': {},
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

    if output_path == '-' and pairing_enabled:
        raise InvalidConfigError("You cannot send output to your terminal when pairing files.")

    if output_format in ('json', 'jsonl') and pairing_enabled:
        raise InvalidConfigError(f"You cannot use {output_format.upper()} format when pairing files.")

    # Apply default Markdown templates if requested and not overridden
    if output_format == 'markdown':
        default_header = utils.DEFAULT_CONFIG['output']['header_template']
        default_footer = utils.DEFAULT_CONFIG['output']['footer_template']

        current_header = output_opts.get('header_template')
        current_footer = output_opts.get('footer_template')

        # If current matches default (or is None/empty/missing), override with Markdown defaults
        if not current_header or current_header == default_header:
            output_opts['header_template'] = "## {{FILENAME}}\n\n```{{EXT}}\n"

        if not current_footer or current_footer == default_footer:
            output_opts['footer_template'] = "\n```\n\n"

    # Apply default XML templates if requested and not overridden
    if output_format == 'xml':
        default_header = utils.DEFAULT_CONFIG['output']['header_template']
        default_footer = utils.DEFAULT_CONFIG['output']['footer_template']
        default_global_header = utils.DEFAULT_CONFIG['output']['global_header_template']
        default_global_footer = utils.DEFAULT_CONFIG['output']['global_footer_template']

        if not output_opts.get('header_template') or output_opts.get('header_template') == default_header:
            output_opts['header_template'] = '<file path="{{FILENAME}}">\n'
        if not output_opts.get('footer_template') or output_opts.get('footer_template') == default_footer:
            output_opts['footer_template'] = "\n</file>\n"
        if not output_opts.get('global_header_template') or output_opts.get('global_header_template') == default_global_header:
            output_opts['global_header_template'] = "<repository>\n"
        if not output_opts.get('global_footer_template') or output_opts.get('global_footer_template') == default_global_footer:
            output_opts['global_footer_template'] = "\n</repository>\n"

    if not pairing_enabled and not dry_run and not estimate_tokens and not clipboard and not list_files and not tree_view and output_path is None:
        raise InvalidConfigError(
            "You must set an output file in your configuration or use the --output flag."
        )

    abs_output_path = None
    if not pairing_enabled and output_path and output_path != '-':
        abs_output_path = Path(output_path).resolve()

    out_folder = None
    if pairing_enabled and output_path:
        out_folder = Path(output_path)
        if not dry_run and not estimate_tokens and not list_files and not tree_view:
            out_folder.mkdir(parents=True, exist_ok=True)

    clipboard_buffer = io.StringIO() if clipboard else None

    if estimate_tokens or list_files or tree_view:
        outfile_ctx = _DevNull()
    elif pairing_enabled or dry_run or clipboard:
        outfile_ctx = nullcontext(clipboard_buffer)
    elif output_path == '-':
        outfile_ctx = nullcontext(sys.stdout)
    else:
        outfile_ctx = open(output_path, 'w', encoding='utf8', newline='')

    # We only want true dry-run behavior (skipping reading) if we are NOT estimating tokens.
    processor_dry_run = (dry_run and not estimate_tokens) or list_files or tree_view
    processor = FileProcessor(
        config,
        output_opts,
        dry_run=processor_dry_run,
        estimate_tokens=estimate_tokens,
        output_format=output_format
    )

    total_excluded_folders = 0

    # Store all items to process for when combining many files into one to enable global TOC
    # List of (file_path, root_path, is_size_excluded)
    all_single_mode_items = []
    # Store all pairs across all roots
    # List of (root_path, pair_key, paths)
    all_paired_items = []
    # Track all files excluded by size across all roots
    all_size_excluded = set()
    # Metadata for TOC and Tree: {Path: {'size': int, 'tokens': int, 'mtime': float, 'depth': int}}
    file_metadata = {}

    with outfile_ctx as outfile:
        global_header = output_opts.get('global_header_template')
        global_footer = output_opts.get('global_footer_template')

        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and output_format == 'json':
            outfile.write('[')

        first_item = True

        iteration_targets = []
        if explicit_files:
            # Bypass finding: process specific files relative to the current folder
            # (root_path, all_paths, excluded_folder_count)
            iteration_targets.append((Path.cwd(), explicit_files, 0))
        else:
            # Standard finding from root folders
            for root_folder in root_folders:
                finding_bar = processor._make_bar(
                    desc=f"Finding in {root_folder}",
                    unit="file",
                    leave=False,
                )
                try:
                    paths, root, excluded = collect_file_paths(
                        root_folder, recursive, exclude_folders, progress=finding_bar
                    )
                finally:
                    finding_bar.close()
                if paths:
                    iteration_targets.append((root, paths, excluded))

        source_exts = tuple(
            e.lower() for e in (pair_opts.get('source_extensions') or [])
        )
        header_exts = tuple(
            e.lower() for e in (pair_opts.get('header_extensions') or [])
        )

        for root_path, all_paths, excluded_count in iteration_targets:
            total_excluded_folders += excluded_count
            if excluded_count > 0:
                stats['filter_reasons']['excluded_folder'] = stats['filter_reasons'].get('excluded_folder', 0) + excluded_count
            stats['total_discovered'] += len(all_paths)
            record_size_exclusions = bool(output_opts.get('max_size_placeholder'))

            filtered_result = filter_file_paths(
                all_paths,
                filter_opts=filter_opts,
                search_opts=search_opts,
                root_path=root_path,
                record_size_exclusions=record_size_exclusions,
                create_backups=processor.create_backups,
                stats=stats,
                abs_output_path=abs_output_path,
            )
            if record_size_exclusions:
                filtered_paths, size_excluded = filtered_result
                all_size_excluded.update(size_excluded)
            else:
                filtered_paths = filtered_result
                size_excluded = []

            if list_files or tree_view:
                paths_to_list = []
                if pairing_enabled:
                    include_mismatched = pair_opts.get('include_mismatched', False)
                    # Use both filtered and size_excluded for pairing listing
                    pairing_inputs = [*filtered_paths, *size_excluded] if record_size_exclusions else filtered_paths

                    paired_paths = _pair_files(
                        pairing_inputs,
                        source_exts,
                        header_exts,
                        include_mismatched,
                        root_path=root_path,
                    )
                    unique_paths = set()
                    for paths in paired_paths.values():
                        unique_paths.update(paths)
                    paths_to_list = sorted(unique_paths)
                else:
                    paths_to_list = filtered_paths
                    if record_size_exclusions and size_excluded:
                        filtered_set = set(filtered_paths)
                        size_excluded_set = set(size_excluded)
                        paths_to_list = [
                            p
                            for p in all_paths
                            if p in filtered_set or p in size_excluded_set
                        ]

                # Apply limit to list/tree
                max_files = filter_opts.get('max_files', 0)
                if max_files > 0:
                    remaining_budget = max_files - stats['total_files']
                    if remaining_budget <= 0:
                        stats['filter_reasons']['file_limit'] = stats['filter_reasons'].get('file_limit', 0) + len(paths_to_list)
                        paths_to_list = []
                        stats['limit_reached'] = True
                        continue
                    elif len(paths_to_list) > remaining_budget:
                        stats['filter_reasons']['file_limit'] = stats['filter_reasons'].get('file_limit', 0) + (len(paths_to_list) - remaining_budget)
                        paths_to_list = paths_to_list[:remaining_budget]
                        stats['limit_reached'] = True

                # Update stats for listed files
                for p in paths_to_list:
                    _update_file_stats(stats, p)

                view_metadata = {}
                for p in paths_to_list:
                    f_size = p.stat().st_size if p.exists() else 0
                    tokens = 0
                    lines = 0
                    is_approx = True

                    if estimate_tokens:
                        content = read_file_best_effort(p)
                        processed = process_content(content, processor.processing_opts)
                        tokens, is_approx = utils.estimate_tokens(processed)
                        lines = utils.count_lines(processed)
                        stats['total_tokens'] += tokens
                        stats['total_lines'] += lines
                        if is_approx:
                            stats['token_count_is_approx'] = True

                    view_metadata[p] = {'size': f_size, 'tokens': tokens, 'lines': lines}
                    stats['top_files'].append((tokens, f_size, _get_rel_path(p, root_path).as_posix()))

                if tree_view:
                    print(_generate_tree_string(paths_to_list, root_path, include_header=False, metadata=view_metadata))
                else:
                    for p in paths_to_list:
                        # Print relative path if possible for cleaner output
                        print(_get_rel_path(p, root_path) if p.is_absolute() else p)
                continue

            # Update stats
            for p in filtered_paths:
                _update_file_stats(stats, p)

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
                for pair_key, paths in paired_paths.items():
                    all_paired_items.append((root_path, pair_key, paths))
            else:
                # Accumulate when combining many files into one
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
                    is_excluded_by_size = False
                    if record_size_exclusions and file_path in size_excluded_set:
                        is_excluded_by_size = True

                    all_single_mode_items.append((file_path, root_path, is_excluded_by_size))

        # End of root_folder loop

        # Metadata and Sorting Pass
        sort_by = output_opts.get('sort_by', 'name')
        sort_reverse = output_opts.get('sort_reverse', False)

        max_total_tokens = filter_opts.get('max_total_tokens', 0)
        needs_metadata = bool(output_opts.get('include_tree') or output_opts.get('table_of_contents'))

        # We need metadata for sorting (except name), budgeting, TOC/Tree, or global placeholders
        global_placeholders = ["{{FILE_COUNT}}", "{{TOTAL_SIZE}}", "{{TOTAL_TOKENS}}", "{{TOTAL_LINES}}"]
        has_global_placeholders = (global_header and any(p in global_header for p in global_placeholders)) or \
                                  (global_footer and any(p in global_footer for p in global_placeholders))

        needs_full_pass = (sort_by != 'name' or max_total_tokens > 0 or needs_metadata or
                           has_global_placeholders or estimate_tokens)

        # Global Sort
        if pairing_enabled:
            if sort_by != 'name' or sort_reverse:
                def get_pair_sort_key(item):
                    root_p, _, paths = item
                    primary_path = paths[0]
                    rel_p = _get_rel_path(primary_path, root_p)

                    if sort_by == 'size':
                        val = primary_path.stat().st_size if primary_path.exists() else 0
                    elif sort_by == 'modified':
                        val = primary_path.stat().st_mtime if primary_path.exists() else 0
                    elif sort_by == 'depth':
                        val = len(rel_p.parts)
                    elif sort_by == 'tokens':
                        content = read_file_best_effort(primary_path)
                        processed = process_content(content, processor.processing_opts)
                        val, _ = utils.estimate_tokens(processed)
                    else:
                        val = rel_p.as_posix()
                    return (val, rel_p.as_posix())

                all_paired_items.sort(key=get_pair_sort_key, reverse=sort_reverse)
        else:
            if sort_by != 'name' or sort_reverse:
                if sort_by in ('name', 'size', 'modified', 'depth'):
                    def get_single_sort_key(item):
                        file_p, root_p, _ = item
                        rel_p = _get_rel_path(file_p, root_p)
                        if sort_by == 'size':
                            val = file_p.stat().st_size if file_p.exists() else 0
                        elif sort_by == 'modified':
                            val = file_p.stat().st_mtime if file_p.exists() else 0
                        elif sort_by == 'depth':
                            val = len(rel_p.parts)
                        else:
                            val = rel_p.as_posix()
                        return (val, rel_p.as_posix())
                    all_single_mode_items.sort(key=get_single_sort_key, reverse=sort_reverse)
                # Note: 'tokens' sort for single-file mode is handled inside the metadata pass below

        # Apply file limit after global sorting
        max_files = filter_opts.get('max_files', 0)
        limit_applied = False
        if max_files > 0:
            if pairing_enabled:
                if len(all_paired_items) > max_files:
                    stats['filter_reasons']['file_limit'] = len(all_paired_items) - max_files
                    all_paired_items = all_paired_items[:max_files]
                    stats['limit_reached'] = True
                    limit_applied = True
            elif sort_by != 'tokens':
                if len(all_single_mode_items) > max_files:
                    stats['filter_reasons']['file_limit'] = len(all_single_mode_items) - max_files
                    all_single_mode_items = all_single_mode_items[:max_files]
                    stats['limit_reached'] = True
                    limit_applied = True

        # Recalculate stats if limit was applied and we aren't doing a full pass anyway
        if limit_applied and not (needs_full_pass and not pairing_enabled and not list_files and not tree_view):
            stats['total_files'] = 0
            stats['total_size_bytes'] = 0
            stats['files_by_extension'] = {}
            if pairing_enabled:
                for _, _, paths in all_paired_items:
                    for p in paths:
                        _update_file_stats(stats, p)
            else:
                for item in all_single_mode_items:
                    _update_file_stats(stats, item[0])

        if needs_full_pass and not pairing_enabled and not list_files and not tree_view:
            budgeted_items = []
            current_tokens = 0
            current_lines = 0
            budget_exceeded = False

            # Account for global header and footer tokens in the budget
            # We estimate these once without placeholders for initial budget.
            if global_header and output_format in ('text', 'markdown', 'xml'):
                current_tokens += utils.estimate_tokens(global_header)[0]
                current_lines += utils.count_lines(global_header)
            if global_footer and output_format in ('text', 'markdown', 'xml'):
                current_tokens += utils.estimate_tokens(global_footer)[0]
                current_lines += utils.count_lines(global_footer)

            # Estimate TOC and Tree tokens if enabled (rough estimation per file)
            if output_format in ('text', 'markdown'):
                if output_opts.get('include_tree'):
                    current_tokens += len(all_single_mode_items) * 12
                if output_opts.get('table_of_contents'):
                    current_tokens += len(all_single_mode_items) * 12

            # If sorting by tokens, we must calculate tokens for all files first
            if sort_by == 'tokens':
                token_data = []
                for item in all_single_mode_items:
                    file_path, root_path, is_excluded_by_size = item
                    rel_p = _get_rel_path(file_path, root_path)
                    if is_excluded_by_size:
                        placeholder = output_opts.get('max_size_placeholder')
                        # Note: 1372-1373 ensures placeholder exists if we are here
                        rendered = _render_template(placeholder, rel_p, size=file_path.stat().st_size if file_path.exists() else 0)
                        tokens, _ = utils.estimate_tokens(rendered)
                    else:
                        content = read_file_best_effort(file_path)
                        processed = process_content(content, processor.processing_opts)
                        tokens, _ = utils.estimate_tokens(processed)
                    token_data.append((tokens, rel_p.as_posix()))

                # Sort by tokens
                # Zip tokens with items to sort them together
                indexed_items = sorted(
                    zip(all_single_mode_items, token_data),
                    key=lambda x: (x[1][0], x[1][1]),
                    reverse=sort_reverse
                )
                all_single_mode_items = [x[0] for x in indexed_items]

            if max_files > 0 and sort_by == 'tokens' and len(all_single_mode_items) > max_files:
                stats['filter_reasons']['file_limit'] = len(all_single_mode_items) - max_files
                all_single_mode_items = all_single_mode_items[:max_files]
                stats['limit_reached'] = True

                # Recalculate stats after truncation
                stats['total_files'] = 0
                stats['total_size_bytes'] = 0
                stats['total_tokens'] = 0
                stats['total_lines'] = 0
                stats['files_by_extension'] = {}
                for item in all_single_mode_items:
                    _update_file_stats(stats, item[0])
                    meta = file_metadata.get(item[0], {})
                    stats['total_tokens'] += meta.get('tokens', 0)
                    stats['total_lines'] += meta.get('lines', 0)

            for i, item in enumerate(all_single_mode_items):
                file_path, root_path, is_excluded_by_size = item
                content_tokens = 0
                content_lines = 0
                processed = None
                file_size = file_path.stat().st_size if file_path.exists() else 0

                rel_p = _get_rel_path(file_path, root_path)

                if is_excluded_by_size:
                    placeholder = output_opts.get('max_size_placeholder')
                    if placeholder:
                        rendered = _render_template(placeholder, rel_p, size=file_size)
                        content_tokens, is_approx = utils.estimate_tokens(rendered)
                        content_lines = utils.count_lines(rendered)
                        if is_approx:
                            stats['token_count_is_approx'] = True
                else:
                    content = read_file_best_effort(file_path)
                    processed = process_content(content, processor.processing_opts)
                    if processor.apply_in_place and processed != content and not estimate_tokens and not dry_run:
                        logging.info("Updating in place: %s", file_path)
                        processor._backup_file(file_path)
                        file_path.write_text(processed, encoding='utf8', newline='')
                    content_tokens, is_approx = utils.estimate_tokens(processed)
                    content_lines = utils.count_lines(processed)
                    if is_approx:
                        stats['token_count_is_approx'] = True

                # Store content tokens and lines for TOC/Tree
                file_metadata[file_path] = {
                    'size': file_size,
                    'tokens': content_tokens,
                    'lines': content_lines
                }

                # Account for header/footer templates in the budget
                h_template = output_opts.get('header_template', utils.DEFAULT_CONFIG['output']['header_template'])
                f_template = output_opts.get('footer_template', utils.DEFAULT_CONFIG['output']['footer_template'])

                rendered_h = _render_template(h_template, rel_p, size=file_size, tokens=content_tokens, lines=content_lines)
                rendered_f = _render_template(f_template, rel_p, size=file_size, tokens=content_tokens, lines=content_lines)

                header_tokens = utils.estimate_tokens(rendered_h)[0]
                footer_tokens = utils.estimate_tokens(rendered_f)[0]
                header_lines = utils.count_lines(rendered_h)
                footer_lines = utils.count_lines(rendered_f)

                # Total tokens for this file entry including its boundaries
                entry_tokens = content_tokens + header_tokens + footer_tokens
                entry_lines = content_lines + header_lines + footer_lines

                if max_total_tokens > 0 and current_tokens + entry_tokens > max_total_tokens and current_tokens > 0:
                    budget_exceeded = True
                    stats['filter_reasons']['budget_limit'] = len(all_single_mode_items) - i
                    logging.debug("Budget limit reached; skipping %d remaining files.", len(all_single_mode_items) - i)
                    break

                current_tokens += entry_tokens
                current_lines += entry_lines
                budgeted_items.append((file_path, root_path, is_excluded_by_size, processed))

            all_single_mode_items = budgeted_items
            stats['budget_exceeded'] = budget_exceeded

            # Recalculate stats based on budgeted items
            stats['total_files'] = 0
            stats['total_size_bytes'] = 0
            stats['total_tokens'] = current_tokens
            stats['total_lines'] = current_lines
            stats['files_by_extension'] = {}
            for item in all_single_mode_items:
                _update_file_stats(stats, item[0])
            budget_pass_performed = True
        else:
            budget_pass_performed = False

        # Process Paired files if enabled
        if pairing_enabled and not list_files and not tree_view:
            processing_bar = processor._make_bar(
                total=sum(len(paths) for _, _, paths in all_paired_items),
                desc="Processing files",
                unit="file",
            )
            template = (
                output_opts.get('paired_filename_template')
                or '{{STEM}}.combined'
            )

            # Group back by root_path for _process_paired_files if needed,
            # or just call it for each pair.
            # Actually, _process_paired_files currently takes a dict of {key: paths}.
            # I'll adapt it or call it per pair.

            # Since we want to support global sorting, we should process in the sorted order.
            for root_path, pair_key, paths in all_paired_items:
                _process_paired_files(
                    {pair_key: paths},
                    template=template,
                    source_exts=source_exts,
                    header_exts=header_exts,
                    root_path=root_path,
                    out_folder=out_folder,
                    processor=processor,
                    processing_bar=processing_bar,
                    dry_run=dry_run,
                    estimate_tokens=estimate_tokens,
                    size_excluded=all_size_excluded,
                    global_header=global_header,
                    global_footer=global_footer,
                    stats=stats,
                )
            processing_bar.close()

        # Process Single File Mode items (including Global Header, TOC, Tree, and Footer)
        if not pairing_enabled and not list_files and not tree_view:
            # Add global header/footer tokens if budget pass was skipped
            if not budget_pass_performed and (not dry_run or estimate_tokens) and output_format in ('text', 'markdown', 'xml'):
                if global_header:
                    tokens, is_approx = utils.estimate_tokens(global_header)
                    lines = utils.count_lines(global_header)
                    stats['total_tokens'] += tokens
                    stats['total_lines'] += lines
                    if is_approx:
                        stats['token_count_is_approx'] = True
                if global_footer:
                    tokens, is_approx = utils.estimate_tokens(global_footer)
                    lines = utils.count_lines(global_footer)
                    stats['total_tokens'] += tokens
                    stats['total_lines'] += lines
                    if is_approx:
                        stats['token_count_is_approx'] = True

            # Write global header after metadata pass to ensure placeholders are filled
            if global_header and not dry_run and not estimate_tokens and output_format in ('text', 'markdown', 'xml'):
                outfile.write(_render_global_template(global_header, stats))

            if output_opts.get('include_tree') and output_format in ('text', 'markdown'):
                root_to_paths = {}
                for item in all_single_mode_items:
                    file_path, root_path = item[0], item[1]
                    if root_path not in root_to_paths:
                        root_to_paths[root_path] = []
                    root_to_paths[root_path].append(file_path)

                if root_to_paths:
                    # Write the section header once
                    tree_header = ""
                    tree_footer = ""
                    if output_format == 'markdown':
                        tree_header = "## Project Structure\n```text\n"
                        tree_footer = "```\n\n"
                    else:
                        tree_header = "Project Structure:\n"
                        tree_footer = "-" * 20 + "\n\n"

                    if not dry_run or estimate_tokens:
                        stats['total_tokens'] += utils.estimate_tokens(tree_header)[0]
                        stats['total_tokens'] += utils.estimate_tokens(tree_footer)[0]
                        stats['total_lines'] += utils.count_lines(tree_header)
                        stats['total_lines'] += utils.count_lines(tree_footer)

                    if not dry_run and not estimate_tokens:
                        outfile.write(tree_header)

                    for root_path, paths in root_to_paths.items():
                        tree_content = _generate_tree_string(
                            paths, root_path, output_format, include_header=False, metadata=file_metadata
                        )
                        if not dry_run or estimate_tokens:
                            token_count, is_approx = utils.estimate_tokens(tree_content)
                            line_count = utils.count_lines(tree_content)
                            stats['total_lines'] += line_count
                            if is_approx:
                                stats['token_count_is_approx'] = True
                        if not dry_run and not estimate_tokens:
                            outfile.write(tree_content + "\n")

                    if not dry_run and not estimate_tokens:
                        outfile.write(tree_footer)

            if output_opts.get('table_of_contents') and output_format in ('text', 'markdown'):
                toc_files = [(item[0], item[1]) for item in all_single_mode_items]
                toc_content = _generate_table_of_contents(toc_files, output_format, metadata=file_metadata)

                if not dry_run or estimate_tokens:
                    token_count, is_approx = utils.estimate_tokens(toc_content)
                    line_count = utils.count_lines(toc_content)
                    stats['total_lines'] += line_count
                    if is_approx:
                        stats['token_count_is_approx'] = True
                if not dry_run and not estimate_tokens:
                    outfile.write(toc_content)

            processing_bar = processor._make_bar(
                total=len(all_single_mode_items),
                desc="Processing files",
                unit="file",
            )

            for item in all_single_mode_items:
                file_path, root_path, is_excluded_by_size = item[:3]
                cached_processed = item[3] if len(item) > 3 else None

                if output_format == 'json' and not dry_run and not estimate_tokens:
                    if not first_item:
                        outfile.write(',')
                    first_item = False

                token_count = 0
                is_approx = True

                if is_excluded_by_size:
                    rel_path = _get_rel_path(file_path, root_path)
                    logging.debug(
                        "File exceeds max size; writing placeholder: %s", rel_path
                    )
                    token_count, is_approx, line_count = processor.write_max_size_placeholder(
                        file_path, root_path, outfile
                    )
                else:
                    token_count, is_approx, line_count = processor.process_and_write(
                        file_path,
                        root_path,
                        outfile,
                        cached_content=cached_processed
                    )

                if not budget_pass_performed and (not dry_run or estimate_tokens):
                    # Total tokens for this file entry include boundaries
                    h_template = output_opts.get('header_template', utils.DEFAULT_CONFIG['output']['header_template'])
                    f_template = output_opts.get('footer_template', utils.DEFAULT_CONFIG['output']['footer_template'])
                    rel_p = _get_rel_path(file_path, root_path)
                    f_size = file_path.stat().st_size if file_path.exists() else 0

                    rendered_h = _render_template(h_template, rel_p, size=f_size, tokens=token_count, lines=line_count)
                    rendered_f = _render_template(f_template, rel_p, size=f_size, tokens=token_count, lines=line_count)

                    header_tokens = utils.estimate_tokens(rendered_h)[0]
                    footer_tokens = utils.estimate_tokens(rendered_f)[0]
                    header_lines = utils.count_lines(rendered_h)
                    footer_lines = utils.count_lines(rendered_f)

                    stats['total_tokens'] += token_count + header_tokens + footer_tokens
                    stats['total_lines'] += line_count + header_lines + footer_lines
                    if is_approx:
                        stats['token_count_is_approx'] = True

                stats['top_files'].append((token_count, file_path.stat().st_size if file_path.exists() else 0, _get_rel_path(file_path, root_path).as_posix()))

                processing_bar.update(1)

            processing_bar.close()

        # Write global footer only for text, markdown, and xml output
        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and global_footer and output_format in ('text', 'markdown', 'xml'):
            outfile.write(_render_global_template(global_footer, stats))

        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and output_format == 'json':
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
    start_time = time.perf_counter()
    parser = argparse.ArgumentParser(
        description=(
            "Combine many files into one document or into pairs. "
            "This tool is helpful for providing better context to AI assistants, "
            "archiving code, or performing code reviews."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              # Combine files in the current folder into 'combined_files.txt'
              python sourcecombine.py

              # Combine files from a specific folder
              python sourcecombine.py src/

              # Use a settings file
              python sourcecombine.py my_config.yml

              # Use settings but override the folders to scan
              python sourcecombine.py my_config.yml project_a/ project_b/

              # Copy the result to your clipboard
              python sourcecombine.py src/ -c

              # Estimate how many tokens the output will use
              python sourcecombine.py -e

              # Skip the 'tests' folder and all '.json' files
              python sourcecombine.py -X tests -x "*.json"
        """),
    )

    # Positional arguments
    parser.add_argument(
        "targets",
        nargs="*",
        metavar="TARGET",
        help=(
            "Folders, files, or a settings file to process. "
            "If you provide a .yml or .yaml file first, the tool will use it for settings."
        ),
    )

    # Configuration Group
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--init",
        action="store_true",
        help="Create a basic 'sourcecombine.yml' file in your current folder to get started.",
    )
    config_group.add_argument(
        "--exclude-file",
        "-x",
        dest="exclude_file",
        action="append",
        default=[],
        help="Skip files that match this pattern (e.g., '*.log'). Use many times to skip more.",
    )
    config_group.add_argument(
        "--exclude-folder",
        "-X",
        dest="exclude_folder",
        action="append",
        default=[],
        help="Skip folders that match this pattern (e.g., 'build'). Use many times to skip more.",
    )
    config_group.add_argument(
        "--include",
        "-i",
        action="append",
        default=[],
        help="Include only files matching this pattern (like '*.py'). You can use this flag many times.",
    )

    # Output Options Group
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output",
        "-o",
        help="Set the output file or folder. This overrides your configuration file.",
    )
    output_group.add_argument(
        "--clipboard",
        "-c",
        action="store_true",
        help="Copy the result to your clipboard instead of saving a file. (Only when combining many files into one)",
    )
    output_group.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "jsonl", "markdown", "xml"],
        help=(
            "Choose the output format. 'json' and 'jsonl' only work when "
            "combining many files into one. 'markdown' and 'xml' formats "
            "automatically add markers like code blocks or tags."
        ),
    )
    output_group.add_argument(
        "--markdown",
        "-m",
        action="store_true",
        help="Shortcut for '--format markdown'.",
    )
    output_group.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Shortcut for '--format json'.",
    )
    output_group.add_argument(
        "--xml",
        "-w",
        action="store_true",
        help="Shortcut for '--format xml'.",
    )
    output_group.add_argument(
        "--line-numbers",
        "-n",
        action="store_true",
        help="Add line numbers to the beginning of each line in the combined output.",
    )
    output_group.add_argument(
        "--toc",
        "-T",
        action="store_true",
        help="Add a Table of Contents with file sizes and token counts to the start of the output. (Only works when combining many files into one in 'text' or 'markdown' formats)",
    )
    output_group.add_argument(
        "--include-tree",
        "-p",
        action="store_true",
        help="Include a visual folder tree with file metadata at the start of the output. (Only when combining many files into one)",
    )
    output_group.add_argument(
        "--compact",
        "-C",
        action="store_true",
        help="Clean up extra spaces and blank lines in the output to save tokens.",
    )
    output_group.add_argument(
        "--sort",
        choices=["name", "size", "modified", "tokens", "depth"],
        help="Sort files by name, size, modified time, token count, or path depth before combining.",
    )
    output_group.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse the sort order.",
    )

    # Preview & Estimation Group
    preview_group = parser.add_argument_group("Preview & Estimation")
    preview_group.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="See which files would be included without writing any files.",
    )
    preview_group.add_argument(
        "--estimate-tokens",
        "-e",
        action="store_true",
        help="Estimate how many tokens the output will use. This is slower because the tool must read every file.",
    )
    preview_group.add_argument(
        "--list-files",
        "-l",
        action="store_true",
        help="Show a list of all files that would be included and then stop.",
    )
    preview_group.add_argument(
        "--tree",
        "-t",
        action="store_true",
        help="Show a visual folder tree of all included files with metadata and then stop.",
    )
    preview_group.add_argument(
        "--limit",
        "-L",
        type=int,
        help="Stop processing after this many files.",
    )

    # Runtime Options Group
    runtime_group = parser.add_argument_group("Runtime Options")
    runtime_group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the tool's version and exit.",
    )
    runtime_group.add_argument(
        "--max-tokens",
        type=int,
        help="Stop adding files once this total token limit is reached. (Only when combining many files into one)",
    )
    runtime_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show extra details to help with troubleshooting.",
    )
    runtime_group.add_argument(
        "--files-from",
        help="Read a list of files from a text file (use '-' for your terminal). This skips folder scanning.",
    )
    runtime_group.add_argument(
        "--extract",
        action="store_true",
        help=(
            "Restore original files and folders from a combined JSON, XML, Markdown, or Text file. "
            "You can read from a file, your terminal ('-'), or your clipboard. Filtering flags "
            "(--include, --exclude-file, --exclude-folder) and preview flags "
            "(--list-files, --tree) are supported."
        ),
    )

    args = parser.parse_args()

    # Configure logging *immediately* based on -v.
    # This ensures logging is set up *before* load_and_validate_config (which logs)
    # is called, preventing a race condition that locks the log level at WARNING.
    prelim_level = logging.DEBUG if args.verbose else logging.INFO

    # Custom logging configuration to use CLILogFormatter
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(CLILogFormatter())
        root_logger.addHandler(handler)
        root_logger.setLevel(prelim_level)



    if args.files_from and args.init:
        logging.error("You cannot use --init and --files-from at the same time.")
        sys.exit(1)

    if args.init:
        target_config = Path("sourcecombine.yml")
        if target_config.exists():
            logging.error("The configuration file '%s' already exists. Stopping.", target_config)
            sys.exit(1)

        template_path = Path(__file__).resolve().parent / "config.template.yml"
        if template_path.exists():
            try:
                shutil.copy2(template_path, target_config)
                logging.info("Created default configuration at %s", target_config.resolve())
            except OSError as exc:
                logging.error("Could not copy the template file: %s", exc)
                sys.exit(1)
        else:
            logging.warning("Template not found at %s; creating a simple configuration.", template_path)
            try:
                with open(target_config, 'w', encoding='utf-8') as f:
                    import yaml
                    f.write("# Default SourceCombine Configuration\n")
                    yaml.dump(utils.DEFAULT_CONFIG, f, sort_keys=False)
                logging.info("Created a simple configuration at %s", target_config.resolve())
            except OSError as exc:
                logging.error("Could not write the configuration file: %s", exc)
                sys.exit(1)
        sys.exit(0)

    targets = args.targets
    config = None
    config_path = None
    remaining_targets = []

    if targets:
        first = targets[0]
        # If the first target is a YAML file, it's our configuration
        # We don't check for existence here so that missing config files
        # trigger a proper "Config not found" error later.
        if first.lower().endswith(('.yml', '.yaml')) and not Path(first).is_dir():
            config_path = first
            remaining_targets = targets[1:]
        else:
            remaining_targets = targets

    # Initially, we don't strictly require root_folders in the config file
    # because we can fall back to the current folder later.
    nested_required = {}

    if not config_path and not remaining_targets:
        # Case 1: No positional targets. Use auto-finding
        defaults = ['sourcecombine.yml', 'sourcecombine.yaml', 'config.yml', 'config.yaml']
        for d in defaults:
            if Path(d).is_file():
                config_path = d
                logging.info("Auto-found config file: %s", config_path)
                break

        if not config_path:
            if args.files_from:
                logging.info("No configuration found. Using default settings with --files-from.")

    # Load config if we found/specified one
    if config_path:
        try:
            config = load_and_validate_config(config_path, nested_required=nested_required)
        except ConfigNotFoundError:
            logging.error("Could not find the configuration file '%s'.", config_path)
            sys.exit(1)
        except InvalidConfigError as e:
            logging.error("The configuration is not valid: %s", e)
            sys.exit(1)

    # Initialize with defaults if no config was loaded
    if config is None:
        config = copy.deepcopy(utils.DEFAULT_CONFIG)

    # Ensure search section exists
    if 'search' not in config:
        config['search'] = {}

    # Apply positional targets or fallback to current folder
    if remaining_targets:
        config['search']['root_folders'] = remaining_targets
    elif not args.files_from:
        if not config.get('search', {}).get('root_folders'):
            if not config_path:
                logging.info(
                    "No config file found. Scanning current folder '.' with default settings."
                )
            else:
                logging.info(
                    "No root folders specified in configuration. Scanning current folder '.'"
                )
            config.setdefault('search', {})['root_folders'] = ["."]

    # Final validation for root_folders
    if not args.files_from:
        try:
            validate_config(config, nested_required={'search': ['root_folders']})
        except InvalidConfigError as e:
            logging.error("The configuration is not valid: %s", e)
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
        if not isinstance(config.get('filters'), dict):
            config['filters'] = {}
        filters = config['filters']

        if not isinstance(filters.get('exclusions'), dict):
            filters['exclusions'] = {}
        exclusions = filters['exclusions']

        if args.exclude_file:
            if not isinstance(exclusions.get('filenames'), list):
                exclusions['filenames'] = []
            filenames = exclusions['filenames']
            for pattern in args.exclude_file:
                # Validate/sanitize the pattern
                sanitized = utils.validate_glob_pattern(pattern, context="CLI --exclude-file")
                filenames.append(sanitized)
            logging.debug("Added CLI file exclusions: %s", args.exclude_file)

        if args.exclude_folder:
            if not isinstance(exclusions.get('folders'), list):
                exclusions['folders'] = []
            folders = exclusions['folders']
            for pattern in args.exclude_folder:
                sanitized = utils.validate_glob_pattern(pattern, context="CLI --exclude-folder")
                folders.append(sanitized)
            logging.debug("Added CLI folder exclusions: %s", args.exclude_folder)

    # Inject CLI inclusions into config
    if args.include:
        # Ensure filters exists and is a dictionary
        if not isinstance(config.get('filters'), dict):
            config['filters'] = {}
        filters = config['filters']

        # Ensure inclusion_groups exists and is a dictionary
        if not isinstance(filters.get('inclusion_groups'), dict):
            filters['inclusion_groups'] = {}
        groups = filters['inclusion_groups']

        # Create a unique group for CLI inclusions and enable it
        groups['_cli_includes'] = {
            'enabled': True,
            'filenames': [utils.validate_glob_pattern(p, context="CLI --include") for p in args.include]
        }
        logging.debug("Added CLI file inclusions: %s", args.include)

    pairing_conf = config.get('pairing') or {}
    output_conf = config.get('output') or {}
    config['pairing'] = pairing_conf
    config['output'] = output_conf

    if args.output:
        if pairing_conf.get('enabled'):
            output_conf['folder'] = args.output
        else:
            output_conf['file'] = args.output

    if args.max_tokens is not None:
        if not isinstance(config.get('filters'), dict):
            config['filters'] = {}
        config['filters']['max_total_tokens'] = args.max_tokens

    if args.limit is not None:
        if not isinstance(config.get('filters'), dict):
            config['filters'] = {}
        config['filters']['max_files'] = args.limit

    if args.toc:
        output_conf['table_of_contents'] = True

    if args.line_numbers:
        output_conf['add_line_numbers'] = True

    if args.include_tree:
        output_conf['include_tree'] = True

    if args.compact:
        if not isinstance(config.get('processing'), dict):
            config['processing'] = {}
        config['processing']['compact_whitespace'] = True

    if args.sort:
        output_conf['sort_by'] = args.sort

    if args.reverse:
        output_conf['sort_reverse'] = True

    # Determine the effective output format. CLI flags take precedence over config.
    if args.markdown:
        args.format = "markdown"
    elif args.json:
        args.format = "json"
    elif args.xml:
        args.format = "xml"

    explicit_files = None
    if args.files_from:
        explicit_files = []
        try:
            if args.files_from == '-':
                # stdin is already open, but we need to ensure we read it line by line
                # without closing it if it's reused (though here we just consume it).
                # Using sys.stdin directly.
                input_source = sys.stdin
                source_name = "stdin"
            else:
                input_source = open(args.files_from, 'r', encoding='utf-8')
                source_name = args.files_from

            if source_name != "stdin":
                with input_source as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            explicit_files.append(Path(line).resolve())
            else:
                for line in input_source:
                    line = line.strip()
                    if line:
                        explicit_files.append(Path(line).resolve())

            logging.info("Read %d file paths from %s.", len(explicit_files), source_name)

        except OSError as e:
            logging.error("Failed to read file list from '%s': %s", args.files_from, e)
            sys.exit(1)

    pairing_enabled = pairing_conf.get('enabled')

    # Auto-detect format from extension if not explicitly set via CLI flags
    if not args.format and not pairing_enabled and args.output and args.output != '-':
        ext = Path(args.output).suffix.lower()
        if ext in ('.md', '.markdown'):
            args.format = 'markdown'
        elif ext == '.json':
            args.format = 'json'
        elif ext == '.jsonl':
            args.format = 'jsonl'
        elif ext == '.xml':
            args.format = 'xml'

    if not args.format:
        args.format = output_conf.get('format', 'text')
    if pairing_enabled:
        output_path = output_conf.get('folder')
    else:
        # Smart extension adjustment: if no explicit output path was provided via CLI
        # and we are using the default filename, adjust the extension to match the format.
        if not args.output and output_conf.get('file', DEFAULT_OUTPUT_FILENAME) == DEFAULT_OUTPUT_FILENAME:
            if args.format == 'markdown':
                output_conf['file'] = str(Path(DEFAULT_OUTPUT_FILENAME).with_suffix('.md'))
            elif args.format == 'json':
                output_conf['file'] = str(Path(DEFAULT_OUTPUT_FILENAME).with_suffix('.json'))
            elif args.format == 'jsonl':
                output_conf['file'] = str(Path(DEFAULT_OUTPUT_FILENAME).with_suffix('.jsonl'))
            elif args.format == 'xml':
                output_conf['file'] = str(Path(DEFAULT_OUTPUT_FILENAME).with_suffix('.xml'))

        output_path = output_conf.get('file', DEFAULT_OUTPUT_FILENAME)

    # Determine output description before the main loop
    if args.clipboard:
        destination_desc = "to clipboard"
    elif output_path == '-':
        destination_desc = "to your terminal"
    elif pairing_enabled:
        destination_desc = (
            "alongside their source files"
            if output_path is None
            else f"to '{output_path}'"
        )
    else:
        destination_desc = f"to '{output_path}'"

    if args.extract:
        output_folder = args.output or "."
        content = ""
        source_name = ""

        if args.clipboard:
            try:
                import pyperclip
                content = pyperclip.paste()
                source_name = "clipboard"
            except ImportError:
                logging.error("The 'pyperclip' library is required for clipboard support. Install it with: pip install pyperclip")
                sys.exit(1)
        elif remaining_targets and remaining_targets[0] == "-":
            content = sys.stdin.read()
            source_name = "stdin"
        elif remaining_targets:
            input_path = Path(remaining_targets[0])
            if not input_path.exists():
                logging.error("Input file not found: %s", input_path)
                sys.exit(1)
            content = read_file_best_effort(input_path)
            source_name = str(input_path)
        else:
            logging.error("No input specified for extraction. Use a file path, '-' for your terminal, or --clipboard.")
            sys.exit(1)

        stats = extract_files(
            content,
            output_folder,
            dry_run=args.dry_run,
            source_name=source_name,
            config=config,
            list_files=args.list_files,
            tree_view=args.tree,
            limit=config.get('filters', {}).get('max_files', 0)
        )
        dest = f"to '{output_folder}'"
        duration = time.perf_counter() - start_time
        _print_execution_summary(stats, args, pairing_enabled=False, destination_desc=dest, duration=duration)
        sys.exit(0)

    mode_desc = "Pairing" if pairing_enabled else "Combining files"
    logging.info("SourceCombine starting. Mode: %s", mode_desc)

    if args.list_files:
        logging.info("Output: Listing files only (no files will be written)")
    elif args.tree:
        logging.info("Output: Showing file tree (no files will be written)")
    elif args.estimate_tokens:
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
            list_files=args.list_files,
            tree_view=args.tree,
            explicit_files=explicit_files,
        )
    except InvalidConfigError as exc:
        logging.error(exc, exc_info=True)
        sys.exit(1)

    if stats:
        duration = time.perf_counter() - start_time
        _print_execution_summary(stats, args, pairing_enabled, destination_desc, duration=duration)


def extract_files(content, output_folder, dry_run=False, source_name="archive", config=None, list_files=False, tree_view=False, limit=0):
    """Recreate the original folder structure and files from a combined file content."""
    output_folder = Path(output_folder)
    stats = {
        'total_discovered': 0,
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'filter_reasons': {},
    }

    if config is None:
        config = copy.deepcopy(utils.DEFAULT_CONFIG)

    if not content:
        logging.error("Input content is empty.")
        sys.exit(1)

    files_to_create = []

    # 1. Try JSON
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and 'path' in entry and 'content' in entry:
                    files_to_create.append((entry['path'], entry['content']))
    except json.JSONDecodeError:
        pass

    # 1.5 Try JSONL if JSON failed
    if not files_to_create:
        try:
            potential_files = []
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if isinstance(entry, dict) and 'path' in entry and 'content' in entry:
                    potential_files.append((entry['path'], entry['content']))
                else:
                    potential_files = []
                    break
            if potential_files:
                files_to_create = potential_files
        except (json.JSONDecodeError, TypeError):
            pass

    # 2. Try XML if JSON failed or found nothing
    if not files_to_create:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            # Support both flat and nested <file> tags
            for file_node in root.iter('file'):
                path = file_node.get('path')
                file_content = file_node.text
                if path and file_content is not None:
                    # XML extraction often has extra newlines due to templates
                    # If it starts and ends with a newline, it's likely from the template
                    if file_content.startswith('\n') and file_content.endswith('\n'):
                        file_content = file_content[1:-1]
                    files_to_create.append((path, file_content))
        except (ET.ParseError, ImportError):
            pass

    # 3. Try Text format (Default SourceCombine output)
    if not files_to_create:
        # Match --- FILENAME --- followed by content and --- end FILENAME ---
        # Note: The non-greedy [\s\S]*? handles many files correctly.
        pattern = re.compile(r'^---\s+(.+?)\s+---\n([\s\S]*?)\n--- end \1 ---', re.MULTILINE)
        for match in pattern.finditer(content):
            path, file_content = match.groups()
            files_to_create.append((path.strip(), file_content))

    # 4. Try Markdown if others failed or found nothing
    if not files_to_create:
        # Find all header starts (## or ###)
        header_pattern = re.compile(r'^#{2,3}\s+(.+?)\s*$', re.MULTILINE)
        headers = list(header_pattern.finditer(content))

        for i, match in enumerate(headers):
            path = match.group(1).strip()
            start = match.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
            section = content[start:end]

            # Find the first code block in this section
            code_pattern = re.compile(r'```(?:\w+)?\n([\s\S]*?)\n```')
            code_match = code_pattern.search(section)
            if code_match:
                files_to_create.append((path, code_match.group(1)))

    if not files_to_create:
        logging.error("Could not find any files to extract in %s. Supported formats are JSON, XML, Markdown, and Text.", source_name)
        sys.exit(1)

    stats['total_discovered'] = len(files_to_create)
    filter_opts = config.get('filters', {})
    search_opts = config.get('search', {})

    filtered_files = []
    for path_str, file_content in files_to_create:
        rel_path = PurePath(path_str)
        include, reason = should_include(
            None,
            rel_path,
            filter_opts,
            search_opts,
            return_reason=True,
            virtual_content=file_content,
        )

        if include:
            filtered_files.append((path_str, file_content))
        else:
            if reason:
                stats['filter_reasons'][reason] = stats['filter_reasons'].get(reason, 0) + 1

    if limit > 0 and len(filtered_files) > limit:
        stats['filter_reasons']['file_limit'] = len(filtered_files) - limit
        filtered_files = filtered_files[:limit]
        stats['limit_reached'] = True

    for path_str, file_content in filtered_files:
        rel_path = PurePath(path_str)
        stats['total_files'] += 1
        ext = rel_path.suffix.lower() or '.no_extension'
        stats['files_by_extension'][ext] = stats['files_by_extension'].get(ext, 0) + 1
        stats['total_size_bytes'] += len(file_content.encode('utf-8'))

    files_to_create = filtered_files

    if list_files:
        for path_str, _ in files_to_create:
            print(path_str)
        return stats

    if tree_view:
        tree_paths = [Path(source_name) / p for p, _ in files_to_create]
        print(_generate_tree_string(tree_paths, Path(source_name), include_header=False))
        return stats

    logging.info("Found %d files to extract from %s", len(files_to_create), source_name)

    extracted_count = 0
    for rel_path_str, file_content in files_to_create:
        # Security check: prevent path traversal and absolute paths across platforms.
        # We explicitly check for both Posix and Windows absolute path patterns.
        # For traversal, we normalize separators to ensure '..' is caught.
        normalized_path = rel_path_str.replace('\\', '/')
        is_unsafe = (
            PurePosixPath(rel_path_str).is_absolute() or
            PureWindowsPath(rel_path_str).is_absolute() or
            '..' in PurePosixPath(normalized_path).parts
        )
        if is_unsafe:
            logging.warning("Skipping potentially unsafe path: %s", rel_path_str)
            continue

        rel_path = Path(rel_path_str)

        target_path = output_folder / rel_path

        if dry_run:
            logging.info("[DRY RUN] Would create: %s", target_path)
        else:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(file_content, encoding='utf-8')
                logging.info("Extracted: %s", target_path)
                extracted_count += 1
            except OSError as e:
                logging.error("Failed to write %s: %s", target_path, e)

    if not dry_run:
        logging.info("Extraction complete. %d files created in %s", extracted_count, output_folder)

    return stats


def _print_execution_summary(stats, args, pairing_enabled, destination_desc=None, duration=None):
    """Print a formatted summary of the execution statistics to stderr."""

    total_included = stats.get('total_files', 0)
    total_discovered = stats.get('total_discovered', 0)
    total_filtered = max(0, total_discovered - total_included)
    excluded_folders = stats.get('excluded_folder_count', 0)

    if args.dry_run:
        summary_title = f"DRY RUN COMPLETE: Would combine {total_included:,} files {destination_desc or ''}".strip()
        title_color = C_YELLOW
    elif args.estimate_tokens:
        summary_title = "TOKEN ESTIMATION COMPLETE"
        title_color = C_CYAN
    elif args.list_files:
        summary_title = "FILE LISTING COMPLETE"
        title_color = C_CYAN
    elif args.tree:
        summary_title = "TREE VIEW COMPLETE"
        title_color = C_CYAN
    else:
        file_word = "file" if total_included == 1 else "files"
        summary_title = f"SUCCESS: Combined {total_included:,} {file_word} {destination_desc or ''}".strip()
        title_color = C_GREEN

    # Header
    print(f"\n{title_color}{C_BOLD}=== {summary_title} ==={C_RESET}", file=sys.stderr)

    if stats.get('budget_exceeded'):
        print(f"  {C_YELLOW}{C_BOLD}WARNING: Output truncated due to token budget.{C_RESET}", file=sys.stderr)
    if stats.get('limit_reached'):
        print(f"  {C_YELLOW}{C_BOLD}WARNING: Output truncated due to file limit.{C_RESET}", file=sys.stderr)

    # Files Section
    label_width = 22
    print(f"  {C_BOLD}Files{C_RESET}", file=sys.stderr)
    print(f"    {C_BOLD}{'Included:':<{label_width}}{C_RESET}{C_CYAN}{total_included:12,}{C_RESET}", file=sys.stderr)
    print(f"    {C_BOLD}{'Filtered:':<{label_width}}{C_RESET}{C_CYAN}{total_filtered:12,}{C_RESET}", file=sys.stderr)

    # Detailed breakdown of filtering reasons
    if stats.get('filter_reasons'):
        # Sort by count descending, then alphabetically
        sorted_reasons = sorted(
            [(r, c) for r, c in stats['filter_reasons'].items() if r != 'excluded_folder'],
            key=lambda x: (-x[1], x[0])
        )
        for reason, count in sorted_reasons:
            if count > 0:
                display_reason = reason.replace('_', ' ')
                # Use dim for less visual noise in the breakdown
                print(f"      {C_DIM}- {display_reason:<{label_width - 4}}{C_RESET}{C_CYAN}{count:12,}{C_RESET}", file=sys.stderr)

    print(f"    {C_BOLD}{'Total Found:':<{label_width}}{C_RESET}{C_CYAN}{total_discovered:12,}{C_RESET}", file=sys.stderr)
    if excluded_folders > 0:
        print(f"    {C_BOLD}{'Excluded Folders:':<{label_width}}{C_RESET}{C_CYAN}{excluded_folders:12,}{C_RESET}", file=sys.stderr)

    # Data Section
    total_size_str = utils.format_size(stats.get('total_size_bytes', 0))
    total_lines = stats.get('total_lines', 0)
    print(f"\n  {C_BOLD}Data{C_RESET}", file=sys.stderr)
    print(f"    {C_BOLD}{'Total Size:':<{label_width}}{C_RESET}{C_CYAN}{total_size_str:>12}{C_RESET}", file=sys.stderr)
    print(f"    {C_BOLD}{'Total Lines:':<{label_width}}{C_RESET}{C_CYAN}{total_lines:12,}{C_RESET}", file=sys.stderr)

    # Token Counts
    # Show token counts if tokens were estimated
    token_count = stats.get('total_tokens', 0)
    if token_count > 0:
        is_approx = stats.get('token_count_is_approx', False)
        token_str = f"{'~' if is_approx else ''}{token_count:,}"
        print(
            f"    {C_BOLD}{'Token Count:':<{label_width}}{C_RESET}{C_CYAN}{token_str:>12}{C_RESET}",
            file=sys.stderr,
        )
        if is_approx:
            print(
                f"      {C_DIM}(Install 'tiktoken' for accurate counts){C_RESET}",
                file=sys.stderr,
            )

        # Budget Usage
        max_tokens = stats.get('max_total_tokens', 0)
        if max_tokens > 0:
            percent = (token_count / max_tokens) * 100
            # Create a 10-character ASCII bar
            bar_len = 10
            filled = min(bar_len, int((percent / 100) * bar_len))
            bar = f"[{'#' * filled}{'-' * (bar_len - filled)}]"
            bar_color = C_YELLOW if percent > 90 else C_GREEN
            print(f"    {C_BOLD}{'Budget Usage:':<{label_width}}{C_RESET}{bar_color}{bar}{C_RESET} {C_CYAN}{percent:>6.1f}%{C_RESET}", file=sys.stderr)

    if duration is not None:
        print(f"    {C_BOLD}{'Duration:':<{label_width}}{C_RESET}{C_CYAN}{duration:.2f}s{C_RESET}", file=sys.stderr)

    # Largest Files
    if stats.get('top_files'):
        # Fallback to sorting by size if no token counts are available
        has_tokens = any(f[0] > 0 for f in stats['top_files'])
        if has_tokens:
            print(f"\n  {C_BOLD}Largest Files (by tokens){C_RESET}", file=sys.stderr)
            top = sorted(stats['top_files'], key=lambda x: (-x[0], x[2]))[:5]
        else:
            print(f"\n  {C_BOLD}Largest Files (by size){C_RESET}", file=sys.stderr)
            top = sorted(stats['top_files'], key=lambda x: (-x[1], x[2]))[:5]

        for tokens, f_size, path in top:
            token_str = f"{tokens:,}"
            size_str = f"({utils.format_size(f_size)})"
            # Truncate long paths
            display_path = (path[:48] + '...') if len(path) > 51 else path
            # Align token counts at 10 and sizes at 12 to keep paths consistent
            if has_tokens:
                print(f"    {C_CYAN}{token_str:>10}{C_RESET}  {C_DIM}{size_str:<12}{C_RESET}  {display_path}", file=sys.stderr)
            else:
                print(f"    {C_CYAN}{size_str:<12}{C_RESET}  {display_path}", file=sys.stderr)

    # Extensions Grid
    if stats['files_by_extension']:
        # Sort by count desc, then alpha
        sorted_exts = sorted(
            stats['files_by_extension'].items(),
            key=lambda item: (-item[1], item[0])
        )

        formatted_counts = [f"{count:,}" for _, count in sorted_exts]
        items = [f"{C_CYAN}{ext}{C_RESET}: {c:>5}" for (ext, _), c in zip(sorted_exts, formatted_counts)]
        raw_items = [f"{ext}: {c:>5}" for (ext, _), c in zip(sorted_exts, formatted_counts)]
        max_len = max(len(s) for s in raw_items) + 3

        # Determine available width
        term_width = 80
        if sys.stderr.isatty():
            try:
                term_width = shutil.get_terminal_size((80, 20)).columns
            except Exception:
                pass

        # Indent is 4
        avail_width = max(40, term_width - 4)
        cols = max(1, avail_width // max_len)

        print(f"\n  {C_BOLD}Extensions{C_RESET}", file=sys.stderr)

        for i in range(0, len(items), cols):
            chunk = items[i:i + cols]
            raw_chunk = raw_items[i:i + cols]
            line_parts = []
            for item, raw_item in zip(chunk, raw_chunk):
                padding = " " * (max_len - len(raw_item))
                line_parts.append(item + padding)
            print(f"    {''.join(line_parts).rstrip()}", file=sys.stderr)

    # Footer
    print(f"\n{title_color}{'=' * (len(summary_title) + 8)}{C_RESET}", file=sys.stderr)


if __name__ == "__main__":
    main()
