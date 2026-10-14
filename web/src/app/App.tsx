import { lazy, Suspense, useEffect, useState } from 'react';
import { AudioLines, CircleHelp } from 'lucide-react';
import type { DemoClip, LibraryEntry } from '../contract';
import { HelpDialog } from '../shared/ui';
import { useAnalysis } from '../features/analysis-session';
import { usePlayback } from '../features/playback';
import { IngestionPanel } from '../features/speech-ingestion';
import { Header, ReviewWorkspace, StageProgress, WelcomeHero } from '../widgets';

const SetupGuide = lazy(() => import('../widgets/setup-guide').then(module => ({ default: module.SetupGuide })));
const RunHistoryDashboard = lazy(() => import('../widgets/run-history').then(module => ({ default: module.RunHistoryDashboard })));
type Page = 'workspace' | 'docs' | 'history';
function pageFromLocation(): Page {
  const path = window.location.pathname.replace(/\/$/, '');
  return path === '/docs' ? 'docs' : path === '/history' ? 'history' : 'workspace';
}

export function App() {
  const analysis = useAnalysis();
  const [intake, setIntake] = useState<'upload' | 'demos' | null>(null);
  const [help, setHelp] = useState(false);
  const [page, setPage] = useState<Page>(pageFromLocation);
  const [savedRunId, setSavedRunId] = useState<string | null>(() => new URLSearchParams(window.location.search).get('run'));

  const ready = analysis.state.status === 'ready' ? analysis.state : null;
  const playback = usePlayback(ready?.recording ?? null, ready?.report ?? null);
  const listing = analysis.library.status === 'ready' ? analysis.library.listing : null;
  const analyzing = analysis.state.status === 'running' || analysis.state.status === 'submitting';
  const isMock = import.meta.env.MODE === 'demo';

  useEffect(() => {
    const onHistory = () => {
      setPage(pageFromLocation());
      setSavedRunId(new URLSearchParams(window.location.search).get('run'));
    };
    window.addEventListener('popstate', onHistory);
    return () => window.removeEventListener('popstate', onHistory);
  }, []);

  useEffect(() => {
    document.title = page === 'docs' ? 'Setup guide · Speech delivery' : page === 'history' ? 'Run history · Speech delivery' : 'Speech delivery flaw detector';
    if (page !== 'workspace') playback.pause();
  }, [page]);

  useEffect(() => {
    if (intake !== null) playback.pause();
  }, [intake]);

  function navigate(next: Page) {
    const path = next === 'docs' ? '/docs' : next === 'history' ? '/history' : '/';
    if (pageFromLocation() !== next) window.history.pushState(null, '', path);
    setPage(next);
    setSavedRunId(null);
    setIntake(null);
    setHelp(false);
    window.scrollTo({ top: 0 });
    document.getElementById('main-content')?.focus({ preventScroll: true });
  }

  function onDemo(demo: DemoClip, entry: LibraryEntry) {
    setIntake(null);
    void analysis.analyzeDemo(demo, entry);
  }

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">Skip to workspace</a>
      <Header
        onHome={() => { analysis.reset(); navigate('workspace'); }}
        onOpenIngest={() => { navigate('workspace'); setIntake('upload'); }}
        onOpenLibrary={() => { navigate('workspace'); setIntake('demos'); }}
        onHelp={() => setHelp(true)}
        onOpenGuide={() => navigate('docs')}
        onOpenHistory={() => navigate('history')}
        isHistory={page === 'history'}
        isGuide={page === 'docs'}
        isAnalyzing={analyzing}
        isMock={isMock}
        hasReport={ready !== null}
      />
      <main id="main-content" tabIndex={-1}>
        {page === 'docs' && <Suspense fallback={<div className="guide-loading" role="status">Loading setup guide…</div>}><SetupGuide onBack={() => navigate('workspace')} /></Suspense>}
        {page === 'history' && <Suspense fallback={<div className="guide-loading" role="status">Loading run history…</div>}><RunHistoryDashboard
          selectedId={savedRunId} isMock={isMock} onSelect={id => {
            setSavedRunId(id);
            window.history.pushState(null, '', id ? `/history?run=${encodeURIComponent(id)}` : '/history');
          }}
        /></Suspense>}
        <div hidden={page !== 'workspace'}>
        {isMock && (
          <div className="notice mock-notice">
            <CircleHelp size={18} />
            <span>Mock preview. These results are fixtures and do not analyze your audio.</span>
          </div>
        )}
        {analysis.library.status === 'failed' && (
          <div className="notice error-notice" role="alert">
            <CircleHelp size={18} />
            <span>Reference library unavailable. {analysis.library.message}</span>
            <button className="text-button" onClick={analysis.retryLibrary}>Retry</button>
          </div>
        )}
        {analysis.library.status === 'loading' && <div className="notice" role="status">Connecting to the reference library… You can still add your recording.</div>}
        {ready ? (
          <ReviewWorkspace
            key={ready.recording.url}
            report={ready.report}
            recording={ready.recording}
            playback={playback}
            activity={{ startedAt: ready.startedAt, logs: ready.logs }}
            onNew={() => setIntake('upload')}
            onViewRun={isMock ? undefined : () => {
              navigate('history');
              setSavedRunId(ready.jobId);
              window.history.replaceState(null, '', `/history?run=${encodeURIComponent(ready.jobId)}`);
            }}
          />
        ) : (
          <>
            {analysis.state.status === 'failed' && (
              <div className="analysis-error" role="alert">
                <CircleHelp size={22} />
                <div>
                  <h2>We couldn't finish this analysis</h2>
                  <p>{analysis.state.message}</p>
                </div>
                <button className="button secondary" onClick={() => setIntake('upload')}>Try again</button>
              </div>
            )}
            {analyzing ? (
              <section className="analysis-progress panel">
                <div className="progress-art"><AudioLines size={32} /></div>
                <span className="eyebrow">Speech analysis</span>
                <h1>Reviewing your recording</h1>
                <p>
                  {analysis.state.status === 'submitting' || analysis.state.status === 'running'
                    ? analysis.state.recording.name : ''}
                </p>
                <StageProgress
                  currentStage={analysis.state.status === 'running' ? analysis.state.stage : 'decode'}
                  fraction={analysis.state.status === 'running' ? analysis.state.fraction : 0}
                  message={analysis.state.status === 'running' || analysis.state.status === 'submitting' ? analysis.state.message : ''}
                  startedAt={analysis.state.status === 'running' || analysis.state.status === 'submitting' ? analysis.state.startedAt : Date.now()}
                  logs={analysis.state.status === 'running' || analysis.state.status === 'submitting' ? analysis.state.logs : []}
                  preparing={analysis.state.status === 'submitting'}
                />
                <button className="text-button stop-waiting" onClick={analysis.reset}>Stop waiting</button>
                <small className="stop-waiting-hint">Returns to the workspace; a submitted job may finish in the background.</small>
              </section>
            ) : (
              <WelcomeHero
                listing={listing}
                libraryLoading={analysis.library.status === 'loading'}
                onUpload={() => setIntake('upload')}
                onLibrary={() => setIntake('demos')}
                onDemo={onDemo}
              />
            )}
          </>
        )}
        </div>
      </main>
      <footer className="app-footer">
        <span className="footer-wordmark">delivery.</span>
        <span>Speech delivery flaw detector</span>
        <button onClick={() => setHelp(true)}>About this review</button>
      </footer>

      {intake && (
        <IngestionPanel
          listing={listing}
          libraryLoading={analysis.library.status === 'loading'}
          initialTab={intake}
          onSelectDemo={onDemo}
          onSubmitUpload={(file, transcript, textId) => {
            setIntake(null);
            void analysis.analyzeUpload(file, transcript, textId);
          }}
          onClose={() => setIntake(null)}
        />
      )}
      {help && <HelpDialog onClose={() => setHelp(false)} />}
    </div>
  );
}

export default App;
