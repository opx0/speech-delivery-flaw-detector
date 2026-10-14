import { unified } from 'unified';
import remarkParse from 'remark-parse';
import { toString } from 'mdast-util-to-string';

export const RUNTIMES = [
  { id: 'docker', label: 'Docker CPU', description: 'Managed setup on Linux, Windows, or macOS.', recommended: true },
  { id: 'cpu', label: 'Native CPU', description: 'Run directly on Debian or Ubuntu Linux.', recommended: false },
  { id: 'cuda', label: 'Native GPU', description: 'Linux with an NVIDIA GPU and CUDA-enabled PyTorch.', recommended: false },
] satisfies readonly { id: 'docker' | 'cpu' | 'cuda'; label: string; description: string; recommended: boolean }[];

export type Runtime = (typeof RUNTIMES)[number]['id'];

export interface GuideSection {
  id: string;
  title: string;
  kind: 'step' | 'reference';
  runtimes: readonly [Runtime, ...Runtime[]];
  markdown: string;
}

export interface Guide {
  title: string;
  sections: GuideSection[];
}

export const GUIDE_REPOSITORY_URL = 'https://github.com/opx0/speech-delivery-flaw-detector/blob/main/docs/LOCAL_SETUP.md';

export function parseGuide(source: string): Guide {
  const tree = unified().use(remarkParse).parse(source);
  const title = tree.children.find(node => node.type === 'heading' && node.depth === 1);
  if (!title) throw new Error('The setup guide needs a document title.');
  const headings = tree.children.flatMap((node, index) => {
    if (node.type !== 'heading' || node.depth !== 2) return [];
    const annotation = tree.children[index + 1];
    const metadata = annotation?.type === 'html'
      ? /^<!-- setup: ([a-z ]+); (step|reference) -->$/.exec(annotation.value.trim())
      : null;
    if (!metadata) throw new Error(`Missing setup metadata for "${toString(node)}".`);
    const scope = metadata[1];
    const kind = metadata[2];
    if (!scope || (kind !== 'step' && kind !== 'reference')) throw new Error('Invalid setup metadata.');
    const runtimes = scope === 'all'
      ? RUNTIMES.map(option => option.id)
      : scope.split(' ').map(value => {
          const option = RUNTIMES.find(option => option.id === value);
          if (!option) throw new Error(`Unknown setup runtime "${value}".`);
          return option.id;
        });
    const [first, ...rest] = runtimes;
    if (!first) throw new Error('A setup section needs an execution path.');
    const start = node.position?.start.offset;
    if (start === undefined) throw new Error('The setup guide is missing source positions.');
    const label = toString(node);
    return [{ title: label, id: label.toLowerCase().replace(/[^a-z0-9 -]/g, '').replace(/\s+/g, '-'),
      kind, runtimes: [first, ...rest], start } satisfies Omit<GuideSection, 'markdown'> & { start: number }];
  });
  const identifiers = new Set<string>();
  const sections = headings.map((heading, index): GuideSection => {
    if (!heading.id || identifiers.has(heading.id)) throw new Error(`Duplicate setup heading "${heading.title}".`);
    identifiers.add(heading.id);
    return {
      id: heading.id,
      title: heading.title,
      kind: heading.kind,
      runtimes: heading.runtimes,
      markdown: source.slice(heading.start, headings[index + 1]?.start ?? source.length),
    };
  });
  if (!sections.length) throw new Error('The setup guide needs sections.');
  return { title: toString(title), sections };
}

export function runtimeFromQuery(value: string | null): Runtime {
  return RUNTIMES.find(option => option.id === value)?.id ?? 'docker';
}

export function documentationLink(href: string | undefined): string | undefined {
  if (!href) return undefined;
  if (href.startsWith('#')) return `#docs-${href.slice(1)}`;
  const url = new URL(href, GUIDE_REPOSITORY_URL);
  return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : undefined;
}
