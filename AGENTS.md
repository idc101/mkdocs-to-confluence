# Agent Guide for mkdocs-to-confluence

This document provides context and instructions for AI agents working on the `mkdocs-to-confluence` repository.

## Project Overview

`mkdocs-to-confluence` is a Python-based MkDocs plugin that automatically publishes documentation to Atlassian Confluence. It handles conversion from Markdown to Confluence Storage Format (XHTML-based), manages page hierarchy, detects changes to minimize updates, and handles attachments like images.

## Technology Stack

- **Language**: Python (>=3.8)
- **Build System**: Hatchling
- **Dependency Management**: `uv` (via `Makefile`)
- **Testing**: `pytest`
- **Linting/Formatting**: `ruff`
- **Type Checking**: `mypy`

## Key Files & Directories

- **`src/mkdocs_to_confluence/`**: Core source code.
  - `plugin.py`: Main entry point for the MkDocs plugin (`MkdocsWithConfluence` class).
  - `exporter.py`: Handles the interaction with the Confluence API.
  - `_vendor/md2cf/`: Modified version of the `md2cf` library for Markdown-to-Confluence conversion.
- **`tests/`**: Test suite.
  - `test-project/`: A sample MkDocs project used for integration/dry-run tests.
- **`mkdocs.yml`**: Configuration for the project's own documentation (and used as a reference for plugin config).
- **`Makefile`**: Automation scripts for setup, testing, and maintenance.
- **`pyproject.toml`**: Project metadata, dependencies, and tool configuration.

## Development Workflow

This project uses `make` to abstract common tasks, utilizing `uv` for environment management.

### Setup
Initialize the development environment:
```bash
make py-setup
```

### Verification & Testing
Always run these commands to verify changes:

1.  **Run Tests**:
    ```bash
    make py-test
    ```
2.  **Lint & Format**:
    ```bash
    make py-ruff      # Check
    make py-ruff-fix  # Auto-fix and format
    ```
3.  **Type Check**:
    ```bash
    make py-mypy
    ```
4.  **Full Quality Check**:
    ```bash
    make quality
    ```

### Documentation
- Serve docs locally: `make docs-serve`
- Build docs: `make docs-build`

## Architecture Notes

- **Plugin Logic**: The plugin hooks into MkDocs' lifecycle events (e.g., `on_page_markdown`, `on_post_build`) to intercept content and upload it.
- **Content Conversion**: The project relies on a vendored and patched version of `md2cf` to parse Markdown and render Confluence-compatible XHTML.
- **Sync Logic**: The plugin calculates content hashes to determine if a page needs updating, preventing unnecessary API calls and version history spam in Confluence.
- **Dry Run**: A "dry run" mode allows exporting the converted content to the filesystem for inspection without uploading.

## Common Tasks

### 1. Adding a New Configuration Option
1.  Update the configuration schema in `src/mkdocs_to_confluence/plugin.py`.
2.  Update `mkdocs.yml` (if applicable) or add a test case in `tests/` to verify the option.
3.  Update the `README.md` or documentation to document the new option.

### 2. Improving Markdown Conversion
1.  Check `src/mkdocs_to_confluence/_vendor/md2cf/confluence_renderer.py` or related files in the vendor directory.
2.  Add a test case in `tests/test_parsing.py` or similar to verify the conversion.
3.  **Note**: Be careful when modifying vendored code; ensure changes are compatible or intended to diverge.

### 3. Debugging API Issues
1.  Use `tests/test_confluence_api.py` as a reference.
2.  The `exporter.py` module handles network requests. Check authentication and payload construction there.
