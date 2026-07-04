import sourcecombine

def test_resolve_information_placeholders_empty_template():
    """Target line 475 of sourcecombine.py: early return if not template."""
    replacements = {}
    sourcecombine._resolve_information_placeholders("", replacements, {})
    assert replacements == {}

    sourcecombine._resolve_information_placeholders(None, replacements, {})
    assert replacements == {}

def test_placeholder_none_rendering():
    """Verify that None values in information are rendered as empty strings."""
    git_info = {
        'git_branch': 'main',
        'git_status': None, # explicitly None
    }

    replacements = {}
    # Use a template that includes the placeholder to trigger resolution
    template = "Status: {{GIT_STATUS}}"
    sourcecombine._resolve_information_placeholders(template, replacements, git_info)

    # Before the fix, replacements['{{GIT_STATUS}}'] will be None
    # and _render_single_pass will render it as "None"
    rendered = sourcecombine._render_single_pass(template, replacements)
    assert rendered == "Status: "

def test_render_single_pass_none_value():
    """Verify that _render_single_pass handles None in replacements safely."""
    template = "Value: {{VAL}}"
    replacements = {"{{VAL}}": None}
    rendered = sourcecombine._render_single_pass(template, replacements)
    assert rendered == "Value: "
