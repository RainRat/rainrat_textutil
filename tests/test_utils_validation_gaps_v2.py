import utils

def test_validate_filters_modified_with_none_values():
    config = {
        'filters': {
            'modified_since': None,
            'modified_until': 1.5
        },
        'search': {'root_folders': ['.']}
    }
    utils.validate_config(config)

def test_validate_filters_exclusions_explicit_none():
    config = {
        'filters': {
            'exclusions': None
        },
        'search': {'root_folders': ['.']}
    }
    utils.validate_config(config)

def test_validate_filters_inclusion_groups_explicit_none():
    config = {
        'filters': {
            'inclusion_groups': None
        },
        'search': {'root_folders': ['.']}
    }
    utils.validate_config(config)

def test_validate_filters_inclusion_groups_defaults_applied():
    config = {
        'filters': {
            'inclusion_groups': {
                'test_group': {}
            }
        },
        'search': {'root_folders': ['.']}
    }
    utils.validate_config(config)
    group = config['filters']['inclusion_groups']['test_group']
    assert group['enabled'] is False
    assert group['filenames'] == []

def test_validate_positive_number_rejects_bool():
    import pytest
    config = {
        'filters': {
            'modified_since': True
        },
        'search': {'root_folders': ['.']}
    }
    with pytest.raises(utils.InvalidConfigError, match="filters.modified_since must be 0 or more"):
        utils.validate_config(config)
