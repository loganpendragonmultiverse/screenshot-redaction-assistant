from __future__ import annotations

import os
from pathlib import Path

import pytest

from screenshot_redaction_assistant import output


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("index", [0, 1])
def test_late_write_failure_rolls_back_and_retries(tmp_path, monkeypatch, reverse, index):
    pair = [(tmp_path / "report.json", b"report"), (tmp_path / "state.json", b"state")]
    if reverse:
        pair.reverse()
    original = output._write_final
    count = 0

    def fail(item):
        nonlocal count
        current = count
        count += 1
        if current == index:
            assert item.fd is not None
            item.written = os.write(item.fd, item.data[:2])
            raise OSError("synthetic late write failure")
        return original(item)

    with monkeypatch.context() as patch:
        patch.setattr(output, "_write_final", fail)
        with pytest.raises(OSError, match="synthetic"):
            output.write_new_outputs(pair)
    assert not any(p.exists() for p, _ in pair)
    assert not list(tmp_path.glob(".forge-output-*"))
    output.write_new_outputs(pair)
    assert [p.read_bytes() for p, _ in pair] == [v for _, v in pair]


@pytest.mark.parametrize("index", [0, 1])
def test_existing_collision_is_preserved(tmp_path, index):
    pair = [(tmp_path / "report.json", b"new-report"), (tmp_path / "state.json", b"new-state")]
    pair[index][0].write_text("existing")
    with pytest.raises(ValueError, match="already exists"):
        output.write_new_outputs(pair)
    assert pair[index][0].read_text() == "existing"
    assert not pair[1 - index][0].exists()


def test_collision_after_preflight_never_overwrites(tmp_path, monkeypatch):
    pair = [(tmp_path / "one", b"one"), (tmp_path / "two", b"two")]
    original = output.os.open

    def collide(path, flags, *args, **kwargs):
        if Path(path) == pair[1][0] and flags & os.O_EXCL:
            pair[1][0].write_text("concurrent")
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(output.os, "open", collide)
    with pytest.raises(FileExistsError):
        output.write_new_outputs(pair)
    assert not pair[0][0].exists()
    assert pair[1][0].read_text() == "concurrent"


def test_changed_new_file_is_preserved_on_rollback(tmp_path, monkeypatch):
    pair = [(tmp_path / "one", b"one"), (tmp_path / "two", b"two")]
    original = output._write_final

    def change(item):
        if item.path == pair[1][0]:
            pair[0][0].write_text("concurrent edit")
            raise OSError("synthetic")
        return original(item)

    monkeypatch.setattr(output, "_write_final", change)
    with pytest.raises(OSError, match="kept changed"):
        output.write_new_outputs(pair)
    assert pair[0][0].read_text() == "concurrent edit"
    assert not pair[1][0].exists()


def test_stdout_failure_rolls_back_new_state(tmp_path):
    path = tmp_path / "state"

    def broken():
        raise BrokenPipeError("consumer closed")

    with pytest.raises(BrokenPipeError):
        output.write_new_outputs([(path, b"state")], deliver=broken)
    assert not path.exists()


import json

from PIL import Image

from screenshot_redaction_assistant.cli import main
from screenshot_redaction_assistant.core import analyze


def fixture(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (16, 16), "white").save(source)
    jobs = [
        {
            "input": str(source),
            "output": str(tmp_path / (name + ".png")),
            "rectangles": [{"left": 1, "top": 1, "right": 4, "bottom": 4}],
        }
        for name in ("a", "b")
    ]
    spec = tmp_path / "jobs.json"
    spec.write_text(json.dumps({"jobs": jobs}))
    return source, jobs, spec


@pytest.mark.parametrize("blocked", ["image", "preview", "audit"])
def test_real_nonadmin_failure_and_retry(tmp_path, capsys, blocked):
    if os.name != "posix" or getattr(os, "geteuid", lambda: 0)() == 0:
        pytest.skip("requires non-admin POSIX permissions")
    source, jobs, spec = fixture(tmp_path)
    before = source.read_bytes()
    restricted = tmp_path / "restricted"
    restricted.mkdir()
    if blocked == "image":
        jobs[1]["output"] = str(restricted / "b.png")
        spec.write_text(json.dumps({"jobs": jobs}))
    previews = restricted if blocked == "preview" else tmp_path / "previews"
    report = (restricted if blocked == "audit" else tmp_path) / "audit.json"
    args = [str(spec), "--preview-dir", str(previews), "--format", "json", "--output", str(report)]
    restricted.chmod(0o555)
    try:
        assert main(args) == 2
        capsys.readouterr()
        assert not any(Path(j["output"]).exists() for j in jobs)
        assert not list(previews.glob("*.png")) and not report.exists()
        assert not list(tmp_path.rglob(".forge-output-*"))
    finally:
        restricted.chmod(0o755)
    assert main(args) == 0
    report_data = json.loads(report.read_text())
    assert report_data["job_count"] == 2
    assert source.read_bytes() == before
    for row in report_data["results"]:
        with Image.open(row["output"]) as im:
            assert im.getpixel((2, 2)) == (0, 0, 0)
            assert im.getpixel((10, 10)) == (255, 255, 255)
            assert not im.info


def test_later_invalid_image_and_missing_audit_parent_leave_no_outputs(tmp_path, capsys):
    _source, jobs, spec = fixture(tmp_path)
    jobs[1]["rectangles"][0]["right"] = 99
    with pytest.raises(ValueError):
        analyze({"jobs": jobs})
    assert not Path(jobs[0]["output"]).exists()
    assert (
        main(
            [
                str(spec),
                "--preview-dir",
                str(tmp_path / "previews"),
                "--output",
                str(tmp_path / "missing" / "audit"),
            ]
        )
        == 2
    )
    capsys.readouterr()
    assert not any(Path(j["output"]).exists() for j in jobs)
    assert not list((tmp_path / "previews").glob("*.png"))
    assert main([str(spec), "--output", str(tmp_path / "audit")]) == 0


@pytest.mark.parametrize("collision", ["duplicate", "source", "preview", "audit"])
def test_collisions_publish_nothing(tmp_path, capsys, collision):
    source, jobs, spec = fixture(tmp_path)
    report = tmp_path / "audit"
    if collision == "duplicate":
        jobs[1]["output"] = jobs[0]["output"]
    elif collision == "source":
        jobs[1]["output"] = str(source)
    elif collision == "preview":
        jobs[1]["output"] = str(tmp_path / "previews" / "preview-1.png")
    else:
        report = Path(jobs[0]["output"])
    spec.write_text(json.dumps({"jobs": jobs}))
    before = source.read_bytes()
    assert (
        main([str(spec), "--preview-dir", str(tmp_path / "previews"), "--output", str(report)]) == 2
    )
    capsys.readouterr()
    assert source.read_bytes() == before
    assert not Path(jobs[0]["output"]).exists()
    assert not list((tmp_path / "previews").glob("*.png"))


def test_stdout_flush_failure_recovers_images(tmp_path, monkeypatch, capsys):
    _source, jobs, spec = fixture(tmp_path)
    from screenshot_redaction_assistant import cli

    class Broken:
        def write(self, text):
            return len(text)

        def flush(self):
            raise BrokenPipeError("closed")

    with monkeypatch.context() as patch:
        patch.setattr(cli.sys, "stdout", Broken())
        assert main([str(spec)]) == 2
    capsys.readouterr()
    assert not any(Path(j["output"]).exists() for j in jobs)


def test_dangling_symlink_is_preserved(tmp_path):
    target = tmp_path / "link"
    try:
        target.symlink_to(tmp_path / "absent")
    except (OSError, NotImplementedError):
        pytest.skip("symlink permission unavailable")
    with pytest.raises(ValueError, match="already exists"):
        output.write_new_outputs([(target, b"new")])
    assert target.is_symlink() and not (tmp_path / "absent").exists()


def test_replaced_file_preserved_on_rollback(tmp_path):
    pair = [(tmp_path / "one", b"one"), (tmp_path / "two", b"two")]

    def replace():
        # Delivery occurs after descriptors close, so replacement is possible
        # on Windows as well as POSIX systems.
        pair[0][0].unlink()
        pair[0][0].mkdir()
        raise OSError("synthetic")

    with pytest.raises(OSError, match="kept changed"):
        output.write_new_outputs(pair, deliver=replace)
    assert pair[0][0].is_dir() and not pair[1][0].exists()
