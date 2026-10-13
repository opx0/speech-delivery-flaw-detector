import contextlib
import json
import socket
import threading
import time
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import cast

import httpx
import numpy as np
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from speech_delivery.analysis.protocol import AnalysisError, ProgressSink
from speech_delivery.api import create_app
from speech_delivery.audio import SAMPLE_RATE, from_samples, sha256_file, write_flac
from speech_delivery.contract import AnalyzeOptions, ClipLabel, ErrorCode, Report, Stage
from speech_delivery.contract import fixtures as fx
from speech_delivery.library import MANIFEST_NAME, Library

WAIT_S = 10.0
OPTIONS = json.dumps({"transcript": fx.TRANSCRIPT})
SCRIPT = (
    (Stage.DECODE, 0.0, "Decoding the recording"),
    (Stage.ALIGN, 0.5, "Aligning words"),
    (Stage.COMPARE, 1.0, "Comparing"),
)


class FakeAnalyzer:
    """Plays a fixed progress script, then returns the fixture report or raises `error`.

    When `gate` is set the analysis waits on it after announcing it started, so a test can
    hold jobs in the running state.
    """

    def __init__(self, error: Exception | None = None, gate: threading.Event | None = None) -> None:
        self.error = error
        self.gate = gate
        self.started = threading.Semaphore(0)
        self.paths: list[Path] = []
        self.existed_during_run: list[bool] = []
        self.options: list[AnalyzeOptions] = []
        self.suffixes: list[str] = []

    def analyze(self, audio_path: Path, options: AnalyzeOptions, progress: ProgressSink) -> Report:
        self.paths.append(audio_path)
        self.options.append(options)
        self.existed_during_run.append(audio_path.read_bytes() == b"RIFFdata")
        self.started.release()
        for stage, fraction, message in SCRIPT:
            progress(stage, fraction, message)
        if self.gate is not None:
            assert self.gate.wait(WAIT_S)
        if self.error is not None:
            raise self.error
        return fx.report("baseline")


def open_client(app: FastAPI) -> httpx.Client:
    """TestClient is an httpx.Client at runtime, but pyright cannot resolve the base class."""
    return cast(httpx.Client, TestClient(app))


def write_dataset(root: Path) -> None:
    manifest = fx.manifest()
    clips: list[ClipLabel] = []
    for index, clip in enumerate(manifest.clips):
        t = np.arange(int(clip.audio.duration_s * SAMPLE_RATE)) / SAMPLE_RATE
        path = root / clip.audio.path
        write_flac(path, from_samples(0.3 * np.sin(2 * np.pi * (200 + index) * t)))
        audio = clip.audio.model_copy(
            update={"sha256": sha256_file(path), "duration_s": len(t) / SAMPLE_RATE}
        )
        clips.append(clip.model_copy(update={"audio": audio}))
    written = manifest.model_copy(update={"clips": tuple(clips)})
    (root / MANIFEST_NAME).write_text(written.model_dump_json(), encoding="utf-8")


@pytest.fixture
def library(tmp_path: Path) -> Library:
    root = tmp_path / "dataset"
    write_dataset(root)
    return Library.load(root)


@pytest.fixture
def analyzer() -> FakeAnalyzer:
    return FakeAnalyzer()


@pytest.fixture
def client(library: Library, analyzer: FakeAnalyzer) -> Iterator[httpx.Client]:
    with open_client(create_app(library, analyzer)) as client:
        yield client


def post_job(
    client: httpx.Client, filename: str = "speech.wav", options: str = OPTIONS
) -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/jobs", files={"audio": (filename, b"RIFFdata")}, data={"options": options}
    )
    return response.status_code, response.json()


def read_events(client: httpx.Client, job_id: str) -> list[dict[str, object]]:
    """Every `data:` payload of a job's stream, read until the server closes it."""
    with client.stream("GET", f"/api/jobs/{job_id}/events") as response:
        assert response.status_code == 200
        return [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]


def test_library_lists_the_baseline_and_the_demos(client: httpx.Client) -> None:
    body = client.get("/api/library").json()

    assert [e["baseline_audio_url"] for e in body["entries"]] == [
        "/api/audio/gettysburg-address.gold"
    ]
    assert [d["clip_id"] for d in body["demos"]] == [
        "gettysburg-address.control",
        "gettysburg-address.rush-l3",
    ]


def test_audio_is_served_with_its_exact_bytes(client: httpx.Client, library: Library) -> None:
    clip = library.clip("gettysburg-address.rush-l3")
    expected = (library.root / clip.audio.path).read_bytes()

    response = client.get("/api/audio/gettysburg-address.rush-l3")

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/flac"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.content == expected


def test_a_range_request_gets_206_with_just_those_bytes(
    client: httpx.Client, library: Library
) -> None:
    expected = (library.root / library.clip("gettysburg-address.gold").audio.path).read_bytes()

    response = client.get("/api/audio/gettysburg-address.gold", headers={"Range": "bytes=10-19"})

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes 10-19/{len(expected)}"
    assert response.content == expected[10:20]


def test_an_open_ended_browser_range_request_gets_the_whole_file_as_206(
    client: httpx.Client, library: Library
) -> None:
    expected = (library.root / library.clip("gettysburg-address.control").audio.path).read_bytes()

    response = client.get("/api/audio/gettysburg-address.control", headers={"Range": "bytes=0-"})

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes 0-{len(expected) - 1}/{len(expected)}"
    assert response.content == expected


@pytest.mark.parametrize(
    "clip_id",
    [
        "gettysburg-address.human-mono",
        "gettysburg-address.reader-dj",
        "gettysburg-address.shifted-male",
        "no-such-clip",
        "../manifest.json",
        "..%2Fmanifest.json",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ],
)
def test_clips_that_are_not_demo_material_return_404(client: httpx.Client, clip_id: str) -> None:
    assert client.get(f"/api/audio/{clip_id}").status_code == 404


def test_a_job_streams_progress_in_order_then_the_report(
    client: httpx.Client, analyzer: FakeAnalyzer
) -> None:
    status, body = post_job(client)
    job_id = body["job_id"]

    events = read_events(client, job_id)

    assert status == 202
    assert job_id.startswith("job-") and len(job_id) == len("job-") + 12
    assert [(e["type"], e.get("stage"), e.get("fraction"), e.get("message")) for e in events] == [
        ("progress", "decode", 0.0, "Decoding the recording"),
        ("progress", "align", 0.5, "Aligning words"),
        ("progress", "compare", 1.0, "Comparing"),
        ("done", None, None, None),
    ]
    assert {e["job_id"] for e in events} == {job_id}
    assert Report.model_validate(events[-1]["report"]) == fx.report("baseline")
    assert analyzer.options[0].transcript == fx.TRANSCRIPT


def test_a_late_subscriber_gets_every_event_replayed(client: httpx.Client) -> None:
    _, body = post_job(client)

    first = read_events(client, body["job_id"])
    second = read_events(client, body["job_id"])

    assert len(first) == 4
    assert second == first


def test_a_participant_error_becomes_a_failed_event_with_its_code(
    library: Library,
) -> None:
    analyzer = FakeAnalyzer(
        error=AnalysisError(ErrorCode.TRANSCRIPT_MISMATCH, "The audio does not match.")
    )
    with open_client(create_app(library, analyzer)) as client:
        _, body = post_job(client)

        events = read_events(client, body["job_id"])

    assert events[-1] == {
        "type": "failed",
        "job_id": body["job_id"],
        "code": "transcript_mismatch",
        "message": "The audio does not match.",
    }
    assert [e["type"] for e in events] == ["progress", "progress", "progress", "failed"]


def test_an_unexpected_error_is_logged_but_never_leaked(
    library: Library, caplog: pytest.LogCaptureFixture
) -> None:
    analyzer = FakeAnalyzer(error=RuntimeError("secret detail"))
    with open_client(create_app(library, analyzer)) as client:
        _, body = post_job(client)

        with client.stream("GET", f"/api/jobs/{body['job_id']}/events") as response:
            text = response.read().decode()

    last = json.loads(text.strip().splitlines()[-1].removeprefix("data: "))
    assert last["code"] == "internal"
    assert last["message"] == "Analysis failed unexpectedly."
    assert "secret detail" not in text
    assert "Traceback" not in text
    assert "secret detail" in caplog.text


def test_the_upload_is_analyzed_under_a_fixed_name_and_removed_afterwards(
    client: httpx.Client, analyzer: FakeAnalyzer
) -> None:
    _, body = post_job(client, filename="../../etc/My Speech.WAV")
    read_events(client, body["job_id"])

    (path,) = analyzer.paths
    assert path.name == "upload.wav"
    assert analyzer.existed_during_run == [True]
    assert not path.exists()
    assert not path.parent.exists()


def test_an_odd_filename_gets_no_suffix(client: httpx.Client, analyzer: FakeAnalyzer) -> None:
    _, body = post_job(client, filename="speech.w av;rm -rf")
    read_events(client, body["job_id"])

    assert analyzer.paths[0].name == "upload"


def test_the_upload_is_removed_after_a_failed_job_too(library: Library) -> None:
    analyzer = FakeAnalyzer(error=RuntimeError("boom"))
    with open_client(create_app(library, analyzer)) as client:
        _, body = post_job(client)
        read_events(client, body["job_id"])

    assert not analyzer.paths[0].parent.exists()


def test_a_body_over_the_limit_is_refused_with_413(library: Library) -> None:
    analyzer = FakeAnalyzer()
    with open_client(create_app(library, analyzer, max_upload_bytes=1000)) as client:
        response = client.post(
            "/api/jobs",
            files={"audio": ("big.wav", b"x" * 200_000)},
            data={"options": OPTIONS},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "The upload is too large."}
    assert analyzer.paths == []


def test_a_chunked_body_is_cut_off_without_a_content_length(library: Library) -> None:
    def body() -> Iterator[bytes]:
        yield b'--x\r\nContent-Disposition: form-data; name="audio"; filename="a.wav"\r\n\r\n'
        for _ in range(40):
            yield b"x" * 10_000

    with open_client(create_app(library, FakeAnalyzer(), max_upload_bytes=1000)) as client:
        response = client.post(
            "/api/jobs",
            content=body(),
            headers={"Content-Type": "multipart/form-data; boundary=x"},
        )

    assert response.status_code == 413


def test_a_file_just_over_the_limit_inside_the_form_allowance_is_refused(
    library: Library,
) -> None:
    analyzer = FakeAnalyzer()
    with open_client(create_app(library, analyzer, max_upload_bytes=1000)) as client:
        response = client.post(
            "/api/jobs",
            files={"audio": ("a.wav", b"x" * 1001)},
            data={"options": OPTIONS},
        )

    assert response.status_code == 413
    assert analyzer.paths == []


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ("not json", "Invalid options: options: Invalid JSON"),
        ('{"transcript": ""}', "Invalid options: transcript: String should have at least 1"),
        ('{"library_text_id": "x"}', "Invalid options: transcript: Field required"),
    ],
)
def test_malformed_options_return_422_with_a_readable_message(
    client: httpx.Client, options: str, message: str
) -> None:
    response = client.post(
        "/api/jobs", files={"audio": ("a.wav", b"RIFFdata")}, data={"options": options}
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith(message)


def test_a_missing_audio_part_returns_422(client: httpx.Client) -> None:
    assert client.post("/api/jobs", data={"options": OPTIONS}).status_code == 422


def test_jobs_beyond_the_queue_cap_are_refused_with_429(library: Library) -> None:
    gate = threading.Event()
    analyzer = FakeAnalyzer(gate=gate)
    with open_client(create_app(library, analyzer, max_queued=1)) as client:
        try:
            for _ in range(2):
                assert post_job(client)[0] == 202
            for _ in range(2):
                assert analyzer.started.acquire(timeout=WAIT_S)
            assert post_job(client)[0] == 202
            status, body = post_job(client)
            leaked = [p for p in analyzer.paths if not p.exists()]
        finally:
            gate.set()

    assert status == 429
    assert "Too many analyses" in body["detail"]
    assert leaked == []


def test_a_finished_job_is_forgotten_after_thirty_minutes(library: Library) -> None:
    now = [1000.0]
    with open_client(create_app(library, FakeAnalyzer(), clock=lambda: now[0])) as client:
        _, body = post_job(client)
        job_id = body["job_id"]
        read_events(client, job_id)

        now[0] += 30 * 60
        assert client.get(f"/api/jobs/{job_id}/events").status_code == 200
        now[0] += 1
        assert client.get(f"/api/jobs/{job_id}/events").status_code == 404


def test_an_unknown_job_returns_404(client: httpx.Client) -> None:
    assert client.get("/api/jobs/job-000000000000/events").status_code == 404


@contextlib.contextmanager
def live_server(app: FastAPI) -> Generator[str]:
    """A real uvicorn on a free localhost port. TestClient buffers a whole response, so
    streaming behaviour has to be checked over a socket."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + WAIT_S
    while not server.started:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(WAIT_S)


def test_a_quiet_stream_sends_heartbeat_comments_until_the_job_ends(library: Library) -> None:
    gate = threading.Event()
    app = create_app(library, FakeAnalyzer(gate=gate), heartbeat_s=0.05)
    lines: list[str] = []
    with live_server(app) as url:
        created = httpx.post(
            f"{url}/api/jobs", files={"audio": ("a.wav", b"RIFFdata")}, data={"options": OPTIONS}
        )
        with httpx.stream("GET", f"{url}/api/jobs/{created.json()['job_id']}/events") as response:
            for line in response.iter_lines():
                lines.append(line)
                if line == ": heartbeat":
                    gate.set()
                if '"type":"done"' in line:
                    break

    assert lines.count(": heartbeat") >= 1
    assert [
        json.loads(x.removeprefix("data: "))["type"] for x in lines if x.startswith("data:")
    ] == [
        "progress",
        "progress",
        "progress",
        "done",
    ]


def test_over_a_real_socket_an_upload_streams_events_and_audio_supports_ranges(
    library: Library,
) -> None:
    analyzer = FakeAnalyzer()
    with live_server(create_app(library, analyzer)) as url:
        created = httpx.post(
            f"{url}/api/jobs",
            files={"audio": ("speech.mp3", b"RIFFdata")},
            data={"options": OPTIONS},
        )
        with httpx.stream("GET", f"{url}/api/jobs/{created.json()['job_id']}/events") as response:
            content_type = response.headers["content-type"]
            events = [
                json.loads(line.removeprefix("data: "))
                for line in response.iter_lines()
                if line.startswith("data: ")
            ]
        ranged = httpx.get(
            f"{url}/api/audio/gettysburg-address.gold", headers={"Range": "bytes=0-"}
        )
        size = (library.root / library.clip("gettysburg-address.gold").audio.path).stat().st_size

    assert created.status_code == 202
    assert content_type.startswith("text/event-stream")
    assert [e["type"] for e in events] == ["progress", "progress", "progress", "done"]
    assert analyzer.paths[0].name == "upload.mp3"
    assert ranged.status_code == 206
    assert ranged.headers["content-range"] == f"bytes 0-{size - 1}/{size}"
    assert len(ranged.content) == size


def test_no_cors_headers_are_sent(client: httpx.Client) -> None:
    response = client.get("/api/library", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_the_spa_fallback_serves_index_html_and_real_files(
    library: Library, tmp_path: Path
) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<h1>app</h1>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("secret")

    with open_client(create_app(library, FakeAnalyzer(), dist)) as client:
        page = client.get("/some/page")
        asset = client.get("/assets/app.js")
        escape = client.get("/..%2Fsecret.txt")
        unknown_api = client.get("/api/nothing")
        library_response = client.get("/api/library")

    assert (page.status_code, page.text) == (200, "<h1>app</h1>")
    assert asset.text == "console.log(1)"
    assert "secret" not in escape.text
    assert unknown_api.status_code == 404
    assert unknown_api.json() == {"detail": "Not found."}
    assert library_response.status_code == 200


def test_without_a_web_dist_unknown_paths_are_404(client: httpx.Client) -> None:
    assert client.get("/some/page").status_code == 404
