import json
import shutil
import subprocess
from html.parser import HTMLParser

import pytest
from PIL import Image, PngImagePlugin

from screenshot_redaction_assistant.cli import main
from screenshot_redaction_assistant.core import analyze, build_jobs
from screenshot_redaction_assistant.editor import render_editor
from screenshot_redaction_assistant.recipes import expand_recipe, union_pixels


def test_union_matches_flattened_pixels_and_metadata(tmp_path):
    source = tmp_path / "source.png"
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "PRIVATE-METADATA-CANARY")
    Image.new("RGB", (20, 20), "white").save(source, pnginfo=metadata)
    original = source.read_bytes()
    rectangles = [
        {"left": 0, "top": 0, "right": 10, "bottom": 10},
        {"left": 5, "top": 5, "right": 15, "bottom": 15},
    ]
    output = tmp_path / "final.png"
    report = analyze(
        {
            "input": str(source),
            "output": str(output),
            "rectangles": rectangles,
            "metadata_review": True,
        }
    )
    result = report["results"][0]
    assert result["redacted_pixels_total"] == 175 and result["rectangle_pixels_sum"] == 200
    with Image.open(output) as image:
        assert sum(image.getpixel((x, y)) == (0, 0, 0) for x in range(20) for y in range(20)) == 175
        assert not image.info
    assert result["metadata_review"]["field_names"] == []
    assert source.read_bytes() == original
    assert union_pixels([]) == 0


def test_normalized_resolution_and_scaling(tmp_path):
    recipe = {
        "reference_size": [20, 20],
        "normalized_rectangles": [{"left": 0.1, "top": 0.2, "right": 0.5, "bottom": 0.6}],
    }
    expanded = expand_recipe(recipe, 20, 20)
    assert [expanded[0][k] for k in ("left", "top", "right", "bottom")] == [2, 4, 10, 12]
    with pytest.raises(ValueError, match="resolution"):
        expand_recipe(recipe, 40, 40)
    assert expand_recipe({**recipe, "allow_scale": True}, 40, 40)[0]["right"] == 20
    with pytest.raises(ValueError, match="aspect"):
        expand_recipe({**recipe, "allow_scale": True}, 40, 20)
    assert expand_recipe({"rectangles": [{"id": "legacy"}]}, 20, 20) == [{"id": "legacy"}]
    source = tmp_path / "source.png"
    Image.new("RGB", (20, 20), "white").save(source)
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps({**recipe, "input": str(source), "output": str(tmp_path / "final.png")})
    )
    assert main([str(spec), "--metadata-review", "--format", "json"]) == 0
    # Expanding jobs twice must not duplicate normalized rectangles.
    jobs = build_jobs(json.loads(spec.read_text()))
    assert len(build_jobs({"jobs": jobs})[0]["rectangles"]) == 1


@pytest.mark.parametrize(
    "update",
    [
        {"reference_size": [0, 20]},
        {"allow_scale": "yes"},
        {"normalized_rectangles": []},
        {"normalized_rectangles": [None]},
        {"normalized_rectangles": [{"left": 0, "top": 0, "right": float("nan"), "bottom": 1}]},
        {"normalized_rectangles": [{"left": 0.8, "top": 0, "right": 0.2, "bottom": 1}]},
    ],
)
def test_invalid_recipes(update):
    data = {
        "reference_size": [20, 20],
        "normalized_rectangles": [{"left": 0, "top": 0, "right": 1, "bottom": 1}],
        **update,
    }
    with pytest.raises((ValueError, TypeError)):
        expand_recipe(data, 20, 20)


def test_editor_contains_original_but_does_not_write_final(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 60), "white").save(source)
    final = tmp_path / "final.png"
    job = {
        "input": str(source),
        "output": str(final),
        "rectangles": [
            {"left": 1, "top": 2, "right": 20, "bottom": 30, "reason": "</script><img src=x>"}
        ],
    }
    html = render_editor(job)
    assert "</script><img" not in html and "data:image/png;base64," in html
    assert "Download final PNG" in html and "Original" in html and "Preview rectangles" in html
    editor = tmp_path / "editor.html"
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(job))
    assert main([str(spec), "--editor", str(editor)]) == 0
    assert not final.exists()
    assert main([str(spec), "--editor", str(editor)]) == 2
    node = shutil.which("node")
    if node:

        class Scripts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.active = False
                self.parts = []

            def handle_starttag(self, tag, attrs):
                self.active = tag == "script" and not dict(attrs).get("type")

            def handle_endtag(self, tag):
                if tag == "script":
                    self.active = False

            def handle_data(self, data):
                if self.active:
                    self.parts.append(data)

        parser = Scripts()
        parser.feed(html)
        script = tmp_path / "editor.js"
        script.write_text("\n".join(parser.parts), encoding="utf-8")
        result = subprocess.run(
            [node, "--check", str(script)], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
