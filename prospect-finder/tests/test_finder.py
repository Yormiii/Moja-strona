import copy
import csv
import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import finder as f

TODAY = dt.date.today()


def sample(index=0):
    raw = copy.deepcopy(f.load_json(ROOT / 'fixtures/companies.json')['records'][index])
    raw['last_verified_at'] = TODAY.isoformat()
    for c in raw['contacts']: c['verified_at'] = TODAY.isoformat()
    for ev in raw['facts'].values(): ev['verified_at'] = TODAY.isoformat()
    for ev in raw['activity_signs']: ev['observed_at'] = TODAY.isoformat()
    return raw


class FinderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='webforge-prospects-')
        self.path = Path(self.temp.name)
        self.store = f.Store(self.path / 'prospects.sqlite3')

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def add(self, index=0): return self.store.ingest([sample(index)])[0]

    def approve(self, id_):
        self.store.review(id_, 'do_weryfikacji', 'Ręczna weryfikacja testu')
        self.store.review(id_, 'zaakceptowany', 'Potwierdzony fikcyjny przykład')

    def test_configuration(self):
        self.assertEqual(len(f.industries()), 30)
        self.assertEqual(len(f.config('locations')['voivodeships']), 16)
        self.assertEqual(len(f.STATUSES), 9)
        self.assertEqual(f.config('industries')['status'], 'robocza-do-potwierdzenia')
        self.assertFalse(f.config('automation')['workers_enabled'])

    def test_fixture_and_adapter(self):
        source = f.JsonFileSource(ROOT / 'fixtures/companies.json')
        self.assertEqual(len(source.search()), 5)
        self.assertTrue(all(r['fictional'] for r in source.search()))
        with self.assertRaises(ValueError): f.JsonFileSource(ROOT / 'fixtures/companies.json', 'public-json')

    def test_city_province_poland_filters(self):
        source = f.JsonFileSource(ROOT / 'fixtures/companies.json')
        self.assertEqual(len(source.search(city='lodz')), 2)
        self.assertEqual(len(source.search(voivodeship='pomorskie')), 1)
        self.assertEqual(len(source.search(country='PL')), 5)
        self.assertEqual(len(source.search(industry='kosmetyczka')), 1)
        self.assertEqual(len(source.search(city='Łódź', voivodeship='pomorskie')), 0)
        with self.assertRaises(ValueError): source.search(industry='nie-ma')
        with self.assertRaises(ValueError): source.search(voivodeship='nie-ma')

    def test_modernization_across_industries(self):
        records = [f.validate_record(sample(1)), f.validate_record(sample(0))]
        self.assertTrue(f.matches(records[0], category='modernizacja'))
        self.assertFalse(f.matches(records[1], category='modernizacja'))
        records[0]['industry'] = 'gospodarstwo'
        self.assertTrue(f.matches(records[0], category='modernizacja'))

    def test_provenance_and_dates_required(self):
        mutations = [lambda r: r.pop('source'), lambda r: r['contacts'][0].pop('source_url'), lambda r: r.pop('last_verified_at'), lambda r: r['facts']['website_status'].pop('note'), lambda r: r.update(last_verified_at='2099-01-01'), lambda r: r.update(last_verified_at='20261027'), lambda r: r.update(api_key='secret'), lambda r: r.update(fictional='true')]
        for mutate in mutations:
            r = sample(); mutate(r)
            with self.subTest(r=r):
                with self.assertRaises((ValueError, TypeError)): f.validate_record(r)

    def test_bad_urls_and_contacts(self):
        for bad in ['javascript:alert(1)', 'https://user:pass@example.invalid/', 'https://example.invalid/?token=secret', 'file:///tmp/x']:
            r = sample(); r['source']['url'] = bad
            with self.assertRaises(ValueError): f.validate_record(r)
        r = sample(); r['contacts'][0]['value'] = 'test\r\nBcc:x@example.invalid'
        with self.assertRaises(ValueError): f.validate_record(r)

    def test_missing_site_is_not_inferred(self):
        r = f.validate_record(sample(2)); result = f.score(r)
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['activity_state'], 'nieustalone')
        self.assertIn('nie oznacza', json.dumps(result, ensure_ascii=False))
        r['website'] = 'https://example.invalid/'
        self.assertEqual(f.score(r)['score'], 0)

    def test_missing_site_full_score(self):
        result = f.score(f.validate_record(sample()))
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['coverage_percent'], 100)
        self.assertEqual(sum(r['points'] for r in result['reasons']), 100)
        self.assertTrue(all(r['evidence'] for r in result['reasons']))

    def test_existing_site_full_score(self):
        r = sample(1)
        for key in f.ISSUES: r['facts'][key]['value'] = True
        r['facts']['sales_potential']['value'] = 'high'
        r['activity_signs'] = sample()['activity_signs']
        self.assertEqual(f.score(f.validate_record(r))['score'], 100)

    def test_stale_evidence_no_points(self):
        r = sample(); stale = (TODAY - dt.timedelta(days=181)).isoformat()
        for ev in r['facts'].values(): ev['verified_at'] = stale
        for ev in r['activity_signs']: ev['observed_at'] = stale
        result = f.score(f.validate_record(r)); self.assertEqual(result['score'], 0)
        self.assertEqual(result['activity_state'], 'nieustalone')

    def test_contradictions_rejected(self):
        r = sample(); r['website'] = 'https://example.invalid/'
        with self.assertRaises(ValueError): f.validate_record(r)
        r = sample(); r['facts']['mobile_issues'] = {**r['facts']['website_status'], 'value': True}
        with self.assertRaises(ValueError): f.validate_record(r)

    def test_dedup_same_source_and_cross_source(self):
        first = self.add(); self.assertEqual(self.add(), first)
        r = sample(); r['source']['provider'] = 'second-public-source'; r['source']['id'] = 'new'
        self.assertEqual(self.store.ingest([r]), [first])
        self.assertEqual(len(self.store.search()), 1)
        self.assertEqual(len(self.store.get(first)['sources']), 2)

    def test_branches_and_fictional_real_are_not_merged(self):
        self.add()
        r = sample(); r['source']['id'] = 'branch'; r['address'] = 'Inny adres 1'; self.store.ingest([r])
        r = sample(); r['fictional'] = False; self.store.ingest([r])
        self.assertEqual(len(self.store.search()), 3)

    def test_old_import_preserves_new_data_and_status(self):
        id_ = self.add(); self.approve(id_)
        r = sample(); r['last_verified_at'] = (TODAY-dt.timedelta(days=5)).isoformat(); r['name'] = 'Starsza nazwa TEST'
        self.store.ingest([r]); current = self.store.get(id_)
        self.assertEqual(current['name'], sample()['name']); self.assertEqual(current['status'], 'zaakceptowany')
        self.assertEqual(f.fingerprint(current), self.store.db.execute('SELECT fingerprint FROM prospects WHERE id=?', (id_,)).fetchone()[0])

    def test_atomic_import_bad_record(self):
        r = sample(1); r['industry'] = 'unknown'
        with self.assertRaises(ValueError): self.store.ingest([sample(), r])
        self.assertEqual(self.store.search(), [])

    def test_status_guards_and_history(self):
        id_ = self.add()
        with self.assertRaises(ValueError): self.store.review(id_, 'kontaktowany', 'Nie wolno przeskoczyć')
        self.approve(id_)
        self.assertEqual(self.store.get(id_)['status'], 'zaakceptowany')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM history').fetchone()[0], 2)
        events = self.store.db.execute('SELECT state FROM automation_events').fetchall()
        self.assertTrue(events); self.assertTrue(all(e[0] == 'blocked' for e in events))

    def test_contact_permission_required_and_bound_to_contacts(self):
        id_ = self.add(); self.approve(id_)
        with self.assertRaises(ValueError): self.store.review(id_, 'kontakt_dozwolony', 'Publiczny email')
        permission = {'source_url':'https://example.invalid/potwierdzenie','verified_at':TODAY.isoformat(),'note':'FIKCYJNE potwierdzenie na potrzeby testu'}
        self.store.review(id_, 'kontakt_dozwolony', 'Ręczne potwierdzenie', permission=permission)
        r = sample(); r['contacts'][0]['value'] = 'nowy@example.invalid'; self.store.ingest([r])
        with self.assertRaises(ValueError): self.store.review(id_, 'kontaktowany', 'Kanał się zmienił')

    def test_decision_file_atomic_and_optimistic_lock(self):
        a = self.add(); b = self.add(1)
        self.store.review(b, 'do_weryfikacji', 'Wcześniej zmienione')
        decisions = [{'id':id_,'status':'do_weryfikacji','expected_status':'znaleziony','reason':'TEST'} for id_ in [a,b]]
        with self.assertRaises(ValueError): self.store.apply_decisions(decisions)
        self.assertEqual(self.store.get(a)['status'], 'znaleziony')
        self.assertEqual(self.store.get(b)['status'], 'do_weryfikacji')

    def test_json_csv_export_sources_and_formula_protection(self):
        r = sample(); r['name'] = '=SUM(1,2) FIRMA FIKCYJNA'; id_ = self.store.ingest([r])[0]
        rows = self.store.search(); j = f.export_records(rows, self.path/'data.json')
        payload = f.load_json(j); self.assertEqual(payload['records'][0]['source'], r['source']); self.assertIn('workflow',payload)
        c = f.export_records(rows, self.path/'data.csv', 'csv')
        parsed = list(csv.reader(io.StringIO(c.read_text(encoding='utf-8-sig'))))
        self.assertTrue(parsed[1][1].startswith("'=")); self.assertIn('sources_json',parsed[0])
        with self.assertRaises(FileExistsError): f.export_records(rows, j)

    def test_private_paths_rejected_inside_repository(self):
        for p in [ROOT/'private/test.sqlite3', ROOT/'exports/private.json']:
            with self.assertRaises(ValueError): f.private_path(p)
        with self.assertRaises(ValueError): f.Store(ROOT/'private.sqlite3')
        with self.assertRaises(ValueError): f.export_records([], ROOT/'bad-export.json')

    def test_adapter_requires_acceptance_and_complete_data(self):
        id_ = self.add()
        with self.assertRaises(ValueError): f.demo_input(self.store.get(id_))
        self.approve(id_); data = f.demo_input(self.store.get(id_)); self.assertEqual(data['nazwa'], sample()['name'])
        self.assertIn('etykieta_branzy',data)
        id2 = self.add(2)
        self.store.review(id2, 'do_weryfikacji', 'Sprawdzam kompletność')
        with self.assertRaises(ValueError): self.store.review(id2, 'zaakceptowany', 'Brak kontaktu')
        self.assertEqual(self.store.get(id2)['status'], 'do_weryfikacji')
        with self.assertRaises(ValueError): f.demo_input(self.store.get(id2))

    def test_all_thirty_branches_convert_to_existing_generator(self):
        drafts = []
        for key in f.industries():
            r = sample(); r['industry'] = key; r['status'] = 'zaakceptowany'; r['id'] = 1
            drafts.append(f.demo_input(r))
        script = "import {validateCompany} from './demo-generator/generate.mjs'; import{readFileSync}from'node:fs'; for(const c of JSON.parse(readFileSync(0,'utf8')))validateCompany(c);"
        result = subprocess.run(['node','--input-type=module','-e',script], cwd=ROOT.parent, input=json.dumps(drafts), text=True, capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_database_persists(self):
        id_ = self.add(); other = f.Store(self.path/'prospects.sqlite3')
        try:self.assertEqual(other.get(id_)['name'],sample()['name'])
        finally:other.close()

    def test_full_manual_workflow_and_rejection(self):
        id_ = self.add(); self.approve(id_)
        self.store.review(id_, 'demo_gotowe', 'Fikcyjny stan ręcznie oznaczony')
        permission = {'source_url':'https://example.invalid/permission','verified_at':TODAY.isoformat(),'note':'Testowa potwierdzona podstawa kontaktu'}
        self.store.review(id_, 'kontakt_dozwolony', 'TEST', permission=permission)
        for status in ['kontaktowany', 'zainteresowany', 'klient']: self.store.review(id_, status, 'Ręczny stan testowy, żadnej wysyłki')
        self.assertEqual(self.store.get(id_)['status'],'klient')
        b = self.add(1); self.store.review(b,'odrzucony','Test odrzucenia'); self.store.review(b,'do_weryfikacji','Ponowna weryfikacja')
        self.assertEqual(self.store.get(b)['status'],'do_weryfikacji')

    def test_import_cannot_approve_or_set_permission(self):
        for key in ['status','contact_permission','assessment','secret']:
            r=sample();r[key]='nie importuj'
            with self.assertRaises(ValueError):self.store.ingest([r])
        with self.assertRaises(ValueError):self.store.search(industry='unknown')

    def test_stale_permission_cannot_enable_contact(self):
        id_=self.add();self.approve(id_)
        permission={'source_url':'https://example.invalid/permission','verified_at':(TODAY-dt.timedelta(days=181)).isoformat(),'note':'Nieaktualna podstawa testowa'}
        with self.assertRaises(ValueError):self.store.review(id_,'kontakt_dozwolony','Stare',permission=permission)
        self.assertEqual(self.store.get(id_)['status'],'zaakceptowany')

    def test_cli_end_to_end_and_no_demo_published(self):
        db = self.path/'cli.sqlite3'
        def cli(*args):
            return subprocess.run([sys.executable,str(ROOT/'finder.py'),'--db',str(db),*args],capture_output=True,text=True)
        result = cli('find','--input',str(ROOT/'fixtures/companies.json'))
        self.assertEqual(result.returncode,0,result.stderr)
        out = self.path/'cli-export.json'
        self.assertEqual(cli('export','--output',str(out)).returncode,0)
        self.assertEqual(len(f.load_json(out)['records']),4)
        self.assertEqual(cli('review','1','--status','do_weryfikacji','--reason','TEST').returncode,0)
        self.assertEqual(cli('review','1','--status','zaakceptowany','--reason','TEST').returncode,0)
        draft = self.path/'draft.json'
        self.assertEqual(cli('demo-input','1','--output',str(draft)).returncode,0)
        self.assertIn('branza',f.load_json(draft))
        self.assertFalse((self.path/'index.html').exists())
        self.assertEqual(cli('find','--input',str(ROOT/'fixtures/companies.json'),'--industry','unknown').returncode,1)


if __name__ == '__main__': unittest.main()
