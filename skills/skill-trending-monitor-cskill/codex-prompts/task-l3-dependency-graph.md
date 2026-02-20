# Codex Task L3: Dependency Graph Visualization

## Priority
Low (v2.0+)

## Objective
Create a module that analyzes Python imports in the codebase and generates dependency graphs in DOT and Mermaid formats.

## Context
- Project has ~15 Python files in `scripts/`
- Need to visualize module dependencies
- Output formats: DOT (Graphviz) and Mermaid (Markdown-embeddable)

## Requirements

### 1. Create `scripts/analyze_dependencies.py`

```python
#!/usr/bin/env python3
"""
Analyze Python module dependencies and generate visualization graphs.
Supports DOT (Graphviz) and Mermaid output formats.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """Information about a Python module."""
    name: str
    path: Path
    imports: Set[str]
    from_imports: Set[str]
    is_internal: bool = True


def extract_imports(file_path: Path) -> Tuple[Set[str], Set[str]]:
    """
    Extract import statements from a Python file using AST.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (import_names, from_import_names)

    Example:
        >>> imports, from_imports = extract_imports(Path('script.py'))
        >>> print(imports)  # {'os', 'sys'}
        >>> print(from_imports)  # {'pathlib.Path', 'typing.List'}
    """
    imports = set()
    from_imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get the base module
                    base_module = node.module.split('.')[0]
                    from_imports.add(base_module)

                    # Also track specific imports
                    for alias in node.names:
                        from_imports.add(f"{node.module}.{alias.name}")

    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")

    return imports, from_imports


def analyze_project_dependencies(
    project_dir: Path,
    include_patterns: Optional[List[str]] = None
) -> Dict[str, ModuleInfo]:
    """
    Analyze all Python files in a project directory.

    Args:
        project_dir: Root directory to analyze
        include_patterns: Glob patterns for files to include (default: ['*.py'])

    Returns:
        Dict mapping module name to ModuleInfo

    Example:
        >>> deps = analyze_project_dependencies(Path('scripts/'))
        >>> for name, info in deps.items():
        ...     print(f"{name}: {len(info.imports)} imports")
    """
    if include_patterns is None:
        include_patterns = ['**/*.py']

    modules = {}
    internal_modules = set()

    # First pass: collect all internal module names
    for pattern in include_patterns:
        for py_file in project_dir.glob(pattern):
            if py_file.name.startswith('_') and py_file.name != '__init__.py':
                continue

            module_name = py_file.stem
            internal_modules.add(module_name)

    logger.info(f"Found {len(internal_modules)} internal modules")

    # Second pass: analyze imports
    for pattern in include_patterns:
        for py_file in project_dir.glob(pattern):
            if py_file.name.startswith('_') and py_file.name != '__init__.py':
                continue

            module_name = py_file.stem
            imports, from_imports = extract_imports(py_file)

            # Filter to only internal imports for dependency graph
            internal_imports = imports & internal_modules
            internal_from_imports = {
                imp.split('.')[0] for imp in from_imports
            } & internal_modules

            modules[module_name] = ModuleInfo(
                name=module_name,
                path=py_file,
                imports=internal_imports,
                from_imports=internal_from_imports,
                is_internal=True
            )

    logger.info(f"Analyzed {len(modules)} modules")

    return modules


def get_dependency_edges(
    modules: Dict[str, ModuleInfo]
) -> List[Tuple[str, str]]:
    """
    Extract directed edges (from -> to) from module dependencies.

    Args:
        modules: Dict from analyze_project_dependencies()

    Returns:
        List of (source_module, target_module) tuples

    Example:
        >>> edges = get_dependency_edges(modules)
        >>> print(edges)  # [('analyze_comprehensive', 'fetch_skill_manager'), ...]
    """
    edges = []

    for module_name, info in modules.items():
        all_deps = info.imports | info.from_imports

        for dep in all_deps:
            if dep in modules and dep != module_name:
                edges.append((module_name, dep))

    # Remove duplicates while preserving order
    seen = set()
    unique_edges = []
    for edge in edges:
        if edge not in seen:
            seen.add(edge)
            unique_edges.append(edge)

    logger.info(f"Found {len(unique_edges)} dependency edges")

    return unique_edges


def generate_dot_graph(
    modules: Dict[str, ModuleInfo],
    edges: List[Tuple[str, str]],
    title: str = "Module Dependencies"
) -> str:
    """
    Generate DOT format graph (for Graphviz).

    Args:
        modules: Dict from analyze_project_dependencies()
        edges: List from get_dependency_edges()
        title: Graph title

    Returns:
        DOT format string

    Example:
        >>> dot = generate_dot_graph(modules, edges)
        >>> Path('deps.dot').write_text(dot)
        >>> # Then: dot -Tpng deps.dot -o deps.png
    """
    lines = [
        f'digraph "{title}" {{',
        '    rankdir=TB;',
        '    node [shape=box, style=filled, fillcolor=lightblue];',
        '    edge [color=gray50];',
        ''
    ]

    # Categorize nodes
    analyzers = []
    fetchers = []
    utils = []
    other = []

    for name in modules.keys():
        if name.startswith('analyze'):
            analyzers.append(name)
        elif name.startswith('fetch') or name.startswith('parse'):
            fetchers.append(name)
        elif name in ['helpers', 'cache_manager', 'rate_limiter'] or 'validator' in name:
            utils.append(name)
        else:
            other.append(name)

    # Add subgraphs for grouping
    if analyzers:
        lines.append('    subgraph cluster_analyzers {')
        lines.append('        label="Analyzers";')
        lines.append('        style=dashed;')
        lines.append('        color=blue;')
        for name in analyzers:
            lines.append(f'        "{name}";')
        lines.append('    }')
        lines.append('')

    if fetchers:
        lines.append('    subgraph cluster_fetchers {')
        lines.append('        label="Fetchers/Parsers";')
        lines.append('        style=dashed;')
        lines.append('        color=green;')
        for name in fetchers:
            lines.append(f'        "{name}";')
        lines.append('    }')
        lines.append('')

    if utils:
        lines.append('    subgraph cluster_utils {')
        lines.append('        label="Utilities";')
        lines.append('        style=dashed;')
        lines.append('        color=orange;')
        for name in utils:
            lines.append(f'        "{name}";')
        lines.append('    }')
        lines.append('')

    # Add edges
    lines.append('    // Dependencies')
    for source, target in edges:
        lines.append(f'    "{source}" -> "{target}";')

    lines.append('}')

    return '\n'.join(lines)


def generate_mermaid_graph(
    modules: Dict[str, ModuleInfo],
    edges: List[Tuple[str, str]],
    title: str = "Module Dependencies"
) -> str:
    """
    Generate Mermaid format graph (Markdown-embeddable).

    Args:
        modules: Dict from analyze_project_dependencies()
        edges: List from get_dependency_edges()
        title: Graph title

    Returns:
        Mermaid format string

    Example:
        >>> mermaid = generate_mermaid_graph(modules, edges)
        >>> # Embed in Markdown: ```mermaid\\n{mermaid}\\n```
    """
    lines = [
        '```mermaid',
        'flowchart TB',
        f'    %% {title}',
        ''
    ]

    # Categorize nodes into subgraphs
    analyzers = [n for n in modules.keys() if n.startswith('analyze')]
    fetchers = [n for n in modules.keys() if n.startswith('fetch') or n.startswith('parse')]
    utils = [n for n in modules.keys() if n in ['helpers', 'cache_manager', 'rate_limiter'] or 'validator' in n]

    # Add subgraphs
    if analyzers:
        lines.append('    subgraph Analyzers')
        for name in analyzers:
            # Mermaid uses underscores, not hyphens in IDs
            safe_name = name.replace('-', '_')
            lines.append(f'        {safe_name}["{name}"]')
        lines.append('    end')
        lines.append('')

    if fetchers:
        lines.append('    subgraph "Fetchers & Parsers"')
        for name in fetchers:
            safe_name = name.replace('-', '_')
            lines.append(f'        {safe_name}["{name}"]')
        lines.append('    end')
        lines.append('')

    if utils:
        lines.append('    subgraph Utilities')
        for name in utils:
            safe_name = name.replace('-', '_')
            lines.append(f'        {safe_name}["{name}"]')
        lines.append('    end')
        lines.append('')

    # Add other nodes
    other = [n for n in modules.keys() if n not in analyzers + fetchers + utils]
    for name in other:
        safe_name = name.replace('-', '_')
        lines.append(f'    {safe_name}["{name}"]')

    lines.append('')

    # Add edges
    lines.append('    %% Dependencies')
    for source, target in edges:
        safe_source = source.replace('-', '_')
        safe_target = target.replace('-', '_')
        lines.append(f'    {safe_source} --> {safe_target}')

    lines.append('```')

    return '\n'.join(lines)


def generate_dependency_report(
    project_dir: Path,
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Generate complete dependency analysis report.

    Args:
        project_dir: Directory to analyze
        output_dir: Where to save reports (default: meta/reports/)

    Returns:
        Dict of output file paths

    Example:
        >>> outputs = generate_dependency_report(Path('scripts/'))
        >>> print(outputs['dot'])  # Path to .dot file
        >>> print(outputs['mermaid'])  # Path to .md file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / 'meta' / 'reports'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Analyze
    modules = analyze_project_dependencies(project_dir)
    edges = get_dependency_edges(modules)

    date_str = datetime.now().strftime('%Y-%m-%d')

    # Generate DOT
    dot_content = generate_dot_graph(modules, edges, "skill-trending-monitor Dependencies")
    dot_path = output_dir / f'{date_str}-dependency-graph.dot'
    dot_path.write_text(dot_content)
    logger.info(f"DOT graph saved to: {dot_path}")

    # Generate Mermaid
    mermaid_content = generate_mermaid_graph(modules, edges, "skill-trending-monitor Dependencies")

    # Wrap in Markdown with stats
    md_content = f"""# Dependency Graph

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Statistics

- **Modules analyzed:** {len(modules)}
- **Dependencies found:** {len(edges)}

## Module Categories

| Category | Count | Modules |
|----------|-------|---------|
| Analyzers | {len([m for m in modules if m.startswith('analyze')])} | {', '.join(m for m in modules if m.startswith('analyze'))} |
| Fetchers/Parsers | {len([m for m in modules if m.startswith('fetch') or m.startswith('parse')])} | {', '.join(m for m in modules if m.startswith('fetch') or m.startswith('parse'))} |
| Utilities | {len([m for m in modules if 'validator' in m or m in ['helpers', 'cache_manager', 'rate_limiter']])} | ... |

## Dependency Graph

{mermaid_content}

## How to Use

### Render DOT (requires Graphviz)

```bash
dot -Tpng meta/reports/{date_str}-dependency-graph.dot -o meta/reports/{date_str}-dependency-graph.png
```

### View Mermaid

The graph above renders automatically on GitHub and most Markdown viewers.
"""

    md_path = output_dir / f'{date_str}-dependency-graph.md'
    md_path.write_text(md_content)
    logger.info(f"Mermaid report saved to: {md_path}")

    return {
        'dot': dot_path,
        'mermaid': md_path,
        'modules': modules,
        'edges': edges
    }


# Main for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print("=" * 70)
    print("DEPENDENCY GRAPH ANALYZER")
    print("=" * 70)

    # Analyze this project's scripts
    scripts_dir = Path(__file__).parent

    print(f"\nAnalyzing: {scripts_dir}")

    try:
        outputs = generate_dependency_report(scripts_dir)

        print(f"\n✅ Generated files:")
        print(f"   DOT:     {outputs['dot']}")
        print(f"   Mermaid: {outputs['mermaid']}")

        print(f"\n📊 Statistics:")
        print(f"   Modules: {len(outputs['modules'])}")
        print(f"   Edges:   {len(outputs['edges'])}")

        print("\n🔗 Top dependencies:")
        # Count incoming edges
        incoming = {}
        for _, target in outputs['edges']:
            incoming[target] = incoming.get(target, 0) + 1

        for module, count in sorted(incoming.items(), key=lambda x: -x[1])[:5]:
            print(f"   {module}: {count} dependents")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
```

### 2. Add Tests

Create `tests/test_dependencies.py`:

```python
#!/usr/bin/env python3
"""Tests for dependency graph analyzer."""

import pytest
from pathlib import Path
import sys

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
```

## Files to Create

1. `scripts/analyze_dependencies.py` - Main implementation
2. `tests/test_dependencies.py` - Tests

## Testing

```bash
cd skill-trending-monitor-cskill

# Run tests
python3 -m pytest tests/test_dependencies.py -v

# Run standalone
python3 scripts/analyze_dependencies.py

# Check outputs
ls -la meta/reports/*dependency*
cat meta/reports/*dependency*.md
```

## Acceptance Criteria

- [ ] `analyze_dependencies.py` created with all functions
- [ ] `tests/test_dependencies.py` passes (6+ tests)
- [ ] Standalone test generates DOT and Mermaid files
- [ ] Mermaid graph renders in GitHub/VSCode preview

## Dependencies

- No external dependencies (uses stdlib `ast`)
- Optional: Graphviz for rendering DOT to PNG

## Notes

- Uses Python's `ast` module for reliable parsing
- Groups modules into Analyzers/Fetchers/Utils categories
- Mermaid format works in GitHub README without extra tools
- DOT format can be rendered with: `dot -Tpng file.dot -o file.png`
