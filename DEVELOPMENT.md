# Development contract

Redact screenshots locally and export flattened PNG results with preview, review, batch, recipe, optional local OCR suggestion, and audit workflows.

Preserve deterministic, source-safe behavior and the interpretation boundary documented in the README. OCR output remains a suggestion requiring review; previews are not redacted deliverables; final outputs are flattened and never replace originals. Every feature release must update tests, version metadata, changelog, README claims, repository metadata, release assets, and the Forge catalog together.

## 1.2.0 improvement session

Add a local canvas editor with distinct original/preview/final states, guarded normalized recipes, exact union coverage and optional output metadata review.

--editor writes a local HTML editor for one job (maximum 16 million pixels), without creating a final output. Draw, move or resize rectangles, edit numeric bounds, and explicitly accept or remove every rectangle before downloading a flattened final PNG or normalized recipe. The HTML embeds the original image and must not be shared as a redacted result. Recipes use reference_size [width,height], normalized_rectangles with finite 0..1 exclusive bounds, and allow_scale false by default; scaling requires explicit true and matching aspect ratio, with bounds rounded outward. Overlapping redacted_pixels_total now counts the pixel union and drawing follows exclusive right/bottom bounds. --metadata-review reports output metadata field names and EXIF counts without values; CLI final PNGs are rebuilt from fresh RGB pixels. Existing source/output protections and opt-in OCR suggestions remain.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.
