#!/usr/bin/env python3
"""Tests for dependency graph analyzer."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from analyze_dependencies import (
    extract_imports,
    analyze_project_dependencies,
    get_dependency_edges,
    generate_dot_graph,
    generate_mermaid_graph
)


@pytest.fixture
def sample_python_file(tmp_path):
    """Create a sample Python file for testing."""
    content = '''
import os
import sys
from pathlib import Path
from typing import List, Dict

from fetch_skill_manager import fetch_all_skills
from utils.helpers import format_date

def main():
    pass
'''
    py_file = tmp_path / "test_module.py"
    py_file.write_text(content)
    return py_file


def test_extract_imports(sample_python_file):
    """Test import extraction."""
    imports, from_imports = extract_imports(sample_python_file)

    assert 'os' in imports
    assert 'sys' in imports
    assert 'pathlib' in from_imports
    assert 'typing' in from_imports


def test_extract_imports_invalid_file(tmp_path):
    """Test handling of invalid Python file."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(")

    imports, from_imports = extract_imports(bad_file)

    # Should return empty sets, not crash
    assert isinstance(imports, set)
    assert isinstance(from_imports, set)


def test_analyze_project_dependencies(tmp_path):
    """Test project dependency analysis."""
    # Create test files
    (tmp_path / "module_a.py").write_text("import module_b")
    (tmp_path / "module_b.py").write_text("import os")
    (tmp_path / "module_c.py").write_text("from module_a import func")

    modules = analyze_project_dependencies(tmp_path)

    assert 'module_a' in modules
    assert 'module_b' in modules
    assert 'module_c' in modules


def test_get_dependency_edges(tmp_path):
    """Test edge extraction."""
    (tmp_path / "main.py").write_text("import helper")
    (tmp_path / "helper.py").write_text("import os")

    modules = analyze_project_dependencies(tmp_path)
    edges = get_dependency_edges(modules)

    assert ('main', 'helper') in edges


def test_generate_dot_graph():
    """Test DOT format generation."""
    from analyze_dependencies import ModuleInfo

    modules = {
        'main': ModuleInfo('main', Path('main.py'), {'helper'}, set()),
        'helper': ModuleInfo('helper', Path('helper.py'), set(), set())
    }
    edges = [('main', 'helper')]

    dot = generate_dot_graph(modules, edges)

    assert 'digraph' in dot
    assert '"main"' in dot
    assert '"helper"' in dot
    assert '->' in dot


def test_generate_mermaid_graph():
    """Test Mermaid format generation."""
    from analyze_dependencies import ModuleInfo

    modules = {
        'analyze_test': ModuleInfo('analyze_test', Path('analyze_test.py'), set(), set()),
        'fetch_data': ModuleInfo('fetch_data', Path('fetch_data.py'), set(), set())
    }
    edges = [('analyze_test', 'fetch_data')]

    mermaid = generate_mermaid_graph(modules, edges)

    assert 'flowchart TB' in mermaid
    assert 'analyze_test' in mermaid
    assert '-->' in mermaid
