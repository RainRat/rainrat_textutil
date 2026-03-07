import os
import shutil
import subprocess
from pathlib import Path

def test_restore_functionality():
    test_dir = Path("test_restore_env")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()

    # 1. Create dummy files
    file1 = test_dir / "file1.txt"
    file1.write_text("Original content 1")

    file2 = test_dir / "file2.txt"
    file2.write_text("Original content 2")

    print("--- Step 1: Created dummy files ---")
    print(f"file1: {file1.read_text()}")
    print(f"file2: {file2.read_text()}")

    # 2. Simulate apply-in-place by creating backups and modifying files
    # We'll just do it manually to ensure we have backups to restore
    shutil.copy2(file1, Path(str(file1) + ".bak"))
    file1.write_text("Modified content 1")

    shutil.copy2(file2, Path(str(file2) + ".bak"))
    file2.write_text("Modified content 2")

    print("\n--- Step 2: Simulated 'apply-in-place' (modified files and created .bak) ---")
    print(f"file1: {file1.read_text()} (Backup exists: {Path(str(file1) + '.bak').exists()})")
    print(f"file2: {file2.read_text()} (Backup exists: {Path(str(file2) + '.bak').exists()})")

    # 3. Test --restore with --dry-run
    print("\n--- Step 3: Testing --restore --dry-run ---")
    result = subprocess.run(
        ["python", "sourcecombine.py", str(test_dir), "--restore", "--dry-run"],
        capture_output=True,
        text=True
    )
    print(result.stderr) # Logging goes to stderr

    # Verify files are NOT restored
    assert file1.read_text() == "Modified content 1"
    assert file2.read_text() == "Modified content 2"
    assert Path(str(file1) + ".bak").exists()
    assert Path(str(file2) + ".bak").exists()
    print("Dry run verified: Files remain modified and backups exist.")

    # 4. Test --restore
    print("\n--- Step 4: Testing --restore ---")
    result = subprocess.run(
        ["python", "sourcecombine.py", str(test_dir), "--restore"],
        capture_output=True,
        text=True
    )
    print(result.stderr)

    # Verify files ARE restored and backups are GONE
    assert file1.read_text() == "Original content 1"
    assert file2.read_text() == "Original content 2"
    assert not Path(str(file1) + ".bak").exists()
    assert not Path(str(file2) + ".bak").exists()
    print("Restore verified: Files returned to original content and backups removed.")

    # Cleanup
    shutil.rmtree(test_dir)
    print("\nVerification successful!")

if __name__ == "__main__":
    test_restore_functionality()
