import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import { parseGuide } from '../src/widgets/setup-guide/model/guide.ts';

const source = await readFile(new URL('../../docs/LOCAL_SETUP.md', import.meta.url), 'utf8');
const guide = parseGuide(source);
const tree = unified().use(remarkParse).parse(source);
let checked = 0;
for (const node of tree.children) {
  if (node.type === 'code' && (node.lang === 'bash' || node.lang === 'sh')) {
    execFileSync('bash', ['-n'], { input: node.value, stdio: ['pipe', 'pipe', 'pipe'] });
    checked++;
  }
}
console.log(`Setup guide: ${guide.sections.length} sections valid; ${checked} shell blocks passed syntax checks. No commands executed.`);
