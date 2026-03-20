# List all available commands
default:
    @just --list

# Install dependencies in development mode
install:
    uv sync
    uvx prek install

# Format all code
format:
    just --fmt --unstable
    uvx ruff format
    uvx ruff check --fix

# Type check
check:
    uvx ruff check .
    uvx ty check .

# Run tests (quick, no coverage)
test:
    uv run python -m pytest

# Run tests with coverage
cov:
    uv run python -m pytest --cov=role_forge --cov-report=term-missing
    uv run python -m coverage xml

# Run CodSpeed benchmarks
bench:
    uv run --with pytest-codspeed python -m pytest tests/test_topology.py --codspeed

# Run pre-commit on all files
pre-commit:
    uvx prek run --all-files

# Full CI check (format + check + test)
ci: pre-commit format check test

# Clean build artifacts
clean:
    rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ .coverage htmlcov/ coverage.xml
    find . -name "__pycache__" -type d -exec rm -rf {} +
    find . -name "*.pyc" -delete
