import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, rm, symlink, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { renderCompany, validateCompany, generateCompany, industries } from '../generate.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const sample = JSON.parse(await readFile(join(root, 'examples/firma-testowa.json'), 'utf8'));
const copy = () => structuredClone(sample);
async function temporary(t) {
  const path = await mkdtemp(join(tmpdir(), 'webforge-test-'));
  t.after(() => rm(path, { recursive: true, force: true }));
  return path;
}

test('osiem wariantów zachowuje branżę, CTA i kolory źródłowych demonstracji', async () => {
  assert.deepEqual(Object.keys(industries).sort(), ['barber', 'elektryk', 'hydraulik', 'kancelaria', 'mechanik', 'restauracja', 'stylistka', 'trener']);
  for (const [branza, preset] of Object.entries(industries)) {
    const original = await readFile(join(root, '..', preset.zrodlo), 'utf8');
    const input = { ...copy(), branza }; delete input.kolory;
    const { html } = renderCompany(input);
    assert.ok(original.includes(`--accent:${preset.akcent}`));
    assert.ok(original.includes(`--dark:${preset.tlo}`));
    assert.ok(original.includes(`>${preset.etykieta}</div>`));
    assert.ok(original.includes(`>${preset.cta}</a>`));
    assert.ok(html.includes(`--accent:${preset.akcent}`));
    assert.ok(html.includes(`--dark:${preset.tlo}`));
    assert.ok(html.includes(preset.etykieta));
    assert.ok(html.includes(`>${preset.cta}</a>`));
  }
});

test('personalizacja nazwy, miasta, usług, opisu i wszystkich danych kontaktowych', () => {
  const { html } = renderCompany(sample);
  for (const value of [sample.nazwa, sample.miasto, sample.opis, ...sample.uslugi.map(s => s.nazwa), sample.kontakt.adres]) assert.ok(html.includes(value));
  assert.match(html, /href="tel:\+48000000000"/);
  assert.match(html, /href="mailto:kontakt@serwis-orbita.example.invalid"/);
  assert.match(html, /href="https:\/\/serwis-orbita.example.invalid\/"/);
  assert.match(html, /--accent:#52d6b6/);
  assert.match(html, /--dark:#101c25/);
});

test('demo jest samodzielne, oznaczone i bez formularzy, skryptów i lokalnych zależności', () => {
  const { html } = renderCompany(sample);
  assert.match(html, /name="robots" content="noindex, nofollow"/);
  assert.match(html, /nie jest oficjalną stroną firmy/);
  assert.doesNotMatch(html, /<script\b|<form\b|\{\{\w+\}\}/i);
  const ids = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]));
  for (const [, href] of html.matchAll(/\bhref="([^"]+)"/g)) {
    if (href.startsWith('#')) assert.ok(ids.has(href.slice(1)), href);
    else assert.match(href, /^(?:https?:|tel:|mailto:)/);
  }
  assert.match(html, /href="https:\/\/webforge.com.pl\/#kontakt"/);
});

test('treści HTML, atrybuty i znaczniki szablonu nie są wykonywane', () => {
  const input = copy();
  input.nazwa = '<script>alert("x")</script> & {{kontakt}}';
  input.opis = '\"><img src=x onerror=alert(1)>';
  input.uslugi = [{ nazwa: '<svg onload=alert(1)>', opis: "' & <b>tekst</b>" }];
  input.kontakt.adres = '<iframe src=x>';
  input.kontakt.www = 'https://example.invalid/?a=1&b=2';
  const { html } = renderCompany(input);
  assert.doesNotMatch(html, /<script\b|<img\b|<svg\b|<iframe\b/i);
  assert.match(html, /&lt;script&gt;alert\(&quot;x&quot;\)/);
  assert.match(html, /&lt;b&gt;tekst&lt;\/b&gt;/);
  assert.match(html, /&amp;b=2/);
  assert.match(html, /\{\{kontakt\}\}/); // Literal user text, not a second template pass.
});

test('odrzucenie niepoprawnych danych i niebezpiecznych adresów', () => {
  const mutations = [
    c => { c.nazwa = ''; }, c => { c.miasto = 123; }, c => { c.opis = ' '; },
    c => { c.branza = '__proto__'; }, c => { c.uslugi = []; },
    c => { c.uslugi = Array(13).fill('Test'); }, c => { c.uslugi = [{ nazwa: '' }]; },
    c => { c.kolory.akcent = '#fff; background:url(x)'; },
    c => { c.kontakt.www = 'javascript:alert(1)'; },
    c => { c.kontakt.www = 'data:text/html,hello'; },
    c => { c.kontakt.www = 'https://user:pass@example.invalid'; },
    c => { c.kontakt.email = 'bad\r\nBcc:someone@example.invalid'; },
    c => { c.kontakt.telefon = '123-abc'; }, c => { c.kontakt.telefon = '-------'; },
    c => { c.kontakt = {}; }, c => { c.slug = '../../index.html'; },
    c => { c.slug = '/tmp/file'; }, c => { c.slug = 'a\\b'; },
    c => { c.slug = 'a'.repeat(101); }, c => { c.nazw = 'literówka'; }
  ];
  for (const mutate of mutations) { const c = copy(); mutate(c); assert.throws(() => validateCompany(c)); }
  for (const c of [null, [], 'firma']) assert.throws(() => validateCompany(c));
});

test('automatyczny slug obsługuje polskie znaki i rozróżnia podobne nazwy', () => {
  const c = copy(); delete c.slug; c.nazwa = 'Łódź Żółw';
  const a = validateCompany(c).slug;
  assert.match(a, /^lodz-zolw-lodz-[0-9a-f]{8}$/);
  assert.equal(a, validateCompany(c).slug);
  c.nazwa = 'Lodz Zolw';
  assert.notEqual(a, validateCompany(c).slug);
});

test('usługi tekstowe oraz pojedynczy kontakt są obsługiwane', () => {
  const input = copy(); input.uslugi = ['Usługa testowa']; input.kontakt = { email: 'demo@example.invalid' }; delete input.kolory;
  const { html } = renderCompany(input);
  assert.match(html, /Usługa testowa/);
  assert.doesNotMatch(html, /href="tel:|>Strona firmy</);
});

test('generowanie do pliku, ochrona przed nadpisaniem, jawne odświeżenie i deterministyczność', async t => {
  const outputRoot = await temporary(t);
  const a = await generateCompany(sample, { outputRoot });
  assert.equal(await readFile(a.path, 'utf8'), a.html);
  await assert.rejects(generateCompany(sample, { outputRoot }), /już istnieje/);
  const b = await generateCompany(sample, { outputRoot, overwrite: true });
  assert.equal(a.html, b.html);
  const input = copy(); input.opis = 'Nowa treść';
  await generateCompany(input, { outputRoot, overwrite: true });
  assert.match(await readFile(a.path, 'utf8'), /Nowa treść/);
});

test('niepoprawne dane nie tworzą katalogów i plików', async t => {
  const root = await temporary(t); const outputRoot = join(root, 'nie-istnieje');
  await assert.rejects(generateCompany({ ...sample, slug: '../escape' }, { outputRoot }));
  await assert.rejects(readFile(join(root, 'escape/index.html')), { code: 'ENOENT' });
  const { stat } = await import('node:fs/promises');
  await assert.rejects(stat(outputRoot), { code: 'ENOENT' });
});

test('nie podąża za symlinkiem katalogu ani pliku nawet z --force', async t => {
  const root = await temporary(t); const elsewhere = join(root, 'outside'); await mkdir(elsewhere);
  const outputRoot = join(root, 'output'); await mkdir(outputRoot);
  await symlink(elsewhere, join(outputRoot, sample.slug));
  await assert.rejects(generateCompany(sample, { outputRoot, overwrite: true }), /Niebezpieczny/);
  await rm(join(outputRoot, sample.slug)); await mkdir(join(outputRoot, sample.slug));
  const target = join(elsewhere, 'production.html'); await writeFile(target, 'bez zmian');
  await symlink(target, join(outputRoot, sample.slug, 'index.html'));
  await assert.rejects(generateCompany(sample, { outputRoot, overwrite: true }), /Niebezpieczny/);
  assert.equal(await readFile(target, 'utf8'), 'bez zmian');
});

test('CLI: pomoc, brak pliku, błędny JSON i nieobsługiwane flagi mają poprawne kody wyjścia', async t => {
  const temp = await temporary(t);
  const cli = (...args) => spawnSync(process.execPath, [join(root, 'generate.mjs'), ...args], { cwd: temp, encoding: 'utf8' });
  assert.equal(cli('--help').status, 0);
  assert.equal(cli().status, 1);
  assert.equal(cli('brak.json').status, 1);
  await writeFile(join(temp, 'bad.json'), '{broken');
  assert.equal(cli('bad.json').status, 1);
  assert.equal(cli('bad.json', '--output=/workspace/index.html').status, 1);
});

test('dołączony wynik przykładowy jest aktualny i odtwarzalny', async () => {
  assert.equal(await readFile(join(root, 'generated', sample.slug, 'index.html'), 'utf8'), renderCompany(sample).html);
});

test('CLI generuje nową firmę także z innego katalogu i odrzuca kolizję', async t => {
  const temp = await temporary(t);
  const input = copy(); input.slug = `test-cli-${process.pid}`;
  const destination = join(root, 'generated', input.slug);
  t.after(() => rm(destination, { recursive: true, force: true }));
  const json = join(temp, 'firma.json'); await writeFile(json, JSON.stringify(input));
  const cli = (...args) => spawnSync(process.execPath, [join(root, 'generate.mjs'), json, ...args], { cwd: temp, encoding: 'utf8' });
  const first = cli(); assert.equal(first.status, 0, first.stderr);
  assert.equal(await readFile(join(destination, 'index.html'), 'utf8'), renderCompany(input).html);
  assert.equal(cli().status, 1);
  assert.equal(cli('--force').status, 0);
});
