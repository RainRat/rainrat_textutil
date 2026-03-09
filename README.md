# SourceCombine

A versatile tool for your terminal to find, filter, and combine source code files from a project into one file (or folder). Use it to give better context to AI assistants, generate documentation, or save your work.

## Key Features

*   **Recursion & Root Folders:** Find files in many folders at once.
*   **Filtering:** Skip folders, files, or specific names using search patterns.
*   **Include Groups:** Group specific files to always include, even if you filter others.
*   **Sorting:** Order files by name, size, modification date, token count, or folder depth.
*   **Limiting:** Stop at a specific file count, total token limit, or total file size.
*   **In-Place Processing:** Clean up extra spaces or blank lines directly in your source files.
*   **Smart Combining:** Combine files while keeping headers and structural markers.
*   **Estimation:** See the total token count without writing any files.
*   **Configuration:** Save your settings in a `sourcecombine.yml` file.

## Download the code

```bash
git clone https://github.com/RainRat/rainrat_textutil.git
cd rainrat_textutil
pip install -r requirements.txt
```

### Verify it works

```bash
python sourcecombine.py --version
```

## Quick Start

Combine all Python files in the current folder into `combined.txt`:

```bash
python sourcecombine.py . -o combined.txt --include "*.py"
```

Combine all files in `src/` and `lib/`, skip the `test/` folder, and estimate the token count:

```bash
python sourcecombine.py src lib -o output/ --exclude-folder "test" --estimate-tokens
```

## Configuration

`sourcecombine.py` looks for a `sourcecombine.yml` file in the current folder or the folders you choose. Use it to set complex exclusion rules, inclusion groups, and default output paths.

See `config.template.yml` for a fully documented example.

## Command Line Arguments

```bash
python sourcecombine.py [TARGET ...] [OPTIONS]
```

### Targets
List one or more folders or files to search. If you do not provide any, the tool uses the current folder. If the first target is a `.yml` or `.yaml` file, the tool uses it as its configuration.

### Core Options
*   `-o` / `--output`: Save the result to a specific file or folder.
*   `--dry-run` / `-d`: Show what would happen without making changes.
*   `--verbose` / `-v`: Show detailed status messages to help troubleshoot issues.
*   `--config`: Use a specific configuration file.

### Filtering & Selection
*   `-i` / `--include`: Include only files matching this search pattern (for example, `*.py`, `*.js`).
*   `-x` / `--exclude-file`: Skip files matching this search pattern (for example, `*.log`).
*   `-X` / `--exclude-folder`: Skip folders matching this search pattern (for example, `node_modules`, `.git`).
*   `--grep` / `-g`: Include only files whose content matches this search pattern.
*   `--skip-binary` / `-B`: Skip files that contain non-text data (binary files).
*   `--since` / `-S`: Include files modified since this time (for example, '1d', '2h', 'YYYY-MM-DD').
*   `--until` / `-U`: Include files modified before this time (for example, '1d', '2h', 'YYYY-MM-DD').
*   `--min-size`: Include only files larger than this size (for example, '10KB', '1MB').
*   `--max-size`: Include only files smaller than this size (for example, '10KB', '1MB').
*   `--max-depth` / `-D`: Limit folder scanning to this depth (for example, `-D 1` for root files only; 0 for no limit).
*   `--git-files` / `-G`: Use `git ls-files` to find files. This respects your `.gitignore` settings.
*   `--files-from`: Read a list of files to include from a text file (use `-` for your terminal). This skips scanning folders.

### Sorting & Limiting
*   `--sort` / `-s`: Sort files by `name`, `size`, `modified`, `tokens`, or `depth` before combining.
*   `--reverse` / `-r`: Reverse the sort order.
*   `--limit` / `-L`: Stop after finding this many files.
*   `--max-tokens` / `-M`: Stop adding files once this total token limit is reached.
*   `--max-total-size`: Stop adding files once this total size limit is reached (for example, '1MB').
*   `--max-total-lines`: Stop adding files once this total line limit is reached.

### Output Options
*   `-a` / `--ai`: Enable a preset for AI assistants: Markdown format, line numbers, Table of Contents, folder tree, and skipping binary files.
*   `-c` / `--clipboard`: Copy the result to your clipboard instead of creating a file.
*   `-f` / `--format`: Choose the output format (`text`, `json`, `jsonl`, `markdown`, `xml`).
*   `-m` / `--markdown`: Shortcut for `--format markdown`.
*   `-j` / `--json`: Shortcut for `--format json`.
*   `-w` / `--xml`: Shortcut for `--format xml`.
*   `-n` / `--line-numbers`: Add line numbers to each file in the output.
*   `-T` / `--toc`: Add a Table of Contents to the start of the output.
*   `-p` / `--include-tree`: Add a visual folder tree to the start of the output.

### Display & Preview
*   `--list-files` / `-l`: Show a list of all files that would be included and then stop.
*   `--tree` / `-t`: Show a visual folder tree of all included files and then stop.
*   `--estimate-tokens` / `-e`: Calculate token counts without writing any files.
    *   *Note: Slower than a dry-run because the tool must read every file.*

### Processing
*   `--compact` / `-C`: Clean up extra spaces and blank lines in the output.
*   `--apply-in-place`: Apply processing rules directly to your source files (WARNING: modifies your files!).
*   `--create-backups`: Create `.bak` copies of your original files when using `--apply-in-place`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` file in your current folder to get started.
*   `--extract`: Recreate original files and folders from a combined JSON, JSONL, XML, Markdown, or Text file. You can read from a file, your terminal (`-`), or your clipboard. Sorting, token estimation, filtering options (`--include`, `--exclude-file`, `--exclude-folder`), and preview options (`--list-files`, `--tree`) are supported. Extraction from structured formats (JSON, XML) automatically preserves original token counts and sizes.
*   `--restore`: Undo 'apply-in-place' changes by restoring original files from their `.bak` copies. This command scans your target folders recursively for backup files.
*   `--show-config`: Show the final combined configuration (including defaults, files, and CLI options) and exit.
*   `--system-info`: Show details about your computer and software environment.
*   `-V` / `--version`: Show the tool's version and exit.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
