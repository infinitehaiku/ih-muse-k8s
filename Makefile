.PHONY: install
install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using virtualenv"
	@uv run python -m virtualenv .venv
	@uv sync --group dev
	@uv run pre-commit install


.PHONY: check-pre-commit
check-pre-commit:
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a

.PHONY: check-python
check-python: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@uv run deptry .

.PHONY: check
check: check-python check-pre-commit

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@uvx --from build pyproject-build --installer uv

.PHONY: clean-build
clean-build: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@uv run python -c "import shutil; import os; shutil.rmtree('dist') if os.path.exists('dist') else None"

.PHONY: publish
publish: ## Publish a release to PyPI.
	@echo "🚀 Publishing."
	@uvx twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docs-install
docs-install: ## Install dependencies for building documentation
	@echo "🚀 Installing documentation dependencies"
	@uv sync --group docs

.PHONY: docs-build
docs-build: docs-install ## Build the documentation
	@echo "🚀 Building documentation"
	@uv run pip install -e ./py-ih-muse
	@uv run python -m sphinx -b html docs/ docs/_build/html || \
		uv run sphinx-build -b html docs/ docs/_build/html

.PHONY: docs-serve
docs-serve: docs-build ## Serve the documentation locally
	@echo "🚀 Serving documentation at http://localhost:8000"
	@uv run python -m http.server --directory docs/_build/html 8000

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
