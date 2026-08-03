import json
from pathlib import Path

import pytest
from PIL import Image

from screenshot_redaction_assistant.cli import main
from screenshot_redaction_assistant.core import (
    _ocr_candidates,
    analyze,
    build_jobs,
    directory_jobs,
    render_json,
    render_markdown,
    review_rectangles,
    write_preview,
)


def job(source: Path, output: Path) -> dict:
    return {
        "input": str(source),
        "output": str(output),
        "rectangles": [{"left": 2, "top": 3, "right": 10, "bottom": 12, "reason": "email"}],
    }


def test_redacts_flattens_and_records_strong_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "redacted.png"
    Image.new("RGB", (20, 20), (255, 255, 255)).save(source)
    report = analyze(job(source, output))
    result = report["results"][0]
    assert report["schema_version"] == 2 and result["flattened"]
    assert result["rectangles"][0]["pixels"] == 72
    assert result["input_sha256"] != result["output_sha256"]
    with Image.open(output) as image:
        assert image.getpixel((5, 5)) == (0, 0, 0)
    assert "output_sha256" in render_json(report) and "visual inspection" in render_markdown(report)


def test_batch_recipe_directory_and_preview(tmp_path: Path) -> None:
    source_dir, output_dir = tmp_path / "in", tmp_path / "out"
    source_dir.mkdir()
    for name in ("a.png", "b.jpg"):
        Image.new("RGB", (20, 20), "white").save(source_dir / name)
    jobs = directory_jobs(
        source_dir,
        output_dir,
        {"rectangles": [{"left": 0, "top": 0, "right": 4, "bottom": 4}], "color": [255, 0, 0]},
        recursive=False,
    )
    assert len(jobs) == 2
    preview = tmp_path / "preview.png"
    manifest = write_preview(jobs[0], preview)
    assert manifest["rectangles"] == 1 and preview.exists()
    report = analyze({"jobs": jobs})
    assert report["job_count"] == 2
    assert all(Path(item["output"]).suffix == ".png" for item in report["results"])


def test_interactive_review_can_skip_replace_and_add() -> None:
    answers = iter(["s", "1,2,5,6", "7,8,9,10", ""])
    reviewed = review_rectangles(
        [
            {"left": 0, "top": 0, "right": 2, "bottom": 2, "reason": "skip"},
            {"left": 0, "top": 0, "right": 3, "bottom": 3, "reason": "replace"},
        ],
        lambda _: next(answers),
    )
    assert len(reviewed) == 2
    assert reviewed[0]["origin"] == "review-correction"
    assert reviewed[1]["reason"] == "review-added"


def test_ocr_candidates_are_suggestions_only() -> None:
    data = {
        "text": ["person@example.com", "ordinary"],
        "left": [1, 20],
        "top": [2, 20],
        "width": [10, 5],
        "height": [4, 5],
    }
    suggestions = _ocr_candidates(data)
    assert suggestions == [
        {
            "left": 1,
            "top": 2,
            "right": 11,
            "bottom": 6,
            "reason": "email",
            "origin": "ocr-suggestion",
        }
    ]
    with pytest.raises(ValueError, match="position fields"):
        _ocr_candidates({"text": []})


def test_validation_and_replacement_safety(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (10, 10)).save(source)
    with pytest.raises(ValueError, match="invalid rectangle"):
        analyze(
            {
                **job(source, tmp_path / "out.png"),
                "rectangles": [{"left": 0, "top": 0, "right": 20, "bottom": 2}],
            }
        )
    output = tmp_path / "occupied.png"
    output.write_text("keep")
    with pytest.raises(ValueError, match="already exists"):
        analyze(job(source, output))
    with pytest.raises(ValueError, match="RGB"):
        analyze({**job(source, tmp_path / "other.png"), "color": [1]})
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="supported images"):
        directory_jobs(empty, tmp_path / "empty-output", {}, False)


def test_cli_batch_and_report_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source_dir = tmp_path / "input"
    source_dir.mkdir()
    Image.new("RGB", (8, 8), "white").save(source_dir / "one.png")
    recipe = tmp_path / "recipe.json"
    recipe.write_text(
        json.dumps({"rectangles": [{"left": 0, "top": 0, "right": 2, "bottom": 2}]}),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.json"
    assert (
        main(
            [
                "--input-dir",
                str(source_dir),
                "--output-dir",
                str(tmp_path / "out"),
                "--recipe",
                str(recipe),
                "--format",
                "json",
                "--output",
                str(report_path),
            ]
        )
        == 0
    )
    assert json.loads(report_path.read_text())["job_count"] == 1
    assert main([]) == 2
    assert "provide a specification" in capsys.readouterr().err


def test_build_jobs_recipe_and_invalid_review() -> None:
    jobs = build_jobs(
        {
            "recipe": {"color": [1, 2, 3]},
            "jobs": [{"input": "a.png", "output": "b.png", "rectangles": [{}]}],
        }
    )
    assert jobs[0]["color"] == [1, 2, 3]
    with pytest.raises(ValueError, match="left,top"):
        review_rectangles([{"left": 0, "top": 0, "right": 1, "bottom": 1}], lambda _: "1,2")


def test_add_review_validation_and_job_shapes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="new rectangle"):
        review_rectangles([], lambda _: "1,2")
    with pytest.raises(TypeError, match="object"):
        build_jobs([])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="recipe"):
        build_jobs({"recipe": []})
    with pytest.raises(ValueError, match="non-empty"):
        build_jobs({"jobs": []})
    with pytest.raises(TypeError, match="each job"):
        build_jobs({"jobs": ["bad"]})
    with pytest.raises(ValueError, match="does not exist"):
        directory_jobs(tmp_path / "missing", tmp_path / "out", {}, False)


def test_preview_collision_and_rectangle_shapes(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (20, 20), "white").save(source)
    preview = tmp_path / "preview.png"
    write_preview(job(source, tmp_path / "out.png"), preview)
    with pytest.raises(ValueError, match="preview already exists"):
        write_preview(job(source, tmp_path / "out.png"), preview)
    with pytest.raises(TypeError, match="rectangle"):
        analyze({**job(source, tmp_path / "bad.png"), "rectangles": ["bad"]})
    with pytest.raises(ValueError, match="RGB integers"):
        analyze({**job(source, tmp_path / "color.png"), "color": [0, True, 0]})


def test_cli_spec_recipe_preview_and_report_collision(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (12, 12), "white").save(source)
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "input": str(source),
                "output": str(tmp_path / "out.png"),
                "rectangles": [{"left": 0, "top": 0, "right": 2, "bottom": 2}],
            }
        ),
        encoding="utf-8",
    )
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps({"color": [3, 4, 5]}), encoding="utf-8")
    report = tmp_path / "report.json"
    assert (
        main(
            [
                str(spec),
                "--recipe",
                str(recipe),
                "--preview-dir",
                str(tmp_path / "previews"),
                "--format",
                "json",
                "--output",
                str(report),
            ]
        )
        == 0
    )
    assert (tmp_path / "previews" / "preview-1.png").exists()
    assert main([str(spec), "--output", str(report)]) == 2
    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]", encoding="utf-8")
    assert main([str(malformed)]) == 2
