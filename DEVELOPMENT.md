# Development contract

Redact screenshots locally and export flattened PNG results with preview, review, batch, recipe, optional local OCR suggestion, and audit workflows.

Preserve deterministic, source-safe behavior and the interpretation boundary documented in the README. OCR output remains a suggestion requiring review; previews are not redacted deliverables; final outputs are flattened and never replace originals. Every feature release must update tests, version metadata, changelog, README claims, repository metadata, release assets, and the Forge catalog together.

## 1.2.0 improvement session

Add a local canvas editor with distinct original/preview/final states, guarded normalized recipes, exact union coverage and optional output metadata review.

--editor writes a local HTML editor for one job (maximum 16 million pixels), without creating a final output. Draw, move or resize rectangles, edit numeric bounds, and explicitly accept or remove every rectangle before downloading a flattened final PNG or normalized recipe. The HTML embeds the original image and must not be shared as a redacted result. Recipes use reference_size [width,height], normalized_rectangles with finite 0..1 exclusive bounds, and allow_scale false by default; scaling requires explicit true and matching aspect ratio, with bounds rounded outward. Overlapping redacted_pixels_total now counts the pixel union and drawing follows exclusive right/bottom bounds. --metadata-review reports output metadata field names and EXIF counts without values; CLI final PNGs are rebuilt from fresh RGB pixels. Existing source/output protections and opt-in OCR suggestions remain.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.

## 1.3.0 acceptance

Save and restore unfinished local rectangle reviews without treating drafts as redacted deliverables.

Generate an editor with `redact-screenshot job.json --editor review.html`. Save unfinished review draft works before all rectangles are accepted. Reopen an editor generated from the same exact source image, choose Restore review draft and continue reviewing. Drafts contain geometry, a source-file fingerprint and acceptance assertions; they contain no image pixels, but remain private and are never a redacted deliverable. A hash is identity evidence, not an authenticity signature: a deliberately edited draft can forge acceptance flags. Restoring a valid draft with unsaved changes requires explicit replacement confirmation. Imports are limited to 2 MiB/5,000 rectangles and reject unknown versions, wrong images, invalid bounds and non-boolean acceptance before changing state. Any source-byte change, even image metadata, requires a fresh review. No automatic browser storage or upload is added. Final PNG/recipe exports still require every rectangle accepted or removed.

## 1.3.1 output recovery

Stage all PNGs, previews and the optional audit before reserving destination names exclusively. Roll back only unchanged files created by this command; preserve existing and concurrent files. Do not promise power-loss atomicity.

## Gold Star requalification — October 17, 2026

The published v1.3.1 closes the identified ordinary output-failure/retry gap within the original local screenshot review and flattened-export purpose. The exact tagged wheel passed all 41 regression/acceptance tests without skips, including non-admin image, preview and audit destination failures followed by retries. Protected platform CI and CodeQL passed on the reviewed PR and merged release commit. Fresh Chromium, Firefox and WebKit checks passed review-draft restore, pending-export guards, accepted PNG/recipe exports and decoded final pixels. Public wheel, source distribution and checksum assets match their verified digests.

No identified meaningful feature remains unfinished within the documented purpose. OCR remains an optional suggestion requiring operator review; final images still require inspection. Maintenance, future compatibility and useful new ideas remain welcome. Output recovery covers ordinary errors and is not a power-loss transaction or a guarantee against hostile filesystem mutation.
