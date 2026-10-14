import { ArrowUpRight, AudioLines } from 'lucide-react';

export interface HeaderProps {
  onHome: () => void;
  onOpenIngest: () => void;
  onOpenLibrary: () => void;
  onHelp: () => void;
  onOpenGuide: () => void;
  onOpenHistory: () => void;
  isHistory: boolean;
  isGuide: boolean;
  isAnalyzing: boolean;
  isMock: boolean;
  hasReport: boolean;
}

export function Header({
  onHome, onOpenIngest, onOpenLibrary, onHelp, onOpenGuide, onOpenHistory, isHistory, isGuide, isAnalyzing, isMock, hasReport,
}: HeaderProps) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button className="brand" aria-label="Delivery home" onClick={onHome}>
          <span className="brand-mark"><AudioLines size={22} strokeWidth={1.5} /></span>
          <span>delivery<span className="brand-period">.</span><small>Speech review studio</small></span>
        </button>
        <nav className="main-nav" aria-label="Workspace">
          <button className={`nav-link${!isGuide && !isHistory && !hasReport && !isAnalyzing ? ' active' : ''}`} onClick={onHome}>Overview</button>
          <button className={`nav-link${isHistory ? ' active' : ''}`} onClick={onOpenHistory}>Run history</button>
          <button className="nav-link" onClick={onOpenLibrary}>Reference library</button>
          <button className="nav-link" onClick={onHelp}>How it works</button>
          <button className={`nav-link${isGuide ? ' active' : ''}`} onClick={onOpenGuide}>Setup guide</button>
        </nav>
        <div className="topbar-actions">
          <span className="connection-badge">
            <span className="status-dot" />{isMock ? 'Mock preview' : 'Local processing'}
          </span>
          <button className="button compact primary" onClick={onOpenIngest} disabled={isAnalyzing}>
            Add recording <ArrowUpRight size={15} />
          </button>
        </div>
      </div>
    </header>
  );
}
