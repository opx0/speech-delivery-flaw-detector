"""Create an offline, reviewer-operated source audition page."""

from collections.abc import Mapping
from html import escape
from pathlib import Path

from speech_delivery.contract.dataset import SourceRecord, TextRecord
from speech_delivery.dataset.screen import ScreenReport


def _report(report: ScreenReport | None) -> str:
    if report is None:
        return "Not screened"
    verdict = "PASS" if report.passed else "REJECT: " + "; ".join(report.reasons)
    return (
        f"{verdict}. {report.duration_s:.1f} s, {report.sample_rate_hz} Hz, "
        f"{report.integrated_lufs:.1f} LUFS, peak {report.true_peak_dbfs:.1f} dBFS, "
        f"noise floor {report.noise_floor_dbfs:.1f} dBFS."
    )


def write_audition(
    sources: tuple[SourceRecord, ...],
    texts: tuple[TextRecord, ...],
    reports: Mapping[str, ScreenReport],
    output_dir: Path,
) -> Path:
    """Write a self-contained HTML review page and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    by_title = {text.title: text for text in texts}
    cards: list[str] = []
    for source in sources:
        text = by_title.get(source.title)
        transcript = text.transcript if text else "No fixed transcript (normative reference)."
        audio_path = f"../../raw/{source.id}{Path(source.audio_url).suffix}"
        cards.append(
            "\n".join(
                (
                    f"<article><h2>{escape(source.title)} "
                    f"<small>{escape(source.speaker_name)}</small></h2>",
                    f'<audio controls preload="metadata" src="{escape(audio_path)}">'
                    f"Audio for {escape(source.id)}</audio>",
                    f"<p><strong>Screen:</strong> {escape(_report(reports.get(source.id)))}</p>",
                    f'<p><strong>Rights:</strong> <a href="{escape(source.rights.evidence_url)}">'
                    f"evidence</a>. {escape(source.rights.notes)}</p>",
                    f'<p class="transcript">{escape(transcript)}</p>',
                    f'<button data-id="{escape(source.id)}" data-decision="accept">Accept</button>',
                    f'<button data-id="{escape(source.id)}" data-decision="reject">Reject</button>',
                    f'<output id="decision-{escape(source.id)}"></output></article>',
                )
            )
        )
    page = "\n".join(
        (
            '<!doctype html><html lang="en"><meta charset="utf-8">',
            "<title>Source audition</title>",
            "<style>",
            "body{font:16px system-ui;max-width:1000px;margin:auto;padding:1rem}",
            "article{border-block-end:1px solid #bbb;padding:1rem 0}",
            "audio{display:block;width:100%;max-width:600px}",
            ".transcript{white-space:pre-wrap}button{margin-right:.5rem}",
            "</style>",
            "<h1>Source audition</h1>",
            "<p>Objective screening is not a listening judgment. Review each clip yourself.</p>",
            "\n".join(cards),
            '<button id="export">Export decisions</button><script>',
            "const key='speech-delivery-audition-decisions';",
            "const decisions=JSON.parse(localStorage.getItem(key)||'{}');",
            "function render(id){",
            "  document.getElementById('decision-'+id).textContent=decisions[id]||'undecided';",
            "}",
            "document.querySelectorAll('[data-decision]').forEach(b=>{",
            "  render(b.dataset.id);",
            "  b.onclick=()=>{",
            "    decisions[b.dataset.id]=b.dataset.decision;",
            "    localStorage.setItem(key,JSON.stringify(decisions)); render(b.dataset.id);",
            "  };",
            "});",
            "document.getElementById('export').onclick=()=>{",
            "  const blob=new Blob([JSON.stringify(decisions,null,2)],{type:'application/json'});",
            "  const a=document.createElement('a'); a.href=URL.createObjectURL(blob);",
            "  a.download='audition-decisions.json'; a.click(); URL.revokeObjectURL(a.href);",
            "};</script></html>",
        )
    )
    path = output_dir / "index.html"
    path.write_text(page)
    return path
