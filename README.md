# Screenshot Redaction Assistant

> ⭐ **Gold Star Project**
> I consider this project complete. Fixes, maintenance and good new ideas are still welcome.
> [About Gold Stars](https://www.loganpendragonforge.com/open-source/?gold=1)
>
> Cover private details in screenshots, review each redaction and save a flattened image.

## What you can do

- Draw, move and resize redaction rectangles locally.
- Save an unfinished review and reopen it with the matching source image.
- Export the final image only after every rectangle has been accepted.


## Current release 1.3.2

Transparent images are composited against an opaque white matte before CLI redaction, previews or browser review/export. Fully transparent RGB content stays invisible; partially transparent pixels preserve their appearance over white. Audit reports record `transparency_matte: [255, 255, 255]`. Source bytes and the source-bound draft fingerprint remain unchanged. Final images still require inspection.

## Output recovery in 1.3.1

Batch images, previews and audit reports are staged together. Ordinary write or delivery failures remove only unchanged files created by the command, so a corrected destination can be retried. Existing files, dangling symlinks and concurrent replacements are preserved. Empty output directories may remain; this is not a power-loss transaction.

## Review drafts in 1.3.0

Save and restore unfinished local rectangle reviews without treating drafts as redacted deliverables.

Generate an editor with `redact-screenshot job.json --editor review.html`. Save unfinished review draft works before all rectangles are accepted. Reopen an editor generated from the same exact source image, choose Restore review draft and continue reviewing. Drafts contain geometry, a source-file fingerprint and acceptance assertions; they contain no image pixels, but remain private and are never a redacted deliverable. A hash is identity evidence, not an authenticity signature: a deliberately edited draft can forge acceptance flags. Restoring a valid draft with unsaved changes requires explicit replacement confirmation. Imports are limited to 2 MiB/5,000 rectangles and reject unknown versions, wrong images, invalid bounds and non-boolean acceptance before changing state. Any source-byte change, even image metadata, requires a fresh review. No automatic browser storage or upload is added. Final PNG/recipe exports still require every rectangle accepted or removed.

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

## Updates in 1.2.0

Add a local canvas editor with distinct original/preview/final states, guarded normalized recipes, exact union coverage and optional output metadata review.

```bash
redact-screenshot job.json --editor review.html
```

--editor writes a local HTML editor for one job (maximum 16 million pixels), without creating a final output. Draw, move or resize rectangles, edit numeric bounds, and explicitly accept or remove every rectangle before downloading a flattened final PNG or normalized recipe. The HTML embeds the original image and must not be shared as a redacted result. Recipes use reference_size [width,height], normalized_rectangles with finite 0..1 exclusive bounds, and allow_scale false by default; scaling requires explicit true and matching aspect ratio, with bounds rounded outward. Overlapping redacted_pixels_total now counts the pixel union and drawing follows exclusive right/bottom bounds. --metadata-review reports output metadata field names and EXIF counts without values; CLI final PNGs are rebuilt from fresh RGB pixels. Existing source/output protections and opt-in OCR suggestions remain.
