from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROJECT = "screenshot-redaction-assistant"
VERSION = 2
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_OCR_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "phone": re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)"),
    "token-like": re.compile(r"\b[A-Za-z0-9_-]{24,}\b"),
}


def _require(data: dict[str, Any], key: str) -> Any:
    value = data.get(key)
    if value is None or value == "" or value == []:
        raise ValueError(f"{key} is required")
    return value


def _color(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("color must contain three RGB integers")
    color = tuple(value)
    if any(
        not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= 255
        for item in color
    ):
        raise ValueError("color must contain three RGB integers from 0 to 255")
    return int(color[0]), int(color[1]), int(color[2])


def _rectangle(raw: Any, width: int, height: int, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TypeError("each rectangle must be an object")
    box = tuple(int(_require(raw, key)) for key in ("left", "top", "right", "bottom"))
    if (
        box[0] < 0
        or box[1] < 0
        or box[2] <= box[0]
        or box[3] <= box[1]
        or box[2] > width
        or box[3] > height
    ):
        raise ValueError(f"invalid rectangle: {raw}")
    return {
        "id": str(raw.get("id", f"R-{index}")),
        "left": box[0],
        "top": box[1],
        "right": box[2],
        "bottom": box[3],
        "reason": str(raw.get("reason", "unspecified")),
        "origin": str(raw.get("origin", "manual")),
        "pixels": (box[2] - box[0]) * (box[3] - box[1]),
    }


def _ocr_candidates(
    data: dict[str, list[Any]], patterns: dict[str, re.Pattern[str]] | None = None
) -> list[dict[str, Any]]:
    patterns = patterns or DEFAULT_OCR_PATTERNS
    required = ("text", "left", "top", "width", "height")
    if any(key not in data for key in required):
        raise ValueError("OCR data is missing position fields")
    suggestions: list[dict[str, Any]] = []
    for index, text in enumerate(data["text"]):
        value = str(text).strip()
        reasons = [name for name, pattern in patterns.items() if pattern.search(value)]
        if not reasons:
            continue
        left, top = int(data["left"][index]), int(data["top"][index])
        suggestions.append(
            {
                "left": left,
                "top": top,
                "right": left + int(data["width"][index]),
                "bottom": top + int(data["height"][index]),
                "reason": ", ".join(reasons),
                "origin": "ocr-suggestion",
            }
        )
    return suggestions


def suggest_ocr(source: Path) -> list[dict[str, Any]]:  # pragma: no cover - optional native adapter
    try:
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image
    except ImportError as exc:
        raise ValueError(
            "OCR suggestions require the optional 'ocr' dependencies and local Tesseract"
        ) from exc
    with Image.open(source) as image:
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        except Exception as exc:
            raise ValueError(f"local OCR failed: {exc}") from exc
    return _ocr_candidates(data)


def build_jobs(data: dict[str, Any], ocr: bool = False) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise TypeError("input specification must be an object")
    recipe = data.get("recipe", {})
    if not isinstance(recipe, dict):
        raise TypeError("recipe must be an object")
    raw_jobs = data.get("jobs", [data])
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise ValueError("jobs must be a non-empty array")
    jobs: list[dict[str, Any]] = []
    for raw in raw_jobs:
        if not isinstance(raw, dict):
            raise TypeError("each job must be an object")
        job = {**recipe, **raw}
        source = Path(_require(job, "input")).resolve()
        rectangles = list(job.get("rectangles", []))
        if ocr:
            rectangles.extend(suggest_ocr(source))
        job["rectangles"] = rectangles
        jobs.append(job)
    return jobs


def directory_jobs(
    input_dir: Path, output_dir: Path, recipe: dict[str, Any], recursive: bool
) -> list[dict[str, Any]]:
    input_dir, output_dir = input_dir.resolve(), output_dir.resolve()
    if not input_dir.is_dir():
        raise ValueError("input directory does not exist")
    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    paths = [
        path
        for path in sorted(iterator)
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
    ]
    if not paths:
        raise ValueError("input directory contains no supported images")
    return [
        {
            **recipe,
            "input": str(path),
            "output": str(output_dir / path.relative_to(input_dir).with_suffix(".png")),
        }
        for path in paths
    ]


def review_rectangles(
    rectangles: list[dict[str, Any]], prompt: Callable[[str], str] = input
) -> list[dict[str, Any]]:
    reviewed: list[dict[str, Any]] = []
    for rectangle in rectangles:
        answer = prompt(
            f"{rectangle.get('reason', 'rectangle')} {rectangle['left']},{rectangle['top']},"
            f"{rectangle['right']},{rectangle['bottom']} [Enter keep / s skip / l,t,r,b replace]: "
        ).strip()
        if answer.casefold() == "s":
            continue
        if answer:
            parts = answer.split(",")
            if len(parts) != 4:
                raise ValueError("replacement rectangle must be left,top,right,bottom")
            rectangle = {
                **rectangle,
                **dict(zip(("left", "top", "right", "bottom"), map(int, parts), strict=True)),
                "origin": "review-correction",
            }
        reviewed.append(rectangle)
    while True:
        answer = prompt("Add rectangle as left,top,right,bottom or press Enter to finish: ").strip()
        if not answer:
            break
        parts = answer.split(",")
        if len(parts) != 4:
            raise ValueError("new rectangle must be left,top,right,bottom")
        reviewed.append(
            {
                **dict(zip(("left", "top", "right", "bottom"), map(int, parts), strict=True)),
                "reason": "review-added",
                "origin": "review-added",
            }
        )
    return reviewed


def write_preview(job: dict[str, Any], target: Path) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    source = Path(_require(job, "input")).resolve()
    target = target.resolve()
    if target.exists():
        raise ValueError(f"preview already exists: {target}")
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        draw = ImageDraw.Draw(image)
        rectangles = [
            _rectangle(item, image.width, image.height, index)
            for index, item in enumerate(_require(job, "rectangles"), 1)
        ]
        for rectangle in rectangles:
            box = tuple(rectangle[key] for key in ("left", "top", "right", "bottom"))
            draw.rectangle(box, outline=(255, 0, 0), width=3)
            draw.text(
                (rectangle["left"] + 2, rectangle["top"] + 2), rectangle["id"], fill=(255, 0, 0)
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format="PNG")
    return {
        "preview": str(target),
        "preview_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "rectangles": len(rectangles),
    }


def _redact(job: dict[str, Any]) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    source = Path(_require(job, "input")).resolve()
    output = Path(_require(job, "output")).resolve()
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    color = _color(job.get("color", [0, 0, 0]))
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        rectangles = [
            _rectangle(item, image.width, image.height, index)
            for index, item in enumerate(_require(job, "rectangles"), 1)
        ]
        draw = ImageDraw.Draw(image)
        for rectangle in rectangles:
            draw.rectangle(
                tuple(rectangle[key] for key in ("left", "top", "right", "bottom")), fill=color
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output, format="PNG")
    return {
        "input": str(source),
        "output": str(output),
        "width": image.width,
        "height": image.height,
        "color": list(color),
        "rectangles": rectangles,
        "redacted_pixels_total": sum(item["pixels"] for item in rectangles),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "flattened": True,
        "reviewed": bool(job.get("reviewed", False)),
    }


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    results = [_redact(job) for job in build_jobs(data)]
    return {
        "schema_version": VERSION,
        "project": PROJECT,
        "job_count": len(results),
        "results": results,
        "all_flattened": all(item["flattened"] for item in results),
        "review_required": True,
    }


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Screenshot Redaction Assistant report", "", f"Jobs: {report['job_count']}", ""]
    for index, result in enumerate(report["results"], 1):
        lines += [
            f"## Job {index}",
            "",
            f"- Input: `{result['input']}`",
            f"- Output: `{result['output']}`",
            f"- Rectangles: {len(result['rectangles'])}",
            f"- Input SHA-256: `{result['input_sha256']}`",
            f"- Output SHA-256: `{result['output_sha256']}`",
            f"- Reviewed interactively: {'yes' if result['reviewed'] else 'no'}",
            "",
        ]
    lines += ["The flattened outputs still require visual inspection before sharing.", ""]
    return "\n".join(lines)
