import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const indexPath = path.resolve(__dirname, '../../src/web/static/js/index.js');

test('index.js imports successfully as an ES module with a minimal browser stub', () => {
    const bootstrapScript = `
globalThis.window = { location: { origin: 'http://example.test' }, addEventListener() {} };
globalThis.document = {
  readyState: 'loading',
  addEventListener() {},
  getElementById() { return null; },
  querySelector() { return null; },
  querySelectorAll() { return []; }
};
globalThis.localStorage = {
  getItem() { return null; },
  setItem() {},
  removeItem() {}
};
globalThis.requestAnimationFrame = (cb) => cb();
globalThis.fetch = async () => ({ ok: true, json: async () => ({}) });
await import(${JSON.stringify(new URL(indexPath, 'file://').href)});
`;

    const result = spawnSync(process.execPath, ['--input-type=module', '--eval', bootstrapScript], {
        encoding: 'utf8'
    });

    assert.equal(result.status, 0, result.stderr || 'node --check failed');
    assert.equal(result.stderr, '');
});
