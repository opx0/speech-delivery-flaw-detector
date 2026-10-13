/* Generated from contract/schema/contract.schema.json by npm run contract:ts. Do not edit. */

/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "FlawKind".
 */
export type FlawKind = "rush" | "drag" | "monotone" | "hesitation" | "pause_collapse" | "energy_fade";
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "ClipRole".
 */
export type ClipRole =
  | "gold"
  | "control"
  | "flawed"
  | "natural_reader"
  | "speaker_shifted"
  | "human_clean"
  | "human_flawed"
  | "normative_reference";
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Sex".
 */
export type Sex = "female" | "male" | "unspecified";
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Split".
 */
export type Split = "calibration" | "test";
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "License".
 */
export type License = "public-domain-mark" | "cc0" | "us-government-work" | "cc-by-4.0" | "original-recording";
/**
 * Competition category. Extemporaneous has no fixed text, so it never has a flawed mirror.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Category".
 */
export type Category = "interpretive_reading" | "declamation" | "persuasive_oratory" | "extemporaneous";
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Stage".
 */
export type Stage = "decode" | "align" | "extract" | "compare" | "explain";
/**
 * The four delivery axes a judge scores.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Axis".
 */
export type Axis = "cadence" | "tone" | "pauses" | "volume";
/**
 * Time-series features rendered in the overlay and used as flaw evidence.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "FeatureName".
 */
export type FeatureName = "speech_rate" | "pitch" | "pitch_variation" | "energy" | "pause" | "clarity";
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "ErrorCode".
 */
export type ErrorCode =
  "unsupported_audio" | "too_long" | "too_large" | "transcript_mismatch" | "alignment_failed" | "internal";

export interface Contract {
  AnalyzeOptions: AnalyzeOptions;
  DatasetManifest: DatasetManifest;
  JobCreated: JobCreated;
  JobEvent: ProgressEvent | DoneEvent | FailedEvent;
  LibraryEntry: LibraryEntry;
  LibraryListing: LibraryListing;
  Report: Report;
  RubricWeights: RubricWeights;
}
/**
 * JSON sent beside the audio file. A transcript matching a library text selects the
 * contrast mode, anything else selects the normative mode.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "AnalyzeOptions".
 */
export interface AnalyzeOptions {
  library_text_id: string | null;
  transcript: string;
  weights: RubricWeights | null;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "RubricWeights".
 */
export interface RubricWeights {
  cadence: number;
  pauses: number;
  tone: number;
  volume: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "DatasetManifest".
 */
export interface DatasetManifest {
  clips: ClipLabel[];
  dataset_version: string;
  schema_version: 1;
  sources: SourceRecord[];
  texts: TextRecord[];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "ClipLabel".
 */
export interface ClipLabel {
  alignment: WordAlignment;
  audio: AudioFile;
  baseline_clip_id: string | null;
  flaws: FlawLabel[];
  id: string;
  pipeline: PipelineStamp | null;
  role: ClipRole;
  source_id: string | null;
  speaker_sex: Sex;
  split: Split;
  text_id: string;
}
/**
 * Words in spoken order, plus the sentence partition used for pause and fade rules.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "WordAlignment".
 */
export interface WordAlignment {
  sentences: WordSpan[];
  words: Word[];
}
/**
 * Inclusive range of word indices.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "WordSpan".
 */
export interface WordSpan {
  /**
   * Zero-based index into a word alignment.
   */
  first: number;
  /**
   * Zero-based index into a word alignment.
   */
  last: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Word".
 */
export interface Word {
  confidence: number;
  /**
   * Time in seconds.
   */
  end: number;
  /**
   * Time in seconds.
   */
  start: number;
  text: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "AudioFile".
 */
export interface AudioFile {
  /**
   * Time in seconds.
   */
  duration_s: number;
  /**
   * Forward-slash path relative to the dataset root.
   */
  path: string;
  sample_rate_hz: number;
  sha256: string;
}
/**
 * A ground-truth flaw region. `injection` is set for DSP clips and absent for human ones.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "FlawLabel".
 */
export interface FlawLabel {
  /**
   * Time in seconds.
   */
  end: number;
  injection:
    (RushParams | DragParams | MonotoneParams | HesitationParams | PauseCollapseParams | EnergyFadeParams) | null;
  kind: FlawKind;
  level: 1 | 2 | 3 | 4;
  /**
   * Time in seconds.
   */
  start: number;
  words: WordSpan;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "RushParams".
 */
export interface RushParams {
  kind: "rush";
  rate_factor: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "DragParams".
 */
export interface DragParams {
  kind: "drag";
  rate_factor: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "MonotoneParams".
 */
export interface MonotoneParams {
  kind: "monotone";
  pitch_excursion_retained: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "HesitationParams".
 */
export interface HesitationParams {
  kind: "hesitation";
  /**
   * @minItems 1
   */
  silences: [InsertedSilence, ...InsertedSilence[]];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "InsertedSilence".
 */
export interface InsertedSilence {
  /**
   * Zero-based index into a word alignment.
   */
  after_word: number;
  /**
   * Time in seconds.
   */
  duration_s: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "PauseCollapseParams".
 */
export interface PauseCollapseParams {
  kind: "pause_collapse";
  pause_retained: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "EnergyFadeParams".
 */
export interface EnergyFadeParams {
  drop_db: number;
  fade_fraction: number;
  kind: "energy_fade";
}
/**
 * How a derived clip was produced, enough to regenerate it byte for byte.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "PipelineStamp".
 */
export interface PipelineStamp {
  config_hash: string;
  name: string;
  seed: number;
  version: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "SourceRecord".
 */
export interface SourceRecord {
  audio_url: string;
  /**
   * Time in seconds.
   */
  excerpt_end: number;
  /**
   * Time in seconds.
   */
  excerpt_start: number;
  id: string;
  page_url: string;
  rights: RightsEvidence;
  speaker_name: string;
  speaker_sex: Sex;
  title: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "RightsEvidence".
 */
export interface RightsEvidence {
  evidence_url: string;
  license: License;
  notes: string;
  verified: boolean;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "TextRecord".
 */
export interface TextRecord {
  category: Category;
  id: string;
  title: string;
  transcript: string;
  transcript_url: string;
}
/**
 * The response to `POST /api/jobs`. Events arrive on `GET /api/jobs/{job_id}/events`.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "JobCreated".
 */
export interface JobCreated {
  job_id: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "ProgressEvent".
 */
export interface ProgressEvent {
  fraction: number;
  job_id: string;
  message: string;
  stage: Stage;
  type: "progress";
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "DoneEvent".
 */
export interface DoneEvent {
  job_id: string;
  report: Report;
  type: "done";
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Report".
 */
export interface Report {
  axis_scores: AxisScore[];
  /**
   * Score from 0 to 100.
   */
  overall: number;
  overlay: OverlaySeries[];
  participant: ParticipantInfo;
  reference: BaselineReference | BandReference;
  regions: FlawRegion[];
  run: RunStamp;
  schema_version: 1;
  weights: RubricWeights;
  words: WordAlignment;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "AxisScore".
 */
export interface AxisScore {
  axis: Axis;
  /**
   * Score from 0 to 100.
   */
  score: number;
  weight: number;
}
/**
 * One feature on the participant's clock, with what was expected drawn beside it.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "OverlaySeries".
 */
export interface OverlaySeries {
  expected: BaselineSeries | BandSeries;
  feature: FeatureName;
  /**
   * Time in seconds.
   */
  hop_s: number;
  participant: (number | null)[];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "BaselineSeries".
 */
export interface BaselineSeries {
  basis: "baseline";
  values: (number | null)[];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "BandSeries".
 */
export interface BandSeries {
  basis: "band";
  high: (number | null)[];
  low: (number | null)[];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "ParticipantInfo".
 */
export interface ParticipantInfo {
  audio_sha256: string;
  /**
   * Time in seconds.
   */
  duration_s: number;
  filename: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "BaselineReference".
 */
export interface BaselineReference {
  basis: "baseline";
  clip_id: string;
  text_id: string;
  /**
   * @minItems 2
   */
  warp: [WarpAnchor, WarpAnchor, ...WarpAnchor[]];
}
/**
 * Participant time `participant_s` lines up with baseline time `baseline_s`.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "WarpAnchor".
 */
export interface WarpAnchor {
  /**
   * Time in seconds.
   */
  baseline_s: number;
  /**
   * Time in seconds.
   */
  participant_s: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "BandReference".
 */
export interface BandReference {
  bands_version: string;
  basis: "band";
  n_reference_clips: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "FlawRegion".
 */
export interface FlawRegion {
  axis: Axis;
  deviation: Deviation;
  /**
   * Time in seconds.
   */
  end: number;
  explanation: Explanation;
  id: string;
  kind: FlawKind;
  severity: number;
  /**
   * Time in seconds.
   */
  start: number;
  words: WordSpan;
}
/**
 * The measured gap behind a flaw.
 *
 * `delta` is observed minus the baseline value, or the signed distance outside the nearest
 * band edge. `z_score` is that gap in units of the reference's own variability.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Deviation".
 */
export interface Deviation {
  delta: number;
  expected: BaselineExpected | BandExpected;
  feature: FeatureName;
  observed: number;
  unit: string;
  z_score: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "BaselineExpected".
 */
export interface BaselineExpected {
  basis: "baseline";
  value: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "BandExpected".
 */
export interface BandExpected {
  basis: "band";
  high: number;
  low: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Explanation".
 */
export interface Explanation {
  detail: string;
  headline: string;
  quoted_text: string;
}
/**
 * Everything that must match for two runs to produce the identical report.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "RunStamp".
 */
export interface RunStamp {
  config_hash: string;
  models: ModelStamp[];
  package_version: string;
  seed: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "ModelStamp".
 */
export interface ModelStamp {
  name: string;
  revision: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "FailedEvent".
 */
export interface FailedEvent {
  code: ErrorCode;
  job_id: string;
  message: string;
  type: "failed";
}
/**
 * A speech the participant can read and be compared against.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "LibraryEntry".
 */
export interface LibraryEntry {
  baseline_audio_url: string;
  baseline_clip_id: string;
  category: Category;
  /**
   * Time in seconds.
   */
  duration_s: number;
  text_id: string;
  title: string;
  transcript: string;
}
/**
 * The response to `GET /api/library`.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "LibraryListing".
 */
export interface LibraryListing {
  demos: DemoClip[];
  entries: LibraryEntry[];
}
/**
 * A dataset clip a visitor can analyze without recording anything. The true flaws are
 * listed so the demo can show the detector against a known answer.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "DemoClip".
 */
export interface DemoClip {
  audio_url: string;
  clip_id: string;
  description: string;
  flaw_kinds: FlawKind[];
  level: number | null;
  text_id: string;
  title: string;
}
