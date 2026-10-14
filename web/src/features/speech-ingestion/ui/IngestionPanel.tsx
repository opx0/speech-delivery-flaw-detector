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
import { RecordingFeedback } from "./RecordingFeedback";
import { RecordingPreview } from "./RecordingPreview";

export interface IngestionPanelProps {
  listing: LibraryListing | null;
  libraryLoading: boolean;
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
  libraryLoading,
  initialTab,
  onSelectDemo,
  onSubmitUpload,
  onClose,
}: IngestionPanelProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const mounted = useRef(true);
  const captureStarted = useRef(0);
  const [tab, setTab] = useState(initialTab);
  const [entryId, setEntryId] = useState(listing?.entries[0]?.text_id ?? "");
  const [uploadTextId, setUploadTextId] = useState("auto");
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [microphonePhase, setMicrophonePhase] = useState<'idle' | 'requesting' | 'recording' | 'saving'>('idle');
  const [microphoneStream, setMicrophoneStream] = useState<MediaStream | null>(null);
  const [recordedSeconds, setRecordedSeconds] = useState<number | null>(null);
  const recording = microphonePhase !== 'idle';
  const [dragging, setDragging] = useState(false);

  const entry =
    listing?.entries.find((item) => item.text_id === entryId) ??
    listing?.entries[0];
  const demos =
    listing?.demos.filter((item) => item.text_id === entry?.text_id) ?? [];

  useEffect(() => {
    mounted.current = true;
    if (opener.current === null && document.activeElement instanceof HTMLElement) {
      opener.current = document.activeElement;
    }
    dialog.current?.showModal();
    return () => {
      mounted.current = false;
      opener.current?.focus();
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
    setRecordedSeconds(null);
    setError(null);
  }

  async function toggleRecording() {
    if (recorder.current?.state === "recording") {
      recorder.current.stop();
      setMicrophonePhase('saving');
      return;
    }
    if (microphonePhase !== 'idle') return;
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError(
        "Microphone recording is not supported here. Upload a file instead.",
      );
      return;
    }
    setMicrophonePhase('requesting');
    setError(null);
    let stream: MediaStream | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      const capturedStream = stream;
      const active = new MediaRecorder(stream);
      const parts: Blob[] = [];
      active.ondataavailable = (event) => parts.push(event.data);
      active.onstop = () => {
        const seconds = (performance.now() - captureStarted.current) / 1000;
        capturedStream.getTracks().forEach(track => track.stop());
        if (!mounted.current) return;
        const extension = active.mimeType.includes("mp4")
          ? "mp4"
          : active.mimeType.includes("ogg")
            ? "ogg"
            : "webm";
        const captured = new File(parts, `microphone-recording.${extension}`, { type: active.mimeType });
        if (!captured.size) setError('No audio was captured. Please try again or upload a file.');
        else if (captured.size > 50 * 1024 * 1024) setError('The recording exceeds 50 MB. Try a shorter take.');
        else {
          chooseFile(captured);
          setRecordedSeconds(seconds);
        }
        setMicrophoneStream(null);
        setMicrophonePhase('idle');
        recorder.current = null;
      };
      active.onerror = () => {
        active.onstop = null;
        if (active.state !== 'inactive') active.stop();
        capturedStream.getTracks().forEach(track => track.stop());
        recorder.current = null;
        if (!mounted.current) return;
        setMicrophoneStream(null);
        setMicrophonePhase('idle');
        setError('Recording was interrupted. Please try again or upload a file.');
      };
      recorder.current = active;
      active.start(250);
      setFile(null);
      setRecordedSeconds(null);
      captureStarted.current = performance.now();
      setMicrophoneStream(stream);
      setMicrophonePhase('recording');
      setError(null);
    } catch {
      stream?.getTracks().forEach(track => track.stop());
      if (!mounted.current) return;
      setMicrophonePhase('idle');
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
          disabled={recording}
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
                if (!recording) chooseFile(event.dataTransfer.files[0]);
              }}
            >
              <input
                ref={input}
                type="file"
                accept="audio/*,.wav,.flac,.mp3,.m4a,.ogg,.webm"
                aria-label="Choose audio recording"
                disabled={recording}
                onChange={(event) => chooseFile(event.target.files?.[0])}
              />
              <span className="upload-icon">
                {file ? <Check size={24} /> : <FileAudio size={26} />}
              </span>
              <h3>{microphonePhase === 'recording' ? 'Capturing your microphone' : file ? file.name : "Drop your recording here"}</h3>
              <p role="status">
                {file
                  ? `${recordedSeconds !== null ? `${formatTime(recordedSeconds)} recorded · ` : ''}${(file.size / 1024 / 1024).toFixed(2)} MB · Add the spoken words below, then analyze`
                  : "WAV, FLAC, MP3, or another supported audio format"}
              </p>
              <button
                type="button"
                className="button secondary"
                onClick={() => input.current?.click()}
                disabled={recording}
              >
                {file ? "Choose another file" : "Browse files"}
              </button>
              <small>Up to 10 minutes · 50 MB maximum</small>
            </div>
            <div className="record-row">
              <span>
                {microphonePhase === 'requesting' ? 'Waiting for microphone permission. Check your browser prompt.'
                  : microphonePhase === 'saving' ? 'Saving your take…'
                  : microphonePhase === 'recording' ? 'Recording… read your transcript aloud.'
                  : 'Or record a fresh take with your microphone.'}
              </span>
              <button
                type="button"
                className={`button secondary${recording ? " recording" : ""}`}
                onClick={() => void toggleRecording()}
                disabled={microphonePhase === 'requesting' || microphonePhase === 'saving'}
              >
                {recording ? <Square size={15} /> : <Mic size={15} />}
                {microphonePhase === 'requesting' ? 'Allow microphone…' : microphonePhase === 'saving' ? 'Saving…' : microphonePhase === 'recording' ? 'Stop recording' : 'Record audio'}
              </button>
            </div>
            {microphonePhase === 'recording' && microphoneStream && <RecordingFeedback
              stream={microphoneStream}
              startedAt={captureStarted.current}
              onLimit={() => {
                if (recorder.current?.state === 'recording') {
                  recorder.current.stop();
                  setMicrophonePhase('saving');
                }
              }}
            />}
            {file && !recording && <RecordingPreview file={file} />}
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
              <span>Audio is temporary. Reports and transcripts are saved locally in Run history.</span>
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
                  {libraryLoading ? 'Loading reference examples…' : 'The reference library is unavailable. Try uploading your own recording.'}
              </div>
            )}
          </div>
        )}
      </div>
    </dialog>
  );
}
