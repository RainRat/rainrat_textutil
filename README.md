# SourceCombine

A versatile tool for your terminal to find, filter, and combine source code files from a project into one file (or folder). Use it to give better context to AI assistants, generate documentation, or save your work.

## Key Features

*   **Find files in many folders:** Scan many folders at once. Use Git to find files and follow your `.gitignore` rules automatically.
*   **Filtering:** Skip folders, files, or specific names using search patterns.
*   **Include Groups:** Group specific files to always include, even if you skip others.
*   **Sorting:** Sort files by name, size, date, tokens, or folder depth.
*   **Limiting:** Stop at a file limit, total tokens, total lines, or total size.
*   **In-Place Processing:** Clean up extra spaces or blank lines directly in your source files.
*   **Smart Combining:** Combine files while keeping headers and structural markers.
*   **Estimation:** See total tokens without writing any files.
*   **Configuration:** Save your settings in a `sourcecombine.yml` configuration file.

## Download the code

```bash
git clone https://github.com/RainRat/rainrat_textutil.git
cd rainrat_textutil
pip install -r requirements.txt
```

*Note: Install the optional `tiktoken` package for more accurate tokens:*

```bash
pip install tiktoken
```

### Verify it works

```bash
python sourcecombine.py --version
```

## Quick Start

Combine all Python files in the current folder into `combined_files.txt`:

```bash
python sourcecombine.py . -o combined_files.txt --include "*.py"
```

Combine all files in `src/` and `lib/`, skip the `test/` folder, and estimate tokens:

```bash
python sourcecombine.py src lib -o output/ --exclude-folder "test" --estimate-tokens
```

Prepare a project for an AI assistant (Markdown format, line numbers, and copied to clipboard):

```bash
python sourcecombine.py . --ai
```

## Configuration

The tool looks for a `sourcecombine.yml` file in the current folder or the folders you choose. Use it to set complex exclusion rules, inclusion groups, and default output paths.

See `config.template.yml` for a fully documented example.

## Terminal Options

```bash
python sourcecombine.py [TARGET ...] [OPTIONS]
```

### Targets
List one or more folders or files to search. If you do not provide any, the tool searches the current folder. If the first target is a `.yml` or `.yaml` file, the tool uses it as its configuration.

### Core Options
*   `-o` / `--output`: Save the result to a specific file or folder.
*   `--dry-run` / `-d`: Show what would happen without making changes.
*   `--verbose` / `-v`: Show detailed messages to help you find and fix problems.
*   `--config`: Use a specific configuration file.

### Filtering & Selection
*   `-i` / `--include` / `--include-file`: Include only files that match this search pattern (for example, `*.py`, `*.js`).
*   `-x` / `--exclude-file` / `--exclude`: Skip files that match this search pattern (for example, `*.log`).
*   `-X` / `--exclude-folder` / `--exclude-dir`: Skip folders that match this search pattern (for example, `node_modules`, `.git`).
*   `--grep` / `-g`: Include only files whose content matches this search pattern.
*   `--exclude-grep` / `-E`: Skip files whose content matches this search pattern.
*   `--skip-binary` / `-B`: Skip files that contain non-text data (binary files).
*   `--since` / `-S`: Include files modified since this time (for example, '1d', '2h', 'YYYY-MM-DD').
*   `--until` / `-U`: Include files modified before this time (for example, '1d', '2h', 'YYYY-MM-DD').
*   `--min-size`: Include only files larger than this size (for example, '10KB', '1MB').
*   `--max-size`: Include only files smaller than this size (for example, '10KB', '1MB').
*   `--max-depth` / `-D`: Limit folder scanning to this depth (for example, `-D 1` for root files only; 0 for no limit).
*   `--git-files` / `-G`: Use `git ls-files` to find files. This follows your `.gitignore` rules.
*   `--files-from`: Read a list of files to include from a text file (use `-` for your terminal). This skips scanning folders.

### Sorting & Limiting
*   `--sort` / `-s`: Sort files by `name`, `size`, `modified`, `tokens`, or `depth` before combining.
*   `--reverse` / `-r`: Reverse the sort order.
*   `--limit` / `-L`: Stop after finding this many files.
*   `--max-tokens` / `-M`: Stop adding files once you reach the total tokens limit.
*   `--max-total-size`: Stop adding files once you reach the total size limit (for example, '1MB').
*   `--max-total-lines`: Stop adding files once you reach the total lines limit.

### Output Options
*   `-a` / `--ai`: Enable a preset for AI assistants: Markdown format, line numbers, Table of Contents, folder tree, and skipping binary files. This also copies to your terminal's clipboard if you do not specify an output.
*   `-c` / `--clipboard`: Copy the result to your clipboard instead of creating a file.
*   `-f` / `--format`: Choose the output format (`text`, `json`, `jsonl`, `markdown`, `xml`).
*   `-m` / `--markdown`: Shortcut for `--format markdown`.
*   `-j` / `--json`: Shortcut for `--format json`.
*   `-w` / `--xml`: Shortcut for `--format xml`.
*   `-n` / `--line-numbers`: Add line numbers to each file in the output.
*   `-T` / `--toc`: Add a Table of Contents to the start of the output.
*   `-p` / `--include-tree`: Add a visual folder tree to the start of the output.
*   `--json-summary`: Save a machine-readable execution summary (file counts, tokens, time taken) in JSON format. Use `-` to print it to your terminal.

### Display & Preview
*   `--list-files` / `-l`: Show a list of all files that would be included and then stop.
*   `--tree` / `-t`: Show a visual folder tree of all included files and then stop.
*   `--estimate-tokens` / `-e`: Calculate tokens without writing any files.
    *   *Note: Slower than a dry-run because the tool must read every file.*

### Processing
*   `--compact` / `-C`: Clean up extra spaces and blank lines in the output.
*   `--max-lines`: Truncate each file to this many lines before combining.
*   `--apply-in-place`: Apply processing rules directly to your source files (WARNING: modifies your files!).
*   `--create-backups`: Create `.bak` copies of your original files when using `--apply-in-place`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` configuration file in your current folder to get started.
*   `--extract`: Rebuild your original files and folders from a combined file (like JSON, XML, or Markdown). You can read from a file, your terminal (`-`), or your clipboard. For example: `python sourcecombine.py --extract combined.json`. Filtering, sorting, and preview options are supported. Line numbers are removed automatically unless you use `--keep-line-numbers`.
*   `--keep-line-numbers`: Keep line numbers when extracting files. By default, they are automatically removed if detected.
*   `--restore`: Undo 'apply-in-place' changes by restoring original files from their `.bak` copies. This command scans your target folders recursively for backup files.
*   `--delete-backups`: Remove all `.bak` files from your target folders. Use this to clean up after you are done with `--apply-in-place`.
*   `--show-config`: Show the final combined configuration (including defaults, files, and options) and exit.
*   `--system-info`: Show details about your computer and environment.
*   `-V` / `--version`: Show the tool's version and exit.

## License

This project is licensed under the MIT License - see the `LICENSE.txt` file for details.
