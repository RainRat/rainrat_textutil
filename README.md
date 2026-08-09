# SourceCombine

SourceCombine is a tool for the terminal that helps you find, filter, and combine text files into a single file or folder. It supports many formats such as JSON, XML, Markdown, and CSV. It is helpful for preparing code context for AI models or managing large groups of files.

## Key Features
*   **Scan Folders:** Search multiple folders at once. Use Git to find files and follow `.gitignore` rules.
*   **Filter Content:** Skip folders and files by name, extension, language, content, or Git changes.
*   **Remove Duplicates:** Skip duplicate files by path or content.
*   **Include Groups:** Keep specific files regardless of other filters.
*   **Pair Files:** Link related files (like `.cpp` and `.h`) into single output files.
*   **Restore Files:** Rebuild original files and folders from combined Text, JSON, JSONL, XML, CSV, or Markdown. Supports filtering, remote URLs, and auto-detecting defaults.
*   **Safe Backups:** Manually back up matching source files before making external edits, inspect backups using diffs, and restore files from their `.bak` copies.
*   **Sort Results:** Organize files by name, size, date, tokens, lines, depth, or language.
*   **Apply Limits:** Stop processing when reaching file, token, size, or line limits.
*   **Choose Output:** Save to the terminal, a file, or the system clipboard.
*   **Collapsible Blocks:** Wrap each file's markdown block in a collapsible HTML `<details>` and `<summary>` element.
*   **AI Integration:** Include system info and Git context automatically with the `--ai` preset.

## Common Flags
*   `--config` (`-k`): Use a custom configuration file (YAML or JSON). The tool automatically searches for `sourcecombine.yml`, `sourcecombine.yaml`, `sourcecombine.json`, `config.yml`, `config.yaml`, or `config.json` in the current folder.
*   `--output` (`-o`): Save results to a file or folder instead of the terminal. Supports template placeholders (for example, `{{PROJECT_NAME}}_{{DATE}}.txt`).
*   `--clipboard` (`-c`): Copy the combined output to the system clipboard.
*   `--git-files` (`-G`): Use Git to find files and follow the `.gitignore` rules automatically.
*   `--ignore-file PATH`: Add an ignore file containing glob patterns to skip. Supports comma-separated lists (for example, `.ignore1,.ignore2`). Default is `.sourcecombineignore`.
*   `--extension` (`--ext`): Include only files with these extensions. You can repeat this flag or use a comma-separated list (for example, `--ext py,js` or `--ext py --ext js`).
*   `--exclude-extension` (`--exclude-ext`): Skip files with these extensions. Supports comma-separated lists (for example, `--exclude-ext log,tmp`).
*   `--limit` (`-L`): Stop processing once you reach this file limit.
*   `--unique` (`-u`): Skip duplicate files by path or content (duplicate removal).
*   `--ai` (`-a`): Preset for AI models (Markdown format, line numbers, Table of Contents, folder tree, project overview, skipping binary files, removing duplicates, and automatically including Git context like logs and diffs). This also copies to the system clipboard if you do not specify an output.
*   `--analyze` (`-A`): Perform a comprehensive project analysis (token counts, line counts, language breakdown, and folder tree) without generating output files.
*   `--strip-components N`: Remove N leading components from file paths during extraction or verification.
*   `--project-name NAME`: Override the project name used in templates and reports.
*   `--project-version VERSION`: Override the project version.
*   `--project-author NAME`: Override the project author.
*   `--project-description TEXT`: Override the project description.
*   `--project-license NAME`: Override the project license.
*   `--project-url URL`: Override the project URL.
*   `--dry-run` (`-d`): Show what would happen without making any changes.
*   `--remove-comments` (`-R`): Remove both single-line and multi-line comments based on the detected language.
*   `--remove-single-line-comments`: Remove only single-line comments based on the detected language.
*   `--mirror`: Recreate the input directory structure in the output folder, applying all filtering and processing rules to each file individually.
*   `--no-content` (`-N`): Skip the actual file content in the output, while preserving templates, information, and structured components like the Table of Contents and Tree View.
*   `--collapsible`: Wrap each file's markdown code block in collapsible HTML `<details>` and `<summary>` tags.
*   `--apply-in-place`: Save processed changes back to the original source files.
*   `--create-backups`: Create `.bak` copies of original files when using `--apply-in-place`, `--extract`, or `--repair`.

### Utility Commands
*   `--init`: Create a basic `sourcecombine.yml` configuration file to get started.
*   `--extract`: Rebuild original files and folders from combined outputs (Text, JSON, XML, JSONL, CSV, or Markdown). You can read from files, folders, remote URLs (http/https), the terminal, or clipboard. Without an input file, it searches for `combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`.
*   `--verify` (`-y`): Verify that files on disk match the content or hashes in combined files or manifests. You can read from files, folders, remote URLs (http/https), the terminal, or clipboard. Without an input file, the tool searches for standard defaults (`combined_files.txt`, `combined_files.md`, `combined_files.json`, `combined_files.xml`, `combined_files.jsonl`, or `combined_files.csv`). For example: `python sourcecombine.py --verify combined_files.json`. Use `--json` for machine-readable output.
*   `--repair` (`-P`): Automatically fix mismatched or missing files when verifying (requires source content).
*   `--backup`: Manually create `.bak` backup files of original files that match the active search configuration and filters. Supports `--json` for machine-readable output and `--dry-run` for previewing.
*   `--restore`: Undo changes made by `--apply-in-place` using `.bak` backup files.
*   `--delete-backups`: Remove all `.bak` files from the folders.
*   `--list-backups`: List all `.bak` backup files in target folders along with their statuses relative to original files. Use `--json` for machine-readable output.
*   `--diff-backups`: Show a unified diff between current files on disk and their `.bak` backup files. Use `--json` for machine-readable output.
*   `--list-languages`: Show all supported language identifiers and exit. Use `--json` for machine-readable output.
*   `--list-placeholders`: Show all supported template placeholders and exit. Use `--json` for machine-readable output.
*   `--project-info` (`-I`): Show detected project information and Git information for the current project. Use `--json` for machine-readable output.
*   `--explain PATH`: Analyze and explain whether the specified path(s) would be included or excluded by the current configuration and filters. Supports `--json` format.
*   `--show-config`: Display the final configuration being used and exit. Use `--json` for machine-readable output.
*   `--export-config`: Save the final combined configuration to a YAML file and exit.
*   `--system-info`: Show environment details (Python version, OS, and other system details). Use `--json` for machine-readable output.
*   `--preview`: (Alias for `--dry-run`) See what files would be processed or extracted without actually writing them to disk.
*   `--analyze` (`-A`): Perform a comprehensive project analysis without generating output files. Shortcut for `--dry-run --estimate-tokens --overview --include-tree --tree`.
*   `--clean`: (Alias for `--delete-backups`) Remove all `.bak` backup files from the current directory and its subfolders.
*   `--version` (`-V`): Show the application version and exit.

## Prerequisites
*   **Python 3.10 or newer:** The tool requires this version or newer to run.

### Standard Dependencies
The tool installs these automatically when you follow the installation steps:
*   **PyYAML:** Loads and validates configuration files.
*   **charset-normalizer:** Detects character encodings in files.
*   **tqdm:** Displays progress bars during scanning and processing.
*   **pyperclip:** Copies output directly to the system clipboard.
    *   *Note for Linux users:* You must install external clipboard tools to use the clipboard features. Install `xclip` or `xsel` for X11 environments, or `wl-clipboard` for Wayland environments.

### Optional Dependencies
*   **tiktoken:** Provides accurate token counting. Without it, the tool uses a character-based estimate (1 token is approximately 4 characters).

## Getting Started
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/RainRat/rainrat_textutil.git
    cd rainrat_textutil
    ```
2.  **Set Up a Virtual Environment (Recommended):**
    Creating a virtual environment keeps your project dependencies separate and avoids conflicts with other Python packages on your computer.

    *   **macOS / Linux:**
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    *   **Windows (Command Prompt):**
        ```cmd
        python -m venv .venv
        .venv\Scripts\activate.bat
        ```
    *   **Windows (PowerShell):**
        ```powershell
        python -m venv .venv
        .venv\Scripts\Activate.ps1
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Optional)* Install `tiktoken` for accurate token counting:
    ```bash
    pip install tiktoken
    ```
4.  **Run the Tool:**
    ```bash
    python sourcecombine.py src/ --output combined.txt
    ```
5.  **Create a Config (Optional):**
    ```bash
    python sourcecombine.py --init
    ```
    This command creates a `sourcecombine.yml` file with default settings to help you get started.

    *(Note)* If you do not have the `PyYAML` library installed, you can also use JSON configurations (such as `sourcecombine.json` or `config.json`). They work immediately using Python's standard library.

For more details, use `python sourcecombine.py --help` or check `config.template.yml`.

## Usage Examples
### Basic Combination
Combine all files in the current directory into `combined_files.txt`:
```bash
python sourcecombine.py
```

### Filtering by Language
Combine only Python and JavaScript files from the `src` folder. You can repeat the language flag or use a simpler comma-separated list:
```bash
# Using comma-separated lists
python sourcecombine.py src/ --language python,javascript --output project_context.txt

# Or repeating the flag
python sourcecombine.py src/ --language python --language javascript --output project_context.txt
```

### File Extraction
Rebuild the original project structure from a combined Markdown file:
```bash
python sourcecombine.py --extract combined_files.md --output restored_project/
```

### AI Model Context
Prepare a full project context for AI models. This preset uses Markdown format and includes a Table of Contents, folder tree, project overview, line numbers, and Git context (logs and diffs). It also removes duplicates and skips binary files. If you do not specify an output file, the tool copies the result to the system clipboard:
```bash
python sourcecombine.py src/ --ai
```

### File Pairing
Combine related files (such as `.cpp` and `.h` pairs) into their own individual combined files in a separate folder:
```bash
python sourcecombine.py src/ --pair .cpp .h --output combined_src/
```

### Collapsible Markdown
Combine files into collapsible Markdown blocks, perfect for reducing clutter when sharing large code bases with AI models:
```bash
python sourcecombine.py src/ --format markdown --collapsible --output project_context.md
```

### File Verification and Repair
Check if your files on disk match the content or SHA-256 hashes stored in a combined file or manifest. You can also automatically fix any missing or modified files.

1. **Verify files on disk:**
   ```bash
   python sourcecombine.py --verify combined_files.json
   ```
   *(or use the short-hand `-y`)*:
   ```bash
   python sourcecombine.py -y combined_files.json
   ```

2. **Repair missing or mismatched files:**
   ```bash
   python sourcecombine.py --repair combined_files.json
   ```
   *(or use the short-hand `-P`)*:
   ```bash
   python sourcecombine.py -P combined_files.json
   ```

### Backup and Restore (Safe Workflows)
You can easily create safe checkpoints of your source files, preview proposed backups or restorations, and clean up or inspect your backups.

1. **Create backups manually for matching configuration/filters:**
   ```bash
   python sourcecombine.py --backup
   ```
   *(or dry-run to preview what will be backed up)*:
   ```bash
   python sourcecombine.py --backup --dry-run
   ```
   *(or output machine-readable JSON format)*:
   ```bash
   python sourcecombine.py --backup --json
   ```

2. **List all backups and check their status relative to disk:**
   ```bash
   python sourcecombine.py --list-backups
   ```

3. **Show diffs between current files on disk and backup copies:**
   ```bash
   python sourcecombine.py --diff-backups
   ```

4. **Restore original files from backups:**
   ```bash
   python sourcecombine.py --restore
   ```

5. **Clean up and delete all backup files:**
   ```bash
   python sourcecombine.py --delete-backups
   ```

### Advanced Filtering and AI Optimization

#### Explain Exclusion/Inclusion
If you are unsure why a file is being skipped or included, you can check using the `--explain` command:
```bash
python sourcecombine.py --explain src/utils.py
```

#### Combine Only Changed Git Files
You can choose to combine only files with staged or unstaged changes in Git using the `--git-diff` flag. This is great for reviewing code changes before committing:
```bash
python sourcecombine.py src/ --git-diff
```
To combine only staged changes, add the `--staged` flag:
```bash
python sourcecombine.py src/ --staged
```

#### Filter by File Size and Age
You can easily skip large or old files to keep your output clean. For example, to only include files smaller than 50 Kilobytes modified in the last 24 hours:
```bash
python sourcecombine.py src/ --max-size 50KB --since 1d
```

#### Optimize Files for AI (Remove Comments and Whitespace)
When sharing code with AI models, you can save tokens by removing source code comments and blank lines. Use the `--remove-comments` and `--compact-whitespace` flags together:
```bash
python sourcecombine.py src/ --remove-comments --compact-whitespace --output compact_code.txt
```

#### Filter by Content Patterns (Grep)
You can filter files by matching patterns in their content. For example, to include only files containing the word "TODO":
```bash
python sourcecombine.py src/ --grep "TODO"
```
Or to skip files containing "DEPRECATED":
```bash
python sourcecombine.py src/ --exclude-grep "DEPRECATED"
```

## Configuration Guide
You can configure SourceCombine using a configuration file instead of passing many options via the command line.

### Configuration Auto-Discovery
When you run SourceCombine, it automatically searches for these configuration files in your current folder (in order of priority):
1. `sourcecombine.yml` or `sourcecombine.yaml`
2. `sourcecombine.json`
3. `config.yml` or `config.yaml`
4. `config.json`

If the tool finds one of these files, it loads your settings automatically. You can also specify a custom configuration file using the `--config` or `-k` flag:
```bash
python sourcecombine.py --config my_custom_config.yml
```

### YAML Configuration Example
Here is a simple and clean YAML configuration file (`sourcecombine.yml`). This configuration defines search rules, filters out build/environment folders, and configures the output file:

```yaml
# --- Search Parameters ---
search:
  # Search recursively through subfolders (true or false).
  recursive: true
  # Only include files with these extensions. Leave empty to include all.
  allowed_extensions:
    - '.py'
    - '.js'

# --- File Filtering ---
filters:
  # Skip duplicate files by path or content.
  unique: true
  # Skip binary files automatically.
  skip_binary: true
  # Exclude specific files and folders.
  exclusions:
    filenames:
      - '*.log'
      - '*.tmp'
    folders:
      - '.git'
      - 'node_modules'
      - 'venv'

# --- Output Settings ---
output:
  # Output file path.
  file: 'combined_files.txt'
  # Add a Table of Contents to the start of the output.
  table_of_contents: true
  # Add a visual folder tree to the start of the output.
  include_tree: true
  # Add a project overview summary.
  project_overview: true
```

### JSON Configuration Example (No PyYAML Required)
If you do not have `PyYAML` installed, or if you prefer JSON, you can use a JSON configuration file (`sourcecombine.json`). It works immediately using Python's standard library:

```json
{
  "search": {
    "recursive": true,
    "allowed_extensions": [
      ".py",
      ".js"
    ]
  },
  "filters": {
    "unique": true,
    "skip_binary": true,
    "exclusions": {
      "filenames": [
        "*.log",
        "*.tmp"
      ],
      "folders": [
        ".git",
        "node_modules",
        "venv"
      ]
    }
  },
  "output": {
    "file": "combined_files.txt",
    "table_of_contents": true,
    "include_tree": true,
    "project_overview": true
  }
}
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
*   `{{GIT_STATUS}}`: Summary of project changes (for example, "2 modified, 1 added").
*   `{{OS}}`, `{{PYTHON_VERSION}}`, `{{PLATFORM}}`, `{{ARCH}}`: System and environment information.
*   `{{ENV:VAR_NAME}}`: Value of an environment variable.
*   `{{SIZE_PERCENT}}`, `{{TOKEN_PERCENT}}`, `{{LINE_PERCENT}}`: Percentage of the total project.
*   `{{FILE_URL}}`: Direct web link to the specific file and commit.
*   `{{FILE_DIFF}}`: Changes specific to the current file (requires `--include-diff` flag).
*   `{{FILE_STATUS}}`: Git status of the current file (for example, `M`, `A`, `??`).
*   `{{MANIFEST_SOURCE}}`: The manifest file from which project information was extracted (for example, `package.json`).
*   `{{PROJECT_URL}}`: Web URL to the repository home (supports GitHub, GitLab, Bitbucket).

### Project Information Placeholders
Used in `global_header_template`, `global_footer_template`, and other project-wide settings:
*   `{{PROJECT_NAME}}`: Name of the project (detected from `package.json`, `pyproject.toml`, `Cargo.toml`, `composer.json`, `pom.xml`, `go.mod`, `*.gemspec`, `mix.exs`, `Package.swift`, `.csproj`, `.fsproj`, `.vbproj`, `.sln`, `settings.gradle`, `project.clj`, `.podspec`, `.xcodeproj`, `CMakeLists.txt`, `Project.toml`, `deno.json`, `deno.jsonc`, `build.zig.zon`, `pubspec.yaml`, `README.md`, or folder name).
*   `{{PROJECT_VERSION}}`: Version of the project (automatically detected from project manifests).
*   `{{PROJECT_AUTHOR}}`: Author of the project (automatically detected from project manifests or LICENSE files).
*   `{{PROJECT_DESCRIPTION}}`: Short description of the project (automatically detected from project manifests).
*   `{{PROJECT_LICENSE}}`: License identifier of the project (automatically detected from project manifests or LICENSE files).
*   `{{MANIFEST_SOURCE}}`: The manifest file from which project information was extracted (for example, `package.json`).
*   `{{FILE_COUNT}}`: Total number of files included.
*   `{{TOTAL_SIZE}}`: Total size of all files.
*   `{{TOTAL_TOKENS}}`: Total number of tokens.
*   `{{TOTAL_LINES}}`: Total number of lines.
*   `{{DATE}}`, `{{TIME}}`, `{{DATETIME}}`: Current date and time.
*   `{{TOC}}`, `{{TABLE_OF_CONTENTS}}`: Table of contents.
*   `{{TREE}}`, `{{PROJECT_STRUCTURE}}`: Visual folder tree.
*   `{{OVERVIEW}}`, `{{PROJECT_OVERVIEW}}`: Project overview summary.
*   `{{OS}}`, `{{PYTHON_VERSION}}`, `{{PLATFORM}}`, `{{ARCH}}`: System and environment information.
*   `{{ENV:VAR_NAME}}`: Value of an environment variable.
*   `{{GIT_STATUS}}`: Summary of project changes (for example, "2 modified, 1 added").
*   `{{GIT_REMOTE_URL}}`: The repository's origin remote URL.
*   `{{PROJECT_URL}}`: Web URL to the repository home (supports GitHub, GitLab, Bitbucket).

### Git Placeholders
These require a Git repository to function:
*   `{{GIT_BRANCH}}`: Current branch name.
*   `{{GIT_COMMIT}}`, `{{GIT_COMMIT_SHORT}}`: Full or short commit hash.
*   `{{GIT_AUTHOR}}`: Author of the latest commit in the project.
*   `{{GIT_TAG}}`: Latest Git tag in the project.
*   `{{GIT_AUTHOR_DATE}}`: Date of the latest commit in the project.
*   `{{GIT_STATUS}}`: Summary of project changes (for example, "2 modified, 1 added").
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

