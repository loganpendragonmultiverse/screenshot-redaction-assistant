from __future__ import annotations

import base64
import io
import json
from importlib.resources import files
from typing import Any

from PIL import Image

from .core import _rectangle


def render_editor(job: dict[str, Any]) -> str:
    with Image.open(job["input"]) as opened:
        if opened.width * opened.height > 16_000_000:
            raise ValueError("editor is limited to 16 million pixels")
        image = opened.convert("RGB")
        rectangles = [
            _rectangle(r, image.width, image.height, i)
            for i, r in enumerate(job.get("rectangles", []), 1)
        ]
        buffer = io.BytesIO()
        Image.frombytes("RGB", image.size, image.tobytes()).save(buffer, format="PNG")
    data = {
        "image": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(),
        "rectangles": rectangles,
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
