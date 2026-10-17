import hashlib
import json
from pathlib import Path

from PIL import Image

from screenshot_redaction_assistant.editor import render_editor


def test_draft_identity_binds_exact_image_and_has_explicit_private_controls(tmp_path: Path):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 60), "white").save(source)
    html = render_editor(
        {"input": str(source), "rectangles": [{"left": 1, "top": 2, "right": 20, "bottom": 30}]}
    )
    payload = json.loads(
        html.split('<script type="application/json" id="data">')[1].split("</script>")[0]
    )
    assert payload["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert payload["reference_size"] == [100, 60]
    assert 'id="draft-save"' in html and 'id="draft-file"' in html
    assert str(source) not in html
    changed = tmp_path / "changed.png"
    Image.new("RGB", (100, 60), "black").save(changed)
    other = render_editor({"input": str(changed), "rectangles": []})
    assert payload["source_sha256"] not in other


def test_cli_geometry_does_not_silently_coerce_fractional_or_boolean_bounds(tmp_path: Path):
    import pytest

    from screenshot_redaction_assistant.core import analyze

    source = tmp_path / "image.png"
    Image.new("RGB", (20, 20), "white").save(source)
    output = tmp_path / "redacted.png"
    for value in (1.5, "1", True):
        with pytest.raises(ValueError, match="integers"):
            analyze(
                {
                    "input": str(source),
                    "output": str(output),
                    "rectangles": [{"left": value, "top": 1, "right": 10, "bottom": 10}],
                }
            )
        assert not output.exists()
