import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  FileAudio,
  Mic,
  Play,
  Square,
  Upload,
  X,
} from "lucide-react";
import type { DemoClip, LibraryEntry, LibraryListing } from "../../../contract";
import { KIND_LABELS } from "../../../entities/flaw";
import { formatTime } from "../../../shared/lib";

export interface IngestionPanelProps {
  listing: LibraryListing | null;
  initialTab: "upload" | "demos";
  onSelectDemo: (demo: DemoClip, entry: LibraryEntry) => void;
  onSubmitUpload: (
    file: File,
    transcript: string,
    textId: string | null,
  ) => void;
  onClose: () => void;
}

export function IngestionPanel({
  listing,
  initialTab,
  onSelectDemo,
  onSubmitUpload,
  onClose,
}: IngestionPanelProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const [tab, setTab] = useState(initialTab);
  const [entryId, setEntryId] = useState(listing?.entries[0]?.text_id ?? "");
  const [uploadTextId, setUploadTextId] = useState("auto");
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [dragging, setDragging] = useState(false);

  const entry =
    listing?.entries.find((item) => item.text_id === entryId) ??
    listing?.entries[0];
  const demos =
    listing?.demos.filter((item) => item.text_id === entry?.text_id) ?? [];

  useEffect(() => {
    dialog.current?.showModal();
    return () => {
      const active = recorder.current;
      if (active) {
        active.onstop = null;
        if (active.state !== "inactive") active.stop();
        active.stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  function chooseFile(candidate: File | undefined) {
    if (!candidate) return;
    if (candidate.size > 50 * 1024 * 1024) {
      setError("The file is larger than 50 MB. Choose a smaller recording.");
      return;
    }
    setFile(candidate);
    setError(null);
  }

  async function toggleRecording() {
    if (recorder.current?.state === "recording") {
      recorder.current.stop();
      return;
    }
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError(
        "Microphone recording is not supported here. Upload a file instead.",
      );
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const active = new MediaRecorder(stream);
      const parts: Blob[] = [];
      active.ondataavailable = (event) => parts.push(event.data);
      active.onstop = () => {
        const extension = active.mimeType.includes("mp4")
          ? "mp4"
          : active.mimeType.includes("ogg")
            ? "ogg"
            : "webm";
        chooseFile(
          new File(parts, `microphone-recording.${extension}`, {
            type: active.mimeType,
          }),
        );
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        recorder.current = null;
      };
      recorder.current = active;
      active.start();
      setRecording(true);
      setError(null);
    } catch {
      setError(
        "Microphone access was denied or is unavailable. You can upload a recording instead.",
      );
    }
  }

  return (
    <dialog
      ref={dialog}
      className="dialog intake-dialog"
      onCancel={onClose}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="dialog-heading">
        <div>
          <span className="eyebrow">Let's hear it</span>
          <h2>Start a new analysis</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close new analysis"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      <div className="intake-tabs" role="tablist" aria-label="Recording input">
        <button
          role="tab"
          aria-selected={tab === "upload"}
          className={tab === "upload" ? "active" : ""}
          onClick={() => setTab("upload")}
        >
          <Upload size={16} /> Your recording
        </button>
        <button
          role="tab"
          aria-selected={tab === "demos"}
          className={tab === "demos" ? "active" : ""}
          onClick={() => setTab("demos")}
        >
          <Play size={16} /> Reference examples
        </button>
      </div>
      <div className="dialog-body">
        {error && (
          <div className="notice error-notice" role="alert">
            {error}
          </div>
        )}
        {tab === "upload" ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (!file || !transcript.trim()) return;
              const selected = listing?.entries.find(
                (item) => item.text_id === uploadTextId,
              );
              onSubmitUpload(
                file,
                transcript.trim(),
                selected?.transcript.trim() === transcript.trim()
                  ? selected.text_id
                  : null,
              );
            }}
          >
            <div
              className={`upload-dropzone${dragging ? " dragging" : ""}${file ? " has-file" : ""}`}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                chooseFile(event.dataTransfer.files[0]);
              }}
            >
              <input
                ref={input}
                type="file"
                accept="audio/*,.wav,.flac,.mp3,.m4a,.ogg,.webm"
                aria-label="Choose audio recording"
                onChange={(event) => chooseFile(event.target.files?.[0])}
              />
              <span className="upload-icon">
                {file ? <Check size={24} /> : <FileAudio size={26} />}
              </span>
              <h3>{file ? file.name : "Drop your recording here"}</h3>
              <p>
                {file
                  ? `${(file.size / 1024 / 1024).toFixed(2)} MB · Ready to analyze`
                  : "WAV, FLAC, MP3, or another supported audio format"}
              </p>
              <button
                type="button"
                className="button secondary"
                onClick={() => input.current?.click()}
              >
                {file ? "Choose another file" : "Browse files"}
              </button>
              <small>Up to 10 minutes · 50 MB maximum</small>
            </div>
            <div className="record-row">
              <span>
                {recording
                  ? "Recording… read your transcript aloud."
                  : "Or record a fresh take with your microphone."}
              </span>
              <button
                type="button"
                className={`button secondary${recording ? " recording" : ""}`}
                onClick={() => void toggleRecording()}
              >
                {recording ? <Square size={15} /> : <Mic size={15} />}
                {recording ? "Stop recording" : "Record audio"}
              </button>
            </div>
            <label className="field-label" htmlFor="upload-text">
              Reference text
            </label>
            <select
              id="upload-text"
              value={uploadTextId}
              onChange={(event) => {
                const id = event.target.value;
                setUploadTextId(id);
                const selected = listing?.entries.find(
                  (item) => item.text_id === id,
                );
                setTranscript(selected?.transcript ?? "");
              }}
            >
              <option value="auto">
                My own text · automatic reference matching
              </option>
              {listing?.entries.map((item) => (
                <option value={item.text_id} key={item.text_id}>
                  {item.title}
                </option>
              ))}
            </select>
            <label className="field-label" htmlFor="spoken-transcript">
              The words you spoke
            </label>
            <textarea
              id="spoken-transcript"
              placeholder="Paste the transcript of your recording…"
              rows={6}
              required
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
            />
            <p className="field-hint">
              We align these words to your audio. Matching library text uses its
              gold reference; other text uses calibrated ranges.
            </p>
            <div className="dialog-footer">
              <span>Audio is temporary, not saved to a history.</span>
              <button
                type="submit"
                className="button primary"
                disabled={!file || !transcript.trim() || recording}
              >
                Analyze recording <ArrowRight size={16} />
              </button>
            </div>
          </form>
        ) : (
          <div className="demo-picker">
            <p>
              Real recordings with controlled delivery changes. Choose a clean
              control or an injected flaw to see what the detector finds.
            </p>
            <label className="field-label" htmlFor="demo-text">
              Choose a speech
            </label>
            <select
              id="demo-text"
              value={entry?.text_id ?? ""}
              onChange={(event) => setEntryId(event.target.value)}
            >
              {listing?.entries.map((item) => (
                <option key={item.text_id} value={item.text_id}>
                  {item.title} · {formatTime(item.duration_s)}
                </option>
              ))}
            </select>
            <div className="demo-list">
              {entry &&
                demos.map((demo) => (
                  <button
                    key={demo.clip_id}
                    className="demo-option"
                    onClick={() => onSelectDemo(demo, entry)}
                  >
                    <span
                      className={`demo-icon${demo.flaw_kinds.length ? "" : " clean"}`}
                    >
                      {demo.flaw_kinds.length ? (
                        <FileAudio size={18} />
                      ) : (
                        <Check size={18} />
                      )}
                    </span>
                    <span>
                      <strong>
                        {demo.flaw_kinds.length
                          ? demo.flaw_kinds
                              .map((kind) => KIND_LABELS[kind])
                              .join(" + ")
                          : "Clean control"}
                      </strong>
                      <small>{demo.description}</small>
                    </span>
                    <Play size={16} />
                  </button>
                ))}
            </div>
            {!demos.length && (
              <div className="empty-library">
                The reference library is unavailable. Try uploading your own
                recording.
              </div>
            )}
          </div>
        )}
      </div>
    </dialog>
  );
}
