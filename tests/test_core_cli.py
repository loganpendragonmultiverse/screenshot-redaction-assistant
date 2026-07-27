import json

import pytest
from PIL import Image

from screenshot_redaction_assistant.cli import main
from screenshot_redaction_assistant.core import analyze, render_json, render_markdown


def test_redacts_and_flattens_with_manifest(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "redacted.png"
    Image.new("RGB", (20, 20), (255, 255, 255)).save(source)
    report = analyze(
        {
            "input": str(source),
            "output": str(output),
            "rectangles": [{"left": 2, "top": 3, "right": 10, "bottom": 12}],
        }
    )
    assert report["flattened"] and report["input_sha256"] != report["output_sha256"]
    with Image.open(output) as image:
        assert image.getpixel((5, 5)) == (0, 0, 0)
    assert "output_sha256" in render_json(report) and "Rectangles" in render_markdown(report)


def test_invalid_rectangle_and_overwrite_rejected(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "out.png"
    Image.new("RGB", (10, 10)).save(source)
    with pytest.raises(ValueError, match="invalid rectangle"):
        analyze(
            {
                "input": str(source),
                "output": str(output),
                "rectangles": [{"left": 0, "top": 0, "right": 20, "bottom": 2}],
            }
        )
    output.write_text("keep")
    with pytest.raises(ValueError, match="already exists"):
        analyze(
            {
                "input": str(source),
                "output": str(output),
                "rectangles": [{"left": 0, "top": 0, "right": 2, "bottom": 2}],
            }
        )


def test_cli_reports_missing_input(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "input": "missing.png",
                "output": str(tmp_path / "out.png"),
                "rectangles": [{"left": 0, "top": 0, "right": 1, "bottom": 1}],
            }
        )
    )
    assert main([str(spec)]) == 2


def test_cli_success_and_report_output(tmp_path, capsys):
    source = tmp_path / "source.png"
    redacted = tmp_path / "redacted.png"
    report_path = tmp_path / "report.json"
    Image.new("RGB", (8, 8), (255, 255, 255)).save(source)
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "input": str(source),
                "output": str(redacted),
                "rectangles": [{"left": 0, "top": 0, "right": 2, "bottom": 2}],
                "color": [255, 0, 0],
            }
        ),
        encoding="utf-8",
    )
    assert main([str(spec), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["flattened"] is True
    redacted.unlink()
    assert main([str(spec), "--output", str(report_path)]) == 0
    assert "Output Sha256" in report_path.read_text(encoding="utf-8")
