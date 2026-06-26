import json
import csv
import io
from pathlib import Path
from sourcecombine import find_and_combine_files
import utils

def test_no_content_text(tmp_path):
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1", encoding='utf-8')

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(test_dir)]
    config['output'] = config['output'].copy()
    config['output']['skip_content'] = True
    config['output']['file'] = str(tmp_path / "output.txt")

    utils.validate_config(config)
    find_and_combine_files(config, config['output']['file'])

    output = Path(config['output']['file']).read_text(encoding='utf-8')
    assert "--- file1.txt ---" in output
    assert "content1" not in output

def test_no_content_json(tmp_path):
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1", encoding='utf-8')

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(test_dir)]
    config['output'] = config['output'].copy()
    config['output']['skip_content'] = True
    config['output']['format'] = 'json'
    config['output']['file'] = str(tmp_path / "output.json")

    utils.validate_config(config)
    find_and_combine_files(config, config['output']['file'], output_format='json')

    output_data = json.loads(Path(config['output']['file']).read_text(encoding='utf-8'))
    assert len(output_data) == 1
    assert output_data[0]['path'] == "file1.txt"
    assert 'content' not in output_data[0]

def test_no_content_csv(tmp_path):
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1", encoding='utf-8')

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = config['search'].copy()
    config['search']['root_folders'] = [str(test_dir)]
    config['output'] = config['output'].copy()
    config['output']['skip_content'] = True
    config['output']['format'] = 'csv'
    config['output']['file'] = str(tmp_path / "output.csv")

    utils.validate_config(config)
    find_and_combine_files(config, config['output']['file'], output_format='csv')

    with open(config['output']['file'], 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]['path'] == "file1.txt"
    assert rows[0]['content'] == ""
