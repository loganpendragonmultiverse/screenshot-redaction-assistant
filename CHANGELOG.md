# Changelog

## 1.3.2

- Composite transparent pixels against an explicit white matte before preview, redaction and browser review/export, preventing hidden RGB channels from becoming visible.
- Preserve exact source hashes, metadata-free final images and ordinary export recovery.

## 1.3.1

- Stage and exclusively reserve all batch images, previews and audit outputs.
- Recover ordinary failed exports without deleting existing or concurrently changed files, enabling safe retry after correcting a destination.
- Preserve source images, flattened pixel-only output, metadata review and local editor behavior.

## 1.3.0 - 2026-10-17

- Reject fractional, boolean and string pixel bounds rather than silently coercing them.

- Download explicit private review drafts containing bounds, selected rectangle and acceptance flags
- Bind drafts to the exact original source image and dimensions, validating all data before replacing review state
- Preserve pending-rectangle final-export guards and warn about unsaved edits
- Reject oversized, malformed and mismatched-image drafts without altering the current review

## 1.2.0 - 2026-09-07

- Add a local canvas editor with distinct original/preview/final states, guarded normalized recipes, exact union coverage and optional output metadata review.
- Added regression coverage for the audited behavior and invalid inputs.

## 1.1.0 - 2026-08-03

- Added explicit multi-job and recursive directory batches with reusable rectangle and color recipes.
- Added outlined preview PNGs and terminal review that can keep, skip, replace, or add rectangles before redaction.
- Added optional local OCR suggestions for email, phone-like, IP, and token-like text without silently accepting any suggestion.
- Expanded audit evidence with rectangle identifiers, reasons, origins, dimensions, pixel totals, fill color, review state, and input/output hashes.
- Raised the Pillow runtime floor to the current fixed 12.3 release line after dependency review.

## 1.0.0 - 2026-07-26

- Released the first complete Screenshot Redaction Assistant command-line workflow.
- Added deterministic reporting, representative examples, cross-platform tests, and explicit limitations.
