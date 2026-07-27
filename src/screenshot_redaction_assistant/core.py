from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT = "screenshot-redaction-assistant"


def _require(data: dict[str, Any], key: str) -> Any:
    value = data.get(key)
    if value is None or value == "" or value == []:
        raise ValueError(f"{key} is required")
    return value


def _screenshot_redaction(data: dict[str, Any]) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    source = Path(_require(data, "input")).resolve()
    output = Path(_require(data, "output")).resolve()
    if output.exists():
        raise ValueError("output already exists")
    rectangles = _require(data, "rectangles")
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        draw = ImageDraw.Draw(image)
        for rectangle in rectangles:
            box = tuple(int(rectangle[key]) for key in ("left", "top", "right", "bottom"))
            if (
                box[0] < 0
                or box[1] < 0
                or box[2] <= box[0]
                or (box[3] <= box[1])
                or (box[2] > image.width)
                or (box[3] > image.height)
            ):
                raise ValueError(f"invalid rectangle: {rectangle}")
            draw.rectangle(box, fill=tuple(data.get("color", [0, 0, 0])))
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output, format="PNG")
    return {
        "input": str(source),
        "output": str(output),
        "width": image.width,
        "height": image.height,
        "rectangles": rectangles,
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "flattened": True,
    }


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    return {"version": 1, "project": PROJECT, **_screenshot_redaction(data)}


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# {report['project'].replace('-', ' ').title()} report", ""]
    for key, value in report.items():
        if key not in {"version", "project"}:
            lines.extend(
                [
                    f"## {key.replace('_', ' ').title()}",
                    "",
                    f"```json\n{json.dumps(value, indent=2, ensure_ascii=False, default=str)}\n```",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"
