import argparse
import base64
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import finder as f
import cloud_runner as c

TEST_KEY='1a'*32 # Synthetic test secret, never used for real results.


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='webforge-cloud-tests-');self.path=Path(self.tmp.name)
        # No real runner secrets or summary destination are inherited by fixtures.
        self.env=patch.dict(os.environ,{'PROSPECT_DATA_KEY':'','PROSPECT_STATE_TOKEN':'','GITHUB_STEP_SUMMARY':str(self.path/'test-only-summary.md')})
        self.env.start();self.addCleanup(self.env.stop)
    def tearDown(self):self.tmp.cleanup()
    def args(self,**kwargs):
        values=dict(region='poznan',industry='all',limit=25,category='wszystkie',storage='temporary',state_repository='',workdir=str(self.path/'work'),output=str(self.path/'output'));values.update(kwargs);return argparse.Namespace(**values)

    def test_workflow_json_is_valid_yaml_subset_dispatch_only_and_scoped(self):
        template=ROOT/'workflow/prospect-finder.yml';w=json.loads(template.read_text())
        installed=ROOT.parent/'.github/workflows/prospect-finder.yml'
        if installed.exists():self.assertEqual(installed.read_text(),template.read_text())
        self.assertEqual(set(w['on']),{'workflow_dispatch'});self.assertEqual(w['permissions'],{'contents':'read'})
        inputs=w['on']['workflow_dispatch']['inputs'];self.assertEqual(inputs['limit']['default'],25)
        self.assertIn('region',inputs);self.assertIn('industry',inputs);self.assertIn('storage',inputs)
        job=w['jobs']['discover'];self.assertNotIn('self-hosted',job['runs-on']);self.assertLessEqual(job['timeout-minutes'],30)
        self.assertIn('github.event.repository.private',job['if']);self.assertFalse(w['concurrency']['cancel-in-progress'])
        steps=job['steps'];checkout=steps[0]
        self.assertEqual(checkout['with']['repository'],c.SOURCE_REPO);self.assertEqual(checkout['with']['ref'],'feature/demo-generator');self.assertFalse(checkout['with']['persist-credentials'])
        for step in steps:
            if 'uses' in step:self.assertRegex(step['uses'],r'@[a-f0-9]{40}$')
            if 'run' in step:self.assertNotIn('${{',step['run']);self.assertNotIn('git push',step['run'])
        upload=next(s for s in steps if s.get('uses','').startswith('actions/upload-artifact@'));self.assertEqual(upload['with']['retention-days'],1);self.assertTrue(upload['with']['path'].endswith('/results.tar.gpg'))
        self.assertIn('workflow_incomplete',steps[-1]['run'])
        test_step=next(s for s in steps if s['name']=='Run offline tests')
        self.assertTrue(test_step['run'].startswith('GITHUB_STEP_SUMMARY= '))
        self.assertNotIn('cache',json.dumps(w).lower());self.assertFalse(f.config('cloud')['future_schedule']['enabled'])

    def test_invalid_key_and_params_fail_before_discovery(self):
        called=[]
        with patch.dict(os.environ,{'PROSPECT_DATA_KEY':''}),redirect_stdout(io.StringIO()):
            result=c.run_cloud(self.args(),discover=lambda *a,**kw:called.append(1))
        self.assertEqual(result,1);self.assertEqual(called,[])
        summary=f.load_json(self.path/'output/summary.json');self.assertIsNone(summary['real_companies_found']);self.assertIn('preflight_failed',summary['errors'])

    def test_summary_never_copies_record_names_urls_errors_or_ids(self):
        raw={'outcome':'completed','real_companies_found':25,'new_records':20,'duplicate_records':5,'with_website':18,'potential_modernizations':4,'error':'SECRET TEST mail@example.invalid','top_scores':[{'id':1,'name':'NIE PUBLIKUJ','score':45,'coverage_percent':50}],'outcomes':{'network_error':2}}
        safe=c.public_summary(raw,'temporary',False,[]);text=json.dumps(safe)
        for hidden in ['SECRET','mail@','NIE PUBLIKUJ','"id"']:self.assertNotIn(hidden,text)
        self.assertEqual(safe['new_records'],20);self.assertIn('45/100',c.markdown(safe))
        unsafe=c.public_summary({'new_records':'PRIVATE','outcomes':{'PRIVATE':1},'top_scores':[{'score':'PRIVATE','coverage_percent':0}]},'temporary',False,['PRIVATE'])
        self.assertNotIn('PRIVATE',json.dumps(unsafe))

    def test_diagnostics_allow_only_categories_and_numbers(self):
        secret='PRIVATE company test@example.invalid https://secret.invalid TOKEN'
        raw={'diagnostics':{'failure':'http_5xx','query':{'clauses':8,'query_bytes':1000,'secret':secret},'events':[{'scope':'overpass','event':'response','category':'http_5xx','http_status':504,'attempt':3,'elapsed_ms':25000,'response_bytes':100,'body':secret,'headers':secret},{'scope':'website','event':'error','category':secret,'elapsed_ms':secret},{'scope':secret,'event':'error'}]}}
        safe=c.public_summary(raw,'temporary',False,['discovery_blocked_or_failed']);encoded=json.dumps(safe)
        self.assertNotIn(secret,encoded);self.assertNotIn('secret.invalid',c.markdown(safe));self.assertIn('504',c.markdown(safe))
        self.assertEqual(safe['diagnostics']['failure'],'http_5xx');self.assertEqual(len(safe['diagnostics']['events']),2)
        from network import safe_diagnostics
        self.assertEqual(safe_diagnostics({'failure':[], 'events':[{'scope':'website','event':'error','category':{}}]})['events'][0]['category'],'network_other')

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_synthetic_run_cannot_write_inherited_production_step_summary(self):
        production=self.path/'production-summary.md';production.write_text('REAL RUN ONLY\n')
        def synthetic(*a,**kw):return {'outcome':'completed','real_companies_found':1,'new_records':1,'duplicate_records':0}
        with patch.dict(os.environ,{'PROSPECT_DATA_KEY':TEST_KEY,'GITHUB_STEP_SUMMARY':str(production)}),redirect_stdout(io.StringIO()):
            self.assertEqual(c.run_cloud(self.args(),discover=synthetic),0)
        self.assertEqual(production.read_text(),'REAL RUN ONLY\n')
        self.assertEqual(f.load_json(self.path/'output/summary.json')['real_companies_found'],1)

    def test_only_cli_explicitly_selects_github_summary_sink(self):
        sink=str(self.path/'cli-test-summary.md')
        with patch.dict(os.environ,{'GITHUB_STEP_SUMMARY':sink}),patch.object(c,'run_cloud',return_value=1) as run:
            self.assertEqual(c.main(['run','--workdir',str(self.path/'w'),'--output',str(self.path/'o')]),1)
        self.assertEqual(run.call_args.kwargs,{'summary_path':sink})

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_failed_production_summary_has_no_synthetic_completed_result(self):
        sink=self.path/'isolated-production.md'
        failed={'outcome':'blocked_or_failed','real_companies_found':0,'new_records':0,'duplicate_records':0,'network_requests':3,'diagnostics':{'failure':'http_5xx','events':[{'scope':'overpass','event':'response','category':'http_5xx','http_status':504,'attempt':3}]}}
        with patch.dict(os.environ,{'PROSPECT_DATA_KEY':TEST_KEY}),redirect_stdout(io.StringIO()):
            self.assertEqual(c.run_cloud(self.args(),discover=lambda *a,**kw:failed,summary_path=sink),1)
        text=sink.read_text();self.assertEqual(text.count('# WebForge'),1);self.assertNotIn('`completed`',text);self.assertIn('| Znalezione firmy | 0 |',text);self.assertIn('http_5xx',text);self.assertIn('504',text)

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_encryption_roundtrip_and_wrong_key(self):
        plain=self.path/'private.txt';plain.write_text('FIKCYJNY PRYWATNY REKORD test@example.invalid')
        encrypted=self.path/'encrypted.gpg';c.crypt(plain,encrypted,TEST_KEY)
        self.assertNotIn(b'example.invalid',encrypted.read_bytes())
        with self.assertRaises(ValueError):c.crypt(encrypted,self.path/'wrong.txt','2b'*32,decrypt=True)
        self.assertFalse((self.path/'wrong.txt').exists())
        output=self.path/'restored.txt';c.crypt(encrypted,output,TEST_KEY,decrypt=True);self.assertEqual(plain.read_bytes(),output.read_bytes())

    def test_snapshot_restores_database_and_rate_cache_only(self):
        work=self.path/'state';work.mkdir();db=f.Store(work/'prospects.sqlite3')
        try:db.ingest([f.load_json(ROOT/'fixtures/companies.json')['records'][0]])
        finally:db.close()
        from network import HttpClient
        client=HttpClient(work/'live/network-cache.sqlite3');client._reserve('synthetic.example.invalid',False);client.close()
        (work/'extra.json').write_text('Nie odtwarzaj eksportu jako stan')
        archive=self.path/'state.tar.gz';c.archive_tree(work,archive,state_only=True)
        destination=self.path/'restored';c.restore_state(archive,destination)
        self.assertFalse((destination/'extra.json').exists());restored=f.Store(destination/'prospects.sqlite3')
        try:self.assertEqual(len(restored.search()),1)
        finally:restored.close()
        cache=sqlite3.connect(destination/'live/network-cache.sqlite3')
        try:self.assertEqual(cache.execute('SELECT count FROM limits').fetchone()[0],1)
        finally:cache.close()

    def test_restore_rejects_traversal_symlinks_and_duplicate_paths(self):
        for index,names in enumerate([['../prospects.sqlite3'],['prospects.sqlite3','prospects.sqlite3'],['unwanted.txt']]):
            archive=self.path/f'bad-{index}.tar.gz'
            with tarfile.open(archive,'w:gz') as stream:
                for name in names:
                    item=tarfile.TarInfo(name);item.size=1;stream.addfile(item,io.BytesIO(b'x'))
            with self.assertRaises(ValueError):c.restore_state(archive,self.path/f'out-{index}')

    def test_state_repository_must_be_private_and_separate(self):
        for name in ['Yormiii/Moja-strona','bad','owner/public']:
            with self.assertRaises(ValueError):c.PrivateRepositoryState(name,'TEST_TOKEN',api=lambda *a:{'private':False,'default_branch':'main'})

    def test_private_state_api_sha_lease_and_publicity_recheck(self):
        calls=[];private=[True]
        def api(path,token,method='GET',payload=None):
            calls.append((path,method,payload))
            if path=='/repos/owner/private':return {'private':private[0],'default_branch':'main'}
            if method=='PUT':return {'content':{'sha':'new'}}
            return None
        state=c.PrivateRepositoryState('owner/private','TEST_TOKEN',api)
        self.assertFalse(state.load(self.path/'absent.gpg'))
        source=self.path/'state.gpg';source.write_bytes(b'FIKCYJNY CIPHER')
        state.sha='old-sha';state.save(source);self.assertEqual(calls[-1][2]['sha'],'old-sha')
        private[0]=False
        with self.assertRaises(ValueError):state.save(source)

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_cloud_offline_synthetic_run_encrypts_no_raw_artifacts(self):
        def discover(store,**kwargs):
            self.assertEqual(kwargs['limit'],25);store.ingest([f.load_json(ROOT/'fixtures/companies.json')['records'][0]])
            return {'outcome':'completed','real_companies_found':1,'new_records':1,'duplicate_records':0,'with_website':0,'potential_modernizations':0,'top_scores':[]}
        with patch.dict(os.environ,{'PROSPECT_DATA_KEY':TEST_KEY}),redirect_stdout(io.StringIO()):result=c.run_cloud(self.args(),discover=discover)
        self.assertEqual(result,0);files={p.name for p in (self.path/'output').iterdir()}
        self.assertEqual(files,{'results.tar.gpg','summary.json','summary.md'})
        self.assertNotIn('TEST', (self.path/'output/summary.md').read_text())

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_failed_discovery_produces_honest_counts_and_encrypted_recovery(self):
        with patch.dict(os.environ,{'PROSPECT_DATA_KEY':TEST_KEY}),redirect_stdout(io.StringIO()):
            result=c.run_cloud(self.args(),discover=lambda *a,**k:{'outcome':'blocked_or_failed','real_companies_found':0,'new_records':0,'duplicate_records':0,'error':'PRIVATE URL https://example.invalid/'})
        summary=f.load_json(self.path/'output/summary.json');self.assertEqual(result,1);self.assertEqual(summary['real_companies_found'],0);self.assertNotIn('PRIVATE URL',json.dumps(summary));self.assertTrue((self.path/'output/results.tar.gpg').exists())

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_private_repository_restores_sqlite_and_dedup_across_runs(self):
        memory={};state_type=c.PrivateRepositoryState
        def api(path,token,method='GET',payload=None):
            if path=='/repos/owner/private':return {'private':True,'default_branch':'main'}
            if '/git/blobs/' in path:return {'encoding':'base64','content':base64.b64encode(memory['bytes']).decode()}
            if method=='PUT':
                self.assertEqual(payload.get('sha'),memory.get('sha'));memory['bytes']=base64.b64decode(payload['content']);memory['sha']='synthetic-sha';return {'content':{'sha':memory['sha']}}
            if 'bytes' in memory:return {'type':'file','size':len(memory['bytes']),'sha':memory['sha']}
            return None
        def discover(store,**kwargs):
            before=len(store.search());store.ingest([f.load_json(ROOT/'fixtures/companies.json')['records'][0]])
            return {'outcome':'completed','real_companies_found':1,'new_records':int(before==0),'duplicate_records':int(before>0),'top_scores':[]}
        for n in (1,2):
            args=self.args(storage='private-repository',state_repository='owner/private',workdir=str(self.path/f'work-{n}'),output=str(self.path/f'out-{n}'))
            with patch.dict(os.environ,{'PROSPECT_DATA_KEY':TEST_KEY,'PROSPECT_STATE_TOKEN':'SYNTHETIC_TEST_TOKEN'}),patch.object(c,'PrivateRepositoryState',side_effect=lambda *a:state_type('owner/private','SYNTHETIC_TEST_TOKEN',api)),redirect_stdout(io.StringIO()):
                self.assertEqual(c.run_cloud(args,discover=discover),0)
            summary=f.load_json(self.path/f'out-{n}/summary.json')
            self.assertEqual(summary['state_restored'],n==2);self.assertEqual(summary['new_records'],int(n==1));self.assertEqual(summary['duplicate_records'],int(n==2))


if __name__=='__main__':unittest.main()
