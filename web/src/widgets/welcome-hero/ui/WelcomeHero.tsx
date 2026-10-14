import { ArrowRight, ArrowUpRight, AudioLines, Play, ShieldCheck } from 'lucide-react';
import type { DemoClip, LibraryEntry, LibraryListing } from '../../../contract';
import { KIND_LABELS } from '../../../entities/flaw';
import { formatTime } from '../../../shared/lib';

export interface WelcomeHeroProps {
  listing: LibraryListing | null;
  libraryLoading: boolean;
  onUpload: () => void;
  onLibrary: () => void;
  onDemo: (demo: DemoClip, entry: LibraryEntry) => void;
}

export function WelcomeHero({ listing, libraryLoading, onUpload, onLibrary, onDemo }: WelcomeHeroProps) {
  const examples = listing?.entries.slice(0, 3).flatMap((entry) => {
    const kind = entry.text_id === 'new-colossus' ? 'drag' : 'rush';
    const demo = listing.demos.find(d => d.text_id === entry.text_id && d.flaw_kinds.includes(kind));
    return demo ? [{ entry, demo }] : [];
  }) ?? [];

  return (
    <>
      <section className="welcome-hero">
        <div className="welcome-copy">
          <span className="eyebrow"><span className="section-tick" /> A closer look at your delivery</span>
          <h1>Make every<br /><em>word land.</em></h1>
          <p>Compare your recording with a reference. Review your pace, pitch, pauses, and energy, one passage at a time.</p>
          <div className="button-row">
            <button className="button primary" onClick={onUpload}>Add your recording <ArrowUpRight size={17} /></button>
            <button className="button secondary" onClick={onLibrary}>Explore examples <ArrowRight size={16} /></button>
          </div>
          <div className="hero-note"><ShieldCheck size={15} /> Local processing. Temporary uploads.</div>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="visual-kicker"><AudioLines size={17} /> From recording to review <span>Illustration</span></div>
          <div className="visual-transcript">Not like the brazen giant<br />of Greek fame,<br /><span>With conquering limbs…</span></div>
          <div className="visual-wave">
            {Array.from({ length: 64 }, (_, i) => (
              <i key={i} style={{ height: `${9 + Math.abs(Math.sin(i * 0.7) * Math.cos(i * 0.23)) * 62}px` }} />
            ))}
            <div className="visual-passage" />
          </div>
          <div className="visual-caption"><span><i /> Your recording</span><span><i /> Gold reference</span><span>Word-aligned comparison</span></div>
          <div className="visual-finding"><span className="visual-play"><Play size={14} fill="currentColor" /></span><span>Listen to a passage.<br /><small>See the measurements behind it.</small></span><ArrowUpRight size={16} /></div>
        </div>
      </section>

      <section className="getting-started">
        <div className="section-heading">
          <div><span className="eyebrow">The reference library</span><h2>Try a reference recording.</h2></div>
          <button className="text-button" onClick={onLibrary}>All {listing?.entries.length ?? ''} texts <ArrowRight size={16} /></button>
        </div>
        {examples.length ? (
          <div className="example-grid">
            {examples.map(({ entry, demo }, i) => (
              <button className="example-card" key={demo.clip_id} onClick={() => onDemo(demo, entry)}>
                <div className="example-top"><span className="example-number">0{i + 1}</span><span>{formatTime(entry.duration_s)} reference</span></div>
                <h3>{entry.title}</h3>
                <p>{entry.category.replaceAll('_', ' ')}</p>
                <div className="example-bottom"><span><span className="tiny-dot amber" />{demo.flaw_kinds.map(kind => KIND_LABELS[kind]).join(', ')}</span><span className="example-arrow"><ArrowUpRight size={18} /></span></div>
              </button>
            ))}
          </div>
        ) : (
          <div className="empty-library" role="status">{libraryLoading ? 'Loading reference examples… You can still add your recording.' : 'Examples appear when the reference library is connected. You can still upload your own recording.'}</div>
        )}
      </section>

      <section className="workflow-section" aria-label="Review process">
        <div className="workflow-heading"><span className="eyebrow">A simple review process</span><h2>Record. Compare.<br /><em>Listen again.</em></h2></div>
        <div className="workflow-strip">
          <div><span>01</span><div><strong>Add your recording</strong><p>Upload audio and the words you spoke, or record a fresh take.</p></div></div>
          <div><span>02</span><div><strong>Review the comparison</strong><p>See your delivery alongside the reference, with timestamped findings.</p></div></div>
          <div><span>03</span><div><strong>Listen to each passage</strong><p>Move between your recording and the reference. Inspect the measured differences.</p></div></div>
        </div>
      </section>
    </>
  );
}
