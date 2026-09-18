import utils


def test_readme_description_setext_header_truncation(tmp_path):
    readme_path = tmp_path / "README.md"
    long_desc = "A" * 250
    readme_path.write_text(
        f"Setext Title\n=====\n{long_desc}\n",
        encoding="utf-8",
    )
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "Setext Title"
    assert identity["project_description"] == "A" * 197 + "..."


def test_readme_description_h1_followed_only_by_headers(tmp_path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "# Header Only\n\n## Subheader 1\n### Subheader 2\n---\n",
        encoding="utf-8",
    )
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "Header Only"
    assert identity["project_description"] == ""
