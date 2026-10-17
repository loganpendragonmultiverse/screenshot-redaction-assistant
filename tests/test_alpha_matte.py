import base64
import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from screenshot_redaction_assistant.core import analyze, write_preview
from screenshot_redaction_assistant.editor import render_editor


@pytest.mark.parametrize("mode", ["RGBA", "P"])
def test_hidden_rgb_uses_same_white_matte_in_cli_preview_and_editor(tmp_path: Path, mode):
    source = tmp_path / "transparent.png"
    image = Image.new("RGBA", (100, 60), "white")
    image.putpixel((70, 40), (211, 23, 47, 0))
    image.putpixel((80, 40), (255, 0, 0, 128))
    if mode == "P":
        image = image.quantize(method=Image.Quantize.FASTOCTREE)
    info = PngImagePlugin.PngInfo()
    info.add_text("private", "synthetic metadata")
    image.save(source, pnginfo=info)
    before = source.read_bytes()
    with Image.open(source) as opened:
        expected = Image.alpha_composite(
            Image.new("RGBA", opened.size, "white"), opened.convert("RGBA")
        ).convert("RGB")
    job = {
        "input": str(source),
        "output": str(tmp_path / "final.png"),
        "rectangles": [{"left": 1, "top": 1, "right": 4, "bottom": 4}],
        "metadata_review": True,
    }
    report = analyze(job)
    write_preview(job, tmp_path / "preview.png")
    html = render_editor(job)
    data = json.loads(
        html.split('<script type="application/json" id="data">')[1].split("</script>")[0]
    )
    browser_pixels = io.BytesIO(base64.b64decode(data["image"].split(",", 1)[1]))
    for output in [Path(job["output"]), tmp_path / "preview.png", browser_pixels]:
        with Image.open(output) as checked:
            assert checked.mode == "RGB"
            assert checked.getpixel((70, 40)) == (255, 255, 255)
            assert checked.getpixel((80, 40)) == expected.getpixel((80, 40))
            assert not checked.info and not checked.getexif()
    assert report["results"][0]["transparency_matte"] == [255, 255, 255]
    assert report["results"][0]["metadata_review"]["field_names"] == []
    assert data["source_sha256"] == hashlib.sha256(before).hexdigest()
    assert source.read_bytes() == before
