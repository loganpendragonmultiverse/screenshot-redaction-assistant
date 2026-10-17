from __future__ import annotations

import base64
import hashlib
import io
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from PIL import Image

from .core import _color, _coordinate_space, _opaque_image, _rectangle


def render_editor(job: dict[str, Any]) -> str:
    source_bytes = Path(job["input"]).read_bytes()
    with Image.open(io.BytesIO(source_bytes)) as opened:
        if opened.width * opened.height > 16_000_000:
            raise ValueError("editor is limited to 16 million pixels")
        coordinate_space = _coordinate_space(job, opened)
        orientation = opened.getexif().get(274, 1)
        image = _opaque_image(opened, coordinate_space)
        rectangles = [
            _rectangle(r, image.width, image.height, i)
            for i, r in enumerate(job.get("rectangles", []), 1)
        ]
        buffer = io.BytesIO()
        Image.frombytes("RGB", image.size, image.tobytes()).save(buffer, format="PNG")
    data = {
        "coordinate_space": coordinate_space,
        "exif_orientation": orientation,
        "color": list(_color(job.get("color", [0, 0, 0]))),
        "image": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(),
        "rectangles": rectangles,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "reference_size": [image.width, image.height],
    }
    payload = (
        json.dumps(data, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return (
        files("screenshot_redaction_assistant")
        .joinpath("editor.html")
        .read_text(encoding="utf-8")
        .replace("__EDITOR_DATA__", payload)
    )
