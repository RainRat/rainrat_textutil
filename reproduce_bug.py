import os
import shutil
from pathlib import Path
import sourcecombine
import utils

def test_mismatched_pairing_output_path():
    # Setup
    root = Path("test_pairing_mismatched")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(exist_ok=True)
    src_dir = root / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "extra.txt").write_text("some content")

    config = utils.DEFAULT_CONFIG.copy()
    config['search']['root_folders'] = [str(root)]
    config['pairing'] = {
        'enabled': True,
        'source_extensions': ['.cpp'],
        'header_extensions': ['.h'],
        'include_mismatched': True
    }
    config['output']['folder'] = None

    print(f"Root: {root.resolve()}")

    stats = sourcecombine.find_and_combine_files(config, output_path=None)

    expected_path = src_dir / "extra.txt" # This is where it SHOULD be
    buggy_path = src_dir / "src" / "extra.txt"

    if buggy_path.exists():
        print(f"BUG DETECTED: Output created at {buggy_path}")
    elif expected_path.exists():
        print("Success: Buggy path does not exist. Original file was preserved or correctly handled.")
    else:
        print("Neither expected nor buggy path found.")

if __name__ == "__main__":
    test_mismatched_pairing_output_path()
