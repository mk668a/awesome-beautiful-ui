#!/usr/bin/env node
// Regenerates the list in README.md from list.json and live GitHub data.
// Usage: GITHUB_TOKEN=$(gh auth token) node scripts/build.mjs

import { readFile, writeFile } from 'node:fs/promises';

const ROOT = new URL('..', import.meta.url);
const START = '<!-- LIST:START -->';
const END = '<!-- LIST:END -->';
const QUIET_AFTER_MONTHS = 3;

const SECTIONS = [
  ['gems', 'Hidden gems', 'Lesser known, each with one effect or idea that is clearly its own.'],
  ['motion', 'Motion and text animation', null],
  ['components', 'Components and design systems', null],
  ['webgl', 'WebGL and creative coding', null],
  ['terminal', 'Terminal and TUI', null],
  ['widgets', 'Widgets and building blocks', null],
];

const PERMISSIVE = new Set([
  'MIT', 'ISC', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', '0BSD', 'Unlicense', 'CC0-1.0',
]);

const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
if (!token) {
  console.error('Set GITHUB_TOKEN (for example: GITHUB_TOKEN=$(gh auth token)).');
  process.exit(1);
}

async function fetchRepo(repo) {
  const res = await fetch(`https://api.github.com/repos/${repo}`, {
    headers: {
      authorization: `Bearer ${token}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'awesome-beautiful-ui',
    },
  });
  if (!res.ok) throw new Error(`${repo}: HTTP ${res.status}`);
  return res.json();
}

async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const i = next++;
      out[i] = await fn(items[i]);
    }
  };
  await Promise.all(Array.from({ length: limit }, worker));
  return out;
}

function stars(n) {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(n < 10000 ? 1 : 0)}k`;
}

function license(entry, data) {
  const id = entry.license ?? data.license?.spdx_id;
  if (!id || id === 'NOASSERTION') return 'license: see repo ⚠';
  return PERMISSIVE.has(id) ? id : `${id} ⚠`;
}

function line(e) {
  return `- [${e.name}](https://github.com/${e.fullName}) - ${e.note} \`★ ${stars(e.stars)}\` \`${e.license}\` \`${e.pushed.slice(0, 7)}\``;
}

const byStars = (a, b) => b.stars - a.stars;

const list = JSON.parse(await readFile(new URL('list.json', ROOT), 'utf8'));
const known = new Set(SECTIONS.map(([id]) => id));
for (const e of list) {
  if (!known.has(e.section)) throw new Error(`${e.repo}: unknown section "${e.section}"`);
}

const cutoff = new Date();
cutoff.setMonth(cutoff.getMonth() - QUIET_AFTER_MONTHS);

const entries = await mapLimit(list, 8, async (entry) => {
  const data = await fetchRepo(entry.repo);
  if (data.full_name.toLowerCase() !== entry.repo.toLowerCase()) {
    console.warn(`moved: ${entry.repo} -> ${data.full_name} (update list.json)`);
  }
  return {
    ...entry,
    fullName: data.full_name,
    stars: data.stargazers_count,
    pushed: data.pushed_at,
    license: license(entry, data),
    quiet: data.archived || new Date(data.pushed_at) < cutoff,
  };
});

const today = new Date().toISOString().slice(0, 10);
const active = entries.filter((e) => !e.quiet);
const quiet = entries.filter((e) => e.quiet);

const out = [`_Last refreshed ${today}. ${active.length} active, ${quiet.length} quiet._`, ''];
for (const [id, title, intro] of SECTIONS) {
  const rows = active.filter((e) => e.section === id).sort(byStars);
  if (!rows.length) continue;
  out.push(`## ${title}`, '');
  if (intro) out.push(intro, '');
  out.push(...rows.map(line), '');
}
out.push(
  '## Quiet classics',
  '',
  `No push in the last ${QUIET_AFTER_MONTHS} months, or archived. Many of these are simply finished. They move back up on their own when development resumes.`,
  '',
  ...quiet.sort(byStars).map(line),
  '',
);

const readmeUrl = new URL('README.md', ROOT);
const readme = await readFile(readmeUrl, 'utf8');
const a = readme.indexOf(START);
const b = readme.indexOf(END);
if (a < 0 || b < a) throw new Error('README.md is missing the LIST markers');
await writeFile(readmeUrl, `${readme.slice(0, a + START.length)}\n${out.join('\n')}${readme.slice(b)}`);
console.log(`README.md updated: ${active.length} active, ${quiet.length} quiet`);
