# rainrat_textutil

A versatile command-line utility for discovering, filtering, processing, and combining text files into various formats (JSON, XML, JSONL, CSV, or Markdown). Designed for developers and data processing, it simplifies complex file management tasks and streamlines the preparation of datasets for LLMs and other tools.

## Key Features
*   **Find files in many folders:** Scan many folders at once. Use Git to find files and follow your `.gitignore` rules automatically.
*   **Filtering:** Skip folders, files, or specific names using search patterns. You can also filter by language, file content, or Git changes.
*   **Deduplication:** Skip duplicate files by absolute path or content.
*   **Include Groups:** Group specific files to always include, even if you skip others.
*   **Pairing:** Combine related files (like source and header pairs) into their own individual output files.
*   **File Extraction:** Rebuild your original files and folders from combined files (like JSON, XML, JSONL, CSV, or Markdown). Filtering, sorting, and processing rules are supported. Batch process multiple files or entire folders. If no input is provided, the tool automatically searches for standard defaults (`combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, or `combined_files.jsonl`).
*   **Sorting:** Sort files by `name`, `size`, `modified`, `tokens`, `lines`, `depth`, or `language`.
*   **Flexible Outputs:** Save results to your terminal, a file (JSON, XML, JSONL, CSV, or Markdown), or copy them to your system clipboard.
*   **AI Context Integration:** Automatically include environment metadata (Python version, OS, Git status) and presets for LLMs.

## Common Flags
*   `--config`: Use a custom configuration file (YAML). The tool automatically searches for `sourcecombine.yml`, `sourcecombine.yaml`, `config.yml`, or `config.yaml` in your current folder.
*   `--output` (`-o`): Save results to a file or folder instead of the terminal.
*   `--clipboard` (`-c`): Copy the combined output to your system clipboard.
*   `--ai` (`-a`): Preset for AI assistants (Markdown, line numbers, TOC, and project overview).
*   `--dry-run` (`-d`): Show what would happen without making any changes.
*   `--apply-in-place`: Save processed changes back to the original source files.
*   `--create-backups`: Create `.bak` copies of original files when using `--apply-in-place`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` configuration file to get started.
*   `--extract`: Rebuild original files and folders from combined outputs (JSON, XML, JSONL, CSV, or Markdown). If no input is provided, it searches for `combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, or `combined_files.jsonl`.
*   `--restore`: Undo changes made by `--apply-in-place` using `.bak` backup files.
*   `--delete-backups`: Remove all `.bak` files from your folders.
*   `--list-languages`: Show all supported language identifiers.
*   `--show-config`: Display the final configuration being used.
*   `--system-info`: Show environment details (Python version, OS, etc.).
*   `--version`: Show the application version and exit.

## Getting Started
1.  **Clone the Repository:** `git clone https://github.com/RainRat/rainrat_textutil.git`
2.  **Install Dependencies:** `pip install -r requirements.txt`
3.  **Run the Utility:** `python sourcecombine.py [flags]`
4.  **Configure (Optional):** Run `python sourcecombine.py --init` to create a configuration file.

For more details, use `python sourcecombine.py --help` or check `config.template.yml`.
