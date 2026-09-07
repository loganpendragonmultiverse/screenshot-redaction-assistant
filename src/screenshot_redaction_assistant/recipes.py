from __future__ import annotations

import math
from itertools import pairwise
from typing import Any


def expand_recipe(job: dict[str, Any], width: int, height: int) -> list[dict[str, Any]]:
    normalized = job.get("normalized_rectangles")
    if normalized is None:
        return list(job.get("rectangles", []))
    reference = job.get("reference_size")
    if (
        not isinstance(reference, list)
        or len(reference) != 2
        or any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in reference)
    ):
        raise ValueError(
            "normalized recipe requires positive integer reference_size [width,height]"
        )
    if not isinstance(job.get("allow_scale", False), bool):
        raise TypeError("allow_scale must be a boolean")
    if reference != [width, height] and not job.get("allow_scale", False):
        raise ValueError("recipe resolution differs; explicit allow_scale is required")
    if abs(width / reference[0] - height / reference[1]) > 0.001:
        raise ValueError("recipe aspect ratio differs; review rectangles for this image")
    if not isinstance(normalized, list) or not normalized:
        raise ValueError("normalized_rectangles must be a non-empty array")
    result = list(job.get("rectangles", []))
    for item in normalized:
        if not isinstance(item, dict):
            raise TypeError("normalized rectangle must be an object")
        values = [item.get(k) for k in ("left", "top", "right", "bottom")]
        if any(
            not isinstance(v, (int, float))
            or isinstance(v, bool)
            or not math.isfinite(v)
            or not 0 <= v <= 1
            for v in values
        ):
            raise ValueError("normalized bounds must be finite numbers between 0 and 1")
        left, top, right, bottom = [float(item[k]) for k in ("left", "top", "right", "bottom")]
        if right <= left or bottom <= top:
            raise ValueError("normalized rectangle must have positive area")
        result.append(
            {
                **item,
                "left": math.floor(left * width),
                "top": math.floor(top * height),
                "right": math.ceil(right * width),
                "bottom": math.ceil(bottom * height),
                "origin": "normalized-recipe",
            }
        )
    return result


def union_pixels(rectangles: list[dict[str, Any]]) -> int:
    xs = sorted({r[k] for r in rectangles for k in ("left", "right")})
    total = 0
    for left, right in pairwise(xs):
        spans = sorted(
            (r["top"], r["bottom"]) for r in rectangles if r["left"] < right and r["right"] > left
        )
        covered = 0
        end = -1
        for top, bottom in spans:
            covered += max(0, bottom - max(top, end))
            end = max(end, bottom)
        total += (right - left) * covered
    return total
