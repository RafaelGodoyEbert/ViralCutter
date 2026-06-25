"""
Focused tests for the TwelveLabs Pegasus viral-analysis backend.

Run directly (no pytest dependency required):
    python tests/test_twelvelabs_backend.py

The live smoke test only runs if TWELVELABS_API_KEY is set; otherwise it is
skipped so the no-network checks still validate the wiring offline.
"""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import create_viral_segments as cv  # noqa: E402


def test_arg_guards():
    """call_twelvelabs must reject missing key / missing video URL before any network call."""
    for kwargs, needle in (
        (dict(prompt="p", api_key="", video_url="http://x"), "API key"),
        (dict(prompt="p", api_key="k", video_url=None), "URL"),
    ):
        try:
            cv.call_twelvelabs(**kwargs)
            assert False, f"expected ValueError for {kwargs}"
        except ValueError as e:
            assert needle.lower() in str(e).lower(), str(e)
    print("OK test_arg_guards")


def test_pegasus_output_parses():
    """A real-shaped Pegasus JSON response must survive clean_json_response()."""
    raw = (
        '{"segments":[{"start_text":"This is an audio test file",'
        '"end_text":"transcription abilities","start_time_ref":"(0s)",'
        '"title":"Hook","reasoning":"why","score":90}]}'
    )
    parsed = cv.clean_json_response(raw)
    assert len(parsed["segments"]) == 1
    assert parsed["segments"][0]["title"] == "Hook"
    print("OK test_pegasus_output_parses")


def test_create_twelvelabs_branch_no_network(monkeypatch_dir):
    """
    create(ai_mode='twelvelabs') must route through call_twelvelabs (passing the
    video_url) and align the returned segments without touching the chunk loop.
    Uses a stubbed Pegasus response — no network.
    """
    project = monkeypatch_dir
    # Minimal transcript so process_segments() has something to align against.
    with open(os.path.join(project, "input.srt"), "w", encoding="utf-8") as f:
        f.write(
            "1\n00:00:00,000 --> 00:00:20,000\nThis is an audio test file for the demo.\n\n"
            "2\n00:00:20,000 --> 00:00:40,000\nIt verifies the transcription abilities of the tool.\n\n"
        )

    captured = {}

    def fake_call(prompt, api_key, video_url, model_name="pegasus1.5"):
        captured["video_url"] = video_url
        captured["model_name"] = model_name
        return (
            '{"segments":[{"start_text":"This is an audio test file",'
            '"end_text":"transcription abilities of the tool","start_time_ref":"(0s)",'
            '"title":"Hook","reasoning":"why","score":90}]}'
        )

    orig = cv.call_twelvelabs
    cv.call_twelvelabs = fake_call
    try:
        result = cv.create(
            num_segments=1,
            viral_mode=True,
            themes="",
            tempo_minimo=5,
            tempo_maximo=30,
            ai_mode="twelvelabs",
            api_key="dummy",
            project_folder=project,
            video_url="https://example.com/video.mp4",
        )
    finally:
        cv.call_twelvelabs = orig

    assert captured["video_url"] == "https://example.com/video.mp4", "video_url not forwarded"
    assert captured["model_name"] == "pegasus1.5"
    segs = result.get("segments", [])
    assert len(segs) == 1, segs
    seg = segs[0]
    # Aligned to the transcript timestamps (not the raw ref tag).
    assert seg["start_time"] == 0.0
    assert seg["end_time"] > seg["start_time"]
    assert seg["title"] == "Hook"
    print("OK test_create_twelvelabs_branch_no_network")


def test_live_smoke():
    """Live wiring check against the real Pegasus API (skipped without a key)."""
    api_key = os.environ.get("TWELVELABS_API_KEY")
    if not api_key:
        print("SKIP test_live_smoke (set TWELVELABS_API_KEY to run)")
        return
    if not cv.HAS_TWELVELABS:
        print("SKIP test_live_smoke (twelvelabs SDK not installed)")
        return
    # A short clip can be rejected as too short; this asserts the call returns a
    # string and does not raise. A full end-to-end run needs a real (>=4s) video.
    out = cv.call_twelvelabs(
        "Return JSON only: {\"segments\":[]}",
        api_key,
        "https://download.samplelib.com/mp4/sample-5s.mp4",
        model_name="pegasus1.5",
    )
    assert isinstance(out, str) and out, "expected a non-empty string response"
    print("OK test_live_smoke (request wiring reached the API)")


if __name__ == "__main__":
    import tempfile

    test_arg_guards()
    test_pegasus_output_parses()
    with tempfile.TemporaryDirectory() as d:
        test_create_twelvelabs_branch_no_network(d)
    test_live_smoke()
    print("\nAll TwelveLabs backend tests passed.")
