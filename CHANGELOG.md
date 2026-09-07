# Changelog

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
