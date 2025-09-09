import re
import sys
import yaml


def load_yaml_config(config_file_path):
    """Load a YAML configuration file with basic error handling."""
    print(f"Loading configuration from: {config_file_path}")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                raise ValueError("Configuration file is empty or invalid.")
            return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{config_file_path}'.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def read_file_best_effort(file_path):
    """Attempt to read a file trying several encodings."""
    encodings = ['utf-8', 'latin-1', 'ascii', 'utf-16']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    print(f"Warning: Could not decode {file_path} with any of the attempted encodings.")
    return ""


def normalize_whitespace(text):
    """Normalize whitespace similarly to previous scripts."""
    previous = None
    while previous != text:
        previous = text
        text = text.replace('    ', '\t').replace('\r', '')
    previous = None
    while previous != text:
        previous = text
        text = text.replace('\t ', '\t').replace(' \n', '\n').replace('\n\n\n', '\n\n').replace('\t\n', '\n')
        text = re.sub(r'(?<!\n|\t)\t', ' ', text)
    return text


def remove_hex_pattern_lines(text, placeholder=None):
    """Remove lines matching a hex pattern, optionally inserting a placeholder once."""
    pattern = re.compile(r"^\s*\w+\(0x[0-9a-fA-F]+,\s*0x[0-9a-fA-F]+\),\s*$")
    lines = text.splitlines()
    out_lines = []
    inserted = False
    for line in lines:
        if pattern.match(line):
            if placeholder and not inserted:
                out_lines.append(placeholder)
                inserted = True
        else:
            out_lines.append(line)
    return "\n".join(out_lines)
