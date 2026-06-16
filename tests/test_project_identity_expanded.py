import pytest
from pathlib import Path
from utils import get_project_identity

def test_ruby_gemspec_detection(tmp_path):
    gemspec = tmp_path / "test-gem.gemspec"
    gemspec.write_text("""
        Gem::Specification.new do |s|
          s.name        = 'test-gem'
          s.version     = '1.2.3'
          s.description = 'A test gem'
          s.license     = 'MIT'
        end
    """, encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "test-gem"
    assert identity["project_version"] == "1.2.3"
    assert identity["project_description"] == "A test gem"
    assert identity["project_license"] == "MIT"

def test_elixir_mix_exs_detection(tmp_path):
    mix_exs = tmp_path / "mix.exs"
    mix_exs.write_text("""
        def project do
          [
            app: :test_app,
            version: "0.1.0",
            elixir: "~> 1.14",
            start_permanent: Mix.env() == :prod,
            deps: deps()
          ]
        end
    """, encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "test_app"
    assert identity["project_version"] == "0.1.0"

def test_swift_package_swift_detection(tmp_path):
    package_swift = tmp_path / "Package.swift"
    package_swift.write_text("""
        import PackageDescription

        let package = Package(
            name: "test-package",
            products: [
                .library(name: "test-package", targets: ["test-package"]),
            ],
            targets: [
                .target(name: "test-package", dependencies: []),
            ]
        )
    """, encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "test-package"

def test_readme_fallback_detection(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("""
# Awesome Project

This is a very awesome project that does many cool things.
It was built with SourceCombine.

## Features
- Fast
- Reliable
    """, encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Awesome Project"
    assert identity["project_description"] == "This is a very awesome project that does many cool things."

def test_readme_no_description_fallback(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Simple Project", encoding='utf-8')

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Simple Project"
    assert identity["project_description"] == ""
