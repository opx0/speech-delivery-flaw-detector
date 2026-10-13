import { useState } from 'react';
import {
  Activity,
  ArrowDownToLine,
  BookOpen,
  CircleHelp,
  FileAudio,
  Headphones,
  Plus,
  ShieldCheck,
} from 'lucide-react';
import type { Report } from '../../../contract';
import type { RecordingSource } from '../../../features/analysis-session';
import type { usePlayback } from '../../../features/playback';
import { computeOverall } from '../../../features/rubric-reweighting';
import { downloadJson, formatTime } from '../../../shared/lib';
import { ScoreBreakdown } from '../../score-breakdown';
import { TranscriptViewer } from '../../transcript-viewer';
import { DeviationChart } from '../../deviation-chart';
import { WaveformTimeline } from '../../waveform-timeline';
import { TransportBar } from '../../transport-bar';
import { FlawCardList } from '../../flaw-card-list';
import { FlawInspector } from '../../flaw-inspector';

export interface ReviewWorkspaceProps {
  report: Report;
  recording: RecordingSource;
  playback: ReturnType<typeof usePlayback>;
  onNew: () => void;
}

export function ReviewWorkspace({
  report,
  recording,
  playback,
  onNew,
}: ReviewWorkspaceProps) {
  const [weights, setWeights] = useState(report.weights);
  const [selectedId, setSelectedId] = useState<string | null>(
    () => [...report.regions].sort((a, b) => a.start - b.start)[0]?.id ?? null,
  );
  const [tab, setTab] = useState<'transcript' | 'features'>('transcript');

  const selected = report.regions.find((region) => region.id === selectedId) ?? null;
  const overall = computeOverall(report.axis_scores, weights);
  const adjusted = Object.entries(weights).some(([axis, value]) =>
    report.axis_scores.some(
      (score) => score.axis === axis && Math.abs(score.weight - value) > 0.00001,
    ),
  );

  function select(id: string) {
    setSelectedId(id);
    const region = report.regions.find((item) => item.id === id);
    if (region) playback.seek(region.start);
  }

  function exportReport() {
    const review: Report = {
      ...report,
      weights,
      overall,
      axis_scores: report.axis_scores.map((score) => ({
        ...score,
        weight: weights[score.axis],
      })),
    };
    downloadJson(review, 'speech-review.json');
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <FileAudio size={14} /> Recording review
          </div>
          <h1>{recording.name}</h1>
          <div className="recording-meta">
            <span>{formatTime(report.participant.duration_s)} duration</span>
            <span>{report.words.words.length} aligned words</span>
            <span className="pill teal">
              {report.reference.basis === 'baseline' ? 'Gold comparison' : 'Calibrated ranges'}
            </span>
          </div>
        </div>
        <div className="button-row">
          <button className="button secondary" onClick={exportReport}>
            <ArrowDownToLine size={16} /> Export report
          </button>
          <button className="button primary" onClick={onNew}>
            <Plus size={16} /> New analysis
          </button>
        </div>
      </div>

      {report.reference.basis === 'band' && (
        <div className="notice">
          <CircleHelp size={18} />
          <span>
            This text has no matching gold recording. Findings use ranges from{' '}
            {report.reference.n_reference_clips} reference clips and carry lower confidence.
          </span>
        </div>
      )}

      <ScoreBreakdown
        axisScores={report.axis_scores}
        weights={weights}
        overallScore={overall}
        adjusted={adjusted}
        onWeightsChange={setWeights}
      />

      <div className="review-grid">
        <div className="review-main">
          <section className="panel review-document">
            <div className="panel-heading">
              <div className="view-tabs" role="tablist" aria-label="Review view">
                <button
                  role="tab"
                  aria-selected={tab === 'transcript'}
                  className={tab === 'transcript' ? 'active' : ''}
                  onClick={() => setTab('transcript')}
                >
                  <BookOpen size={16} /> Transcript
                </button>
                <button
                  role="tab"
                  aria-selected={tab === 'features'}
                  className={tab === 'features' ? 'active' : ''}
                  onClick={() => setTab('features')}
                >
                  <Activity size={16} /> Acoustic features
                </button>
              </div>
              <span className="document-hint">Click to seek</span>
            </div>
            {tab === 'transcript' ? (
              <TranscriptViewer
                words={report.words}
                currentTime={playback.currentTime}
                regions={report.regions}
                selectedId={selectedId}
                onSeek={playback.seek}
                onSelect={select}
              />
            ) : (
              <DeviationChart
                overlaySeries={report.overlay}
                currentTime={playback.currentTime}
                onSeek={playback.seek}
              />
            )}
          </section>

          <section className="panel audio-panel">
            <div className="panel-heading">
              <div className="panel-title">
                <Headphones size={17} />
                <h2>Listen closely</h2>
              </div>
              <div className="source-switch" aria-label="Playback source">
                <button
                  aria-pressed={playback.source === 'participant'}
                  className={playback.source === 'participant' ? 'active' : ''}
                  onClick={() => playback.changeSource('participant')}
                >
                  Your recording
                </button>
                <button
                  aria-pressed={playback.source === 'baseline'}
                  className={playback.source === 'baseline' ? 'active' : ''}
                  disabled={report.reference.basis !== 'baseline'}
                  onClick={() => playback.changeSource('baseline')}
                >
                  Gold reference
                </button>
              </div>
            </div>
            <WaveformTimeline
              audioUrl={recording.url}
              duration={playback.duration}
              currentTime={playback.currentTime}
              regions={report.regions}
              selectedId={selectedId}
              onSeek={playback.seek}
              onSelectRegion={select}
            />
            <TransportBar playback={playback} />
            {playback.error && (
              <p className="audio-error" role="alert">
                {playback.error}
              </p>
            )}
            {playback.source === 'baseline' && (
              <p className="audio-note">
                Listening to the gold recording. The playhead stays aligned to your transcript.
              </p>
            )}
          </section>
        </div>

        <aside className="review-sidebar" aria-label="Delivery findings">
          <FlawCardList
            regions={report.regions}
            selectedId={selectedId}
            onSelect={select}
          />
          <FlawInspector
            region={selected}
            onPlayRegion={(region) => playback.playRegion(region, { loop: false })}
            onLoopRegion={(region) => playback.playRegion(region, { loop: true })}
          />
        </aside>
      </div>

      <div className="review-footer">
        <ShieldCheck size={14} />
        <span>Measured from your recording. Scores describe delivery, not content.</span>
        <span>Analysis v{report.run.package_version}</span>
      </div>
    </>
  );
}
