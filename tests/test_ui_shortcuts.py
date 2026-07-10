import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import subprocess
import sys
import os
import shutil
import sourcecombine

def test_shortcuts():
    # Test -V for version
    result = subprocess.run([sys.executable, "sourcecombine.py", "-V"], capture_output=True, text=True)
    expected_version = f"sourcecombine.py {sourcecombine.__version__}"
    assert expected_version in result.stdout or expected_version in result.stderr

    # Test -s for sort and -r for reverse
    # Create dummy files
    test_dir = "shortcut_test_dir"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "b.txt"), "w") as f: f.write("b")
    with open(os.path.join(test_dir, "a.txt"), "w") as f: f.write("a")

    # Sort by name reverse: b then a
    # Files are logged to stderr
    result = subprocess.run([sys.executable, "sourcecombine.py", test_dir, "-d", "-s", "name", "-r"], capture_output=True, text=True)
    lines = result.stderr.splitlines()
    file_lines = []
    for line in lines:
        if line.strip().endswith(".txt"):
            file_lines.append(line.strip())

    assert "b.txt" in file_lines
    assert "a.txt" in file_lines
    # Check order
    b_idx = file_lines.index("b.txt")
    a_idx = file_lines.index("a.txt")
    assert b_idx < a_idx

    # Test -M for max-tokens
    # We use -M 1 to trigger a token limit warning
    result = subprocess.run([sys.executable, "sourcecombine.py", test_dir, "-d", "-M", "1"], capture_output=True, text=True)
    combined_output = result.stdout + result.stderr
    assert "WARNING: Output shortened due to: token limit" in combined_output

    # Test -N for no-content
    with open(os.path.join(test_dir, "content.txt"), "w") as f: f.write("SHOULD_BE_SKIPPED")
    result = subprocess.run([sys.executable, "sourcecombine.py", test_dir, "-N", "-o", "-"], capture_output=True, text=True)
    assert "SHOULD_BE_SKIPPED" not in result.stdout
    assert "content.txt" in result.stdout

    # Test -O for overview
    result = subprocess.run([sys.executable, "sourcecombine.py", test_dir, "-O", "-o", "-"], capture_output=True, text=True)
    assert "Project Overview:" in result.stdout

    # Test -F for files-from
    files_list = os.path.join(test_dir, "files.txt")
    with open(files_list, "w") as f:
        f.write(os.path.join(test_dir, "a.txt") + "\n")
    result = subprocess.run([sys.executable, "sourcecombine.py", "-F", files_list, "-o", "-"], capture_output=True, text=True)
    assert "a.txt" in result.stdout
    assert "b.txt" not in result.stdout

    # Test -P for pair
    pair_dir = os.path.join(test_dir, "pair")
    os.makedirs(pair_dir, exist_ok=True)
    with open(os.path.join(pair_dir, "main.cpp"), "w") as f: f.write("cpp")
    with open(os.path.join(pair_dir, "main.h"), "w") as f: f.write("h")
    # Output to stdout is not supported for pairing, so we use a temp output folder
    out_pair = os.path.join(test_dir, "out_pair")
    result = subprocess.run([sys.executable, "sourcecombine.py", pair_dir, "-P", ".cpp", ".h", "-o", out_pair], capture_output=True, text=True)
    assert os.path.exists(os.path.join(out_pair, "main.combined"))

    # Cleanup
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    try:
        test_shortcuts()
        print("Shortcuts test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
