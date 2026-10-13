import { ChevronRight, Plus, Radio } from "lucide-react";

export interface HeaderProps {
  onOpenIngest: () => void;
  isAnalyzing: boolean;
  isMock: boolean;
}

export function Header({
  onOpenIngest,
  isAnalyzing,
  isMock,
}: HeaderProps) {
  return (
    <header className="topbar">
      <div className="breadcrumbs">
        <span>Workspace</span>
        <ChevronRight size={14} />
        <strong>Speech review</strong>
      </div>
      <div className="topbar-actions">
        <span className="connection-badge">
          <Radio size={14} />
          {isMock ? "Mock preview" : "Local workspace"}
        </span>
        <button
          className="button compact secondary"
          onClick={onOpenIngest}
          disabled={isAnalyzing}
        >
          <Plus size={15} /> Add recording
        </button>
      </div>
    </header>
  );
}
