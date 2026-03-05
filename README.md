# rainrat_textutil

A versatile CLI tool for searching, filtering, and combining source code files from a project into a single output file (or folder). Perfect for providing context to LLMs, generating documentation, or creating backups.

## Key Features

*   **Recursion & Root Folders:** Search recursively from multiple root folders.
*   **Filtering:** Exclude folders, files, or specific filename patterns using standard globs.
*   **Include Groups:** Define specific groups of files to always include, even if they would otherwise be filtered.
*   **Sorting:** Order files by name, size, modification date, tokens, or depth.
*   **Limiting:** Restrict output by file count, total tokens, or total file size.
*   **In-Place Processing:** Option to apply whitespace compaction and other processing directly to the source files.
*   **Smart Combining:** Option to combine files while respecting file headers and structural markers.
*   **Estimation:** Perform a dry-run or estimate token counts without writing files.
*   **Configuration:** Use a `sourcecombine.yml` file to store your project-specific settings.

## Installation

```bash
git clone https://github.com/RainRat/rainrat_textutil.git
cd rainrat_textutil
pip install -r requirements.txt
```

## Quick Start

Combine all Python files in the current folder into `combined.txt`:

```bash
python sourcecombine.py . -o combined.txt --include "*.py"
```

Combine all files in `src/` and `lib/`, excluding anything in `test/`, and estimate the total token count:

```bash
python sourcecombine.py src lib -o output/ --exclude-folder "test" --estimate-tokens
```

## Configuration

`sourcecombine.py` looks for a `sourcecombine.yml` file in the current directory or the root folders you specify. You can use this to define complex exclusion rules, inclusion groups, and default output paths.

See `config.template.yml` for a fully documented example.

## Command Line Arguments

```bash
python sourcecombine.py [TARGET ...] [OPTIONS]
```

### Targets
List one or more folders or files to search. If none are provided, the tool defaults to the current directory.

### Core Options
*   `-o` / `--output`: Path to the output file or folder.
*   `--dry-run`: Show which files would be processed without actually combining them.
*   `--verbose` / `-v`: Show detailed information about each file found and its processing status.
*   `--config`: Path to a specific configuration file.

### Search & Filtering
*   `-i` / `--include`: Glob patterns for files to include (for example, `*.py`, `*.js`).
*   `-x` / `--exclude`: Glob patterns for files to exclude.
*   `-X` / `--exclude-folder`: Folder names to skip entirely (for example, `node_modules`, `.git`, `__pycache__`).
*   `--grep` / `-g`: Only include files whose *content* matches this regular expression.

### Sorting & Limiting
*   `--sort` / `-s`: Sort files by `name`, `size`, `modified`, `tokens`, or `depth` before combining.
*   `--reverse` / `-r`: Reverse the sort order.
*   `--limit` / `-L`: Stop processing after this many files.
*   `--since` / `-S`: Include files modified since this time (for example, '1d', '2h', 'YYYY-MM-DD').
*   `--until` / `-U`: Include files modified before this time (for example, '1d', '2h', 'YYYY-MM-DD').
*   `--min-size`: Include only files larger than this size (for example, '10KB', '1MB').
*   `--max-size`: Include only files smaller than this size (for example, '10KB', '1MB').
*   `--max-depth` / `-D`: Limit folder scanning to this depth (for example, `-D 1` for root files only; 0 for no limit).
*   `--git-files` / `-G`: Use `git ls-files` to find files. This automatically respects your `.gitignore` and includes both tracked and untracked files. If the folder is not a Git repository, it falls back to standard scanning.
*   `--max-tokens` / `-M`: Stop adding files once this total token limit is reached. (Only works when combining many files into one).
*   `--max-total-size`: Stop adding files once this total size limit is reached (for example, '1MB'). (Only works when combining many files into one).
*   `--max-total-lines`: Stop adding files once this total line limit is reached. (Only when combining many files into one).
*   `--estimate-tokens` / `-e`: Calculate token counts without creating any files.
    *   *Note: Slower than a regular dry-run because it must read the file contents.*

### Display
*   `--list-files`: Print a flat list of all files that would be included.
*   `--tree`: Print a tree-style view of the project structure and included files.

### Processing
*   `--compact-whitespace`: Remove redundant blank lines and leading/trailing whitespace.
*   `--apply-in-place`: Apply whitespace compaction directly to the source files (WARNING: modifies your source files!).
*   `--create-backups`: When using `--apply-in-place`, create `.bak` copies of the original files.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
