# List all available commands
default:
    @just --list

# Install dependencies in development mode
install:
    uv sync --dev
    uvx prek install

# Format all code
format:
    just --fmt --unstable
    uvx ruff format
    uvx ruff check --fix

# Lint checking (without auto-fix)
lint:
    uvx ruff check .

# Type check
check:
    uvx ty check

# Run tests (quick, no coverage)
test:
    uv run pytest

# Run tests with coverage
cov:
    uv run pytest --cov=agent_caster --cov-report=term-missing
    uv run coverage xml

# Run pre-commit on all files
pre-commit:
    uvx prek run --all-files

# Full CI check (format + lint + check + test)
ci: format lint check test

# Clean build artifacts
clean:
    rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ .coverage htmlcov/ coverage.xml
    find . -name "__pycache__" -type d -exec rm -rf {} +
    find . -name "*.pyc" -delete
