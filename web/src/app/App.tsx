import { useState } from 'react';
import {
  AudioLines,
  ChevronRight,
  CircleHelp,
  FolderOpen,
  Headphones,
  LayoutDashboard,
  Plus,
} from 'lucide-react';
import type { DemoClip, LibraryEntry } from '../contract';
import { HelpDialog } from '../shared/ui';
import { useAnalysis } from '../features/analysis-session';
import { usePlayback } from '../features/playback';
import { IngestionPanel } from '../features/speech-ingestion';
import {
  Header,
  ReviewWorkspace,
  StageProgress,
  WelcomeHero,
} from '../widgets';

export function App() {
  const analysis = useAnalysis();
  const [intake, setIntake] = useState<'upload' | 'demos' | null>(null);
  const [help, setHelp] = useState(false);

  const ready = analysis.state.status === 'ready' ? analysis.state : null;
  const playback = usePlayback(ready?.recording ?? null, ready?.report ?? null);
  const listing = analysis.library.status === 'ready' ? analysis.library.listing : null;
  const analyzing =
    analysis.state.status === 'running' || analysis.state.status === 'submitting';
  const isMock = import.meta.env.MODE === 'demo';

  const onDemo = (demo: DemoClip, entry: LibraryEntry) => {
    setIntake(null);
    void analysis.analyzeDemo(demo, entry);
  };

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to workspace
      </a>
      <aside className="app-sidebar">
        <a className="brand" href="/" aria-label="Delivery home">
          <span className="brand-mark">
            <AudioLines size={23} />
          </span>
          <span>
            delivery<span className="brand-period">.</span>
            <small>Speech review studio</small>
          </span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">S</span>
          <span>
            Local workspace<small>Speech delivery project</small>
          </span>
          <ChevronRight size={14} />
        </div>
        <nav className="main-nav" aria-label="Workspace">
          <span className="nav-label">Workspace</span>
          <button
            className="nav-item active"
            onClick={() => document.getElementById('main-content')?.focus()}
          >
            <LayoutDashboard size={18} /> Speech review
          </button>
          <button className="nav-item" onClick={() => setIntake('demos')}>
            <FolderOpen size={18} /> Reference library
            {listing && <span className="nav-count">{listing.entries.length}</span>}
          </button>
          <button className="nav-item" onClick={() => setIntake('upload')}>
            <Plus size={18} /> New analysis
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-tip">
            <Headphones size={21} />
            <strong>Listen. Notice. Improve.</strong>
            <p>Every finding starts with a moment you can hear.</p>
          </div>
          <button className="nav-item" onClick={() => setHelp(true)}>
            <CircleHelp size={18} /> How it works
          </button>
          <div className="local-status">
            <span className="status-dot" />
            {isMock ? 'Mock preview mode' : 'Local analysis workspace'}
          </div>
        </div>
      </aside>

      <div className="app-content">
        <Header
          onOpenIngest={() => setIntake('upload')}
          isAnalyzing={analyzing}
          isMock={isMock}
        />
        <main id="main-content" tabIndex={-1}>
          {isMock && (
            <div className="notice mock-notice">
              <CircleHelp size={18} />
              <span>
                Mock preview. These results are fixtures and do not analyze your audio. Use normal development mode for real analysis.
              </span>
            </div>
          )}
          {analysis.library.status === 'failed' && (
            <div className="notice error-notice" role="alert">
              <CircleHelp size={18} />
              <span>Reference library unavailable. {analysis.library.message}</span>
              <button className="text-button" onClick={analysis.retryLibrary}>
                Retry
              </button>
            </div>
          )}
          {ready ? (
            <ReviewWorkspace
              key={ready.recording.url}
              report={ready.report}
              recording={ready.recording}
              playback={playback}
              onNew={() => setIntake('upload')}
            />
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">Your practice, with perspective</span>
                  <h1>Speech review</h1>
                  <p>A clearer picture of your delivery, one passage at a time.</p>
                </div>
                <span className="pill muted">
                  <AudioLines size={14} /> Audio-first analysis
                </span>
              </div>
              {analysis.state.status === 'failed' && (
                <div className="analysis-error" role="alert">
                  <CircleHelp size={22} />
                  <div>
                    <h2>We couldn't finish this analysis</h2>
                    <p>{analysis.state.message}</p>
                  </div>
                  <button className="button secondary" onClick={() => setIntake('upload')}>
                    Try again
                  </button>
                </div>
              )}
              {analyzing ? (
                <section className="analysis-progress panel">
                  <div className="progress-art">
                    <AudioLines size={40} />
                  </div>
                  <span className="eyebrow">A closer listen is underway</span>
                  <h2>Reviewing your recording</h2>
                  <p>
                    {analysis.state.status === 'submitting' ||
                    analysis.state.status === 'running'
                      ? analysis.state.recording.name
                      : ''}
                  </p>
                  <StageProgress
                    currentStage={
                      analysis.state.status === 'running' ? analysis.state.stage : 'decode'
                    }
                    fraction={
                      analysis.state.status === 'running' ? analysis.state.fraction : 0
                    }
                    message={
                      analysis.state.status === 'running'
                        ? analysis.state.message
                        : 'Loading audio and submitting your analysis…'
                    }
                  />
                  <small>
                    Alignment runs locally on the CPU. Longer recordings take more time.
                  </small>
                </section>
              ) : (
                <WelcomeHero
                  listing={listing}
                  onUpload={() => setIntake('upload')}
                  onLibrary={() => setIntake('demos')}
                  onDemo={onDemo}
                />
              )}
            </>
          )}
        </main>
      </div>

      {intake && (
        <IngestionPanel
          listing={listing}
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
