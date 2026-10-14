import { useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, ArrowLeft, ArrowRight, History, RefreshCw, ShieldCheck } from 'lucide-react';
import type { SavedRun, RunStatus } from '../../../features/run-history';
import { useRunHistory } from '../../../features/run-history';
import { downloadJson, formatTime } from '../../../shared/lib';
import { KIND_LABELS } from '../../../entities/flaw';
import { DeviationChart } from '../../deviation-chart';
import { TranscriptViewer } from '../../transcript-viewer';

const STATUS_LABELS: Record<RunStatus, string> = {
  queued: 'Queued', running: 'Processing', done: 'Completed', failed: 'Failed', interrupted: 'Interrupted',
};
const date = (seconds: number) => new Date(seconds * 1000).toLocaleString();
const elapsed = (seconds: number | null) => seconds === null ? '—' : `${seconds.toFixed(2)}s`;

function Status({ status }: { status: RunStatus }) {
  return <span className={`pill run-status ${status}`}>{STATUS_LABELS[status]}</span>;
}

function ParameterTree({ data }: { data: unknown }) {
  if (data === null || typeof data !== 'object') return <span>{String(data ?? 'not recorded')}</span>;
  if (Array.isArray(data)) return <details className="parameter-array"><summary>{data.length} entries · expand to inspect</summary>
    <ParameterTree data={Object.fromEntries(data.map((value, index) => [String(index), value]))} />
  </details>;
  return <dl className="parameter-tree">{Object.entries(data).map(([key, value]) => (
    <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd><ParameterTree data={value} /></dd></div>
  ))}</dl>;
}

function RunDetail({ run }: { run: SavedRun }) {
  const root = useRef<HTMLElement>(null);
  useEffect(() => { root.current?.scrollIntoView({ block: 'start' }); }, []);
  const [tab, setTab] = useState<'report' | 'parameters' | 'activity'>('report');
  const [time, setTime] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [exported, setExported] = useState(false);
  const report = run.report;
  return (
    <section ref={root} className="run-detail" aria-label="Saved run details">
      <div className="page-heading run-detail-heading">
        <div><span className="eyebrow">Saved evidence · {run.job_id}</span><h2>{run.filename}</h2>
          <div className="recording-meta"><Status status={run.status} /><span>{date(run.created_at)}</span><span>{elapsed(run.elapsed_s)} processing</span></div>
        </div>
        <button className="button secondary" onClick={() => { downloadJson(run, `${run.job_id}-evidence.json`); setExported(true); }}>
          <ArrowDownToLine size={16} /> Export run evidence
        </button>
      </div>
      {exported && <p className="export-status" role="status">Download requested: {run.job_id}-evidence.json</p>}
      <div className="notice"><ShieldCheck size={18} /><span>
        Reports-only history. Audio is not saved in the journal; temporary uploads are deleted after processing. This saved view has no playback.
        Transcript, measured features, parameters, and findings remain available. Local storage is not an independent accuracy verification.
      </span></div>
      {run.error && <div className="notice error-notice" role="alert"><span>{run.error.code}: {run.error.message}</span></div>}
      {run.upload_cleanup === 'incomplete' && <div className="notice error-notice" role="alert">Temporary upload cleanup failed. Server storage needs attention.</div>}
      {run.status === 'interrupted' && run.upload_cleanup === 'pending' && <div className="notice error-notice">The server stopped before upload cleanup was confirmed. Temporary files may remain; check server storage.</div>}
      <div className="history-tabs view-tabs" role="tablist" aria-label="Run evidence">
        {(['report', 'parameters', 'activity'] as const).map(value => <button key={value} role="tab" aria-selected={tab === value}
          aria-controls={`run-${value}`} className={tab === value ? 'active' : ''} onClick={() => setTab(value)}>
          {value === 'report' ? 'Saved report' : value === 'parameters' ? 'Parameters & provenance' : 'Stage activity'}
        </button>)}
      </div>
      {tab === 'report' && <div id="run-report" role="tabpanel">
        {!report ? <div className="empty-library">{run.status === 'running' || run.status === 'queued'
          ? 'This run is still processing. Its saved result will appear here automatically.'
          : 'No completed report was produced for this run. Inspect parameters and stage activity for the recorded outcome.'}</div> : <>
          <div className="score-grid history-scores">
            <div className="overall-card"><span className="eyebrow">Original delivery score</span><div><strong>{report.overall.toFixed(1)}</strong><span>/ 100</span></div><small>Not an accuracy percentage</small></div>
            {report.axis_scores.map(axis => <div className="axis-card" key={axis.axis}><span className="eyebrow">{axis.axis}</span>
              <div className="axis-score"><strong>{axis.score.toFixed(1)}</strong><span>/ 100</span></div><small>Weight {(axis.weight * 100).toFixed(0)}%</small></div>)}
          </div>
          <p className="history-caption">{report.regions.length} findings · {report.words.words.length} aligned words · {formatTime(report.participant.duration_s)} audio · {report.reference.basis === 'baseline'
            ? `Gold comparison: ${report.reference.clip_id}` : `Lower-confidence calibrated ranges: ${report.reference.n_reference_clips} reference clips`}. Original server scores are preserved; review-time weight adjustments do not overwrite them.</p>
          <section className="panel history-findings"><div className="panel-heading"><h3>Measured findings</h3><span>{report.regions.length} regions</span></div>
            {!report.regions.length && <p className="history-caption">No regions were flagged. This does not prove the recording has no delivery flaws.</p>}
            {report.regions.map(region => <article key={region.id} className={`history-finding${selectedId === region.id ? ' selected' : ''}`}>
              <button className="text-button" onClick={() => { setSelectedId(region.id); setTime(region.start); }}>
                {formatTime(region.start)}–{formatTime(region.end)} · {KIND_LABELS[region.kind]}
              </button><h4>{region.explanation.headline}</h4><p>{region.explanation.detail}</p>
              <blockquote>{region.explanation.quoted_text}</blockquote>
              <dl className="finding-measures"><div><dt>Observed</dt><dd>{region.deviation.observed.toFixed(3)} {region.deviation.unit}</dd></div>
                <div><dt>Expected</dt><dd>{region.deviation.expected.basis === 'baseline' ? region.deviation.expected.value.toFixed(3)
                  : `${region.deviation.expected.low.toFixed(3)}–${region.deviation.expected.high.toFixed(3)}`} {region.deviation.unit}</dd></div>
                <div><dt>Deviation z</dt><dd>{region.deviation.z_score.toFixed(3)}</dd></div>
                <div><dt>Severity</dt><dd>{region.severity.toFixed(3)} / 1</dd></div></dl>
            </article>)}
          </section>
          <section className="panel history-transcript"><div className="panel-heading"><h3>Word-aligned transcript</h3><span className="document-hint">Click to inspect · no playback</span></div>
            <TranscriptViewer words={report.words} regions={report.regions} selectedId={selectedId} currentTime={time} onSeek={setTime} onSelect={setSelectedId} inspectionOnly />
          </section>
          <section className="panel history-chart"><div className="panel-heading"><h3>Saved acoustic measurements</h3><span className="document-hint">Inspecting {formatTime(time)}</span></div>
            <DeviationChart overlaySeries={report.overlay} currentTime={time} onSeek={setTime} inspectionOnly />
            <label className="history-inspection">Inspection position <input aria-label="Inspection position in seconds" type="range" min={0} max={report.participant.duration_s} step={0.02} value={time} onChange={event => setTime(Number(event.target.value))} /><span>{formatTime(time)}</span></label>
          </section>
        </>}
      </div>}
      {tab === 'parameters' && <div id="run-parameters" role="tabpanel" className="panel history-parameters">
        <h3>Input identity</h3><ParameterTree data={{ filename: run.filename, upload_bytes: run.upload_bytes, audio_sha256: run.audio_sha256, dataset_manifest_sha256: run.parameters.dataset_manifest_sha256, upload_cleanup: run.upload_cleanup }} />
        <h3>Submitted options</h3><ParameterTree data={run.options} />
        <h3>Effective rubric weights</h3><ParameterTree data={run.parameters.effective_weights} />
        <h3>Model & runtime</h3><ParameterTree data={{ alignment_model: run.parameters.alignment_model, transcript_match_threshold: run.parameters.transcript_match_threshold, runtime_at_startup: run.parameters.runtime_at_startup, runtime_after: run.runtime_after }} />
        <h3>Calibration snapshot</h3><p className="history-caption">Exact calibration loaded for this run, not today's settings. Thresholds, spreads, bands, and scoring parameters are preserved.</p><ParameterTree data={run.parameters.calibration} />
        {report && <><h3>Report provenance & reference</h3><ParameterTree data={{ run: report.run, reference: report.reference }} /></>}
      </div>}
      {tab === 'activity' && <section id="run-activity" role="tabpanel" className="panel history-activity">
        <h3>Server-recorded stage activity</h3><p className="history-caption">Elapsed time is measured on the server from worker start; queue time is separate. Percentages describe one stage, not overall accuracy or an ETA.</p>
        <dl className="finding-measures"><div><dt>Submitted</dt><dd>{date(run.created_at)}</dd></div><div><dt>Started</dt><dd>{run.started_at ? date(run.started_at) : '—'}</dd></div>
          <div><dt>Finished</dt><dd>{run.finished_at ? date(run.finished_at) : '—'}</dd></div><div><dt>Processing</dt><dd>{elapsed(run.elapsed_s)}</dd></div></dl>
        <ol aria-label="Saved server activity">{run.events.map((event, index) => <li key={index}>
          <time dateTime={new Date(event.at * 1000).toISOString()}>{new Date(event.at * 1000).toLocaleTimeString()}</time>
          <span>{event.stage && <strong>{event.stage.toUpperCase()} · {Math.round((event.fraction ?? 0) * 100)}% · </strong>}{event.message}</span>
          <code>{elapsed(event.elapsed_s)}</code>
        </li>)}</ol>
      </section>}
    </section>
  );
}

export function RunHistoryDashboard({ selectedId, onSelect, isMock }: {
  selectedId: string | null; onSelect: (id: string | null) => void; isMock: boolean;
}) {
  const history = useRunHistory(isMock ? null : selectedId);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<RunStatus | 'all'>('all');
  const listing = history.listing;
  const runs = listing?.runs.filter(run => (status === 'all' || run.status === status)
    && `${run.filename} ${run.job_id}`.toLowerCase().includes(query.toLowerCase())) ?? [];
  return <>
    <div className="page-heading"><div><span className="eyebrow"><History size={14} /> Accountability dashboard</span><h1>Run history</h1>
      <p className="history-intro">What ran, which parameters it used, and what it measured. Saved locally on this server—not just in this browser tab.</p></div>
      <button className="button secondary" onClick={history.refresh} disabled={isMock}><RefreshCw size={16} /> Refresh history</button>
    </div>
    {isMock ? <div className="notice mock-notice">Run history is unavailable in mock preview. Open the real API on port 8000 to see actual saved runs.</div> : <>
      <div className="history-stats">
        {[['Saved runs', listing?.total], ['Completed', listing?.counts.done], ['Processing / queued', listing ? listing.counts.running + listing.counts.queued : undefined], ['Failed / interrupted', listing ? listing.counts.failed + listing.counts.interrupted : undefined]].map(([label, count]) => (
          <div className="panel" key={label}><span className="eyebrow">{label}</span><strong>{count ?? '—'}</strong></div>
        ))}
      </div>
      <p className="history-caption">History begins when report-only storage is enabled. Earlier analyses and visual checks are not reconstructed or claimed as verified.</p>
      {history.error && <div className="notice error-notice" role="alert">{history.error} <button className="text-button" onClick={history.refresh}>Retry</button></div>}
      {!listing && !history.error && <p className="history-caption" role="status">Loading saved runs…</p>}
      {listing && <section className="panel history-list" aria-label="Saved analyses">
        <div className="panel-heading"><h2>Analyses</h2><div className="history-filters">
          <input aria-label="Find runs on this page" placeholder="Find on this page…" value={query} onChange={event => setQuery(event.target.value)} />
          <select aria-label="Filter status on this page" value={status} onChange={event => setStatus(event.target.value as RunStatus | 'all')}><option value="all">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></div></div>
        {!listing.total ? <div className="history-empty"><History size={28} /><h3>No saved runs yet</h3><p>Analyze a recording or demo. Its parameters, stage activity, and outcome will appear here automatically.</p></div> : <>
          <div className="history-table-scroll"><table><caption className="sr-only">Saved runs, newest first</caption><thead><tr><th>Recording / run</th><th>Submitted</th><th>Status</th><th>Score</th><th>Findings</th><th>Time</th></tr></thead>
            <tbody>{runs.map(run => <tr key={run.job_id} className={selectedId === run.job_id ? 'selected' : ''}>
              <td><button className="run-open" onClick={() => onSelect(run.job_id)} aria-label={`Inspect run ${run.job_id}: ${run.filename}`}><strong>{run.filename}</strong><small>{run.job_id}</small></button></td>
              <td>{date(run.created_at)}</td><td><Status status={run.status} /></td><td>{run.overall?.toFixed(1) ?? '—'}</td><td>{run.findings ?? '—'}</td><td>{elapsed(run.elapsed_s)}</td>
            </tr>)}</tbody></table></div>
          {!runs.length && <p className="history-caption">No matches on this page.</p>}
          <div className="history-pagination"><button className="text-button" disabled={history.offset === 0} onClick={() => history.setOffset(Math.max(0, history.offset - 30))}><ArrowLeft size={14} /> Newer</button>
            <span>{history.offset + 1}–{Math.min(history.offset + listing.runs.length, listing.total)} of {listing.total}</span>
            <button className="text-button" disabled={history.offset + listing.runs.length >= listing.total} onClick={() => history.setOffset(history.offset + 30)}>Older <ArrowRight size={14} /></button></div>
        </>}
      </section>}
      {selectedId && <><button className="text-button" onClick={() => onSelect(null)}>Close saved run</button>
        {history.detailError && <div className="notice error-notice" role="alert">{history.detailError}</div>}
        {!history.detail && !history.detailError && <p className="history-caption" role="status">Opening saved run…</p>}
        {history.detail?.job_id === selectedId && <RunDetail key={selectedId} run={history.detail} />}
      </>}
    </>}
  </>;
}
