# Codex Task M3: Add GitHub Actions CI/CD Workflow

## Priority
Medium

## Objective
Create a GitHub Actions workflow that runs tests and linting on push/PR.

## Context
- Python 3.10+ project
- pytest for testing
- No existing CI/CD

## Requirements

### 1. Create `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          python -m pytest tests/ -v --tb=short

      - name: Run tests with coverage
        if: matrix.python-version == '3.11'
        run: |
          python -m pytest tests/ --cov=scripts --cov-report=xml --cov-report=term-missing

      - name: Upload coverage to Codecov
        if: matrix.python-version == '3.11'
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
        continue-on-error: true

  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install linting tools
        run: |
          python -m pip install --upgrade pip
          pip install flake8 black isort

      - name: Check code formatting with Black
        run: |
          black --check --diff scripts/ tests/
        continue-on-error: true

      - name: Check import sorting with isort
        run: |
          isort --check-only --diff scripts/ tests/
        continue-on-error: true

      - name: Lint with flake8
        run: |
          # Stop build if there are Python syntax errors or undefined names
          flake8 scripts/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
          # Exit-zero treats all errors as warnings
          flake8 scripts/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics

  validate-config:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Validate JSON configs
        run: |
          python3 -c "import json; json.load(open('assets/config.json'))"
          python3 -c "import json; json.load(open('assets/filters.json'))"
          echo "✅ All JSON configs are valid"
```

### 2. Create `.github/workflows/security.yml`

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  schedule:
    # Run weekly on Monday at 00:00 UTC
    - cron: '0 0 * * 1'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install security tools
        run: |
          python -m pip install --upgrade pip
          pip install bandit safety

      - name: Run Bandit security linter
        run: |
          bandit -r scripts/ -ll --skip B101
        continue-on-error: true

      - name: Check dependencies for vulnerabilities
        run: |
          pip install -r requirements.txt
          safety check --full-report
        continue-on-error: true
```

### 3. Add CI Badge to README

Add at the top of `README.md` (after the title):

```markdown
![CI](https://github.com/YOUR_USERNAME/skill-trending-monitor-cskill/actions/workflows/ci.yml/badge.svg)
```

Note: Replace `YOUR_USERNAME` with actual GitHub username when repo is published.

### 4. Create `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "python"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "ci"
```

## Files to Create

1. `.github/workflows/ci.yml` - Main CI workflow
2. `.github/workflows/security.yml` - Security scanning
3. `.github/dependabot.yml` - Dependency updates

## Files to Modify

1. `README.md` - Add CI badge (at the top)

## Directory Structure

```
.github/
├── workflows/
│   ├── ci.yml
│   └── security.yml
└── dependabot.yml
```

## Testing (Local Validation)

```bash
cd skill-trending-monitor-cskill

# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/security.yml'))"
python3 -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"

# Run tests locally (what CI will run)
python3 -m pytest tests/ -v
```

Note: Requires `pip install pyyaml` for YAML validation.

## Acceptance Criteria

- [ ] `.github/workflows/ci.yml` created
- [ ] `.github/workflows/security.yml` created
- [ ] `.github/dependabot.yml` created
- [ ] All YAML files are valid syntax
- [ ] README has CI badge placeholder

## Dependencies

None - standalone task

## Notes

- Workflows use `continue-on-error: true` for non-critical checks (formatting)
- Security scan runs weekly to catch new vulnerabilities
- Coverage only runs on Python 3.11 to avoid duplicate uploads
- Badge will show "no status" until repo is pushed to GitHub
