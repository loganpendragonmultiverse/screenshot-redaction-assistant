# Screenshot Redaction Assistant

[![CI](https://github.com/loganpendragonmultiverse/screenshot-redaction-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/screenshot-redaction-assistant/actions/workflows/ci.yml)

Redact screenshots locally into flattened PNG files with visual previews and detailed audit evidence. Version 1.1 supports one image, explicit job batches, recursive directories, reusable rectangle recipes, terminal review and correction, and optional local OCR suggestions for email addresses, phone-like text, IP addresses, and token-like strings.

## Three-minute start

```bash
python -m pip install .
redact-screenshot examples/sample.json --preview-dir previews --output audit.md
redact-screenshot --input-dir screenshots --output-dir redacted --recipe examples/recipe.json --recursive --review
```

Install `.[ocr]` plus a local Tesseract executable to use `--suggest-ocr`. OCR candidates are never silently applied: use `--review` to keep, skip, replace, or add rectangles. Preview images outline rectangles without flattening them; only final outputs permanently cover pixels.

## Batch and recipes

A specification may contain one job or a `jobs` array. A top-level `recipe` supplies reusable rectangles and color settings that individual jobs can override. Directory mode discovers PNG, JPEG, and WebP images and reproduces their relative paths as flattened PNG outputs. Existing previews, images, and reports are never overwritten.

Every result records rectangle IDs, reasons, origins, coordinates, pixel totals, dimensions, fill color, review status, and input/output SHA-256 hashes.

## Privacy and interpretation boundary

The tool runs locally and does not upload images, include telemetry, or require an account. OCR uses the operator's local Tesseract installation. Redaction is permanent only in the exported flattened PNG. OCR can miss sensitive text or produce false positives; recipes can be wrong for images with different dimensions; rectangle pixel totals can overlap. Operators must inspect every final image and avoid sharing originals or previews.

## Development

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
mypy src
pytest
python -m build
```

Python 3.10 or newer is supported on Windows, macOS, and Linux. Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).
