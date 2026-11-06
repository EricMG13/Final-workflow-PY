const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const files = ['screen.css', 'report-adapter.css', 'context-embed.css'];
const read = (f) => fs.readFileSync(path.join(__dirname, f), 'utf8');
const screen = read('screen.css');

function luminance(hex) {
  const v = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt(v.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a, b) {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

test('primary hover excludes disabled and keeps white text', () => {
  const m = screen.match(/(\.primary-action:hover[^{]*)\{([^}]*)\}/);
  assert.ok(m, 'no .primary-action:hover rule');
  assert.equal(m[1], '.primary-action:hover:not(:disabled)');
  assert.ok(m[2].includes('color:#fff'), `hover block lacks color:#fff: ${m[2]}`);
});

test('no text below 11px and no em/rem below 1', () => {
  const offenders = [];
  for (const f of files) {
    for (const m of read(f).matchAll(/font(?:-size)?:\s*(?:\d{3}\s+)?([\d.]+)(px|em|rem)/g)) {
      const v = parseFloat(m[1]);
      if ((m[2] === 'px' && v < 11) || (m[2] !== 'px' && v < 1)) offenders.push(`${f}: ${m[0]}`);
    }
  }
  assert.deepEqual(offenders, [], `undersized text: ${offenders.join('; ')}`);
});

test('type ramp tokens are declared and used', () => {
  for (const d of ['--fs-label:11px', '--fs-compact:12px', '--fs-body:13px', '--fs-control:14px']) {
    assert.ok(/:root\{[^}]*/.test(screen) && screen.split('}')[screen.split('}').findIndex((s) => s.includes(':root{'))].includes(d), `:root lacks ${d}`);
  }
  assert.doesNotMatch(screen, /font-size:1[1-4]px/);
  assert.doesNotMatch(screen, /font:(?:\d{3}\s+)?1[1-4]px/);
});

test('--text-quaternary contrast on white', () => {
  const m = screen.match(/--text-quaternary:(#[0-9a-fA-F]{6})/);
  assert.ok(m, 'token missing');
  const ratio = contrast(m[1], '#ffffff');
  assert.ok(ratio >= 5.5, `contrast ${ratio.toFixed(2)} < 5.5`);
  assert.equal(ratio.toFixed(2), '6.06');
});

test('report-adapter.css declares every --fs token it uses (injected without screen.css)', () => {
  const adapter = read('report-adapter.css');
  const brand = read('brand.css');
  const used = [...new Set(adapter.match(/var\(--fs-[a-z]+\)/g) || [])].map((v) => v.slice(4, -1));
  const block = (adapter.match(/\.library-report\s*\{[^}]*\}/) || [''])[0];
  const missing = used.filter((t) => !block.includes(`${t}:`) && !brand.includes(`${t}:`));
  assert.deepEqual(missing, [], `undeclared in the report document: ${missing.join(', ')}`);
});

const rule = (selector) => [...screen.matchAll(/([^{}]+)\{([^}]*)\}/g)].filter((m) => m[1].trim().split(',').map((x) => x.trim()).includes(selector)).map((m) => m[2]);

test('tools-workspace: the opened navigator takes a 238px column beside the content', () => {
  const found = [...screen.matchAll(/([^{}]*\.tools-workspace[^{}]*:has\(\.navigator\.mobile-open\)[^{}]*)\{([^}]*)\}/g)];
  assert.ok(found.some((m) => /grid-template-columns:\s*238px minmax\(0,\s*1fr\)\s*(;|$)/.test(m[2])), 'no two-column 238px rule');
});

test('tools-workspace: the Modules toggle spans every column', () => {
  assert.ok(rule('.tools-workspace .mobile-modules').some((b) => /grid-column:\s*1\/-1/.test(b)), 'toggle does not span');
});

test('border radii use only the DESIGN.md scale', () => {
  const allowed = new Set(['0', '1px', '50%', '999px', 'var(--radius-inline)', 'var(--radius-control)', 'var(--radius-card)']);
  const values = [...screen.matchAll(/border-radius:([^;}]*)/g)].flatMap((m) => m[1].trim().split(/\s+/));
  const bad = [...new Set(values.filter((v) => !allowed.has(v)))];
  assert.deepEqual(bad, []);
  assert.match(screen, /:root\{[^}]*--radius-inline:4px/);
});

test('forced colours keep pills, buttons and the active rail item visible; the case link does not wrap', () => {
  const block = /@media\(forced-colors:active\)\{(.*)\}\s*$/m.exec(screen);
  assert.ok(block, 'no forced-colors block');
  assert.ok(block[1].includes('.rail a[aria-current]') && block[1].includes('.badge'));
  assert.ok(rule('.issuer-meta a').some((b) => b.includes('white-space:nowrap')));
});
