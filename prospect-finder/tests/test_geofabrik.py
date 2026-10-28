"""Synthetic PBF envelopes only. No real companies or network in unit tests."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import struct
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import finder as f
import geofabrik as g
import cloud_runner as c


def resolver(host,port,**kwargs):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',port))]
def pbf(size=2048):
    header=b'\x0a\x09OSMHeader\x18\x10'
    return struct.pack('>I',len(header))+header+b'SYNTHETIC ONLY'.ljust(size-4-len(header),b'X')


class Response:
    def __init__(self,status,headers=None,body=b''):
        self.status=status;self.headers=headers or {};self.body=io.BytesIO(body);self.read_sizes=[]
    def __enter__(self):return self
    def __exit__(self,*a):self.close()
    def close(self):pass
    def read(self,size):
        if not 0<=size<=1048576:raise AssertionError('Unbounded read')
        self.read_sizes.append(size);return self.body.read(size)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='webforge-pbf-tests-');self.path=Path(self.temp.name);self.clients=[];self.now=1800000000.;self.calls=[];self.responses=[]
        self.env=patch.dict(os.environ,{'PROSPECT_DATA_KEY':'','PROSPECT_STATE_TOKEN':'','GITHUB_STEP_SUMMARY':str(self.path/'inherited-summary')});self.env.start();self.addCleanup(self.env.stop)
    def tearDown(self):
        for client in self.clients:client.close()
        self.temp.cleanup()
    def sleep(self,seconds):self.now+=seconds
    def client(self,wire,**settings):
        cfg={**f.config('geofabrik'),**settings}
        result=g.Downloader(self.path/'ledger.sqlite3',cfg=cfg,opener=wire,resolver=resolver,clock=lambda:self.now,sleep=self.sleep,monotonic=lambda:self.now);self.clients.append(result);return result
    def wire(self,body=None,**options):
        body=body or pbf()
        def opened(url,method,headers,timeout):
            self.calls.append((url,method,headers))
            if method=='HEAD':
                response=Response(200,{'Content-Length':str(options.get('size',len(body))),'ETag':'"synthetic-version"'})
            elif url.endswith('.md5'):
                digest=options.get('md5',hashlib.md5(body,usedforsecurity=False).hexdigest())
                response=Response(200,{},(digest+'  wielkopolskie-latest.osm.pbf\n').encode())
            elif headers.get('Range'):
                wanted=int(headers['Range'].split('-')[-1])+1
                response=Response(options.get('range_status',206),{'Content-Range':f'bytes 0-{wanted-1}/{len(body)}','Content-Length':str(wanted)},body[:wanted])
            else:response=Response(options.get('status',200),{'Content-Length':str(len(body))},body)
            self.responses.append(response);return response
        return opened
    def run_source(self,client,profile='wielkopolskie-full'):
        return g.source_test_run(self.path/'ledger.sqlite3',self.path/'cache',profile=profile,downloader=client)

    def test_full_stream_checksum_resource_report_and_cache_reuse(self):
        body=pbf(3*1048576+1);client=self.client(self.wire(body))
        report=self.run_source(client)
        self.assertEqual(report['outcome'],'completed');self.assertTrue(report['checksum_verified']);self.assertTrue(report['pbf_header_valid'])
        self.assertEqual(report['downloaded_bytes'],len(body));self.assertEqual(report['sha256'],hashlib.sha256(body).hexdigest())
        self.assertGreater(report['rss_peak_bytes'],0);self.assertFalse(report['import_executed']);self.assertEqual(report['buffer_bytes'],1048576)
        self.assertEqual((self.path/'cache/wielkopolskie.osm.pbf').stat().st_size,len(body))
        self.assertTrue(all(max(r.read_sizes or [0])<=1048576 for r in self.responses))
        before=len(self.calls);again=self.run_source(self.client(self.wire(body)))
        self.assertTrue(again['cache_used']);self.assertEqual(again['downloaded_bytes'],0);self.assertEqual(len(self.calls)-before,2)

    def test_sample_uses_range_and_does_not_claim_complete_integrity(self):
        body=pbf(2*1048576);report=self.run_source(self.client(self.wire(body)),profile='wielkopolskie-sample')
        self.assertEqual(report['outcome'],'completed');self.assertEqual(report['file_size_bytes'],len(body));self.assertEqual(report['downloaded_bytes'],1048576)
        self.assertTrue(report['pbf_header_valid']);self.assertFalse(report['checksum_verified']);self.assertFalse((self.path/'cache/wielkopolskie.osm.pbf').exists());self.assertFalse((self.path/'cache/wielkopolskie.part').exists())
        self.assertEqual(len(self.calls),2);self.assertEqual(self.calls[-1][2]['Range'],'bytes=0-1048575')

    def test_ignored_range_never_falls_back_to_full_download(self):
        report=self.run_source(self.client(self.wire(pbf(2*1048576),range_status=200)),profile='wielkopolskie-sample')
        self.assertEqual(report['failure'],'range_not_supported');self.assertEqual(self.responses[-1].read_sizes,[]);self.assertEqual(report['bytes_received'],0)

    def test_checksum_mismatch_discards_partial_file(self):
        report=self.run_source(self.client(self.wire(md5='0'*32)))
        self.assertEqual(report['failure'],'checksum_mismatch');self.assertFalse(report['checksum_verified']);self.assertFalse((self.path/'cache/wielkopolskie.osm.pbf').exists());self.assertFalse((self.path/'cache/wielkopolskie.part').exists())

    def test_html_and_invalid_protobuf_header_are_not_pbf(self):
        for bad in [b'<html>PRIVATE</html>',b'\x00\x01\x00\x01',struct.pack('>I',4)+b'xxxx',struct.pack('>I',12)+b'\x0a\x09OSMHeader']:
            self.assertFalse(g.pbf_header_valid(bad))
        report=self.run_source(self.client(self.wire(body=b'<html>NOT PBF</html>')))
        self.assertEqual(report['failure'],'invalid_pbf_header');self.assertFalse(report['checksum_verified'])

    def test_unapproved_dataset_urls_localhost_downgrade_and_large_file_rejected(self):
        for bad in ['http://download.geofabrik.de/europe/poland/wielkopolskie-latest.osm.pbf','https://localhost/x','https://download.geofabrik.de/europe/poland-latest.osm.pbf','https://download.geofabrik.de/europe/poland/wielkopolskie-latest.osm.pbf?token=PRIVATE']:
            with self.assertRaises(g.SourceError):g.allowed_url(bad,'wielkopolskie')
        with self.assertRaises(ValueError):g.profile_config('poland-full')
        report=self.run_source(self.client(self.wire(size=268435457)))
        self.assertEqual(report['failure'],'download_too_large');self.assertEqual(len(self.calls),1)

    def test_guarded_same_dataset_redirect_is_followed_but_external_is_not(self):
        base=self.wire()
        def redirect(url,method,headers,timeout):
            if url.endswith('latest.osm.pbf') and method=='HEAD':return Response(302,{'Location':'wielkopolskie-261027.osm.pbf'})
            return base(url,method,headers,timeout)
        report=self.run_source(self.client(redirect));self.assertEqual(report['outcome'],'completed')
        self.now+=86401
        report=self.run_source(self.client(lambda *a:Response(302,{'Location':'https://localhost/PRIVATE'})))
        self.assertEqual(report['failure'],'url_rejected')

    def test_budget_and_retry_after_persist_across_runs_and_midnight(self):
        client=self.client(lambda *a:Response(429,{'Retry-After':'3600'}));report=self.run_source(client)
        self.assertEqual(report['failure'],'http_429');self.assertEqual(report['network_requests'],1)
        again=self.run_source(self.client(self.wire()));self.assertEqual(again['failure'],'budget_exceeded');self.assertEqual(again['network_requests'],0)
        self.now+=86401
        small=self.run_source(self.client(self.wire(),max_bytes_per_day=100))
        self.assertEqual(small['failure'],'budget_exceeded')

    def test_disk_and_deadline_limits_and_metadata_validator(self):
        client=self.client(self.wire())
        with patch('geofabrik.shutil.disk_usage',return_value=type('Disk',(),{'free':0})()):report=self.run_source(client)
        self.assertEqual(report['failure'],'disk_space');self.assertEqual(len(self.calls),2)
        self.now+=86401;client=self.client(self.wire(),max_total_seconds=1);self.now+=2
        report=self.run_source(client);self.assertEqual(report['failure'],'download_deadline')
        self.now+=86401;report=self.run_source(self.client(self.wire(status=412)))
        self.assertEqual(report['failure'],'metadata_changed');self.assertEqual(self.calls[-1][2]['If-Match'],'"synthetic-version"')

    def test_head_304_reuses_metadata_and_cache_is_still_hash_checked(self):
        body=pbf();first=self.run_source(self.client(self.wire(body)));self.assertEqual(first['outcome'],'completed')
        base=self.wire(body)
        def wire(url,method,headers,timeout):
            if method=='HEAD':
                self.assertEqual(headers['If-None-Match'],'"synthetic-version"');return Response(304)
            return base(url,method,headers,timeout)
        self.assertTrue(self.run_source(self.client(wire))['cache_used'])
        (self.path/'cache/wielkopolskie.osm.pbf').write_bytes(b'X'*len(body))
        self.assertFalse(self.run_source(self.client(wire))['cache_used'])

    def test_safe_summary_copies_no_urls_headers_contacts_paths_or_error_text(self):
        raw={'mode':'geofabrik-test','profile':'wielkopolskie-sample','outcome':'completed','file_size_bytes':123,'real_companies_found':99,'name':'PRIVATE','url':'https://private.invalid/','ETag':'SECRET','error':'PRIVATE TOKEN','stages':[{'stage':'download','http_status':206,'category':'ok','header':'SECRET'}]}
        safe=c.public_summary(raw,'temporary',False,[]);text=json.dumps(safe)+c.markdown(safe)
        self.assertNotIn('PRIVATE',text);self.assertNotIn('SECRET',text);self.assertIsNone(safe['real_companies_found']);self.assertIsNone(safe['instance']);self.assertIn('file_size_bytes',text)

    def test_missing_length_or_private_dns_fails_before_file_download(self):
        report=self.run_source(self.client(lambda *a:Response(200,{})))
        self.assertEqual(report['failure'],'invalid_metadata');self.assertEqual(report['network_requests'],1)
        client=self.client(self.wire());client.resolver=lambda h,p,**kw:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',p))]
        report=self.run_source(client);self.assertEqual(report['failure'],'url_rejected');self.assertEqual(report['network_requests'],0)

    def test_truncated_download_reports_partial_bytes_and_is_not_promoted(self):
        body=pbf();base=self.wire(body)
        def wire(url,method,headers,timeout):
            if method=='GET' and not url.endswith('.md5'):return Response(200,{'Content-Length':str(len(body))},body[:-7])
            return base(url,method,headers,timeout)
        report=self.run_source(self.client(wire))
        self.assertEqual(report['failure'],'file_truncated');self.assertEqual(report['downloaded_bytes'],len(body)-7);self.assertFalse((self.path/'cache/wielkopolskie.osm.pbf').exists());self.assertFalse((self.path/'cache/wielkopolskie.part').exists())

    def test_lock_is_not_removed_by_competing_run_and_request_cap_is_enforced(self):
        cache=self.path/'cache';cache.mkdir();(cache/'.download.lock').write_text('OTHER RUN')
        report=self.run_source(self.client(self.wire()));self.assertEqual(report['failure'],'cache_busy');self.assertEqual((cache/'.download.lock').read_text(),'OTHER RUN')
        (cache/'.download.lock').unlink()
        report=self.run_source(self.client(self.wire(),max_requests_per_run=1))
        self.assertEqual(report['failure'],'budget_exceeded');self.assertEqual(report['network_requests'],1)

    def test_compressed_response_is_rejected_before_reading_data(self):
        base=self.wire()
        def wire(url,method,headers,timeout):
            if method=='GET' and not url.endswith('.md5'):
                response=Response(200,{'Content-Encoding':'gzip'},b'PRIVATE');self.responses.append(response);return response
            return base(url,method,headers,timeout)
        report=self.run_source(self.client(wire));self.assertEqual(report['failure'],'unsupported_encoding');self.assertEqual(self.responses[-1].read_sizes,[])

    @unittest.skipUnless(shutil.which('gpg'),'GPG unavailable')
    def test_cloud_source_mode_no_overpass_no_import_and_no_raw_pbf_in_archive(self):
        args=argparse.Namespace(mode='geofabrik-test',geofabrik_profile='wielkopolskie-full',region='poznan',industry='all',limit=25,category='wszystkie',storage='temporary',state_repository='',instance='private-coffee',accept_instance_terms=False,workdir=str(self.path/'work'),output=str(self.path/'output'))
        original=g.source_test_run
        def source(ledger,cache,profile):
            client=g.Downloader(ledger,opener=self.wire(),resolver=resolver,clock=lambda:self.now,sleep=self.sleep,monotonic=lambda:self.now)
            try:return original(ledger,cache,profile=profile,downloader=client)
            finally:client.close()
        with patch.dict(os.environ,{'PROSPECT_DATA_KEY':'1a'*32}),patch.object(c,'source_test_run',side_effect=source),patch.object(c,'HttpClient',side_effect=AssertionError('Overpass client forbidden')),redirect_stdout(io.StringIO()):
            self.assertEqual(c.run_cloud(args,discover=lambda *a,**kw:self.fail('No discovery')),0)
        self.assertFalse(list((self.path/'work').rglob('*.pbf')));self.assertFalse(list(self.path.glob('webforge-pbf-*')));self.assertFalse((self.path/'inherited-summary').exists())
        plain=self.path/'result.tar.gz';c.crypt(self.path/'output/results.tar.gpg',plain,'1a'*32,decrypt=True)
        with tarfile.open(plain) as archive:self.assertFalse(any(m.name.endswith(('.pbf','.part')) for m in archive.getmembers()))
        store=f.Store(self.path/'work/prospects.sqlite3')
        try:self.assertEqual(len(store.search()),0)
        finally:store.close()

    def test_workflow_source_mode_is_explicit_ten_inputs_and_no_raw_artifact(self):
        workflow=json.loads((ROOT/'workflow/prospect-finder.yml').read_text());inputs=workflow['on']['workflow_dispatch']['inputs']
        self.assertEqual(len(inputs),10);self.assertIn('geofabrik-test',inputs['mode']['options']);self.assertEqual(inputs['geofabrik_profile']['default'],'wielkopolskie-sample')
        step=next(s for s in workflow['jobs']['discover']['steps'] if s['name']=='Discover and encrypt private results')
        self.assertIn('--geofabrik-profile "$PF_GEOFABRIK_PROFILE"',step['run']);self.assertNotIn('${{',step['run'])
        self.assertNotIn('actions/cache',json.dumps(workflow));self.assertFalse(f.config('geofabrik')['automatic_schedule'])


if __name__=='__main__':unittest.main()
