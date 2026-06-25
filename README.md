# SourceCombine

SourceCombine is a tool for the terminal that helps you find, filter, and combine text files into a single file or folder. It supports many formats such as JSON, XML, Markdown, and CSV. It is helpful for preparing code context for AI models or managing large groups of files.

## Key Features
*   **Find files in many folders:** Scan many folders at once. Use Git to find files and follow the `.gitignore` rules automatically.
*   **Filtering:** Skip folders, files, or specific names using glob patterns. You can also filter by language, file content (using regular expressions), or Git changes.
*   **Duplicate Removal:** Skip duplicate files by path or content.
*   **Include Groups:** Group specific files to always include, even if you skip others.
*   **Pairing:** Combine related files (such as source and header pairs) into their own individual output files.
*   **File Extraction:** Rebuild the original files and folders from combined files (such as JSON, XML, JSONL, CSV, or Markdown). The tool supports filtering, sorting, and processing rules. Batch process multiple files, entire folders, or remote URLs (http/https). Without an input file, the tool automatically searches for standard defaults (`combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`).
*   **Sorting:** Sort files by `name`, `size`, `modified`, `tokens`, `lines`, `depth`, or `language`.
*   **Limiting:** Stop processing once you reach a file, token, size, or line limit.
*   **Flexible Outputs:** Save results to the terminal, a file (JSON, XML, JSONL, CSV, or Markdown), or copy them to the system clipboard.
*   **AI Context Integration:** Automatically include environment metadata (Python version, OS, Git status) and presets for AI models.

## Common Flags
*   `--config`: Use a custom configuration file (YAML). The tool automatically searches for `sourcecombine.yml`, `sourcecombine.yaml`, `config.yml`, or `config.yaml` in the current folder.
*   `--output` (`-o`): Save results to a file or folder instead of the terminal. Supports template placeholders (for example, `{{PROJECT_NAME}}_{{DATE}}.txt`).
*   `--clipboard` (`-c`): Copy the combined output to the system clipboard.
*   `--git-files` (`-G`): Use Git to find files and follow the `.gitignore` rules automatically.
*   `--extension` (`--ext`): Include only files with these extensions (for example, `py`, `js`).
*   `--exclude-extension` (`--exclude-ext`): Skip files with these extensions (for example, `log`, `tmp`).
*   `--limit` (`-L`): Stop processing once you reach this file limit.
*   `--unique` (`-u`): Skip duplicate files by absolute path or content.
*   `--ai` (`-a`): Preset for AI models (Markdown format, line numbers, Table of Contents, folder tree, project overview, skipping binary files, removing duplicates, and automatically including Git context like logs and diffs). This also copies to the system clipboard if you do not specify an output.
*   `--strip-components N`: Remove N leading components from file paths during extraction or verification.
*   `--project-name NAME`: Override the project name used in templates and reports.
*   `--project-version VERSION`: Override the project version.
*   `--project-description TEXT`: Override the project description.
*   `--project-license NAME`: Override the project license.
*   `--project-url URL`: Override the project URL.
*   `--dry-run` (`-d`): Show what would happen without making any changes.
*   `--remove-comments`: Remove both single-line and multi-line comments based on the detected language.
*   `--remove-single-line-comments`: Remove only single-line comments based on the detected language.
*   `--mirror`: Recreate the input directory structure in the output folder, applying all filtering and processing rules to each file individually.
*   `--apply-in-place`: Save processed changes back to the original source files.
*   `--create-backups`: Create `.bak` copies of original files when using `--apply-in-place`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` configuration file to get started.
*   `--extract`: Rebuild original files and folders from combined outputs (JSON, XML, JSONL, CSV, or Markdown). You can read from files, folders, remote URLs (http/https), the terminal, or clipboard. Without an input file, it searches for `combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`.
*   `--verify`: Verify that files on disk match the content or hashes in combined files or manifests. You can read from files, folders, remote URLs (http/https), the terminal, or clipboard. Without an input file, the tool searches for standard defaults (`combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`). For example: `python sourcecombine.py --verify combined_files.json`.
*   `--restore`: Undo changes made by `--apply-in-place` using `.bak` backup files.
*   `--delete-backups`: Remove all `.bak` files from the folders.
*   `--list-languages`: Show all supported language identifiers and exit.
*   `--list-placeholders`: Show all supported template placeholders and exit.
*   `--project-info`: Show detected project metadata and Git information for the current project.
*   `--show-config`: Display the final configuration being used and exit.
*   `--export-config`: Save the final combined configuration to a YAML file and exit.
*   `--system-info`: Show environment details (Python version, OS, and other system details).
*   `--preview`: (Alias for `--dry-run`) See what files would be processed or extracted without actually writing them to disk.
*   `--clean`: (Alias for `--delete-backups`) Remove all `.bak` backup files from the current directory and its subfolders.
*   `--version`: Show the application version and exit.

## Prerequisites
*   **Python 3.10 or newer:** Use this version or newer for modern Python features.

### Standard Dependencies
The tool installs these automatically when you follow the installation steps:
*   **PyYAML:** Loads and validates configuration files.
*   **charset-normalizer:** Detects character encodings in files.
*   **tqdm:** Displays progress bars during scanning and processing.
*   **pyperclip:** Copies output directly to the system clipboard.

### Optional Dependencies
*   **tiktoken:** Provides accurate token counting. Without it, the tool uses a character-based estimate (1 token is approximately 4 characters).

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

## Usage Examples
### Basic Combination
Combine all files in the current directory into `combined_files.txt`:
```bash
python sourcecombine.py
```

### Filtering by Language
Combine only Python and JavaScript files from the `src` folder:
```bash
python sourcecombine.py src/ --language python --language javascript --output project_context.txt
```

### File Extraction
Rebuild the original project structure from a combined Markdown file:
```bash
python sourcecombine.py --extract combined_files.md --output restored_project/
```

### AI Model Context
Prepare a comprehensive project context for AI models (includes line numbers, tree view, and automatically copies to the system clipboard):
```bash
python sourcecombine.py src/ --ai
```

### File Pairing
Combine related files (such as `.cpp` and `.h` pairs) into their own individual combined files in a separate folder:
```bash
python sourcecombine.py src/ --pair .cpp .h --output combined_src/
```

## Template Customization
You can customize the output by using templates in the configuration file. Templates support placeholders that are replaced with actual data when the tool runs. Both file-level and global templates support all project-level and Git placeholders.

### File-Level Placeholders
Used in `header_template` and `footer_template`:
*   `{{FILENAME}}`: Full relative path to the file.
*   `{{EXT}}`: File extension (for example, `py`).
*   `{{STEM}}`: Filename without extension (for example, `main`).
*   `{{DIR}}`: Folder path containing the file.
*   `{{DIR_SLUG}}`: A version of the folder path safe for use in filenames.
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
*   `{{PROJECT_NAME}}`: Name of the project (detected from `package.json`, `pyproject.toml`, `Cargo.toml`, `composer.json`, `pom.xml`, `go.mod`, `*.gemspec`, `mix.exs`, `Package.swift`, `.csproj`, `.fsproj`, `.vbproj`, `.sln`, `settings.gradle`, `project.clj`, `.podspec`, `.xcodeproj`, `README.md`, or folder name).
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
*   `{{DIR}}`: Folder path containing the pair.
*   `{{DIR_SLUG}}`: A version of the folder path safe for use in filenames.
*   `{{LANG}}`: Detected language tag of the pair (for example, `cpp`).
*   `{{INDEX}}`: The current pair's position in the list (1, 2, 3...).
*   `{{TOTAL}}`: The total number of pairs being processed.
