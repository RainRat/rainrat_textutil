import os
import shutil
from pathlib import Path
import sourcecombine
import utils

def test_template_pairing_output_path():
    # Setup
    root = Path("test_pairing_template")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(exist_ok=True)
    src_dir = root / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "main.cpp").write_text("some content")
    (src_dir / "main.h").write_text("some header")

    config = utils.DEFAULT_CONFIG.copy()
    config['search']['root_folders'] = [str(root)]
    config['pairing'] = {
        'enabled': True,
        'source_extensions': ['.cpp'],
        'header_extensions': ['.h'],
        'include_mismatched': True
    }
    config['output']['folder'] = None
    config['output']['paired_filename_template'] = '{{DIR}}/{{STEM}}.combined'

    print(f"Root: {root.resolve()}")

    stats = sourcecombine.find_and_combine_files(config, output_path=None)

    expected_path = src_dir / "main.combined"
    buggy_path = src_dir / "src" / "main.combined"

    if buggy_path.exists():
        print(f"BUG DETECTED: Output created at {buggy_path}")
    elif expected_path.exists():
        print(f"Success: Output created at {expected_path}")
    else:
        print("Neither expected nor buggy path found.")

if __name__ == "__main__":
    test_template_pairing_output_path()
