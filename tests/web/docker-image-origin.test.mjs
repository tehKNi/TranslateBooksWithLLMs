import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('default compose file does not point at the upstream hydropix image', () => {
    const source = readFileSync('docker-compose.yml', 'utf8');

    assert.doesNotMatch(
        source,
        /ghcr\.io\/hydropix\/translatebookswithllms:latest/i,
        'fork deployment must not default to the upstream hydropix image'
    );
});

test('remote ollama compose example does not point at the upstream hydropix image', () => {
    const source = readFileSync('docker-compose.remote-ollama.example.yml', 'utf8');

    assert.doesNotMatch(
        source,
        /ghcr\.io\/hydropix\/translatebookswithllms:latest/i,
        'fork remote-ollama example must not default to the upstream hydropix image'
    );
});

test('root Dockerfile does not inherit from the upstream hydropix image by default', () => {
    const source = readFileSync('Dockerfile', 'utf8');

    assert.doesNotMatch(
        source,
        /^FROM ghcr\.io\/hydropix\/translatebookswithllms:latest$/im,
        'fork Dockerfile must not inherit from the upstream hydropix image by default'
    );
});
