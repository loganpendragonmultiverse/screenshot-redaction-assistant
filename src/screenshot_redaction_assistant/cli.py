from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import (
    analyze,
    build_jobs,
    directory_jobs,
    render_json,
    render_markdown,
    review_rectangles,
    write_preview,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Redact one or more screenshots with reviewable evidence."
    )
    parser.add_argument("spec", nargs="?", type=Path, help="UTF-8 JSON job or batch specification")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--recipe", type=Path)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--suggest-ocr", action="store_true")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--preview-dir", type=Path)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="write the audit report")
    args = parser.parse_args(argv)
    try:
        recipe = json.loads(args.recipe.read_text(encoding="utf-8")) if args.recipe else {}
        if args.input_dir or args.output_dir:
            if not args.input_dir or not args.output_dir:
                raise ValueError("--input-dir and --output-dir must be used together")
            jobs = directory_jobs(args.input_dir, args.output_dir, recipe, args.recursive)
            data: dict[str, Any] = {"jobs": jobs}
        elif args.spec:
            loaded = json.loads(args.spec.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise TypeError("input specification must be an object")
            data = loaded
            if recipe:
                data = {**data, "recipe": {**data.get("recipe", {}), **recipe}}
        else:
            raise ValueError("provide a specification or an input and output directory")
        jobs = build_jobs(data, ocr=args.suggest_ocr)
        if args.review:
            for job in jobs:
                job["rectangles"] = review_rectangles(job["rectangles"])
                job["reviewed"] = True
        if args.preview_dir:
            for index, job in enumerate(jobs, 1):
                write_preview(job, args.preview_dir / f"preview-{index}.png")
        report = analyze({"jobs": jobs})
        rendered = render_json(report) if args.format == "json" else render_markdown(report)
        if args.output:
            if args.output.exists():
                raise ValueError(f"report already exists: {args.output}")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
