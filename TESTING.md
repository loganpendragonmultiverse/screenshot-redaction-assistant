# Testing

Run `python -m pip install -e ".[dev]"`, then `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, and `python -m build`.

Tests cover flattened pixels, replacement safety, detailed manifests, multi-job specifications, recursive directory recipes, previews, review keep/skip/replace/add behavior, pure OCR suggestion classification, invalid rectangles and colors, CLI modes, and supported image discovery. Native OCR execution is optional and is not claimed by CI; the deterministic OCR-to-rectangle adapter is tested without requiring Tesseract.
