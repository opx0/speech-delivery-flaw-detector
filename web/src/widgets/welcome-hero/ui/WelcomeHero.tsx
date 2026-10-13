import {
  Activity,
  ArrowRight,
  AudioLines,
  BookOpen,
  ChevronRight,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import type { DemoClip, LibraryEntry, LibraryListing } from '../../../contract';
import { formatTime } from '../../../shared/lib';

export interface WelcomeHeroProps {
  listing: LibraryListing | null;
  onUpload: () => void;
  onLibrary: () => void;
  onDemo: (demo: DemoClip, entry: LibraryEntry) => void;
}

export function WelcomeHero({ listing, onUpload, onLibrary, onDemo }: WelcomeHeroProps) {
  const examples =
    listing?.entries.slice(0, 3).flatMap((entry) => {
      const demo = listing.demos.find(
        (d) => d.text_id === entry.text_id && d.flaw_kinds.includes('rush'),
      );
      return demo ? [{ entry, demo }] : [];
    }) ?? [];

  return (
    <>
      <section className="welcome-hero">
        <div className="welcome-copy">
          <span className="eyebrow">
            <span className="status-dot" /> Hear the difference
          </span>
          <h2>
            Make every
            <br />
            <em>word land.</em>
          </h2>
          <p>
            See where your pace, pitch, pauses, and energy change. Listen to the moment. Understand what to work on.
          </p>
          <div className="button-row">
            <button className="button primary" onClick={onUpload}>
              <Upload size={17} /> Add your recording
            </button>
            <button className="button secondary" onClick={onLibrary}>
              Explore examples <ArrowRight size={16} />
            </button>
          </div>
          <div className="hero-note">
            <ShieldCheck size={15} /> Local analysis. Temporary uploads. Your own voice.
          </div>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="visual-kicker">
            <AudioLines size={17} /> A closer listen <span>01 / 03</span>
          </div>
          <div className="visual-transcript">
            A great speech isn't just
            <br />
            what you say.
            <br />
            <span>It's how you say it.</span>
          </div>
          <div className="visual-wave">
            {Array.from({ length: 48 }, (_, i) => (
              <i
                key={i}
                style={{
                  height: `${12 + Math.abs(Math.sin(i * 0.7) * Math.cos(i * 0.23)) * 65}px`,
                }}
              />
            ))}
          </div>
          <div className="visual-caption">
            <span>
              <i /> Your delivery
            </span>
            <span>
              <i /> Reference
            </span>
          </div>
          <div className="visual-finding">
            <Activity size={17} />
            <div>
              From sound to insight
              <small>Listen · Locate · Understand</small>
            </div>
            <ChevronRight size={17} />
          </div>
        </div>
      </section>

      <section className="getting-started">
        <div className="section-heading">
          <div>
            <span className="eyebrow">No recording? Start here</span>
            <h2>Try a reference example</h2>
          </div>
          <button className="text-button" onClick={onLibrary}>
            View library <ArrowRight size={15} />
          </button>
        </div>
        {examples.length ? (
          <div className="example-grid">
            {examples.map(({ entry, demo }, i) => (
              <button
                className="example-card"
                key={demo.clip_id}
                onClick={() => onDemo(demo, entry)}
              >
                <div className="example-top">
                  <span className={`example-icon example-icon-${i}`}>
                    <BookOpen size={20} />
                  </span>
                  <span className="pill muted">{formatTime(entry.duration_s)}</span>
                </div>
                <h3>{entry.title}</h3>
                <p>{entry.category.replaceAll('_', ' ')}</p>
                <div className="example-bottom">
                  <span>
                    <span className="tiny-dot amber" /> Rushed reading
                  </span>
                  <ArrowRight size={18} />
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="empty-library">
            Examples appear when the reference library is connected. You can still upload your own recording.
          </div>
        )}
      </section>

      <div className="workflow-strip">
        <div>
          <span>01</span>
          <strong>Bring your voice</strong>
          <small>Audio + the words you spoke</small>
        </div>
        <div>
          <span>02</span>
          <strong>Find the moments</strong>
          <small>Delivery grounded in timestamps</small>
        </div>
        <div>
          <span>03</span>
          <strong>Hear what changes</strong>
          <small>Measured evidence, clear feedback</small>
        </div>
      </div>
    </>
  );
}
