# Install dependencies
install:
	poetry install

# Format code with black
format:
	poetry run black .

# Lint code with flake8
lint:
	poetry run flake8 app tests --select=F401

# Type checking with mypy
type:
	poetry run mypy app

# Run tests
test:
	poetry run pytest tests/

# Run tests with coverage
test-cov:
	poetry run pytest --cov=app --cov-report=term-missing tests/

# Run all checks (format, lint, type)
check: format lint type

