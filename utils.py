import copy
import json
import logging
import platform
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from charset_normalizer import from_bytes

try:  # Mandatory dependency for YAML support, but handled gracefully
    import yaml
except ImportError:
    yaml = None

try:  # Optional tool for accurate token counting
    import tiktoken
except ImportError:
    tiktoken = None


__version__ = "0.5.0"
DEFAULT_OUTPUT_FILENAME = "combined_files.txt"
FILENAME_PLACEHOLDER = "{{FILENAME}}"

# Mapping of file extensions to Markdown-friendly language tags for syntax highlighting.
EXTENSION_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".rb": "ruby",
    ".rs": "rust",
    ".go": "go",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".h": "cpp",
    ".cs": "csharp",
    ".java": "java",
    ".kt": "kotlin",
    ".php": "php",
    ".sql": "sql",
    ".xml": "xml",
    ".toml": "toml",
    ".ini": "ini",
    ".conf": "ini",
    ".bat": "batch",
    ".cmd": "batch",
    ".ps1": "powershell",
    ".dockerfile": "dockerfile",
    ".makefile": "makefile",
    ".cmake": "cmake",
    ".swift": "swift",
    ".dart": "dart",
    ".scala": "scala",
    ".lua": "lua",
    ".r": "r",
    ".pl": "perl",
    ".pm": "perl",
    ".vue": "vue",
    ".svelte": "svelte",
    ".groovy": "groovy",
    ".m": "objectivec",
    ".mm": "objectivecpp",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".clj": "clojure",
    ".cljs": "clojure",
    ".cljc": "clojure",
    ".edn": "clojure",
    ".hs": "haskell",
    ".lhs": "haskell",
    ".sol": "solidity",
    ".jl": "julia",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".hcl": "hcl",
    ".tf": "hcl",
    ".pyx": "cython",
    ".pxd": "cython",
    ".pxi": "cython",
    ".zig": "zig",
    ".nim": "nim",
    ".jsonc": "json",
    ".zon": "zig",
}

# Mapping of specific filenames to Markdown-friendly language tags.
FILENAME_TO_LANG = {
    ".gitignore": "gitignore",
    ".gitattributes": "gitattributes",
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "cmakelists.txt": "cmake",
    "package.json": "json",
    "package-lock.json": "json",
    "yarn.lock": "yaml",
    "pnpm-lock.yaml": "yaml",
    "composer.json": "json",
    "composer.lock": "json",
    "cargo.toml": "toml",
    "cargo.lock": "toml",
    "pyproject.toml": "toml",
    "poetry.lock": "toml",
    "gemfile": "ruby",
    "rakefile": "ruby",
    "jenkinsfile": "groovy",
    "procfile": "yaml",
    "sourcecombine.yml": "yaml",
    "sourcecombine.yaml": "yaml",
    "pubspec.yaml": "yaml",
    "pubspec.lock": "yaml",
}

COMPACT_WHITESPACE_GROUPS = (
    'normalize_line_endings',
    'spaces_to_tabs',
    'trim_spaces_around_tabs',
    'replace_mid_line_tabs',
    'trim_trailing_whitespace',
    'compact_blank_lines',
    'compact_space_runs',
)

# Mapping of language tags to their comment styles.
# Each entry is a tuple of (single_line_prefix, multi_line_start, multi_line_end).
# Use None if a style is not supported for that language.
LANG_TO_COMMENT_STYLE = {
    "python": ("#", '"""', '"""'),
    "javascript": ("//", "/*", "*/"),
    "typescript": ("//", "/*", "*/"),
    "html": (None, "<!--", "-->"),
    "css": (None, "/*", "*/"),
    "scss": ("//", "/*", "*/"),
    "sass": ("//", "/*", "*/"),
    "less": ("//", "/*", "*/"),
    "bash": ("#", None, None),
    "ruby": ("#", "=begin", "=end"),
    "rust": ("//", "/*", "*/"),
    "go": ("//", "/*", "*/"),
    "c": ("//", "/*", "*/"),
    "cpp": ("//", "/*", "*/"),
    "csharp": ("//", "/*", "*/"),
    "java": ("//", "/*", "*/"),
    "kotlin": ("//", "/*", "*/"),
    "php": ("//", "/*", "*/"),
    "sql": ("--", "/*", "*/"),
    "xml": (None, "<!--", "-->"),
    "toml": ("#", None, None),
    "ini": (";", None, None),
    "batch": ("REM", None, None),
    "powershell": ("#", "<#", "#>"),
    "dockerfile": ("#", None, None),
    "makefile": ("#", None, None),
    "cmake": ("#", None, None),
    "swift": ("//", "/*", "*/"),
    "dart": ("//", "/*", "*/"),
    "scala": ("//", "/*", "*/"),
    "lua": ("--", "--[[", "]]"),
    "r": ("#", None, None),
    "perl": ("#", "=pod", "=cut"),
    "groovy": ("//", "/*", "*/"),
    "objectivec": ("//", "/*", "*/"),
    "objectivecpp": ("//", "/*", "*/"),
    "elixir": ("#", None, None),
    "erlang": ("%", None, None),
    "clojure": (";", None, None),
    "haskell": ("--", "{-", "-}"),
    "solidity": ("//", "/*", "*/"),
    "julia": ("#", "#=", "=#"),
    "hcl": ("#", "/*", "*/"),
    "zig": ("//", None, None),
    "nim": ("#", "#[", "]#"),
}

DEFAULT_CONFIG = {
    'logging': {
        'level': 'INFO',
    },
    'search': {
        'max_depth': 0,
        'use_git': False,
        'use_git_diff': False,
        'git_diff_ref': None,
        'git_staged': False,
        'git_unstaged': False,
        'allowed_languages': [],
        'exclude_languages': [],
        'exclude_extensions': [],
        'custom_languages': {},
        'ignore_files': [],
    },
    'filters': {
        'unique': False,
        'skip_binary': False,
        'min_tokens': 0,
        'max_tokens': 0,
        'min_lines': 0,
        'max_lines': 0,
        'max_total_tokens': 0,
        'max_total_size_bytes': 0,
        'max_total_lines': 0,
        'max_files': 0,
        'modified_since': 0,
        'modified_until': 0,
        'grep': '',
        'exclude_grep': '',
        'exclusions': {
            'filenames': [
                '*.pyc', '*.pyo', '*.pyd',
                '.DS_Store', 'Thumbs.db',
                '.coverage', '.tox', '.nox',
                '.sourcecombineignore',
            ],
            'folders': [
                '.git', '.svn', '.hg', '.cvs',
                '.idea', '.vscode',
                '__pycache__', 'node_modules',
                'venv', '.venv', 'env', '.env',
                'dist', 'build', 'target',
                'egg-info', '.egg-info',
            ],
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
        'file': DEFAULT_OUTPUT_FILENAME,
        'folder': None,
        'paired_filename_template': '{{STEM}}.combined',
        'add_line_numbers': False,
        'table_of_contents': False,
        'project_overview': False,
        'git_log_count': 0,
        'header_template': f"--- {FILENAME_PLACEHOLDER} ---\n",
        'footer_template': f"\n--- end {FILENAME_PLACEHOLDER} ---\n",
        'global_header_template': None,
        'global_footer_template': None,
        'max_size_placeholder': None,
        'format': 'text',
        'sort_by': 'name',
        'sort_reverse': False,
        'summary_json': None,
        'show_diff': False,
        'include_diff': False,
        'mirror': False,
        'skip_content': False,
        'collapsible': False,
    },
    'project': {
        'name': None,
        'version': None,
        'author': None,
        'description': None,
        'license': None,
        'url': None,
    },
    'processing': {
        'apply_in_place': False,
        'create_backups': True,
        'remove_comments': False,
        'remove_single_line_comments': False,
        'max_lines': 0,
        'max_tokens': 0,
    },
}


class ConfigNotFoundError(FileNotFoundError):
    """Raised when the configuration file cannot be found."""


class InvalidConfigError(Exception):
    """Raised when the configuration file is invalid."""


def load_yaml_config(config_file_path):
    """Load a YAML configuration file."""
    if yaml is None:
        raise InvalidConfigError(
            "The 'PyYAML' library is required to load YAML configurations. "
            "Install it with: pip install pyyaml"
        )

    logging.info("Loading configuration from: %s", config_file_path)
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                raise InvalidConfigError("Configuration file is empty or invalid.")
            return config
    except FileNotFoundError as e:
        raise ConfigNotFoundError(
            f"Configuration file not found at '{config_file_path}'."
        ) from e
    except (AttributeError, yaml.YAMLError) as e:
        mark = getattr(e, 'problem_mark', None)
        location = ""
        if mark:
            location = f" at line {mark.line + 1}, column {mark.column + 1}"

        problem = getattr(e, 'problem', None) or str(e)
        context = getattr(e, 'context', None)
        details = f"{context}: {problem}" if context else problem

        hint = None
        if isinstance(e, yaml.scanner.ScannerError) and context:
            if 'quoted scalar' in context:
                hint = "Check for missing closing quotes in the YAML file."

        message = f"Error parsing YAML file{location}: {details}"
        if hint:
            message = f"{message} ({hint})"

        raise InvalidConfigError(message) from e


def save_yaml_config(config_file_path, config):
    """Save a dictionary to a YAML configuration file."""
    if yaml is None:
        raise InvalidConfigError(
            "The 'PyYAML' library is required to save YAML configurations. "
            "Install it with: pip install pyyaml"
        )

    logging.info("Saving configuration to: %s", config_file_path)
    try:
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write("# SourceCombine Configuration\n")
            yaml.dump(config, f, sort_keys=False)
    except OSError as e:
        raise InvalidConfigError(f"Could not write configuration file: {e}") from e


def _decode_best_effort(raw_bytes: bytes, source_label: str) -> tuple[str, str]:
    """Identify and apply the best character encoding for the provided bytes.

    Returns a tuple of (decoded_text, encoding_name).
    """
    try:
        text = raw_bytes.decode('utf-8-sig')
        if '\x00' in text:
            raise UnicodeError("Found empty (NUL) characters; trying fallback detection.")
        # Only return utf-8-sig if it actually had a BOM
        encoding = 'utf-8-sig' if raw_bytes.startswith(b'\xef\xbb\xbf') else 'utf-8'
        return text, encoding
    except UnicodeError:
        pass

    best_guess = from_bytes(raw_bytes).best()
    if best_guess and best_guess.encoding:
        encoding = best_guess.encoding
        if encoding.lower().replace('-', '_').startswith('utf_16'):
            has_bom = raw_bytes.startswith((b'\xff\xfe', b'\xfe\xff'))
            has_nulls = b'\x00' in raw_bytes
            if not has_bom and not has_nulls and len(raw_bytes) < 6:
                # Guard against spurious UTF-16 guesses on very small files
                encoding = 'latin-1'
        try:
            return raw_bytes.decode(encoding, errors='replace').lstrip('\ufeff'), encoding
        except LookupError:
            logging.warning(
                "Detected encoding '%s' is not supported for %s.", encoding, source_label
            )

    logging.warning(
        "Could not detect encoding for %s; decoding with UTF-8 replacements.",
        source_label,
    )
    return raw_bytes.decode('utf-8', errors='replace').lstrip('\ufeff'), 'utf-8'


def read_file_best_effort(file_path: str | Path) -> tuple[str, str]:
    """Attempt to read a file using multiple methods.

    Try to decode the file as UTF-8, then use automated detection to find the
    most likely encoding before falling back to a standard UTF-8 read with
    replacements.

    Returns:
        (str, str): The text content and the name of its encoding.
    """
    try:
        raw_bytes = Path(file_path).read_bytes()
        return _decode_best_effort(raw_bytes, str(file_path))
    except FileNotFoundError:
        raise
    except OSError:
        logging.warning("Could not read %s.", file_path)
        return "", 'utf-8'


def parse_ignore_file(file_path: str | Path) -> list[str]:
    """Read an ignore file and return a list of non-empty patterns.

    Supports '#' for comments and skips empty lines.
    """
    path = Path(file_path)
    if not path.is_file():
        return []

    patterns = []
    try:
        content, _ = read_file_best_effort(path)
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            patterns.append(line)
    except Exception as e:
        logging.warning("Could not read ignore file '%s': %s", file_path, e)

    return patterns


def read_url_best_effort(url: str, timeout: int = 15) -> tuple[str, str]:
    """Fetch content from a URL and decode it using best-effort logic.

    Returns a tuple of (content_text, encoding_name).
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': f'SourceCombine/{__version__}'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_bytes = response.read()
            return _decode_best_effort(raw_bytes, url)
    except Exception as e:
        logging.warning("Failed to fetch content from URL '%s': %s", url, e)
        return "", 'utf-8'


def _looks_binary(
    path: Path | None = None, sample: bytes | None = None, sample_size: int = 4096
) -> bool:
    """Return ``True`` if the file seems to contain data that is not text."""

    if sample is None:
        if path is None:
            return False
        try:
            with open(path, 'rb') as f:
                sample = f.read(sample_size)
        except OSError:
            return False
    else:
        sample = sample[:sample_size]

    if not sample:
        return False

    if b'\x00' in sample:
        return True

    allowed_control_bytes = {9, 10, 12, 13}
    non_text_control = sum(
        1 for byte in sample if byte < 0x20 and byte not in allowed_control_bytes
    )
    return (non_text_control / len(sample)) > 0.30


def remove_comments_by_lang(text, lang, single_only=False, multi_only=False):
    """Remove comments from text based on the language style.

    Parameters
    ----------
    text : str
        The source text to process.
    lang : str
        The language tag (for example, 'python', 'cpp').
    single_only : bool
        If true, only remove single-line comments.
    multi_only : bool
        If true, only remove multi-line comments.
    """
    if not text or not lang or lang not in LANG_TO_COMMENT_STYLE:
        return text

    single_prefix, multi_start, multi_end = LANG_TO_COMMENT_STYLE[lang]

    # Handle multi-line comments first to avoid them being partially
    # matched by single-line prefix rules.
    if multi_start and multi_end and not single_only:
        # We use a non-greedy dotall match to find all comment blocks.
        pattern = re.escape(multi_start) + r'.*?' + re.escape(multi_end)
        text = re.sub(pattern, '', text, flags=re.DOTALL)

    if single_prefix and not multi_only:
        # Match from prefix to end of line, being careful not to match
        # prefixes inside strings or already within multi-line comments.
        # This is a basic implementation; robust comment removal usually
        # requires a proper lexer, but this works for most common cases.
        pattern = r'^[ \t]*' + re.escape(single_prefix) + r'.*$'
        text = re.sub(pattern, '', text, flags=re.MULTILINE)

        # Also try to catch trailing comments, but only if they are preceded by whitespace
        # to reduce the risk of matching markers inside strings.
        trailing_pattern = r'[ \t]+' + re.escape(single_prefix) + r'.*$'
        text = re.sub(trailing_pattern, '', text, flags=re.MULTILINE)

    return text


def compact_whitespace(text, *, groups=None):
    """Compact and normalize whitespace within ``text``.

    This function is designed for formatting plain text and may not be suitable
    for code, especially Python, where whitespace is part of the code's meaning.

    Transformations are applied in the following order:

    - Change Windows (CRLF) and classic Mac (CR) line endings to standard newlines (LF).
    - Convert each run of four spaces that follow each other to a tab character. This is
      intended to normalize indentation but may affect other formatting.
    - Trim spaces that surround tabs, which helps collapse mixed indentation.
    - Replace mid-line tabs (those not at the start of a line) with single
      spaces for readability.
    - Trim trailing horizontal whitespace from all lines.
    - Collapse many blank lines into at most two newlines that follow each other.
    - Reduce any remaining long runs of spaces to at most two characters.

    Note: keep the search patterns compatible with Python 3.8 for the sake
    of the packaging targets this project supports.
    """
    def _should_apply(key):
        if groups is None:
            return True
        value = groups.get(key, True)
        if value is None:
            return True
        return bool(value)

    if _should_apply('normalize_line_endings'):
        text = text.replace('\r\n', '\n').replace('\r', '\n')
    if _should_apply('spaces_to_tabs'):
        text = re.sub(r' {4}', '\t', text)
    if _should_apply('trim_spaces_around_tabs'):
        text = re.sub(r' +\t', '\t', text)
        text = re.sub(r'(?<=[^\n\t])\t +', '\t', text)
        text = re.sub(r'^(\t+) +(?=\S)', r'\1', text, flags=re.MULTILINE)
        text = re.sub(r'\t {2,}(?=\s|$)', '\t ', text)
    if _should_apply('replace_mid_line_tabs'):
        text = re.sub(r'(?<=[^\n\t])\t+', ' ', text)
    if _should_apply('trim_trailing_whitespace'):
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    if _should_apply('compact_blank_lines'):
        text = re.sub(r'\n{3,}', '\n\n', text)
    if _should_apply('compact_space_runs'):
        text = re.sub(r' {3,}', '  ', text)
    return text


def _validate_compact_whitespace_groups(groups, *, context):
    if groups is None:
        return
    if not isinstance(groups, dict):
        raise InvalidConfigError(
            f"'{context}' must be a dictionary of group names (set to true, false, or null)."
        )

    for key, value in groups.items():
        if key not in COMPACT_WHITESPACE_GROUPS:
            logging.warning(
                "Unknown compact_whitespace_groups entry '%s' in %s; it will be ignored.",
                key,
                context,
            )
            continue
        if value is not None and not isinstance(value, bool):
            raise InvalidConfigError(
                f"Values in '{context}' must be true, false, or null."
            )


def _validate_regex_list(rules, context_prefix, source):
    """Validate a list of regex replacement rules."""
    if rules is None:
        return
    if not isinstance(rules, list):
        raise InvalidConfigError(f"'{context_prefix}' must be a list.")

    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise InvalidConfigError(
                f"Item {i} in '{context_prefix}' must be a dictionary."
            )
        if 'pattern' in rule:
            validate_regex_pattern(
                rule['pattern'],
                context=f"{context_prefix}[{i}]",
                source=source,
            )


def _replace_line_block(text, regex, replacement=None):
    """Collapse blocks of lines matching ``regex`` into ``replacement``.

    ``regex`` should be a compiled search pattern that matches an entire
    line. Lines that follow each other and match are treated as a single block.
    If ``replacement`` is ``None`` the block is simply removed; otherwise
    ``replacement`` is inserted once for each block.
    """
    lines = text.splitlines()
    out_lines = []
    in_block = False
    for line in lines:
        if regex.match(line):
            in_block = True
            continue
        if in_block:
            if replacement is not None:
                out_lines.append(replacement)
            in_block = False
        out_lines.append(line)
    if in_block:
        if replacement is not None:
            out_lines.append(replacement)

    result = "\n".join(out_lines)
    if text.endswith("\n") and out_lines:
        result += "\n"
    return result


def _validate_glob_list(filenames, context_prefix):
    """Validate and sanitize a list of search patterns in place."""
    if filenames is None:
        return
    if not isinstance(filenames, list):
        raise InvalidConfigError(f"'{context_prefix}' must be a list.")

    for i, pattern in enumerate(filenames):
        sanitized = validate_glob_pattern(
            pattern, context=f"{context_prefix}[{i}]"
        )
        if sanitized != pattern:
            filenames[i] = sanitized


def _normalize_string_list(items, context_prefix, item_label="text", list_label="a list"):
    """Ensure a value is a list of lowercase strings and update it in-place.

    Returns the normalized list.
    """
    if items is None:
        return []
    if not isinstance(items, list):
        raise InvalidConfigError(f"{context_prefix} must be {list_label}.")

    normalized = []
    for item in items:
        if not isinstance(item, str):
            raise InvalidConfigError(f"Values in '{context_prefix}' must be {item_label}.")
        normalized.append(item.lower())

    items[:] = normalized
    return normalized


def _normalize_extension_list(ext_list, context_prefix):
    """Normalize a list of file extensions in place.

    Ensures each extension is a lowercase string with a leading dot.
    """
    _normalize_string_list(ext_list, context_prefix)

    normalized = []
    for ext in (ext_list or []):
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized.append(ext)

    if ext_list is not None:
        ext_list[:] = normalized
    return normalized


def _raise_validation_error(key: str, context: str, requirement: str) -> None:
    """Raise InvalidConfigError with context-dependent formatting."""
    if context in ('search', 'filters'):
        message = f"{context}.{key} {requirement}"
    elif context == 'processing':
        message = f"'{context}.{key}' {requirement}"
    else:  # output
        message = f"'{context}.{key}' {requirement}."
    raise InvalidConfigError(message)


def _validate_bool(container: Mapping[str, Any], key: str, context: str) -> None:
    """Ensure the value at ``key`` in ``container`` is a boolean if present."""
    val = container.get(key)
    if val is not None and not isinstance(val, bool):
        _raise_validation_error(key, context, "must be true or false")


def _validate_positive_number(
    container: Mapping[str, Any], key: str, context: str, types: Any = int
) -> None:
    """Ensure the value at ``key`` in ``container`` is a non-negative number if present."""
    val = container.get(key)
    if val is not None:
        if isinstance(val, bool) or not isinstance(val, types) or val < 0:
            _raise_validation_error(key, context, "must be 0 or more")


def _validate_search_section(config):
    """Validate the 'search' section of the configuration."""
    search = config.get('search')
    if not isinstance(search, dict):
        raise InvalidConfigError("'search' section must be a dictionary.")

    _validate_positive_number(search, 'max_depth', 'search')
    _validate_bool(search, 'use_git', 'search')
    _validate_bool(search, 'use_git_diff', 'search')

    git_diff_ref = search.get('git_diff_ref')
    if git_diff_ref is not None and not isinstance(git_diff_ref, str):
        raise InvalidConfigError(
            "search.git_diff_ref must be text or nothing"
        )

    _validate_bool(search, 'git_staged', 'search')
    _validate_bool(search, 'git_unstaged', 'search')

    root_folders = search.get('root_folders')
    if root_folders is not None and not isinstance(root_folders, list):
        raise InvalidConfigError("search.root_folders must be a list of folders.")

    _normalize_extension_list(search.get('allowed_extensions'), 'search.allowed_extensions')
    _normalize_extension_list(search.get('exclude_extensions'), 'search.exclude_extensions')

    _normalize_string_list(
        search.get('allowed_languages'),
        'search.allowed_languages',
        list_label="a list of languages",
    )
    _normalize_string_list(
        search.get('exclude_languages'),
        'search.exclude_languages',
        list_label="a list of languages",
    )
    _normalize_string_list(search.get('ignore_files'), 'search.ignore_files')

    custom_langs = search.get('custom_languages')
    if custom_langs is not None:
        if not isinstance(custom_langs, dict):
            raise InvalidConfigError("search.custom_languages must be a dictionary.")
        normalized = {}
        for key, val in custom_langs.items():
            if not isinstance(key, str) or not isinstance(val, str):
                raise InvalidConfigError("Both keys and values in 'search.custom_languages' must be text.")
            normalized[key.lower()] = val.lower()
        search['custom_languages'] = normalized


def _validate_filters_section(config):
    """Validate the 'filters' section of the configuration."""
    filters = config.get('filters')
    if not isinstance(filters, dict):
        raise InvalidConfigError("'filters' section must be a dictionary.")

    integer_filters = (
        'min_size_bytes',
        'max_size_bytes',
        'min_tokens',
        'max_tokens',
        'min_lines',
        'max_lines',
        'max_total_tokens',
        'max_total_size_bytes',
        'max_total_lines',
        'max_files',
    )
    for key in integer_filters:
        _validate_positive_number(filters, key, 'filters')

    for key in ('modified_since', 'modified_until'):
        _validate_positive_number(filters, key, 'filters', types=(int, float))

    _validate_bool(filters, 'unique', 'filters')
    _validate_bool(filters, 'skip_binary', 'filters')

    grep_pattern = filters.get('grep')
    if grep_pattern:
        validate_regex_pattern(grep_pattern, context="filters.grep")

    exclude_grep_pattern = filters.get('exclude_grep')
    if exclude_grep_pattern:
        validate_regex_pattern(exclude_grep_pattern, context="filters.exclude_grep")

    exclusions_conf = filters.get('exclusions')
    if exclusions_conf is not None:
        if not isinstance(exclusions_conf, dict):
            raise InvalidConfigError("filters.exclusions must be a dictionary.")
        filenames = exclusions_conf.get('filenames', [])
        _validate_glob_list(filenames, "filters.exclusions.filenames")
        folders = exclusions_conf.get('folders', [])
        _validate_glob_list(folders, "filters.exclusions.folders")

    groups = filters.get('inclusion_groups')
    if groups is not None:
        if not isinstance(groups, dict):
            raise InvalidConfigError("filters.inclusion_groups must be a dictionary.")
        for group_name, group in groups.items():
            if not isinstance(group, dict):
                raise InvalidConfigError(
                    f"filters.inclusion_groups.{group_name} must be a dictionary."
                )
            group.setdefault('enabled', False)
            filenames = group.setdefault('filenames', [])
            _validate_glob_list(
                filenames, f"filters.inclusion_groups.{group_name}.filenames"
            )

    if (
        isinstance(groups, dict)
        and any(
            isinstance(g, dict) and g.get('enabled') for g in groups.values()
        )
        and config.get('search', {}).get('allowed_extensions')
    ):
        raise InvalidConfigError(
            "'filters.inclusion_groups' and 'search.allowed_extensions' cannot be used at the same time; "
            "specify file types in the inclusion group patterns instead (for example, 'src/**/*.py')."
        )


def _validate_processing_section(config, *, source=None):
    """Validate the 'processing' section of the configuration."""
    processing_conf = config.get('processing')
    if not isinstance(processing_conf, dict):
        raise InvalidConfigError("'processing' section must be a dictionary.")

    _validate_bool(processing_conf, 'apply_in_place', 'processing')
    _validate_bool(processing_conf, 'compact_whitespace', 'processing')
    _validate_bool(processing_conf, 'create_backups', 'processing')
    _validate_bool(processing_conf, 'remove_comments', 'processing')
    _validate_bool(processing_conf, 'remove_single_line_comments', 'processing')

    _validate_compact_whitespace_groups(
        processing_conf.get('compact_whitespace_groups'),
        context='processing.compact_whitespace_groups',
    )

    # Validate regex patterns in regex_replacements
    _validate_regex_list(
        processing_conf.get('regex_replacements'),
        "processing.regex_replacements",
        source,
    )

    # Validate regex patterns in line_regex_replacements
    _validate_regex_list(
        processing_conf.get('line_regex_replacements'),
        "processing.line_regex_replacements",
        source,
    )

    _validate_positive_number(processing_conf, 'max_lines', 'processing')
    _validate_positive_number(processing_conf, 'max_tokens', 'processing')

    if 'in_place_groups' in processing_conf:
        raise InvalidConfigError(
            "'processing.in_place_groups' is no longer used. "
            "Use 'processing.apply_in_place' instead."
        )


def _validate_pairing_section(config):
    """Validate the 'pairing' section and its interaction with 'search'."""
    pairing_conf = config.get('pairing')
    if not isinstance(pairing_conf, dict):
        raise InvalidConfigError("'pairing' section must be a dictionary.")

    search_conf = config['search']

    if pairing_conf.get('enabled'):
        if search_conf.get('allowed_extensions'):
            raise InvalidConfigError(
                "'allowed_extensions' cannot be used when pairing is enabled; remove it or disable pairing."
            )
        if search_conf.get('exclude_extensions'):
            raise InvalidConfigError(
                "'exclude_extensions' cannot be used when pairing is enabled; remove it or disable pairing."
            )

        source_ext_list = pairing_conf.get('source_extensions')
        _normalize_extension_list(source_ext_list, 'pairing.source_extensions')

        header_ext_list = pairing_conf.get('header_extensions')
        _normalize_extension_list(header_ext_list, 'pairing.header_extensions')

        source_exts = tuple(e.lower() for e in (source_ext_list or []))
        header_exts = tuple(e.lower() for e in (header_ext_list or []))
        effective_allowed_extensions = source_exts + header_exts
        effective_exclude_extensions = ()
    else:
        effective_allowed_extensions = tuple(
            e.lower() for e in (search_conf.get('allowed_extensions') or [])
        )
        effective_exclude_extensions = tuple(
            e.lower() for e in (search_conf.get('exclude_extensions') or [])
        )

    search_conf['effective_allowed_extensions'] = effective_allowed_extensions
    search_conf['effective_exclude_extensions'] = effective_exclude_extensions


def _validate_project_section(config):
    """Validate the 'project' section of the configuration."""
    project = config.get('project')
    if project is None:
        return

    if not isinstance(project, dict):
        raise InvalidConfigError("'project' section must be a dictionary.")

    fields = ['name', 'version', 'description', 'license', 'url']
    for field in fields:
        val = project.get(field)
        if val is not None and not isinstance(val, str):
            raise InvalidConfigError(f"'project.{field}' must be text or nothing.")


def _validate_output_section(config):
    """Validate the 'output' section of the configuration."""

    output_conf = config.get('output')
    if not isinstance(output_conf, dict):
        raise InvalidConfigError("'output' section must be a dictionary.")

    string_fields = [
        'file',
        'folder',
        'header_template',
        'footer_template',
        'global_header_template',
        'global_footer_template',
        'max_size_placeholder',
        'format',
        'summary_json',
    ]

    for field in string_fields:
        value = output_conf.get(field)
        if value is not None and not isinstance(value, str):
            raise InvalidConfigError(f"'output.{field}' must be text or nothing.")

    _validate_bool(output_conf, 'table_of_contents', 'output')
    _validate_bool(output_conf, 'project_overview', 'output')
    _validate_positive_number(output_conf, 'git_log_count', 'output')

    placeholder = output_conf.get('max_size_placeholder')

    if placeholder and FILENAME_PLACEHOLDER not in placeholder:
        logging.warning(
            "'output.max_size_placeholder' is set but does not include the %s placeholder",
            FILENAME_PLACEHOLDER,
        )

    fmt = output_conf.get('format')
    if fmt is not None and fmt not in ('text', 'json', 'jsonl', 'markdown', 'xml', 'manifest', 'csv'):
        raise InvalidConfigError("'output.format' must be one of: text, json, jsonl, markdown, xml, manifest, csv")

    sort_by = output_conf.get('sort_by')
    if sort_by is not None and sort_by not in ('name', 'size', 'modified', 'tokens', 'lines', 'depth', 'language'):
        raise InvalidConfigError(
            "'output.sort_by' must be one of: name, size, modified, tokens, lines, depth, language"
        )

    _validate_bool(output_conf, 'sort_reverse', 'output')
    _validate_bool(output_conf, 'show_diff', 'output')
    _validate_bool(output_conf, 'include_diff', 'output')
    _validate_bool(output_conf, 'mirror', 'output')
    _validate_bool(output_conf, 'skip_content', 'output')
    _validate_bool(output_conf, 'collapsible', 'output')


def apply_line_regex_replacements(text, rules):
    """Apply line-oriented regex replacements.

    Each rule in ``rules`` must provide a ``pattern`` key. If ``replacement``
    is supplied, it is inserted once for each contiguous block of matching
    lines; otherwise matching lines are removed. Rules are applied
    sequentially.
    """
    for rule in rules or []:
        pattern = rule.get('pattern')
        if not pattern:
            continue
        replacement = rule.get('replacement')
        compiled = validate_regex_pattern(
            pattern, context="processing.line_regex_replacements"
        )
        text = _replace_line_block(text, compiled, replacement)
    return text


def validate_config(
    config: dict,
    required_keys: Sequence[str] | None = None,
    defaults: Mapping[str, Any] = DEFAULT_CONFIG,
    nested_required: Mapping[str, Sequence[str]] | None = None,
    source: str | Path | None = None,
) -> None:
    """Check the settings and apply default values.

    This function performs the same validation steps as
    :func:`load_and_validate_config` but operates on a dictionary instead of a
    file path.
    """
    if not isinstance(config, dict):
        raise InvalidConfigError("Configuration must be a dictionary.")

    if required_keys:
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InvalidConfigError(
                f"Config is missing required keys: {', '.join(missing_keys)}"
            )

    if defaults:
        def apply_defaults(cfg, defs):
            for key, value in defs.items():
                if isinstance(value, dict):
                    if key not in cfg or cfg[key] is None:
                        cfg[key] = {}
                    node = cfg[key]
                    if isinstance(node, dict):
                        apply_defaults(node, value)
                elif key not in cfg or cfg[key] is None:
                    # Use deepcopy to prevent shared references to mutable defaults (lists/dicts)
                    # polluting the global DEFAULT_CONFIG when 'cfg' is modified later.
                    cfg[key] = copy.deepcopy(value)

        apply_defaults(config, defaults)

    if nested_required:
        for key, subkeys in nested_required.items():
            if not isinstance(config.get(key), dict):
                raise InvalidConfigError(
                    f"'{key}' section must be a dictionary with keys: {', '.join(subkeys)}"
                )
            missing_sub = [sub for sub in subkeys if sub not in config[key]]
            if missing_sub:
                raise InvalidConfigError(
                    f"'{key}' section is missing keys: {', '.join(missing_sub)}"
                )

    _validate_search_section(config)
    _validate_filters_section(config)
    _validate_processing_section(config, source=source)
    _validate_pairing_section(config)
    _validate_output_section(config)
    _validate_project_section(config)


def load_and_validate_config(
    config_file_path: str | Path,
    required_keys: Sequence[str] | None = None,
    defaults: Mapping[str, Any] = DEFAULT_CONFIG,
    nested_required: Mapping[str, Sequence[str]] | None = None,
) -> dict:
    """Load a YAML config file and enforce required keys and defaults.

    ``defaults`` may contain nested dictionaries, which are merged recursively
    into the loaded configuration. The canonical defaults are provided by
    ``DEFAULT_CONFIG`` but may be overridden or extended via the ``defaults``
    parameter.
    """
    config = load_yaml_config(config_file_path)
    validate_config(
        config,
        required_keys=required_keys,
        defaults=defaults,
        nested_required=nested_required,
        source=config_file_path,
    )
    return config


def process_content(buffer: str, options: Mapping[str, Any], language: str | None = None) -> str:
    """Process text based on a dictionary of options.

    Supported options include:
    - ``remove_initial_c_style_comment`` (bool)
    - ``remove_all_c_style_comments`` (bool)
    - ``remove_comments`` (bool): remove both single-line and multi-line comments.
    - ``remove_single_line_comments`` (bool): remove only single-line comments.
    - ``regex_replacements`` (list of dicts): each rule must contain ``pattern`` (str)
      and ``replacement`` (str). Rules are applied sequentially. Capture groups
      can be referenced in the replacement string (for example, ``"\\1"``).
    - ``line_regex_replacements`` (list of dicts): similar to ``regex_replacements`` but
      applied to whole lines. Blocks of matching lines that follow each other
      collapse into a single ``replacement`` entry (or are removed if
      ``replacement`` is omitted).
    - ``compact_whitespace`` (bool)
    - ``compact_whitespace_groups`` (dict): optional overrides that enable or disable
      specific whitespace transformations. Supported keys are defined in
      ``COMPACT_WHITESPACE_GROUPS``.
    - ``max_lines`` (int): if greater than zero, shorten the output to this many lines.
    - ``max_tokens`` (int): if greater than zero, shorten the output to this many tokens.
    """
    if not options:
        return buffer

    if options.get('remove_initial_c_style_comment'):
        stripped = buffer.lstrip()
        if stripped.startswith('/*'):
            end_index = stripped.find('*/', 2)
            if end_index != -1:
                buffer = stripped[end_index + 2:].lstrip()

    if options.get('remove_all_c_style_comments'):
        buffer = re.sub(r'/\*.*?\*/', '', buffer, flags=re.DOTALL)

    if language and (options.get('remove_comments') or options.get('remove_single_line_comments')):
        single_only = bool(options.get('remove_single_line_comments') and not options.get('remove_comments'))
        buffer = remove_comments_by_lang(buffer, language, single_only=single_only)

    regex_rules = []
    for rule in options.get('regex_replacements', []):
        pattern = rule.get('pattern')
        replacement = rule.get('replacement')
        if pattern is None or replacement is None:
            continue
        compiled = validate_regex_pattern(
            pattern, context="processing.regex_replacements"
        )
        regex_rules.append((compiled, replacement))

    for compiled, replacement in regex_rules:
        buffer = compiled.sub(replacement, buffer)

    line_rules = options.get('line_regex_replacements')
    if line_rules:
        buffer = apply_line_regex_replacements(buffer, line_rules)

    compact_enabled = bool(options.get('compact_whitespace'))
    compact_overrides = options.get('compact_whitespace_groups')
    resolved_groups = None

    if isinstance(compact_overrides, dict):
        resolved_groups = {key: compact_enabled for key in COMPACT_WHITESPACE_GROUPS}
        recognized_override_present = False

        for key, value in compact_overrides.items():
            if key not in resolved_groups:
                continue
            recognized_override_present = True
            if value is None:
                continue
            resolved_groups[key] = bool(value)

        if recognized_override_present:
            compact_enabled = any(resolved_groups.values())
        else:
            resolved_groups = None

    if compact_enabled:
        buffer = compact_whitespace(buffer, groups=resolved_groups)

    max_lines = options.get('max_lines', 0)
    if max_lines > 0:
        lines = buffer.splitlines(keepends=True)
        if len(lines) > max_lines:
            buffer = "".join(lines[:max_lines])

    max_tokens = options.get('max_tokens', 0)
    if max_tokens > 0:
        buffer = truncate_tokens(buffer, max_tokens)

    return buffer


def detect_language_from_shebang(content: str) -> str | None:
    """Identify the language from the shebang line (for example, #!/usr/bin/env python3)."""
    if not content or not content.startswith("#!"):
        return None

    first_line = content.split('\n', 1)[0]

    # Common mappings for shebangs to language tags
    interpreters = [
        ("python", "python"),
        ("node", "javascript"),
        ("ruby", "ruby"),
        ("perl", "perl"),
        ("php", "php"),
        ("bash", "bash"),
        ("zsh", "bash"),
        ("sh", "bash"),
        ("groovy", "groovy"),
    ]

    for marker, lang in interpreters:
        if marker in first_line:
            return lang

    return None


def get_language_tag(path: str | Path, content: str | None = None, overrides: Mapping[str, str] | None = None) -> str:
    """Return a Markdown-friendly language tag for the file at ``path``.

    This function maps common extensions and filenames to their corresponding
    language identifiers for syntax highlighting. If no mapping is found and
    ``content`` is provided, it attempts to detect the language from a shebang
    line. Otherwise, it falls back to the file extension.
    """
    path = Path(path)
    name = path.name.lower()
    ext = path.suffix.lower()

    if overrides:
        # Check for full filename override first
        if name in overrides:
            return overrides[name]
        # Then check for extension with dot
        if ext in overrides:
            return overrides[ext]
        # Then check for extension without dot
        dotless_ext = ext.lstrip('.')
        if dotless_ext in overrides:
            return overrides[dotless_ext]

    if name in FILENAME_TO_LANG:
        return FILENAME_TO_LANG[name]

    if ext in EXTENSION_TO_LANG:
        return EXTENSION_TO_LANG[ext]

    # Try shebang detection for extensionless scripts or unrecognized extensions
    if content:
        shebang_lang = detect_language_from_shebang(content)
        if shebang_lang:
            return shebang_lang

    return ext.lstrip('.') or "text"


def get_all_languages() -> list[str]:
    """Return a sorted list of all unique supported language identifiers."""
    all_langs = set(EXTENSION_TO_LANG.values())
    all_langs.update(FILENAME_TO_LANG.values())
    return sorted(list(all_langs))


def count_lines(text: str) -> int:
    """Return the number of lines in the text."""
    return len(text.splitlines())


def add_line_numbers(text):
    """Prepend line numbers to each line of text."""
    lines = text.splitlines()
    numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
    if text.endswith("\n"):
        numbered.append("")
    return "\n".join(numbered)


def remove_line_numbers(text):
    """Remove line numbers from each line of text.

    This identifies lines starting with 'N: ' and removes that prefix.
    It checks if the majority of lines match this pattern to avoid
    accidental removal of content that happens to start with a number.
    """
    lines = text.splitlines()
    if not lines:
        return text

    pattern = re.compile(r"^\s*\d+:\s")
    matches = 0
    non_empty_lines = 0

    for line in lines:
        if line.strip():
            non_empty_lines += 1
            if pattern.match(line):
                matches += 1

    # If more than 50% of non-empty lines match, remove the prefix
    if non_empty_lines > 0 and (matches / non_empty_lines) > 0.5:
        # Use the compiled regex that specifically targets the 'N: ' at the start
        processed = [pattern.sub("", line) for line in lines]
        result = "\n".join(processed)
        if text.endswith("\n"):
            result += "\n"
        return result

    return text


def validate_glob_pattern(pattern, *, context="file pattern"):
    """Warn about potentially problematic search patterns."""
    if not isinstance(pattern, str):
        raise InvalidConfigError(
            f"Search pattern in {context} must be text, but got: {type(pattern).__name__}"
        )

    normalized = pattern
    if '\\' in pattern:
        logging.warning(
            "Search pattern in %s ('%s') uses backslashes; treating them as '/' for cross-platform matching.",
            context,
            pattern,
        )
        normalized = pattern.replace('\\', '/')

    normalized = re.sub(r'/+', '/', normalized)

    if Path(normalized).is_absolute():
        logging.warning(
            "Search pattern in %s ('%s') appears to be an absolute path. "
            "Patterns are matched against relative paths and filenames. This may not work as expected.",
            context,
            pattern,
        )

    if '(' in normalized or ')' in normalized or '+' in normalized:
        logging.warning(
            "File pattern in %s ('%s') contains characters that may be "
            "interpreted as advanced search syntax, but this tool uses simple search patterns. "
            "Special characters are *, ?, [].",
            context,
            pattern,
        )

    if normalized.count('[') != normalized.count(']'):
        logging.warning(
            "Search pattern in %s ('%s') has mismatched brackets '[' and ']'. "
            "This may cause unexpected matching behavior.",
            context,
            pattern,
        )

    return normalized


def validate_regex_pattern(pattern, *, context="search pattern", source=None):
    """Return a compiled search pattern after validating ``pattern``.

    Raises ``InvalidConfigError`` with a helpful message when ``pattern`` is
    invalid. ``context`` describes where the pattern originated so the error
    can guide the user to the right configuration entry.
    """

    try:
        return re.compile(pattern)
    except re.error as exc:
        location = f"Invalid search pattern in {context}"
        if source:
            location += f" (from '{source}')"
        raise InvalidConfigError(
            f"{location}: '{pattern}'. {exc}"
        ) from exc


def estimate_tokens(text: str, encoding_name: str = "cl100k_base") -> tuple[int, bool]:
    """Estimate how many tokens are in the text.

    Returns the token count and whether it is an estimate.
    """
    if tiktoken:
        try:
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text, disallowed_special=())), False
        except Exception:
            pass

    # Approx: 1 token ~= 4 chars
    return len(text) // 4, True


def truncate_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    """Shorten the text to a maximum number of tokens.

    If tiktoken is available, it uses the specified encoding to shorten accurately.
    Otherwise, it uses a character-based approximation (1 token ~= 4 characters).
    """
    if max_tokens <= 0:
        return text

    if tiktoken:
        try:
            encoding = tiktoken.get_encoding(encoding_name)
            tokens = encoding.encode(text, disallowed_special=())
            if len(tokens) <= max_tokens:
                return text
            return encoding.decode(tokens[:max_tokens])
        except Exception:
            pass

    # Fallback to character-based truncation
    # 1 token ~= 4 chars, so we take max_tokens * 4
    char_limit = max_tokens * 4
    if len(text) <= char_limit:
        return text
    return text[:char_limit]


def format_size(size_bytes: int) -> str:
    """Return the file size in an easy-to-read format such as KB or MB."""
    if size_bytes < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:,.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:,.2f} YB"


def format_tokens(count: int, is_approx: bool = False) -> str:
    """Return the token count as a string with comma separators and a leading tilde if approximate."""
    return f"{'~' if is_approx else ''}{count:,}"


def parse_time_value(value: str) -> float:
    """Convert a time such as '1h' or '2023-01-01' into a number the computer can use.

    Supports relative durations (for example, '1h', '2d', '4w') and absolute dates
    in 'YYYY-MM-DD' format.
    """
    if not value:
        return 0.0

    import time
    from datetime import datetime, timedelta

    value = value.lower().strip()

    # Try absolute date YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.timestamp()
        except ValueError:
            raise InvalidConfigError(f"Invalid date format: '{value}'. Use YYYY-MM-DD.")

    # Try relative durations
    match = re.match(r'^(\d+)([smhdw])$', value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        if unit == 's':
            delta = timedelta(seconds=amount)
        elif unit == 'm':
            delta = timedelta(minutes=amount)
        elif unit == 'h':
            delta = timedelta(hours=amount)
        elif unit == 'd':
            delta = timedelta(days=amount)
        elif unit == 'w':
            delta = timedelta(weeks=amount)
        else:
            raise InvalidConfigError(f"Unknown time unit: '{unit}' in '{value}'")

        return time.time() - delta.total_seconds()

    # Try raw number (seconds)
    if value.isdigit():
        return float(value)

    raise InvalidConfigError(
        f"Invalid time value: '{value}'. Use '1h', '2d', 'YYYY-MM-DD', or seconds."
    )


def parse_size_value(value: str) -> int:
    """Convert a human-readable size such as '10KB' or '1.5MB' into bytes.

    Supports units: B, K, KB, M, MB, G, GB, T, TB (case-insensitive).
    """
    if not value:
        return 0

    value = value.strip().upper().replace(',', '').lstrip('~').strip()
    match = re.match(r'^([\d.]+)\s*([A-Z]*)$', value)
    if not match:
        raise InvalidConfigError(f"Invalid size value: '{value}'. Use '10KB', '1.5MB', and similar units.")

    try:
        number = float(match.group(1))
    except ValueError as e:
        raise InvalidConfigError(
            f"Invalid size value: '{value}'. Use '10KB', '1.5MB', and similar units."
        ) from e
    unit = match.group(2)

    if not unit or unit == 'B':
        return int(number)

    units = {
        'K': 1024,
        'KB': 1024,
        'M': 1024**2,
        'MB': 1024**2,
        'G': 1024**3,
        'GB': 1024**3,
        'T': 1024**4,
        'TB': 1024**4,
    }

    if unit not in units:
        raise InvalidConfigError(f"Unknown size unit: '{unit}' in '{value}'")

    return int(number * units[unit])


def _format_author(author_data: Any) -> str:
    """Normalize author information into a consistent string (e.g., 'Name <email> (url)')."""
    if not author_data:
        return ""
    if isinstance(author_data, str):
        return author_data
    if isinstance(author_data, dict):
        parts = []
        if author_data.get('name'):
            parts.append(str(author_data['name']))
        if author_data.get('email'):
            parts.append(f"<{author_data['email']}>")
        if author_data.get('url'):
            parts.append(f"({author_data['url']})")
        return " ".join(parts) if parts else ""
    if isinstance(author_data, list):
        return ", ".join(filter(None, [_format_author(a) for a in author_data]))
    return str(author_data)


def _parse_json_manifest(manifest_path: Path, identity: dict) -> bool:
    """Read a JSON manifest and update identity; return True if successful."""
    if not manifest_path.is_file():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            if data.get('name'):
                identity["project_name"] = str(data['name'])
            if data.get('version'):
                identity["project_version"] = str(data['version'])
            if data.get('author'):
                identity["project_author"] = _format_author(data['author'])
            elif data.get('authors'):
                identity["project_author"] = _format_author(data['authors'])
            if data.get('description'):
                identity["project_description"] = str(data['description'])
            if data.get('license'):
                identity["project_license"] = str(data['license'])
            if data.get('homepage'):
                identity["project_url"] = str(data['homepage'])
            elif data.get('repository'):
                repo = data.get('repository')
                if isinstance(repo, dict) and repo.get('url'):
                    identity["project_url"] = str(repo['url'])
                elif isinstance(repo, str):
                    identity["project_url"] = repo
            return True
    except Exception:
        pass
    return False


def get_project_identity(root_folder: str | Path) -> dict:
    """Detect project information (name, version, author, description, license) from manifest files."""
    identity = {
        "project_name": "Project",
        "project_version": "",
        "project_author": "",
        "project_description": "",
        "project_license": "",
        "project_url": "",
        "manifest_source": None
    }

    try:
        root_path = Path(root_folder).resolve()
        identity["project_name"] = root_path.name or "Project"

        manifest_found = False
        # 1. Node.js (package.json)
        if _parse_json_manifest(root_path / "package.json", identity):
            identity["manifest_source"] = "package.json"
            manifest_found = True

        # 1.1 .NET Projects (*.csproj, *.fsproj, *.vbproj, *.sln)
        if not manifest_found:
            dotnet_projects = list(root_path.glob("*.csproj")) + \
                             list(root_path.glob("*.fsproj")) + \
                             list(root_path.glob("*.vbproj"))
            if not dotnet_projects:
                dotnet_projects = list(root_path.glob("*.sln"))

            if dotnet_projects:
                try:
                    # If it's a solution, try to find the first project file
                    target_file = dotnet_projects[0]
                    if target_file.suffix == '.sln':
                        # Heuristic: look for first project file mentioned in .sln
                        sln_content = target_file.read_text(encoding='utf-8')
                        match = re.search(r'Project\(".*"\) = ".*", "(.*\.(?:cs|fs|vb)proj)"', sln_content)
                        if match:
                            potential_proj = root_path / match.group(1).replace('\\', '/')
                            if potential_proj.is_file():
                                target_file = potential_proj

                    if target_file.suffix != '.sln':
                        content = target_file.read_text(encoding='utf-8')
                        m = re.search(r'<AssemblyName>(.*?)</AssemblyName>', content)
                        if m:
                            identity["project_name"] = m.group(1)
                        else:
                            identity["project_name"] = target_file.stem

                        m = re.search(r'<Version>(.*?)</Version>', content)
                        if m:
                            identity["project_version"] = m.group(1)

                        m = re.search(r'<Authors>(.*?)</Authors>', content)
                        if m:
                            identity["project_author"] = m.group(1)

                        m = re.search(r'<Description>(.*?)</Description>', content)
                        if m:
                            identity["project_description"] = m.group(1)

                        m = re.search(r'<PackageLicenseExpression>(.*?)</PackageLicenseExpression>', content)
                        if m:
                            identity["project_license"] = m.group(1)

                        m = re.search(r'<PackageProjectUrl>(.*?)</PackageProjectUrl>', content)
                        if m:
                            identity["project_url"] = m.group(1)

                    identity["manifest_source"] = target_file.name
                    manifest_found = True
                except Exception:
                    pass

        # 1.2 Gradle Projects (build.gradle, build.gradle.kts, settings.gradle)
        if not manifest_found:
            gradle_settings = root_path / "settings.gradle"
            if not gradle_settings.is_file():
                gradle_settings = root_path / "settings.gradle.kts"

            if gradle_settings.is_file():
                try:
                    content = gradle_settings.read_text(encoding='utf-8')
                    match = re.search(r'rootProject\.name\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        identity["project_name"] = match.group(1)

                    # Try to get project URL from settings.gradle if available (less common)
                    # or stay with default if not found.

                    # Now try to get version from build.gradle
                    gradle_build = root_path / "build.gradle"
                    if not gradle_build.is_file():
                        gradle_build = root_path / "build.gradle.kts"

                    if gradle_build.is_file():
                        build_content = gradle_build.read_text(encoding='utf-8')
                        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', build_content, re.MULTILINE)
                        if match:
                            identity["project_version"] = match.group(1)

                    identity["manifest_source"] = gradle_settings.name
                    manifest_found = True
                except Exception:
                    pass

        # 1.3 Clojure Projects (project.clj)
        if not manifest_found:
            project_clj = root_path / "project.clj"
            if project_clj.is_file():
                try:
                    content = project_clj.read_text(encoding='utf-8')
                    match = re.search(r'\(defproject\s+([^\s]+)\s+"([^"]+)"', content)
                    if match:
                        identity["project_name"] = match.group(1)
                        identity["project_version"] = match.group(2)

                        # Check for authors if possible (less standardized in project.clj)

                        m = re.search(r':description\s+"([^"]+)"', content)
                        if m:
                            identity["project_description"] = m.group(1)

                        m = re.search(r':license\s+\{:name\s+"([^"]+)"', content)
                        if m:
                            identity["project_license"] = m.group(1)

                        m = re.search(r':url\s+"([^"]+)"', content)
                        if m:
                            identity["project_url"] = m.group(1)

                    identity["manifest_source"] = "project.clj"
                    manifest_found = True
                except Exception:
                    pass

        # 1.4 CocoaPods (*.podspec)
        if not manifest_found:
            podspecs = list(root_path.glob("*.podspec"))
            if podspecs:
                try:
                    target_file = podspecs[0]
                    content = target_file.read_text(encoding='utf-8')
                    m = re.search(r'\.name\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_name"] = m.group(1)
                    m = re.search(r'\.version\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_version"] = m.group(1)
                    m = re.search(r'\.authors?\s*=\s*(.+)$', content, re.MULTILINE)
                    if m:
                        # Attempt to clean up author string (can be a dict or string)
                        author_raw = m.group(1).strip().strip('"').strip("'")
                        identity["project_author"] = author_raw
                    m = re.search(r'\.summary\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_description"] = m.group(1)
                    m = re.search(r'\.license\s*=\s*.*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_license"] = m.group(1)
                    m = re.search(r'\.homepage\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_url"] = m.group(1)
                    identity["manifest_source"] = target_file.name
                    manifest_found = True
                except Exception:
                    pass

        # 1.5 Xcode Projects (*.xcodeproj)
        if not manifest_found:
            xcodeproj = list(root_path.glob("*.xcodeproj"))
            if xcodeproj:
                identity["project_name"] = xcodeproj[0].stem
                identity["manifest_source"] = xcodeproj[0].name
                # Xcode project information is buried in pbxproj, usually easier to just take the name
                manifest_found = True

        # 2. Python (pyproject.toml)
        if not manifest_found:
            pyproject = root_path / "pyproject.toml"
            if pyproject.is_file():
                try:
                    content = pyproject.read_text(encoding='utf-8')
                    # Name
                    match = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                    if not match:
                        match = re.search(
                            r'\[project\][^\[]*name\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL
                        )
                    if match:
                        identity["project_name"] = match.group(1)

                    # Version
                    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                    if not match:
                        match = re.search(
                            r'\[project\][^\[]*version\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL
                        )
                    if match:
                        identity["project_version"] = match.group(1)

                    # Author
                    match = re.search(r'^authors\s*=\s*\[(.*?)\]', content, re.MULTILINE | re.DOTALL)
                    if not match:
                        match = re.search(r'\[project\][^\[]*authors\s*=\s*\[(.*?)\]', content, re.DOTALL)
                    if match:
                        # Very simple extraction for TOML list of dicts
                        authors_raw = match.group(1)
                        names = re.findall(r'name\s*=\s*["\']([^"\']+)["\']', authors_raw)
                        if names:
                            identity["project_author"] = ", ".join(names)

                    # Description
                    match = re.search(r'^description\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                    if not match:
                        match = re.search(
                            r'\[project\][^\[]*description\s*=\s*["\']([^"\']+)["\']',
                            content,
                            re.DOTALL,
                        )
                    if match:
                        identity["project_description"] = match.group(1)

                    # License
                    match = re.search(r'^license\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                    if not match:
                        # Support license = { text = "MIT" }
                        match = re.search(r'license\s*=\s*\{[^}]*text\s*=\s*["\']([^"\']+)["\']', content)
                    if not match:
                        # Support [project.license] text = "MIT"
                        match = re.search(
                            r'\[project\.license\][^\[]*text\s*=\s*["\']([^"\']+)["\']',
                            content,
                            re.DOTALL,
                        )
                    if match:
                        identity["project_license"] = match.group(1)

                    # Project URL
                    match = re.search(r'^urls?\s*=\s*\{[^}]*homepage\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE | re.IGNORECASE)
                    if not match:
                        match = re.search(r'\[project\.urls\][^\[]*homepage\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL | re.IGNORECASE)
                    if match:
                        identity["project_url"] = match.group(1)

                    identity["manifest_source"] = "pyproject.toml"
                    manifest_found = True
                except Exception:
                    pass

        # 3. Rust (Cargo.toml)
        if not manifest_found:
            cargo = root_path / "Cargo.toml"
            if cargo.is_file():
                try:
                    content = cargo.read_text(encoding='utf-8')
                    # [package] section
                    package_match = re.search(r'\[package\]([\s\S]*?)(?:\n\[|$)', content)
                    if package_match:
                        pkg_content = package_match.group(1)
                        m = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', pkg_content, re.MULTILINE)
                        if m:
                            identity["project_name"] = m.group(1)
                        m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', pkg_content, re.MULTILINE)
                        if m:
                            identity["project_version"] = m.group(1)
                        m = re.search(r'^authors\s*=\s*\[(.*?)\]', pkg_content, re.MULTILINE | re.DOTALL)
                        if m:
                            authors_raw = m.group(1)
                            authors = [a.strip().strip('"').strip("'") for a in authors_raw.split(',') if a.strip()]
                            identity["project_author"] = ", ".join(authors)
                        m = re.search(
                            r'^description\s*=\s*["\']([^"\']+)["\']', pkg_content, re.MULTILINE
                        )
                        if m:
                            identity["project_description"] = m.group(1)
                        m = re.search(r'^license\s*=\s*["\']([^"\']+)["\']', pkg_content, re.MULTILINE)
                        if m:
                            identity["project_license"] = m.group(1)
                        m = re.search(r'^homepage\s*=\s*["\']([^"\']+)["\']', pkg_content, re.MULTILINE)
                        if m:
                            identity["project_url"] = m.group(1)
                        elif not identity["project_url"]:
                            m = re.search(r'^repository\s*=\s*["\']([^"\']+)["\']', pkg_content, re.MULTILINE)
                            if m:
                                identity["project_url"] = m.group(1)
                    identity["manifest_source"] = "Cargo.toml"
                    manifest_found = True
                except Exception:
                    pass

        # 4. PHP (composer.json)
        if not manifest_found:
            if _parse_json_manifest(root_path / "composer.json", identity):
                identity["manifest_source"] = "composer.json"
                manifest_found = True

        # 5. Java (pom.xml)
        if not manifest_found:
            pom = root_path / "pom.xml"
            if pom.is_file():
                try:
                    content = pom.read_text(encoding='utf-8')
                    # Simplified XML parsing with regex
                    m = re.search(r'<artifactId>(.*?)</artifactId>', content)
                    if m:
                        identity["project_name"] = m.group(1)
                    m = re.search(r'<version>(.*?)</version>', content)
                    if m:
                        identity["project_version"] = m.group(1)
                    # Authors in POM are usually in <developers>
                    m = re.search(r'<developers>.*?<name>(.*?)</name>', content, re.DOTALL)
                    if m:
                        identity["project_author"] = m.group(1)
                    m = re.search(r'<description>(.*?)</description>', content)
                    if m:
                        identity["project_description"] = m.group(1)
                    # License is often in <licenses><license><name>...
                    m = re.search(r'<license>.*?<name>(.*?)</name>', content, re.DOTALL)
                    if m:
                        identity["project_license"] = m.group(1)
                    m = re.search(r'<url>(.*?)</url>', content)
                    if m:
                        identity["project_url"] = m.group(1)
                    identity["manifest_source"] = "pom.xml"
                    manifest_found = True
                except Exception:
                    pass

        # 6. Go (go.mod)
        if not manifest_found:
            gomod = root_path / "go.mod"
            if gomod.is_file():
                try:
                    content = gomod.read_text(encoding='utf-8')
                    match = re.search(r'^module\s+(.+)$', content, re.MULTILINE)
                    if match:
                        identity["project_name"] = match.group(1).strip()
                        identity["manifest_source"] = "go.mod"
                        manifest_found = True
                except Exception:
                    pass

        # 7. Ruby (Gemfile or *.gemspec)
        if not manifest_found:
            gemspecs = list(root_path.glob("*.gemspec"))
            if gemspecs:
                try:
                    target_file = gemspecs[0]
                    content = target_file.read_text(encoding='utf-8')
                    m = re.search(r'\.name\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_name"] = m.group(1)
                    m = re.search(r'\.version\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_version"] = m.group(1)
                    m = re.search(r'\.authors?\s*=\s*\[(.*?)\]', content, re.MULTILINE | re.DOTALL)
                    if m:
                        authors_raw = m.group(1)
                        authors = [a.strip().strip('"').strip("'") for a in authors_raw.split(',') if a.strip()]
                        identity["project_author"] = ", ".join(authors)
                    m = re.search(r'\.description\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_description"] = m.group(1)
                    m = re.search(r'\.license\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_license"] = m.group(1)
                    m = re.search(r'\.homepage\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_url"] = m.group(1)
                    identity["manifest_source"] = target_file.name
                    manifest_found = True
                except Exception:
                    pass

        # 8. Elixir (mix.exs)
        if not manifest_found:
            mix_exs = root_path / "mix.exs"
            if mix_exs.is_file():
                try:
                    content = mix_exs.read_text(encoding='utf-8')
                    m = re.search(r'app:\s*:([a-zA-Z0-9_]+)', content)
                    if m:
                        identity["project_name"] = m.group(1)
                    m = re.search(r'version:\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_version"] = m.group(1)
                    # Elixir authors are often in a list
                    m = re.search(r'homepage_url:\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_url"] = m.group(1)
                    identity["manifest_source"] = "mix.exs"
                    manifest_found = True
                except Exception:
                    pass

        # 9. Swift (Package.swift)
        if not manifest_found:
            package_swift = root_path / "Package.swift"
            if package_swift.is_file():
                try:
                    content = package_swift.read_text(encoding='utf-8')
                    m = re.search(r'name:\s*["\']([^"\']+)["\']', content)
                    if m:
                        identity["project_name"] = m.group(1)
                    identity["manifest_source"] = "Package.swift"
                    manifest_found = True
                except Exception:
                    pass

        # 9.1 CMake Projects (CMakeLists.txt)
        if not manifest_found:
            cmake = root_path / "CMakeLists.txt"
            if cmake.is_file():
                try:
                    content = cmake.read_text(encoding='utf-8')
                    # Match project(Name ...) with support for multi-line and various arguments
                    # Use re.IGNORECASE as CMake commands are case-insensitive
                    m = re.search(r'project\s*\(\s*([a-zA-Z0-9._-]+)', content, re.IGNORECASE)
                    if m:
                        identity["project_name"] = m.group(1)

                        # Extract VERSION
                        v_match = re.search(r'VERSION\s+([0-9.]+)', content, re.IGNORECASE)
                        if v_match:
                            identity["project_version"] = v_match.group(1)

                        # Extract DESCRIPTION
                        d_match = re.search(r'DESCRIPTION\s+["\']([^"\']+)["\']', content, re.IGNORECASE)
                        if d_match:
                            identity["project_description"] = d_match.group(1)

                        # Extract HOMEPAGE_URL
                        h_match = re.search(r'HOMEPAGE_URL\s+["\']([^"\']+)["\']', content, re.IGNORECASE)
                        if h_match:
                            identity["project_url"] = h_match.group(1)

                        identity["manifest_source"] = "CMakeLists.txt"
                        manifest_found = True
                except Exception:
                    pass

        # 9.2 Julia Projects (Project.toml)
        if not manifest_found:
            julia_project = root_path / "Project.toml"
            if julia_project.is_file():
                try:
                    content = julia_project.read_text(encoding='utf-8')
                    m = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                    if m:
                        identity["project_name"] = m.group(1)
                    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                    if m:
                        identity["project_version"] = m.group(1)
                    identity["manifest_source"] = "Project.toml"
                    manifest_found = True
                except Exception:
                    pass

        # 9.3 Deno Projects (deno.json, deno.jsonc)
        if not manifest_found:
            deno_manifest = root_path / "deno.json"
            if not deno_manifest.is_file():
                deno_manifest = root_path / "deno.jsonc"

            if deno_manifest.is_file():
                try:
                    content = deno_manifest.read_text(encoding='utf-8')
                    if deno_manifest.suffix == '.jsonc':
                        content = remove_comments_by_lang(content, 'javascript')

                    data = json.loads(content)
                    if isinstance(data, dict):
                        if data.get('name'):
                            identity["project_name"] = str(data['name'])
                        if data.get('version'):
                            identity["project_version"] = str(data['version'])
                        if data.get('author'):
                            identity["project_author"] = _format_author(data['author'])
                        elif data.get('authors'):
                            identity["project_author"] = _format_author(data['authors'])
                        if data.get('description'):
                            identity["project_description"] = str(data['description'])
                        if data.get('license'):
                            identity["project_license"] = str(data['license'])

                        identity["manifest_source"] = deno_manifest.name
                        manifest_found = True
                except Exception:
                    pass

        # 9.4 Zig Projects (build.zig.zon)
        if not manifest_found:
            zig_manifest = root_path / "build.zig.zon"
            if zig_manifest.is_file():
                try:
                    content = zig_manifest.read_text(encoding='utf-8')
                    # .name = "my-project" or .name = .my_project
                    name_match = re.search(r'\.name\s*=\s*[".]?(.*?)[",]?\s*(?:\n|,)', content)
                    if name_match:
                        identity["project_name"] = name_match.group(1).strip()

                    # .version = "1.2.3"
                    version_match = re.search(r'\.version\s*=\s*"(.*?)"', content)
                    if version_match:
                        identity["project_version"] = version_match.group(1).strip()

                    identity["manifest_source"] = "build.zig.zon"
                    manifest_found = True
                except Exception:
                    pass

        # 10. Flutter/Dart (pubspec.yaml)
        if not manifest_found:
            pubspec = root_path / "pubspec.yaml"
            if pubspec.is_file():
                try:
                    content = pubspec.read_text(encoding='utf-8')
                    m = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        identity["project_name"] = m.group(1).strip()
                    m = re.search(r'^version:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        identity["project_version"] = m.group(1).strip()
                    # authors: [Name <email>] or author: Name
                    m = re.search(r'^authors?:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        identity["project_author"] = m.group(1).strip().strip('[').strip(']')
                    m = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        identity["project_description"] = m.group(1).strip()
                    m = re.search(r'^homepage:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        identity["project_url"] = m.group(1).strip()
                    elif not identity["project_url"]:
                        m = re.search(r'^repository:\s*(.+)$', content, re.MULTILINE)
                        if m:
                            identity["project_url"] = m.group(1).strip()

                    identity["manifest_source"] = "pubspec.yaml"
                    manifest_found = True
                except Exception:
                    pass

        # 11. README Fallback
        if not manifest_found:
            readme = root_path / "README.md"
            if readme.is_file():
                try:
                    content = readme.read_text(encoding='utf-8')
                    # Try to get the first H1 (ATX style: # Name)
                    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)

                    # If not found, try Setext style (Name followed by ===)
                    if not m:
                        m = re.search(r'^([^\n]+)\n={3,}\s*$', content, re.MULTILINE)

                    if m:
                        identity["project_name"] = m.group(1).strip()
                        # Try to get the paragraph following the H1 for description
                        # We look for the first non-empty line after the H1 that isn't another header
                        remaining = content[m.end():].strip()
                        if remaining:
                            lines = remaining.splitlines()
                            for line in lines:
                                line = line.strip()
                                if line:
                                    if not line.startswith('#') and not (line.startswith('===') or line.startswith('---')):
                                        # Limit description length
                                        desc = line
                                        if len(desc) > 200:
                                            desc = desc[:197] + "..."
                                        identity["project_description"] = desc
                                    break
                except Exception:
                    pass

        # 11. Fallback: Search for LICENSE or COPYING files if author or license is still missing
        if not identity.get("project_author") or not identity.get("project_license"):
            license_files = ["LICENSE", "LICENSE.txt", "COPYING", "COPYING.txt", "LICENSE.md"]
            for f_name in license_files:
                license_file = root_path / f_name
                if license_file.is_file():
                    try:
                        content = license_file.read_text(encoding='utf-8').strip()
                        if not content:
                            continue

                        # Extract License
                        if not identity.get("project_license"):
                            # Try to extract license type from the first line
                            first_line = content.split('\n')[0].strip()
                            license_name = re.sub(r'^(The\s+)?(MIT|Apache|GPL|BSD|ISC|Mozilla|Unlicense|Zlib)\s+License.*$', r'\2', first_line, flags=re.IGNORECASE)
                            if license_name != first_line:
                                identity["project_license"] = license_name
                            elif len(first_line) < 50:
                                identity["project_license"] = first_line
                            else:
                                identity["project_license"] = f_name

                        # Extract Author from Copyright notice
                        if not identity.get("project_author"):
                            # Look for "Copyright (c) YEAR Name" or similar
                            match = re.search(r'Copyright\s+(?:\(c\)\s+)?(?:\d{4}-)?\d{4}\s+(.+)$', content, re.MULTILINE | re.IGNORECASE)
                            if match:
                                author = match.group(1).strip()
                                # Clean up common trailing punctuation or "All rights reserved"
                                author = re.split(r'\.|\s{2,}|All rights', author)[0].strip()
                                if author:
                                    identity["project_author"] = author
                        break
                    except Exception:
                        pass

    except Exception:
        pass

    return identity


def get_datetime_placeholders() -> dict:
    """Return a dictionary of current date and time values."""
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_system_info() -> dict:
    """Return environment details including OS, Python version, and architecture."""
    return {
        "os": platform.system(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "arch": platform.machine(),
    }
