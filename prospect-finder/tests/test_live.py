"""All network responses here are synthetic; no real company data in fixtures."""
import copy
import datetime as dt
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import finder as f
from network import HttpClient,Response,NetworkError,BudgetExceeded,public_url,transport
from live import build_query,region_config,classify,element_record,OverpassSource,SiteAuditor,PageSignals,discover_run


def resolver(host,port,**kwargs):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',port))]
class Clock:
    def __init__(self):self.now=dt.datetime.now(dt.timezone.utc).timestamp();self.waits=[]
    def __call__(self):return self.now
    def sleep(self,seconds):self.waits.append(seconds);self.now+=seconds


def element(id_=1,**tags):
    return {'id':id_,'type':'node','lat':52.4064,'lon':16.9252,'timestamp':'2020-01-01T00:00:00Z','tags':{'name':f'FIKCYJNA FIRMA TEST {id_}','shop':'car_repair','addr:city':'Poznań',**tags}}


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='webforge-live-tests-');self.path=Path(self.temp.name);self.clock=Clock();self.clients=[]
    def tearDown(self):
        for c in self.clients:c.close()
        self.temp.cleanup()
    def client(self,wire=None,**settings):
        if wire is None:wire=lambda *args:Response(200,{'content-type':'text/html'},b'<html></html>',self.clock())
        c=HttpClient(self.path/'cache.sqlite3',wire=wire,clock=self.clock,sleep=self.clock.sleep,resolver=resolver,settings=settings)
        self.clients.append(c);return c
    def record(self,website='https://company.example.invalid/'):
        return element_record(element(website=website),region_config('poznan'),dt.date.today().isoformat())

    def test_query_covers_all_thirty_bounded_and_region(self):
        q=build_query(region_config('poznan'))
        self.assertEqual(set(f.config('osm')['rules']),set(f.industries()));self.assertEqual(len(f.industries()),30)
        self.assertIn('[timeout:25]',q);self.assertIn('out meta center 1500',q);self.assertIn('around:30000,52.4064,16.9252',q)
        for groups in f.config('osm')['rules'].values():
            for group in groups:
                for c in group:self.assertIn(json.dumps(c['key']),q)
        with self.assertRaises(ValueError):build_query(region_config('poznan'),'no-such-industry')

    def test_specific_classification_before_broad(self):
        self.assertEqual(classify({'shop':'hairdresser','hairdresser':'barber'}),'barber')
        self.assertEqual(classify({'shop':'hairdresser'}),'fryzjer')
        self.assertEqual(classify({'tourism':'guest_house','name':'Agroturystyka TEST'}),'agroturystyka')
        self.assertIsNone(classify({'shop':'unknown'}))

    def test_same_name_branches_without_address_are_not_collapsed(self):
        a=element(101,name='FIKCYJNA SIEĆ TEST');b=element(102,name='FIKCYJNA SIEĆ TEST');b['lon']=16.94
        c=self.client(lambda *args:Response(200,{},json.dumps({'elements':[a,b]}).encode(),self.clock()))
        records=OverpassSource(c).search(limit=3);self.assertEqual(len(records),2)
        store=f.Store(self.path/'branches.sqlite3')
        try:self.assertEqual(len(set(store.ingest(records))),2)
        finally:store.close()

    def test_mapping_contacts_license_geo_not_activity(self):
        r=element_record(element(**{'contact:email':'test@example.invalid','contact:phone':'+48 000 000 000','website':'company.example.invalid'}),region_config('poznan'),dt.date.today().isoformat())
        self.assertFalse(r['fictional']);self.assertEqual(len(r['contacts']),2);self.assertEqual(r['website'],'https://company.example.invalid/')
        self.assertIn('/node/1',r['source']['url']);self.assertIn('OpenStreetMap',r['source_metadata']['attribution']);self.assertEqual(r['source_metadata']['license'],'ODbL-1.0');self.assertEqual(r['activity_signs'],[])

    def test_missing_website_tag_and_explicit_no_stay_unknown(self):
        for e in [element(),element(website='no')]:
            e['tags'].pop('addr:city',None);r=element_record(e,region_config('poznan'),dt.date.today().isoformat())
            self.assertIsNone(r['website']);self.assertEqual(r['facts']['website_status']['value'],'unknown');self.assertEqual(f.score(r)['score'],0);self.assertIn('Nieustalona',r['city'])

    def test_closed_private_and_outside_region_skipped(self):
        for e in [element(disused='yes'),element(access='private'),{**element(),'lat':50.0},element(name='')]:
            self.assertIsNone(element_record(e,region_config('poznan'),dt.date.today().isoformat()))

    def test_source_limit_fair_selection_and_remark_error(self):
        payload={'elements':[element(i) for i in range(1,5)]+[element(9,shop='hairdresser')]}
        def wire(*a):return Response(200,{},json.dumps(payload).encode(),self.clock())
        c=self.client(wire);source=OverpassSource(c);records=source.search(limit=3)
        self.assertEqual(len(records),3);self.assertEqual({r['industry'] for r in records},{'mechanik','fryzjer'})
        payload={'remark':'runtime error','elements':[]};self.clock.now+=86401
        with self.assertRaises(NetworkError):source.search(limit=3)

    def test_safe_url_blocks_private_loopback_credentials_and_scheme(self):
        for bad in ['file:///tmp/x','https://user:pass@example.invalid/','http://localhost/','http://169.254.169.254/','http://[::1]/','http://10.0.0.1/']:
            def actual_literal(host,port,**kw):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',(host,port))]
            with self.assertRaises(NetworkError):public_url(bad,actual_literal)
        self.assertEqual(public_url('https://example.invalid/',resolver),'https://example.invalid/')

    def test_cache_reuses_and_expires(self):
        calls=[]
        def wire(*args):calls.append(args);return Response(200,{},b'OK',self.clock())
        c=self.client(wire,cache_ttl_seconds=60);self.assertFalse(c.request('https://example.invalid/').cached)
        self.assertTrue(c.request('https://example.invalid/').cached);self.assertEqual(len(calls),1)
        self.clock.now+=61;c.request('https://example.invalid/');self.assertEqual(len(calls),2)

    def test_warm_cache_works_without_dns_and_long_retry_defers_whole_host(self):
        c=self.client();c.request('https://example.invalid/')
        c.resolver=lambda *a,**k:(_ for _ in ()).throw(OSError('TEST DNS failure'))
        self.assertTrue(c.request('https://example.invalid/').cached)
        c.resolver=resolver;c.wire=lambda *a:Response(429,{'retry-after':'3600'},b'',self.clock())
        with self.assertRaises(NetworkError):c.request('https://another.example.invalid/a')
        with self.assertRaises(BudgetExceeded):c.request('https://another.example.invalid/b')

    def test_host_interval_and_per_run_daily_persistent_limits(self):
        c=self.client(max_requests_per_run=2);c.request('https://example.invalid/a');c.request('https://example.invalid/b');self.assertTrue(any(v>=2 for v in self.clock.waits))
        with self.assertRaises(BudgetExceeded):c.request('https://example.invalid/c')
        c2=self.client(max_requests_per_day=2)
        with self.assertRaises(BudgetExceeded):c2.request('https://another.example.invalid/')

    def test_retry_with_delay_and_long_retry_after_not_ignored(self):
        calls=[]
        def wire(*args):
            calls.append(args);return Response(429 if len(calls)==1 else 200,{'retry-after':'3'},b'x',self.clock())
        c=self.client(wire);self.assertEqual(c.request('https://example.invalid/').status,200);self.assertEqual(len(calls),2);self.assertTrue(any(v>=3 for v in self.clock.waits))
        def long(*args):return Response(429,{'retry-after':'3600'},b'x',self.clock())
        c.wire=long
        with self.assertRaises(NetworkError):c.request('https://example.invalid/long')
        before=c.requests;self.clock.now+=301;self.assertEqual(c.request('https://example.invalid/long').status,429);self.assertEqual(c.requests,before)

    def test_retry_io_errors_and_download_budget(self):
        calls=[]
        def fail(*args):calls.append(1);raise OSError('TEST simulated blocked network')
        c=self.client(fail,max_attempts=2)
        with self.assertRaises(NetworkError):c.request('https://example.invalid/')
        self.assertEqual(len(calls),2)
        c2=self.client(max_download_bytes_per_day=1)
        with self.assertRaises(BudgetExceeded):c2.request('https://other.example.invalid/')

    def test_protected_host_and_unsafe_post_never_sent(self):
        calls=[];c=self.client(lambda *a:calls.append(a))
        for target,kwargs in [('https://webforge.com.pl/',{}),('https://example.invalid/',{'method':'POST','data':b'x'})]:
            with self.assertRaises(NetworkError):c.request(target,**kwargs)
        self.assertEqual(calls,[])

    def test_transport_rejects_oversized_and_compressed_bodies(self):
        class Fake:
            status=200
            def __init__(self,headers,body):self.headers=headers;self.body=body
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return self.body[:n]
        for response in [Fake({'Content-Length':'100'},b'x'),Fake({},b'x'*11),Fake({'Content-Encoding':'gzip'},b'x')]:
            with patch('network.urllib.request.build_opener') as build:
                build.return_value.open.return_value=response
                with self.assertRaises(NetworkError):transport('https://example.invalid/','GET',None,{},2,10)

    def site_client(self,html=b'<html></html>',status=200,robots=b'',redirect=None):
        calls=[]
        def wire(target,*args):
            calls.append(target)
            if target.endswith('/robots.txt'):return Response(200 if robots else 404,{},robots,self.clock())
            if redirect:return Response(302,{'location':redirect},b'',self.clock())
            return Response(status,{'content-type':'text/html'},html,self.clock())
        return self.client(wire),calls

    def test_robots_disallow_home_not_requested(self):
        c,calls=self.site_client(robots=b'User-agent: *\nDisallow: /\n')
        r=SiteAuditor(c).audit(self.record());self.assertEqual(r['site_check']['outcome'],'robots_disallowed');self.assertEqual(len(calls),1);self.assertNotIn('technical_issues',r['facts'])

    def test_crawl_delay_respected_and_long_delay_never_bypassed(self):
        c,calls=self.site_client(robots=b'User-agent: *\nCrawl-delay: 8\n');SiteAuditor(c).audit(self.record());self.assertTrue(any(x>=8 for x in self.clock.waits))
        c2,calls2=self.site_client(robots=b'User-agent: *\nCrawl-delay: 120\n');auditor=SiteAuditor(c2)
        for path in ['a','b']:self.assertEqual(auditor.audit(self.record('https://other.example.invalid/'+path))['site_check']['outcome'],'network_error')
        self.assertTrue(all(u.endswith('/robots.txt') for u in calls2))

    def test_html_old_technology_and_no_domain_age_logic(self):
        c,calls=self.site_client(html=b'<html><frameset></frameset></html>');r=SiteAuditor(c).audit(self.record())
        self.assertTrue(r['facts']['outdated']['value']);self.assertNotIn('mobile_issues',r['facts']);self.assertEqual(r['activity_signs'],[])
        self.assertTrue(f.matches(r,category='modernizacja'));self.assertEqual(len(calls),2)

    def test_viewport_missing_is_hint_not_scored_mobile_issue(self):
        c,_=self.site_client();r=SiteAuditor(c).audit(self.record());self.assertEqual(r['site_check']['outcome'],'reachable')
        self.assertIn('viewport_not_detected',[s['code'] for s in r['site_check']['signals']]);self.assertNotIn('mobile_issues',r['facts']);self.assertEqual(f.score(r)['score'],0)

    def test_http_error_is_not_missing_site_and_access_denied_unknown(self):
        c,_=self.site_client(status=404);r=SiteAuditor(c).audit(self.record());self.assertTrue(r['facts']['technical_issues']['value']);self.assertEqual(r['facts']['website_status']['value'],'present')
        c2,_=self.site_client(status=403);r2=SiteAuditor(c2).audit(self.record('https://other.example.invalid/'));self.assertEqual(r2['site_check']['outcome'],'access_limited');self.assertNotIn('technical_issues',r2['facts'])

    def test_redirect_private_never_reached_and_robots_checked_cross_host(self):
        c,calls=self.site_client(redirect='http://localhost/');r=SiteAuditor(c).audit(self.record());self.assertEqual(r['site_check']['outcome'],'network_error');self.assertFalse(any('localhost' in x for x in calls))

    def test_failed_network_and_no_url_no_false_issues(self):
        c=self.client(lambda *a:(_ for _ in ()).throw(OSError('TEST network failure')),max_attempts=1)
        r=SiteAuditor(c).audit(self.record());self.assertEqual(r['site_check']['outcome'],'network_error');self.assertNotIn('technical_issues',r['facts'])
        r=self.record();r['website']=None;r['facts']['website_status']['value']='unknown';out=SiteAuditor(c).audit(r);self.assertEqual(out['site_check']['outcome'],'no_url')

    def test_discover_end_to_end_private_and_blocked_run(self):
        payload={'elements':[element(i,website=f'https://test-{i}.example.invalid/') for i in range(1,4)]}
        def wire(target,*a):
            if target.endswith('/api/interpreter'):return Response(200,{},json.dumps(payload).encode(),self.clock())
            if target.endswith('/robots.txt'):return Response(404,{},b'',self.clock())
            return Response(200,{'content-type':'text/html'},b'<html></html>',self.clock())
        c=self.client(wire);store=f.Store(self.path/'data.sqlite3')
        try:
            report=discover_run(store,limit=3,workdir=self.path/'private',client=c)
            self.assertEqual(report['real_companies_found'],3);self.assertEqual(report['stored_unique_records'],3);self.assertEqual(len(f.load_json(report['json_export'])['records']),3)
            self.assertTrue(all(r['status']=='znaleziony' for r in store.search()))
            before=c.requests;again=discover_run(store,limit=3,workdir=self.path/'private',client=c);self.assertEqual(again['stored_unique_records'],3);self.assertEqual(c.requests,before)
            self.clock.now+=86401;c.wire=lambda *a:(_ for _ in ()).throw(OSError('TEST blocked'))
            blocked=discover_run(store,limit=3,workdir=self.path/'private',client=c);self.assertEqual(blocked['outcome'],'blocked_or_failed');self.assertEqual(blocked['real_companies_found'],0)
        finally:store.close()

    def test_artifact_paths_remain_outside_repo(self):
        with self.assertRaises(ValueError):HttpClient(ROOT/'cache.sqlite3',resolver=resolver)
        store=f.Store(self.path/'store.sqlite3')
        try:
            with self.assertRaises(ValueError):discover_run(store,workdir=ROOT/'data')
        finally:store.close()


if __name__=='__main__':unittest.main()
