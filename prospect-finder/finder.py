"""WebForge Prospect Finder 0.2 — evidence-based, standard library only."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import math
import sqlite3
import sys
import unicodedata
from urllib.parse import urlsplit, urlunsplit
from typing import Protocol

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
STATUSES = ['znaleziony', 'do_weryfikacji', 'zaakceptowany', 'demo_gotowe', 'kontakt_dozwolony', 'kontaktowany', 'zainteresowany', 'odrzucony', 'klient']
TRANSITIONS = {
    'znaleziony': ['do_weryfikacji', 'odrzucony'],
    'do_weryfikacji': ['zaakceptowany', 'odrzucony'],
    'zaakceptowany': ['demo_gotowe', 'kontakt_dozwolony', 'odrzucony'],
    'demo_gotowe': ['kontakt_dozwolony', 'odrzucony'],
    'kontakt_dozwolony': ['kontaktowany', 'odrzucony'],
    'kontaktowany': ['zainteresowany', 'odrzucony'],
    'zainteresowany': ['klient', 'odrzucony'],
    'odrzucony': ['do_weryfikacji'], 'klient': [],
}
FACT_VALUES = {'website_status': ['present', 'missing', 'unknown'], 'sales_potential': ['low', 'medium', 'high', 'unknown']}
ISSUES = ['outdated', 'mobile_issues', 'unclear_offer', 'technical_issues']
APPROVED = set(STATUSES) - {'znaleziony', 'do_weryfikacji', 'odrzucony'}


def load_json(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return json.load(stream)


def config(name):
    return load_json(ROOT / 'config' / f'{name}.json')


def industries():
    return {i['id']: i for i in config('industries')['industries']}


def norm(value):
    return re.sub(r'\s+', ' ', ''.join(c for c in unicodedata.normalize('NFKD', value.casefold().replace('ł', 'l')) if not unicodedata.combining(c))).strip()


def text(value, field, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f'{field}: wymagany niepusty tekst, maks. {limit} znaków, bez znaków sterujących')
    return value.strip()


def date(value, field, today=None):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(f'{field}: wymagana data YYYY-MM-DD')
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f'{field}: wymagana data YYYY-MM-DD') from exc
    if parsed > (today or dt.date.today()):
        raise ValueError(f'{field}: data z przyszłości')
    return parsed.isoformat()


def url(value, field):
    value = text(value, field, 2000)
    try:
        p = urlsplit(value)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.port not in (None, 80, 443):
            raise ValueError()
        # Do not accept links carrying tokens, credentials, or private notes.
        if p.query or p.fragment:
            raise ValueError()
    except ValueError as exc:
        raise ValueError(f'{field}: publiczny HTTP/HTTPS bez loginu, hasła, query i fragmentu') from exc
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', '', ''))


def keys(obj, allowed, field):
    if not isinstance(obj, dict) or set(obj) - set(allowed):
        raise ValueError(f'{field}: nieznane pola lub nieprawidłowy obiekt')


def evidence(value, field, today=None):
    keys(value, ['source_url', 'verified_at', 'note', 'value'], field)
    return {'source_url': url(value.get('source_url'), field), 'verified_at': date(value.get('verified_at'), field, today), 'note': text(value.get('note'), field, 1000)}


def validate_record(raw, today=None):
    keys(raw, ['name', 'industry', 'city', 'voivodeship', 'country', 'address', 'website', 'contacts', 'source', 'last_verified_at', 'activity_signs', 'facts', 'services', 'description', 'fictional', 'geo', 'source_metadata', 'site_check'], 'firma')
    if type(raw.get('fictional')) is not bool:
        raise ValueError('fictional: wymagane jawne true/false')
    industry = raw.get('industry')
    if industry not in industries():
        raise ValueError('Nieznana branża; sprawdź config/industries.json')
    province = raw.get('voivodeship')
    if province not in config('locations')['voivodeships'] or raw.get('country', 'PL') != 'PL':
        raise ValueError('Nieprawidłowe województwo lub kraj')
    source = raw.get('source')
    keys(source, ['provider', 'id', 'url'], 'source')
    source = {'provider': text(source.get('provider'), 'provider', 80), 'id': text(source.get('id'), 'source.id', 160), 'url': url(source.get('url'), 'source.url')}
    record = {
        'name': text(raw.get('name'), 'name', 160), 'industry': industry,
        'city': text(raw.get('city'), 'city', 120), 'voivodeship': province, 'country': 'PL',
        'address': text(raw['address'], 'address', 300) if raw.get('address') else '',
        'website': url(raw['website'], 'website') if raw.get('website') else None,
        'source': source, 'last_verified_at': date(raw.get('last_verified_at'), 'last_verified_at', today),
        'fictional': raw['fictional'], 'contacts': [], 'activity_signs': [], 'facts': {},
        'services': [], 'description': '',
    }
    for c in raw.get('contacts', []):
        keys(c, ['kind', 'value', 'source_url', 'verified_at'], 'contact')
        kind = c.get('kind'); value = text(c.get('value'), 'contact.value', 300)
        if kind == 'email':
            if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value):
                raise ValueError('Nieprawidłowy email')
        elif kind == 'phone':
            if not re.fullmatch(r'\+?[0-9 ()-]{7,30}', value) or not 7 <= len(re.sub(r'\D', '', value)) <= 15:
                raise ValueError('Nieprawidłowy telefon')
        else:
            raise ValueError('contact.kind: tylko email/phone')
        record['contacts'].append({'kind': kind, 'value': value, 'source_url': url(c.get('source_url'), 'contact.source_url'), 'verified_at': date(c.get('verified_at'), 'contact.verified_at', today)})
    for item in raw.get('activity_signs', []):
        keys(item, ['description', 'source_url', 'observed_at'], 'activity_signs')
        record['activity_signs'].append({'description': text(item.get('description'), 'activity.description', 600), 'source_url': url(item.get('source_url'), 'activity.source_url'), 'observed_at': date(item.get('observed_at'), 'activity.observed_at', today)})
    facts = raw.get('facts', {})
    keys(facts, ['website_status', 'sales_potential', *ISSUES], 'facts')
    for key, item in facts.items():
        ev = evidence(item, f'facts.{key}', today); value = item.get('value')
        if key in FACT_VALUES:
            if value not in FACT_VALUES[key]:
                raise ValueError(f'Nieprawidłowa wartość {key}')
        elif value is not None and type(value) is not bool:
            raise ValueError(f'{key}: true/false/null')
        record['facts'][key] = {**ev, 'value': value}
    site = record['facts'].get('website_status', {}).get('value')
    if site == 'missing' and record['website'] or site == 'present' and not record['website']:
        raise ValueError('Sprzeczne website i website_status')
    if site == 'missing' and any(record['facts'].get(k, {}).get('value') is True for k in ISSUES):
        raise ValueError('Nie można oceniać problemów nieistniejącej strony')
    services = raw.get('services', [])
    if not isinstance(services, list) or len(services) > 12:
        raise ValueError('services: lista maks. 12 usług')
    record['services'] = [text(s, 'service', 120) for s in services]
    if raw.get('description'):
        record['description'] = text(raw['description'], 'description', 2000)
    if 'geo' in raw:
        geo=raw['geo'];keys(geo,['lat','lon'],'geo')
        if any(type(geo.get(k)) not in (int,float) or not math.isfinite(geo[k]) for k in ('lat','lon')) or not -90<=geo['lat']<=90 or not -180<=geo['lon']<=180:raise ValueError('Nieprawidłowe współrzędne')
        record['geo']=geo
    if 'source_metadata' in raw:
        metadata=raw['source_metadata'];keys(metadata,['license','attribution','copyright_url','osm_timestamp','classification_note'],'source_metadata')
        record['source_metadata']={k:url(v,k) if k=='copyright_url' else text(v,k,1500) for k,v in metadata.items()}
    if 'site_check' in raw:
        report=raw['site_check'];keys(report,['checked_at','outcome','http_status','final_url','signals'],'site_check')
        if report.get('outcome') not in ['no_url','unknown','reachable','http_error','access_limited','robots_disallowed','network_error','budget_exceeded']:raise ValueError('Nieprawidłowy wynik audytu')
        status=report.get('http_status')
        if status is not None and (type(status) is not int or not 100<=status<=599):raise ValueError('Nieprawidłowy HTTP status')
        signals=report.get('signals',[])
        if not isinstance(signals,list) or len(signals)>20:raise ValueError('Nieprawidłowe sygnały audytu')
        for signal in signals:
            keys(signal,['code','detail'],'site_check.signal');text(signal.get('code'),'signal.code',80);text(signal.get('detail'),'signal.detail',600)
        record['site_check']={'checked_at':date(report.get('checked_at'),'site_check.checked_at',today),'outcome':report['outcome'],'http_status':status,'final_url':url(report['final_url'],'final_url') if report.get('final_url') else None,'signals':signals}
    return record


def score(record, today=None):
    today = today or dt.date.today()
    cfg = config('scoring'); w = cfg['weights']; days = cfg['freshness_days']
    if set(w) != {'missing_website', *ISSUES, 'activity', 'sales_potential'} or any(type(v) is not int or v < 0 for v in w.values()) or type(days) is not int or days < 0:
        raise ValueError('Nieprawidłowa konfiguracja wag lub świeżości')
    if max(w['missing_website'], sum(w[k] for k in ISSUES)) + w['activity'] + w['sales_potential'] != 100:
        raise ValueError('Wagi muszą dawać maksymalnie 100 punktów')
    reasons = []; known = 0
    def fresh(day): return 0 <= (today - dt.date.fromisoformat(day)).days <= days
    def fact(key):
        ev = record['facts'].get(key)
        return ev if ev and fresh(ev['verified_at']) and ev['value'] not in (None, 'unknown') else None
    site = fact('website_status')
    need = 0
    if site and site['value'] == 'missing':
        need = w['missing_website']; known += w['missing_website']
        reasons.append({'criterion': 'missing_website', 'points': need, 'reason': 'Potwierdzony brak strony', 'evidence': [site]})
    elif site and site['value'] == 'present':
        for key in ISSUES:
            ev = fact(key); points = w[key] if ev and ev['value'] is True else 0
            if ev: known += w[key]
            need += points
            reasons.append({'criterion': key, 'points': points, 'reason': 'Potwierdzony problem' if points else 'Nie stwierdzono problemu' if ev else 'Brak aktualnych informacji — bez punktów', 'evidence': [ev] if ev else []})
    else:
        reasons.append({'criterion': 'website', 'points': 0, 'reason': 'Status strony nieustalony lub nieaktualny. Brak adresu nie oznacza braku strony.', 'evidence': []})
    active = [s for s in record['activity_signs'] if fresh(s['observed_at'])]
    activity = w['activity'] if active else 0
    if active: known += w['activity']
    reasons.append({'criterion': 'activity', 'points': activity, 'reason': 'Aktualne oznaki działalności' if active else 'Brak aktualnych oznak w danych — nie oznacza nieaktywności', 'evidence': active})
    sales_fact = fact('sales_potential'); sales = 0
    if sales_fact:
        known += w['sales_potential']; sales = round(w['sales_potential'] * {'low': 1/3, 'medium': 2/3, 'high': 1}[sales_fact['value']])
    reasons.append({'criterion': 'sales_potential', 'points': sales, 'reason': 'Udokumentowana ocena potencjału' if sales_fact else 'Potencjał nieustalony — bez punktów', 'evidence': [sales_fact] if sales_fact else []})
    return {'score': min(100, need + activity + sales), 'coverage_percent': min(100, known), 'activity_state': 'oznaki_aktywnosci' if active else 'nieustalone', 'reasons': reasons, 'scored_at': today.isoformat(), 'scoring_version': cfg['version']}


def matches(record, *, industry=None, city=None, voivodeship=None, country='PL', category='wszystkie'):
    if industry and industry not in industries(): raise ValueError('Nieznana branża filtra')
    if voivodeship and voivodeship not in config('locations')['voivodeships']: raise ValueError('Nieznane województwo')
    if country != 'PL' or category not in ('wszystkie', 'modernizacja'): raise ValueError('Nieznany kraj/kategoria')
    if industry and record['industry'] != industry or city and norm(record['city']) != norm(city) or voivodeship and record['voivodeship'] != voivodeship:
        return False
    if category == 'modernizacja':
        scored = score(record)
        return any(r['criterion'] in ISSUES and r['points'] > 0 for r in scored['reasons'])
    return True


class SourceAdapter(Protocol):
    def search(self, **filters) -> list[dict]: ...


class JsonFileSource:
    """Adapter contract: search(**filters) -> iterable of validated records. No HTTP."""
    def __init__(self, path, adapter='test-json'):
        cfg = config('sources')['adapters'].get(adapter)
        if not cfg or not cfg['enabled'] or cfg['kind'] != 'json-file': raise ValueError('Nieznane/wyłączone źródło lub niezaimplementowany adapter')
        if cfg['mode'] == 'public': path = private_path(path)
        data = load_json(path)
        keys(data, ['dataset_type', 'records'], 'dataset')
        if data.get('dataset_type') != cfg['mode'] or not isinstance(data.get('records'), list):
            raise ValueError('Typ pliku nie odpowiada adapterowi')
        self.records = [validate_record(r) for r in data['records']]
        if any(r['fictional'] != (cfg['mode'] == 'fictional') for r in self.records):
            raise ValueError('Błędne oznaczenie danych fikcyjnych/publicznych')

    def search(self, **filters):
        # Validate filters even for an empty dataset.
        dummy = {'industry': '', 'city': '', 'voivodeship': '', 'facts': {}, 'activity_signs': []}
        matches(dummy, **filters)
        return [r for r in self.records if matches(r, **filters)]


def private_path(path):
    path = Path(path).expanduser().resolve()
    if path == REPO or REPO in path.parents:
        raise ValueError('Bazy, eksporty i dane robocze muszą być POZA repozytorium (gałąź jest publicznie wdrażana)')
    return path


def fingerprint(record):
    parts = [str(record['fictional']), record['name'], record['country'], record['voivodeship'], record['city'], record['address']]
    return hashlib.sha256('\0'.join(norm(v) for v in parts).encode()).hexdigest()


class Store:
    def __init__(self, path):
        self.path = private_path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path); self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS prospects(id INTEGER PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'znaleziony', permission TEXT);
        CREATE TABLE IF NOT EXISTS identities(provider TEXT NOT NULL, source_id TEXT NOT NULL, fictional INTEGER NOT NULL, prospect_id INTEGER NOT NULL REFERENCES prospects(id), PRIMARY KEY(provider,source_id,fictional));
        CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, prospect_id INTEGER NOT NULL REFERENCES prospects(id), old_status TEXT, new_status TEXT NOT NULL, reason TEXT NOT NULL, changed_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS automation_events(id INTEGER PRIMARY KEY, prospect_id INTEGER NOT NULL REFERENCES prospects(id), event TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'blocked', created_at TEXT NOT NULL);
        ''')
        os.chmod(self.path, 0o600)

    def close(self): self.db.close()

    def ingest(self, records):
        records = [validate_record(r) for r in records]; ids = []
        with self.db:
            for incoming in records:
                fp = fingerprint(incoming); src = incoming['source']
                hits = self.db.execute('SELECT id FROM prospects WHERE fingerprint=? UNION SELECT prospect_id FROM identities WHERE provider=? AND source_id=? AND fictional=?', (fp, src['provider'], src['id'], int(incoming['fictional']))).fetchall()
                if len(hits) > 1: raise ValueError('Niejednoznaczna tożsamość firmy — wymagana ręczna weryfikacja')
                if hits:
                    id_ = hits[0][0]; old = json.loads(self.db.execute('SELECT payload FROM prospects WHERE id=?', (id_,)).fetchone()[0])
                    latest = incoming if incoming['last_verified_at'] >= old['last_verified_at'] else old
                    merged = {**latest}
                    merged['services'] = latest['services'] or old['services'] or incoming['services']
                    merged['description'] = latest['description'] or old['description'] or incoming['description']
                    for key in ('contacts', 'activity_signs'):
                        merged[key] = list({json.dumps(x, sort_keys=True, ensure_ascii=False): x for x in old[key] + incoming[key]}.values())
                    merged['facts'] = dict(old['facts'])
                    for key, value in incoming['facts'].items():
                        if key not in merged['facts'] or value['verified_at'] >= merged['facts'][key]['verified_at']: merged['facts'][key] = value
                    # The newest explicit site observation controls page-specific facts.
                    site = merged['facts'].get('website_status', {}).get('value')
                    if site == 'missing':
                        merged['website'] = None
                        for key in ISSUES: merged['facts'].pop(key, None)
                    merged['sources'] = list({json.dumps(x, sort_keys=True): x for x in old.get('sources', [old['source']]) + [src]}.values())
                    self.db.execute('UPDATE prospects SET fingerprint=?,payload=? WHERE id=?', (fingerprint(merged), json.dumps(merged, ensure_ascii=False), id_))
                else:
                    incoming['sources'] = [src]
                    cur = self.db.execute('INSERT INTO prospects(fingerprint,payload) VALUES (?,?)', (fp, json.dumps(incoming, ensure_ascii=False))); id_ = cur.lastrowid
                self.db.execute('INSERT OR IGNORE INTO identities VALUES (?,?,?,?)', (src['provider'], src['id'], int(incoming['fictional']), id_)); ids.append(id_)
        return ids

    def get(self, id_):
        row = self.db.execute('SELECT * FROM prospects WHERE id=?', (id_,)).fetchone()
        if row is None: raise ValueError('Nie znaleziono rekordu')
        record = json.loads(row['payload'])
        return {**record, 'id': row['id'], 'status': row['status'], 'contact_permission': json.loads(row['permission']) if row['permission'] else None, 'assessment': score(record)}

    def search(self, status=None, **filters):
        if status and status not in STATUSES: raise ValueError('Nieznany status')
        matches({'industry': '', 'city': '', 'voivodeship': '', 'facts': {}, 'activity_signs': []}, **filters)
        records = [self.get(row[0]) for row in self.db.execute('SELECT id FROM prospects')]
        return sorted([r for r in records if (not status or r['status'] == status) and matches(r, **filters)], key=lambda r: (-r['assessment']['score'], r['id']))

    def review(self, id_, status, reason, expected_status=None, permission=None):
        with self.db: self._review(id_, status, reason, expected_status, permission)

    def _review(self, id_, status, reason, expected_status=None, permission=None):
        record = self.get(id_); old = record['status']; reason = text(reason, 'reason', 1000)
        if expected_status is not None and old != expected_status: raise ValueError('Status zmienił się od eksportu — odśwież dane')
        if status not in TRANSITIONS[old]: raise ValueError(f'Niedozwolona zmiana statusu: {old} → {status}')
        if status == 'zaakceptowany':
            # Every newly approved record must be convertible without invented content.
            demo_input({**record, 'status': 'zaakceptowany'})
        if status == 'kontakt_dozwolony':
            if not permission: raise ValueError('Wymagane jawne potwierdzenie podstawy kontaktu; publiczny email nie wystarcza')
            permission = evidence(permission, 'contact_permission')
            if not record['contacts']: raise ValueError('Brak kanału kontaktu')
            permission['contacts_fingerprint'] = hashlib.sha256(json.dumps(sorted((c['kind'], c['value']) for c in record['contacts'])).encode()).hexdigest()
            if (dt.date.today() - dt.date.fromisoformat(permission['verified_at'])).days > config('scoring')['freshness_days']: raise ValueError('Potwierdzenie kontaktu wymaga aktualizacji')
        elif status == 'kontaktowany':
            if not record['contact_permission']: raise ValueError('Brak podstawy kontaktu')
            current = hashlib.sha256(json.dumps(sorted((c['kind'], c['value']) for c in record['contacts'])).encode()).hexdigest()
            if record['contact_permission'].get('contacts_fingerprint') != current or (dt.date.today() - dt.date.fromisoformat(record['contact_permission']['verified_at'])).days > config('scoring')['freshness_days']:
                raise ValueError('Potwierdzenie kontaktu nieaktualne lub zmieniły się dane kontaktowe')
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        self.db.execute('UPDATE prospects SET status=?,permission=? WHERE id=?', (status, json.dumps(permission or record['contact_permission'], ensure_ascii=False) if permission or record['contact_permission'] else None, id_))
        self.db.execute('INSERT INTO history(prospect_id,old_status,new_status,reason,changed_at) VALUES (?,?,?,?,?)', (id_, old, status, reason, now))
        event = {'zaakceptowany': 'prospect.accepted', 'demo_gotowe': 'demo.approved', 'kontakt_dozwolony': 'contact.approved', 'zainteresowany': 'quote.requested'}.get(status)
        if event: self.db.execute('INSERT INTO automation_events(prospect_id,event,created_at) VALUES (?,?,?)', (id_, event, now))

    def apply_decisions(self, decisions):
        if not isinstance(decisions, list): raise ValueError('Decyzje: wymagana lista')
        with self.db:
            for d in decisions:
                keys(d, ['id', 'status', 'reason', 'expected_status', 'permission'], 'decision')
                if not d.get('expected_status'): raise ValueError('Brak expected_status')
                self._review(d['id'], d['status'], d['reason'], d['expected_status'], d.get('permission'))


def demo_input(record):
    if record['status'] not in APPROVED: raise ValueError('Rekord musi być najpierw zaakceptowany')
    if not record['services'] or not record['description']: raise ValueError('Uzupełnij potwierdzone services i description; adapter ich nie wymyśla')
    contact = {}
    for c in record['contacts']:
        if (dt.date.today() - dt.date.fromisoformat(c['verified_at'])).days <= config('scoring')['freshness_days']:
            contact.setdefault('email' if c['kind'] == 'email' else 'telefon', c['value'])
    if record['website']: contact['www'] = record['website']
    if not contact: raise ValueError('Brak aktualnego kontaktu/WWW potrzebnego generatorowi')
    if record['address']: contact['adres'] = record['address']
    profile = industries()[record['industry']]
    templates = load_json(REPO / 'demo-generator/data/industries.json')
    if profile['demo_template'] not in templates: raise ValueError('Branża nie ma poprawnego mapowania szablonu')
    return {'slug': f'prospect-{record["id"]}-'+fingerprint(record)[:8], 'nazwa': record['name'], 'branza': profile['demo_template'], 'etykieta_branzy': text(profile['label'], 'industry.label', 120), 'cta': 'Zapytaj o ofertę', 'miasto': record['city'], 'opis': record['description'], 'uslugi': record['services'], 'kontakt': contact}


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def export_records(records, path, kind='json'):
    path = private_path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if kind == 'json':
        content = json.dumps({'version': 1, 'exported_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'workflow': TRANSITIONS, 'records': records}, ensure_ascii=False, indent=2)
    elif kind == 'csv':
        stream = io.StringIO(newline=''); writer = csv.writer(stream)
        writer.writerow(['id', 'name', 'industry', 'city', 'voivodeship', 'website', 'status', 'score', 'coverage_percent', 'fictional', 'last_verified_at', 'contacts_json', 'sources_json', 'reasons_json', 'geo_json', 'source_metadata_json', 'site_check_json'])
        for r in records:
            writer.writerow([csv_safe(v) for v in [r['id'], r['name'], r['industry'], r['city'], r['voivodeship'], r['website'] or '', r['status'], r['assessment']['score'], r['assessment']['coverage_percent'], r['fictional'], r['last_verified_at'], json.dumps(r['contacts'], ensure_ascii=False), json.dumps(r.get('sources', [r['source']]), ensure_ascii=False), json.dumps(r['assessment']['reasons'], ensure_ascii=False), json.dumps(r.get('geo'),ensure_ascii=False), json.dumps(r.get('source_metadata'),ensure_ascii=False), json.dumps(r.get('site_check'),ensure_ascii=False)]])
        content = '\ufeff' + stream.getvalue()
    else: raise ValueError('Eksport: json/csv')
    # Exclusive creation: never overwrite a database, source file, or prior export.
    with path.open('x', encoding='utf-8', newline='') as stream: stream.write(content)
    os.chmod(path, 0o600)
    return path


def parser():
    p = argparse.ArgumentParser(description='WebForge Prospect Finder v0.2 — bez wysyłki i publikacji')
    p.add_argument('--db', default=str(Path.home() / '.local/share/webforge-prospects/prospects.sqlite3'))
    sub = p.add_subparsers(dest='command', required=True)
    def filters(cmd):
        cmd.add_argument('--industry'); cmd.add_argument('--city'); cmd.add_argument('--voivodeship'); cmd.add_argument('--country', default='PL', choices=['PL']); cmd.add_argument('--category', default='wszystkie', choices=['wszystkie', 'modernizacja'])
    find = sub.add_parser('find'); find.add_argument('--input', required=True); find.add_argument('--source', choices=[k for k,v in config('sources')['adapters'].items() if v['kind']=='json-file'], default='test-json'); filters(find)
    discover=sub.add_parser('discover');discover.add_argument('--region',default='poznan');discover.add_argument('--limit',type=int,default=25);discover.add_argument('--workdir');discover.add_argument('--industry');discover.add_argument('--category',choices=['wszystkie','modernizacja'],default='wszystkie')
    ls = sub.add_parser('list'); filters(ls); ls.add_argument('--status', choices=STATUSES)
    exp = sub.add_parser('export'); filters(exp); exp.add_argument('--status', choices=STATUSES); exp.add_argument('--format', choices=['json', 'csv'], default='json'); exp.add_argument('--output', required=True)
    review = sub.add_parser('review'); review.add_argument('id', type=int); review.add_argument('--status', choices=STATUSES, required=True); review.add_argument('--reason', required=True); review.add_argument('--permission-file')
    decisions = sub.add_parser('apply-decisions'); decisions.add_argument('--input', required=True)
    demo = sub.add_parser('demo-input'); demo.add_argument('id', type=int); demo.add_argument('--output', required=True)
    sub.add_parser('config'); return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == 'config':
        print(json.dumps({'industries': config('industries'), 'locations': config('locations'), 'statuses': STATUSES}, ensure_ascii=False, indent=2)); return 0
    store = Store(args.db)
    try:
        if args.command=='discover':
            from live import discover_run
            report=discover_run(store,region=args.region,limit=args.limit,workdir=args.workdir,industry=args.industry,category=args.category)
            print(json.dumps(report,ensure_ascii=False,indent=2))
            return 0 if report['outcome']=='completed' else 2
        filters = {k: getattr(args, k) for k in ('industry', 'city', 'voivodeship', 'country', 'category') if hasattr(args, k)}
        if args.command == 'find':
            source = JsonFileSource(args.input, args.source)
            print(json.dumps({'ids': store.ingest(source.search(**filters))}, ensure_ascii=False))
        elif args.command in ('list', 'export'):
            records = store.search(status=args.status, **filters)
            if args.command == 'list': print(json.dumps(records, ensure_ascii=False, indent=2))
            else: print(export_records(records, args.output, args.format))
        elif args.command == 'review':
            store.review(args.id, args.status, args.reason, permission=load_json(args.permission_file) if args.permission_file else None); print('Zapisano decyzję; niczego nie wysłano')
        elif args.command == 'apply-decisions':
            store.apply_decisions(load_json(args.input)); print('Zapisano decyzje; niczego nie wysłano')
        elif args.command == 'demo-input':
            draft = demo_input(store.get(args.id))
            path = private_path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf8') as stream: json.dump(draft, stream, ensure_ascii=False, indent=2)
            os.chmod(path, 0o600); print('Zapisano wyłącznie JSON szkicu poza repozytorium. Nie wygenerowano ani nie opublikowano strony.')
    finally: store.close()
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print(f'Błąd: {exc}', file=sys.stderr); sys.exit(1)
