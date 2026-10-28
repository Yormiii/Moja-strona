"""Bounded, streaming source benchmark. No prospect import and no Overpass calls."""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import sqlite3
import struct
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit

from finder import config, private_path
from network import NoRedirect, PhaseHTTPHandler, PhaseHTTPSHandler, public_url, error_category, http_category, ERROR_CATEGORIES

SOURCE_ERRORS=ERROR_CATEGORIES|{'invalid_metadata','range_not_supported','metadata_changed','checksum_mismatch','invalid_pbf_header','file_truncated','disk_space','download_deadline','download_too_large','cache_busy'}


class SourceError(Exception):
    def __init__(self,category):self.category=category;super().__init__(category)


def profile_config(profile):
    cfg=config('geofabrik')
    if profile not in cfg['profiles']:raise ValueError('Nieznany profil Geofabrik')
    dataset,scope=profile.rsplit('-',1)
    return cfg,dataset,scope


def allowed_url(url,dataset):
    p=urlsplit(url)
    if p.scheme!='https' or p.netloc!='download.geofabrik.de' or p.query or p.fragment or not re.fullmatch(r'/europe/poland/'+re.escape(dataset)+r'-(latest|[0-9]{6})\.osm\.pbf(?:\.md5)?',p.path):raise SourceError('url_rejected')
    return url


def open_request(url,method,headers,timeout):
    req=urllib.request.Request(url,method=method,headers=headers)
    opener=urllib.request.build_opener(NoRedirect(),PhaseHTTPHandler(8),PhaseHTTPSHandler(8))
    try:return opener.open(req,timeout=timeout)
    except urllib.error.HTTPError as exc:return exc


def pbf_header_valid(prefix):
    """Validate just the first BlobHeader envelope, never pretend to parse entities."""
    if len(prefix)<4:return False
    size=struct.unpack('>I',prefix[:4])[0]
    if not 1<=size<=65536 or len(prefix)<4+size:return False
    data=prefix[4:4+size];pos=0;kind=None;blob_size=None
    def varint():
        nonlocal pos
        value=0
        for shift in range(0,70,7):
            if pos>=len(data):raise ValueError()
            b=data[pos];pos+=1;value|=(b&127)<<shift
            if b<128:return value
        raise ValueError()
    try:
        while pos<len(data):
            tag=varint();field,wire=tag>>3,tag&7
            if field==0:return False
            if wire==0:
                value=varint()
                if field==3:blob_size=value
            elif wire==2:
                length=varint()
                if length>len(data)-pos:return False
                value=data[pos:pos+length];pos+=length
                if field==1:kind=value
            elif wire in (1,5):
                pos+=8 if wire==1 else 4
                if pos>len(data):return False
            else:return False
        return kind==b'OSMHeader' and type(blob_size) is int and 0<blob_size<=32*1024*1024
    except ValueError:return False


class Downloader:
    def __init__(self,ledger_path,*,cfg=None,opener=open_request,resolver=None,clock=time.time,sleep=time.sleep,monotonic=time.monotonic):
        self.cfg=cfg or config('geofabrik');self.opener=opener;self.resolver=resolver;self.clock=clock;self.sleep=sleep;self.monotonic=monotonic
        self.started=monotonic();self.requests=0;self.bytes_received=0;self.events=[]
        path=private_path(ledger_path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.db=sqlite3.connect(path)
        self.db.executescript('CREATE TABLE IF NOT EXISTS pbf_usage(day TEXT PRIMARY KEY, requests INTEGER, bytes INTEGER, next_at REAL); CREATE TABLE IF NOT EXISTS pbf_metadata(dataset TEXT PRIMARY KEY, payload TEXT);')
        os.chmod(path,0o600)

    def close(self):self.db.close()
    def deadline(self):
        if self.monotonic()-self.started>self.cfg['max_total_seconds']:raise SourceError('download_deadline')

    def reserve(self,size):
        self.deadline();day=dt.datetime.fromtimestamp(self.clock(),dt.timezone.utc).date().isoformat()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT requests,bytes FROM pbf_usage WHERE day=?',(day,)).fetchone() or (0,0)
            next_at=self.db.execute('SELECT COALESCE(MAX(next_at),0) FROM pbf_usage').fetchone()[0]
            delay=max(0,next_at-self.clock())
            if self.requests>=self.cfg['max_requests_per_run'] or row[0]>=self.cfg['max_requests_per_day'] or row[1]+size>self.cfg['max_bytes_per_day'] or delay>self.cfg['max_wait_seconds']:raise SourceError('budget_exceeded')
            self.db.execute('INSERT INTO pbf_usage VALUES(?,1,?,?) ON CONFLICT(day) DO UPDATE SET requests=requests+1,bytes=bytes+excluded.bytes,next_at=excluded.next_at',(day,size,max(next_at,self.clock())+self.cfg['min_interval_seconds']));self.db.commit()
        except Exception:self.db.rollback();raise
        self.requests+=1
        if delay:self.sleep(delay)
        self.deadline();return day

    def adjust(self,day,reserved,received):
        with self.db:self.db.execute('UPDATE pbf_usage SET bytes=bytes+? WHERE day=?',(received-reserved,day))

    def request(self,url,method,headers,size,dataset,stage):
        for redirect in range(self.cfg['max_redirects']+1):
            allowed_url(url,dataset)
            public_url(url) if self.resolver is None else public_url(url,self.resolver)
            day=self.reserve(size);started=self.monotonic()
            try:response=self.opener(url,method,{'User-Agent':config('network')['user_agent'],'Accept-Encoding':'identity',**headers},self.cfg['read_timeout_seconds'])
            except Exception as exc:
                self.events.append({'stage':stage,'category':error_category(exc),'elapsed_ms':max(0,int((self.monotonic()-started)*1000))});raise
            status=response.status
            self.events.append({'stage':stage,'http_status':status,'category':'ok' if status in (200,206,304) else http_category(status),'elapsed_ms':max(0,int((self.monotonic()-started)*1000))})
            if status in (429,503) and response.headers.get('Retry-After'):
                value=response.headers['Retry-After']
                try:delay=float(value)
                except ValueError:
                    try:delay=email.utils.parsedate_to_datetime(value).timestamp()-self.clock()
                    except (ValueError,TypeError,OverflowError):delay=0
                with self.db:self.db.execute('UPDATE pbf_usage SET next_at=MAX(next_at,?) WHERE day=?',(self.clock()+max(0,delay),day))
            if status in (301,302,303,307,308):
                location=response.headers.get('Location','');response.close();self.adjust(day,size,0)
                if not location or redirect==self.cfg['max_redirects']:raise SourceError('http_other')
                url=urljoin(url,location);continue
            return response,url,day
        raise SourceError('http_other')

    def read_small(self,response,limit):
        self.deadline()
        try:body=response.read(limit+1)
        except TimeoutError as exc:raise SourceError('read_timeout') from exc
        self.bytes_received+=len(body)
        if len(body)>limit:raise SourceError('response_too_large')
        self.deadline();return body


def source_test_run(ledger_path,cache_dir,*,profile='wielkopolskie-sample',downloader=None):
    cfg,dataset,scope=profile_config(profile);cache=private_path(cache_dir)
    cache.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(cache,0o700)
    lock=cache/'.download.lock'
    report={'mode':'geofabrik-test','outcome':'blocked_or_failed','profile':profile,'dataset':dataset,'scope':scope,'stages':[],'cache_used':False,'checksum_verified':False,'pbf_header_valid':False,'import_executed':False,'buffer_bytes':cfg['chunk_bytes']}
    owned=downloader is None;client=downloader or Downloader(ledger_path);part=cache/(dataset+'.part');started=client.monotonic();locked=False
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd);locked=True
        if part.is_symlink():raise SourceError('url_rejected')
        raw=client.db.execute('SELECT payload FROM pbf_metadata WHERE dataset=?',(dataset,)).fetchone()
        saved=json.loads(raw[0]) if raw else {};headers={}
        if saved.get('etag'):headers['If-None-Match']=saved['etag']
        elif saved.get('last_modified'):headers['If-Modified-Since']=saved['last_modified']
        response,final_url,day=client.request(cfg['datasets'][dataset]['url'],'HEAD',headers,0,dataset,'metadata')
        with response:
            if response.status==304 and saved:
                meta=saved;allowed_url(meta['url'],dataset)
            elif response.status==200:
                length=response.headers.get('Content-Length','')
                if not re.fullmatch(r'[0-9]{1,12}',length):raise SourceError('invalid_metadata')
                meta={'size':int(length),'url':final_url,'etag':response.headers.get('ETag'),'last_modified':response.headers.get('Last-Modified')}
            else:raise SourceError(http_category(response.status))
        size=meta['size']
        if type(size) is not int or size<1:raise SourceError('invalid_metadata')
        report['file_size_bytes']=size
        if size>cfg['max_file_bytes']:raise SourceError('download_too_large')
        with client.db:client.db.execute('INSERT OR REPLACE INTO pbf_metadata VALUES(?,?)',(dataset,json.dumps(meta)))
        checksum=None
        if scope=='full':
            response,_,day=client.request(meta['url']+'.md5','GET',{},512,dataset,'checksum')
            with response:
                if response.status!=200:raise SourceError(http_category(response.status))
                data=client.read_small(response,512);client.adjust(day,512,len(data))
            found=re.fullmatch(rb'([a-fA-F0-9]{32})(?:\s+\*?[^\r\n]{1,200})?\s*',data.strip())
            if not found:raise SourceError('invalid_metadata')
            checksum=found.group(1).decode().lower()
        target=cache/(dataset+'.osm.pbf')
        if target.is_symlink():raise SourceError('url_rejected')
        if scope=='full' and target.is_file() and target.stat().st_size==size:
            digest=hashlib.md5(usedforsecurity=False);sha=hashlib.sha256();prefix=b''
            with target.open('rb') as stream:
                while block:=stream.read(cfg['chunk_bytes']):
                    client.deadline();digest.update(block);sha.update(block);prefix=(prefix+block)[:65540] if len(prefix)<65540 else prefix
            if digest.hexdigest()==checksum and pbf_header_valid(prefix):
                report.update(cache_used=True,checksum_verified=True,pbf_header_valid=True,sha256=sha.hexdigest(),download_ms=0,downloaded_bytes=0,outcome='completed')
                return report
        wanted=min(size,cfg['sample_bytes']) if scope=='sample' else size
        if shutil.disk_usage(cache).free<wanted+cfg['minimum_free_disk_bytes']:raise SourceError('disk_space')
        headers={}
        if scope=='sample':headers['Range']=f'bytes=0-{wanted-1}'
        if meta.get('etag') and not meta['etag'].startswith('W/'):headers['If-Match']=meta['etag']
        elif meta.get('last_modified'):headers['If-Unmodified-Since']=meta['last_modified']
        response,_,day=client.request(meta['url'],'GET',headers,wanted,dataset,'download')
        received=0;sha=hashlib.sha256();digest=hashlib.md5(usedforsecurity=False);prefix=b'';download_start=client.monotonic()
        with response:
            if response.status==412:raise SourceError('metadata_changed')
            if response.headers.get('Content-Encoding','identity').lower() not in ('','identity'):raise SourceError('unsupported_encoding')
            if scope=='sample':
                if response.status!=206:raise SourceError(http_category(response.status) if response.status>=400 else 'range_not_supported')
                if response.headers.get('Content-Range')!=f'bytes 0-{wanted-1}/{size}':raise SourceError('metadata_changed')
            elif response.status!=200:raise SourceError(http_category(response.status))
            length=response.headers.get('Content-Length')
            if length is not None and length!=str(wanted):raise SourceError('metadata_changed')
            with part.open('wb') as stream:
                os.chmod(part,0o600)
                while True:
                    client.deadline()
                    try:block=response.read(min(cfg['chunk_bytes'],wanted-received+1))
                    except TimeoutError as exc:raise SourceError('read_timeout') from exc
                    if not block:break
                    received+=len(block);client.bytes_received+=len(block);report['downloaded_bytes']=received
                    if received>wanted:raise SourceError('response_too_large')
                    stream.write(block);sha.update(block);digest.update(block)
                    if len(prefix)<65540:prefix=(prefix+block)[:65540]
                client.deadline()
        report['downloaded_bytes']=received;report['download_ms']=max(0,int((client.monotonic()-download_start)*1000))
        if received!=wanted:raise SourceError('file_truncated')
        if not pbf_header_valid(prefix):raise SourceError('invalid_pbf_header')
        report['pbf_header_valid']=True
        if scope=='full':
            if digest.hexdigest()!=checksum:raise SourceError('checksum_mismatch')
            report['checksum_verified']=True;os.replace(part,target)
        client.adjust(day,wanted,received)
        report.update(outcome='completed',sha256=sha.hexdigest())
    except Exception as exc:
        report['failure']=exc.category if isinstance(exc,SourceError) else 'cache_busy' if isinstance(exc,FileExistsError) else error_category(exc)
    finally:
        if locked:part.unlink(missing_ok=True);lock.unlink(missing_ok=True)
        report['elapsed_ms']=max(0,int((client.monotonic()-started)*1000));report['network_requests']=client.requests;report['bytes_received']=client.bytes_received
        report['stages']=client.events
        report['rss_peak_bytes']=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*(1 if sys.platform=='darwin' else 1024)
        if owned:client.close()
    return report


def safe_source_report(raw):
    if not isinstance(raw,dict):raw={}
    profiles=config('geofabrik')['profiles'];profile=raw.get('profile')
    safe={'profile':profile if isinstance(profile,str) and profile in profiles else None,'outcome':raw.get('outcome') if raw.get('outcome') in ('completed','blocked_or_failed') else 'not_started','import_executed':False}
    for key in ('cache_used','checksum_verified','pbf_header_valid'):safe[key]=raw.get(key) is True
    failure=raw.get('failure');safe['failure']=failure if isinstance(failure,str) and failure in SOURCE_ERRORS else None
    for key in ('file_size_bytes','downloaded_bytes','download_ms','elapsed_ms','network_requests','bytes_received','rss_peak_bytes','buffer_bytes'):
        value=raw.get(key)
        if type(value) is int and 0<=value<=2**50:safe[key]=value
    digest=raw.get('sha256')
    if isinstance(digest,str) and re.fullmatch('[a-f0-9]{64}',digest):safe['sha256']=digest
    safe['stages']=[]
    stages=raw.get('stages',[])
    for item in stages[:8] if isinstance(stages,list) else []:
        if not isinstance(item,dict) or item.get('stage') not in ('metadata','checksum','download'):continue
        category=item.get('category');event={'stage':item['stage'],'category':category if isinstance(category,str) and category in SOURCE_ERRORS|{'ok'} else 'network_other'}
        for key,maximum in [('http_status',599),('elapsed_ms',3600000)]:
            value=item.get(key)
            if type(value) is int and 0<=value<=maximum:event[key]=value
        safe['stages'].append(event)
    return safe


def source_markdown(summary):
    source=summary['geofabrik'];lines=['# WebForge — test źródła Geofabrik','',f"Stan: `{summary['outcome']}`; profil: `{source['profile']}`",f"Magazyn: `{summary['storage']}`; odtworzono stan: `{summary['state_restored']}`",'', 'To test pobierania, bez importu firm i bez Overpass. Próbka nie potwierdza pobrania ani integralności całego pliku.','', '| Miara | Wartość |','|---|---:|']
    for key in ('file_size_bytes','downloaded_bytes','download_ms','elapsed_ms','network_requests','rss_peak_bytes','buffer_bytes','cache_used','pbf_header_valid','checksum_verified'):lines.append(f"| {key} | {source.get(key,'nieustalono')} |")
    lines+=['', 'RSS dotyczy procesu testu pobierania, nie przyszłego importu/geometrii. Walidacja PBF obejmuje pierwszy BlobHeader; pełny profil dodatkowo porównuje MD5 operatora.','', '| Etap | Kategoria | HTTP | ms do nagłówków |','|---|---|---:|---:|']
    for row in source['stages']:lines.append('| '+' | '.join(str(row.get(k,'—')) for k in ('stage','category','http_status','elapsed_ms'))+' |')
    lines+=['',f"Kategoria przerwania: `{source.get('failure')}`; błędy runnera: "+(', '.join(summary['errors']) or 'brak'),'', '© OpenStreetMap contributors — ODbL 1.0; wyciąg Geofabrik. Surowy PBF nie jest wysyłany w artefakcie ani snapshotcie Git.']
    return '\n'.join(lines)+'\n'
