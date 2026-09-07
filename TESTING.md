# Testing

Run `python -m pip install -e ".[dev]"`, then `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, and `python -m build`.

Tests cover flattened pixels, replacement safety, detailed manifests, multi-job specifications, recursive directory recipes, previews, review keep/skip/replace/add behavior, pure OCR suggestion classification, invalid rectangles and colors, CLI modes, and supported image discovery. Native OCR execution is optional and is not claimed by CI; the deterministic OCR-to-rectangle adapter is tested without requiring Tesseract.

## 1.2.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Add a local canvas editor with distinct original/preview/final states, guarded normalized recipes, exact union coverage and optional output metadata review.
