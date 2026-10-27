import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { safeUrl, validateExport, decision } from '../panel.mjs';
import { renderCompany } from '../../demo-generator/generate.mjs';

const record = {id:1,name:'<script>TEST</script>',city:'Łódź',industry:'mechanik',voivodeship:'lodzkie',fictional:true,status:'znaleziony',assessment:{score:0,reasons:[]}};
test('panel przyjmuje eksport i nie traktuje nazw jako HTML', () => {
  const d = validateExport({version:1,records:[record]}); assert.equal(d.records[0].name,record.name);
  assert.throws(()=>validateExport({version:1,records:[record,record]}));
  assert.throws(()=>validateExport({version:1,records:[{...record,fictional:'true'}]}));
  assert.throws(()=>validateExport({version:1,records:[{...record,assessment:{score:101,reasons:[]}}]}));
});
test('panel odrzuca niebezpieczne linki', () => {
  for (const bad of ['javascript:alert(1)','data:text/html,x','https://user:password@example.invalid/']) assert.equal(safeUrl(bad),null);
  assert.equal(safeUrl('https://example.invalid/'),'https://example.invalid/');
});
test('decyzje mają oczekiwany status i kontakt wymaga dowodu', () => {
  const d = decision(record,'do_weryfikacji','Sprawdź'); assert.equal(d.expected_status,'znaleziony');
  assert.throws(()=>decision(record,'do_weryfikacji',''));
  assert.throws(()=>decision(record,'kontakt_dozwolony','Publiczny kontakt'));
  assert.throws(()=>decision(record,'znaleziony','Nie zmieniono'));
});
test('panel nie ma kodu wysyłki, innerHTML ani połączeń sieciowych', async () => {
  const js = await readFile(new URL('../panel.mjs',import.meta.url),'utf8');
  const html = await readFile(new URL('../panel.html',import.meta.url),'utf8');
  assert.doesNotMatch(js,/innerHTML|\bfetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon/);
  assert.match(html,/connect-src 'none'/); assert.match(html,/noindex, nofollow/);
});
test('minimalny adapter pozwala opisać branżę poza ośmioma bazowymi bez zmiany starych danych', async () => {
  const c = JSON.parse(await readFile(new URL('../../demo-generator/examples/firma-testowa.json',import.meta.url),'utf8'));
  const {html} = renderCompany({...c,etykieta_branzy:'Agroturystyka <TEST>',cta:'Zapytaj & zobacz'});
  assert.match(html,/Agroturystyka &lt;TEST&gt;/); assert.match(html,/Zapytaj &amp; zobacz/);
  assert.throws(()=>renderCompany({...c,cta:''}));
  assert.throws(()=>renderCompany({...c,etykieta_branzy:'x'.repeat(121)}));
});
