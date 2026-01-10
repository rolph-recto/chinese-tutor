Use uv to do anything with Python.

Read README.md to get an overview of the codebase.

Run the ruff linter whenever you write Python code, which will both
check and potentially fix issues. You can run ruff this way:
```
uvx ruff check --fix
```
Address any remaining issues that ruff does not automatically fix.

Whenever you add a new feature, be sure to add tests using the existing Pytest harness to check functionality. Run tests using the following command:
```
uv run pytest -v
```

Add plans you make in the plan/ directory.

Add specifications you make in the specs/ directory.
