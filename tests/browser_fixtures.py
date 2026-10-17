"""Generate small synthetic browser fixtures with the installed package."""

import sys
from pathlib import Path

from PIL import Image

from screenshot_redaction_assistant.core import analyze
from screenshot_redaction_assistant.editor import render_editor

root = Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
for orientation in (3, 6):
    source = root / f"source{orientation}.jpg"
    image = Image.new("RGB", (20, 40), "white")
    image.paste("red", (0, 0, 10, 20))
    exif = image.getexif()
    exif[274] = orientation
    image.save(source, exif=exif)
    for policy in ("raw-v1", "exif-display-v1"):
        stem = f"screen-{'raw' if policy == 'raw-v1' else 'display'}{orientation}"
        job = {
            "input": str(source),
            "output": str(root / f"{stem}-cli.png"),
            "coordinate_space": policy,
            "color": [12, 34, 56],
            "rectangles": [{"left": 1, "top": 2, "right": 5, "bottom": 6}],
        }
        (root / f"{stem}.html").write_text(render_editor(job), encoding="utf-8")
        analyze(job)
