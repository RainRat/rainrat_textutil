# rainrat_textutil

A versatile command-line utility for discovering, filtering, processing, and combining text files into various formats (JSON, XML, JSONL, CSV, or Markdown). Designed for developers and data processing, it simplifies complex file management tasks and streamlines the preparation of datasets for LLMs and other tools.

## Key Features
*   **Find files in many folders:** Scan many folders at once. Use Git to find files and follow your `.gitignore` rules automatically.
*   **Filtering:** Skip folders, files, or specific names using search patterns. You can also filter by language, file content, or Git changes.
*   **Deduplication:** Skip duplicate files by absolute path or content.
*   **Include Groups:** Group specific files to always include, even if you skip others.
*   **Pairing:** Combine related files (like source and header pairs) into their own individual output files.
*   **File Extraction:** Rebuild your original files and folders from combined files (like JSON, XML, JSONL, CSV, or Markdown). Filtering, sorting, and processing rules are supported. Batch process multiple files or entire folders. If no input is provided, the tool automatically searches for standard defaults (`combined_files.txt`, `.md`, `.json`, `.xml`, or `.jsonl`).
*   **Sorting:** Sort files by `name`, `size`, `modified`, `tokens`, `lines`, `depth`, or `language`.
*   **Flexible Outputs:** Save results to your terminal, a file (JSON, XML, JSONL, CSV, or Markdown), or copy them to your system clipboard.
*   **AI Metadata Integration:** Automatically include environment metadata (e.g., Python version, OS, timestamp, Git status) for AI context.

## Common Flags
*   `--config`: Use a custom configuration file (YAML) to manage complex tasks.
*   `--output`: Save results to a file (JSON, XML, JSONL, CSV, or Markdown) instead of the terminal.
*   `--copy`: Copy the combined output to your system clipboard.
*   `--apply-in-place`: Save each processed file's changes back to the original file (e.g., for batch replacements).
*   `--create-backups`: Create `.bak` copies of your original files when using `--apply-in-place`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` configuration file in your current folder to get started.
*   `--list-languages`: Show a list of all supported language identifiers and then stop.
*   `--extract`: Rebuild your original files and folders from combined files (like JSON, XML, JSONL, CSV, or Markdown). You can read from one or more files, folders, your terminal (`-`), or the system clipboard. If no input is provided, the tool automatically searches for standard defaults (`combined_files.txt`, `.md`, `.json`, `.xml`, or `.jsonl`). For example: `python sourcecombine.py --extract outputs/`. Filtering, sorting, and preview options are supported. Line numbers are removed automatically unless you use `--keep-line-numbers`.
*   `--verify`: Verify that files on disk match the content or hashes in combined files or manifests. For example: `python sourcecombine.py --verify combined_files.json`.
*   `--keep-line-numbers`: Keep line numbers when extracting files. By default, the tool removes them automatically if detected.
*   `--preview`: (Alias for `--dry-run`) See what files would be processed or extracted without actually writing them to disk.
*   `--clean`: (Alias for `--delete-backups`) Remove all `.bak` backup files from the current directory and its subfolders.
*   `--version`: Show the application version and exit.

## Getting Started
1.  **Clone the Repository:** `git clone https://github.com/RainRat/rainrat_textutil.git`
2.  **Install Dependencies:** `pip install -r requirements.txt`
3.  **Run the Utility:** `python sourcecombine.py [flags]`

For more details, use `python sourcecombine.py --help` or check the `config.template.yml`.
