# Testing

Run `python -m pip install -e ".[dev]"`, then `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, and `python -m build`.

Tests cover flattened pixels, replacement safety, detailed manifests, multi-job specifications, recursive directory recipes, previews, review keep/skip/replace/add behavior, pure OCR suggestion classification, invalid rectangles and colors, CLI modes, and supported image discovery. Native OCR execution is optional and is not claimed by CI; the deterministic OCR-to-rectangle adapter is tested without requiring Tesseract.

## 1.2.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Add a local canvas editor with distinct original/preview/final states, guarded normalized recipes, exact union coverage and optional output metadata review.

## 1.3.0 acceptance

Save and restore unfinished local rectangle reviews without treating drafts as redacted deliverables.

Verify Download explicit private review drafts containing bounds, selected rectangle and acceptance flags; Bind drafts to the exact original source image and dimensions, validating all data before replacing review state; Preserve pending-rectangle final-export guards and warn about unsaved edits; Reject oversized, malformed and mismatched-image drafts without altering the current review. Run the full existing quality and build gates; release only through protected PR checks and verified tag artifacts.

## 1.3.1 recovery acceptance

Verify multi-image validation, preview/image/report destination collisions, missing and unwritable report destinations, staging failures, reservation races, partial writes, concurrent replacement/edit preservation, stdout failure and successful retry. Decode flattened PNGs and verify manifest hashes and source bytes. Run installed-wheel acceptance as well as the full source gates.

## 1.3.2 alpha-safe flattening

Composite RGBA and palette transparency against opaque white before rendering previews, final PNGs and browser editor pixels. Verify hidden RGB cannot become visible, partial alpha matches the documented matte, editor/CLI pixels agree, metadata is dropped and source bytes/fingerprints remain unchanged. Run source gates and actual tagged-wheel/browser acceptance before publishing.

## 1.4.0 acceptance

- Require terminal or browser review before applying OCR suggestions; interrupted terminal review leaves no outputs.
- Use a shared EXIF display coordinate policy for image rendering, OCR, previews and recipes, with an explicit raw policy for legacy geometry and guarded version 1/2 draft imports.
- Export a browser audit bound to the final PNG hash; keep configured fill colors in browser previews, exports and recipes.
- Document audit privacy and add oriented-image, review-gate and three-browser regressions.

Run the complete source gates and installed built-wheel tests. Run `tests/browser_fixtures.py` with the installed package and a fresh private output directory, then `tests/browser_acceptance.mjs` in Chromium, Firefox and WebKit. These fixtures are synthetic. Protected CI and independent exact-head review remain required before release.

With Playwright and its three browser engines available, use:

```bash
python tests/browser_fixtures.py /tmp/fresh-browser-fixtures
FIXTURE_DIR=/tmp/fresh-browser-fixtures node tests/browser_acceptance.mjs
```

For an external Playwright installation, set `PLAYWRIGHT_MODULE` to its absolute `index.mjs` path. Browser JSON receipts and downloaded test artifacts stay in the fixture directory. Use a new directory for another run so output protection remains exercised. Apply exported recipes to their matching synthetic source and compare decoded PNG pixels.
