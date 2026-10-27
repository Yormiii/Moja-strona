import { readFile, mkdir, lstat, open, rename, unlink } from 'node:fs/promises';
import { resolve, dirname, join, relative, isAbsolute } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';

const ROOT = dirname(fileURLToPath(import.meta.url));
export const OUTPUT_ROOT = join(ROOT, 'generated');
export const industries = JSON.parse(await readFile(join(ROOT, 'data/industries.json'), 'utf8'));
const template = await readFile(join(ROOT, 'templates/demo.html'), 'utf8');

const fail = message => { throw new Error(message); };
const record = (value, field) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${field}: wymagany obiekt`);
  return value;
};
function text(value, field, max = 500) {
  if (typeof value !== 'string' || !value.trim() || value.length > max || /[\x00-\x08\x0b-\x1f\x7f]/.test(value)) {
    fail(`${field}: wymagany niepusty tekst, maks. ${max} znaków`);
  }
  return value.trim();
}
function knownKeys(value, keys, field) {
  for (const key of Object.keys(value)) if (!keys.includes(key)) fail(`${field}: nieznane pole ${key}`);
}
export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

export function validateCompany(input) {
  record(input, 'firma');
  knownKeys(input, ['nazwa', 'branza', 'miasto', 'uslugi', 'opis', 'kolory', 'kontakt', 'slug'], 'firma');
  const nazwa = text(input.nazwa, 'nazwa', 160);
  const branza = text(input.branza, 'branza', 40);
  if (!Object.hasOwn(industries, branza)) fail(`branza: wybierz ${Object.keys(industries).join(', ')}`);
  const miasto = text(input.miasto, 'miasto', 120);
  const opis = text(input.opis, 'opis', 2000);
  if (!Array.isArray(input.uslugi) || input.uslugi.length < 1 || input.uslugi.length > 12) {
    fail('uslugi: wymagana lista od 1 do 12 usług');
  }
  const uslugi = input.uslugi.map((service, i) => {
    if (typeof service === 'string') return { nazwa: text(service, `uslugi[${i}]`, 120), opis: '' };
    record(service, `uslugi[${i}]`);
    knownKeys(service, ['nazwa', 'opis'], `uslugi[${i}]`);
    return { nazwa: text(service.nazwa, `uslugi[${i}].nazwa`, 120), opis: service.opis === undefined ? '' : text(service.opis, `uslugi[${i}].opis`, 600) };
  });
  const preset = industries[branza];
  const colors = input.kolory === undefined ? {} : record(input.kolory, 'kolory');
  knownKeys(colors, ['akcent', 'tlo'], 'kolory');
  const kolory = { akcent: colors.akcent ?? preset.akcent, tlo: colors.tlo ?? preset.tlo };
  for (const [key, value] of Object.entries(kolory)) {
    if (typeof value !== 'string' || !/^#[\da-f]{6}$/i.test(value)) fail(`kolory.${key}: wymagany kolor #RRGGBB`);
  }
  const contact = record(input.kontakt, 'kontakt');
  knownKeys(contact, ['telefon', 'email', 'www', 'adres'], 'kontakt');
  const kontakt = {};
  for (const [key, value] of Object.entries(contact)) kontakt[key] = text(value, `kontakt.${key}`, 300);
  if (!kontakt.telefon && !kontakt.email && !kontakt.www) fail('kontakt: podaj telefon, email lub www');
  if (kontakt.telefon && !/^\+?[\d ()-]{7,30}$/.test(kontakt.telefon)) fail('kontakt.telefon: nieprawidłowy numer');
  if (kontakt.telefon && !/^\+?\d{7,15}$/.test(kontakt.telefon.replace(/[ ()-]/g, ''))) fail('kontakt.telefon: wymagane 7–15 cyfr');
  if (kontakt.email && !/^[a-z\d.!#$%&'*+/=?^_`{|}~-]+@[a-z\d](?:[a-z\d.-]*[a-z\d])?\.[a-z]{2,}$/i.test(kontakt.email)) fail('kontakt.email: nieprawidłowy adres');
  if (kontakt.www) {
    let url;
    try { url = new URL(kontakt.www); } catch { fail('kontakt.www: nieprawidłowy URL'); }
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) fail('kontakt.www: dozwolony HTTP/HTTPS bez danych logowania');
    kontakt.www = url.href;
  }
  const id = createHash('sha256').update(`${nazwa}\0${miasto}`).digest('hex').slice(0, 8);
  const base = `${nazwa}-${miasto}`.toLowerCase().replace(/ł/g, 'l').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60).replace(/-$/, '') || 'firma';
  const slug = input.slug ?? `${base}-${id}`;
  if (typeof slug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 100) fail('slug: 1–100 znaków a-z, 0-9 i pojedyncze łączniki');
  return { nazwa, branza, miasto, opis, uslugi, kolory, kontakt, slug };
}

export function renderCompany(input) {
  const company = validateCompany(input);
  const preset = industries[company.branza];
  const esc = escapeHtml;
  const services = company.uslugi.map((service, i) => `<article class="card"><span class="num">${String(i + 1).padStart(2, '0')}</span><h3>${esc(service.nazwa)}</h3>${service.opis ? `<p>${esc(service.opis)}</p>` : ''}</article>`).join('\n');
  const contact = company.kontakt;
  const links = [];
  if (contact.telefon) links.push(`<a class="btn" href="tel:${esc(contact.telefon.replace(/[ ()-]/g, ''))}">${esc(contact.telefon)}</a>`);
  if (contact.email) links.push(`<a class="btn ghost" href="mailto:${esc(contact.email)}">${esc(contact.email)}</a>`);
  if (contact.www) links.push(`<a class="btn ghost" href="${esc(contact.www)}" rel="noopener noreferrer">Strona firmy</a>`);
  if (contact.adres) links.push(`<p>${esc(contact.adres)}</p>`);
  const values = {
    nazwa: esc(company.nazwa), miasto: esc(company.miasto), opis: esc(company.opis),
    opisMeta: esc(company.opis.replace(/\s+/g, ' ').slice(0, 160)),
    branza: esc(preset.etykieta), naglowek: esc(`${company.nazwa} — ${company.miasto}`),
    cta: esc(preset.cta), akcent: company.kolory.akcent, tlo: company.kolory.tlo,
    uslugi: services, kontakt: links.join('\n')
  };
  // One pass: user text resembling {{tokens}} is never evaluated again.
  const html = template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (!Object.hasOwn(values, key)) fail(`Nieznany znacznik szablonu: ${key}`);
    return values[key];
  });
  return { company, html };
}

async function safeDirectory(directory) {
  // Reject symlinks in the entire output path, including ancestors.
  const parent = dirname(directory);
  if (parent !== directory) await safeDirectory(parent);
  try {
    const info = await lstat(directory);
    if (info.isSymbolicLink() || !info.isDirectory()) fail(`Niebezpieczny katalog wyjściowy: ${directory}`);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    await mkdir(directory);
  }
}

export async function generateCompany(input, { outputRoot = OUTPUT_ROOT, overwrite = false } = {}) {
  const result = renderCompany(input); // Validate before creating files.
  const root = resolve(outputRoot);
  const folder = resolve(root, result.company.slug);
  const rel = relative(root, folder);
  if (!rel || rel.startsWith('..') || isAbsolute(rel)) fail('Niedozwolona ścieżka wyjściowa');
  await safeDirectory(folder);
  const destination = join(folder, 'index.html');
  try {
    const info = await lstat(destination);
    if (info.isSymbolicLink() || !info.isFile()) fail('Niebezpieczny plik docelowy');
    if (!overwrite) fail('Demo już istnieje. Użyj --force, aby je odświeżyć.');
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (!overwrite) {
    const handle = await open(destination, 'wx');
    try { await handle.writeFile(result.html, 'utf8'); } finally { await handle.close(); }
  } else {
    const temp = join(folder, `.index-${randomUUID()}.tmp`);
    try {
      await (async () => { const handle = await open(temp, 'wx'); try { await handle.writeFile(result.html, 'utf8'); } finally { await handle.close(); } })();
      await rename(temp, destination);
    } finally { await unlink(temp).catch(error => { if (error.code !== 'ENOENT') throw error; }); }
  }
  return { ...result, path: destination };
}

async function main(args) {
  if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
    console.log('Użycie: node demo-generator/generate.mjs <firma.json> [--force]\nWyjście: demo-generator/generated/<slug>/index.html');
    return;
  }
  if (args.length < 1 || args.length > 2 || args[0].startsWith('-') || (args.length === 2 && args[1] !== '--force')) {
    fail('Użycie: node demo-generator/generate.mjs <firma.json> [--force]');
  }
  const input = JSON.parse(await readFile(resolve(args[0]), 'utf8'));
  const result = await generateCompany(input, { overwrite: args[1] === '--force' });
  console.log(`Wygenerowano lokalnie: ${result.path}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).catch(error => {
    console.error(`Błąd generatora: ${error.message}`);
    process.exitCode = 1;
  });
}
