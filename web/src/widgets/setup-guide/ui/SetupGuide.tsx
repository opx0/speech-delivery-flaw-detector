import { useEffect, useState, type ReactNode } from 'react';
import Markdown, { type Components, type ExtraProps } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft, ArrowUpRight, Check, Copy, Cpu, BookOpen } from 'lucide-react';
import source from '../../../../../docs/LOCAL_SETUP.md?raw';
import { documentationLink, GUIDE_REPOSITORY_URL, parseGuide, RUNTIMES, runtimeFromQuery, type Runtime } from '../model/guide';

const guide = parseGuide(source);

function fenceText(node: ExtraProps['node']): string {
  return node?.children.flatMap(child => child.type === 'element' && child.tagName === 'code'
    ? child.children.flatMap(part => part.type === 'text' ? [part.value] : [])
    : []).join('') ?? '';
}

function CopyCode({ children, text }: { children: ReactNode; text: string }) {
  const [status, setStatus] = useState<'idle' | 'copied' | 'failed'>('idle');
  useEffect(() => {
    if (status === 'idle') return;
    const timer = window.setTimeout(() => setStatus('idle'), 2500);
    return () => window.clearTimeout(timer);
  }, [status]);
  return (
    <div className="guide-code">
      <div className="guide-code-bar">
        <span>Terminal / code</span>
        <button className="guide-copy" onClick={async () => {
          try {
            await navigator.clipboard.writeText(text);
            setStatus('copied');
          } catch {
            setStatus('failed');
          }
        }} aria-label="Copy commands">
          {status === 'copied' ? <Check size={13} /> : <Copy size={13} />}
          {status === 'copied' ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre>{children}</pre>
      <span className="guide-copy-status" role="status">
        {status === 'failed' ? 'Copy unavailable. Select the code and copy it manually.' : status === 'copied' ? 'Commands copied.' : ''}
      </span>
    </div>
  );
}

const markdownComponents = {
  pre: ({ children, node }) => <CopyCode text={fenceText(node)}>{children}</CopyCode>,
  table: ({ children }) => <div className="guide-table"><table>{children}</table></div>,
  a: ({ children, href }) => {
    const target = documentationLink(href);
    const external = target?.startsWith('http');
    return <a href={target} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined}>{children}</a>;
  },
} satisfies Components;

export function SetupGuide({ onBack }: { onBack: () => void }) {
  const [runtime, setRuntime] = useState<Runtime>(() => runtimeFromQuery(new URLSearchParams(window.location.search).get('runtime')));
  const sections = guide.sections.filter(section => section.runtimes.includes(runtime));
  const steps = sections.filter(section => section.kind === 'step');
  const reference = sections.filter(section => section.kind === 'reference');
  const option = RUNTIMES.find(option => option.id === runtime);

  useEffect(() => {
    const target = document.getElementById(window.location.hash.slice(1));
    target?.scrollIntoView();
  }, [runtime]);

  return (
    <div className="setup-guide">
      <div className="guide-breadcrumb"><button onClick={onBack}><ArrowLeft size={14} /> Back to workspace</button><a href={GUIDE_REPOSITORY_URL} target="_blank" rel="noreferrer">Read in the repository <ArrowUpRight size={14} /></a></div>
      <div className="guide-heading">
        <span className="eyebrow"><BookOpen size={13} /> Documentation</span>
        <h1>{guide.title}</h1>
        <p>Choose where to run the app. Follow the commands from a Git clone to your first recording review.</p>
      </div>
      <fieldset className="guide-runtimes">
        <legend>Choose an execution path</legend>
        {RUNTIMES.map(item => (
          <label className={`guide-runtime${item.id === runtime ? ' selected' : ''}`} key={item.id}>
            <input type="radio" name="execution-path" aria-label={item.label} checked={runtime === item.id} onChange={() => setRuntime(item.id)} />
            <span><strong>{item.label}</strong><small>{item.description}</small></span>
            {item.recommended && <span className="guide-recommended">Recommended</span>}
          </label>
        ))}
      </fieldset>
      <div className="guide-path-note"><Cpu size={14} /><span>This selects instructions, not the runtime of the current server.</span><a href={`/docs?runtime=${runtime}`} target="_blank" rel="noreferrer">Link to this path <ArrowUpRight size={13} /></a></div>
      <details className="guide-mobile-contents"><summary>On this page</summary><nav aria-label="Guide section shortcuts">{sections.map(section => <a key={section.id} href={`#docs-${section.id}`}>{section.title}</a>)}</nav></details>
      <div className="guide-layout">
        <aside className="guide-sidebar">
          <span className="eyebrow">{option?.label} setup</span>
          <nav aria-label="Setup steps">
            {steps.map((section, index) => <a href={`#docs-${section.id}`} key={section.id}><span>{String(index + 1).padStart(2, '0')}</span>{section.title}</a>)}
          </nav>
          <span className="eyebrow">Reference</span>
          <nav aria-label="Setup reference">
            {reference.map(section => <a href={`#docs-${section.id}`} key={section.id}>{section.title}</a>)}
          </nav>
          <div className="guide-source-note">The app and repository use the same Markdown guide.</div>
        </aside>
        <article className="guide-article" aria-label={`${option?.label} instructions`}>
          {sections.map(section => (
            <section key={`${runtime}-${section.id}`} id={`docs-${section.id}`} className="guide-section">
              {section.kind === 'step' && <span className="guide-step">Step {steps.indexOf(section) + 1} of {steps.length}</span>}
              <Markdown remarkPlugins={[remarkGfm]} skipHtml components={markdownComponents}>{section.markdown}</Markdown>
            </section>
          ))}
        </article>
      </div>
    </div>
  );
}
