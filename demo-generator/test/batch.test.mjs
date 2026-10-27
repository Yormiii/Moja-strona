import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, rm, mkdir, writeFile, symlink, stat, cp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { generateCompanies, industries, renderCompany } from '../generate.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const sample = JSON.parse(await readFile(join(root, 'examples/firma-testowa.json'), 'utf8'));
function company(slug, branza = 'mechanik') {
  const c = structuredClone(sample); c.slug = slug; c.nazwa = `Firma fikcyjna ${slug}`; c.branza = branza; delete c.kolory; return c;
}
async function temporary(t) {
  const path = await mkdtemp(join(tmpdir(), 'webforge-batch-'));
  t.after(() => rm(path, { recursive: true, force: true })); return path;
}
async function absent(path) { await assert.rejects(stat(path), { code: 'ENOENT' }); }

test('paczka ośmiu branż wybiera cztery warianty i kolory bez danych kolorystycznych', async t => {
  const outputRoot = await temporary(t);
  const data = Object.keys(industries).map(key => company(`test-${key}`, key));
  const result = await generateCompanies(data, { outputRoot });
  assert.equal(result.total, 8); assert.equal(result.pages.length, 8);
  assert.equal(new Set(Object.values(industries).map(p => p.szablon)).size, 4);
  for (const c of data) {
    const html = await readFile(join(outputRoot, c.slug, 'index.html'), 'utf8');
    const preset = industries[c.branza];
    assert.ok(html.includes(`class="layout-${preset.szablon}"`));
    assert.ok(html.includes(`--accent:${preset.akcent}`));
    assert.ok(html.includes(`--dark:${preset.tlo}`));
    assert.doesNotMatch(html, /\{\{\w+\}\}/);
  }
});

test('katalog łączy stare i nowe wyniki; dopisanie lub pominięcie firm niczego nie usuwa', async t => {
  const outputRoot = await temporary(t);
  await generateCompanies([company('pierwsza')], { outputRoot });
  const previous = await readFile(join(outputRoot, 'pierwsza/index.html'), 'utf8');
  await writeFile(join(outputRoot, 'notatka.txt'), 'zachowaj');
  await generateCompanies([company('druga', 'barber')], { outputRoot });
  const catalog = await readFile(join(outputRoot, 'index.html'), 'utf8');
  for (const slug of ['pierwsza', 'druga']) assert.ok(catalog.includes(`href="./${slug}/index.html"`));
  assert.equal(await readFile(join(outputRoot, 'pierwsza/index.html'), 'utf8'), previous);
  assert.equal(await readFile(join(outputRoot, 'notatka.txt'), 'utf8'), 'zachowaj');
  const again = await generateCompanies([company('druga', 'barber')], { outputRoot });
  assert.equal(again.pages[0].status, 'bez zmian'); assert.equal(again.total, 2);
  assert.equal(await readFile(join(outputRoot, 'index.html'), 'utf8'), catalog);
});

test('katalog obejmuje wcześniejsze demo v0.1 bez manifestu; pomija katalog bez index.html', async t => {
  const outputRoot = await temporary(t);
  await mkdir(join(outputRoot, 'stara-firma'));
  const old = '<!doctype html><title>Stare &amp; Test — Łódź | Demo WebForge</title><meta name="robots" content="noindex">';
  await writeFile(join(outputRoot, 'stara-firma/index.html'), old);
  await mkdir(join(outputRoot, 'pusty'));
  const result = await generateCompanies(company('nowa'), { outputRoot });
  assert.equal(result.total, 2);
  const catalog = await readFile(result.catalogPath, 'utf8');
  assert.match(catalog, /Stare &amp; Test — Łódź/);
  assert.doesNotMatch(catalog, /\.\/pusty\//);
  assert.equal(await readFile(join(outputRoot, 'stara-firma/index.html'), 'utf8'), old);
});

test('cała paczka jest walidowana przed zapisem pierwszej strony', async t => {
  const outputRoot = join(await temporary(t), 'output');
  for (const data of [[], Array(1001).fill(company('a')), [company('a'), { ...company('b'), branza: 'nieznana' }], [company('a'), company('a')], [company('a'), { ...company('b'), slug: '../escape' }]]) {
    await assert.rejects(generateCompanies(data, { outputRoot }));
    await absent(outputRoot);
  }
});

test('kolizja później w paczce nie zapisuje wcześniejszych firm ani katalogu', async t => {
  const outputRoot = await temporary(t);
  const old = company('stara'); await generateCompanies(old, { outputRoot });
  const before = await readFile(join(outputRoot, 'index.html'), 'utf8');
  await assert.rejects(generateCompanies([company('nowa'), { ...old, opis: 'Inny opis' }], { outputRoot }), /--force/);
  await absent(join(outputRoot, 'nowa'));
  assert.equal(await readFile(join(outputRoot, 'index.html'), 'utf8'), before);
  await absent(join(outputRoot, '.generator.lock'));
});

test('--force aktualizuje tylko firmy z paczki, zachowując pozostałe wyniki', async t => {
  const outputRoot = await temporary(t);
  await generateCompanies([company('a'), company('b')], { outputRoot });
  const oldB = await readFile(join(outputRoot, 'b/index.html'), 'utf8');
  const result = await generateCompanies({ ...company('a'), opis: 'Zaktualizowana oferta testowa' }, { outputRoot, overwrite: true });
  assert.equal(result.pages[0].status, 'odświeżono'); assert.equal(result.total, 2);
  assert.equal(await readFile(join(outputRoot, 'b/index.html'), 'utf8'), oldB);
  assert.match(await readFile(join(outputRoot, 'a/index.html'), 'utf8'), /Zaktualizowana oferta testowa/);
});

test('katalog i strony zachowują noindex, oznaczenia demo i kodowanie XSS', async t => {
  const outputRoot = await temporary(t); const c = company('xss');
  c.nazwa = '<img src=x onerror=alert(1)> & {{demonstracje}}';
  const result = await generateCompanies([c], { outputRoot });
  for (const path of [result.catalogPath, result.pages[0].path]) {
    const html = await readFile(path, 'utf8');
    assert.match(html, /name="robots" content="noindex, nofollow"/);
    assert.match(html, /demonstrac/i);
    assert.doesNotMatch(html, /<img\b|<script\b|<form\b/);
    assert.match(html, /&lt;img/);
  }
  const html = await readFile(result.catalogPath, 'utf8');
  assert.match(html, /\{\{demonstracje\}\}/); // No recursive template interpretation.
});

test('katalog koduje także tytuł starszej strony i ma bezpieczne względne odnośniki', async t => {
  const outputRoot = await temporary(t); await mkdir(join(outputRoot, 'legacy'));
  await writeFile(join(outputRoot, 'legacy/index.html'), '<title><script>alert(1)</script> &quot;X&quot;</title>');
  const r = await generateCompanies(company('nowa'), { outputRoot });
  const html = await readFile(r.catalogPath, 'utf8'); assert.doesNotMatch(html, /<script/);
  assert.match(html, /&lt;script&gt;/); assert.match(html, /&quot;X&quot;/);
  for (const [, href] of html.matchAll(/href="(\.\/[^"]+)"/g)) assert.ok(await stat(join(outputRoot, href)).then(s => s.isFile()));
});

test('symlink katalogu zbiorczego jest odrzucany zanim powstanie demo', async t => {
  const temp = await temporary(t); const outputRoot = join(temp, 'output'); await mkdir(outputRoot);
  const target = join(temp, 'nie-ruszaj'); await writeFile(target, 'bez zmian');
  await symlink(target, join(outputRoot, 'index.html'));
  await assert.rejects(generateCompanies(company('nowa'), { outputRoot, overwrite: true }), /Niebezpieczny/);
  assert.equal(await readFile(target, 'utf8'), 'bez zmian'); await absent(join(outputRoot, 'nowa'));
  await absent(join(outputRoot, '.generator.lock'));
});

test('symlink wcześniejszego demo i katalogu nadrzędnego nie jest śledzony', async t => {
  const temp = await temporary(t); const outputRoot = join(temp, 'output'); await mkdir(outputRoot);
  await symlink(temp, join(outputRoot, 'stara'));
  await assert.rejects(generateCompanies(company('nowa'), { outputRoot }), /symlink/);
  await absent(join(outputRoot, 'nowa'));
  await symlink(outputRoot, join(temp, 'alias'));
  await assert.rejects(generateCompanies(company('nowa'), { outputRoot: join(temp, 'alias/nested') }), /Niebezpieczny/);
});

test('blokada chroni przed drugim procesem i nie usuwa jego blokady', async t => {
  const outputRoot = await temporary(t); const lock = join(outputRoot, '.generator.lock');
  await writeFile(lock, 'zajęte');
  await assert.rejects(generateCompanies(company('nowa'), { outputRoot }), /Generator już działa/);
  assert.equal(await readFile(lock, 'utf8'), 'zajęte'); await absent(join(outputRoot, 'nowa'));
});

test('CLI przyjmuje listę i dodaje kolejną firmę bez modyfikacji kodu', async t => {
  const temp = await temporary(t); const cliRoot = join(temp, 'generator'); await mkdir(cliRoot);
  for (const name of ['generate.mjs', 'data', 'templates', 'package.json']) await cp(join(root, name), join(cliRoot, name), { recursive: true });
  const json = join(temp, 'firmy.json');
  const cli = () => spawnSync(process.execPath, [join(cliRoot, 'generate.mjs'), json], { cwd: temp, encoding: 'utf8' });
  await writeFile(json, JSON.stringify([company('a'), company('b', 'barber')]));
  assert.equal(cli().status, 0);
  await writeFile(json, JSON.stringify([company('c', 'restauracja')]));
  const r = cli(); assert.equal(r.status, 0, r.stderr);
  const html = await readFile(join(cliRoot, 'generated/index.html'), 'utf8');
  for (const slug of ['a', 'b', 'c']) assert.ok(html.includes(`./${slug}/index.html`));
});

test('dołączona lista fikcyjnych firm i katalog są odtwarzalne', async t => {
  const input = JSON.parse(await readFile(join(root, 'examples/lista-firm.json'), 'utf8'));
  const outputRoot = await temporary(t); await generateCompanies(input, { outputRoot });
  assert.equal(await readFile(join(root, 'generated/index.html'), 'utf8'), await readFile(join(outputRoot, 'index.html'), 'utf8'));
  for (const c of input) {
    assert.match(c.nazwa, /fikcyjna/); assert.match(c.kontakt.email, /\.invalid$/);
    assert.equal(await readFile(join(root, 'generated', c.slug, 'index.html'), 'utf8'), renderCompany(c).html);
  }
});
