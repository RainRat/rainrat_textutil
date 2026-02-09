import argparse
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


def _get_rel_path(path, root_path):
    """Return ``path`` relative to ``root_path`` with fallback to original."""
    try:
        return path.relative_to(root_path)
    except ValueError:
        return path


def _render_template(template, relative_path):
    """Replace placeholders in ``template`` with values from ``relative_path``."""
    if not template:
        return ""
    rendered = template.replace(FILENAME_PLACEHOLDER, relative_path.as_posix())
    rendered = rendered.replace("{{EXT}}", relative_path.suffix.lstrip(".") or "")
    return rendered


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
    """Return all paths in ``root_folder`` while pruning excluded folders.

    If ``root_folder`` is a file, it returns a list containing only that file.
    """
    root_path = Path(root_folder)
    try:
        if root_path.is_file():
            if progress:
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
        rel_p = _get_rel_path(p, root_path)

        if record_size_exclusions:
            include, reason = should_include(
                p,
                rel_p,
                filter_opts,
                search_opts,
                return_reason=True,
            )
        else:
            include = should_include(
                p,
                rel_p,
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


def _path_without_suffix(file_path, root_path):
    return _get_rel_path(file_path, root_path).with_suffix("")


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
            pair_key = _path_without_suffix(src, root_path)
            paired[pair_key] = pair
        elif include_mismatched and (src or hdr):
            path = src or hdr
            pair_key = _path_without_suffix(path, root_path)
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

        outfile.write(_render_template(header_template, relative_path))
        outfile.write(content)
        outfile.write(_render_template(footer_template, relative_path))
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

    def process_and_write(self, file_path, root_path, outfile, output_format='text', cached_content=None):
        """Read, process, and write a single file.

        Returns
        -------
        tuple[int, bool]
            A tuple containing (token_count, is_approximate) for the written content.
        """
        if self.dry_run:
            logging.info(_get_rel_path(file_path, root_path))
            return 0, True

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
                if output_format == 'xml':
                    from xml.sax.saxutils import escape
                    processed_content = escape(processed_content)
                self._write_with_templates(outfile, processed_content, relative_path)

        # Estimate tokens on the final processed content
        return utils.estimate_tokens(processed_content)

    def write_max_size_placeholder(self, file_path, root_path, outfile, output_format='text'):
        """Write the placeholder for files skipped for exceeding max size.

        Returns
        -------
        tuple[int, bool]
            A tuple containing (token_count, is_approximate) for the placeholder.
        """

        if self.dry_run:
            logging.info(_get_rel_path(file_path, root_path))
            return 0, True

        placeholder = self.output_opts.get('max_size_placeholder')
        if not placeholder:
            return 0, True

        relative_path = _get_rel_path(file_path, root_path)
        rendered = _render_template(placeholder, relative_path)

        if not self.estimate_tokens:
            if output_format == 'json':
                entry = {
                    "path": relative_path.as_posix(),
                    "content": rendered
                }
                json.dump(entry, outfile)
            else:
                if output_format == 'xml':
                    from xml.sax.saxutils import escape
                    rendered = escape(rendered)
                self._write_with_templates(outfile, rendered, relative_path)

        return utils.estimate_tokens(rendered)


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
    # { 'folder': { 'subfolder': { 'file.txt': None } } }
    tree = {}
    for p in rel_paths:
        parts = p.parts
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

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

            meta_str = ""
            if metadata and current_rel_path in rel_to_orig:
                orig_path = rel_to_orig[current_rel_path]
                file_meta = metadata.get(orig_path)
                if file_meta:
                    parts = []
                    if 'size' in file_meta:
                        parts.append(utils.format_size(file_meta['size']))
                    if 'tokens' in file_meta:
                        parts.append(f"{file_meta['tokens']:,} tokens")
                    if parts:
                        meta_str = f" ({', '.join(parts)})"

            lines.append(f"{prefix}{connector}{item}{meta_str}")

            # If the item has children (it's a folder), recurse
            children = node[item]
            if children:
                extension = "    " if is_last else "│   "
                _add_node(children, prefix + extension, current_rel_parts)

    # Add the root folder name first
    lines.append(f"{root_path.name}/")
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
                file_meta = metadata[file_path]
                parts = []
                if 'size' in file_meta:
                    parts.append(utils.format_size(file_meta['size']))
                if 'tokens' in file_meta:
                    parts.append(f"{file_meta['tokens']:,} tokens")
                if parts:
                    meta_str = f" ({', '.join(parts)})"

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
                file_meta = metadata[file_path]
                parts = []
                if 'size' in file_meta:
                    parts.append(utils.format_size(file_meta['size']))
                if 'tokens' in file_meta:
                    parts.append(f"{file_meta['tokens']:,} tokens")
                if parts:
                    meta_str = f" ({', '.join(parts)})"

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
        'token_count_is_approx': False,
        'budget_exceeded': False
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
        raise InvalidConfigError("Stdout output is not available in pairing mode.")

    if output_format == 'json' and pairing_enabled:
        raise InvalidConfigError("JSON format is not compatible with paired output.")

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

    if not pairing_enabled and not dry_run and not estimate_tokens and not clipboard and not list_files and output_path is None:
        raise InvalidConfigError(
            "'output.file' must be set when pairing is disabled and clipboard mode is off."
        )

    out_folder = None
    if pairing_enabled and output_path:
        out_folder = Path(output_path)
        if not dry_run and not estimate_tokens and not list_files:
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
    processor = FileProcessor(config, output_opts, dry_run=processor_dry_run, estimate_tokens=estimate_tokens)

    total_excluded_folders = 0

    # Store all items to process for single-file mode to enable global TOC
    # List of (file_path, root_path, is_size_excluded)
    all_single_mode_items = []
    # Metadata for TOC and Tree: {Path: {'size': int, 'tokens': int}}
    file_metadata = {}

    with outfile_ctx as outfile:
        global_header = output_opts.get('global_header_template')
        global_footer = output_opts.get('global_footer_template')

        # Only write global headers for text, markdown, and xml output
        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and global_header and output_format in ('text', 'markdown', 'xml'):
            outfile.write(global_header)

        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and output_format == 'json':
            outfile.write('[')

        first_item = True

        iteration_targets = []
        if explicit_files:
            # Bypass discovery: process specific files relative to CWD
            # (root_path, all_paths, excluded_folder_count)
            iteration_targets.append((Path.cwd(), explicit_files, 0))
        else:
            # Standard discovery from root folders
            for root_folder in root_folders:
                discovery_bar = processor._make_bar(
                    desc=f"Discovering in {root_folder}",
                    unit="file",
                    leave=False,
                )
                try:
                    paths, root, excluded = collect_file_paths(
                        root_folder, recursive, exclude_folders, progress=discovery_bar
                    )
                finally:
                    discovery_bar.close()
                if paths:
                    iteration_targets.append((root, paths, excluded))

        for root_path, all_paths, excluded_count in iteration_targets:
            total_excluded_folders += excluded_count
            stats['total_discovered'] += len(all_paths)

            source_exts = tuple(
                e.lower() for e in (pair_opts.get('source_extensions') or [])
            )
            header_exts = tuple(
                e.lower() for e in (pair_opts.get('header_extensions') or [])
            )
            record_size_exclusions = bool(output_opts.get('max_size_placeholder'))

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

                # Update stats for listed files
                for p in paths_to_list:
                    _update_file_stats(stats, p)

                if tree_view:
                    view_metadata = {}
                    for p in paths_to_list:
                        view_metadata[p] = {'size': p.stat().st_size if p.exists() else 0}
                        if estimate_tokens:
                            content = read_file_best_effort(p)
                            processed = process_content(content, processor.processing_opts)
                            tokens, is_approx = utils.estimate_tokens(processed)
                            view_metadata[p]['tokens'] = tokens
                            stats['total_tokens'] += tokens
                            if is_approx:
                                stats['token_count_is_approx'] = True

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
                # Process pairing immediately per root folder
                processing_bar = processor._make_bar(
                    total=(
                        len(filtered_paths) + len(size_excluded)
                        if (filtered_paths or size_excluded)
                        else None
                    ),
                    desc="Processing files",
                    unit="file",
                )

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
                processing_bar.close()
            else:
                # Accumulate for single-file mode
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

        # Metadata and Budgeting Pass for Single File Mode
        max_total_tokens = filter_opts.get('max_total_tokens', 0)
        needs_metadata = bool(output_opts.get('include_tree') or output_opts.get('table_of_contents'))

        if (max_total_tokens > 0 or (estimate_tokens and needs_metadata)) and not pairing_enabled and not list_files and not tree_view:
            budgeted_items = []
            current_tokens = 0
            budget_exceeded = False

            # Account for global header and footer tokens in the budget
            if global_header and output_format in ('text', 'markdown', 'xml'):
                current_tokens += utils.estimate_tokens(global_header)[0]
            if global_footer and output_format in ('text', 'markdown', 'xml'):
                current_tokens += utils.estimate_tokens(global_footer)[0]

            for item in all_single_mode_items:
                file_path, root_path, is_excluded_by_size = item
                tokens = 0
                processed = None

                rel_p = _get_rel_path(file_path, root_path)

                if is_excluded_by_size:
                    placeholder = output_opts.get('max_size_placeholder')
                    if placeholder:
                        rendered = _render_template(placeholder, rel_p)
                        tokens, _ = utils.estimate_tokens(rendered)
                else:
                    content = read_file_best_effort(file_path)
                    processed = process_content(content, processor.processing_opts)
                    if processor.apply_in_place and processed != content and not estimate_tokens and not dry_run:
                        logging.info("Updating in place: %s", file_path)
                        processor._backup_file(file_path)
                        file_path.write_text(processed, encoding='utf8', newline='')
                    tokens, _ = utils.estimate_tokens(processed)

                # Store metadata for TOC/Tree
                file_metadata[file_path] = {
                    'size': file_path.stat().st_size if file_path.exists() else 0,
                    'tokens': tokens
                }

                # Account for header/footer templates in the budget
                h_template = output_opts.get('header_template', utils.DEFAULT_CONFIG['output']['header_template'])
                f_template = output_opts.get('footer_template', utils.DEFAULT_CONFIG['output']['footer_template'])
                tokens += utils.estimate_tokens(_render_template(h_template, rel_p))[0]
                tokens += utils.estimate_tokens(_render_template(f_template, rel_p))[0]

                if max_total_tokens > 0 and current_tokens + tokens > max_total_tokens and current_tokens > 0:
                    budget_exceeded = True
                    break

                current_tokens += tokens
                budgeted_items.append((file_path, root_path, is_excluded_by_size, processed))

            all_single_mode_items = budgeted_items
            stats['budget_exceeded'] = budget_exceeded

            # Recalculate stats based on budgeted items
            stats['total_files'] = 0
            stats['total_size_bytes'] = 0
            stats['files_by_extension'] = {}
            for item in all_single_mode_items:
                _update_file_stats(stats, item[0])
        elif needs_metadata and not pairing_enabled and not list_files and not tree_view:
            # Just collect sizes if we don't need a full budgeting/token pass
            for item in all_single_mode_items:
                file_path = item[0]
                file_metadata[file_path] = {
                    'size': file_path.stat().st_size if file_path.exists() else 0
                }

        # Process Single File Mode items (including TOC and Tree)
        if not pairing_enabled and not list_files and not tree_view:
            if output_opts.get('include_tree') and output_format in ('text', 'markdown'):
                root_to_paths = {}
                for item in all_single_mode_items:
                    file_path, root_path = item[0], item[1]
                    if root_path not in root_to_paths:
                        root_to_paths[root_path] = []
                    root_to_paths[root_path].append(file_path)

                for root_path, paths in root_to_paths.items():
                    tree_content = _generate_tree_string(paths, root_path, output_format, metadata=file_metadata)
                    if estimate_tokens:
                        token_count, is_approx = utils.estimate_tokens(tree_content)
                        stats['total_tokens'] += token_count
                        if is_approx:
                            stats['token_count_is_approx'] = True
                    elif not dry_run:
                        outfile.write(tree_content + "\n")

            if output_opts.get('table_of_contents') and output_format in ('text', 'markdown'):
                # Generate TOC
                # Only include files that are not size-excluded for the TOC?
                # Or include them all? Usually TOC lists what's in the document.
                # If size-excluded files get a placeholder, they are "in" the document.
                toc_files = [(item[0], item[1]) for item in all_single_mode_items]
                toc_content = _generate_table_of_contents(toc_files, output_format, metadata=file_metadata)

                if estimate_tokens:
                    # Count tokens for TOC
                    token_count, is_approx = utils.estimate_tokens(toc_content)
                    stats['total_tokens'] += token_count
                    if is_approx:
                        stats['token_count_is_approx'] = True
                elif not dry_run:
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
                    token_count, is_approx = processor.write_max_size_placeholder(
                        file_path, root_path, outfile, output_format=output_format
                    )
                else:
                    token_count, is_approx = processor.process_and_write(
                        file_path,
                        root_path,
                        outfile,
                        output_format=output_format,
                        cached_content=cached_processed
                    )

                if not dry_run or estimate_tokens:
                    stats['total_tokens'] += token_count
                    if is_approx:
                        stats['token_count_is_approx'] = True

                processing_bar.update(1)

            processing_bar.close()

        # Write global footer only for text, markdown, and xml output
        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and global_footer and output_format in ('text', 'markdown', 'xml'):
            outfile.write(global_footer)

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
    parser = argparse.ArgumentParser(
        description=(
            "Combine multiple source files into one document or organized pairs. "
            "This tool is useful for creating AI context, documentation, or code reviews."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              # Combine files in the current folder into 'combined_files.txt'
              python sourcecombine.py

              # Combine files from a specific folder
              python sourcecombine.py src/

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
        help="One or more configuration files, folders, or files to process.",
    )

    # Configuration Group
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--init",
        action="store_true",
        help="Create a starter 'sourcecombine.yml' file in the current folder.",
    )
    config_group.add_argument(
        "--exclude-file",
        "-x",
        dest="exclude_file",
        action="append",
        default=[],
        help="Skip files that match this pattern (e.g., '*.log'). Use multiple times to skip more.",
    )
    config_group.add_argument(
        "--exclude-folder",
        "-X",
        dest="exclude_folder",
        action="append",
        default=[],
        help="Skip folders that match this pattern (e.g., 'build'). Use multiple times to skip more.",
    )
    config_group.add_argument(
        "--include",
        "-i",
        action="append",
        default=[],
        help="Include only files matching this glob pattern. Can be used multiple times. Overrides/appends to config.",
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
        help="Copy the result to your clipboard instead of saving a file. (Single-file mode only)",
    )
    output_group.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "markdown", "xml"],
        default="text",
        help=(
            "Choose the output format. 'json' creates a list of file contents. "
            "'markdown' automatically adds code blocks. (Single-file mode only)"
        ),
    )
    output_group.add_argument(
        "--toc",
        action="store_true",
        help="Add a Table of Contents (including file sizes and token counts) to the start of the output. (Works for 'text' and 'markdown' formats in single-file mode only)",
    )
    output_group.add_argument(
        "--include-tree",
        action="store_true",
        help="Include a visual folder tree with file metadata at the start of the output. (Single-file mode only)",
    )

    # Runtime Options Group
    runtime_group = parser.add_argument_group("Runtime Options")
    runtime_group.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Show which files would be included without creating any files.",
    )
    runtime_group.add_argument(
        "--estimate-tokens",
        "-e",
        action="store_true",
        help="Estimate token usage. This is slower because it must read the file contents.",
    )
    runtime_group.add_argument(
        "--max-tokens",
        type=int,
        help="Stop adding files once this total token limit is reached. (Single-file mode only)",
    )
    runtime_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show extra details to help with troubleshooting.",
    )
    runtime_group.add_argument(
        "--list-files",
        action="store_true",
        help="Print a list of all files that would be included and then stop.",
    )
    runtime_group.add_argument(
        "--tree",
        action="store_true",
        help="Show a visual folder tree of all included files with metadata and then stop.",
    )
    runtime_group.add_argument(
        "--files-from",
        help="Read a list of files from a text file (use '-' for console). This skips folder scanning.",
    )

    args = parser.parse_args()

    # Configure logging *immediately* based on -v.
    # This ensures logging is set up *before* load_and_validate_config (which logs)
    # is called, preventing a race condition that locks the log level at WARNING.
    prelim_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=prelim_level, format='%(levelname)s: %(message)s')

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

    # Relax root_folders requirement if we have other targets or --files-from
    nested_required = {'search': ['root_folders']}
    if args.files_from or remaining_targets:
        nested_required = {}

    if not config_path and not remaining_targets:
        # Case 1: No positional targets. Use auto-discovery
        defaults = ['sourcecombine.yml', 'sourcecombine.yaml', 'config.yml', 'config.yaml']
        for d in defaults:
            if Path(d).is_file():
                config_path = d
                logging.info("Auto-discovered config file: %s", config_path)
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
    elif not config_path and not args.files_from:
        logging.info(
            "No config file found. Scanning current folder '.' with default settings."
        )
        config['search']['root_folders'] = ["."]

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

    if args.toc:
        output_conf['table_of_contents'] = True

    if args.include_tree:
        output_conf['include_tree'] = True

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
    if pairing_enabled:
        output_path = output_conf.get('folder')
    else:
        output_path = output_conf.get('file', DEFAULT_OUTPUT_FILENAME)

    # Determine output description before the main loop
    if args.clipboard:
        destination_desc = "to clipboard"
    elif output_path == '-':
        destination_desc = "to stdout"
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

    # Success/Completion Feedback
    use_color = sys.stderr.isatty() and not os.getenv("NO_COLOR")
    green = "\033[32m" if use_color else ""
    yellow = "\033[33m" if use_color else ""
    reset = "\033[0m" if use_color else ""

    if args.dry_run:
        logging.info(f"{yellow}Dry run complete.{reset}")
    elif args.list_files:
        logging.info(f"{green}Success!{reset} File listing complete.")
    elif args.tree:
        logging.info(f"{green}Success!{reset} Tree view complete.")
    elif args.estimate_tokens:
        logging.info(f"{green}Success!{reset} Token estimation complete.")
    else:
        logging.info(f"{green}Success!{reset} Combined files {destination_desc}")

    if stats:
        _print_execution_summary(stats, args, pairing_enabled)


def _print_execution_summary(stats, args, pairing_enabled):
    """Print a formatted summary of the execution statistics to stderr."""

    total_included = stats.get('total_files', 0)
    total_discovered = stats.get('total_discovered', 0)
    total_filtered = max(0, total_discovered - total_included)
    total_size_mb = stats.get('total_size_bytes', 0) / (1024 * 1024)
    excluded_folders = stats.get('excluded_folder_count', 0)

    # ANSI color codes (if supported)
    bold = "\033[1m"
    reset = "\033[0m"
    dim = "\033[90m"
    green = "\033[32m"
    yellow = "\033[33m"
    cyan = "\033[36m"

    use_color = sys.stderr.isatty() and not os.getenv("NO_COLOR")
    if not use_color:
        bold = reset = dim = green = yellow = cyan = ""

    if args.dry_run:
        summary_title = "Dry-Run Summary"
        title_color = yellow
    elif args.estimate_tokens:
        summary_title = "Token Estimation Summary"
        title_color = cyan
    elif args.list_files:
        summary_title = "File List Summary"
        title_color = cyan
    elif args.tree:
        summary_title = "Tree View Summary"
        title_color = cyan
    else:
        summary_title = "Execution Summary"
        title_color = green

    # Header
    print(f"\n{title_color}{bold}=== {summary_title} ==={reset}", file=sys.stderr)

    if stats.get('budget_exceeded'):
        print(f"  {yellow}{bold}WARNING: Output truncated due to token budget.{reset}", file=sys.stderr)

    # Files Section
    label_width = 18
    print(f"  {bold}Files{reset}", file=sys.stderr)
    print(f"    {bold}{'Included:':<{label_width}}{reset}{total_included:12,}", file=sys.stderr)
    print(f"    {bold}{'Filtered:':<{label_width}}{reset}{total_filtered:12,}", file=sys.stderr)
    print(f"    {bold}{'Total:':<{label_width}}{reset}{total_discovered:12,}", file=sys.stderr)
    if excluded_folders > 0:
        print(f"    {bold}{'Excluded Folders:':<{label_width}}{reset}{excluded_folders:12,}", file=sys.stderr)

    # Data Section
    total_size_str = utils.format_size(stats.get('total_size_bytes', 0))
    print(f"\n  {bold}Data{reset}", file=sys.stderr)
    print(f"    {bold}{'Total Size:':<{label_width}}{reset}{total_size_str:>12}", file=sys.stderr)

    # Token Counts
    # Show token counts for single-file mode OR if estimate_tokens was requested
    if not pairing_enabled and (not args.dry_run or args.estimate_tokens) and not args.list_files and not args.tree:
        token_count = stats.get('total_tokens', 0)
        is_approx = stats.get('token_count_is_approx', False)
        token_str = f"{'~' if is_approx else ''}{token_count:,}"
        print(
            f"    {bold}{'Token Count:':<{label_width}}{reset}{token_str:>12}",
            file=sys.stderr,
        )
        if is_approx:
            print(
                f"      {dim}(Install 'tiktoken' for accurate counts){reset}",
                file=sys.stderr,
            )

    # Extensions Grid
    if stats['files_by_extension']:
        # Sort by count desc, then alpha
        sorted_exts = sorted(
            stats['files_by_extension'].items(),
            key=lambda item: (-item[1], item[0])
        )

        formatted_counts = [f"{count:,}" for _, count in sorted_exts]
        items = [f"{cyan}{ext}{reset}: {c}" for (ext, _), c in zip(sorted_exts, formatted_counts)]
        raw_items = [f"{ext}: {c}" for (ext, _), c in zip(sorted_exts, formatted_counts)]
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

        print(f"\n  {bold}Extensions{reset}", file=sys.stderr)

        for i in range(0, len(items), cols):
            chunk = items[i:i + cols]
            raw_chunk = raw_items[i:i + cols]
            line_parts = []
            for item, raw_item in zip(chunk, raw_chunk):
                padding = " " * (max_len - len(raw_item))
                line_parts.append(item + padding)
            print(f"    {''.join(line_parts).rstrip()}", file=sys.stderr)

    # Footer
    print(f"\n{title_color}{'=' * (len(summary_title) + 8)}{reset}", file=sys.stderr)


if __name__ == "__main__":
    main()
