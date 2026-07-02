import argparse
import copy
import csv
import difflib
import fnmatch
import hashlib
import importlib.util
import io
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap
import time
from contextlib import nullcontext
from datetime import datetime
from functools import lru_cache
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, Mapping
from xml.sax.saxutils import escape as _xml_escape
import xml.etree.ElementTree as ET

# Local imports
import utils
from utils import (
    FILENAME_PLACEHOLDER,
    DEFAULT_OUTPUT_FILENAME,
    ConfigNotFoundError,
    add_line_numbers,
    format_tokens,
    load_and_validate_config,
    process_content,
    read_file_best_effort,
    validate_config,
    _looks_binary,
)

# Export for backward compatibility and to handle module reloads correctly
InvalidConfigError = utils.InvalidConfigError
DEFAULT_CONFIG = utils.DEFAULT_CONFIG

__version__ = "0.5.0"

# Standardized labels for resource limit warnings
TRUNCATION_CHECKS = [
    ('token_limit_reached', 'token limit'),
    ('size_limit_reached', 'size limit'),
    ('line_limit_reached', 'line limit'),
    ('limit_reached', 'file limit'),
]


def _get_pyperclip():
    """Lazy-load pyperclip for clipboard support."""
    try:
        import pyperclip
        return pyperclip
    except ImportError:
        return None


def xml_escape(data: str) -> str:
    """Escape &, <, >, \", and ' for safe use in XML."""
    if data is None:
        return ""
    return _xml_escape(data, {'"': "&quot;", "'": "&apos;"})


def _to_int_or_none(val: Any) -> int | None:
    """Safely convert a value to an integer, returning None on failure.

    Handles strings with commas and leading '~' (approximate indicator).
    """
    if val is None:
        return None
    try:
        s = str(val).lstrip('~').replace(',', '')
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _plural(count: int, singular: str, plural_form: str | None = None) -> str:
    """Return the singular or plural form of a word based on the count."""
    if count == 1:
        return singular
    return plural_form if plural_form is not None else (singular + "s")


def _print_diff(old_text, new_text, filename):
    """Print a colored unified diff between old_text and new_text."""
    if old_text == new_text:
        return

    diff = difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )

    has_diff = False
    for line in diff:
        has_diff = True
        if line.startswith('+++') or line.startswith('---'):
            sys.stderr.write(f"{C_BOLD}{line}{C_RESET}")
        elif line.startswith('@@'):
            sys.stderr.write(f"{C_CYAN}{line}{C_RESET}")
        elif line.startswith('+'):
            sys.stderr.write(f"{C_GREEN}{line}{C_RESET}")
        elif line.startswith('-'):
            sys.stderr.write(f"{C_RED}{line}{C_RESET}")
        else:
            sys.stderr.write(line)

    if has_diff:
        sys.stderr.write("\n")


def _convert_to_json_friendly(obj):
    """Recursively convert objects (such as Path) to JSON-compatible types."""
    if isinstance(obj, dict):
        return {k: _convert_to_json_friendly(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_json_friendly(i) for i in obj]
    elif isinstance(obj, Path):
        return str(obj)
    return obj


def _write_json_summary(stats, file_path, duration=None, source_desc=None, destination_desc=None):
    """Write the execution summary in JSON format to a file or stderr."""
    if not file_path:
        return

    summary = _convert_to_json_friendly(stats)
    if duration is not None:
        summary['duration_seconds'] = duration
    if source_desc:
        summary['source'] = source_desc
    if destination_desc:
        summary['destination'] = destination_desc

    json_data = json.dumps(summary, indent=2)

    try:
        if file_path == '-':
            # Write to stderr to avoid mixing with stdout output
            sys.stderr.write("\n--- JSON Execution Summary ---\n")
            sys.stderr.write(json_data)
            sys.stderr.write("\n------------------------------\n")
        else:
            output_file = Path(file_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json_data, encoding='utf-8')
            logging.info("JSON execution summary saved to '%s'.", file_path)
    except OSError as e:
        logging.error("Failed to write JSON summary to '%s': %s", file_path, e)


class _LazyColor:
    """A helper for ANSI colors that respects isatty and NO_COLOR."""

    def __init__(self, code):
        self.code = code

    def __str__(self):
        return self._render(only_stderr=False)

    def _render(self, only_stderr=False):
        # We check isatty and NO_COLOR on every string conversion so it
        # works correctly even if sys.stdout/stderr is redirected mid-run or
        # in tests.
        if os.getenv("NO_COLOR"):
            return ""

        if only_stderr:
            return self.code if sys.stderr.isatty() else ""

        # Default: check if either is a TTY
        if sys.stderr.isatty() or sys.stdout.isatty():
            return self.code

        return ""

    def __format__(self, format_spec):
        only_stderr = (format_spec == "only_stderr")
        return self._render(only_stderr=only_stderr)


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
    """A clean logging formatter for the terminal.

    Removes the 'INFO:' prefix for standard messages and adds semantic colors
    to WARNING and ERROR levels.
    """

    def format(self, record):
        if record.levelno == logging.WARNING:
            prefix = f"{C_YELLOW:only_stderr}WARNING:{C_RESET:only_stderr} "
        elif record.levelno >= logging.ERROR:
            prefix = f"{C_RED:only_stderr}ERROR:{C_RESET:only_stderr} "
        elif record.levelno == logging.DEBUG:
            prefix = f"{C_DIM:only_stderr}DEBUG:{C_RESET:only_stderr} "
        else:
            prefix = ""

        # For multi-line messages, ensure the prefix is only on the first line
        message = record.getMessage()
        
        # Include traceback if present
        if record.exc_info:
            if not message.endswith('\n'):
                message += '\n'
            message += self.formatException(record.exc_info)
        if record.stack_info:
            if not message.endswith('\n'):
                message += '\n'
            message += self.formatStack(record.stack_info)

        if "\n" in message and prefix:
            # Strip ANSI from prefix for correct indentation calculation
            raw_prefix = _ANSI_ESCAPE.sub('', str(prefix))
            indent = " " * len(raw_prefix)
            lines = message.splitlines()
            return f"{prefix}{lines[0]}\n" + "\n".join(f"{indent}{line}" for line in lines[1:])

        return f"{prefix}{message}"


class _DevNull:
    """A file-compatible object that discards all writes."""
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

    def set_description(self, desc=None, refresh=True):
        return None

    def set_postfix(self, ordered_dict=None, refresh=True, **kwargs):
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
    if enabled:
        try:
            from tqdm import tqdm as _tqdm
            return _tqdm(iterable, **kwargs)
        except ImportError:
            pass
    return _SilentProgress(iterable)


def _get_rel_path(path, root_path):
    """Return ``path`` relative to ``root_path`` with fallback to original."""
    try:
        return path.relative_to(root_path)
    except ValueError:
        return path


def _truncate_path(path: str, max_width: int) -> str:
    """Shorten a path by removing characters from the middle.

    This ensures that both the beginning of the path and the filename
    remain visible when space is limited.
    """
    if len(path) <= max_width:
        return path

    # If the width is too small for ellipses, just return the first characters
    if max_width < 4:
        return path[:max_width]

    # If the width is small, just return it shortened from the end
    if max_width <= 10:
        return path[:max_width-3] + "..."

    # Determine how much to keep from the start and end
    # We want to favor the end (filename) more
    tail_len = min(len(path) // 2, max_width // 2)
    head_len = max_width - tail_len - 3

    return f"{path[:head_len]}...{path[-tail_len:]}"


def _make_ascii_bar(
    percent: float,
    bar_len: int = 10,
    colored: bool = False,
    use_rounding: bool = True,
    ensure_min_one: bool = True,
) -> str:
    """Create a fixed-width ASCII progress bar from a percentage.

    The bar uses '#' for filled and '-' for empty space. It ensures that
    any positive percentage shows at least one '#' block unless
    ensure_min_one is False.
    """
    if use_rounding:
        filled = int((percent / 100) * bar_len + 0.5)
    else:
        filled = int((percent / 100) * bar_len)

    if ensure_min_one and percent > 0 and filled == 0:
        filled = 1
    filled = min(bar_len, filled)

    hashes = '#' * filled
    dashes = '-' * (bar_len - filled)

    if colored:
        return f"{C_CYAN}{hashes}{C_RESET}{C_DIM}{dashes}{C_RESET}"
    return hashes + dashes


def _get_folder_stats(top_files):
    """Aggregate token, size, and line statistics by parent folders."""
    if not top_files:
        return {}

    folder_stats = {}
    for item in top_files:
        tokens, size, path = item[:3]
        lines = item[4] if len(item) > 4 else 0
        p = Path(path)
        # Traverse up parent folders
        for parent in p.parents:
            # We skip the root '.' as it's already represented by project totals
            if str(parent) == '.':
                continue

            folder_path = parent.as_posix()
            if folder_path not in folder_stats:
                folder_stats[folder_path] = {'tokens': 0, 'size': 0, 'lines': 0, 'files': 0}

            folder_stats[folder_path]['tokens'] += (tokens or 0)
            folder_stats[folder_path]['size'] += (size or 0)
            folder_stats[folder_path]['lines'] += (lines or 0)
            folder_stats[folder_path]['files'] += 1

    return folder_stats


def _get_summary_top_items(stats, items, is_folder=False):
    """Select the best metric (tokens, lines, or size) and return top 5 items.

    Returns a tuple of (sorted_items, title, total_weight, has_tokens, has_lines).
    """
    if is_folder:
        # items is list of (path, data_dict)
        has_tokens = any(f[1]['tokens'] > 0 for f in items)
        has_lines = any(f[1].get('lines', 0) > 0 for f in items)

        if has_tokens:
            sorted_items = sorted(items, key=lambda x: (-x[1]['tokens'], x[0]))[:5]
            title = "Largest Folders (by tokens)"
            total_weight = stats.get('total_tokens', 0)
        elif has_lines:
            sorted_items = sorted(items, key=lambda x: (-x[1]['lines'], x[0]))[:5]
            title = "Largest Folders (by lines)"
            total_weight = stats.get('total_lines', 0)
        else:
            sorted_items = sorted(items, key=lambda x: (-x[1]['size'], x[0]))[:5]
            title = "Largest Folders (by size)"
            total_weight = stats.get('total_size_bytes', 0)
    else:
        # items is stats['top_files']: list of (tokens, size, path, status, lines)
        has_tokens = any(f[0] > 0 for f in items)
        has_lines = any(len(f) > 4 and f[4] > 0 for f in items)

        if has_tokens:
            sorted_items = sorted(items, key=lambda x: (-x[0], x[2]))[:5]
            title = "Largest Files (by tokens)"
            total_weight = stats.get('total_tokens', 0)
        elif has_lines:
            sorted_items = sorted(items, key=lambda x: (-x[4] if len(x) > 4 else 0, x[2]))[:5]
            title = "Largest Files (by lines)"
            total_weight = stats.get('total_lines', 0)
        else:
            sorted_items = sorted(items, key=lambda x: (-x[1], x[2]))[:5]
            title = "Largest Files (by size)"
            total_weight = stats.get('total_size_bytes', 0)

    return sorted_items, title, total_weight, has_tokens, has_lines


def _format_metadata_summary(meta: Mapping[str, Any], colored: bool = False) -> str:
    """Return file or folder details in an easy-to-read format."""
    parts = []

    # Prepend status indicator if present (for example, [M], [A], [??])
    status_label = ""
    if 'status' in meta and meta['status']:
        status = meta['status']
        label = f"[{status}]"
        if colored:
            if status in ('A', '??'):
                status_label = f"{C_GREEN}{label}{C_RESET} "
            elif status in ('M', 'R'):
                status_label = f"{C_YELLOW}{label}{C_RESET} "
            elif status == 'D':
                status_label = f"{C_RED}{label}{C_RESET} "
            else:
                status_label = f"{label} "
        else:
            status_label = f"{label} "

    if 'files' in meta and meta['files'] is not None:
        count = meta['files']
        parts.append(f"{count} {_plural(count, 'file')}")
    if 'language' in meta and meta['language']:
        parts.append(meta['language'])
    if 'size' in meta and meta['size'] is not None:
        parts.append(utils.format_size(meta['size']))
    if 'lines' in meta and meta['lines'] is not None and meta['lines'] > 0:
        parts.append(f"{meta['lines']:,} {_plural(meta['lines'], 'line')}")
    if 'tokens' in meta and meta['tokens'] is not None and meta['tokens'] > 0:
        count = meta['tokens']
        parts.append(f"{count:,} {_plural(count, 'token')}")

    summary = f"({' • '.join(parts)})" if parts else ""
    if status_label and summary:
        return f" {status_label} {summary}"
    if status_label:
        return f" {status_label.strip()}"
    if summary:
        return f" {summary}"
    return ""


def _construct_git_web_url(remote_url, commit_or_branch, relative_path=None):
    """Convert a Git remote URL into an HTTPS web link for projects or files."""
    if not remote_url:
        return None

    # Normalize remote_url to HTTPS
    # ssh: git@github.com:User/Repo.git -> https://github.com/User/Repo
    # https: https://github.com/User/Repo.git -> https://github.com/User/Repo
    url = remote_url
    if url.startswith('git@'):
        url = url.replace(':', '/', 1).replace('git@', 'https://', 1)

    if url.endswith('.git'):
        url = url[:-4]

    if not relative_path:
        return url

    # Add path and commit/branch based on known providers
    if 'github.com' in url:
        return f"{url}/blob/{commit_or_branch}/{relative_path}"
    if 'gitlab.com' in url:
        return f"{url}/-/blob/{commit_or_branch}/{relative_path}"
    if 'bitbucket.org' in url:
        return f"{url}/src/{commit_or_branch}/{relative_path}"

    return None


def _render_single_pass(template, replacements):
    """Replace many placeholders in a template in a single pass.

    Placeholders are matched in order of longest first to ensure that
    more specific markers (such as {{DIR_SLUG}}) are preferred over
    shorter ones (such as {{DIR}}).
    """
    if not template or not replacements:
        return template or ""

    # Sort keys by length descending to prevent partial prefix matching
    sorted_keys = tuple(sorted(replacements.keys(), key=len, reverse=True))
    pattern = re.compile("|".join(re.escape(k) for k in sorted_keys))
    return pattern.sub(
        lambda m: str(replacements[m.group(0)]) if replacements[m.group(0)] is not None else "",
        template
    )


def _resolve_metadata_placeholders(template, replacements, data):
    """Resolve project, system, datetime, and environment placeholders.

    This consolidates common metadata logic used in both file-level and
    global templates.
    """
    if not template:
        return

    data = data or {}

    # Project-level replacements
    replacements["{{PROJECT_NAME}}"] = data.get('project_name', 'Project')
    replacements["{{PROJECT_VERSION}}"] = data.get('project_version', '')
    replacements["{{PROJECT_DESCRIPTION}}"] = data.get('project_description', '')
    replacements["{{PROJECT_LICENSE}}"] = data.get('project_license', '')
    replacements["{{DATE}}"] = data.get('date', '')
    replacements["{{TIME}}"] = data.get('time', '')
    replacements["{{DATETIME}}"] = data.get('datetime', '')

    # System-level replacements
    replacements["{{OS}}"] = data.get('os', '')
    replacements["{{PYTHON_VERSION}}"] = data.get('python_version', '')
    replacements["{{PLATFORM}}"] = data.get('platform', '')
    replacements["{{ARCH}}"] = data.get('arch', '')

    # Project-level Git info
    for key in (
        'git_branch', 'git_commit', 'git_commit_short', 'git_author',
        'git_author_date', 'git_tag', 'git_status', 'git_diff', 'git_log', 'git_remote_url'
    ):
        placeholder = f"{{{{{key.upper()}}}}}"
        if placeholder not in replacements:
            replacements[placeholder] = data.get(key) or ''

    if "{{PROJECT_URL}}" not in replacements:
        # Prioritize manual project URL override
        if data.get('project_url'):
            replacements["{{PROJECT_URL}}"] = data['project_url']
        else:
            replacements["{{PROJECT_URL}}"] = _construct_git_web_url(
                data.get('git_remote_url'), data.get('git_commit')
            ) or ""

    # Environment variable resolution
    if '{{ENV:' in template:
        env_matches = re.findall(r'{{ENV:([A-Za-z0-9_]+)}}', template)
        for var_name in env_matches:
            replacements[f"{{{{ENV:{var_name}}}}}"] = os.environ.get(var_name, '')


def _render_template(template, relative_path, size=None, tokens=None, lines=None, escape_func=None, modified=None, content=None, custom_languages=None, index=None, total=None, global_size=None, global_tokens=None, global_lines=None, git_info=None, file_path=None):
    """Replace placeholders in a template with file information.

    The placeholders include FILENAME, EXT, STEM, DIR, DIR_SLUG, SIZE,
    TOKENS, LINE_COUNT, MODIFIED, LANG, INDEX, TOTAL, percentages,
    Git info, PROJECT_NAME, and current DATE/TIME.
    """
    if not template:
        return ""

    raw_filename = relative_path.as_posix()
    filename = raw_filename
    ext = relative_path.suffix.lstrip(".") or ""
    stem = relative_path.stem
    parent_dir = relative_path.parent.as_posix()
    dir_slug = _slugify_relative_dir(parent_dir)
    lang = utils.get_language_tag(relative_path, content=content, overrides=custom_languages)

    if escape_func:
        filename = escape_func(filename)
        ext = escape_func(ext)
        stem = escape_func(stem)
        parent_dir = escape_func(parent_dir)
        lang = escape_func(lang)

    replacements = {
        FILENAME_PLACEHOLDER: filename,
        "{{EXT}}": ext,
        "{{STEM}}": stem,
        "{{DIR}}": parent_dir,
        "{{DIR_SLUG}}": dir_slug,
        "{{LANG}}": lang,
    }

    if "{{HASH}}" in template:
        replacements["{{HASH}}"] = (
            hashlib.sha256(content.encode('utf-8', errors='replace')).hexdigest()
            if content is not None
            else ""
        )

    replacements["{{SIZE}}"] = utils.format_size(size) if size is not None else ""
    replacements["{{TOKENS}}"] = f"{tokens:,}" if tokens is not None else ""
    replacements["{{LINE_COUNT}}"] = f"{lines:,}" if lines is not None else ""
    replacements["{{MODIFIED}}"] = (
        datetime.fromtimestamp(modified).isoformat() if modified is not None else ""
    )

    replacements["{{INDEX}}"] = str(index) if index is not None else ""
    replacements["{{TOTAL}}"] = str(total) if total is not None else ""

    def _calc_percent(val, total_val):
        if val is not None and total_val and total_val > 0:
            return f"{(val / total_val * 100):.1f}%"
        return ""

    replacements["{{SIZE_PERCENT}}"] = _calc_percent(size, global_size)
    replacements["{{TOKEN_PERCENT}}"] = _calc_percent(tokens, global_tokens)
    replacements["{{LINE_PERCENT}}"] = _calc_percent(lines, global_lines)

    # Project, System, Datetime, and Git replacements
    _resolve_metadata_placeholders(template, replacements, git_info)

    if git_info:
        replacements["{{FILE_DIFF}}"] = git_info.get('file_diffs', {}).get(raw_filename, '')
        replacements["{{FILE_STATUS}}"] = git_info.get('file_statuses', {}).get(raw_filename, '')

        # Fetch file-specific Git info only if placeholders are present
        file_git_placeholders = ["{{FILE_AUTHOR}}", "{{FILE_AUTHOR_DATE}}", "{{FILE_LOG}}"]
        if any(p in template for p in file_git_placeholders):
            repo_root = git_info.get('git_repo_root')
            file_git_data = _get_file_git_info(raw_filename, repo_root)
            replacements["{{FILE_AUTHOR}}"] = file_git_data.get('file_author', '')
            replacements["{{FILE_AUTHOR_DATE}}"] = file_git_data.get('file_author_date', '')
            replacements["{{FILE_LOG}}"] = file_git_data.get('file_log', '')

        # Construct FILE_URL only if the placeholder is present
        if "{{FILE_URL}}" in template:
            remote_url = git_info.get('git_remote_url')
            if remote_url:
                commit = git_info.get('git_commit')
                repo_root = git_info.get('git_repo_root')
                if commit and repo_root:
                    # Use provided file_path or try to resolve it from relative_path
                    try:
                        target_file = Path(file_path) if file_path else (Path(repo_root) / raw_filename)
                        abs_file = target_file.resolve()
                        rel_to_repo = abs_file.relative_to(Path(repo_root).resolve()).as_posix()
                        replacements["{{FILE_URL}}"] = _construct_git_web_url(remote_url, commit, rel_to_repo) or ""
                    except (ValueError, OSError):
                        replacements["{{FILE_URL}}"] = ""

    return _render_single_pass(template, replacements)


def _render_global_template(template, stats):
    """Replace placeholders in a global template with project information.

    The placeholders include FILE_COUNT, TOTAL_SIZE, TOTAL_TOKENS, and TOTAL_LINES,
    as well as Git information, PROJECT_NAME, and current DATE/TIME if available.
    """
    if not template:
        return ""

    if stats is None:
        return template

    file_count = stats.get('total_files', 0)
    total_size = utils.format_size(stats.get('total_size_bytes', 0))
    total_tokens = stats.get('total_tokens', 0)
    total_lines = stats.get('total_lines', 0)
    is_approx = stats.get('token_count_is_approx', False)
    token_str = format_tokens(total_tokens, is_approx)

    replacements = {
        "{{FILE_COUNT}}": f"{file_count:,}",
        "{{TOTAL_SIZE}}": total_size,
        "{{TOTAL_TOKENS}}": token_str,
        "{{TOTAL_LINES}}": f"{total_lines:,}",
    }

    # Project, System, Datetime, and Git replacements
    _resolve_metadata_placeholders(template, replacements, stats)

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
def _matches_folder_glob_cached(parts, patterns):
    parts_cf = tuple(p.casefold() for p in parts)

    for pattern in patterns:
        # Check individual parts (for example, 'node_modules')
        if any(fnmatch.fnmatchcase(p_cf, pattern) for p_cf in parts_cf):
            return True

        # Check all parent paths to ensure recursive exclusion (for example, 'src/generated'
        # matches 'src/generated/assets')
        current = ""
        for p_cf in parts_cf:
            current = (current + "/" + p_cf) if current else p_cf
            if fnmatch.fnmatchcase(current, pattern):
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

    When ``return_reason`` is ``True``, it returns a pair of ``(true or false, reason)``.
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
        relative_path.parent.parts, exclusion_folders
    ):
        return (False, 'excluded') if return_reason else False

    allowed_extensions = search_opts.get('effective_allowed_extensions') or ()
    suffix = relative_path.suffix.lower()
    if allowed_extensions and suffix not in allowed_extensions:
        return (False, 'extension') if return_reason else False

    exclude_extensions = search_opts.get('effective_exclude_extensions') or ()
    if exclude_extensions and suffix in exclude_extensions:
        return (False, 'extension') if return_reason else False

    allowed_languages = search_opts.get('allowed_languages')
    exclude_languages = search_opts.get('exclude_languages')

    if allowed_languages or exclude_languages:
        # For language filtering, we might need to look at the content if the extension is
        # missing or unrecognized.
        sample_content = None
        if not suffix or (suffix not in utils.EXTENSION_TO_LANG and file_name.lower() not in utils.FILENAME_TO_LANG):
            if virtual_content:
                sample_content = (
                    virtual_content.decode('utf-8', errors='replace')
                    if isinstance(virtual_content, bytes)
                    else virtual_content
                )
            elif file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        sample_content = f.readline()
                except OSError:
                    pass

        custom_languages = search_opts.get('custom_languages')
        lang = utils.get_language_tag(relative_path, content=sample_content, overrides=custom_languages)

        if exclude_languages and lang in exclude_languages:
            return (False, 'language_excluded') if return_reason else False

        if allowed_languages and lang not in allowed_languages:
            return (False, 'language_mismatch') if return_reason else False

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
            stat = file_path.stat()
            file_size = stat.st_size
            mtime = stat.st_mtime

            since = filter_opts.get('modified_since', 0)
            if since > 0 and mtime < since:
                return (False, 'modified_since') if return_reason else False

            until = filter_opts.get('modified_until', 0)
            if until > 0 and mtime > until:
                return (False, 'modified_until') if return_reason else False
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

    grep_pattern = filter_opts.get('grep')
    exclude_grep_pattern = filter_opts.get('exclude_grep')
    min_tokens = filter_opts.get('min_tokens', 0)
    max_tokens = filter_opts.get('max_tokens', 0)
    min_lines = filter_opts.get('min_lines', 0)
    max_lines = filter_opts.get('max_lines', 0)

    if grep_pattern or exclude_grep_pattern or min_tokens > 0 or max_tokens > 0 or min_lines > 0 or max_lines > 0:
        try:
            if virtual_content is not None:
                content = (
                    virtual_content.decode('utf-8', errors='replace')
                    if isinstance(virtual_content, bytes)
                    else virtual_content
                )
            elif file_path is not None:
                # We use read_file_best_effort to be consistent with how files are combined.
                content, _ = read_file_best_effort(file_path)
            else:
                content = ""

            if grep_pattern and not re.search(grep_pattern, content):
                return (False, 'grep_mismatch') if return_reason else False

            if exclude_grep_pattern and re.search(exclude_grep_pattern, content):
                return (False, 'exclude_grep_match') if return_reason else False

            if min_tokens > 0 or max_tokens > 0:
                tokens, _ = utils.estimate_tokens(content)
                if min_tokens > 0 and tokens < min_tokens:
                    return (False, 'too_few_tokens') if return_reason else False
                if max_tokens > 0 and tokens > max_tokens:
                    return (False, 'too_many_tokens') if return_reason else False

            if min_lines > 0 or max_lines > 0:
                lines = utils.count_lines(content)
                if min_lines > 0 and lines < min_lines:
                    return (False, 'too_few_lines') if return_reason else False
                if max_lines > 0 and lines > max_lines:
                    return (False, 'too_many_lines') if return_reason else False

        except Exception as exc:
            logging.warning("Error while checking content patterns or metrics on '%s': %s", rel_str, exc)
            return (False, 'grep_error') if return_reason else False

    return (True, None) if return_reason else True


def _parse_git_diff_by_file(diff_text):
    """Parse a multi-file Git diff into a dictionary of file paths to diff hunks."""
    if not diff_text:
        return {}

    file_diffs = {}
    # Use finditer to locate all lines starting with 'diff --git '
    diff_headers = []
    for match in re.finditer(r'^diff --git (.*)$', diff_text, re.MULTILINE):
        diff_headers.append((match.start(), match.group(1)))

    for i, (start, header) in enumerate(diff_headers):
        # The header is typically 'a/path b/path' or '"a/path" "b/path"'
        # Git quotes the path if it contains special characters such as spaces.
        if header.endswith('"'):
            # Find the start of the second path part, which starts with ' "b/'
            # rfind ensures we get the last occurrence, as the first path could also be quoted.
            second_path_marker = header.rfind(' "b/')
            if second_path_marker != -1:
                filename = header[second_path_marker + 4 : -1]
            else:
                # Fallback for unexpected formats
                filename = header.split(' ')[-1].strip('"').replace('b/', '', 1)
        else:
            # Unquoted path, find the last ' b/' marker.
            second_path_marker = header.rfind(' b/')
            if second_path_marker != -1:
                filename = header[second_path_marker + 3 :]
            else:
                # Fallback for unexpected formats
                filename = header.split(' ')[-1].replace('b/', '', 1)

        end = diff_headers[i + 1][0] if i + 1 < len(diff_headers) else len(diff_text)
        file_diffs[filename] = diff_text[start:end].strip()

    return file_diffs


@lru_cache(maxsize=1024)
def _get_file_git_info(file_path, repo_root):
    """Retrieve the last author, date, and commit message for a specific file."""
    if not repo_root or not file_path:
        return {}

    try:
        # %an: author name, %ai: author date (ISO 8601-compatible), %s: subject
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%an%n%ai%n%s', '--', file_path],
            cwd=repo_root, capture_output=True, text=True, check=True
        )
        lines = result.stdout.splitlines()
        if len(lines) >= 3:
            return {
                'file_author': lines[0],
                'file_author_date': lines[1],
                'file_log': lines[2]
            }
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return {}


def _get_git_info(root_folder, log_count=0, include_diff=False, diff_ref=None, staged=False, unstaged=False):
    """Retrieve Git branch, commit, and status information for the project.

    Returns a dictionary containing 'git_branch', 'git_commit', 'git_commit_short',
    'git_log', 'git_status', 'file_statuses', 'git_diff', and 'file_diffs'.
    """
    info = {
        'git_branch': 'N/A',
        'git_commit': 'N/A',
        'git_commit_short': 'N/A',
        'git_author': 'N/A',
        'git_author_date': 'N/A',
        'git_tag': None,
        'git_log': None,
        'git_status': None,
        'git_diff': None,
        'git_remote_url': None,
        'git_repo_root': None,
        'file_statuses': {},
        'file_diffs': {}
    }

    root_path = Path(root_folder)
    git_cwd = root_path.parent if root_path.is_file() else root_path
    try:
        # Get repo root
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=git_cwd, capture_output=True, text=True, check=True
        )
        info['git_repo_root'] = Path(result.stdout.strip()).as_posix()

        # Get branch name
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=git_cwd, capture_output=True, text=True, check=True
        )
        info['git_branch'] = result.stdout.strip()

        # Get full commit hash, author and date
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H%n%an%n%ai'],
                cwd=git_cwd, capture_output=True, text=True, check=True
            )
            lines = result.stdout.splitlines()
            if len(lines) >= 3:
                info['git_commit'] = lines[0]
                info['git_commit_short'] = info['git_commit'][:7]
                info['git_author'] = lines[1]
                info['git_author_date'] = lines[2]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            # Fallback to rev-parse if git log fails (for example, empty repo or shallow clone issues)
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=git_cwd, capture_output=True, text=True, check=True
            )
            info['git_commit'] = result.stdout.strip()
            info['git_commit_short'] = info['git_commit'][:7]

        # Get latest tag
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                cwd=git_cwd, capture_output=True, text=True, check=True
            )
            info['git_tag'] = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

        # Get remote URL
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=git_cwd, capture_output=True, text=True, check=True
            )
            info['git_remote_url'] = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

        # Get porcelain status for WIP overview and tree labels
        result = subprocess.run(
            ['git', 'status', '--porcelain', '-uall'],
            cwd=git_cwd, capture_output=True, text=True, check=True
        )
        status_lines = result.stdout.splitlines()
        if status_lines:
            counts = {'M': 0, 'A': 0, '?': 0, 'R': 0, 'D': 0}
            for line in status_lines:
                if len(line) < 4:
                    continue
                # X is index status, Y is work tree status
                x, y = line[0], line[1]
                path = line[3:].strip().strip('"')

                # Determine primary status for this file
                if x == '?' or y == '?':
                    status_code = '??'
                    counts['?'] += 1
                elif x == 'A' or y == 'A':
                    status_code = 'A'
                    counts['A'] += 1
                elif x == 'M' or y == 'M':
                    status_code = 'M'
                    counts['M'] += 1
                elif x == 'R' or y == 'R':
                    status_code = 'R'
                    counts['R'] += 1
                    # Handle renames such as "old -> new"
                    if " -> " in path:
                        path = path.split(" -> ")[-1].strip().strip('"')
                elif x == 'D' or y == 'D':
                    status_code = 'D'
                    counts['D'] += 1
                else:
                    status_code = None

                if status_code:
                    info['file_statuses'][path] = status_code

            summary_parts = []
            if counts['M'] > 0: summary_parts.append(f"{counts['M']} modified")
            if counts['A'] > 0: summary_parts.append(f"{counts['A']} added")
            if counts['?'] > 0: summary_parts.append(f"{counts['?']} untracked")
            if counts['R'] > 0: summary_parts.append(f"{counts['R']} renamed")
            if counts['D'] > 0: summary_parts.append(f"{counts['D']} deleted")

            if summary_parts:
                info['git_status'] = ", ".join(summary_parts)

        # Get recent log if requested
        if log_count > 0:
            result = subprocess.run(
                ['git', 'log', f'-{log_count}', '--oneline', '--no-decorate'],
                cwd=git_cwd, capture_output=True, text=True, check=True
            )
            info['git_log'] = result.stdout.strip()

        # Get diff if requested
        if include_diff:
            diff_cmd = ['git', 'diff', '--relative']
            if staged:
                diff_cmd.append('--cached')
                if diff_ref:
                    diff_cmd.append(diff_ref)
            elif unstaged:
                # No extra flags needed for unstaged, but we don't pass diff_ref
                # to match collect_git_diff_files behavior for unstaged.
                pass
            elif diff_ref:
                diff_cmd.append(diff_ref)
            else:
                diff_cmd.append('HEAD')

            result = subprocess.run(
                diff_cmd,
                cwd=git_cwd, capture_output=True, text=True, check=True
            )
            info['git_diff'] = result.stdout.strip()
            info['file_diffs'] = _parse_git_diff_by_file(info['git_diff'])

    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return info


def collect_git_files(root_folder, progress=None):
    """Use git ls-files to find files in the repository.

    Returns (file_paths, root_path, excluded_folder_count) if successful, else None.
    """
    root_path = Path(root_folder)
    git_cwd = root_path.parent if root_path.is_file() else root_path
    try:
        # Run git ls-files to get all tracked and untracked files (ignoring those in .gitignore)
        # --cached: show tracked files
        # --others: show untracked files
        # --exclude-standard: use standard git exclusion rules (.gitignore and other standard rules)
        result = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
            cwd=git_cwd,
            capture_output=True,
            text=True,
            check=True
        )
        file_paths = []
        for line in result.stdout.splitlines():
            if line:
                file_paths.append(git_cwd / line)
                if progress is not None:
                    progress.update(1)

        # Sort for deterministic output
        file_paths.sort()
        return file_paths, git_cwd, 0
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        logging.warning(
            "Finding files with Git failed in '%s': %s. Falling back to standard scanning.",
            root_folder,
            exc,
        )
        return None


def collect_git_diff_files(root_folder, diff_ref=None, progress=None, staged_only=False, unstaged_only=False):
    """Use git diff to find changed files in the repository.

    Returns (file_paths, root_path, excluded_folder_count) if successful, else None.
    """
    root_path = Path(root_folder)
    git_cwd = root_path.parent if root_path.is_file() else root_path
    try:
        file_paths_set = set()

        def _run_git(args):
            result = subprocess.run(
                args, cwd=git_cwd, capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                if line:
                    file_paths_set.add(line)

        # Determine which changes to include
        if staged_only:
            # Staged changes only
            cmd = ['git', 'diff', '--name-only', '--cached', '--relative']
            if diff_ref:
                cmd.append(diff_ref)
            _run_git(cmd)

        elif unstaged_only:
            # Unstaged changes only (modified but not staged).
            # We ignore diff_ref here because 'unstaged' is defined relative to the index.
            _run_git(['git', 'diff', '--name-only', '--relative'])
            # Also include untracked files for unstaged search
            _run_git(['git', 'ls-files', '--others', '--exclude-standard', '--', '.'])

        else:
            # Default: staged + unstaged + untracked
            _run_git(['git', 'diff', '--name-only', '--relative', diff_ref or 'HEAD'])
            # Untracked files
            _run_git(['git', 'ls-files', '--others', '--exclude-standard', '--', '.'])

        file_paths = []
        for rel_path in sorted(file_paths_set):
            p = git_cwd / rel_path
            # Filter out deleted files
            if p.is_file():
                file_paths.append(p)
                if progress is not None:
                    progress.update(1)

        return file_paths, git_cwd, 0
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        logging.warning(
            "Finding changed files with Git failed in '%s': %s. Falling back to standard scanning.",
            root_folder,
            exc,
        )
        return None


def collect_file_paths(root_folder, recursive, exclude_folders, progress=None, max_depth=0, use_git=False, use_git_diff=False, git_diff_ref=None, git_staged=False, git_unstaged=False):
    """Return all paths in ``root_folder`` while skipping excluded folders.

    If ``root_folder`` is a file, it returns a list containing only that file.
    """
    root_path = Path(root_folder)
    try:
        if root_path.is_file():
            if progress is not None:
                progress.update(1)
            # Use parent as root for absolute paths, but preserve context for relative paths
            root = root_path.parent if root_path.is_absolute() else Path('.')
            return [root_path], root, 0

        git_results = None
        if use_git_diff:
            git_results = collect_git_diff_files(
                root_folder, diff_ref=git_diff_ref, progress=progress,
                staged_only=git_staged, unstaged_only=git_unstaged
            )

        if git_results is None and use_git:
            git_results = collect_git_files(root_folder, progress=progress)

        if git_results is not None:
            file_paths, root, excluded = git_results
            # Apply common Git post-processing filters (depth and exclusions)
            if max_depth > 0:
                file_paths = [
                    p for p in file_paths
                    if len(p.relative_to(root).parts) <= max_depth
                ]

            exclude_patterns = _normalize_patterns(exclude_folders)
            if exclude_patterns:
                def _is_excluded(p):
                    rel_p = p.relative_to(root)
                    return _matches_folder_glob_cached(
                        rel_p.parent.parts, exclude_patterns
                    )

                file_paths = [p for p in file_paths if not _is_excluded(p)]

            return file_paths, root, excluded
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
        parts = relative_path.parts
        excluded = _matches_folder_glob_cached(parts, exclude_patterns)
        if excluded:
            logging.debug("Skipping folder: %s", relative_path.as_posix())
        return excluded

    if recursive:
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                rel_dir = Path(dirpath).relative_to(root_path)
                current_depth = len(rel_dir.parts)

                if max_depth > 0 and current_depth >= max_depth:
                    dirnames[:] = []
                    continue

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
    """Apply filters to ``file_paths`` and return the matches.

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
    stats: Mapping[str, Any] = None,
    index: int = None,
    total: int = None,
    custom_languages: Mapping[str, str] = None,
) -> str:
    """Render the paired filename template with placeholders."""

    source_ext = source_path.suffix if source_path else ''
    header_ext = header_path.suffix if header_path else ''
    dir_value = relative_dir.as_posix()
    dir_slug = _slugify_relative_dir(dir_value)

    # Detect language from primary file if available
    primary_path = source_path or header_path
    lang = ""
    if primary_path:
        lang = utils.get_language_tag(primary_path, overrides=custom_languages)

    replacements = {
        '{{STEM}}': stem,
        '{{SOURCE_EXT}}': source_ext,
        '{{HEADER_EXT}}': header_ext,
        '{{DIR}}': dir_value,
        '{{DIR_SLUG}}': dir_slug,
        '{{LANG}}': lang,
        '{{INDEX}}': str(index) if index is not None else "",
        '{{TOTAL}}': str(total) if total is not None else "",
    }

    # Project, System, Datetime, and Git replacements
    _resolve_metadata_placeholders(template, replacements, stats)

    # Validate that all {{...}} placeholders in the template are known
    for match in re.finditer(r"{{([A-Za-z0-9_:]+)}}", template):
        placeholder = match.group(0)
        if placeholder not in replacements:
            raise ValueError(
                f"Unknown placeholder '{{{{{match.group(1)}}}}}' in paired filename template"
            )

    return _render_single_pass(template, replacements)


def _group_paths_by_stem_suffix(file_paths, *, root_path):
    """Group ``file_paths`` by stem and suffix for pairing logic.
    
    Returns a dict mapping Path stems to a dict of extensions.
    Each file is represented by its full relative stem.
    """

    grouped = {}
    for file_path in file_paths:
        try:
            relative = file_path.relative_to(root_path)
        except ValueError:
            relative = None

        stem_path = (relative or file_path).with_suffix("")
        grouped.setdefault(stem_path, {}).setdefault(file_path.suffix.lower(), []).append(
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
    """Return a list of (pairing_key, paths) tuples for paired files.

    We use a two-pass approach:
    1. Exact matches by full relative path.
    2. Convention-based matches by dropping the top-level folder (for example, src/ vs include/).
    """

    file_map = _group_paths_by_stem_suffix(filtered_paths, root_path=root_path)
    paired = []
    used_files = set()

    # Pass 1: Exact matches (Full relative paths)
    # This handles src/app/main.cpp and tests/app/main.cpp correctly.
    for stem, ext_map in file_map.items():
        src = _select_preferred_path(ext_map, source_exts)
        hdr = _select_preferred_path(ext_map, header_exts)
        if src and hdr:
            pair = [src]
            if hdr != src:
                pair.append(hdr)
            paired.append((stem, pair))
            used_files.update(pair)

    # Pass 2: Convention matches (Shortened paths)
    # This handles src/main.cpp and include/main.h.
    remaining_files = [p for p in filtered_paths if p not in used_files]
    if remaining_files:
        truncated_map = {}
        for p in remaining_files:
            try:
                relative = p.relative_to(root_path)
            except ValueError:
                relative = None

            stem = (relative or p).with_suffix("")
            if relative is not None and len(stem.parts) > 1:
                truncated_stem = Path(*stem.parts[1:])
                truncated_map.setdefault(truncated_stem, {}).setdefault(p.suffix.lower(), []).append(p)

        for t_stem, ext_map in truncated_map.items():
            # Only pair if the shortened stem is unambiguous
            src = _select_preferred_path(ext_map, source_exts)
            hdr = _select_preferred_path(ext_map, header_exts)

            if src and hdr:
                pair = [src]
                if hdr != src:
                    pair.append(hdr)
                # Use the full path of the source as the key for consistency
                pair_key = _get_rel_path(src, root_path).with_suffix("")
                paired.append((pair_key, pair))
                used_files.update(pair)

    # Final Pass: Mismatched files if requested
    if include_mismatched:
        for p in filtered_paths:
            if p not in used_files:
                pair_key = _get_rel_path(p, root_path)
                paired.append((pair_key, [p]))
                used_files.add(p)

    return paired


def _process_paired_files(
    paired_items,
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
    pair_index=None,
    total_pairs=None,
):
    """Process paired files and write combined outputs."""

    size_excluded_set = set(size_excluded or [])
    running_tokens = 0
    running_lines = 0
    running_size = 0
    total_items = total_pairs if total_pairs is not None else len(paired_items)
    for i, (pairing_key, paths) in enumerate(paired_items):
        item_index = pair_index if pair_index is not None else (i + 1)
        stem = Path(pairing_key).name
        if processing_bar:
            processing_bar.set_description(f"Pairing {_truncate_path(stem, 40)}")
        ext_map = {p.suffix.lower(): [p] for p in paths}
        source_path = _select_preferred_path(ext_map, source_exts)
        header_path = _select_preferred_path(ext_map, header_exts)

        primary_path = source_path or header_path or paths[0]
        relative_dir = _get_rel_path(primary_path, root_path).parent

        # If it's a mismatched file (no header/source pair), use the full relative path
        # as the output filename to avoid collisions if multiple files share the same stem
        # but have different extensions (and include_mismatched is True).
        if not source_path and not header_path and len(paths) == 1:
            out_filename = _get_rel_path(paths[0], root_path).as_posix()
        else:
            out_filename = _render_paired_filename(
                template,
                stem,
                source_path,
                header_path,
                relative_dir=relative_dir,
                stats=stats,
                index=item_index,
                total=total_items,
                custom_languages=processor.custom_languages,
            )
        out_path = Path(out_filename)
        if out_path.is_absolute():
            raise utils.InvalidConfigError(
                "Paired filename template must produce a relative path"
            )

        if out_folder:
            out_file = out_folder / out_path
        else:
            if len(out_path.parts) > 1:
                out_file = root_path / out_path
            else:
                out_file = primary_path.parent / out_path

        try:
            abs_out = out_file.resolve()
            if any(p.resolve() == abs_out for p in paths):
                logging.warning(
                    "Skipping pair '%s' because its output path would overwrite one of its input files: %s",
                    stem, out_file
                )
                if processing_bar:
                    processing_bar.update(len(paths))
                continue
        except OSError:
            pass

        if dry_run:
            logging.info("[PAIR %s] -> %s", stem, out_file)
            for path in paths:
                logging.info("  - %s", _get_rel_path(path, root_path))

            if not estimate_tokens and getattr(processor, 'show_diff', False) is not True:
                if stats is not None:
                    for path in paths:
                        rel_p_str = _get_rel_path(path, root_path).as_posix()
                        status = stats.get('file_statuses', {}).get(rel_p_str)
                        lang = _get_stat_lang(path, stats)
                        stats['top_files'].append((0, path.stat().st_size if path.exists() else 0, rel_p_str, status, 0, lang))
                continue

        pair_buffer = None
        if estimate_tokens:
            pair_out_ctx = _DevNull()
        elif dry_run and getattr(processor, 'show_diff', False) is True:
            pair_buffer = io.StringIO()
            pair_out_ctx = nullcontext(pair_buffer)
        else:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            pair_out_ctx = open(out_file, 'w', encoding='utf8', newline='')

        with pair_out_ctx as pair_out:
            if global_header and not estimate_tokens:
                pair_out.write(_render_global_template(global_header, stats))

            pair_size = sum(p.stat().st_size if p.exists() else 0 for p in paths)
            pair_tokens = 0
            pair_lines = 0

            # For percentages in paired mode, we might want them relative to the pair
            # but the processor usually uses global stats.
            # If we want them relative to the pair, we need to pass the pair totals.
            # The test expects them relative to the pair.

            if primary_path in size_excluded_set:
                token_count, is_approx, line_count = processor.write_max_size_placeholder(
                    primary_path, root_path, pair_out,
                    index=item_index, total=total_items,
                    global_size=pair_size,
                    global_tokens=None, # We don't have pair tokens yet
                    global_lines=None
                )
                f_size = primary_path.stat().st_size if primary_path.exists() else 0
                if stats is not None:
                    _update_stats_metrics(stats, token_count, line_count, is_approx)
                    _update_token_stats(stats, primary_path, token_count)
                    _update_line_stats(stats, primary_path, line_count)
                    rel_p_str = _get_rel_path(primary_path, root_path).as_posix()
                    status = stats.get('file_statuses', {}).get(rel_p_str)
                    lang = _get_stat_lang(primary_path, stats)
                    stats['top_files'].append((token_count, f_size, rel_p_str, status, line_count, lang))

                running_tokens += token_count
                running_lines += line_count
                running_size += f_size
                if processing_bar:
                    processing_bar.set_postfix(size=utils.format_size(running_size), lines=f"{running_lines:,}", tokens=f"{running_tokens:,}")
                    processing_bar.update(len(paths))
            else:
                # First pass to get pair totals if needed for percentages
                pair_tokens = 0
                pair_lines = 0
                for file_path in paths:
                    content, _ = read_file_best_effort(file_path)
                    lang = utils.get_language_tag(file_path, content=content, overrides=processor.custom_languages)
                    processed = utils.process_content(content, processor.processing_opts, language=lang)
                    tokens, _ = utils.estimate_tokens(processed)
                    pair_tokens += tokens
                    pair_lines += utils.count_lines(processed)

                for file_path in paths:
                    if file_path in size_excluded_set:
                        token_count, is_approx, line_count = processor.write_max_size_placeholder(
                            file_path, root_path, pair_out,
                            index=item_index, total=total_items,
                            global_size=pair_size,
                            global_tokens=pair_tokens,
                            global_lines=pair_lines
                        )
                    else:
                        token_count, is_approx, line_count = processor.process_and_write(
                            file_path,
                            root_path,
                            pair_out,
                            index=item_index, total=total_items,
                            global_size=pair_size,
                            global_tokens=pair_tokens,
                            global_lines=pair_lines
                        )
                    f_size = file_path.stat().st_size if file_path.exists() else 0
                    if stats is not None:
                        _update_stats_metrics(stats, token_count, line_count, is_approx)
                        _update_token_stats(stats, file_path, token_count)
                        _update_line_stats(stats, file_path, line_count)
                        rel_p_str = _get_rel_path(file_path, root_path).as_posix()
                        status = stats.get('file_statuses', {}).get(rel_p_str)
                        lang = _get_stat_lang(file_path, stats)
                        stats['top_files'].append((token_count, f_size, rel_p_str, status, line_count, lang))

                    running_tokens += token_count
                    running_lines += line_count
                    running_size += f_size
                    if processing_bar:
                        processing_bar.set_postfix(size=utils.format_size(running_size), lines=f"{running_lines:,}", tokens=f"{running_tokens:,}")
                        processing_bar.update(1)

            if global_footer and not estimate_tokens:
                pair_out.write(_render_global_template(global_footer, stats))

        if dry_run and getattr(processor, 'show_diff', False) is True and pair_buffer is not None:
            if out_file.exists():
                old_content, _ = read_file_best_effort(out_file)
                _print_diff(old_content, pair_buffer.getvalue(), out_file.as_posix())


def _get_stat_ext(file_path):
    """Return the normalized extension or '.no_extension' for stats tracking."""
    ext = file_path.suffix.lower() if hasattr(file_path, 'suffix') else Path(file_path).suffix.lower()
    return ext or '.no_extension'


def _get_stat_lang(file_path, stats):
    """Return the programming language tag for stats tracking."""
    return utils.get_language_tag(file_path, overrides=stats.get('custom_languages'))


def _update_file_stats(stats, file_path, size=None):
    stats['total_files'] += 1
    if size is None:
        try:
            size = file_path.stat().st_size
        except OSError:
            size = 0
    stats['total_size_bytes'] += size

    ext = _get_stat_ext(file_path)
    if 'files_by_extension' in stats:
        stats['files_by_extension'][ext] = stats['files_by_extension'].get(ext, 0) + 1
        if 'size_by_extension' in stats:
            stats['size_by_extension'][ext] = stats['size_by_extension'].get(ext, 0) + size

    if 'files_by_language' in stats:
        lang = _get_stat_lang(file_path, stats)
        stats['files_by_language'][lang] = stats['files_by_language'].get(lang, 0) + 1
        if 'size_by_language' in stats:
            stats['size_by_language'][lang] = stats['size_by_language'].get(lang, 0) + size


def _update_token_stats(stats, file_path, tokens):
    if tokens:
        ext = _get_stat_ext(file_path)
        if 'tokens_by_extension' in stats:
            stats['tokens_by_extension'][ext] = stats['tokens_by_extension'].get(ext, 0) + tokens

        if 'tokens_by_language' in stats:
            lang = _get_stat_lang(file_path, stats)
            stats['tokens_by_language'][lang] = stats['tokens_by_language'].get(lang, 0) + tokens


def _update_line_stats(stats, file_path, lines):
    if lines:
        ext = _get_stat_ext(file_path)
        if 'lines_by_extension' in stats:
            stats['lines_by_extension'][ext] = stats['lines_by_extension'].get(ext, 0) + lines

        if 'lines_by_language' in stats:
            lang = _get_stat_lang(file_path, stats)
            stats['lines_by_language'][lang] = stats['lines_by_language'].get(lang, 0) + lines


def _update_stats_metrics(stats, tokens, lines, is_approx):
    """Update global project metrics in the stats dictionary."""
    stats['total_tokens'] = stats.get('total_tokens', 0) + tokens
    stats['total_lines'] = stats.get('total_lines', 0) + lines
    if is_approx:
        stats['token_count_is_approx'] = True


def _populate_project_stats(stats, root_folder, config):
    """Gather project identity, system info, and manual overrides."""
    stats.update(utils.get_project_identity(root_folder))
    stats.update(utils.get_datetime_placeholders())
    stats.update(utils.get_system_info())

    project_meta = config.get('project', {})
    if project_meta.get('name'):
        stats['project_name'] = project_meta['name']
    if project_meta.get('version'):
        stats['project_version'] = project_meta['version']
    if project_meta.get('description'):
        stats['project_description'] = project_meta['description']
    if project_meta.get('license'):
        stats['project_license'] = project_meta['license']
    if project_meta.get('url'):
        stats['project_url'] = project_meta['url']


def _apply_project_overrides(config, args):
    """Apply project metadata CLI overrides to the configuration."""
    project_conf = config.setdefault('project', {})
    if project_conf is None:
        project_conf = config['project'] = {}

    if getattr(args, 'project_name', None) is not None:
        project_conf['name'] = args.project_name
    if getattr(args, 'project_version', None) is not None:
        project_conf['version'] = args.project_version
    if getattr(args, 'project_description', None) is not None:
        project_conf['description'] = args.project_description
    if getattr(args, 'project_license', None) is not None:
        project_conf['license'] = args.project_license
    if getattr(args, 'project_url', None) is not None:
        project_conf['url'] = args.project_url


class FileProcessor:
    """Process files according to configuration and write them to an output.

    Parameters
    ----------
    config : dict
        Settings containing ``processing`` and output rules for files.
    output_opts : dict
        Options that control how processed content is written, including
        header/footer templates and whether to include line numbers.
    dry_run : bool, optional
        When ``True``, only log the files that would be processed without
        performing any writes.
    """

    def __init__(self, config, output_opts, dry_run=False, estimate_tokens=False, output_format='text', git_info=None):
        self.config = config
        self.search_opts = config.get('search', {}) or {}
        self.custom_languages = self.search_opts.get('custom_languages', {})
        self.output_opts = output_opts or {}
        self.git_info = git_info
        self.dry_run = dry_run
        self.estimate_tokens = estimate_tokens
        self.output_format = output_format
        self.skip_content = bool(self.output_opts.get('skip_content', False))
        self.show_diff = bool(self.output_opts.get('show_diff', False))
        self.processing_opts = config.get('processing', {}) or {}
        self.apply_in_place = bool(self.processing_opts.get('apply_in_place'))
        if self.apply_in_place:
            self.create_backups = bool(
                self.processing_opts.get('create_backups', True)
            )
        else:
            self.create_backups = False
        self.seen_hashes = set()
        self.csv_writer = None

    def _make_bar(self, **kwargs):
        return _progress_bar(enabled=_progress_enabled(self.dry_run), **kwargs)

    def _write_with_templates(self, outfile, content, relative_path, size=None, tokens=None, lines=None, modified=None, index=None, total=None, global_size=None, global_tokens=None, global_lines=None, file_path=None):
        """Write ``content`` with configured header/footer templates."""

        header_template = self.output_opts.get(
            'header_template', utils.DEFAULT_CONFIG['output']['header_template']
        )
        footer_template = self.output_opts.get(
            'footer_template', utils.DEFAULT_CONFIG['output']['footer_template']
        )

        escape_func = xml_escape if self.output_format == 'xml' else None

        if self.output_format not in ("json", "jsonl", "manifest", "csv"):
            outfile.write(_render_template(
                header_template, relative_path, size=size, tokens=tokens, lines=lines,
                escape_func=escape_func, modified=modified, content=content,
                custom_languages=self.custom_languages, index=index, total=total,
                global_size=global_size, global_tokens=global_tokens, global_lines=global_lines,
                git_info=self.git_info, file_path=file_path
            ))
        outfile.write(content)
        if self.output_format not in ("json", "jsonl", "manifest", "csv"):
            outfile.write(_render_template(
                footer_template, relative_path, size=size, tokens=tokens, lines=lines,
                escape_func=escape_func, modified=modified, content=content,
                custom_languages=self.custom_languages, index=index, total=total,
                global_size=global_size, global_tokens=global_tokens, global_lines=global_lines,
                git_info=self.git_info, file_path=file_path
            ))

    def get_content_hash(self, content):
        """Return the SHA-256 hash of the content."""
        return hashlib.sha256(content.encode('utf-8', errors='replace')).hexdigest()

    def _backup_file(self, file_path):
        """Create a ``.bak`` backup for ``file_path`` when backups are enabled.

        The backup is an exact copy of the original file and keeps its
        details (such as the date it was changed). If ``create_backups`` is ``False``
        no action is taken. Failures to copy raise ``utils.InvalidConfigError`` so the
        tool stops before overwriting code.
        """

        if not self.create_backups:
            return

        backup_path = Path(f"{file_path}.bak")
        try:
            shutil.copy2(file_path, backup_path)
        except OSError as exc:
            raise utils.InvalidConfigError(
                f"Failed to create backup for '{file_path}': {exc}"
            ) from exc

    def _apply_inplace_if_needed(self, file_path, root_path, content, processed_content, encoding, dry_run=None, estimate_tokens=None):
        """Apply in-place updates and print diffs if configured."""
        if dry_run is None:
            dry_run = self.dry_run
        if estimate_tokens is None:
            estimate_tokens = self.estimate_tokens

        if not self.apply_in_place or processed_content == content:
            return

        if self.show_diff:
            _print_diff(content, processed_content, _get_rel_path(file_path, root_path).as_posix())

        if not estimate_tokens and not dry_run:
            logging.info("Updating in place: %s (encoding: %s)", file_path, encoding)
            self._backup_file(file_path)
            file_path.write_text(processed_content, encoding=encoding, newline='')

    def _emit_entry(
        self,
        outfile,
        content,
        relative_path,
        file_size,
        token_count,
        is_approx,
        line_count,
        include_line_numbers=True,
        modified=None,
        index=None,
        total=None,
        global_size=None,
        global_tokens=None,
        global_lines=None,
        file_path=None,
    ):
        """Format and write a single file entry to the output stream."""
        if self.estimate_tokens:
            return

        if self.output_format in ("json", "jsonl", "manifest"):
            entry = {
                "path": relative_path.as_posix(),
                "size_bytes": file_size,
                "tokens": token_count,
                "tokens_is_approx": is_approx,
                "lines": line_count,
                "language": utils.get_language_tag(relative_path, content=content, overrides=self.custom_languages),
                "sha256": self.get_content_hash(content),
            }
            if self.output_format != "manifest" and not self.skip_content:
                entry["content"] = content
            if modified is not None:
                entry["modified"] = modified
            json.dump(entry, outfile)
            if self.output_format == "jsonl":
                outfile.write("\n")
        elif self.output_format == "csv":
            fieldnames = ["path", "size_bytes", "tokens", "tokens_is_approx", "lines", "language", "sha256", "content", "modified"]

            if self.csv_writer is None:
                self.csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames, lineterminator='\n')
                self.csv_writer.writeheader()

            entry = {
                "path": relative_path.as_posix(),
                "size_bytes": file_size,
                "tokens": token_count,
                "tokens_is_approx": is_approx,
                "lines": line_count,
                "language": utils.get_language_tag(relative_path, content=content, overrides=self.custom_languages),
                "sha256": self.get_content_hash(content),
                "content": content if not self.skip_content else "",
                "modified": modified if modified is not None else "",
            }
            self.csv_writer.writerow(entry)
        else:
            if include_line_numbers and self.output_opts.get("add_line_numbers", False):
                content = add_line_numbers(content)
            if self.output_format == "xml":
                content = xml_escape(content)
            self._write_with_templates(
                outfile,
                content,
                relative_path,
                size=file_size,
                tokens=token_count,
                lines=line_count,
                modified=modified,
                index=index,
                total=total,
                global_size=global_size,
                global_tokens=global_tokens,
                global_lines=global_lines,
                file_path=file_path,
            )

    def process_and_write(self, file_path, root_path, outfile, cached_content=None, index=None, total=None, global_size=None, global_tokens=None, global_lines=None):
        """Read, process, and write a single file.

        Returns
        -------
        tuple[int, bool, int]
            A tuple containing (token_count, is_approximate, line_count) for the written content.
        """
        if self.dry_run and not (self.show_diff and (self.apply_in_place or outfile is not None)):
            logging.info(_get_rel_path(file_path, root_path))
            return 0, True, 0

        logging.debug("Processing: %s", file_path)
        if cached_content is not None:
            processed_content = cached_content
            content = None
        else:
            content, encoding = read_file_best_effort(file_path)
            lang = utils.get_language_tag(file_path, content=content, overrides=self.custom_languages)
            processed_content = utils.process_content(content, self.processing_opts, language=lang)
            self._apply_inplace_if_needed(file_path, root_path, content, processed_content, encoding)

        relative_path = _get_rel_path(file_path, root_path)
        stat = file_path.stat() if file_path.exists() else None
        file_size = stat.st_size if stat else 0
        modified = stat.st_mtime if stat else None

        # Estimate tokens on the final processed content
        token_count, is_approx = utils.estimate_tokens(processed_content)
        line_count = utils.count_lines(processed_content)

        if not self.dry_run or outfile is not None:
            self._emit_entry(
                outfile,
                processed_content if not self.skip_content else "",
                relative_path,
                file_size,
                token_count,
                is_approx,
                line_count,
                modified=modified,
                index=index,
                total=total,
                global_size=global_size,
                global_tokens=global_tokens,
                global_lines=global_lines,
                file_path=file_path,
            )

        return token_count, is_approx, line_count

    def write_max_size_placeholder(self, file_path, root_path, outfile, index=None, total=None, global_size=None, global_tokens=None, global_lines=None):
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
        stat = file_path.stat() if file_path.exists() else None
        file_size = stat.st_size if stat else 0
        modified = stat.st_mtime if stat else None

        # Estimate tokens on the placeholder content (but the placeholder itself might have tokens placeholder)
        # For max_size_placeholder, it's a bit tricky because we don't know the token count of the placeholder
        # until it's rendered. But we want to support {{SIZE}} in it.
        rendered = _render_template(
            placeholder, relative_path, size=file_size, modified=modified,
            content=None, custom_languages=self.custom_languages,
            index=index, total=total, global_size=global_size,
            global_tokens=global_tokens, global_lines=global_lines,
            git_info=self.git_info, file_path=file_path
        )

        token_count, is_approx = utils.estimate_tokens(rendered)
        line_count = utils.count_lines(rendered)

        self._emit_entry(
            outfile,
            rendered,
            relative_path,
            file_size,
            token_count,
            is_approx,
            line_count,
            include_line_numbers=False,
            modified=modified,
            index=index,
            total=total,
            global_size=global_size,
            global_tokens=global_tokens,
            global_lines=global_lines,
            file_path=file_path,
        )

        return token_count, is_approx, line_count


def _generate_tree_string(paths, root_path, output_format='text', include_header=True, metadata=None):
    """Generate a visual folder tree of file paths."""
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
                folder_metadata[parent]['size'] += (file_meta.get('size') or 0)
                folder_metadata[parent]['tokens'] += (file_meta.get('tokens') or 0)
                folder_metadata[parent]['lines'] += (file_meta.get('lines') or 0)
                folder_metadata[parent]['files'] += 1

    lines = []
    if include_header:
        if output_format == 'markdown':
            lines.append("## Project Structure")
            lines.append("```text")
        else:
            lines.append("Project Structure:")

    dim = str(C_DIM) if output_format == 'text' else ""
    reset = str(C_RESET) if output_format == 'text' else ""
    folder_style = (str(C_BOLD) + str(C_CYAN)) if output_format == 'text' else ""
    file_style = str(C_BOLD) if output_format == 'text' else ""

    def _add_node(node, prefix="", rel_parts=()):
        items = sorted(node.keys())
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = f"{dim}└── {reset}" if is_last else f"{dim}├── {reset}"

            current_rel_parts = rel_parts + (item,)
            current_rel_path = Path(*current_rel_parts)
            children = node[item]

            meta_str = ""
            if metadata:
                is_text = (output_format == 'text')
                if children:
                    # It's a folder - show totals
                    if current_rel_path in folder_metadata:
                        meta_str = f"{dim}{_format_metadata_summary(folder_metadata[current_rel_path], colored=is_text)}{reset}"
                elif current_rel_path in rel_to_orig:
                    # It's a file - show individual stats
                    orig_path = rel_to_orig[current_rel_path]
                    file_meta = metadata.get(orig_path)
                    if file_meta:
                        meta_str = f"{dim}{_format_metadata_summary(file_meta, colored=is_text)}{reset}"

            style = folder_style if children else file_style
            suffix = f"{dim}/{reset}" if children else ""
            lines.append(f"{prefix}{connector}{style}{item}{suffix}{meta_str}")

            # If the item has children (it's a folder), recurse
            if children:
                extension = "    " if is_last else f"{dim}│{reset}   "
                _add_node(children, prefix + extension, current_rel_parts)

    # Add the root folder name first
    root_meta_str = ""
    if metadata and Path('.') in folder_metadata:
        is_text = (output_format == 'text')
        root_meta_str = f"{dim}{_format_metadata_summary(folder_metadata[Path('.')], colored=is_text)}{reset}"

    lines.append(f"{folder_style}{root_path.name or str(root_path)}{dim}/{reset}{root_meta_str}")
    _add_node(tree)

    if include_header:
        if output_format == 'markdown':
            lines.append("```\n")
        else:
            lines.append("-" * 20 + "\n")

    return "\n".join(lines)


def _generate_project_overview(stats, output_format='text', processing_opts=None):
    """Generate a project overview summary from execution statistics."""
    if not stats:
        return ""

    lines = []
    if output_format == 'markdown':
        lines.append("# Project Overview\n")
        lines.append("## Statistics")
    else:
        lines.append("Project Overview:")

    total_files = stats.get('total_files', 0)
    total_size_bytes = stats.get('total_size_bytes', 0)
    total_size = utils.format_size(total_size_bytes)
    total_tokens = stats.get('total_tokens', 0)
    total_lines = stats.get('total_lines', 0)
    is_approx = stats.get('token_count_is_approx', False)

    token_str = format_tokens(total_tokens, is_approx)
    timestamp = stats.get('datetime') or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = stats.get('project_name', 'Project')

    if output_format == 'markdown':
        lines.append(f"- **Project:** {project_name}")
        if stats.get('project_version'):
            lines.append(f"- **Version:** {stats['project_version']}")
        if stats.get('project_license'):
            lines.append(f"- **License:** {stats['project_license']}")
        if stats.get('project_url'):
            lines.append(f"- **URL:** {stats['project_url']}")
        if stats.get('manifest_source'):
            lines.append(f"- **Manifest:** {stats['manifest_source']}")
        lines.append(f"- **Generated at:** {timestamp}")
        if stats.get('os'):
            lines.append(f"- **OS:** {stats['os']}")
        if stats.get('python_version'):
            lines.append(f"- **Python:** {stats['python_version']}")
        if stats.get('git_branch') and stats.get('git_branch') != 'N/A':
            lines.append(f"- **Git Branch:** {stats['git_branch']}")
        if stats.get('git_commit_short') and stats.get('git_commit_short') != 'N/A':
            lines.append(f"- **Git Commit:** {stats['git_commit_short']}")
        if stats.get('git_status'):
            lines.append(f"- **Git Status:** {stats['git_status']}")

        git_log = stats.get('git_log')
        if git_log:
            lines.append("\n### Recent Changes")
            lines.append("```text")
            lines.append(git_log)
            lines.append("```\n")

        git_diff = stats.get('git_diff')
        if git_diff:
            lines.append("\n### Current Changes")
            lines.append("```diff")
            lines.append(git_diff)
            lines.append("```\n")

        lines.append(f"- **Files:** {total_files:,}")
        lines.append(f"- **Total Size:** {total_size}")
        lines.append(f"- **Total Lines:** {total_lines:,}")
        lines.append(f"- **Total Tokens:** {token_str}")
    else:
        lines.append(f"  Project:      {project_name}")
        if stats.get('project_version'):
            lines.append(f"  Version:      {stats['project_version']}")
        if stats.get('project_license'):
            lines.append(f"  License:      {stats['project_license']}")
        if stats.get('project_url'):
            lines.append(f"  URL:          {stats['project_url']}")
        if stats.get('manifest_source'):
            lines.append(f"  Manifest:     {stats['manifest_source']}")
        lines.append(f"  Generated at: {timestamp}")
        if stats.get('os'):
            lines.append(f"  OS:           {stats['os']}")
        if stats.get('python_version'):
            lines.append(f"  Python:       {stats['python_version']}")
        if stats.get('git_branch') and stats.get('git_branch') != 'N/A':
            lines.append(f"  Git Branch:   {stats['git_branch']}")
        if stats.get('git_commit_short') and stats.get('git_commit_short') != 'N/A':
            lines.append(f"  Git Commit:   {stats['git_commit_short']}")
        if stats.get('git_status'):
            lines.append(f"  Git Status:   {stats['git_status']}")

        git_log = stats.get('git_log')
        if git_log:
            lines.append("\n  Recent Changes:")
            for line in git_log.splitlines():
                lines.append(f"    {line}")
            lines.append("")

        git_diff = stats.get('git_diff')
        if git_diff:
            lines.append("\n  Current Changes:")
            for line in git_diff.splitlines():
                lines.append(f"    {line}")
            lines.append("")

        lines.append(f"  Files:        {total_files:,}")
        lines.append(f"  Total Size:   {total_size}")
        lines.append(f"  Total Lines:  {total_lines:,}")
        lines.append(f"  Total Tokens: {token_str}")

    # Truncation Notices
    truncations = [label for key, label in TRUNCATION_CHECKS if stats.get(key)]

    if truncations:
        notice = "WARNING: Output shortened due to: " + ", ".join(truncations)
        if output_format == 'markdown':
            lines.append(f"\n> [!CAUTION]\n> **{notice}**")
        else:
            lines.append(f"\n  {notice}")

    # Processing Details
    if processing_opts:
        active_rules = []
        if processing_opts.get('compact_whitespace'):
            active_rules.append("Whitespace compaction")
        if processing_opts.get('remove_comments'):
            active_rules.append("Comment removal")
        elif processing_opts.get('remove_single_line_comments'):
            active_rules.append("Single-line comment removal")
        if processing_opts.get('remove_all_c_style_comments'):
            active_rules.append("C-style comment removal")
        if processing_opts.get('max_lines'):
            active_rules.append(f"Shortened to {processing_opts['max_lines']} lines per file")

        if active_rules:
            if output_format == 'markdown':
                lines.append("\n## Applied Processing")
                for rule in active_rules:
                    lines.append(f"- {rule}")
            else:
                lines.append("\n  Applied Processing:")
                for rule in active_rules:
                    lines.append(f"    - {rule}")

    # Largest Files
    top_files = stats.get('top_files')
    if top_files:
        sorted_top, title, total_weight, has_tokens, has_lines = _get_summary_top_items(
            stats, top_files, is_folder=False
        )

        if output_format == 'markdown':
            lines.append(f"\n## {title}")
            md_header = "| File"
            md_divider = "| :---"
            if has_tokens:
                md_header += " | Tokens"
                md_divider += " | :---"
            if has_lines:
                md_header += " | Lines"
                md_divider += " | :---"
            md_header += " | Size | Language | % |"
            md_divider += " | :--- | :--- | :--- |"
            lines.append(md_header)
            lines.append(md_divider)

            for item in sorted_top:
                tokens, size, path = item[:3]
                f_lines = item[4] if len(item) > 4 else 0
                f_lang = item[5] if len(item) > 5 else ""
                weight = tokens if has_tokens else (f_lines if has_lines else size)
                percent = (weight / total_weight * 100) if total_weight > 0 else 0

                row = f"| `{path}`"
                if has_tokens: row += f" | {tokens:,}"
                if has_lines: row += f" | {f_lines:,}"
                row += f" | {utils.format_size(size)} | {f_lang} | {percent:.1f}% |"
                lines.append(row)
        else:
            lines.append(f"\n  {title}:")
            for item in sorted_top:
                tokens, size, path = item[:3]
                f_lines = item[4] if len(item) > 4 else 0
                f_lang = item[5] if len(item) > 5 else ""
                weight = tokens if has_tokens else (f_lines if has_lines else size)
                percent = (weight / total_weight * 100) if total_weight > 0 else 0

                parts = []
                if has_tokens: parts.append(f"{tokens:>10} tokens")
                if has_lines: parts.append(f"{f_lines:>8} lines")
                parts.append(f"{utils.format_size(size):>10}")
                f_lang_label = f_lang[:10] if len(f_lang) <= 10 else (f_lang[:7] + "...")
                parts.append(f"{f_lang_label:<10}")

                lines.append(f"    {path:<30} {' • '.join(parts)} ({percent:>5.1f}%)")

    # Largest Folders
    folder_stats = _get_folder_stats(top_files)
    if folder_stats:
        sorted_folders, title, total_weight, has_tokens, has_lines = _get_summary_top_items(
            stats, list(folder_stats.items()), is_folder=True
        )

        if output_format == 'markdown':
            lines.append(f"\n## {title}")
            md_header = "| Folder"
            md_divider = "| :---"
            if has_tokens:
                md_header += " | Tokens"
                md_divider += " | :---"
            if has_lines:
                md_header += " | Lines"
                md_divider += " | :---"
            md_header += " | Size | Files | % |"
            md_divider += " | :--- | :--- | :--- |"
            lines.append(md_header)
            lines.append(md_divider)

            for path, data in sorted_folders:
                tokens = data['tokens']
                size = data['size']
                f_lines = data.get('lines', 0)
                files = data['files']
                weight = tokens if has_tokens else (f_lines if has_lines else size)
                percent = (weight / total_weight * 100) if total_weight > 0 else 0

                row = f"| `{path}`"
                if has_tokens: row += f" | {tokens:,}"
                if has_lines: row += f" | {f_lines:,}"
                row += f" | {utils.format_size(size)} | {files:,} | {percent:.1f}% |"
                lines.append(row)
        else:
            lines.append(f"\n  {title}:")
            for path, data in sorted_folders:
                tokens = data['tokens']
                size = data['size']
                f_lines = data.get('lines', 0)
                files = data['files']
                weight = tokens if has_tokens else (f_lines if has_lines else size)
                percent = (weight / total_weight * 100) if total_weight > 0 else 0

                parts = []
                if has_tokens: parts.append(f"{tokens:>10} tokens")
                if has_lines: parts.append(f"{f_lines:>8} lines")
                parts.append(f"{utils.format_size(size):>10}")
                parts.append(f"{files:>4} files")

                lines.append(f"    {path:<30} {' • '.join(parts)} ({percent:>5.1f}%)")

    # Language Breakdown
    lang_stats = stats.get('files_by_language', {})
    if lang_stats:
        tokens_by_lang = stats.get('tokens_by_language', {})
        lines_by_lang = stats.get('lines_by_language', {})
        size_by_lang = stats.get('size_by_language', {})
        has_lang_tokens = any(v > 0 for v in tokens_by_lang.values())
        has_lang_lines = any(v > 0 for v in lines_by_lang.values())

        if has_lang_tokens:
            total_weight = total_tokens
            weight_by_lang = tokens_by_lang
            weight_label = "% Tokens"
        elif has_lang_lines:
            total_weight = total_lines
            weight_by_lang = lines_by_lang
            weight_label = "% Lines"
        else:
            total_weight = total_size_bytes
            weight_by_lang = size_by_lang
            weight_label = "% Size"

        sorted_langs = sorted(
            lang_stats.items(),
            key=lambda item: (-weight_by_lang.get(item[0], 0), -item[1], item[0])
        )

        if output_format == 'markdown':
            lines.append("\n## Languages")
            md_header = "| Language | Count"
            md_divider = "| :--- | :---"
            if has_lang_lines:
                md_header += " | Lines"
                md_divider += " | :---"
            md_header += f" | % Files | {weight_label} |"
            md_divider += " | :--- | :--- |"
            lines.append(md_header)
            lines.append(md_divider)

            for lang, count in sorted_langs:
                f_percent = (count / total_files * 100) if total_files > 0 else 0
                w_percent = (weight_by_lang.get(lang, 0) / total_weight * 100) if total_weight > 0 else 0
                row = f"| `{lang}` | {count:,}"
                if has_lang_lines: row += f" | {lines_by_lang.get(lang, 0):,}"
                row += f" | {f_percent:.1f}% | {w_percent:.1f}% |"
                lines.append(row)
        else:
            lines.append("\n  Languages:")
            for lang, count in sorted_langs:
                f_percent = (count / total_files * 100) if total_files > 0 else 0
                w_percent = (weight_by_lang.get(lang, 0) / total_weight * 100) if total_weight > 0 else 0
                l_lines = lines_by_lang.get(lang, 0)

                # ASCII bar
                bar = f"[{_make_ascii_bar(w_percent)}]"

                parts = [f"{count:>5,} files"]
                if has_lang_lines: parts.append(f"{l_lines:>8,} lines")

                metrics = f"({f_percent:>5.1f}% • {w_percent:>5.1f}%)"
                lines.append(f"    {lang:<10} {' • '.join(parts)} {metrics} {bar}")

    if output_format == 'markdown':
        lines.append("\n---")
    else:
        lines.append("\n" + "-" * 20 + "\n")

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
                meta_str = _format_metadata_summary(metadata[file_path], colored=(output_format == 'text'))

            # Create a basic anchor link.
            slug = re.sub(r'[^a-z0-9 _-]', '', posix_rel_path.lower()).replace(' ', '-')

            toc_lines.append(f"- [{posix_rel_path}](#{slug}){meta_str}")
        toc_lines.append("")

    else: # text
        dim = str(C_DIM) if output_format == 'text' else ""
        reset = str(C_RESET) if output_format == 'text' else ""

        toc_lines.append("Table of Contents:")
        for file_path, root_path in files:
            rel_path = _get_rel_path(file_path, root_path)

            meta_str = ""
            if metadata and file_path in metadata:
                meta_str = f"{dim}{_format_metadata_summary(metadata[file_path], colored=True)}{reset}"

            toc_lines.append(f"{dim}- {reset}{rel_path.as_posix()}{meta_str}")
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
    """Find, filter, and combine files based on the settings."""
    stats = {
        'total_discovered': 0,
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'tokens_by_extension': {},
        'lines_by_extension': {},
        'size_by_extension': {},
        'files_by_language': {},
        'tokens_by_language': {},
        'lines_by_language': {},
        'size_by_language': {},
        'custom_languages': config.get('search', {}).get('custom_languages', {}),
        'total_tokens': 0,
        'total_lines': 0,
        'token_count_is_approx': False,
        'token_limit_reached': False,
        'size_limit_reached': False,
        'line_limit_reached': False,
        'top_files': [],
        'max_total_tokens': config.get('filters', {}).get('max_total_tokens', 0),
        'max_total_size_bytes': config.get('filters', {}).get('max_total_size_bytes', 0),
        'max_total_lines': config.get('filters', {}).get('max_total_lines', 0),
        'max_files': config.get('filters', {}).get('max_files', 0),
        'filter_reasons': {},
    }

    # Gather project metadata for templates
    first_root = "."
    if config.get('search', {}).get('root_folders'):
        first_root = config['search']['root_folders'][0]

    _populate_project_stats(stats, first_root, config)

    search_opts = config.get('search', {})
    filter_opts = config.get('filters', {})
    output_opts = config.get('output', {})

    git_log_count = output_opts.get('git_log_count', 0)
    stats.update(_get_git_info(
        first_root,
        log_count=git_log_count,
        include_diff=output_opts.get('include_diff', False),
        diff_ref=search_opts.get('git_diff_ref'),
        staged=search_opts.get('git_staged', False),
        unstaged=search_opts.get('git_unstaged', False)
    ))

    # Resolve dynamic output path if it contains placeholders
    if isinstance(output_path, str) and output_path != '-' and '{{' in output_path:
        output_path = _render_global_template(output_path, stats)

    stats['resolved_output_path'] = output_path

    # Ensure project metadata is also in git_info for FileProcessor when Git is not present
    git_info = config.get('git_info', {})
    git_info.update({
        'project_name': stats.get('project_name', 'Project'),
        'date': stats.get('date', ''),
        'time': stats.get('time', ''),
        'datetime': stats.get('datetime', ''),
        'os': stats.get('os', ''),
        'python_version': stats.get('python_version', ''),
        'platform': stats.get('platform', ''),
        'arch': stats.get('arch', ''),
    })
    config['git_info'] = git_info
    pair_opts = config.get('pairing', {})

    exclude_folders = filter_opts.get('exclusions', {}).get('folders') or []

    pairing_enabled = pair_opts.get('enabled')
    mirror_enabled = output_opts.get('mirror', False)
    root_folders = search_opts.get('root_folders') or []
    recursive = search_opts.get('recursive', True)

    if mirror_enabled:
        if pairing_enabled:
            raise utils.InvalidConfigError("Mirror mode and pairing mode cannot be used at the same time.")
        if clipboard:
            raise utils.InvalidConfigError("Mirror mode and clipboard cannot be used at the same time.")
        if output_path == '-':
            raise utils.InvalidConfigError("Mirror mode cannot output to the terminal.")
        if output_format in ('json', 'jsonl', 'manifest', 'csv'):
            raise utils.InvalidConfigError(f"Mirror mode does not support {output_format.upper()} format.")

    if clipboard and pairing_enabled:
        raise utils.InvalidConfigError("The clipboard can only be used when combining many files into one.")

    if output_path == '-' and pairing_enabled:
        raise utils.InvalidConfigError("You cannot send output to the terminal when pairing files.")

    if output_format in ('json', 'jsonl', 'manifest', 'csv') and pairing_enabled:
        raise utils.InvalidConfigError(f"You cannot use {output_format.upper()} format when pairing files.")

    if mirror_enabled:
        # Default to no headers/footers for mirror mode unless explicitly overridden
        default_header = utils.DEFAULT_CONFIG['output']['header_template']
        default_footer = utils.DEFAULT_CONFIG['output']['footer_template']

        if not output_opts.get('header_template') or output_opts.get('header_template') == default_header:
            output_opts['header_template'] = ""
        if not output_opts.get('footer_template') or output_opts.get('footer_template') == default_footer:
            output_opts['footer_template'] = ""

    # Apply default Markdown templates if requested and not overridden
    if output_format == 'markdown':
        default_header = utils.DEFAULT_CONFIG['output']['header_template']
        default_footer = utils.DEFAULT_CONFIG['output']['footer_template']

        current_header = output_opts.get('header_template')
        current_footer = output_opts.get('footer_template')

        # If current matches default (or is None/empty/missing), override with Markdown defaults
        if not current_header or current_header == default_header:
            output_opts['header_template'] = "## {{FILENAME}}\n\n```{{LANG}}\n"

        if not current_footer or current_footer == default_footer:
            output_opts['footer_template'] = "\n```\n\n"

    # Apply default XML templates if requested and not overridden
    if output_format == 'xml':
        default_header = utils.DEFAULT_CONFIG['output']['header_template']
        default_footer = utils.DEFAULT_CONFIG['output']['footer_template']
        default_global_header = utils.DEFAULT_CONFIG['output']['global_header_template']
        default_global_footer = utils.DEFAULT_CONFIG['output']['global_footer_template']

        if not output_opts.get('header_template') or output_opts.get('header_template') == default_header:
            output_opts['header_template'] = '<file path="{{FILENAME}}" modified="{{MODIFIED}}">\n'
        if not output_opts.get('footer_template') or output_opts.get('footer_template') == default_footer:
            output_opts['footer_template'] = "\n</file>\n"
        if not output_opts.get('global_header_template') or output_opts.get('global_header_template') == default_global_header:
            output_opts['global_header_template'] = "<repository>\n"
        if not output_opts.get('global_footer_template') or output_opts.get('global_footer_template') == default_global_footer:
            output_opts['global_footer_template'] = "\n</repository>\n"

    if not pairing_enabled and not dry_run and not estimate_tokens and not clipboard and not list_files and not tree_view and output_path is None:
        raise utils.InvalidConfigError(
            "You must set an output file in the configuration or use the --output option."
        )

    abs_output_path = None
    if not pairing_enabled and output_path and output_path != '-':
        try:
            abs_output_path = Path(output_path).resolve()
        except OSError:
            # Fallback to absolute path if resolve fails (for example, file doesn't exist yet and parent is weird)
            try:
                abs_output_path = Path(output_path).absolute()
            except OSError:
                abs_output_path = None

    out_folder = None
    if pairing_enabled and output_path:
        out_folder = Path(output_path)
        if not dry_run and not estimate_tokens and not list_files and not tree_view:
            out_folder.mkdir(parents=True, exist_ok=True)

    clipboard_buffer = io.StringIO() if clipboard else None

    if estimate_tokens or list_files or tree_view:
        outfile_ctx = _DevNull()
    elif (dry_run and output_opts.get('show_diff') and output_path and output_path != '-'):
        clipboard_buffer = io.StringIO()
        outfile_ctx = nullcontext(clipboard_buffer)
    elif pairing_enabled or mirror_enabled or dry_run or clipboard:
        outfile_ctx = nullcontext(clipboard_buffer)
    elif output_path == '-':
        outfile_ctx = nullcontext(sys.stdout)
    else:
        # Automatically create parent folders for the output file.
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        outfile_ctx = open(output_path, 'w', encoding='utf8', newline='')

    # We only want true dry-run behavior (skipping reading) if we are NOT estimating tokens.
    processor_dry_run = (dry_run and not estimate_tokens) or list_files or tree_view
    processor = FileProcessor(
        config,
        output_opts,
        dry_run=processor_dry_run,
        estimate_tokens=estimate_tokens,
        output_format=output_format,
        git_info=stats  # stats already contains git_branch and other metadata
    )

    total_excluded_folders = 0

    # Store all items to process for when combining many files into one to enable global Table of Contents
    # List of (file_path, root_path, is_size_excluded)
    all_combined_items = []
    # Store all pairs across all roots
    # List of (root_path, pair_key, paths)
    all_paired_items = []
    # Track all files excluded by size across all roots
    all_size_excluded = set()
    # For path-based deduplication
    seen_paths = set()
    # Metadata for Table of Contents and Tree: {Path: {'size': int, 'tokens': int, 'mtime': float, 'depth': int}}
    file_metadata = {}

    with outfile_ctx as outfile:
        global_header = output_opts.get('global_header_template')
        global_footer = output_opts.get('global_footer_template')

        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and output_format in ('json', 'manifest'):
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
                    desc=f"Finding in {_truncate_path(root_folder, 40)}",
                    unit="file",
                    leave=False,
                )
                try:
                    paths, root, excluded = collect_file_paths(
                        root_folder,
                        recursive,
                        exclude_folders,
                        progress=finding_bar,
                        max_depth=search_opts.get('max_depth', 0),
                        use_git=search_opts.get('use_git', False),
                        use_git_diff=search_opts.get('use_git_diff', False),
                        git_diff_ref=search_opts.get('git_diff_ref'),
                        git_staged=search_opts.get('git_staged', False),
                        git_unstaged=search_opts.get('git_unstaged', False),
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

            # Path-based deduplication
            unique_for_root = []
            if filter_opts.get('unique'):
                for p in all_paths:
                    try:
                        abs_p = p.resolve()
                        if abs_p in seen_paths:
                            logging.debug("Skipping duplicate path: %s", p)
                            stats['filter_reasons']['duplicate_path'] = stats['filter_reasons'].get('duplicate_path', 0) + 1
                            continue
                        seen_paths.add(abs_p)
                        unique_for_root.append(p)
                    except OSError:
                        unique_for_root.append(p)
            else:
                unique_for_root = all_paths

            record_size_exclusions = bool(output_opts.get('max_size_placeholder'))

            filtered_result = filter_file_paths(
                unique_for_root,
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
                    for _, paths in paired_paths:
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
                    remaining_file_limit = max_files - stats['total_files']
                    if remaining_file_limit <= 0:
                        stats['filter_reasons']['file_limit'] = stats['filter_reasons'].get('file_limit', 0) + len(paths_to_list)
                        paths_to_list = []
                        stats['limit_reached'] = True
                        continue
                    elif len(paths_to_list) > remaining_file_limit:
                        stats['filter_reasons']['file_limit'] = stats['filter_reasons'].get('file_limit', 0) + (len(paths_to_list) - remaining_file_limit)
                        paths_to_list = paths_to_list[:remaining_file_limit]
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

                    content = None
                    if estimate_tokens:
                        content, _ = read_file_best_effort(p)
                        processed = process_content(content, processor.processing_opts)
                        tokens, is_approx = utils.estimate_tokens(processed)
                        lines = utils.count_lines(processed)
                        _update_stats_metrics(stats, tokens, lines, is_approx)
                        _update_token_stats(stats, p, tokens)
                        _update_line_stats(stats, p, lines)

                    rel_p_str = _get_rel_path(p, root_path).as_posix()
                    status = stats.get('file_statuses', {}).get(rel_p_str)
                    lang = utils.get_language_tag(p, content=content if estimate_tokens else None, overrides=processor.custom_languages)
                    view_metadata[p] = {'size': f_size, 'tokens': tokens, 'lines': lines, 'status': status, 'language': lang}
                    stats['top_files'].append((tokens, f_size, rel_p_str, status, lines, lang))

                if tree_view:
                    print(_generate_tree_string(paths_to_list, root_path, include_header=False, metadata=view_metadata))
                else:
                    for p in paths_to_list:
                        # Print relative path if possible for cleaner output
                        print(_get_rel_path(p, root_path) if p.is_absolute() else p)
                continue

            # Update stats
            if not pairing_enabled:
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

                # Collect all unique files that were successfully paired
                paired_files_set = set()
                for _, paths in paired_paths:
                    paired_files_set.update(paths)

                # Only update stats for files that are part of a pair
                for p in sorted(paired_files_set):
                    _update_file_stats(stats, p)

                # Record how many files were skipped because they weren't paired
                unpaired_count = len(set(pairing_inputs)) - len(paired_files_set)
                if unpaired_count > 0:
                    stats['filter_reasons']['unpaired'] = stats['filter_reasons'].get('unpaired', 0) + unpaired_count

                for pair_key, paths in paired_paths:
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

                    all_combined_items.append((file_path, root_path, is_excluded_by_size))

        # End of root_folder loop

        # Metadata and Sorting Pass
        sort_by = output_opts.get('sort_by', 'name')
        sort_reverse = output_opts.get('sort_reverse', False)

        max_total_tokens = filter_opts.get('max_total_tokens', 0)
        max_total_size = filter_opts.get('max_total_size_bytes', 0)
        max_total_lines = filter_opts.get('max_total_lines', 0)
        new_placeholders = ["{{INDEX}}", "{{TOTAL}}", "{{SIZE_PERCENT}}", "{{TOKEN_PERCENT}}", "{{LINE_PERCENT}}"]
        header_template = output_opts.get('header_template') or ""
        footer_template = output_opts.get('footer_template') or ""
        has_new_placeholders = any(p in header_template for p in new_placeholders) or \
                               any(p in footer_template for p in new_placeholders)

        needs_metadata = bool(
            output_opts.get('include_tree')
            or output_opts.get('table_of_contents')
            or output_opts.get('project_overview')
            or has_new_placeholders
        )

        # We need metadata for sorting (except name), token limit, size limit, Table of Contents/Tree, or global placeholders
        global_placeholders = ["{{FILE_COUNT}}", "{{TOTAL_SIZE}}", "{{TOTAL_TOKENS}}", "{{TOTAL_LINES}}"]
        has_global_placeholders = (global_header and any(p in global_header for p in global_placeholders)) or \
                                  (global_footer and any(p in global_footer for p in global_placeholders))

        needs_full_pass = (sort_by not in ('name',) or max_total_tokens > 0 or max_total_size > 0 or max_total_lines > 0 or
                           needs_metadata or has_global_placeholders or estimate_tokens or filter_opts.get('unique'))

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
                        content, _ = read_file_best_effort(primary_path)
                        processed = process_content(content, processor.processing_opts)
                        val, _ = utils.estimate_tokens(processed)
                    elif sort_by == 'lines':
                        content, _ = read_file_best_effort(primary_path)
                        processed = process_content(content, processor.processing_opts)
                        val = utils.count_lines(processed)
                    elif sort_by == 'language':
                        val = utils.get_language_tag(primary_path, overrides=processor.custom_languages)
                    else:
                        val = rel_p.as_posix()
                    return (val, rel_p.as_posix())

                all_paired_items.sort(key=get_pair_sort_key, reverse=sort_reverse)
        else:
            if sort_by != 'name' or sort_reverse:
                if sort_by in ('name', 'size', 'modified', 'depth', 'language'):
                    def get_single_sort_key(item):
                        file_p, root_p, _ = item
                        rel_p = _get_rel_path(file_p, root_p)
                        if sort_by == 'size':
                            val = file_p.stat().st_size if file_p.exists() else 0
                        elif sort_by == 'modified':
                            val = file_p.stat().st_mtime if file_p.exists() else 0
                        elif sort_by == 'depth':
                            val = len(rel_p.parts)
                        elif sort_by == 'language':
                            val = utils.get_language_tag(file_p, overrides=processor.custom_languages)
                        else:
                            val = rel_p.as_posix()
                        return (val, rel_p.as_posix())
                    all_combined_items.sort(key=get_single_sort_key, reverse=sort_reverse)
                # Note: 'tokens' and 'lines' sort when combining many files into one is handled inside the metadata pass below

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
            elif sort_by not in ('tokens', 'lines'):
                if len(all_combined_items) > max_files:
                    stats['filter_reasons']['file_limit'] = len(all_combined_items) - max_files
                    all_combined_items = all_combined_items[:max_files]
                    stats['limit_reached'] = True
                    limit_applied = True

        # Recalculate stats if limit was applied and we aren't doing a full pass anyway
        if limit_applied and not (needs_full_pass and not pairing_enabled and not list_files and not tree_view):
            stats['total_files'] = 0
            stats['total_size_bytes'] = 0
            stats['files_by_extension'] = {}
            stats['size_by_extension'] = {}
            stats['tokens_by_extension'] = {}
            stats['lines_by_extension'] = {}
            stats['files_by_language'] = {}
            stats['size_by_language'] = {}
            stats['tokens_by_language'] = {}
            stats['lines_by_language'] = {}
            if pairing_enabled:
                for _, _, paths in all_paired_items:
                    for p in paths:
                        _update_file_stats(stats, p)
            else:
                for item in all_combined_items:
                    _update_file_stats(stats, item[0])

        if needs_full_pass and not pairing_enabled and not list_files and not tree_view:
            limited_items = []
            current_tokens = 0
            current_lines = 0
            current_size = 0
            overhead_tokens = 0
            overhead_lines = 0
            overhead_size = 0
            token_limit_reached = False
            size_limit_reached = False
            line_limit_reached = False

            # Account for global header and footer in the limit
            # We estimate these once without placeholders for initial limit.
            if global_header and output_format in ('text', 'markdown', 'xml'):
                overhead_tokens += utils.estimate_tokens(global_header)[0]
                overhead_lines += utils.count_lines(global_header)
                overhead_size += len(global_header.encode('utf-8'))
            if global_footer and output_format in ('text', 'markdown', 'xml'):
                overhead_tokens += utils.estimate_tokens(global_footer)[0]
                overhead_lines += utils.count_lines(global_footer)
                overhead_size += len(global_footer.encode('utf-8'))

            # Estimate Table of Contents and Tree overhead if enabled
            if output_format in ('text', 'markdown'):
                if output_opts.get('project_overview'):
                    overhead_tokens += 100 + (len(stats.get('files_by_extension', {})) * 10)
                    overhead_size += 500 + (len(stats.get('files_by_extension', {})) * 50)
                if output_opts.get('include_tree'):
                    overhead_tokens += len(all_combined_items) * 12
                    overhead_size += len(all_combined_items) * 50
                if output_opts.get('table_of_contents'):
                    overhead_tokens += len(all_combined_items) * 12
                    overhead_size += len(all_combined_items) * 50

            # If sorting by tokens or lines, we must calculate metrics for all files first
            if sort_by in ('tokens', 'lines'):
                metric_data = []
                sort_bar = processor._make_bar(
                    total=len(all_combined_items),
                    desc=f"Calculating {sort_by} for sorting",
                    unit="file",
                )
                running_metric = 0
                for item in all_combined_items:
                    file_path, root_path, is_excluded_by_size = item
                    rel_p = _get_rel_path(file_path, root_path)
                    rel_p_str = rel_p.as_posix()
                    sort_bar.set_description(f"Analyzing {_truncate_path(rel_p_str, 40)}")
                    if is_excluded_by_size:
                        placeholder = output_opts.get('max_size_placeholder')
                        # Note: 1372-1373 ensures placeholder exists if we are here
                        rendered = _render_template(
                            placeholder, rel_p,
                            size=file_path.stat().st_size if file_path.exists() else 0,
                            custom_languages=search_opts.get('custom_languages'),
                            git_info=stats, file_path=file_path
                        )
                        if sort_by == 'tokens':
                            val, _ = utils.estimate_tokens(rendered)
                        else:
                            val = utils.count_lines(rendered)
                    else:
                        content, _ = read_file_best_effort(file_path)
                        lang = utils.get_language_tag(file_path, content=content, overrides=processor.custom_languages)
                        processed = utils.process_content(content, processor.processing_opts, language=lang)
                        if sort_by == 'tokens':
                            val, _ = utils.estimate_tokens(processed)
                        else:
                            val = utils.count_lines(processed)
                    metric_data.append((val, rel_p_str))
                    running_metric += val
                    sort_bar.set_postfix(**{sort_by: f"{running_metric:,}"})
                    sort_bar.update(1)
                sort_bar.close()

                # Sort by metric
                # Zip metric with items to sort them together
                indexed_items = sorted(
                    zip(all_combined_items, metric_data),
                    key=lambda x: (x[1][0], x[1][1]),
                    reverse=sort_reverse
                )
                all_combined_items = [x[0] for x in indexed_items]

            if max_files > 0 and sort_by in ('tokens', 'lines') and len(all_combined_items) > max_files:
                stats['filter_reasons']['file_limit'] = len(all_combined_items) - max_files
                all_combined_items = all_combined_items[:max_files]
                stats['limit_reached'] = True

            est_bar = processor._make_bar(
                total=len(all_combined_items),
                desc="Analyzing files",
                unit="file",
            )
            for i, item in enumerate(all_combined_items):
                file_path, root_path, is_excluded_by_size = item

                rel_p = _get_rel_path(file_path, root_path)
                rel_p_str = rel_p.as_posix()
                est_bar.set_description(f"Analyzing {_truncate_path(rel_p_str, 40)}")
                content_tokens = 0
                content_lines = 0
                content_size = 0
                processed = None
                file_size = file_path.stat().st_size if file_path.exists() else 0

                rel_p = _get_rel_path(file_path, root_path)

                if is_excluded_by_size:
                    placeholder = output_opts.get('max_size_placeholder')
                    if placeholder:
                        rendered = _render_template(
                            placeholder, rel_p, size=file_size,
                            custom_languages=search_opts.get('custom_languages'),
                            git_info=stats, file_path=file_path
                        )
                        content_tokens, is_approx = utils.estimate_tokens(rendered)
                        content_lines = utils.count_lines(rendered)
                        content_size = len(rendered.encode('utf-8'))
                        if is_approx:
                            stats['token_count_is_approx'] = True
                else:
                    content, encoding = read_file_best_effort(file_path)
                    lang = utils.get_language_tag(file_path, content=content, overrides=processor.custom_languages)
                    processed = utils.process_content(content, processor.processing_opts, language=lang)
                    processor._apply_inplace_if_needed(file_path, root_path, content, processed, encoding, dry_run=dry_run, estimate_tokens=estimate_tokens)

                    # Content-based deduplication
                    if filter_opts.get('unique'):
                        content_hash = processor.get_content_hash(processed)
                        if content_hash in processor.seen_hashes:
                            logging.debug("Skipping duplicate content: %s", rel_p_str)
                            stats['filter_reasons']['duplicate_content'] = stats['filter_reasons'].get('duplicate_content', 0) + 1
                            continue
                        processor.seen_hashes.add(content_hash)

                    content_tokens, is_approx = utils.estimate_tokens(processed)
                    content_lines = utils.count_lines(processed)
                    content_size = len(processed.encode('utf-8'))
                    if is_approx:
                        stats['token_count_is_approx'] = True

                _update_token_stats(stats, file_path, content_tokens)
                _update_line_stats(stats, file_path, content_lines)

                # Store content details for Table of Contents/Tree
                rel_p_str = rel_p.as_posix()
                status = stats.get('file_statuses', {}).get(rel_p_str)
                file_metadata[file_path] = {
                    'size': file_size,
                    'tokens': content_tokens,
                    'lines': content_lines,
                    'status': status,
                    'language': utils.get_language_tag(file_path, content=processed, overrides=processor.custom_languages)
                }
                lang = file_metadata[file_path]['language']
                stats['top_files'].append((content_tokens, file_size, rel_p_str, status, content_lines, lang))

                # Account for header/footer templates in the limit
                h_template = output_opts.get('header_template', utils.DEFAULT_CONFIG['output']['header_template'])
                f_template = output_opts.get('footer_template', utils.DEFAULT_CONFIG['output']['footer_template'])

                rendered_h = _render_template(
                    h_template, rel_p, size=file_size, tokens=content_tokens,
                    lines=content_lines, custom_languages=search_opts.get('custom_languages'),
                    git_info=stats, file_path=file_path
                )
                rendered_f = _render_template(
                    f_template, rel_p, size=file_size, tokens=content_tokens,
                    lines=content_lines, custom_languages=search_opts.get('custom_languages'),
                    git_info=stats, file_path=file_path
                )

                header_tokens = utils.estimate_tokens(rendered_h)[0]
                footer_tokens = utils.estimate_tokens(rendered_f)[0]
                header_lines = utils.count_lines(rendered_h)
                footer_lines = utils.count_lines(rendered_f)
                header_size = len(rendered_h.encode('utf-8'))
                footer_size = len(rendered_f.encode('utf-8'))

                # Total metrics for this file entry including its boundaries
                entry_tokens = content_tokens + header_tokens + footer_tokens
                entry_lines = content_lines + header_lines + footer_lines
                entry_size = content_size + header_size + footer_size

                if max_total_tokens > 0 and (current_tokens + overhead_tokens + entry_tokens) > max_total_tokens and (current_tokens + overhead_tokens) > 0:
                    token_limit_reached = True
                    stats['filter_reasons']['token_limit'] = len(all_combined_items) - i
                    logging.debug("Token limit reached; skipping %d remaining files.", len(all_combined_items) - i)
                    break

                if max_total_size > 0 and (current_size + overhead_size + entry_size) > max_total_size and (current_size + overhead_size) > 0:
                    size_limit_reached = True
                    stats['filter_reasons']['size_limit'] = len(all_combined_items) - i
                    logging.debug("Total size limit reached; skipping %d remaining files.", len(all_combined_items) - i)
                    break

                if max_total_lines > 0 and (current_lines + overhead_lines + entry_lines) > max_total_lines and (current_lines + overhead_lines) > 0:
                    line_limit_reached = True
                    stats['filter_reasons']['line_limit'] = len(all_combined_items) - i
                    logging.debug("Total line limit reached; skipping %d remaining files.", len(all_combined_items) - i)
                    break

                current_tokens += entry_tokens
                current_lines += entry_lines
                current_size += entry_size
                est_bar.set_postfix(size=utils.format_size(current_size), lines=f"{current_lines:,}", tokens=f"{current_tokens:,}")
                limited_items.append((file_path, root_path, is_excluded_by_size, processed))
                est_bar.update(1)

            est_bar.close()
            # Clear hashes before final output pass so they can be tracked again if needed,
            # but for combined files we want to keep them if we were using them for filtering.
            # Actually, we should clear them if we are going to re-process in the output pass.
            processor.seen_hashes.clear()
            all_combined_items = limited_items
            stats['token_limit_reached'] = token_limit_reached
            stats['size_limit_reached'] = size_limit_reached
            stats['line_limit_reached'] = line_limit_reached

            # Recalculate stats based on limited items
            stats['total_files'] = 0
            stats['total_size_bytes'] = 0
            stats['total_tokens'] = current_tokens
            stats['total_lines'] = current_lines
            stats['files_by_extension'] = {}
            stats['size_by_extension'] = {}
            stats['tokens_by_extension'] = {}
            stats['lines_by_extension'] = {}
            stats['files_by_language'] = {}
            stats['size_by_language'] = {}
            stats['tokens_by_language'] = {}
            stats['lines_by_language'] = {}
            for item in all_combined_items:
                file_p = item[0]
                meta = file_metadata.get(file_p, {})
                _update_file_stats(stats, file_p, size=meta.get('size'))
                _update_token_stats(stats, file_p, meta.get('tokens'))
                _update_line_stats(stats, file_p, meta.get('lines'))
            token_limit_pass_performed = True
        else:
            token_limit_pass_performed = False

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
            total_pairs = len(all_paired_items)
            for i, (root_path, pair_key, paths) in enumerate(all_paired_items):
                _process_paired_files(
                    [(pair_key, paths)],
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
                    pair_index=i + 1,
                    total_pairs=total_pairs,
                )
            processing_bar.close()

        # Process items (including Global Header, Table of Contents, Tree, and Footer) when combining many files into one
        if not pairing_enabled and not list_files and not tree_view:
            # Update global header tokens if they will be included in the output or estimation
            if (not dry_run or estimate_tokens) and output_format in ('text', 'markdown', 'xml'):
                if global_header:
                    rendered_h = _render_global_template(global_header, stats)
                    tokens, is_approx = utils.estimate_tokens(rendered_h)
                    lines = utils.count_lines(rendered_h)
                    _update_stats_metrics(stats, tokens, lines, is_approx)

            # Write global header after metadata pass to ensure placeholders are filled
            if global_header and not dry_run and not estimate_tokens and output_format in ('text', 'markdown', 'xml'):
                outfile.write(_render_global_template(global_header, stats))

            if output_opts.get('project_overview') and output_format in ('text', 'markdown'):
                overview_content = _generate_project_overview(
                    stats, output_format, processing_opts=config.get('processing')
                )
                if not dry_run or estimate_tokens:
                    token_count, is_approx = utils.estimate_tokens(overview_content)
                    line_count = utils.count_lines(overview_content)
                    _update_stats_metrics(stats, token_count, line_count, is_approx)
                if not dry_run and not estimate_tokens:
                    outfile.write(overview_content + "\n")

            if output_opts.get('include_tree') and output_format in ('text', 'markdown'):
                root_to_paths = {}
                for item in all_combined_items:
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
                            _update_stats_metrics(stats, token_count, line_count, is_approx)
                        if not dry_run and not estimate_tokens:
                            outfile.write(tree_content + "\n")

                    if not dry_run and not estimate_tokens:
                        outfile.write(tree_footer)

            if output_opts.get('table_of_contents') and output_format in ('text', 'markdown'):
                toc_files = [(item[0], item[1]) for item in all_combined_items]
                toc_content = _generate_table_of_contents(toc_files, output_format, metadata=file_metadata)

                if not dry_run or estimate_tokens:
                    token_count, is_approx = utils.estimate_tokens(toc_content)
                    line_count = utils.count_lines(toc_content)
                    _update_stats_metrics(stats, token_count, line_count, is_approx)
                if not dry_run and not estimate_tokens:
                    outfile.write(toc_content)

            processing_bar = processor._make_bar(
                total=len(all_combined_items),
                desc="Processing files",
                unit="file",
            )

            running_tokens = 0
            running_lines = 0
            running_size = 0

            total_items = len(all_combined_items)
            for i, item in enumerate(all_combined_items):
                file_path, root_path, is_excluded_by_size = item[:3]
                cached_processed = item[3] if len(item) > 3 else None
                item_index = i + 1

                rel_p = _get_rel_path(file_path, root_path)
                rel_p_str = rel_p.as_posix()
                processing_bar.set_description(f"Processing {_truncate_path(rel_p_str, 40)}")

                if mirror_enabled and not dry_run and not estimate_tokens:
                    target_file = Path(output_path) / rel_p
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    item_outfile_ctx = open(target_file, 'w', encoding='utf8', newline='')
                else:
                    item_outfile_ctx = nullcontext(outfile)

                with item_outfile_ctx as item_outfile:
                    if output_format in ('json', 'manifest') and not dry_run and not estimate_tokens:
                        if not first_item:
                            item_outfile.write(',')
                        first_item = False

                    token_count = 0
                    is_approx = True

                    if is_excluded_by_size:
                        logging.debug(
                            "File exceeds max size; writing placeholder: %s", rel_p_str
                        )
                        token_count, is_approx, line_count = processor.write_max_size_placeholder(
                            file_path, root_path, item_outfile,
                            index=item_index, total=total_items,
                            global_size=stats.get('total_size_bytes'),
                            global_tokens=stats.get('total_tokens'),
                            global_lines=stats.get('total_lines')
                        )
                    else:
                        token_count, is_approx, line_count = processor.process_and_write(
                            file_path,
                            root_path,
                            item_outfile,
                            cached_content=cached_processed,
                            index=item_index, total=total_items,
                            global_size=stats.get('total_size_bytes'),
                            global_tokens=stats.get('total_tokens'),
                            global_lines=stats.get('total_lines')
                        )

                if not token_limit_pass_performed and (not dry_run or estimate_tokens):
                    # Total tokens for this file entry include boundaries
                    h_template = output_opts.get('header_template', utils.DEFAULT_CONFIG['output']['header_template'])
                    f_template = output_opts.get('footer_template', utils.DEFAULT_CONFIG['output']['footer_template'])
                    rel_p = _get_rel_path(file_path, root_path)
                    f_size = file_path.stat().st_size if file_path.exists() else 0

                    rendered_h = _render_template(h_template, rel_p, size=f_size, tokens=token_count, lines=line_count, custom_languages=search_opts.get('custom_languages'), index=item_index, total=total_items, global_size=stats.get('total_size_bytes'), global_tokens=stats.get('total_tokens'), global_lines=stats.get('total_lines'), file_path=file_path)
                    rendered_f = _render_template(f_template, rel_p, size=f_size, tokens=token_count, lines=line_count, custom_languages=search_opts.get('custom_languages'), index=item_index, total=total_items, global_size=stats.get('total_size_bytes'), global_tokens=stats.get('total_tokens'), global_lines=stats.get('total_lines'), file_path=file_path)

                    header_tokens = utils.estimate_tokens(rendered_h)[0]
                    footer_tokens = utils.estimate_tokens(rendered_f)[0]
                    header_lines = utils.count_lines(rendered_h)
                    footer_lines = utils.count_lines(rendered_f)

                    _update_stats_metrics(stats, token_count + header_tokens + footer_tokens, line_count + header_lines + footer_lines, is_approx)
                    _update_token_stats(stats, file_path, token_count)
                    _update_line_stats(stats, file_path, line_count)

                f_size = file_path.stat().st_size if file_path.exists() else 0
                if not token_limit_pass_performed:
                    rel_p_str = _get_rel_path(file_path, root_path).as_posix()
                    status = stats.get('file_statuses', {}).get(rel_p_str)
                    lang = _get_stat_lang(file_path, stats)
                    stats['top_files'].append((token_count, f_size, rel_p_str, status, line_count, lang))

                running_tokens += token_count
                running_lines += line_count
                running_size += f_size
                processing_bar.set_postfix(size=utils.format_size(running_size), lines=f"{running_lines:,}", tokens=f"{running_tokens:,}")
                processing_bar.update(1)

            processing_bar.close()

        # Process global footer and update stats
        if not pairing_enabled and not list_files and not tree_view and global_footer and output_format in ('text', 'markdown', 'xml'):
            if not dry_run or estimate_tokens:
                rendered_f = _render_global_template(global_footer, stats)
                tokens, is_approx = utils.estimate_tokens(rendered_f)
                lines = utils.count_lines(rendered_f)
                _update_stats_metrics(stats, tokens, lines, is_approx)

            if not dry_run and not estimate_tokens:
                outfile.write(_render_global_template(global_footer, stats))

        if not pairing_enabled and not dry_run and not estimate_tokens and not list_files and not tree_view and output_format in ('json', 'manifest'):
            outfile.write(']')

    stats['excluded_folder_count'] = total_excluded_folders

    if (dry_run and output_opts.get('show_diff') and output_path and output_path != '-' and not pairing_enabled):
        new_content = clipboard_buffer.getvalue()
        if Path(output_path).exists():
            old_content, _ = read_file_best_effort(output_path)
            _print_diff(old_content, new_content, output_path)

    if clipboard and clipboard_buffer is not None:
        combined_output = clipboard_buffer.getvalue()
        pyperclip = _get_pyperclip()
        if pyperclip:
            pyperclip.copy(combined_output)
            logging.info("Copied combined output to clipboard.")
        else:
            logging.error("The 'pyperclip' tool is required for clipboard support. Install it with: pip install pyperclip")
            # We don't exit here as the output might have been written elsewhere or be the only intended action.
            # But usually if --clipboard is requested, user wants it there.
            # If they didn't specify an output file, it goes to stdout by default too?
            # Let's check if we should exit.
            # The previous code didn't check, just failed with AttributeError.
            pass

    return stats


def main():
    """Main function to parse arguments and run the tool."""
    start_time = time.perf_counter()
    parser = argparse.ArgumentParser(
        description=(
            "A versatile tool for the terminal to find, filter, and combine source code files "
            "from a project into one file (or folder). Use it to give better context to AI "
            "models, generate documentation, or save work."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              # Combine files in the current folder into 'combined_files.txt'
              python sourcecombine.py

              # Combine files from a specific folder
              python sourcecombine.py src/

              # Use a configuration file
              python sourcecombine.py my_config.yml

              # Use a configuration but override the folders to search
              python sourcecombine.py my_config.yml project_a/ project_b/

              # Copy the result to the system clipboard
              python sourcecombine.py src/ -c

              # Estimate how many tokens the output will use
              python sourcecombine.py -e

              # Skip the 'tests' folder and all '.json' files
              python sourcecombine.py -X tests -x "*.json"

              # Rebuild files from a combined file
              python sourcecombine.py --extract combined_files.txt

              # Verify files against a combined manifest
              python sourcecombine.py --verify combined_files.json
        """),
    )

    # Core Options Group
    core_group = parser.add_argument_group("Core Options")
    core_group.add_argument(
        "targets",
        nargs="*",
        metavar="TARGET",
        help="Folders or files to search. If empty, the tool searches the current folder. If the first target is a YAML file (.yml or .yaml), it is used as the configuration.",
    )
    core_group.add_argument(
        "--config",
        "-k",
        metavar="PATH",
        help="Use a specific configuration file. This stops the tool from trying to find one automatically in the target list.",
    )
    core_group.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Save the result to a specific file or folder. This takes priority over the path in the settings. Supports template placeholders (for example, '{{PROJECT_NAME}}_{{DATE}}.txt').",
    )
    core_group.add_argument(
        "--dry-run",
        "--preview",
        "-d",
        action="store_true",
        help="Show what would happen without making any changes.",
    )
    core_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed status messages to help find and fix problems.",
    )

    # Project Information Group
    project_group = parser.add_argument_group("Project Information")
    project_group.add_argument(
        "--project-name",
        metavar="NAME",
        help="Override the project name used in templates and reports.",
    )
    project_group.add_argument(
        "--project-version",
        metavar="VERSION",
        help="Override the project version used in templates and reports.",
    )
    project_group.add_argument(
        "--project-description",
        metavar="TEXT",
        help="Override the project description used in templates and reports.",
    )
    project_group.add_argument(
        "--project-license",
        metavar="NAME",
        help="Override the project license used in templates and reports.",
    )
    project_group.add_argument(
        "--project-url",
        metavar="URL",
        help="Override the project URL used in templates and reports.",
    )

    # Filtering & Selection Group
    filtering_group = parser.add_argument_group("Filtering & Selection")
    filtering_group.add_argument(
        "--exclude",
        "--exclude-file",
        "-x",
        dest="exclude_file",
        action="append",
        metavar="PATTERN",
        default=[],
        help="Skip files that match this pattern (for example, '*.log'). Can be used multiple times.",
    )
    filtering_group.add_argument(
        "--exclude-folder",
        "--exclude-dir",
        "-X",
        dest="exclude_folder",
        action="append",
        metavar="PATTERN",
        default=[],
        help="Skip folders that match this pattern (for example, 'build'). Can be used multiple times.",
    )
    filtering_group.add_argument(
        "--include",
        "--include-file",
        "-i",
        action="append",
        metavar="PATTERN",
        default=[],
        help="Include only files that match this pattern (for example, '*.py'). Can be used multiple times.",
    )
    filtering_group.add_argument(
        "--extension",
        "--ext",
        action="append",
        metavar="EXT",
        default=[],
        help="Include only files with these extensions (for example, 'py', 'js'). Can be used multiple times.",
    )
    filtering_group.add_argument(
        "--exclude-extension",
        "--exclude-ext",
        action="append",
        metavar="EXT",
        default=[],
        help="Skip files with these extensions (for example, 'log', 'tmp'). Can be used multiple times.",
    )
    filtering_group.add_argument(
        "--language",
        "--lang",
        action="append",
        metavar="LANG",
        default=[],
        help="Include only files of these languages (for example, 'python', 'cpp'). Can be used multiple times. See --list-languages for a full list.",
    )
    filtering_group.add_argument(
        "--exclude-language",
        "--exclude-lang",
        action="append",
        metavar="LANG",
        default=[],
        help="Skip files of these languages (for example, 'javascript', 'html'). Can be used multiple times.",
    )
    filtering_group.add_argument(
        "--since",
        "-S",
        metavar="TIME",
        help="Include files modified since this time (for example, '1d', '2h', 'YYYY-MM-DD').",
    )
    filtering_group.add_argument(
        "--until",
        "-U",
        metavar="TIME",
        help="Include files modified before this time (for example, '1d', '2h', 'YYYY-MM-DD').",
    )
    filtering_group.add_argument(
        "--min-size",
        metavar="SIZE",
        help="Include only files at least this size (for example, '10KB', '1MB').",
    )
    filtering_group.add_argument(
        "--max-size",
        metavar="SIZE",
        help="Include only files at most this size (for example, '10KB', '1MB').",
    )
    filtering_group.add_argument(
        "--min-tokens",
        type=int,
        metavar="N",
        help="Include only files with at least this many tokens.",
    )
    filtering_group.add_argument(
        "--max-file-tokens",
        type=int,
        metavar="N",
        help="Include only files with at most this many tokens.",
    )
    filtering_group.add_argument(
        "--min-lines",
        type=int,
        metavar="N",
        help="Include only files with at least this many lines.",
    )
    filtering_group.add_argument(
        "--max-file-lines",
        type=int,
        metavar="N",
        help="Include only files with at most this many lines.",
    )
    filtering_group.add_argument(
        "--files-from",
        metavar="PATH",
        help="Read a list of files from a text file (use '-' for the terminal). This skips looking for files in folders.",
    )
    filtering_group.add_argument(
        "--grep",
        "-g",
        metavar="REGEX",
        help="Include only files whose content matches this regular expression.",
    )
    filtering_group.add_argument(
        "--exclude-grep",
        "-E",
        metavar="REGEX",
        help="Skip files whose content matches this regular expression.",
    )
    filtering_group.add_argument(
        "--skip-binary",
        "-B",
        action="store_true",
        help="Skip files that contain non-text data (binary files).",
    )
    filtering_group.add_argument(
        "--max-depth",
        "-D",
        type=int,
        metavar="N",
        help="Limit folder scanning to this depth (for example, '-D 1' for root files only; 0 for no limit).",
    )
    filtering_group.add_argument(
        "--git-files",
        "-G",
        action="store_true",
        help="Use 'git ls-files' to find files. This follows the .gitignore rules.",
    )
    filtering_group.add_argument(
        "--git-diff",
        nargs="?",
        const=True,
        metavar="REF",
        help="Include only files changed in Git since REF (default: HEAD, staged, and untracked).",
    )
    filtering_group.add_argument(
        "--staged",
        action="store_true",
        help="Include only staged changes in Git. This automatically enables Git diff functionality.",
    )
    filtering_group.add_argument(
        "--unstaged",
        action="store_true",
        help="Include only unstaged and untracked changes in Git. This automatically enables Git diff functionality.",
    )
    filtering_group.add_argument(
        "--unique",
        "-u",
        action="store_true",
        help="Skip duplicate files by path or content (duplicate removal).",
    )
    filtering_group.add_argument(
        "--strip-components",
        type=int,
        default=0,
        metavar="N",
        help="Remove N leading components from file paths during extraction or verification.",
    )
    filtering_group.add_argument(
        "--map-lang",
        nargs=2,
        action="append",
        metavar=("EXTENSION", "LANGUAGE"),
        help="Manually map a file extension or filename to a specific language (for example, '.mjml' 'html'). Can be used multiple times.",
    )

    # Sorting & Limiting Group
    sorting_group = parser.add_argument_group("Sorting & Limiting")
    sorting_group.add_argument(
        "--sort",
        "-s",
        choices=["name", "size", "modified", "tokens", "lines", "depth", "language"],
        help="Sort files by name, size, date (modified), tokens, lines, folder depth, or language before combining.",
    )
    sorting_group.add_argument(
        "--reverse",
        "-r",
        action="store_true",
        help="Reverse the sort order.",
    )
    sorting_group.add_argument(
        "--limit",
        "-L",
        type=int,
        metavar="N",
        help="Stop processing once you reach this file limit.",
    )
    sorting_group.add_argument(
        "--max-tokens",
        "-M",
        type=int,
        metavar="N",
        help="Stop processing once you reach the total tokens limit (only when combining many files or extracting).",
    )
    sorting_group.add_argument(
        "--max-total-size",
        metavar="SIZE",
        help="Stop processing once you reach the total size limit (for example, '5MB') (only when combining many files or extracting).",
    )
    sorting_group.add_argument(
        "--max-total-lines",
        type=int,
        metavar="N",
        help="Stop processing once you reach the total lines limit (only when combining many files or extracting).",
    )

    # Output Options Group
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--ai",
        "-a",
        action="store_true",
        help=(
            "Enable preset for AI models (Markdown, line numbers, Table of Contents, tree, project overview, "
            "skipping binary, duplicate removal, and Git context (logs and diffs)). Copies to clipboard if "
            "no output is specified."
        ),
    )
    output_group.add_argument(
        "--clipboard",
        "-c",
        action="store_true",
        help="Use the system clipboard to save combined output or read content for extraction.",
    )
    output_group.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "jsonl", "markdown", "xml", "manifest", "csv"],
        help="Choose the output format ('text', 'json', 'jsonl', 'markdown', 'xml', 'manifest', 'csv'). 'json', 'jsonl', 'manifest', and 'csv' only work when combining many files into one.",
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
        "--jsonl",
        "-J",
        action="store_true",
        help="Shortcut for '--format jsonl'.",
    )
    output_group.add_argument(
        "--xml",
        "-w",
        action="store_true",
        help="Shortcut for '--format xml'.",
    )
    output_group.add_argument(
        "--csv",
        action="store_true",
        help="Shortcut for '--format csv'.",
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
        help="Add a Table of Contents with sizes and tokens to the start of the output (only when combining many files into one in 'text' or 'markdown' formats).",
    )
    output_group.add_argument(
        "--include-tree",
        "-p",
        action="store_true",
        help="Include a visual folder tree with details at the start of the output (only when combining many files into one).",
    )
    output_group.add_argument(
        "--overview",
        action="store_true",
        help="Add a project overview summary with statistics and language breakdown to the start of the output (only when combining many files into one).",
    )
    output_group.add_argument(
        "--git-log",
        nargs="?",
        const=5,
        type=int,
        metavar="N",
        help="Include the last N git commit messages in the project overview and templates ({{GIT_LOG}}). Default is 5 if the flag is present.",
    )
    output_group.add_argument(
        "--include-diff",
        action="store_true",
        help="Include the Git diff in the project overview and templates ({{GIT_DIFF}} and {{FILE_DIFF}}).",
    )
    output_group.add_argument(
        "--header",
        metavar="TEMPLATE",
        help="Override the template written before each file's content.",
    )
    output_group.add_argument(
        "--footer",
        metavar="TEMPLATE",
        help="Override the template written after each file's content.",
    )
    output_group.add_argument(
        "--global-header",
        metavar="TEMPLATE",
        help="Override the template written at the very beginning of the output.",
    )
    output_group.add_argument(
        "--global-footer",
        metavar="TEMPLATE",
        help="Override the template written at the very end of the output.",
    )
    output_group.add_argument(
        "--max-size-placeholder",
        metavar="TEMPLATE",
        help="Override the placeholder written when a file exceeds the size limit.",
    )
    output_group.add_argument(
        "--json-summary",
        metavar="PATH",
        help="Save an execution summary (file counts, tokens, duration) in JSON format. Use '-' to print it to the terminal. Supports template placeholders.",
    )
    output_group.add_argument(
        "--mirror",
        action="store_true",
        help="Recreate the input directory structure in the output folder, applying all filtering and processing rules to each file individually.",
    )
    output_group.add_argument(
        "--no-content",
        action="store_true",
        help="Skip the actual file content in the output, while keeping templates and metadata. (Supported in all formats).",
    )

    # Pairing Options Group
    pairing_group = parser.add_argument_group("Pairing Options")
    pairing_group.add_argument(
        "--pair",
        nargs=2,
        action="append",
        metavar=("SOURCE_EXT", "HEADER_EXT"),
        help="Enable file pairing by matching source and header extensions (for example, '.cpp' '.h'). Can be used multiple times.",
    )
    pairing_group.add_argument(
        "--include-unpaired",
        action="store_true",
        help="Include files that do not have a matching pair when pairing is enabled.",
    )
    pairing_group.add_argument(
        "--pair-template",
        metavar="TEMPLATE",
        help="Set the filename template for paired output (for example, '{{STEM}}.combined').",
    )

    # Display & Preview Group
    display_group = parser.add_argument_group("Display & Preview")
    display_group.add_argument(
        "--estimate-tokens",
        "-e",
        action="store_true",
        help="Calculate total tokens without writing any files. This is slower because every file must be read.",
    )
    display_group.add_argument(
        "--list-files",
        "-l",
        action="store_true",
        help="Show a list of all files that would be included and exit.",
    )
    display_group.add_argument(
        "--tree",
        "-t",
        action="store_true",
        help="Show a visual folder tree of all included files with details and exit.",
    )
    display_group.add_argument(
        "--diff",
        action="store_true",
        help="Show a colored diff of changes (when using --output, --apply-in-place, --extract, or --verify).",
    )

    # Processing Group
    processing_group = parser.add_argument_group("Processing")
    processing_group.add_argument(
        "--compact",
        "-C",
        action="store_true",
        help="Clean up extra spaces and blank lines in the output.",
    )
    processing_group.add_argument(
        "--apply-in-place",
        action="store_true",
        help="Apply processing rules directly to the source files (WARNING: modifies the files!).",
    )
    processing_group.add_argument(
        "--create-backups",
        action="store_true",
        help="Create '.bak' copies of original files when using --apply-in-place.",
    )
    processing_group.add_argument(
        "--remove-comments",
        action="store_true",
        help="Remove both single-line and multi-line comments based on the detected language.",
    )
    processing_group.add_argument(
        "--remove-single-line-comments",
        action="store_true",
        help="Remove only single-line comments based on the detected language.",
    )
    processing_group.add_argument(
        "--max-lines",
        type=int,
        metavar="N",
        help="Shorten each file to this many lines before combining.",
    )
    processing_group.add_argument(
        "--truncate-tokens",
        type=int,
        metavar="N",
        help="Shorten each file to this many tokens before combining.",
    )
    processing_group.add_argument(
        "--replace",
        nargs=2,
        action="append",
        metavar=("REGEX", "REPLACEMENT"),
        help="Add a global search-and-replace rule using regular expressions. Can be used multiple times.",
    )
    processing_group.add_argument(
        "--replace-line",
        nargs=2,
        action="append",
        metavar=("REGEX", "REPLACEMENT"),
        help="Add a line-based regular expression rule to find and replace content. Matching lines that follow each other are replaced by a single entry. Can be used multiple times.",
    )

    # Utility Commands Group
    utility_group = parser.add_argument_group("Utility Commands")
    utility_group.add_argument(
        "--init",
        action="store_true",
        help="Create a basic 'sourcecombine.yml' configuration file in the current folder to get started.",
    )
    utility_group.add_argument(
        "--list-languages",
        action="store_true",
        help="Show a list of all supported language identifiers and exit.",
    )
    utility_group.add_argument(
        "--list-placeholders",
        action="store_true",
        help="Show all supported template placeholders and exit.",
    )
    utility_group.add_argument(
        "--extract",
        action="store_true",
        help=(
            "Rebuild original files and folders from combined outputs (JSON, XML, Markdown, etc.). "
            "Supports filtering, sorting, and processing."
        ),
    )
    utility_group.add_argument(
        "--keep-line-numbers",
        action="store_true",
        help="Keep line numbers when extracting files. By default, the tool removes them automatically if detected.",
    )
    utility_group.add_argument(
        "--restore",
        action="store_true",
        help="Undo 'apply-in-place' changes by restoring original files from their .bak copies. This command scans target folders recursively for backup files.",
    )
    utility_group.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Verify that files on disk match the content or hashes in combined files or manifests. "
            "Read from files, folders, remote URLs, the terminal, or the clipboard. "
            "Searches for standard defaults if no input is provided."
        ),
    )
    utility_group.add_argument(
        "--repair",
        action="store_true",
        help="Automatically fix mismatched or missing files when verifying (requires source content).",
    )
    utility_group.add_argument(
        "--delete-backups",
        "--clean",
        action="store_true",
        help="Remove all '.bak' files from target folders. Use this to clean up after '--apply-in-place'.",
    )
    utility_group.add_argument(
        "--show-config",
        action="store_true",
        help="Show the final combined configuration (including defaults, files, and options) and exit.",
    )
    utility_group.add_argument(
        "--export-config",
        nargs="?",
        const="sourcecombine.yml",
        metavar="FILENAME",
        help="Save the final configuration to a YAML file (defaults to 'sourcecombine.yml') and exit.",
    )
    utility_group.add_argument(
        "--system-info",
        action="store_true",
        help="Show details about the system and environment.",
    )
    utility_group.add_argument(
        "--project-info",
        action="store_true",
        help="Show detected project information and Git status for the current project.",
    )
    utility_group.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the tool's version and exit.",
    )
    args = parser.parse_args()

    # Handle the AI preset option by enabling several other options
    if args.ai:
        args.markdown = True
        args.line_numbers = True
        args.toc = True
        args.include_tree = True
        args.overview = True
        args.skip_binary = True
        args.unique = True

        # Automatically include Git context if not explicitly disabled
        if args.git_log is None:
            args.git_log = 5
        args.include_diff = True

        # If no explicit output is provided, attempt to use the system clipboard
        if not args.output and not args.clipboard and not (
            args.dry_run or args.list_files or args.tree or args.estimate_tokens
        ):
            if importlib.util.find_spec("pyperclip"):
                args.clipboard = True
                logging.debug("AI preset: Automatically enabled the system clipboard.")

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

    if args.system_info:
        print_system_info()
        sys.exit(0)

    if getattr(args, 'project_info', None) is True:
        # We need to load and validate config first to get root folders and metadata overrides
        targets = args.targets
        config_path = args.config
        remaining_targets = []
        if targets:
            first = targets[0]
            if (not config_path and not args.extract and
                first.lower().endswith(('.yml', '.yaml')) and not Path(first).is_dir()):
                config_path = first
                remaining_targets = targets[1:]
            else:
                remaining_targets = targets
        if not config_path and not remaining_targets:
            defaults = ['sourcecombine.yml', 'sourcecombine.yaml', 'config.yml', 'config.yaml']
            for d in defaults:
                if Path(d).is_file():
                    config_path = d
                    break
        try:
            if config_path:
                config = load_and_validate_config(config_path)
            else:
                config = copy.deepcopy(utils.DEFAULT_CONFIG)
                utils.validate_config(config)
        except (ConfigNotFoundError, utils.InvalidConfigError) as e:
            _handle_invalid_config_error(e, args.verbose)

        if remaining_targets:
            config['search']['root_folders'] = remaining_targets
        elif not config.get('search', {}).get('root_folders'):
            config.setdefault('search', {})['root_folders'] = ["."]

        _apply_project_overrides(config, args)

        stats = {}
        root = config['search']['root_folders'][0]
        _populate_project_stats(stats, root, config)
        git_info = _get_git_info(root, log_count=config['output'].get('git_log_count', 0), include_diff=config['output'].get('include_diff', False))
        stats.update(git_info)
        print_project_info(stats)
        sys.exit(0)

    if args.list_placeholders:
        print_placeholders()
        sys.exit(0)

    if args.list_languages:
        print(f"\n{C_BOLD}{C_CYAN}Supported Languages and Mappings:{C_RESET}")

        # Group extensions and filenames by language tag
        lang_groups = {}
        for ext, lang in utils.EXTENSION_TO_LANG.items():
            lang_groups.setdefault(lang, []).append(ext)
        for name, lang in utils.FILENAME_TO_LANG.items():
            lang_groups.setdefault(lang, []).append(name)

        # Format the output as a table
        lang_tags = sorted(lang_groups.keys())
        tag_width = 15
        desc_width = max(40, shutil.get_terminal_size((80, 20)).columns - tag_width - 6)

        print(f"  {C_DIM}{'LANGUAGE TAG':<{tag_width}}  EXTENSION / FILENAME MAPPINGS{C_RESET}")
        for tag in lang_tags:
            items = sorted(lang_groups[tag])
            items_str = ", ".join(items)

            # Wrap long lists of extensions
            wrapped = textwrap.wrap(items_str, width=desc_width)

            # Print the first line with the tag
            first_line = wrapped[0] if wrapped else ""
            print(f"  {C_BOLD}{C_CYAN}{tag:<{tag_width}}{C_RESET}  {C_DIM}{first_line}{C_RESET}")

            # Print subsequent lines indented
            for line in wrapped[1:]:
                print(f"  {' ':<{tag_width}}  {C_DIM}{line}{C_RESET}")

        print(f"\n{C_BOLD}Total:{C_RESET} {len(lang_tags)} languages supported.\n")
        sys.exit(0)

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
                    f.write("# Default SourceCombine Configuration\n")
                    if utils.yaml:
                        utils.yaml.dump(utils.DEFAULT_CONFIG, f, sort_keys=False)
                    else:
                        logging.warning("PyYAML not found; creating an empty configuration.")
                logging.info("Created a simple configuration at %s", target_config.resolve())
            except OSError as exc:
                logging.error("Could not write the configuration file: %s", exc)
                sys.exit(1)
        sys.exit(0)

    targets = args.targets
    config = None
    config_path = args.config
    remaining_targets = []

    if targets:
        first = targets[0]
        # Auto-detect config only if --config wasn't used and we aren't extracting.
        # This keeps the behavior consistent for simple cases while adding
        # explicit control for advanced ones.
        if (not config_path and not args.extract and
            first.lower().endswith(('.yml', '.yaml')) and not Path(first).is_dir()):
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
        except utils.InvalidConfigError as e:
            _handle_invalid_config_error(e, args.verbose, f"The configuration is not valid: {e}")

    # Initialize with defaults if no config was loaded
    if config is None:
        config = copy.deepcopy(utils.DEFAULT_CONFIG)

    # Ensure all default sections and values exist
    utils.validate_config(config)

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
        except utils.InvalidConfigError as e:
            _handle_invalid_config_error(e, args.verbose, f"The configuration is not valid: {e}")

    if args.restore:
        # Use the finalized root folders for restoration
        restore_targets = config.get('search', {}).get('root_folders', ["."])
        restore_backups(restore_targets, dry_run=args.dry_run)
        sys.exit(0)

    if args.delete_backups:
        # Use the finalized root folders for deletion
        delete_targets = config.get('search', {}).get('root_folders', ["."])
        delete_backups(delete_targets, dry_run=args.dry_run)
        sys.exit(0)

    # Re-configure level based on config, *unless* -v was used.
    # The -v (DEBUG) option always overrides the configuration file's setting.
    if not args.verbose:
        level_str = config.get('logging', {}).get('level', 'INFO')
        log_level = getattr(logging, level_str.upper(), logging.INFO)
        # Set the level on the *root logger* since basicConfig was already called
        logging.getLogger().setLevel(log_level)

    # Inject CLI exclusions into config
    if args.exclude_file or args.exclude_folder:
        filters = config['filters']
        exclusions = filters['exclusions']

        if args.exclude_file:
            filenames = exclusions['filenames']
            for pattern in args.exclude_file:
                # Validate/sanitize the pattern
                sanitized = utils.validate_glob_pattern(pattern, context="--exclude-file")
                filenames.append(sanitized)
            logging.debug("Added terminal file exclusions: %s", args.exclude_file)

        if args.exclude_folder:
            folders = exclusions['folders']
            for pattern in args.exclude_folder:
                sanitized = utils.validate_glob_pattern(pattern, context="--exclude-folder")
                folders.append(sanitized)
            logging.debug("Added terminal folder exclusions: %s", args.exclude_folder)

    # Inject terminal inclusions into config
    if args.include:
        filters = config['filters']
        groups = filters['inclusion_groups']

        # Create a unique group for terminal inclusions and enable it
        groups['_cli_includes'] = {
            'enabled': True,
            'filenames': [utils.validate_glob_pattern(p, context="--include") for p in args.include]
        }
        logging.debug("Added terminal file inclusions: %s", args.include)

    if args.map_lang:
        custom_langs = config['search'].setdefault('custom_languages', {})
        if custom_langs is None:
            custom_langs = config['search']['custom_languages'] = {}
        for pattern, lang in args.map_lang:
            custom_langs[pattern.lower()] = lang.lower()
        logging.debug("Added terminal language mappings: %s", args.map_lang)

    search = config.get('search') or {}

    cli_extensions = getattr(args, 'extension', [])
    if cli_extensions:
        if not isinstance(search.get('allowed_extensions'), list):
            search['allowed_extensions'] = []
        search['allowed_extensions'].extend(cli_extensions)
        logging.debug("Added terminal extension inclusions: %s", cli_extensions)

    cli_exclude_extensions = getattr(args, 'exclude_extension', [])
    if cli_exclude_extensions:
        if not isinstance(search.get('exclude_extensions'), list):
            search['exclude_extensions'] = []
        search['exclude_extensions'].extend(cli_exclude_extensions)
        logging.debug("Added terminal extension exclusions: %s", cli_exclude_extensions)

    if args.language:
        if not isinstance(search.get('allowed_languages'), list):
            search['allowed_languages'] = []
        search['allowed_languages'].extend(args.language)
        logging.debug("Added terminal language inclusions: %s", args.language)

    if args.exclude_language:
        if not isinstance(search.get('exclude_languages'), list):
            search['exclude_languages'] = []
        search['exclude_languages'].extend(args.exclude_language)
        logging.debug("Added terminal language exclusions: %s", args.exclude_language)

    pairing_conf = config.get('pairing') or {}

    if args.pair:
        pairing_conf['enabled'] = True
        source_exts = pairing_conf.get('source_extensions')
        if not isinstance(source_exts, list):
            source_exts = pairing_conf['source_extensions'] = []
        header_exts = pairing_conf.get('header_extensions')
        if not isinstance(header_exts, list):
            header_exts = pairing_conf['header_extensions'] = []

        for src, hdr in args.pair:
            # Ensure extensions have leading dots
            if not src.startswith('.'):
                src = '.' + src
            if not hdr.startswith('.'):
                hdr = '.' + hdr
            source_exts.append(src.lower())
            header_exts.append(hdr.lower())
        logging.debug("Added terminal pairing rules: %s", args.pair)

    if args.include_unpaired:
        pairing_conf['include_mismatched'] = True
        logging.debug("Terminal enabled include_mismatched pairing.")

    output_conf = config.get('output') or {}

    if args.pair_template:
        output_conf['paired_filename_template'] = args.pair_template
        logging.debug("Terminal set paired_filename_template: %s", args.pair_template)
    config['pairing'] = pairing_conf
    config['output'] = output_conf
    config['search'] = search

    if args.output and not args.extract:
        if pairing_conf.get('enabled'):
            output_conf['folder'] = args.output
        else:
            output_conf['file'] = args.output

    if args.max_tokens is not None:
        config['filters']['max_total_tokens'] = args.max_tokens

    if args.max_total_size is not None:
        try:
            config['filters']['max_total_size_bytes'] = utils.parse_size_value(args.max_total_size)
        except utils.InvalidConfigError as e:
            _handle_invalid_config_error(e, args.verbose)

    if args.min_tokens is not None:
        config['filters']['min_tokens'] = args.min_tokens
    if args.max_file_tokens is not None:
        config['filters']['max_tokens'] = args.max_file_tokens
    if args.min_lines is not None:
        config['filters']['min_lines'] = args.min_lines
    if args.max_file_lines is not None:
        config['filters']['max_lines'] = args.max_file_lines

    if args.max_total_lines is not None:
        config['filters']['max_total_lines'] = args.max_total_lines

    if args.limit is not None:
        config['filters']['max_files'] = args.limit

    if args.max_depth is not None:
        config['search']['max_depth'] = args.max_depth

    if args.grep:
        config['filters']['grep'] = args.grep

    if args.exclude_grep:
        config['filters']['exclude_grep'] = args.exclude_grep

    if args.skip_binary:
        config['filters']['skip_binary'] = True

    if args.unique:
        config['filters']['unique'] = True

    if args.git_files:
        config['search']['use_git'] = True

    if args.git_diff:
        config['search']['use_git_diff'] = True
        if isinstance(args.git_diff, str):
            config['search']['git_diff_ref'] = args.git_diff

    if args.staged:
        config['search']['git_staged'] = True
        config['search']['use_git_diff'] = True

    if args.unstaged:
        config['search']['git_unstaged'] = True
        config['search']['use_git_diff'] = True

    if args.since or args.until:
        filters = config['filters']
        try:
            if args.since:
                filters['modified_since'] = utils.parse_time_value(args.since)
            if args.until:
                filters['modified_until'] = utils.parse_time_value(args.until)
        except utils.InvalidConfigError as e:
            _handle_invalid_config_error(e, args.verbose)

    if args.min_size or args.max_size:
        filters = config['filters']
        try:
            if args.min_size:
                filters['min_size_bytes'] = utils.parse_size_value(args.min_size)
            if args.max_size:
                filters['max_size_bytes'] = utils.parse_size_value(args.max_size)
        except utils.InvalidConfigError as e:
            _handle_invalid_config_error(e, args.verbose)

    if args.toc:
        output_conf['table_of_contents'] = True

    if args.json_summary:
        output_conf['summary_json'] = args.json_summary

    if getattr(args, 'mirror', False):
        output_conf['mirror'] = True

    if getattr(args, 'no_content', False):
        output_conf['skip_content'] = True

    if args.line_numbers:
        output_conf['add_line_numbers'] = True

    if args.include_tree:
        output_conf['include_tree'] = True

    if getattr(args, 'overview', False):
        output_conf['project_overview'] = True

    _apply_project_overrides(config, args)

    if args.diff:
        output_conf['show_diff'] = True

    if args.compact:
        config['processing']['compact_whitespace'] = True

    if args.apply_in_place:
        config['processing']['apply_in_place'] = True

    if args.create_backups:
        config['processing']['create_backups'] = True

    if getattr(args, 'remove_comments', False):
        config['processing']['remove_comments'] = True

    if getattr(args, 'remove_single_line_comments', False):
        config['processing']['remove_single_line_comments'] = True

    if args.max_lines is not None:
        config['processing']['max_lines'] = args.max_lines

    if args.truncate_tokens is not None:
        config['processing']['max_tokens'] = args.truncate_tokens

    if args.replace:
        regex_rules = config['processing'].setdefault('regex_replacements', [])
        if regex_rules is None:
            regex_rules = config['processing']['regex_replacements'] = []
        for pattern, replacement in args.replace:
            regex_rules.append({'pattern': pattern, 'replacement': replacement})
        logging.debug("Added %d terminal regex replacements.", len(args.replace))

    if args.replace_line:
        line_rules = config['processing'].setdefault('line_regex_replacements', [])
        if line_rules is None:
            line_rules = config['processing']['line_regex_replacements'] = []
        for pattern, replacement in args.replace_line:
            line_rules.append({'pattern': pattern, 'replacement': replacement})
        logging.debug("Added %d terminal line regex replacements.", len(args.replace_line))

    if args.sort:
        output_conf['sort_by'] = args.sort

    if args.reverse:
        output_conf['sort_reverse'] = True

    # Determine the effective output format. Terminal options take precedence over configuration.
    # Handle git-log if provided
    if args.git_log is not None:
        output_conf['git_log_count'] = args.git_log

    if getattr(args, 'include_diff', False):
        output_conf['include_diff'] = True

    if args.header is not None:
        output_conf['header_template'] = args.header
    if args.footer is not None:
        output_conf['footer_template'] = args.footer
    if args.global_header is not None:
        output_conf['global_header_template'] = args.global_header
    if args.global_footer is not None:
        output_conf['global_footer_template'] = args.global_footer
    if args.max_size_placeholder is not None:
        output_conf['max_size_placeholder'] = args.max_size_placeholder

    if args.markdown:
        args.format = "markdown"
    elif args.json:
        args.format = "json"
    elif getattr(args, 'jsonl', False):
        args.format = "jsonl"
    elif args.xml:
        args.format = "xml"
    elif getattr(args, 'csv', False):
        args.format = "csv"

    explicit_files = None
    if args.files_from:
        explicit_files = []
        try:
            if args.files_from == '-':
                source_name = "stdin"
                input_ctx = nullcontext(sys.stdin)
            else:
                source_name = args.files_from
                input_ctx = open(args.files_from, 'r', encoding='utf-8')

            with input_ctx as f:
                for line in f:
                    line = line.strip()
                    if line:
                        explicit_files.append(Path(line).resolve())

            logging.info("Read %d file paths from %s.", len(explicit_files), source_name)

        except OSError as e:
            logging.error("Failed to read file list from '%s': %s", args.files_from, e)
            sys.exit(1)

    pairing_enabled = pairing_conf.get('enabled')
    mirror_enabled = output_conf.get('mirror', False)

    # Auto-detect format from extension if not explicitly set via CLI flags
    effective_output = args.output if (args.output and args.output != '-') else output_conf.get('file')
    if not args.format and not pairing_enabled and effective_output:
        ext = Path(effective_output).suffix.lower()
        if ext in ('.md', '.markdown'):
            args.format = 'markdown'
        elif ext == '.json':
            args.format = 'json'
        elif ext == '.jsonl':
            args.format = 'jsonl'
        elif ext == '.xml':
            args.format = 'xml'
        elif ext == '.csv':
            args.format = 'csv'

    if not args.format:
        args.format = output_conf.get('format', 'text')
    output_conf['format'] = args.format

    if args.show_config:
        logging.info("Final merged configuration:")
        if utils.yaml:
            utils.yaml.dump(_convert_to_json_friendly(config), sys.stdout, sort_keys=False)
        else:
            json.dump(_convert_to_json_friendly(config), sys.stdout, indent=2)
        sys.exit(0)

    if args.export_config:
        try:
            utils.save_yaml_config(args.export_config, _convert_to_json_friendly(config))
            logging.info("Configuration exported to %s", Path(args.export_config).resolve())
        except (OSError, utils.InvalidConfigError) as exc:
            logging.error("Could not export configuration: %s", exc)
            sys.exit(1)
        sys.exit(0)

    if mirror_enabled:
        output_path = output_conf.get('folder') or output_conf.get('file')
        if not output_path:
            raise utils.InvalidConfigError("You must set an output folder for mirror mode.")
    elif pairing_enabled:
        output_path = output_conf.get('folder')
    else:
        # Determine the effective output file, falling back to the default if not set.
        current_output_file = output_conf.get('file', DEFAULT_OUTPUT_FILENAME)

        # If the target is an existing folder or ends with a trailing slash,
        # treat it as a folder and put the default filename inside it.
        is_intended_dir = False
        if current_output_file:
            if Path(current_output_file).is_dir():
                is_intended_dir = True
            elif current_output_file.endswith(os.sep) or (os.altsep and current_output_file.endswith(os.altsep)):
                is_intended_dir = True

        if is_intended_dir:
            current_output_file = str(Path(current_output_file) / DEFAULT_OUTPUT_FILENAME)
            output_conf['file'] = current_output_file

        # Smart extension adjustment: if the output filename is the default filename,
        # adjust the extension to match the format. This works even if the file is
        # inside a folder specified via terminal options or configuration.
        if Path(current_output_file).name == DEFAULT_OUTPUT_FILENAME:
            if args.format == 'markdown':
                output_conf['file'] = str(Path(current_output_file).with_suffix('.md'))
            elif args.format == 'json':
                output_conf['file'] = str(Path(current_output_file).with_suffix('.json'))
            elif args.format == 'jsonl':
                output_conf['file'] = str(Path(current_output_file).with_suffix('.jsonl'))
            elif args.format == 'xml':
                output_conf['file'] = str(Path(current_output_file).with_suffix('.xml'))
            elif args.format == 'csv':
                output_conf['file'] = str(Path(current_output_file).with_suffix('.csv'))

        output_path = output_conf.get('file', DEFAULT_OUTPUT_FILENAME)

    # Determine output description before the main loop
    if args.clipboard:
        destination_desc = "to clipboard"
    elif output_path == '-':
        destination_desc = "to the terminal"
    elif mirror_enabled:
        destination_desc = f"to '{output_path}' (mirrored)"
    elif pairing_enabled:
        destination_desc = (
            "alongside their source files"
            if output_path is None
            else f"to '{output_path}'"
        )
    else:
        destination_desc = f"to '{output_path}'"

    if args.extract or args.verify:
        sources = []

        if args.clipboard:
            pyperclip = _get_pyperclip()
            if pyperclip:
                try:
                    sources.append(("clipboard", pyperclip.paste()))
                except Exception as e:
                    logging.error("Failed to paste from clipboard: %s", e)
                    sys.exit(1)
            else:
                logging.error("The 'pyperclip' tool is required for clipboard support. Install it with: pip install pyperclip")
                sys.exit(1)

        for target in remaining_targets:
            if target == "-":
                sources.append(("stdin", sys.stdin.read()))
            elif target.startswith(('http://', 'https://')):
                content, _ = utils.read_url_best_effort(target)
                if content:
                    sources.append((target, content))
            else:
                input_path = Path(target)
                if input_path.is_dir():
                    # Batch scan directory for potential combined files
                    paths, _, _ = collect_file_paths(input_path, recursive=True, exclude_folders=[])
                    for p in paths:
                        if not _looks_binary(p):
                            content, _ = read_file_best_effort(p)
                            if content:
                                sources.append((str(p), content))
                elif input_path.is_file():
                    content, _ = read_file_best_effort(input_path)
                    sources.append((str(input_path), content))
                else:
                    logging.warning("%s target not found: %s", "Verification" if args.verify else "Extraction", target)

        if not sources:
            # Fallback: look for the default combined file
            input_path = Path(output_path)
            if not input_path.is_file():
                # Try common format-specific defaults if the standard one doesn't exist
                for alt in ['combined_files.md', 'combined_files.json', 'combined_files.xml', 'combined_files.jsonl', 'combined_files.csv']:
                    if Path(alt).is_file():
                        input_path = Path(alt)
                        break

            if input_path.is_file():
                logging.info("No input specified. Using found file: %s", input_path)
                content, _ = read_file_best_effort(input_path)
                sources.append((str(input_path), content))
            else:
                logging.error("No input specified. Use a file path, folder, '-' for the terminal, or --clipboard.")
                sys.exit(1)

        if args.verify:
            verify_files(
                sources,
                root_folder=".",
                config=config,
                show_diff=config.get('output', {}).get('show_diff', False),
                repair=args.repair,
                dry_run=args.dry_run,
                strip_components=args.strip_components,
            )
            sys.exit(0)

        output_folder = args.output or "."
        stats = extract_files(
            sources,
            output_folder,
            dry_run=args.dry_run,
            config=config,
            list_files=args.list_files,
            tree_view=args.tree,
            limit=config.get('filters', {}).get('max_files', 0),
            estimate_tokens=args.estimate_tokens,
            sort_by=config.get('output', {}).get('sort_by', 'name'),
            sort_reverse=config.get('output', {}).get('sort_reverse', False),
            keep_line_numbers=args.keep_line_numbers,
            show_diff=config.get('output', {}).get('show_diff', False),
            strip_components=args.strip_components,
        )
        dest = f"to '{output_folder}'"
        if len(sources) == 1:
            source_desc = f"from '{sources[0][0]}'"
        else:
            source_desc = f"from {len(sources)} sources"

        duration = time.perf_counter() - start_time
        _print_execution_summary(stats, args, pairing_enabled=False, destination_desc=dest, duration=duration, source_desc=source_desc, mirror_enabled=mirror_enabled)

        summary_path = output_conf.get('summary_json')
        if summary_path and summary_path != '-' and '{{' in summary_path:
            summary_path = _render_global_template(summary_path, stats)

        _write_json_summary(stats, summary_path, duration=duration, source_desc=source_desc, destination_desc=dest)
        sys.exit(0)

    if mirror_enabled:
        action_desc = "Mirror"
    elif pairing_enabled:
        action_desc = "Pair"
    else:
        action_desc = "Combine"
    logging.info("%sOperation: %s%s", C_DIM, action_desc, C_RESET)

    if args.list_files:
        logging.info("%sOutput: Listing files only%s %s(no files will be written)%s", C_CYAN, C_RESET, C_DIM, C_RESET)
    elif args.tree:
        logging.info("%sOutput: Showing file tree%s %s(no files will be written)%s", C_CYAN, C_RESET, C_DIM, C_RESET)
    elif args.estimate_tokens:
        logging.info("%sOutput: Token estimation only%s %s(no files will be written)%s", C_CYAN, C_RESET, C_DIM, C_RESET)
    else:
        dry_run_indicator = f" {C_DIM}(dry run){C_RESET}" if args.dry_run else ""
        logging.info("%sOutput:%s %s%s%s%s", C_CYAN, C_RESET, C_BOLD, destination_desc, C_RESET, dry_run_indicator)

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
    except utils.InvalidConfigError as exc:
        if args.verbose:
            logging.error(exc, exc_info=True)
        else:
            logging.error(exc)
        sys.exit(1)

    if stats:
        # Determine source description
        actual_roots = config.get('search', {}).get('root_folders') or []
        if args.files_from:
            source_desc = "from file list"
        elif len(actual_roots) == 1:
            source_desc = f"from '{actual_roots[0]}'"
        elif len(actual_roots) > 1:
            source_desc = f"from {len(actual_roots)} targets"
        else:
            source_desc = ""

        duration = time.perf_counter() - start_time

        # Update destination description if output path was resolved
        resolved_path = stats.get('resolved_output_path')
        if resolved_path and resolved_path != '-' and not pairing_enabled:
            destination_desc = f"to '{resolved_path}'"

        _print_execution_summary(stats, args, pairing_enabled, destination_desc, duration=duration, source_desc=source_desc, mirror_enabled=mirror_enabled)

        summary_path = output_conf.get('summary_json')
        if summary_path and summary_path != '-' and '{{' in summary_path:
            summary_path = _render_global_template(summary_path, stats)

        _write_json_summary(stats, summary_path, duration=duration, source_desc=source_desc, destination_desc=destination_desc)


def _parse_combined_content(content, source_name="combined file"):
    """Identify and parse combined file content into a list of (path, content, meta) tuples."""
    if not content:
        return []

    files_found = []

    # 1. Try JSON
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and 'path' in entry:
                    meta = {
                        'tokens': _to_int_or_none(entry.get('tokens')),
                        'size': _to_int_or_none(entry.get('size_bytes')),
                        'lines': _to_int_or_none(entry.get('lines')),
                        'is_approx': entry.get('tokens_is_approx', False),
                        'modified': entry.get('modified'),
                        'sha256': entry.get('sha256'),
                        'language': entry.get('language'),
                    }
                    files_found.append((entry['path'], entry.get('content'), meta))
            if files_found:
                return files_found
    except json.JSONDecodeError:
        pass

    # 1.5 Try JSONL if JSON failed
    potential_files = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if isinstance(entry, dict) and 'path' in entry:
                meta = {
                    'tokens': _to_int_or_none(entry.get('tokens')),
                    'size': _to_int_or_none(entry.get('size_bytes')),
                    'lines': _to_int_or_none(entry.get('lines')),
                    'is_approx': entry.get('tokens_is_approx', False),
                    'modified': entry.get('modified'),
                    'sha256': entry.get('sha256'),
                    'language': entry.get('language'),
                }
                potential_files.append((entry['path'], entry.get('content'), meta))
            else:
                logging.debug("Skipping malformed JSONL line in %s: %s", source_name, line)
        except (json.JSONDecodeError, TypeError):
            pass

    if potential_files:
        return potential_files

    # 2. Try XML
    try:
        root = ET.fromstring(content)
        # Support both flat and nested <file> tags
        for file_node in root.iter('file'):
            try:
                path = file_node.get('path')
                file_content = file_node.text
                if path:
                    # XML extraction often has extra newlines due to templates
                    if file_content and file_content.startswith('\n') and file_content.endswith('\n'):
                        file_content = file_content[1:-1]

                    tokens_val = file_node.get('tokens')
                    size_val = file_node.get('size')
                    lines_val = file_node.get('lines')
                    mod_val = file_node.get('modified')
                    sha_val = file_node.get('sha256')
                    lang_val = file_node.get('language')

                    tokens = _to_int_or_none(tokens_val)
                    size = utils.parse_size_value(size_val) if size_val else None
                    is_approx = False
                    if tokens_val and str(tokens_val).strip().startswith('~'):
                        is_approx = True
                    if size_val and str(size_val).strip().startswith('~'):
                        is_approx = True

                    meta = {
                        'tokens': tokens,
                        'size': size,
                        'lines': _to_int_or_none(lines_val),
                        'is_approx': is_approx,
                        'modified': datetime.fromisoformat(mod_val).timestamp() if mod_val else None,
                        'sha256': sha_val,
                        'language': lang_val,
                    }
                    files_found.append((path, file_content, meta))
            except (ValueError, TypeError, Exception) as exc:
                logging.debug("Skipping malformed XML file entry: %s", exc)
                continue

        if files_found:
            return files_found
    except (ET.ParseError, ImportError):
        pass

    # 2.5 Try CSV
    if content.startswith("path,size_bytes,tokens,"):
        try:
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                if row.get("path"):
                    meta = {
                        'tokens': _to_int_or_none(row.get('tokens')),
                        'size': _to_int_or_none(row.get('size_bytes')),
                        'lines': _to_int_or_none(row.get('lines')),
                        'is_approx': row.get('tokens_is_approx') == 'True',
                        'modified': float(row['modified']) if row.get('modified') else None,
                        'sha256': row.get('sha256'),
                        'language': row.get('language'),
                    }
                    files_found.append((row['path'], row.get('content'), meta))
            if files_found:
                return files_found
        except (csv.Error, ValueError, KeyError):
            pass

    # 3. Try Text format (Default SourceCombine output)
    pattern = re.compile(r'^---\s+(.+?)\s+---\n([\s\S]*?)\n--- end \1 ---', re.MULTILINE)
    for match in pattern.finditer(content):
        path, file_content = match.groups()
        files_found.append((path.strip(), file_content, {}))
    if files_found:
        return files_found

    # 4. Try Markdown
    code_block_pattern = re.compile(r'^```(?:\S+)?\n([\s\S]*?)\n^```', re.MULTILINE)
    header_pattern = re.compile(r'^#{2,3}\s+(.+?)\s*$', re.MULTILINE)

    last_pos = 0
    for cb_match in code_block_pattern.finditer(content):
        search_space = content[last_pos:cb_match.start()]
        h_matches = list(header_pattern.finditer(search_space))
        if h_matches:
            path = h_matches[-1].group(1).strip()
            file_content = cb_match.group(1)
            files_found.append((path, file_content, {}))
        last_pos = cb_match.end()

    return files_found


def verify_files(sources, root_folder=".", config=None, show_diff=False, repair=False, dry_run=False, strip_components=0):
    """Verify that files on disk match the manifest or combined file."""
    root_folder = Path(root_folder)
    if config is None:
        config = copy.deepcopy(utils.DEFAULT_CONFIG)

    files_to_verify = []
    for name, content in sources:
        found = _parse_combined_content(content, source_name=name)
        if not found:
            logging.warning("No files found to verify in %s.", name)
        files_to_verify.extend(found)

    if not files_to_verify:
        logging.error("No files found to verify in any of the sources.")
        sys.exit(1)

    title = "Repair Report" if repair else "Verification Report"
    print(f"\n{C_BOLD}=== {title} ==={C_RESET}")

    matches = 0
    mismatches = 0
    missing = 0
    repaired = 0
    total = len(files_to_verify)

    for rel_path_str, expected_content, meta in files_to_verify:
        # Safety check: prevent path traversal (similar to extract_files)
        try:
            requested_path = Path(rel_path_str)

            if strip_components > 0:
                parts = requested_path.parts
                if len(parts) <= strip_components:
                    logging.warning("Skipping path with fewer than %d components: %s", strip_components, rel_path_str)
                    continue
                requested_path = Path(*parts[strip_components:])
            if requested_path.is_absolute() or PurePosixPath(rel_path_str).is_absolute() or PureWindowsPath(rel_path_str).is_absolute() or '..' in requested_path.parts or ':' in rel_path_str:
                logging.warning("Skipping unsafe path: %s", rel_path_str)
                continue
            target_path = (root_folder / requested_path).resolve()
        except (ValueError, OSError):
            logging.warning("Skipping invalid path: %s", rel_path_str)
            continue

        if not target_path.exists():
            if repair and expected_content is not None:
                if dry_run:
                    print(f"  {C_CYAN}[REPAIR]{C_RESET}  {rel_path_str} {C_DIM}(would create missing file){C_RESET}")
                    repaired += 1
                else:
                    try:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        target_path.write_text(expected_content, encoding='utf-8')
                        if meta.get('modified') is not None:
                            os.utime(target_path, (meta['modified'], meta['modified']))
                        print(f"  {C_GREEN}[REPAIRED]{C_RESET} {rel_path_str} {C_DIM}(created missing file){C_RESET}")
                        repaired += 1
                    except OSError as e:
                        print(f"  {C_RED}[ERROR]{C_RESET}    {rel_path_str} {C_DIM}(failed to repair: {e}){C_RESET}")
                        missing += 1
            else:
                print(f"  {C_RED}[MISSING]{C_RESET} {rel_path_str}")
                missing += 1
            continue

        # Priority 1: Check SHA-256 if available in metadata
        expected_sha = meta.get('sha256')
        if expected_sha:
            try:
                actual_sha = hashlib.sha256(target_path.read_bytes()).hexdigest()
                if actual_sha == expected_sha:
                    print(f"  {C_GREEN}[OK]{C_RESET}      {rel_path_str} {C_DIM}(hash match){C_RESET}")
                    matches += 1
                else:
                    if repair and expected_content is not None:
                        if dry_run:
                            print(f"  {C_CYAN}[REPAIR]{C_RESET}  {rel_path_str} {C_DIM}(would fix hash mismatch){C_RESET}")
                            repaired += 1
                        else:
                            try:
                                target_path.write_text(expected_content, encoding='utf-8')
                                if meta.get('modified') is not None:
                                    os.utime(target_path, (meta['modified'], meta['modified']))
                                print(f"  {C_GREEN}[REPAIRED]{C_RESET} {rel_path_str} {C_DIM}(fixed hash mismatch){C_RESET}")
                                repaired += 1
                            except OSError as e:
                                print(f"  {C_RED}[ERROR]{C_RESET}    {rel_path_str} {C_DIM}(failed to repair: {e}){C_RESET}")
                                mismatches += 1
                    else:
                        print(f"  {C_RED}[MISMATCH]{C_RESET} {rel_path_str} {C_DIM}(hash mismatch){C_RESET}")
                        mismatches += 1
                        if show_diff and expected_content is not None:
                            actual_content, _ = read_file_best_effort(target_path)
                            _print_diff(actual_content, expected_content, rel_path_str)
            except OSError as e:
                print(f"  {C_RED}[ERROR]{C_RESET}    {rel_path_str} {C_DIM}({e}){C_RESET}")
                mismatches += 1
            continue

        # Priority 2: Check content if available
        if expected_content is not None:
            actual_content, _ = read_file_best_effort(target_path)
            # Normalize line endings for content comparison to be robust across OS
            if actual_content.replace('\r\n', '\n') == expected_content.replace('\r\n', '\n'):
                print(f"  {C_GREEN}[OK]{C_RESET}      {rel_path_str} {C_DIM}(content match){C_RESET}")
                matches += 1
            else:
                if repair:
                    if dry_run:
                        print(f"  {C_CYAN}[REPAIR]{C_RESET}  {rel_path_str} {C_DIM}(would fix content mismatch){C_RESET}")
                        repaired += 1
                    else:
                        try:
                            target_path.write_text(expected_content, encoding='utf-8')
                            if meta.get('modified') is not None:
                                os.utime(target_path, (meta['modified'], meta['modified']))
                            print(f"  {C_GREEN}[REPAIRED]{C_RESET} {rel_path_str} {C_DIM}(fixed content mismatch){C_RESET}")
                            repaired += 1
                        except OSError as e:
                            print(f"  {C_RED}[ERROR]{C_RESET}    {rel_path_str} {C_DIM}(failed to repair: {e}){C_RESET}")
                            mismatches += 1
                else:
                    print(f"  {C_RED}[MISMATCH]{C_RESET} {rel_path_str} {C_DIM}(content mismatch){C_RESET}")
                    mismatches += 1
                    if show_diff:
                        _print_diff(actual_content, expected_content, rel_path_str)
            continue

        print(f"  {C_YELLOW}[SKIPPED]{C_RESET}  {rel_path_str} {C_DIM}(no hash or content to verify against){C_RESET}")

    print(f"\n{C_BOLD}Summary:{C_RESET}")
    print(f"  Matches:    {C_GREEN if matches == total else C_RESET}{matches}/{total}{C_RESET}")
    if repaired:
        print(f"  Repaired:   {C_GREEN}{repaired}{C_RESET}")
    if mismatches:
        print(f"  Mismatches: {C_RED}{mismatches}{C_RESET}")
    if missing:
        print(f"  Missing:    {C_RED}{missing}{C_RESET}")
    print(f"{C_BOLD}{'=' * 27}{C_RESET}\n")

    return {
        'matches': matches,
        'mismatches': mismatches,
        'missing': missing,
        'repaired': repaired,
        'total': total
    }


def _handle_invalid_config_error(exc, verbose, message=None):
    """Handle InvalidConfigError by logging it and exiting."""
    if verbose:
        logging.error(message or str(exc), exc_info=True)
    else:
        logging.error(message or str(exc))
    sys.exit(1)


def extract_files(sources, output_folder, dry_run=False, source_name="combined file", config=None, list_files=False, tree_view=False, limit=0, estimate_tokens=False, sort_by='name', sort_reverse=False, keep_line_numbers=False, show_diff=False, strip_components=0):
    """Recreate the original folder structure and files from combined content sources."""
    output_folder = Path(output_folder)

    if config is None:
        config = copy.deepcopy(utils.DEFAULT_CONFIG)

    stats = {
        'total_discovered': 0,
        'total_files': 0,
        'total_size_bytes': 0,
        'size_by_extension': {},
        'files_by_language': {},
        'size_by_language': {},
        'total_lines': 0,
        'total_tokens': 0,
        'tokens_by_extension': {},
        'lines_by_extension': {},
        'tokens_by_language': {},
        'lines_by_language': {},
        'custom_languages': config.get('search', {}).get('custom_languages', {}),
        'token_count_is_approx': False,
        'top_files': [],
        'files_by_extension': {},
        'max_files': limit,
        'max_total_tokens': config.get('filters', {}).get('max_total_tokens', 0),
        'max_total_size_bytes': config.get('filters', {}).get('max_total_size_bytes', 0),
        'max_total_lines': config.get('filters', {}).get('max_total_lines', 0),
        'filter_reasons': {},
    }

    # Handle backward compatibility for single source string/bytes
    if isinstance(sources, (str, bytes)):
        sources = [(source_name, sources)]

    if not sources:
        logging.error("No extraction sources provided.")
        sys.exit(1)

    files_to_create = []
    for name, content in sources:
        found = _parse_combined_content(content, source_name=name)
        if not found:
            logging.warning("Could not find any files to extract in %s.", name)
        files_to_create.extend(found)

    if not files_to_create:
        logging.error("Could not find any files to extract in any of the sources.")
        sys.exit(1)

    # Gather project metadata for templates
    _populate_project_stats(stats, output_folder, config)

    stats['total_discovered'] = len(files_to_create)
    filter_opts = config.get('filters', {})
    search_opts = config.get('search', {})

    filtered_files = []
    for path_str, file_content, meta in files_to_create:
        rel_path = PurePath(path_str)

        # Automatically remove line numbers unless requested otherwise
        if not keep_line_numbers:
            file_content = utils.remove_line_numbers(file_content)

        # Apply processing rules if any are configured
        processing_opts = config.get('processing', {})
        if processing_opts:
            lang = utils.get_language_tag(rel_path, content=file_content, overrides=config.get('search', {}).get('custom_languages'))
            processed_content = utils.process_content(file_content, processing_opts, language=lang)
            if processed_content != file_content:
                file_content = processed_content
                # Clear metrics metadata as it's no longer accurate for the processed content
                meta.pop('size', None)
                meta.pop('tokens', None)
                meta.pop('lines', None)
                meta.pop('is_approx', None)

        include, reason = should_include(
            None,
            rel_path,
            filter_opts,
            search_opts,
            return_reason=True,
            virtual_content=file_content,
        )

        if include:
            filtered_files.append((path_str, file_content, meta))
        else:
            if reason:
                stats['filter_reasons'][reason] = stats['filter_reasons'].get(reason, 0) + 1

    # Content-based deduplication for extraction
    if filter_opts.get('unique'):
        processor = FileProcessor(config, {}, dry_run=True)
        unique_files = []
        for path_str, file_content, meta in filtered_files:
            content_hash = processor.get_content_hash(file_content)
            if content_hash in processor.seen_hashes:
                logging.debug("Skipping duplicate content in extraction: %s", path_str)
                stats['filter_reasons']['duplicate_content'] = stats['filter_reasons'].get('duplicate_content', 0) + 1
                continue
            processor.seen_hashes.add(content_hash)
            unique_files.append((path_str, file_content, meta))
        filtered_files = unique_files

    # Initial metadata calculation needed for sorting and limits
    for path_str, file_content, meta in filtered_files:
        if meta.get('size') is None:
            meta['size'] = len(file_content.encode('utf-8'))
        if meta.get('lines') is None:
            meta['lines'] = utils.count_lines(file_content)

    # Token Estimation Pass (needed before global limits if sorting by tokens or requested)
    if estimate_tokens or sort_by == 'tokens' or stats['max_total_tokens'] > 0:
        needs_estimation = [f for f in filtered_files if f[2].get('tokens') is None]
        if needs_estimation:
            est_bar = _progress_bar(
                needs_estimation,
                desc="Estimating tokens",
                unit="file",
                enabled=_progress_enabled(False)
            )
            running_tokens = 0
            running_lines = 0
            running_size = 0
            for path_str, file_content, meta in est_bar:
                est_bar.set_description(f"Estimating {_truncate_path(path_str, 40)}")
                tokens, is_approx = utils.estimate_tokens(file_content)
                meta['tokens'] = tokens
                meta['is_approx'] = is_approx
                running_tokens += tokens
                running_lines += meta.get('lines', 0)
                running_size += (meta.get('size') or 0)
                est_bar.set_postfix(size=utils.format_size(running_size), lines=f"{running_lines:,}", tokens=f"{running_tokens:,}")
            est_bar.close()

    # Global Sort
    if sort_by != 'name' or sort_reverse:
        def get_extract_sort_key(item):
            path_str, file_content, meta = item
            if sort_by == 'size':
                val = meta['size']
            elif sort_by == 'tokens':
                val = meta.get('tokens', 0)
            elif sort_by == 'lines':
                val = meta.get('lines', 0)
            elif sort_by == 'modified':
                val = meta.get('modified', 0)
            elif sort_by == 'language':
                val = utils.get_language_tag(path_str, content=file_content, overrides=config.get('search', {}).get('custom_languages'))
            elif sort_by == 'depth':
                val = len(PurePath(path_str).parts)
            else:
                val = path_str
            return (val, path_str)

        filtered_files.sort(key=get_extract_sort_key, reverse=sort_reverse)

    if limit > 0 and len(filtered_files) > limit:
        stats['filter_reasons']['file_limit'] = len(filtered_files) - limit
        filtered_files = filtered_files[:limit]
        stats['limit_reached'] = True

    # Apply global limits (tokens, size, lines)
    max_total_tokens = stats['max_total_tokens']
    max_total_size = stats['max_total_size_bytes']
    max_total_lines = stats['max_total_lines']

    limited_files = []
    current_tokens = 0
    current_size = 0
    current_lines = 0

    for i, item in enumerate(filtered_files):
        path_str, file_content, meta = item

        file_tokens = (meta.get('tokens') or 0)
        file_size = meta['size']
        file_lines = meta['lines']

        if max_total_tokens > 0 and (current_tokens + file_tokens) > max_total_tokens and current_tokens > 0:
            stats['token_limit_reached'] = True
            stats['filter_reasons']['token_limit'] = len(filtered_files) - i
            break

        if max_total_size > 0 and (current_size + file_size) > max_total_size and current_size > 0:
            stats['size_limit_reached'] = True
            stats['filter_reasons']['size_limit'] = len(filtered_files) - i
            break

        if max_total_lines > 0 and (current_lines + file_lines) > max_total_lines and current_lines > 0:
            stats['line_limit_reached'] = True
            stats['filter_reasons']['line_limit'] = len(filtered_files) - i
            break

        current_tokens += file_tokens
        current_size += file_size
        current_lines += file_lines
        limited_files.append(item)

    filtered_files = limited_files

    # Final Stats Pass
    for path_str, file_content, meta in filtered_files:
        rel_path = PurePath(path_str)
        stats['total_files'] += 1
        ext = rel_path.suffix.lower() or '.no_extension'
        stats['files_by_extension'][ext] = stats['files_by_extension'].get(ext, 0) + 1

        stats['total_size_bytes'] += meta['size']
        stats['size_by_extension'][ext] = stats['size_by_extension'].get(ext, 0) + meta['size']

        tokens = meta.get('tokens') or 0
        lines = meta.get('lines') or 0
        _update_stats_metrics(stats, tokens, lines, meta.get('is_approx', False))
        if tokens:
            stats['tokens_by_extension'][ext] = stats['tokens_by_extension'].get(ext, 0) + tokens
        if lines:
            stats['lines_by_extension'][ext] = stats['lines_by_extension'].get(ext, 0) + lines

        lang = meta.get('language') or utils.get_language_tag(path_str, content=file_content, overrides=stats.get('custom_languages'))
        stats['top_files'].append((meta.get('tokens') or 0, meta['size'], path_str, meta.get('status'), lines, lang))

    files_to_create = filtered_files

    if list_files:
        for path_str, _, _ in files_to_create:
            print(path_str)
        return stats

    if tree_view:
        tree_paths = [Path(source_name) / p for p, _, _ in files_to_create]
        metadata_lookup = {
            Path(source_name) / p: {
                'size': m['size'],
                'tokens': m.get('tokens', 0),
                'lines': m['lines'],
                'language': utils.get_language_tag(p, content=c, overrides=config.get('search', {}).get('custom_languages'))
            }
            for p, c, m in files_to_create
        }
        print(_generate_tree_string(tree_paths, Path(source_name), include_header=False, metadata=metadata_lookup))
        return stats

    logging.info("Found %d files to extract from %s", len(files_to_create), source_name)

    extracted_count = 0

    extraction_bar = _progress_bar(
        files_to_create,
        desc="Extracting files",
        unit="file",
        enabled=_progress_enabled(dry_run)
    )

    running_size = 0
    running_lines = 0
    running_tokens = 0

    for rel_path_str, file_content, meta in extraction_bar:
        extraction_bar.set_description(f"Extracting {_truncate_path(rel_path_str, 40)}")
        # Security check: prevent path traversal and absolute paths across platforms.
        try:
            # We use joinpath and resolve to catch traversal and absolute path attempts.
            # Malformed paths such as 'C:../' or '/etc/passwd' are handled safely.
            requested_path = Path(rel_path_str)

            if strip_components > 0:
                parts = requested_path.parts
                if len(parts) <= strip_components:
                    logging.warning("Skipping path with fewer than %d components: %s", strip_components, rel_path_str)
                    continue
                requested_path = Path(*parts[strip_components:])
            
            # Absolute paths are always unsafe.
            if requested_path.is_absolute() or PurePosixPath(rel_path_str).is_absolute() or PureWindowsPath(rel_path_str).is_absolute():
                logging.warning("Skipping absolute path: %s", rel_path_str)
                continue

            # Check for '..' in parts across different path flavors to catch bypasses such as 'C:../'
            # We also check the raw string for ':' which is unsafe in relative paths.
            if ('..' in requested_path.parts or 
                '..' in PurePosixPath(rel_path_str.replace('\\', '/')).parts or
                '..' in PureWindowsPath(rel_path_str).parts or
                ':' in rel_path_str):
                logging.warning("Skipping potentially unsafe path: %s", rel_path_str)
                continue

            target_path = (output_folder / requested_path).resolve()
        except (ValueError, OSError):
            logging.warning("Skipping invalid path: %s", rel_path_str)
            continue

        if show_diff and target_path.exists():
            old_content, _ = read_file_best_effort(target_path)
            _print_diff(old_content, file_content, rel_path_str)

        if dry_run:
            logging.info("[DRY RUN] Would create: %s", target_path)
        else:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(file_content, encoding='utf-8')
                if meta.get('modified') is not None:
                    os.utime(target_path, (meta['modified'], meta['modified']))
                logging.info("Extracted: %s", target_path)
                extracted_count += 1
            except OSError as e:
                logging.error("Failed to write %s: %s", target_path, e)

            running_size += (_to_int_or_none(meta.get('size')) or 0)
            running_lines += (_to_int_or_none(meta.get('lines')) or 0)
            running_tokens += (_to_int_or_none(meta.get('tokens')) or 0)
            extraction_bar.set_postfix(size=utils.format_size(running_size), lines=f"{running_lines:,}", tokens=f"{running_tokens:,}")

    if not dry_run:
        logging.info("Extraction complete. %d files created in %s", extracted_count, output_folder)

    return stats


def restore_backups(targets, dry_run=False):
    """Scan targets recursively for .bak files and restore them."""
    if not targets:
        targets = ["."]

    restored_count = 0
    error_count = 0

    for target in targets:
        root_path = Path(target)
        if not root_path.exists():
            logging.warning("Target folder not found: %s", target)
            continue

        if root_path.is_file():
            # If a single file is targeted, check if it's a backup or has one
            backup_files = []
            if root_path.suffix == ".bak":
                backup_files = [root_path]
            elif Path(f"{root_path}.bak").is_file():
                backup_files = [Path(f"{root_path}.bak")]
        else:
            # Recursive scan for .bak files
            backup_files = sorted(root_path.rglob("*.bak"))

        if not backup_files:
            logging.info("No backup files (.bak) found in '%s'.", target)
            continue

        for backup_path in backup_files:
            original_path = backup_path.with_suffix("")
            rel_path = _get_rel_path(original_path, root_path)

            if dry_run:
                logging.info("[DRY RUN] Would restore: %s", rel_path)
                restored_count += 1
            else:
                try:
                    # Move the backup back to the original location, overwriting the processed file
                    shutil.move(backup_path, original_path)
                    logging.info("Restored: %s", rel_path)
                    restored_count += 1
                except OSError as e:
                    logging.error("Failed to restore %s: %s", rel_path, e)
                    error_count += 1

    if restored_count > 0 or error_count > 0:
        action = "Would restore" if dry_run else "Restored"
        logging.info("%s %d files. Errors: %d", action, restored_count, error_count)
    else:
        logging.info("No files were restored.")

    return restored_count, error_count


def delete_backups(targets, dry_run=False):
    """Scan targets recursively for .bak files and delete them."""
    if not targets:
        targets = ["."]

    deleted_count = 0
    error_count = 0

    for target in targets:
        root_path = Path(target)
        if not root_path.exists():
            logging.warning("Target folder not found: %s", target)
            continue

        if root_path.is_file():
            # If a single file is targeted, check if it's a backup
            backup_files = [root_path] if root_path.suffix == ".bak" else []
        else:
            # Recursive scan for .bak files
            backup_files = sorted(root_path.rglob("*.bak"))

        if not backup_files:
            logging.info("No backup files (.bak) found in '%s'.", target)
            continue

        for backup_path in backup_files:
            rel_path = _get_rel_path(backup_path, root_path)

            if dry_run:
                logging.info("[DRY RUN] Would delete: %s", rel_path)
                deleted_count += 1
            else:
                try:
                    os.remove(backup_path)
                    logging.info("Deleted backup: %s", rel_path)
                    deleted_count += 1
                except OSError as e:
                    logging.error("Failed to delete backup %s: %s", rel_path, e)
                    error_count += 1

    if deleted_count > 0 or error_count > 0:
        action = "Would delete" if dry_run else "Deleted"
        logging.info("%s %d backup files. Errors: %d", action, deleted_count, error_count)
    else:
        logging.info("No backup files were deleted.")

    return deleted_count, error_count


def print_system_info():
    """Print environment diagnostics and optional dependency status."""

    print(f"\n{C_BOLD}{C_CYAN}=== SYSTEM INFORMATION ==={C_RESET}")
    print(f"  {C_BOLD}SourceCombine Version:{C_RESET} {__version__}")
    print(f"  {C_BOLD}Python Version:{C_RESET}      {sys.version.split()[0]}")
    print(f"  {C_BOLD}Platform:{C_RESET}            {platform.platform()}")
    print(f"  {C_BOLD}Executable:{C_RESET}          {sys.executable}")
    print(f"  {C_BOLD}Current Folder:{C_RESET}      {Path.cwd()}")

    config_file = Path("sourcecombine.yml")
    config_status = "Found" if config_file.exists() else "Not found"
    print(f"  {C_BOLD}Local Config:{C_RESET}        {config_status} ({config_file.resolve() if config_file.exists() else 'N/A'})")

    print(f"\n  {C_BOLD}Optional Dependencies:{C_RESET}")

    deps = [
        ("tiktoken", "Accurate token counting"),
        ("pyperclip", "Clipboard support"),
        ("tqdm", "Progress bars"),
        ("yaml", "Configuration support (PyYAML)"),
        ("charset_normalizer", "Encoding detection"),
    ]

    for dep_name, purpose in deps:
        spec = importlib.util.find_spec(dep_name)
        status = f"{C_GREEN}Installed{C_RESET}" if spec else f"{C_YELLOW}Not found{C_RESET}"
        print(f"    {C_BOLD}{dep_name:<20}{C_RESET} {status:<20} {C_DIM}({purpose}){C_RESET}")

    print(f"\n{C_BOLD}{'=' * 40}{C_RESET}\n")


def print_placeholders():
    """Print all supported template placeholders and their descriptions."""
    print(f"\n{C_BOLD}{C_CYAN}=== TEMPLATE PLACEHOLDERS ==={C_RESET}")

    categories = {
        "File-Level Placeholders": [
            ("{{FILENAME}}", "Full relative path to the file."),
            ("{{EXT}}", "File extension (for example, 'py')."),
            ("{{STEM}}", "Filename without extension (for example, 'main')."),
            ("{{DIR}}", "Folder path containing the file."),
            ("{{DIR_SLUG}}", "A version of the folder path safe for use in filenames."),
            ("{{LANG}}", "Detected language tag (for example, 'python', 'cpp')."),
            ("{{SIZE}}", "Human-readable file size."),
            ("{{TOKENS}}", "Number of tokens in the file."),
            ("{{LINE_COUNT}}", "Number of lines in the file."),
            ("{{MODIFIED}}", "Last modified date and time."),
            ("{{HASH}}", "SHA-256 hash of the file content."),
            ("{{INDEX}}", "The current file's position in the list (1, 2, 3...)."),
            ("{{TOTAL}}", "The total number of files being processed."),
            ("{{SIZE_PERCENT}}", "Percentage of the total project size."),
            ("{{TOKEN_PERCENT}}", "Percentage of the total project tokens."),
            ("{{LINE_PERCENT}}", "Percentage of the total project lines."),
        ],
        "Project Information (Global) Placeholders": [
            ("{{PROJECT_NAME}}", "Name of the project."),
            ("{{PROJECT_VERSION}}", "Version of the project."),
            ("{{PROJECT_DESCRIPTION}}", "Short description of the project."),
            ("{{PROJECT_LICENSE}}", "License identifier of the project."),
            ("{{FILE_COUNT}}", "Total number of files included."),
            ("{{TOTAL_SIZE}}", "Total size of all files."),
            ("{{TOTAL_TOKENS}}", "Total number of tokens."),
            ("{{TOTAL_LINES}}", "Total number of lines."),
            ("{{DATE}}", "Current date (YYYY-MM-DD)."),
            ("{{TIME}}", "Current time (HH:MM:SS)."),
            ("{{DATETIME}}", "Current date and time."),
        ],
        "Git Placeholders": [
            ("{{GIT_BRANCH}}", "Current branch name."),
            ("{{GIT_COMMIT}}", "Full commit hash."),
            ("{{GIT_COMMIT_SHORT}}", "Short commit hash (7 characters)."),
            ("{{GIT_AUTHOR}}", "Author of the latest commit."),
            ("{{GIT_AUTHOR_DATE}}", "Date of the latest commit."),
            ("{{GIT_TAG}}", "Latest Git tag."),
            ("{{GIT_STATUS}}", "Summary of project changes."),
            ("{{GIT_LOG}}", "Recent commit messages."),
            ("{{GIT_DIFF}}", "Project-wide changes."),
            ("{{FILE_DIFF}}", "Changes specific to the current file (File-level only)."),
            ("{{GIT_REMOTE_URL}}", "The repository's origin remote URL."),
            ("{{PROJECT_URL}}", "Web URL to the repository home."),
            ("{{FILE_URL}}", "Direct web link to the specific file and commit (File-level only)."),
            ("{{FILE_AUTHOR}}", "Last author of the file (File-level only)."),
            ("{{FILE_AUTHOR_DATE}}", "Last commit date of the file (File-level only)."),
            ("{{FILE_LOG}}", "Subject of the last commit for the file (File-level only)."),
            ("{{FILE_STATUS}}", "Git status of the file (for example, 'M', 'A', '??') (File-level only)."),
        ],
        "System & Environment Placeholders": [
            ("{{OS}}", "Operating system name."),
            ("{{PYTHON_VERSION}}", "Python version."),
            ("{{PLATFORM}}", "Detailed platform information."),
            ("{{ARCH}}", "CPU architecture."),
            ("{{ENV:VAR_NAME}}", "Value of an environment variable."),
        ],
        "Pairing-Specific Placeholders": [
            ("{{STEM}}", "Base filename shared by the pair."),
            ("{{SOURCE_EXT}}", "Extension of the source file (for example, '.cpp')."),
            ("{{HEADER_EXT}}", "Extension of the header file (for example, '.h')."),
            ("{{DIR}}", "Folder path containing the pair."),
            ("{{DIR_SLUG}}", "A version of the folder path safe for use in filenames."),
            ("{{LANG}}", "Detected language of the pair."),
            ("{{INDEX}}", "The current pair's position in the list."),
            ("{{TOTAL}}", "The total number of pairs being processed."),
            ("Note:", "All project, system, and Git placeholders are also supported."),
        ]
    }

    placeholder_width = 25

    for category, placeholders in categories.items():
        print(f"\n  {C_BOLD}{category}{C_RESET}")
        for placeholder, description in placeholders:
            print(f"    {C_BOLD}{C_CYAN}{placeholder:<{placeholder_width}}{C_RESET} {C_DIM}{description}{C_RESET}")

    print(f"\n{C_BOLD}{'=' * 40}{C_RESET}\n")


def print_project_info(stats):
    """Print detected project information and Git status."""
    print(f"\n{C_BOLD}{C_CYAN}=== PROJECT INFORMATION ==={C_RESET}")

    categories = {
        "Project Information": [
            ("Name", stats.get('project_name')),
            ("Version", stats.get('project_version')),
            ("Description", stats.get('project_description')),
            ("License", stats.get('project_license')),
            ("URL", stats.get('project_url')),
            ("Manifest", stats.get('manifest_source')),
        ],
        "Git Information": [
            ("Branch", stats.get('git_branch')),
            ("Commit", stats.get('git_commit')),
            ("Short Commit", stats.get('git_commit_short')),
            ("Author", stats.get('git_author')),
            ("Date", stats.get('git_author_date')),
            ("Tag", stats.get('git_tag')),
            ("Remote URL", stats.get('git_remote_url')),
            ("Repo Root", stats.get('git_repo_root')),
            ("Status", stats.get('git_status')),
        ],
        "System & Environment": [
            ("OS", stats.get('os')),
            ("Python", stats.get('python_version')),
            ("Platform", stats.get('platform')),
            ("Architecture", stats.get('arch')),
        ]
    }

    label_width = 15

    for category, fields in categories.items():
        print(f"\n  {C_BOLD}{category}{C_RESET}")
        for label, value in fields:
            display_value = str(value) if value is not None else "N/A"
            if "\n" in display_value:
                lines = display_value.splitlines()
                print(f"    {C_BOLD}{label:<{label_width}}{C_RESET} {C_DIM}{lines[0]}{C_RESET}")
                for line in lines[1:]:
                    print(f"    {' ':<{label_width}} {C_DIM}{line}{C_RESET}")
            else:
                print(f"    {C_BOLD}{label:<{label_width}}{C_RESET} {C_DIM}{display_value}{C_RESET}")

    print(f"\n{C_BOLD}{'=' * 40}{C_RESET}\n")


def _print_limit_usage_bar(label, current, maximum, label_width, is_size=False):
    """Print an ASCII progress bar for limit usage."""
    if maximum <= 0:
        return
    percent = (current / maximum) * 100
    # Create a 10-character ASCII bar
    bar = f"[{_make_ascii_bar(percent, use_rounding=False, ensure_min_one=False)}]"
    if percent >= 100:
        bar_color = C_RED
    elif percent > 90:
        bar_color = C_YELLOW
    else:
        bar_color = C_GREEN

    if is_size:
        detail = f"({utils.format_size(current)} • {utils.format_size(maximum)})"
    else:
        detail = f"({current:,} • {maximum:,})"

    print(f"    {C_BOLD}{label:<{label_width}}{C_RESET}{bar_color}{bar}{C_RESET} {C_DIM}{percent:>6.1f}%{C_RESET} {C_DIM}{detail}{C_RESET}", file=sys.stderr)


def _print_execution_summary(stats, args, pairing_enabled, destination_desc=None, duration=None, source_desc=None, mirror_enabled=False):
    """Print a summary of the totals to the terminal."""

    def _split_unit(s):
        """Split a string such as '1.50 MB' or '1,000 tokens' into (value, unit)."""
        parts = s.split(' ', 1)
        return (parts[0], f" {parts[1]}") if len(parts) == 2 else (s, "")

    def _get_metric_style(metric_name, primary_metric):
        return f"{C_BOLD}{C_CYAN}" if metric_name == primary_metric else C_DIM

    def _format_header(label, metric_name, primary_metric, width=12):
        h = f"{label:>{width}}"
        return f"{C_BOLD}{h}{C_RESET}{C_DIM}" if metric_name == primary_metric else h

    def _get_primary_metric(t, l):
        return 'tokens' if t else ('lines' if l else 'size')

    # Determine available width for layout and truncation
    term_width = 80
    try:
        term_width = shutil.get_terminal_size((80, 20)).columns
    except Exception:
        pass

    total_included = stats.get('total_files', 0)
    total_discovered = stats.get('total_discovered', 0)
    total_filtered = max(0, total_discovered - total_included)
    excluded_folders = stats.get('excluded_folder_count', 0)

    total_size_bytes = stats.get('total_size_bytes', 0)
    total_size_str = utils.format_size(total_size_bytes)
    token_count = stats.get('total_tokens', 0)
    total_lines = stats.get('total_lines', 0)
    is_approx = stats.get('token_count_is_approx', False)

    parts = []
    if token_count > 0:
        token_word = _plural(token_count, "token")
        parts.append(f"{C_BOLD}{C_CYAN}{'~' if is_approx else ''}{token_count:,}{C_RESET} {C_DIM}{token_word}{C_RESET}")
    if total_lines > 0:
        line_word = _plural(total_lines, "line")
        parts.append(f"{C_BOLD}{C_CYAN}{total_lines:,}{C_RESET} {C_DIM}{line_word}{C_RESET}")
    val, unit = _split_unit(total_size_str)
    parts.append(f"{C_BOLD}{C_CYAN}{val}{C_RESET}{C_DIM}{unit}{C_RESET}")

    # Add format to data hint if applicable
    if getattr(args, 'extract', False) is not True and not (getattr(args, 'list_files', False) is True or getattr(args, 'tree', False) is True):
        fmt_name = (getattr(args, 'format', None) or stats.get('output_format', 'text')).upper()
        parts.append(f"{C_BOLD}{C_CYAN}{fmt_name}{C_RESET}")

    data_hint = f"{C_DIM} • {C_RESET}".join(parts)

    limit_reached = any(stats.get(k) for k, _ in TRUNCATION_CHECKS)

    if args.dry_run or total_included == 0 or limit_reached:
        title_color = C_YELLOW
    elif args.estimate_tokens or args.list_files or args.tree:
        title_color = C_CYAN
    else:
        title_color = C_GREEN

    # Build project context (Name + Git info)
    project_name = stats.get('project_name', 'Project')
    git_branch = stats.get('git_branch')
    git_commit = stats.get('git_commit_short')

    # Shorten components if they are extremely long to prevent wrapping
    # We use more generous limits now as we will fall back to multi-line layout
    if term_width <= 80:
        proj_limit = 40
        branch_limit = 30
        desc_limit = 60
    else:
        proj_limit = 80
        branch_limit = 60
        desc_limit = 120

    if len(project_name) > proj_limit:
        project_name = project_name[:proj_limit-3] + "..."
    
    if git_branch and len(git_branch) > branch_limit:
        git_branch = git_branch[:branch_limit-3] + "..."

    project_version = stats.get('project_version')
    project_license = stats.get('project_license')

    project_ctx = project_name
    if project_version:
        project_ctx += f" v{project_version}"
    if project_license:
        project_ctx += f" [{project_license}]"

    if git_branch and git_branch != 'N/A':
        if git_commit and git_commit != 'N/A':
            project_ctx = f"{project_ctx} ({git_branch}:{git_commit})"
        else:
            project_ctx = f"{project_ctx} ({git_branch})"

    # Shorten descriptions if they are too long
    if source_desc and len(source_desc) > desc_limit:
        if source_desc.startswith("from '") and source_desc.endswith("'"):
            source_desc = f"from '{_truncate_path(source_desc[6:-1], desc_limit - 7)}'"
        else:
            source_desc = _truncate_path(source_desc, desc_limit)

    if destination_desc and len(destination_desc) > desc_limit:
        if destination_desc.startswith("to '") and destination_desc.endswith("' (mirrored)"):
            destination_desc = f"to '{_truncate_path(destination_desc[4:-12], desc_limit - 16)}' (mirrored)"
        elif destination_desc.startswith("to '") and destination_desc.endswith("'"):
            destination_desc = f"to '{_truncate_path(destination_desc[4:-1], desc_limit - 5)}'"
        else:
            destination_desc = _truncate_path(destination_desc, desc_limit)

    # Highlight destination in the summary title
    highlighted_dest = f"{C_CYAN}{destination_desc}{title_color}" if destination_desc else ""

    file_word = _plural(total_included, "file")

    # Determine base action for status title
    if getattr(args, 'extract', False) is True:
        base_action = "EXTRACTION"
        verb = "extract"
        action = "Extracted"
    elif getattr(args, 'apply_in_place', False) is True:
        base_action = "UPDATE"
        verb = "update in-place"
        action = "Updated in-place"
    elif mirror_enabled:
        base_action = "MIRROR"
        verb = "mirror"
        action = "Mirrored"
    elif pairing_enabled:
        base_action = "PAIRING"
        verb = "pair"
        action = "Paired"
    else:
        base_action = "COMBINE"
        verb = "combine"
        action = "Combined"

    # Refine status prefix with base action
    if total_included == 0:
        status_prefix = f"NO FILES FOUND ({base_action})"
    elif getattr(args, 'dry_run', False) is True:
        status_prefix = f"{base_action} PREVIEW"
    elif getattr(args, 'estimate_tokens', False) is True:
        status_prefix = f"{base_action} ESTIMATION"
    elif getattr(args, 'list_files', False) is True:
        status_prefix = f"{base_action} LISTING"
    elif getattr(args, 'tree', False) is True:
        status_prefix = f"{base_action} TREE VIEW"
    else:
        status_prefix = f"{base_action} SUCCESS"

    if limit_reached:
        status_prefix = f"{status_prefix} (SHORTENED)"

    # Header part
    header_main = f"{status_prefix}: [{project_ctx}]"
    
    # Details part
    if getattr(args, 'dry_run', False) is True:
        verb_phrase = f"Would {verb} {total_included:,} {file_word}"
    elif getattr(args, 'estimate_tokens', False) is True or getattr(args, 'list_files', False) is True or getattr(args, 'tree', False) is True:
        verb_phrase = f"{total_included:,} {file_word}"
    else:
        verb_phrase = f"{action} {total_included:,} {file_word}"

    # We use _ANSI_ESCAPE to correctly calculate the visible length for the border
    raw_header_main = _ANSI_ESCAPE.sub('', header_main)
    raw_data_hint = _ANSI_ESCAPE.sub('', data_hint)

    # 4 (=== ) + 2 ( [) + 1 (]) + 4 ( ===) = 11 overhead
    if len(raw_header_main) + len(raw_data_hint) + 11 <= term_width:
        # Fits in one line
        header_text = f"{header_main} {C_RESET}{C_DIM}[{C_RESET}{data_hint}{C_DIM}]{C_RESET}"
        raw_title_len = len(raw_header_main) + len(raw_data_hint) + 11
        print(f"\n{title_color}{C_BOLD}=== {header_text}{title_color}{C_BOLD} ==={C_RESET}", file=sys.stderr)
    else:
        # Top border with status and project
        border_len = min(term_width, len(raw_header_main) + 8)
        border_len = max(border_len, 40)
        
        main_part = f"=== {header_main} "
        filler_len = max(0, border_len - len(_ANSI_ESCAPE.sub('', main_part)))
        print(f"\n{title_color}{C_BOLD}{main_part}{'=' * filler_len}{C_RESET}", file=sys.stderr)
        
        # Show data hint on its own line if it didn't fit in header
        print(f"  {C_DIM}[{C_RESET}{data_hint}{C_DIM}]{C_RESET}", file=sys.stderr)
        raw_title_len = border_len

    # Detail lines
    print(f"  {C_BOLD}{verb_phrase}{C_RESET}", file=sys.stderr)
    if source_desc:
        print(f"  {C_DIM}{source_desc}{C_RESET}", file=sys.stderr)
    if highlighted_dest:
        print(f"  {C_DIM}{highlighted_dest}{C_RESET}", file=sys.stderr)
    
    truncations = [label for key, label in TRUNCATION_CHECKS if stats.get(key)]
    if truncations:
        notice = "WARNING: Output shortened due to: " + ", ".join(truncations)
        print(f"  {C_YELLOW}{C_BOLD}{notice}{C_RESET}", file=sys.stderr)

    # Files Section
    label_width = 24
    print(f"  {C_BOLD}{C_CYAN}Files{C_RESET}", file=sys.stderr)

    has_skipped_files = total_filtered > 0
    has_skipped_folders = excluded_folders > 0
    has_any_skips = has_skipped_files or has_skipped_folders

    found_label_style = C_DIM if not has_any_skips else C_BOLD
    found_value_style = C_DIM if not has_any_skips else f"{C_BOLD}{C_CYAN}"
 
    found_unit = f" {_plural(total_discovered, 'file')}"
    print(f"    {found_label_style}{'Total Found:':<{label_width}}{C_RESET}{found_value_style}{total_discovered:12,}{C_RESET}{C_DIM}{found_unit:<8}{C_RESET}", file=sys.stderr)

    if has_any_skips:
        included_percent = (total_included / total_discovered * 100) if total_discovered > 0 else 0
        skipped_percent = (total_filtered / total_discovered * 100) if total_discovered > 0 else 0

        # Files tree branches
        included_unit = f" {_plural(total_included, 'file')}"
        print(f"    {C_DIM}├── {C_RESET}{C_BOLD}{'Included:':<{label_width - 4}}{C_RESET}{C_BOLD}{C_GREEN}{total_included:12,}{C_RESET}{C_DIM}{included_unit:<8}{C_RESET} {C_DIM}({C_RESET}{C_BOLD}{C_CYAN}{included_percent:>6.1f}{C_RESET}{C_DIM}%){C_RESET}", file=sys.stderr)

        if has_skipped_files:
            skipped_connector = "├── " if has_skipped_folders else "└── "
            skipped_unit = f" {_plural(total_filtered, 'file')}"
            print(f"    {C_DIM}{skipped_connector}{C_RESET}{C_BOLD}{'Skipped:':<{label_width - 4}}{C_RESET}{C_BOLD}{C_YELLOW}{total_filtered:12,}{C_RESET}{C_DIM}{skipped_unit:<8}{C_RESET} {C_DIM}({C_RESET}{C_BOLD}{C_CYAN}{skipped_percent:>6.1f}{C_RESET}{C_DIM}%){C_RESET}", file=sys.stderr)

            # Detailed breakdown of filtering reasons
            relevant_reasons = [(r, c) for r, c in stats.get('filter_reasons', {}).items() if r != 'excluded_folder' and c > 0]
            if relevant_reasons:
                sorted_reasons = sorted(relevant_reasons, key=lambda x: (-x[1], x[0]))
                outer_skipped_indent = "│   " if has_skipped_folders else "    "

                for i, (reason, count) in enumerate(sorted_reasons):
                    is_last = i == len(sorted_reasons) - 1
                    connector = "└── " if is_last else "├── "
                    display_reason = (reason.replace('_', ' ').capitalize() + ":")
                    reason_percent = (count / total_filtered * 100) if total_filtered > 0 else 0
                    reason_unit = f" {_plural(count, 'file')}"
                    print(f"    {C_DIM}{outer_skipped_indent}{connector}{C_RESET}{C_BOLD}{display_reason:<{label_width - 8}}{C_RESET}{C_BOLD}{C_CYAN}{count:12,}{C_RESET}{C_DIM}{reason_unit:<8}{C_RESET} {C_DIM}({C_RESET}{C_BOLD}{C_CYAN}{reason_percent:>6.1f}{C_RESET}{C_DIM}%){C_RESET}", file=sys.stderr)

        if has_skipped_folders:
            folder_unit = f" {_plural(excluded_folders, 'folder')}"
            print(f"    {C_DIM}└── {C_RESET}{C_BOLD}{'Skipped Folders:':<{label_width - 4}}{C_RESET}{C_BOLD}{C_CYAN}{excluded_folders:12,}{C_RESET}{C_DIM}{folder_unit:<8}{C_RESET}", file=sys.stderr)

    # Performance Section
    # Check if any limits were active
    has_limits = any(stats.get(k, 0) > 0 for k in ('max_total_tokens', 'max_total_size_bytes', 'max_total_lines', 'max_files'))

    if duration is not None or has_limits or total_included > 0:
        section_name = "Performance & Limits" if has_limits else "Performance"
        print(f"\n  {C_BOLD}{C_CYAN}{section_name}{C_RESET}", file=sys.stderr)

        bps = total_size_bytes / duration if duration and duration > 0 else 0
        tps = token_count / duration if duration and duration > 0 else 0
        lps = total_lines / duration if duration and duration > 0 else 0

        val, unit = _split_unit(total_size_str)
        size_throughput = ""
        if bps > 0:
            s_val, s_unit = _split_unit(utils.format_size(bps))
            size_throughput = f" {C_DIM}({C_RESET}{C_BOLD}{C_CYAN}{s_val:>12}{C_RESET} {C_DIM}{s_unit.strip() + '/s':<10}){C_RESET}"
        print(f"    {C_BOLD}{'Total Size:':<{label_width}}{C_RESET}{C_BOLD}{C_CYAN}{val:>12}{C_RESET}{C_DIM}{unit:<8}{C_RESET}{size_throughput}", file=sys.stderr)

        if total_lines > 0:
            lines_throughput = ""
            if lps > 0:
                lines_throughput = f" {C_DIM}({C_RESET}{C_BOLD}{C_CYAN}{lps:>12,.0f}{C_RESET} {C_DIM}{'lines/s':<10}){C_RESET}"
            unit_label = f" {line_word}"
            print(f"    {C_BOLD}{'Total Lines:':<{label_width}}{C_RESET}{C_BOLD}{C_CYAN}{total_lines:12,}{C_RESET}{C_DIM}{unit_label:<8}{C_RESET}{lines_throughput}", file=sys.stderr)

        # Token Counts
        # Show token counts if tokens were estimated
        if token_count > 0:
            token_str = format_tokens(token_count, is_approx)
            token_word = _plural(token_count, "token")
            tokens_throughput = ""
            if tps > 0:
                tokens_throughput = f" {C_DIM}({C_RESET}{C_BOLD}{C_CYAN}{tps:>12,.0f}{C_RESET} {C_DIM}{'tokens/s':<10}){C_RESET}"
            unit_label = f" {token_word}"
            print(
                f"    {C_BOLD}{'Total Tokens:':<{label_width}}{C_RESET}{C_BOLD}{C_CYAN}{token_str:>12}{C_RESET}{C_DIM}{unit_label:<8}{C_RESET}{tokens_throughput}",
                file=sys.stderr,
            )
            if is_approx:
                print(
                    f"      {C_DIM}(Install 'tiktoken' for accurate counts){C_RESET}",
                    file=sys.stderr,
                )

        if duration is not None:
            fps = total_discovered / duration if duration > 0 else 0
            print(f"    {C_BOLD}{'Duration:':<{label_width}}{C_RESET}{C_BOLD}{C_CYAN}{duration:12.2f}{C_RESET}{C_DIM}{' s':<8}{C_RESET} {C_DIM}({C_RESET}{C_BOLD}{C_CYAN}{fps:>12,.1f}{C_RESET} {C_DIM}{'files/s':<10}){C_RESET}", file=sys.stderr)

        _print_limit_usage_bar('File Limit Usage:', total_included, stats.get('max_files', 0), label_width)
        _print_limit_usage_bar('Token Limit Usage:', token_count, stats.get('max_total_tokens', 0), label_width)
        _print_limit_usage_bar('Size Limit Usage:', total_size_bytes, stats.get('max_total_size_bytes', 0), label_width, is_size=True)
        _print_limit_usage_bar('Line Limit Usage:', total_lines, stats.get('max_total_lines', 0), label_width)

    # Determine column visibility based on terminal width to prevent wrapping
    # We prioritize: Primary Metric > Percentage > Path > Language > Status > Distribution > Secondary Metrics
    show_secondary = term_width >= 100
    show_dist = term_width >= 80
    show_status_col = term_width >= 60
    show_lang_col = term_width >= 70

    # Only show STATUS column if at least one displayed file has a status
    any_has_status = any(len(f) > 3 and f[3] for f in stats.get('top_files', [])) if stats.get('top_files') else False
    any_has_status = any_has_status and show_status_col

    # Largest Files
    if stats.get('top_files'):
        top, title, total_for_percent, has_tokens, has_lines = _get_summary_top_items(
            stats, stats['top_files'], is_folder=False
        )
        primary_metric = _get_primary_metric(has_tokens, has_lines)

        # Calculate dynamic overhead for path width
        # Indentation (4) + Primary (13) + % (7)
        overhead = 4 + 13 + 7
        # Secondary Metrics (13 each)
        if show_secondary:
            if has_tokens and primary_metric != 'tokens': overhead += 13
            if has_lines and primary_metric != 'lines': overhead += 13
            if primary_metric != 'size': overhead += 13
        # Distribution (13)
        if show_dist: overhead += 13
        # Spacer for aggregate FILES (%) column (16)
        overhead += 16
        # Status (7)
        if any_has_status: overhead += 7
        # Language (12)
        if show_lang_col: overhead += 12

        path_width = max(20, term_width - overhead)

        # Build dynamic header
        header_parts = []
        # Secondary metrics first
        if show_secondary:
            if has_tokens and primary_metric != 'tokens':
                header_parts.append(_format_header('TOKENS', 'tokens', primary_metric))
            if has_lines and primary_metric != 'lines':
                header_parts.append(_format_header('LINES', 'lines', primary_metric))
            if primary_metric != 'size':
                header_parts.append(_format_header('SIZE', 'size', primary_metric))

        # Primary metric last before %
        if has_tokens and primary_metric == 'tokens':
            header_parts.append(_format_header('TOKENS', 'tokens', primary_metric))
        elif has_lines and primary_metric == 'lines':
            header_parts.append(_format_header('LINES', 'lines', primary_metric))
        elif primary_metric == 'size':
            header_parts.append(_format_header('SIZE', 'size', primary_metric))

        header_parts.append(f"{'%':>6}")
        if show_dist: header_parts.append(f"{'DISTRIBUTION':<12}")

        # Empty space to match Files (%) column in other tables
        header_parts.append(f"{' ': <15}")

        if any_has_status: header_parts.append(f"{'STATUS':<6}")
        if show_lang_col: header_parts.append(f"{'LANGUAGE':<11}")
        header_parts.append("PATH")

        print(f"\n  {C_BOLD}{C_CYAN}{title}{C_RESET}", file=sys.stderr)
        print(f"    {C_DIM}{' '.join(header_parts)}{C_RESET}", file=sys.stderr)

        for item in top:
            tokens, f_size, path = item[:3]
            status = item[3] if len(item) > 3 else None
            f_lines = item[4] if len(item) > 4 else 0
            lang = item[5] if len(item) > 5 else ""
            val_num = tokens if has_tokens else (f_lines if has_lines else f_size)
            percent = 0.0
            if total_for_percent > 0:
                percent = (val_num / total_for_percent) * 100

            # 10-character ASCII distribution bar
            bar = _make_ascii_bar(percent, colored=True)

            size_str = utils.format_size(f_size)
            s_val, s_unit = _split_unit(size_str)
            # Use smart middle-truncation for paths
            display_path = _truncate_path(path, path_width)

            # Align values while keeping units dimmed
            size_padding = " " * max(0, 12 - len(s_val) - len(s_unit))

            row_parts = []
            # Secondary metrics first
            if show_secondary:
                if has_tokens and primary_metric != 'tokens':
                    token_str = format_tokens(tokens, is_approx)
                    row_parts.append(f"{C_DIM}{token_str:>12}{C_RESET}")
                if has_lines and primary_metric != 'lines':
                    row_parts.append(f"{C_DIM}{f_lines:12,}{C_RESET}")
                if primary_metric != 'size':
                    row_parts.append(f"{size_padding}{C_DIM}{s_val}{C_RESET}{C_DIM}{s_unit}{C_RESET}")

            # Primary metric last
            if has_tokens and primary_metric == 'tokens':
                token_str = format_tokens(tokens, is_approx)
                row_parts.append(f"{C_BOLD}{C_CYAN}{token_str:>12}{C_RESET}")
            elif has_lines and primary_metric == 'lines':
                row_parts.append(f"{C_BOLD}{C_CYAN}{f_lines:12,}{C_RESET}")
            elif primary_metric == 'size':
                row_parts.append(f"{size_padding}{C_BOLD}{C_CYAN}{s_val}{C_RESET}{C_DIM}{s_unit}{C_RESET}")

            row_parts.append(f"{C_BOLD}{C_CYAN}{percent:>5.1f}{C_RESET}{C_DIM}%{C_RESET}")

            if show_dist:
                row_parts.append(f"{C_DIM}[{C_RESET}{bar}{C_DIM}]{C_RESET}")

            # Empty space for Files (%) alignment
            row_parts.append(" " * 15)

            if any_has_status:
                if status:
                    label = f"[{status}]"
                    visible_len = len(label)
                    if status in ('A', '??'):
                        status_text = f"{C_GREEN}{label}{C_RESET}"
                    elif status in ('M', 'R'):
                        status_text = f"{C_YELLOW}{label}{C_RESET}"
                    elif status == 'D':
                        status_text = f"{C_RED}{label}{C_RESET}"
                    else:
                        status_text = label
                    row_parts.append(f"{status_text}{' ' * (6 - visible_len)}")
                else:
                    row_parts.append(" " * 6)

            if show_lang_col:
                lang_label = lang[:11] if len(lang) <= 11 else (lang[:8] + "...")
                row_parts.append(f"{C_DIM}{lang_label:<11}{C_RESET}")

            row_parts.append(f"{C_BOLD}{display_path}{C_RESET}")
            print(f"    {' '.join(row_parts)}", file=sys.stderr)

    # Largest Folders
    folder_stats = _get_folder_stats(stats.get('top_files'))
    if folder_stats:
        top_f, title, total_for_percent, has_tokens, has_lines = _get_summary_top_items(
            stats, list(folder_stats.items()), is_folder=True
        )
        primary_metric = _get_primary_metric(has_tokens, has_lines)

        # Calculate dynamic overhead for path width
        # Indentation (4) + Primary (13) + % (7)
        overhead = 4 + 13 + 7
        # Secondary Metrics (13 each)
        if show_secondary:
            if has_tokens and primary_metric != 'tokens': overhead += 13
            if has_lines and primary_metric != 'lines': overhead += 13
            if primary_metric != 'size': overhead += 13
        # Distribution (13)
        if show_dist: overhead += 13
        # Files (%) (16)
        overhead += 16
        # Status Spacer (7)
        if any_has_status: overhead += 7
        # Language Spacer (12)
        if show_lang_col: overhead += 12

        path_width = max(20, term_width - overhead)

        # Build dynamic header
        header_parts = []
        # Secondary metrics first
        if show_secondary:
            if has_tokens and primary_metric != 'tokens':
                header_parts.append(_format_header('TOKENS', 'tokens', primary_metric))
            if has_lines and primary_metric != 'lines':
                header_parts.append(_format_header('LINES', 'lines', primary_metric))
            if primary_metric != 'size':
                header_parts.append(_format_header('SIZE', 'size', primary_metric))

        # Primary metric last before %
        if has_tokens and primary_metric == 'tokens':
            header_parts.append(_format_header('TOKENS', 'tokens', primary_metric))
        elif has_lines and primary_metric == 'lines':
            header_parts.append(_format_header('LINES', 'lines', primary_metric))
        elif primary_metric == 'size':
            header_parts.append(_format_header('SIZE', 'size', primary_metric))

        header_parts.append(f"{'%':>6}")
        if show_dist: header_parts.append(f"{'DISTRIBUTION':<12}")

        header_parts.append(f"{'FILES (%)':>15}")
        if any_has_status: header_parts.append(f"{' ': <6}") # Spacer to match largest files
        if show_lang_col: header_parts.append(f"{' ': <11}") # Language spacer
        header_parts.append("FOLDER")

        print(f"\n  {C_BOLD}{C_CYAN}{title}{C_RESET}", file=sys.stderr)
        print(f"    {C_DIM}{' '.join(header_parts)}{C_RESET}", file=sys.stderr)

        for path, data in top_f:
            tokens = data['tokens']
            f_size = data['size']
            f_lines = data.get('lines', 0)
            files = data['files']
            val_num = tokens if has_tokens else (f_lines if has_lines else f_size)
            percent = (val_num / total_for_percent * 100) if total_for_percent > 0 else 0.0
            bar = _make_ascii_bar(percent, colored=True)

            size_str = utils.format_size(f_size)
            s_val, s_unit = _split_unit(size_str)
            display_path = _truncate_path(path, path_width)
            size_padding = " " * max(0, 12 - len(s_val) - len(s_unit))

            row_parts = []
            # Secondary metrics first
            if show_secondary:
                if has_tokens and primary_metric != 'tokens':
                    token_str = format_tokens(tokens, is_approx)
                    row_parts.append(f"{C_DIM}{token_str:>12}{C_RESET}")
                if has_lines and primary_metric != 'lines':
                    row_parts.append(f"{C_DIM}{f_lines:12,}{C_RESET}")
                if primary_metric != 'size':
                    row_parts.append(f"{size_padding}{C_DIM}{s_val}{C_RESET}{C_DIM}{s_unit}{C_RESET}")

            # Primary metric last
            if has_tokens and primary_metric == 'tokens':
                token_str = format_tokens(tokens, is_approx)
                row_parts.append(f"{C_BOLD}{C_CYAN}{token_str:>12}{C_RESET}")
            elif has_lines and primary_metric == 'lines':
                row_parts.append(f"{C_BOLD}{C_CYAN}{f_lines:12,}{C_RESET}")
            elif primary_metric == 'size':
                row_parts.append(f"{size_padding}{C_BOLD}{C_CYAN}{s_val}{C_RESET}{C_DIM}{s_unit}{C_RESET}")

            row_parts.append(f"{C_BOLD}{C_CYAN}{percent:>5.1f}{C_RESET}{C_DIM}%{C_RESET}")

            if show_dist:
                row_parts.append(f"{C_DIM}[{C_RESET}{bar}{C_DIM}]{C_RESET}")

            # Consolidated Files (%)
            f_percent = (files / total_included * 100) if total_included > 0 else 0
            f_val = f"{files:,}"
            f_p_val = f"({f_percent:>5.1f}%)"
            row_parts.append(f"{C_DIM}{f_val:>6} {f_p_val}{C_RESET}")

            if any_has_status:
                row_parts.append(" " * 6) # Spacer to match largest files
            if show_lang_col:
                row_parts.append(" " * 11) # Language spacer

            row_parts.append(f"{C_BOLD}{display_path}{C_RESET}{C_DIM}/{C_RESET}")
            print(f"    {' '.join(row_parts)}", file=sys.stderr)

    # Languages List
    files_by_lang = stats.get('files_by_language')
    if files_by_lang:
        tokens_by_lang = stats.get('tokens_by_language', {})
        lines_by_lang = stats.get('lines_by_language', {})
        size_by_lang = stats.get('size_by_language', {})
        has_lang_tokens = any(v > 0 for v in tokens_by_lang.values())
        has_lang_lines = any(v > 0 for v in lines_by_lang.values())

        if has_lang_tokens:
            total_weight = stats.get('total_tokens', 0)
            weight_by_lang = tokens_by_lang
            title = "Languages (by tokens)"
        elif has_lang_lines:
            total_weight = stats.get('total_lines', 0)
            weight_by_lang = lines_by_lang
            title = "Languages (by lines)"
        else:
            total_weight = stats.get('total_size_bytes', 0)
            weight_by_lang = size_by_lang
            title = "Languages (by size)"

        primary_metric = _get_primary_metric(has_lang_tokens, has_lang_lines)

        # Calculate dynamic overhead for language width
        # Indentation (4) + Primary (13) + % (7)
        overhead = 4 + 13 + 7
        # Secondary Metrics (13 each)
        if show_secondary:
            if has_lang_tokens and primary_metric != 'tokens': overhead += 13
            if has_lang_lines and primary_metric != 'lines': overhead += 13
            if primary_metric != 'size': overhead += 13
        # Distribution (13)
        if show_dist: overhead += 13
        # Files (%) (16)
        overhead += 16
        # Status Spacer (7)
        if any_has_status: overhead += 7
        # Language metadata spacer (12)
        if show_lang_col: overhead += 12

        lang_width = max(20, term_width - overhead)

        # Build dynamic header
        header_parts = []
        # Secondary metrics first
        if show_secondary:
            if has_lang_tokens and primary_metric != 'tokens':
                header_parts.append(_format_header('TOKENS', 'tokens', primary_metric))
            if has_lang_lines and primary_metric != 'lines':
                header_parts.append(_format_header('LINES', 'lines', primary_metric))
            if primary_metric != 'size':
                header_parts.append(_format_header('SIZE', 'size', primary_metric))

        # Primary metric last before %
        if has_lang_tokens and primary_metric == 'tokens':
            header_parts.append(_format_header('TOKENS', 'tokens', primary_metric))
        elif has_lang_lines and primary_metric == 'lines':
            header_parts.append(_format_header('LINES', 'lines', primary_metric))
        elif primary_metric == 'size':
            header_parts.append(_format_header('SIZE', 'size', primary_metric))

        header_parts.append(f"{'%':>6}")
        if show_dist: header_parts.append(f"{'DISTRIBUTION':<12}")

        header_parts.append(f"{'FILES (%)':>15}")
        if any_has_status: header_parts.append(f"{' ': <6}") # Spacer to match largest files
        if show_lang_col: header_parts.append(f"{' ': <11}") # Language spacer
        header_parts.append("LANGUAGE")
        header = f"    {C_DIM}{' '.join(header_parts)}{C_RESET}"

        # Sort by weight desc, then count desc, then alpha
        sorted_langs = sorted(
            files_by_lang.items(),
            key=lambda item: (-weight_by_lang.get(item[0], 0), -item[1], item[0])
        )

        display_items = []
        top_10 = sorted_langs[:10]
        others = sorted_langs[10:]

        for lang, count in top_10:
            display_items.append({
                'lang': lang,
                'count': count,
                'weight': weight_by_lang.get(lang, 0),
                'tokens': tokens_by_lang.get(lang, 0),
                'lines': lines_by_lang.get(lang, 0),
                'size': size_by_lang.get(lang, 0)
            })

        if others:
            display_items.append({
                'lang': '(others)',
                'count': sum(c for l, c in others),
                'weight': sum(weight_by_lang.get(l, 0) for l, c in others),
                'tokens': sum(tokens_by_lang.get(l, 0) for l, c in others),
                'lines': sum(lines_by_lang.get(l, 0) for l, c in others),
                'size': sum(size_by_lang.get(l, 0) for l, c in others)
            })

        print(f"\n  {C_BOLD}{C_CYAN}{title}{C_RESET}", file=sys.stderr)
        print(header, file=sys.stderr)

        for d in display_items:
            count = d['count']
            weight = d['weight']
            f_percent = (count / total_included * 100) if total_included > 0 else 0
            w_percent = (weight / total_weight * 100) if total_weight > 0 else 0
            bar = _make_ascii_bar(w_percent, colored=True)

            size_str = utils.format_size(d['size'])
            s_val, s_unit = _split_unit(size_str)
            size_padding = " " * max(0, 12 - len(s_val) - len(s_unit))

            # Row Metrics (TOKENS, LINES, SIZE, %, DISTRIBUTION) - Vertical alignment with Largest Files
            row_parts = []
            # Secondary metrics first
            if show_secondary:
                if has_lang_tokens and primary_metric != 'tokens':
                    token_str = format_tokens(d['tokens'], is_approx)
                    row_parts.append(f"{C_DIM}{token_str:>12}{C_RESET}")
                if has_lang_lines and primary_metric != 'lines':
                    row_parts.append(f"{C_DIM}{d['lines']:12,}{C_RESET}")
                if primary_metric != 'size':
                    row_parts.append(f"{size_padding}{C_DIM}{s_val}{C_RESET}{C_DIM}{s_unit}{C_RESET}")

            # Primary metric last
            if has_lang_tokens and primary_metric == 'tokens':
                token_str = format_tokens(d['tokens'], is_approx)
                row_parts.append(f"{C_BOLD}{C_CYAN}{token_str:>12}{C_RESET}")
            elif has_lang_lines and primary_metric == 'lines':
                row_parts.append(f"{C_BOLD}{C_CYAN}{d['lines']:12,}{C_RESET}")
            elif primary_metric == 'size':
                row_parts.append(f"{size_padding}{C_BOLD}{C_CYAN}{s_val}{C_RESET}{C_DIM}{s_unit}{C_RESET}")

            row_parts.append(f"{C_BOLD}{C_CYAN}{w_percent:>5.1f}{C_RESET}{C_DIM}%{C_RESET}")

            if show_dist:
                row_parts.append(f"{C_DIM}[{C_RESET}{bar}{C_DIM}]{C_RESET}")

            # Consolidated Files (%)
            f_val = f"{count:,}"
            f_p_val = f"({f_percent:>5.1f}%)"
            row_parts.append(f"{C_DIM}{f_val:>6} {f_p_val}{C_RESET}")

            if any_has_status:
                row_parts.append(" " * 6) # Spacer to match largest files
            if show_lang_col:
                row_parts.append(" " * 11) # Language spacer

            lang_label = d['lang']
            display_lang = _truncate_path(lang_label, lang_width)
            row_parts.append(f"{C_BOLD}{display_lang}{C_RESET}")

            print(f"    {' '.join(row_parts)}", file=sys.stderr)

    # Footer
    footer_len = min(raw_title_len, term_width)
    print(f"\n{title_color}{'=' * footer_len}{C_RESET}", file=sys.stderr)


if __name__ == "__main__":
    main()
