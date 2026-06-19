.PHONY: lint

lint:
	ruff check .
	ruff format --check .
	pyright
	pytest
