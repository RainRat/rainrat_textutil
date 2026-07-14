import pytest
import utils
import sourcecombine
from unittest.mock import MagicMock

def test_validate_project_section_not_dict():
    config = {
        'project': "not a dict",
        'search': {'root_folders': ['.']}
    }
    with pytest.raises(utils.InvalidConfigError, match="'project' section must be a dictionary."):
        utils.validate_config(config)

def test_validate_project_section_invalid_field_type():
    config = {
        'project': {'name': 123},
        'search': {'root_folders': ['.']}
    }
    with pytest.raises(utils.InvalidConfigError, match="'project.name' must be text or nothing."):
        utils.validate_config(config)

def test_apply_project_overrides_with_none_config():
    config = {'project': None}
    args = MagicMock()
    args.project_name = "Override Name"
    args.project_version = None
    args.project_author = None
    args.project_description = None
    args.project_license = None
    args.project_url = None

    sourcecombine._apply_project_overrides(config, args)

    assert config['project'] == {'name': "Override Name"}

def test_get_project_identity_dotnet_fallback_name(tmp_path):
    csproj = tmp_path / "MyProject.csproj"
    csproj.write_text("<Project></Project>")

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "MyProject"
