# SourceCombine

A versatile tool for your terminal to find, filter, and combine source code files from a project into one file (or folder). Use it to give better context to AI assistants, generate documentation, or save your work.

## Key Features

*   **Find files in many folders:** Scan many folders at once. Use Git to find files and follow your `.gitignore` rules automatically.
*   **Filtering:** Skip folders, files, or specific names using search patterns. You can also filter by language, file content, or Git changes.
*   **Include Groups:** Group specific files to always include, even if you skip others.
*   **Pairing:** Combine related files (like source and header pairs) into their own individual output files.
*   **File Extraction:** Rebuild your original files and folders from combined files (like JSON, XML, or Markdown). Batch process multiple files or entire folders.
*   **Sorting:** Sort files by `name`, `size`, `modified`, `tokens`, `depth`, or `language`.
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

Combine related source and header pairs (like `.cpp` and `.h`) into an `outputs/` folder:

```bash
python sourcecombine.py src/ -o outputs/ --config example_cpp_h.yml
```

## Configuration

The tool looks for a `sourcecombine.yml` file in the current folder or the folders you choose. Use it to set complex exclusion rules, inclusion groups, and default output paths.

See `config.template.yml` for a fully documented example.

## Custom Templates

You can customize the output by using templates in your configuration file. Templates use placeholders in double curly braces (for example, `{{FILENAME}}`) that the tool replaces with actual data.

### File Templates
Used in `header_template` and `footer_template` for each file:
*   `{{FILENAME}}`: The relative path to the file (for example, `src/main.py`).
*   `{{EXT}}`: The file extension (for example, `py`).
*   `{{STEM}}`: The filename without its extension (for example, `main` from `main.py`).
*   `{{DIR}}`: The relative folder path (or `.` for the root folder).
*   `{{DIR_SLUG}}`: A simplified version of the folder path (`root` when `DIR` is `.`).
*   `{{LANG}}`: The language identifier for syntax highlighting (for example, `python`).
*   `{{SIZE}}`: The human-readable file size (for example, `1.5KB`).
*   `{{TOKENS}}`: The number of tokens in the file.
*   `{{LINE_COUNT}}`: The number of lines in the file.
*   `{{MODIFIED}}`: The last modified time in ISO 8601 format.

### Project Templates
Used in `global_header_template` and `global_footer_template` for the whole project:
*   `{{FILE_COUNT}}`: The total number of files included.
*   `{{TOTAL_SIZE}}`: The combined size of all files in a human-readable format.
*   `{{TOTAL_TOKENS}}`: The total number of tokens across all included files.
*   `{{TOTAL_LINES}}`: The total number of lines across all included files.

### Pairing Templates
Used in `paired_filename_template` when combining related files:
*   `{{STEM}}`: The base name shared by the pair (for example, `main` from `main.cpp`).
*   `{{SOURCE_EXT}}`: The extension of the source file (for example, `.cpp`).
*   `{{HEADER_EXT}}`: The extension of the header file (for example, `.h`).
*   `{{DIR}}`: The relative folder path.
*   `{{DIR_SLUG}}`: A simplified folder name.

## Terminal Options

```bash
python sourcecombine.py [TARGET ...] [OPTIONS]
```

### Targets
List one or more folders or files to search. If you do not provide any, the tool searches the current folder. If the first target is a `.yml` or `.yaml` file, the tool uses it as its configuration.

### Core Options
*   `-o` / `--output`: Save the result to a specific file or folder. This takes priority over the path in your settings.
*   `--dry-run` / `-d`: Show what would happen without making changes.
*   `--verbose` / `-v`: Show detailed status messages to help find and fix problems.
*   `--config` / `-k`: Use a specific configuration file. This stops the tool from trying to find one automatically in your target list.

### Filtering & Selection
*   `-i` / `--include` / `--include-file`: Include only files that match this search pattern (for example, `*.py`, `*.js`).
*   `--language` / `--lang`: Include only files of these languages (for example, `python`, `cpp`). Use this option again to include more. See `--list-languages` for a full list.
*   `--exclude-language` / `--exclude-lang`: Skip files of these languages (for example, `javascript`, `html`). Use this option again to skip more.
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
*   `--git-diff [REF]`: Include only files that have changed in Git. If you provide a REF (like `main`), it finds changes since that commit. Otherwise, it finds unstaged, staged, and untracked changes.
*   `--map-lang EXTENSION LANGUAGE`: Manually map a file extension or filename to a specific language (for example, `.mjml` `html`). Use this option again to add more.
*   `--files-from`: Read a list of files from a text file (use '-' for your terminal). This skips looking for files in folders.

### Sorting & Limiting
*   `--sort` / `-s`: Sort files by name, size, date (modified), tokens, folder depth, or language before combining.
*   `--reverse` / `-r`: Reverse the sort order.
*   `--limit` / `-L`: Stop adding files once you reach this limit.
*   `--max-tokens` / `-M`: Stop adding files once you reach the total tokens limit (only when combining many files into one).
*   `--max-total-size`: Stop adding files once you reach the total size limit (for example, '5MB') (only when combining many files into one).
*   `--max-total-lines`: Stop adding files once you reach the total lines limit (only when combining many files into one).

### Output Options
*   `-a` / `--ai`: Enable a preset for AI assistants: Markdown format, line numbers, Table of Contents, folder tree, and skipping binary files. This also copies to your terminal's clipboard if you do not specify an output.
*   `--clipboard` / `-c`: Copy the combined text to the clipboard instead of creating a file (only when combining many files into one).
*   `--format` / `-f`: Choose the output format ('text', 'json', 'jsonl', 'markdown', 'xml'). 'json' and 'jsonl' only work when combining many files into one.
*   `-m` / `--markdown`: Shortcut for `--format markdown`.
*   `-j` / `--json`: Shortcut for `--format json`.
*   `-w` / `--xml`: Shortcut for `--format xml`.
*   `--line-numbers` / `-n`: Add line numbers to the beginning of each line in the combined output.
*   `--toc` / `-T`: Add a Table of Contents with sizes and tokens to the start of the output (only when combining many files into one in 'text' or 'markdown' formats).
*   `--include-tree` / `-p`: Include a visual folder tree with details at the start of the output (only when combining many files into one).
*   `--json-summary`: Save a machine-readable execution summary (file counts, tokens, time taken) in JSON format. Use `-` to print it to your terminal.

### Display & Preview
*   `--list-files` / `-l`: Show a list of all files that would be included and then stop.
*   `--tree` / `-t`: Show a visual folder tree of all included files with details and then stop.
*   `--diff`: Show a colored diff of changes (only when using `--apply-in-place` or `--extract`).
*   `--estimate-tokens` / `-e`: Calculate tokens without writing any files.
    *   *Note: Slower than a dry-run because the tool must read every file.*

### Processing
*   `--compact` / `-C`: Clean up extra spaces and blank lines in the output.
*   `--max-lines`: Truncate each file to this many lines before combining.
*   `--replace PATTERN REPLACEMENT`: Add a global search-and-replace rule using regular expressions. Use this option again to add more.
*   `--replace-line PATTERN REPLACEMENT`: Add a line-based search-and-replace rule. Matching lines that follow each other collapse into a single replacement.
*   `--apply-in-place`: Apply processing rules directly to your source files (WARNING: modifies your files!).
*   `--create-backups`: Create `.bak` copies of your original files when using `--apply-in-place`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` configuration file in your current folder to get started.
*   `--list-languages`: Show a list of all supported language identifiers and then stop.
*   `--extract`: Rebuild your original files and folders from combined files (like JSON, XML, or Markdown). You can read from one or more files, folders, your terminal (`-`), or your clipboard. For example: `python sourcecombine.py --extract outputs/`. Filtering, sorting, and preview options are supported. Line numbers are removed automatically unless you use `--keep-line-numbers`.
*   `--keep-line-numbers`: Keep line numbers when extracting files. By default, the tool removes them automatically if detected.
*   `--restore`: Undo 'apply-in-place' changes by restoring original files from their `.bak` copies. This command scans your target folders recursively for backup files.
*   `--delete-backups`: Remove all `.bak` files from your target folders. Use this to clean up after you are done with `--apply-in-place`.
*   `--show-config`: Show the final combined configuration (including defaults, files, and options) and exit.
*   `--system-info`: Show details about your computer and environment.
*   `-V` / `--version`: Show the tool's version and exit.

## License

This project is licensed under the MIT License - see the `LICENSE.txt` file for details.
