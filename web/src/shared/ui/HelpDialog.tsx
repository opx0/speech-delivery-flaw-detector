import { useEffect, useRef } from 'react';
import { ShieldCheck, X } from 'lucide-react';

export interface HelpDialogProps {
  onClose: () => void;
}

export function HelpDialog({ onClose }: HelpDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  return (
    <dialog ref={ref} className="dialog help-dialog" onCancel={onClose} onClose={onClose}>
      <div className="dialog-heading">
        <div>
          <span className="eyebrow">A little context</span>
          <h2>How speech review works</h2>
        </div>
        <button className="icon-button" aria-label="Close help" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
      <div className="dialog-body help-content">
        <p>
          We measure delivery, rather than the quality of your ideas. Supply the words you spoke so the system can locate them in your recording.
        </p>
        <ol>
          <li>
            <strong>Add a recording.</strong> Upload audio, record with your microphone, or try a real dataset example.
          </li>
          <li>
            <strong>Choose your reference.</strong> Matching library text is compared with its gold reading. Other text uses calibrated ranges, with lower-confidence findings.
          </li>
          <li>
            <strong>Listen and inspect.</strong> Select a highlighted passage to see its timestamp, measured deviation, and explanation.
          </li>
        </ol>
        <p>
          Pitch is relative to each speaker's median. Energy is relative to their loud speech frames. Scores cover cadence, tone, pauses, and volume.
        </p>
        <div className="notice">
          <ShieldCheck size={18} />
          <span>Uploaded files are temporary. This workspace has no account or saved recording history.</span>
        </div>
      </div>
    </dialog>
  );
}
