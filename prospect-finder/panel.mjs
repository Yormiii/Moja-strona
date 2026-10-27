export const statuses = ['znaleziony', 'do_weryfikacji', 'zaakceptowany', 'demo_gotowe', 'kontakt_dozwolony', 'kontaktowany', 'zainteresowany', 'odrzucony', 'klient'];
export function safeUrl(value) {
  try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) && !u.username && !u.password ? u.href : null; } catch { return null; }
}
export function validateExport(data) {
  if (data?.version !== 1 || !Array.isArray(data.records) || data.records.length > 10000) throw Error('Nieprawidłowy eksport v1 (maks. 10000 rekordów).');
  const seen = new Set();
  for (const r of data.records) {
    if (!Number.isInteger(r.id) || r.id < 1 || seen.has(r.id) || typeof r.name !== 'string' || typeof r.city !== 'string' || typeof r.industry !== 'string' || typeof r.voivodeship !== 'string' || typeof r.fictional !== 'boolean' || !statuses.includes(r.status) || !Number.isInteger(r.assessment?.score) || r.assessment.score < 0 || r.assessment.score > 100 || !Array.isArray(r.assessment.reasons)) throw Error('Nieprawidłowy rekord eksportu.');
    seen.add(r.id);
  }
  return data;
}
export function decision(record, status, reason, permission) {
  if (!statuses.includes(status) || status === record.status || !reason.trim()) throw Error('Wybierz nowy status i podaj uzasadnienie.');
  const d = { id: record.id, expected_status: record.status, status, reason: reason.trim() };
  if (status === 'kontakt_dozwolony') {
    if (!permission?.note?.trim() || !safeUrl(permission.source_url) || !/^\d{4}-\d{2}-\d{2}$/.test(permission.verified_at || '')) throw Error('Kontakt wymaga uzasadnienia, źródła i daty potwierdzenia.');
    d.permission = permission;
  }
  return d;
}

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  let data = { records: [], workflow: {} }; const pending = new Map();
  const el = (tag, text) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; };
  function link(parent, label, href) {
    const safe = safeUrl(href);
    if (!safe) return;
    const a = el('a', label); a.href = safe; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.referrerPolicy = 'no-referrer'; parent.append(a, el('br'));
  }
  function options(id, values) {
    const select = $(id); while (select.options.length > 1) select.remove(1);
    for (const value of [...new Set(values)].sort()) { const o = el('option', value.replaceAll('_', ' ')); o.value = value; select.append(o); }
  }
  function render() {
    $('records').replaceChildren();
    const query = $('query').value.toLocaleLowerCase('pl');
    const records = data.records.filter(r => (!query || `${r.name} ${r.city}`.toLocaleLowerCase('pl').includes(query)) && (!$('industry').value || r.industry === $('industry').value) && (!$('province').value || r.voivodeship === $('province').value) && (!$('status').value || r.status === $('status').value) && (!$('category').value || r.assessment.reasons.some(x => ['outdated', 'mobile_issues', 'unclear_offer', 'technical_issues'].includes(x.criterion) && x.points > 0))).sort((a,b) => b.assessment.score-a.assessment.score);
    $('message').textContent = `${records.length} z ${data.records.length} rekordów. Decyzje do pobrania: ${pending.size}.`;
    for (const r of records) {
      const card = el('article'); card.append(el('h2', r.name));
      for (const label of [r.fictional ? 'FIKCYJNE DANE TESTOWE' : 'Dane publiczne — do weryfikacji', r.status.replaceAll('_',' '), `Punkty: ${r.assessment.score}/100`, `Pokrycie danych: ${r.assessment.coverage_percent}%`]) { const b = el('span', label); b.className = 'badge'; card.append(b); }
      card.append(el('p', `${r.industry} · ${r.city} · ${r.voivodeship} · weryfikacja: ${r.last_verified_at}`));
      const details = el('details'); details.append(el('summary', 'Uzasadnienie, kontakty i źródła'));
      for (const reason of r.assessment.reasons) {
        details.append(el('p', `${reason.criterion}: +${reason.points} — ${reason.reason}`));
        for (const ev of reason.evidence || []) link(details, `${ev.note || ev.description || 'Dowód'} (${ev.verified_at || ev.observed_at || ''})`, ev.source_url);
      }
      for (const c of r.contacts || []) { details.append(el('p', `${c.kind}: ${c.value} — ${c.verified_at}`)); link(details, 'Źródło kontaktu', c.source_url); }
      for (const s of r.sources || [r.source]) if (s) link(details, `Źródło: ${s.provider}`, s.url);
      if (r.website) link(details, 'Strona firmy', r.website);
      card.append(details);
      const controls = el('div'); controls.className = 'review';
      const statusLabel = el('label', 'Nowy status'); const select = el('select');
      for (const value of data.workflow?.[r.status] || []) if (statuses.includes(value)) { const o = el('option', value.replaceAll('_',' ')); o.value = value; select.append(o); }
      statusLabel.append(select); controls.append(statusLabel);
      const reasonLabel = el('label', 'Uzasadnienie decyzji'); const reason = el('input'); reason.maxLength = 1000; reasonLabel.append(reason); controls.append(reasonLabel);
      const noteLabel = el('label', 'Podstawa kontaktu (tylko gdy dozwolony)'); const note = el('input'); note.maxLength = 1000; noteLabel.append(note); controls.append(noteLabel);
      const sourceLabel = el('label', 'Źródło potwierdzenia kontaktu'); const source = el('input'); source.type = 'url'; sourceLabel.append(source); controls.append(sourceLabel);
      const dateLabel = el('label', 'Data potwierdzenia'); const date = el('input'); date.type = 'date'; dateLabel.append(date); controls.append(dateLabel);
      const save = el('button', 'Dodaj decyzję do pliku'); save.type = 'button'; save.disabled = !select.options.length;
      const message = el('p', pending.has(r.id) ? 'Decyzja oczekuje w pliku. SQLite nie zostało zmienione.' : ''); message.setAttribute('role','status');
      save.onclick = () => { try { pending.set(r.id, decision(r, select.value, reason.value, { note: note.value, source_url: source.value, verified_at: date.value })); message.textContent = 'Dodano decyzję. Pobierz plik i zastosuj go lokalnie.'; $('download').disabled = false; } catch (error) { message.textContent = error.message; } };
      controls.append(save); card.append(controls, message); $('records').append(card);
    }
  }
  $('file').onchange = async () => {
    try {
      const file = $('file').files[0]; if (!file) return;
      if (file.size > 10 * 1024 * 1024) throw Error('Plik jest zbyt duży (maks. 10 MB).');
      const loaded = validateExport(JSON.parse(await file.text())); data = loaded; pending.clear(); $('download').disabled = true;
      options('industry', data.records.map(r=>r.industry)); options('province', data.records.map(r=>r.voivodeship)); options('status', statuses); render();
    } catch (error) { $('message').textContent = error.message; }
  };
  for (const id of ['query','industry','province','status','category']) $(id).oninput = render;
  $('download').onclick = () => {
    const blob = new Blob([JSON.stringify([...pending.values()], null, 2)], { type: 'application/json' });
    const href = URL.createObjectURL(blob); const a = el('a'); a.href = href; a.download = 'webforge-decisions.json'; a.click(); setTimeout(()=>URL.revokeObjectURL(href), 1000);
  };
}
