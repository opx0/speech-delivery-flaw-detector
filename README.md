# speech-delivery-flaw-detector

Compares a speech against a gold-standard delivery of the same text, then pinpoints where and
why the delivery deviates, with timestamps and acoustic causes.

The dashboard overlays your pitch, pace, energy, and pauses on the gold delivery's curves. It
marks the regions where your delivery departs from the gold curves. Each marked region links
to an explanation, for example "Rushed pacing, 00:14 to 00:18, 4.7 words/s against an expected
2.6 words/s".

## Status

The data contract is in place. Dataset building, analysis, evaluation, the API, and the
dashboard are built against that contract and are not in the repository yet.

## How it works

The system has two modes. The mode follows from the transcript you upload.

| Mode | When it applies | What the speech is compared with |
| --- | --- | --- |
| Contrast | The transcript matches a text in the dataset library. | The gold delivery of the same text, aligned word by word. |
| Normative | The transcript is not in the library, or the speech is unscripted. | Percentile bands learned from the gold and natural-reader clips. Findings are marked lower confidence. |

Scores cover four delivery axes: cadence, tone, pauses, and volume. Content quality is out of
scope because the text is identical by construction in contrast mode.

Pitch and energy are normalized to each speaker's own median, so a female speaker can be
compared with a male baseline without false pitch errors.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/speech_delivery/contract/` | The data contract: pydantic models for every payload. |
| `contract/schema/` | The JSON Schema bundle exported from the models. |
| `contract/fixtures/` | Synthetic example payloads for every contract root. |
| `web/` | The TypeScript dashboard and the types generated from the schema. |
| `scripts/` | Build scripts. |
| `tests/` | Python tests. |

## Develop

Requires `uv` and Node.js.

1. Install the dependencies with `make setup`.
2. Run every check with `make check`. It runs the formatter check, the linter, the type checker, the tests,
   the TypeScript type check, and the schema validation of the fixtures.
3. After you change a contract model, run `make contract`. It rewrites the JSON Schema, the
   fixtures, and `web/src/contract/generated.ts`. The tests fail if you forget.

## Licenses

The code is MIT licensed. See `LICENSE`. Dataset labels and derived audio will be CC BY 4.0.
Each source recording keeps its public-domain status, and its provenance and rights evidence are
recorded in the dataset manifest.
