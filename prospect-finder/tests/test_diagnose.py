"""All responses are synthetic. Never count probes as actual prospects."""
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import sys
import tempfile
import unittest
import http.client
import urllib.request
from contextlib import redirect_stdout
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cloud_runner as c
import diagnose as d
import finder as f
import network as n


def resolver(host,port,**kwargs):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',port))]
def count_body(count=0):return json.dumps({'elements':[{'type':'count','tags':{'total':str(count)}}]}).encode()


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='webforge-diagnostic-tests-');self.path=Path(self.tmp.name);self.clients=[];self.now=1800000000.0
        self.env=patch.dict(os.environ,{'PROSPECT_DATA_KEY':'','PROSPECT_STATE_TOKEN':'','GITHUB_STEP_SUMMARY':str(self.path/'inherited-summary')});self.env.start();self.addCleanup(self.env.stop)
    def tearDown(self):
        for client in self.clients:client.close()
        self.tmp.cleanup()
    def sleep(self,seconds):self.now+=seconds
    def client(self,wire=None,instance='overpass-de',**overrides):
        cfg=d.diagnostic_settings(instance,instance=='private-coffee');cfg.update(overrides)
        if wire is None:wire=lambda url,*args:n.Response(200,{},b'PRIVATE STATUS IP' if url.endswith('/status') else count_body(2),self.now)
        client=n.HttpClient(self.path/'network-cache.sqlite3',settings=cfg,wire=wire,resolver=resolver,clock=lambda:self.now,sleep=self.sleep);self.clients.append(client);return client

    def test_queries_are_tiny_count_only_and_one_industry_2km(self):
        tiny,small=d.probe_queries()
        self.assertIn('node(1);out count;',tiny);self.assertIn('around:2000,52.4064,16.9252',small)
        self.assertEqual(small.count('nwr('),1);self.assertIn('["shop"="car_repair"]',small)
        for query in (tiny,small):
            self.assertIn('[timeout:5]',query);self.assertTrue(query.endswith('out count;'));self.assertNotIn('out meta',query);self.assertLess(len(query),300)
        with self.assertRaises(ValueError):d.probe_queries(industry='all')

    def test_all_three_checks_independent_no_real_company_counts_or_raw_status(self):
        client=self.client();report=d.diagnose_run(client)
        self.assertEqual(report['outcome'],'completed');self.assertEqual(client.requests,3)
        self.assertEqual([p['name'] for p in report['probes']],list(d.PROBES));self.assertEqual(report['probes'][2]['matched_osm_objects'],2)
        safe=c.public_summary(report,'temporary',False,[]);text=c.markdown(safe)
        self.assertIsNone(safe['real_companies_found']);self.assertNotIn('PRIVATE',text);self.assertIn('obiekty OSM',text);self.assertNotIn('| Znalezione firmy |',text)
        report['real_companies_found']=99;report['new_records']=99
        safe=c.public_summary(report,'temporary',False,[]);self.assertIsNone(safe['real_companies_found']);self.assertIsNone(safe['new_records'])

    def test_zero_objects_is_valid_probe_not_absent_company_claim(self):
        self.assertEqual(d.parse_count(n.Response(200,{},count_body(0),self.now)),0)
        for bad in [{'elements':[]},{'elements':[{'type':'node','name':'PRIVATE'}]},{'elements':[{'type':'count','tags':{'total':'PRIVATE CONTACT'}}]}]:
            with self.assertRaises(n.NetworkError):d.parse_count(n.Response(200,{},json.dumps(bad).encode(),self.now))

    def test_connect_read_and_server_execution_timeout_are_distinct(self):
        calls=[]
        def wire(url,*args):
            calls.append(url)
            if len(calls)==1:raise n.NetworkError('PRIVATE connect',category='connect_timeout')
            if len(calls)==2:raise n.NetworkError('PRIVATE read',category='read_timeout')
            return n.Response(200,{},b'{"remark":"Query timed out PRIVATE","elements":[]}',self.now)
        report=d.diagnose_run(self.client(wire))
        self.assertEqual([p['category'] for p in report['probes']],['connect_timeout','read_timeout','overpass_timeout'])
        self.assertEqual(report['network_requests'],3);self.assertNotIn('PRIVATE',json.dumps(report))

    def test_429_and_access_denial_stop_following_queries_without_failover(self):
        for status in (429,403,407,451):
            client=self.client(lambda *a:n.Response(status,{'retry-after':'3600'},b'PRIVATE',self.now))
            report=d.diagnose_run(client)
            self.assertEqual(client.requests,1);self.assertEqual([p['outcome'] for p in report['probes']],['failed','skipped','skipped'])
            self.assertEqual(report['instance'],'overpass-de');self.now+=86401

    def test_status_endpoint_failure_does_not_prevent_independent_query_check(self):
        client=self.client(lambda url,*args:n.Response(404 if url.endswith('/status') else 200,{},count_body(),self.now))
        report=d.diagnose_run(client)
        self.assertEqual([p['outcome'] for p in report['probes']],['failed','passed','passed'])

    def test_warm_probe_cache_is_reported_and_shares_existing_budget(self):
        client=self.client();d.diagnose_run(client);client.requests=0
        report=d.diagnose_run(client)
        self.assertEqual(client.requests,0);self.assertEqual(report['cache_hits'],3)
        self.assertTrue(all(p['events'][0]['event']=='cache' for p in report['probes']))

    def test_manual_instance_selection_requires_terms_and_rejects_arbitrary_url(self):
        self.assertFalse(f.config('overpass')['automatic_failover'])
        with self.assertRaises(ValueError):n.instance_settings('private-coffee')
        with self.assertRaises(ValueError):n.instance_settings('https://localhost/')
        selected=n.instance_settings('private-coffee',True)
        self.assertEqual(selected['overpass_endpoint'],'https://overpass.private.coffee/api/interpreter')
        called=[]
        client=self.client(lambda url,*a:(called.append(url) or n.Response(200,{},b'OK' if url.endswith('/status') else count_body(),self.now)),instance='private-coffee')
        d.diagnose_run(client,instance='private-coffee');self.assertEqual(len(called),3);self.assertTrue(all(url.startswith('https://overpass.private.coffee/') for url in called))

    def test_global_overpass_budget_and_long_retry_after_survive_instance_change(self):
        client=self.client(overpass_requests_per_day=1)
        client.request(client.cfg['overpass_endpoint'],method='POST',data=b'data=x',overpass=True)
        other=self.client(instance='private-coffee',overpass_requests_per_day=1)
        with self.assertRaises(n.BudgetExceeded):other.request(other.cfg['overpass_endpoint'],method='POST',data=b'data=x',overpass=True)
        self.now+=86401;client.defer('overpass-api.de',3600)
        with self.assertRaises(n.BudgetExceeded):other.request(other.cfg['overpass_endpoint'],method='POST',data=b'data=y',overpass=True)

    def test_socket_connection_timeout_is_tagged_before_read(self):
        for cls,base in [(n.PhaseHTTPConnection,http.client.HTTPConnection),(n.PhaseHTTPSConnection,http.client.HTTPSConnection)]:
            connection=cls('example.invalid',timeout=35,connect_timeout=8)
            self.assertEqual(connection.timeout,8)
            with patch.object(base,'connect',side_effect=TimeoutError('PRIVATE HOST')):
                with self.assertRaises(n.NetworkError) as caught:connection.connect()
            self.assertEqual(caught.exception.category,'connect_timeout')

    def test_actual_urllib_path_uses_instrumented_connections_without_network(self):
        for scheme,base in [('http',http.client.HTTPConnection),('https',http.client.HTTPSConnection)]:
            with patch.object(base,'connect',side_effect=TimeoutError('PRIVATE synthetic')):
                with self.assertRaises(n.NetworkError) as caught:n.transport(scheme+'://example.invalid/','GET',None,{},15,1024)
            self.assertEqual(caught.exception.category,'connect_timeout')

    def test_safe_diagnostic_output_drops_unknown_fields_and_secret_endpoints(self):
        raw={'mode':'diagnose','instance':['PRIVATE'],'probes':[{'name':'minimal_query','outcome':'passed','http_status':200,'matched_osm_objects':False,'secret':'PRIVATE URL CONTACT','events':[{'scope':'overpass','event':'error','category':'read_timeout','body':'PRIVATE','url':'PRIVATE'}]}]}
        safe=c.public_summary(raw,'temporary',False,[])
        self.assertNotIn('PRIVATE',json.dumps(safe));self.assertNotIn('matched_osm_objects',safe['probes'][0])

    def test_diagnostic_does_not_weaken_url_guards_or_unsafe_post_block(self):
        calls=[];client=self.client(lambda *a:calls.append(a))
        for target,kwargs in [('http://localhost/',{}),('https://webforge.com.pl/',{}),('https://example.invalid/',{'method':'POST','data':b'x','overpass':True})]:
            with self.assertRaises(n.NetworkError):client.request(target,**kwargs)
        self.assertEqual(calls,[])

    def test_connected_socket_uses_read_timeout_and_headers_are_read_phase(self):
        connection=n.PhaseHTTPConnection('example.invalid',timeout=15,connect_timeout=8);connection.sock=Mock()
        with patch.object(http.client.HTTPConnection,'connect'):connection.connect()
        connection.sock.settimeout.assert_called_with(15)
        with patch.object(http.client.HTTPConnection,'getresponse',side_effect=TimeoutError('PRIVATE headers')):
            with self.assertRaises(n.NetworkError) as caught:connection.getresponse()
        self.assertEqual(caught.exception.category,'read_timeout')
        with patch.object(http.client.HTTPConnection,'request',side_effect=TimeoutError('PRIVATE send')):
            with self.assertRaises(n.NetworkError) as caught:connection.request('POST','/',body=b'x')
        self.assertEqual(caught.exception.category,'write_timeout')

    def test_body_timeout_retains_http_status_and_tls_proxy_handlers_remain(self):
        response=Mock();response.status=200;response.headers={};response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.read.side_effect=TimeoutError('PRIVATE BODY')
        with patch('network.urllib.request.build_opener') as build:
            build.return_value.open.return_value=response
            with self.assertRaises(n.NetworkError) as caught:n.transport('https://example.invalid/','GET',None,{},15,1024)
        self.assertEqual(caught.exception.category,'read_timeout');self.assertEqual(caught.exception.http_status,200)
        https=n.PhaseHTTPSHandler(8);self.assertEqual(https._context.verify_mode,ssl.CERT_REQUIRED);self.assertTrue(https._context.check_hostname)
        opener=urllib.request.build_opener(n.NoRedirect(),n.PhaseHTTPHandler(8),https)
        self.assertTrue(any(isinstance(h,n.PhaseHTTPSHandler) for h in opener.handlers));self.assertTrue(any(isinstance(h,n.NoRedirect) for h in opener.handlers))

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_cloud_diagnostic_mode_does_not_invoke_discover_or_ingest_prospects(self):
        args=argparse.Namespace(region='poznan',industry='all',limit=25,category='wszystkie',storage='temporary',state_repository='',workdir=str(self.path/'work'),output=str(self.path/'output'),mode='diagnose',instance='overpass-de',accept_instance_terms=False)
        def make_client(path,settings):
            return n.HttpClient(path,settings=settings,wire=lambda url,*a:n.Response(200,{},b'PRIVATE IP' if url.endswith('/status') else count_body(23),self.now),resolver=resolver,clock=lambda:self.now,sleep=self.sleep)
        with patch.dict(os.environ,{'PROSPECT_DATA_KEY':'1a'*32}),patch.object(c,'HttpClient',side_effect=make_client),redirect_stdout(io.StringIO()):
            self.assertEqual(c.run_cloud(args,discover=lambda *a,**kw:self.fail('Full discovery must not run')),0)
        store=f.Store(self.path/'work/prospects.sqlite3')
        try:self.assertEqual(len(store.search()),0)
        finally:store.close()
        safe=f.load_json(self.path/'output/summary.json');self.assertEqual(safe['mode'],'diagnose');self.assertIsNone(safe['real_companies_found']);self.assertNotIn('PRIVATE',json.dumps(safe));self.assertFalse((self.path/'inherited-summary').exists())
        self.assertTrue((self.path/'output/results.tar.gpg').exists())

    def test_workflow_manual_controls_and_all_inputs_are_quoted_not_executable_code(self):
        workflow=json.loads((ROOT/'workflow/prospect-finder.yml').read_text());inputs=workflow['on']['workflow_dispatch']['inputs']
        self.assertEqual(inputs['mode']['options'],['diagnose','discover']);self.assertEqual(inputs['instance']['default'],'overpass-de');self.assertFalse(inputs['accept_instance_terms']['default'])
        step=next(s for s in workflow['jobs']['discover']['steps'] if s['name']=='Discover and encrypt private results')
        self.assertIn('--mode "$PF_MODE"',step['run']);self.assertIn('--instance "$PF_INSTANCE"',step['run']);self.assertNotIn('${{',step['run'])


if __name__=='__main__':unittest.main()
