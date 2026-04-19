import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const expectedImage = 'ghcr.io/tehkni/translatebookswithllms:latest';

test('default compose file uses a lowercase docker image reference', () => {
    const source = readFileSync('docker-compose.yml', 'utf8');

    assert.match(
        source,
        new RegExp(`image: \\$\\{TRANSLATEBOOK_IMAGE:-${expectedImage.replaceAll('/', '\\/')}\\}`),
        'docker-compose.yml must use a lowercase default image reference'
    );
});

test('remote ollama compose example uses a lowercase docker image reference', () => {
    const source = readFileSync('docker-compose.remote-ollama.example.yml', 'utf8');

    assert.match(
        source,
        new RegExp(`image: \\$\\{TRANSLATEBOOK_IMAGE:-${expectedImage.replaceAll('/', '\\/')}\\}`),
        'docker-compose.remote-ollama.example.yml must use a lowercase default image reference'
    );
});

test('root Dockerfile uses a lowercase default base image reference', () => {
    const source = readFileSync('Dockerfile', 'utf8');

    assert.match(
        source,
        new RegExp(`ARG BASE_IMAGE=${expectedImage.replaceAll('/', '\\/')}`),
        'Dockerfile must use a lowercase default base image reference'
    );
});
