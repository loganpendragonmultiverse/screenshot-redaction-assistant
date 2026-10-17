import base64
import io
import json

import pytest
from PIL import Image, ImageOps

from screenshot_redaction_assistant.cli import main
from screenshot_redaction_assistant.core import analyze, build_jobs, prepare_preview
from screenshot_redaction_assistant.editor import render_editor


def payload(html):
    return json.loads(
        html.split('<script type="application/json" id="data">')[1].split("</script>")[0]
    )


@pytest.mark.parametrize("orientation", range(2, 9))
def test_display_pixels_recipe_preview_editor_and_source_safety(tmp_path, orientation):
    source = tmp_path / "source.jpg"
    image = Image.new("RGB", (20, 40), "white")
    image.paste("red", (0, 0, 10, 20))
    exif = image.getexif()
    exif[274] = orientation
    image.save(source, exif=exif)
    original = source.read_bytes()
    with Image.open(source) as opened:
        expected = ImageOps.exif_transpose(opened).convert("RGB")
    width, height = expected.size
    rectangle = {"left": width - 5, "top": 2, "right": width, "bottom": 8}
    job = {
        "input": str(source),
        "output": str(tmp_path / "final.png"),
        "coordinate_space": "exif-display-v1",
        "rectangles": [rectangle],
        "color": [12, 34, 56],
    }
    report = analyze(job)["results"][0]
    assert report["coordinate_space"] == "exif-display-v1"
    with Image.open(job["output"]) as final:
        assert final.size == expected.size
        assert final.getpixel((0, 0)) == expected.getpixel((0, 0))
        assert final.getpixel((width - 1, 3)) == (12, 34, 56)
        assert not final.info
    data = payload(render_editor(job))
    assert data["coordinate_space"] == "exif-display-v1"
    assert data["exif_orientation"] == orientation and data["color"] == [12, 34, 56]
    with Image.open(io.BytesIO(base64.b64decode(data["image"].split(",")[1]))) as embedded:
        assert embedded.size == expected.size and embedded.tobytes() == expected.tobytes()
    _, preview_bytes = prepare_preview(job, tmp_path / "preview.png")
    with Image.open(io.BytesIO(preview_bytes)) as preview:
        assert preview.size == expected.size
    normalized = {
        **job,
        "rectangles": [],
        "reference_size": [width, height],
        "normalized_rectangles": [{"left": 0.5, "top": 0, "right": 1, "bottom": 0.5}],
    }
    assert build_jobs(normalized)[0]["rectangles"][0]["right"] == width
    assert source.read_bytes() == original


def test_legacy_oriented_rectangles_require_explicit_policy_and_raw_is_preserved(tmp_path):
    source = tmp_path / "source.jpg"
    image = Image.new("RGB", (20, 40), "white")
    exif = image.getexif()
    exif[274] = 3  # Same dimensions: a size/hash check alone cannot protect an old draft.
    image.save(source, exif=exif)
    job = {
        "input": str(source),
        "output": str(tmp_path / "out.png"),
        "rectangles": [{"left": 1, "top": 2, "right": 5, "bottom": 6}],
    }
    with pytest.raises(ValueError, match="unmarked rectangle"):
        analyze(job)
    with pytest.raises(ValueError, match="unmarked rectangle"):
        render_editor(job)
    report = analyze({**job, "coordinate_space": "raw-v1"})
    assert report["results"][0]["coordinate_space"] == "raw-v1"
    assert payload(render_editor({**job, "coordinate_space": "raw-v1"}))["reference_size"] == [
        20,
        40,
    ]
    assert (
        payload(render_editor({"input": str(source), "rectangles": []}))["coordinate_space"]
        == "exif-display-v1"
    )
    with pytest.raises(ValueError, match="coordinate_space"):
        build_jobs({**job, "coordinate_space": "guess"})


def test_cli_ocr_requires_review_before_reading_or_creating_anything(tmp_path, capsys):
    assert main([str(tmp_path / "missing.json"), "--suggest-ocr"]) == 2
    assert "requires --review or --editor" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_ocr_candidate_flows_to_editor_pending_or_explicit_terminal_review(tmp_path, monkeypatch):
    from screenshot_redaction_assistant import cli, core

    source = tmp_path / "image.png"
    Image.new("RGB", (20, 20), "white").save(source)
    rectangle = {"left": 1, "top": 2, "right": 5, "bottom": 6, "origin": "ocr-suggestion"}
    seen = []

    def suggest(path, policy):
        seen.append(policy)
        return [rectangle]

    monkeypatch.setattr(core, "suggest_ocr", suggest)
    spec = tmp_path / "job.json"
    output = tmp_path / "out.png"
    spec.write_text(json.dumps({"input": str(source), "output": str(output), "rectangles": []}))
    editor = tmp_path / "review.html"
    assert main([str(spec), "--suggest-ocr", "--editor", str(editor)]) == 0
    assert (
        not output.exists()
        and payload(editor.read_text())["rectangles"][0]["origin"] == "ocr-suggestion"
    )
    monkeypatch.setattr(cli, "review_rectangles", lambda rows: [{**rows[0], "right": 4}])
    report = tmp_path / "audit.json"
    assert (
        main([str(spec), "--suggest-ocr", "--review", "--format", "json", "--output", str(report)])
        == 0
    )
    assert json.loads(report.read_text())["results"][0]["reviewed"] is True
    assert seen == ["exif-display-v1", "exif-display-v1"]


def test_core_does_not_export_unreviewed_ocr_candidates(tmp_path):
    source = tmp_path / "image.png"
    Image.new("RGB", (20, 20), "white").save(source)
    output = tmp_path / "final.png"
    job = {
        "input": str(source),
        "output": str(output),
        "rectangles": [{"left": 1, "top": 2, "right": 5, "bottom": 6, "origin": "ocr-suggestion"}],
    }
    with pytest.raises(ValueError, match="explicit review"):
        analyze(job)
    assert not output.exists()
    assert analyze({**job, "reviewed": True})["results"][0]["reviewed"] is True


def test_optional_ocr_adapter_receives_the_same_oriented_matte_pixels(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace

    from screenshot_redaction_assistant.core import suggest_ocr

    source = tmp_path / "source.jpg"
    image = Image.new("RGB", (20, 40), "white")
    exif = image.getexif()
    exif[274] = 6
    image.save(source, exif=exif)
    seen = []

    def image_to_data(image, **kwargs):
        seen.append((image.size, image.mode, dict(image.info)))
        return {"text": ["a@example.com"], "left": [25], "top": [2], "width": [10], "height": [6]}

    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        SimpleNamespace(image_to_data=image_to_data, Output=SimpleNamespace(DICT="dict")),
    )
    assert suggest_ocr(source)[0]["right"] == 35
    suggest_ocr(source, "raw-v1")
    assert seen == [((40, 20), "RGB", {}), ((20, 40), "RGB", {})]


def test_interrupted_review_returns_actionable_error_without_outputs(tmp_path, monkeypatch, capsys):
    from screenshot_redaction_assistant import cli

    source = tmp_path / "image.png"
    Image.new("RGB", (20, 20), "white").save(source)
    output = tmp_path / "out.png"
    spec = tmp_path / "job.json"
    spec.write_text(
        json.dumps(
            {
                "input": str(source),
                "output": str(output),
                "rectangles": [{"left": 1, "top": 2, "right": 5, "bottom": 6}],
            }
        )
    )

    def interrupted(rows):
        raise EOFError

    monkeypatch.setattr(cli, "review_rectangles", interrupted)
    assert main([str(spec), "--review"]) == 2
    assert "review ended before completion" in capsys.readouterr().err
    assert not output.exists()
