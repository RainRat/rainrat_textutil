# SourceCombine

SourceCombine is a tool for the terminal that helps you find, filter, and combine text files into a single file or folder. It supports many formats such as JSON, XML, Markdown, and CSV. It is helpful for preparing code context for AI models or managing large groups of files.

## Key Features
*   **Find files in many folders:** Scan many folders at once. Use Git to find files and follow the `.gitignore` rules automatically.
*   **Filtering:** Skip folders, files, or specific names using glob patterns. You can also filter by language, file content (using regular expressions), or Git changes.
*   **Deduplication:** Skip duplicate files by absolute path or content.
*   **Include Groups:** Group specific files to always include, even if you skip others.
*   **Pairing:** Combine related files (such as source and header pairs) into their own individual output files.
*   **File Extraction:** Rebuild the original files and folders from combined files (such as JSON, XML, JSONL, CSV, or Markdown). Filtering, sorting, and processing rules are supported. Batch process multiple files or entire folders. Without an input file, the tool automatically searches for standard defaults (`combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`).
*   **Sorting:** Sort files by `name`, `size`, `modified`, `tokens`, `lines`, `depth`, or `language`.
*   **Limiting:** Stop processing once you reach a file, token, size, or line limit.
*   **Flexible Outputs:** Save results to the terminal, a file (JSON, XML, JSONL, CSV, or Markdown), or copy them to the system clipboard.
*   **AI Context Integration:** Automatically include environment metadata (Python version, OS, Git status) and presets for AI models.

## Common Flags
*   `--config`: Use a custom configuration file (YAML). The tool automatically searches for `sourcecombine.yml`, `sourcecombine.yaml`, `config.yml`, or `config.yaml` in the current folder.
*   `--output` (`-o`): Save results to a file or folder instead of the terminal. Supports template placeholders (for example, `{{PROJECT_NAME}}_{{DATE}}.txt`).
*   `--clipboard` (`-c`): Copy the combined output to the system clipboard.
*   `--git-files` (`-G`): Use Git to find files and follow the `.gitignore` rules automatically.
*   `--limit` (`-L`): Stop processing once you reach this file limit.
*   `--ai` (`-a`): Preset for AI models (Markdown format, line numbers, Table of Contents, folder tree, project overview, and skipping binary files). This also copies to the system clipboard if you do not specify an output.
*   `--dry-run` (`-d`): Show what would happen without making any changes.
*   `--mirror`: Recreate the input directory structure in the output folder, applying all filtering and processing rules to each file individually.
*   `--apply-in-place`: Save processed changes back to the original source files.
*   `--create-backups`: Create `.bak` copies of original files when using `--apply-in-place`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` configuration file to get started.
*   `--extract`: Rebuild original files and folders from combined outputs (JSON, XML, JSONL, CSV, or Markdown). You can read from files, folders, the terminal, or clipboard. Without an input file, it searches for `combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`.
*   `--verify`: Verify that files on disk match the content or hashes in combined files or manifests. Without an input file, the tool searches for standard defaults (`combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`). For example: `python sourcecombine.py --verify combined_files.json`.
*   `--restore`: Undo changes made by `--apply-in-place` using `.bak` backup files.
*   `--delete-backups`: Remove all `.bak` files from the folders.
*   `--list-languages`: Show all supported language identifiers.
*   `--list-placeholders`: Show all supported template placeholders and then stop.
*   `--show-config`: Display the final configuration being used.
*   `--export-config`: Save the final combined configuration to a YAML file.
*   `--system-info`: Show environment details (Python version, OS, and other system details).
*   `--preview`: (Alias for `--dry-run`) See what files would be processed or extracted without actually writing them to disk.
*   `--clean`: (Alias for `--delete-backups`) Remove all `.bak` backup files from the current directory and its subfolders.
*   `--version`: Show the application version and exit.

## Prerequisites
*   **Python 3.10 or newer:** This tool uses modern Python features.
*   **PyYAML:** Required for loading configuration files.
*   **charset-normalizer:** Required for detecting file encodings.
*   **tiktoken (optional):** Install this for accurate token counting. If not installed, the tool uses a character-based estimate (1 token ≈ 4 characters).
*   **tqdm (optional):** Install this to see progress bars while the tool scans and processes files.
*   **pyperclip (optional):** Install this to enable copying output directly to the system clipboard.

## Getting Started
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/RainRat/rainrat_textutil.git
    cd rainrat_textutil
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Optional)* Install `tiktoken` for accurate token counting:
    ```bash
    pip install tiktoken
    ```
3.  **Run the Tool:**
    ```bash
    python sourcecombine.py src/ --output combined.txt
    ```
4.  **Create a Config (Optional):**
    ```bash
    python sourcecombine.py --init
    ```
    This command creates a `sourcecombine.yml` file with default settings to help you get started.

For more details, use `python sourcecombine.py --help` or check `config.template.yml`.

## Template Customization
You can customize the output by using templates in the configuration file. Templates support placeholders that are replaced with actual data when the tool runs. All project-level and Git placeholders are available in both file-level and global templates.

### File-Level Placeholders
Used in `header_template` and `footer_template`:
*   `{{FILENAME}}`: Full relative path to the file.
*   `{{EXT}}`: File extension (for example, `py`).
*   `{{STEM}}`: Filename without extension (for example, `main`).
*   `{{DIR}}`: Folder path containing the file.
*   `{{DIR_SLUG}}`: A filesystem-safe version of the folder path.
*   `{{LANG}}`: Detected language tag (for example, `python`, `cpp`).
*   `{{SIZE}}`: Human-readable file size.
*   `{{TOKENS}}`: Number of tokens in the file.
*   `{{LINE_COUNT}}`: Number of lines in the file.
*   `{{HASH}}`: SHA-256 hash of the file content.
*   `{{INDEX}}`: The current file's position in the list (1, 2, 3...).
*   `{{TOTAL}}`: The total number of files being processed.
*   `{{MODIFIED}}`: Last modified date and time.
*   `{{FILE_AUTHOR}}`: Last author of the file according to Git.
*   `{{FILE_AUTHOR_DATE}}`: Last commit date of the file according to Git.
*   `{{FILE_LOG}}`: Subject of the last commit for the file according to Git.
*   `{{GIT_STATUS}}`: Summary of working tree changes (for example, "2 modified, 1 added").
*   `{{OS}}`, `{{PYTHON_VERSION}}`, `{{PLATFORM}}`, `{{ARCH}}`: System and environment metadata.
*   `{{ENV:VAR_NAME}}`: Value of an environment variable.
*   `{{SIZE_PERCENT}}`, `{{TOKEN_PERCENT}}`, `{{LINE_PERCENT}}`: Percentage of the total project.
*   `{{FILE_URL}}`: Direct web link to the specific file and commit.
*   `{{FILE_DIFF}}`: Changes specific to the current file (requires `--include-diff` flag).
*   `{{FILE_STATUS}}`: Git status of the current file (for example, `M`, `A`, `??`).

### Project-Level Placeholders
Used in `global_header_template`, `global_footer_template`, and other project-wide settings:
*   `{{PROJECT_NAME}}`: Name of the project (detected from `package.json`, `pyproject.toml`, or folder name).
*   `{{PROJECT_VERSION}}`: Version of the project.
*   `{{PROJECT_DESCRIPTION}}`: Short description of the project.
*   `{{PROJECT_LICENSE}}`: License identifier of the project.
*   `{{FILE_COUNT}}`: Total number of files included.
*   `{{TOTAL_SIZE}}`: Total size of all files.
*   `{{TOTAL_TOKENS}}`: Total number of tokens.
*   `{{TOTAL_LINES}}`: Total number of lines.
*   `{{DATE}}`, `{{TIME}}`, `{{DATETIME}}`: Current date and time.
*   `{{OS}}`, `{{PYTHON_VERSION}}`, `{{PLATFORM}}`, `{{ARCH}}`: System and environment metadata.
*   `{{ENV:VAR_NAME}}`: Value of an environment variable.
*   `{{GIT_STATUS}}`: Summary of working tree changes (for example, "2 modified, 1 added").
*   `{{GIT_REMOTE_URL}}`: The repository's origin remote URL.
*   `{{PROJECT_URL}}`: Web URL to the repository home (supports GitHub, GitLab, Bitbucket).

### Git Placeholders
These require a Git repository to function:
*   `{{GIT_BRANCH}}`: Current branch name.
*   `{{GIT_COMMIT}}`, `{{GIT_COMMIT_SHORT}}`: Full or short commit hash.
*   `{{GIT_AUTHOR}}`: Author of the latest commit in the project.
*   `{{GIT_TAG}}`: Latest Git tag in the project.
*   `{{GIT_AUTHOR_DATE}}`: Date of the latest commit in the project.
*   `{{GIT_STATUS}}`: Summary of working tree changes (for example, "2 modified, 1 added").
*   `{{GIT_LOG}}`: Recent commit messages (requires `--git-log` flag).
*   `{{GIT_DIFF}}`: Project-wide changes (requires `--include-diff` flag).

### Pairing Placeholders
Used in `paired_filename_template`. Supports all project-level, system, and Git placeholders, plus:
*   `{{STEM}}`: Base filename shared by the pair.
*   `{{SOURCE_EXT}}`: Extension of the source file (for example, `.cpp`).
*   `{{HEADER_EXT}}`: Extension of the header file (for example, `.h`).
*   `{{LANG}}`: Detected language of the pair (for example, `cpp`).
*   `{{INDEX}}`: The current pair's position in the list (1, 2, 3...).
*   `{{TOTAL}}`: The total number of pairs being processed.
*   `{{DIR}}`, `{{DIR_SLUG}}`: Relative folder path.
