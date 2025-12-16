import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sourcecombine import FileProcessor
from utils import DEFAULT_CONFIG
import io
from pathlib import Path

def test_file_processor_defaults():
    config = {'processing': {}, 'output': {}}
    processor = FileProcessor(config, config['output'])

    out = io.StringIO()
    # Dummy file
    p = Path('dummy.txt')
    p.write_text('content', encoding='utf-8')

    try:
        # process_and_write needs read_file_best_effort which reads the file
        processor.process_and_write(p, Path('.'), out)
        content = out.getvalue()
        print(f"Content: {repr(content)}")
        if "--- dummy.txt ---" in content:
            print("Uses default header.")
        else:
            print("No header.")
    finally:
        if p.exists():
            p.unlink()

if __name__ == "__main__":
    test_file_processor_defaults()
