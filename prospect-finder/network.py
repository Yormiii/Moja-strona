"""Bounded read-only HTTP transport. Cache and rate ledger stay outside the repository."""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import random
import socket
import ssl
import sqlite3
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from dataclasses import dataclass
from functools import partial

from finder import config, private_path


ERROR_CATEGORIES=frozenset(('network_other','budget_exceeded','dns_error','url_rejected','protected_host','method_rejected','timeout','connect_timeout','read_timeout','write_timeout','tls_error','connection_error','proxy_error','response_too_large','unsupported_encoding','retry_after_deferred','http_429','http_5xx','http_4xx','http_other','invalid_json','overpass_timeout','overpass_memory_limit','overpass_runtime_error','invalid_payload','invalid_data'))


def instance_settings(name='overpass-de',accept_terms=False):
    instances=config('overpass')['instances']
    if name not in instances:raise ValueError('Nieznana instancja Overpass')
    entry=instances[name]
    if entry.get('requires_terms_acceptance') and accept_terms is not True:raise ValueError('Wymagane zapoznanie się z zasadami operatora')
    return {'overpass_endpoint':entry['endpoint']}


class NetworkError(Exception):
    def __init__(self,message,*,category='network_other',http_status=None):
        super().__init__(message)
        self.category=category if isinstance(category,str) and category in ERROR_CATEGORIES else 'network_other'
        self.http_status=http_status if type(http_status) is int and 100<=http_status<=599 else None


class BudgetExceeded(NetworkError):
    def __init__(self,message):super().__init__(message,category='budget_exceeded')


def error_category(exc):
    # Exception types/reason types only: never publish arbitrary exception text.
    if isinstance(exc,NetworkError):return exc.category
    if isinstance(exc,socket.gaierror):return 'dns_error'
    if isinstance(exc,(TimeoutError,socket.timeout)):return 'timeout'
    if isinstance(exc,ssl.SSLError):return 'tls_error'
    if isinstance(exc,urllib.error.URLError):
        return error_category(exc.reason) if isinstance(exc.reason,Exception) else 'network_other'
    if isinstance(exc,(ConnectionError,http.client.IncompleteRead)):return 'connection_error'
    return 'network_other'


def http_category(status):
    if status==407:return 'proxy_error'
    if status==429:return 'http_429'
    if 500<=status<=599:return 'http_5xx'
    if 400<=status<=499:return 'http_4xx'
    return 'http_other'


def safe_diagnostics(raw):
    """Public boundary: finite enums and bounded integers; no URLs/text/headers."""
    if not isinstance(raw,dict):raw={}
    events=[]
    candidates=raw.get('events',[])
    for item in candidates[:500] if isinstance(candidates,list) else []:
        if not isinstance(item,dict) or item.get('scope') not in ('overpass','website') or item.get('event') not in ('response','error','cache'):continue
        category=item.get('category')
        e={'scope':item['scope'],'event':item['event'],'category':category if isinstance(category,str) and category in ERROR_CATEGORIES|{'ok'} else 'network_other'}
        for key,maximum,minimum in [('http_status',599,100),('attempt',100,0),('elapsed_ms',3600000,0),('response_bytes',8388608,0)]:
            value=item.get(key)
            if type(value) is int and minimum<=value<=maximum:e[key]=value
        events.append(e)
    query={}
    q=raw.get('query',{})
    if isinstance(q,dict):
        for key,maximum in [('clauses',1000),('query_bytes',100000),('radius_m',50000),('output_limit',1500)]:
            if type(q.get(key)) is int and 0<=q[key]<=maximum:query[key]=q[key]
    failure=raw.get('failure')
    return {'failure':failure if isinstance(failure,str) and failure in ERROR_CATEGORIES else None,'query':query,'events':events}


def public_url(url, resolver=socket.getaddrinfo):
    """Reject non-public addresses and repeat validation on every redirect/request."""
    try:
        p = urlsplit(url)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.port not in (None, 80, 443):
            raise ValueError()
        if any(ord(c) < 33 for c in url): raise ValueError()
        host = p.hostname.rstrip('.').lower()
        if host in ('localhost', 'metadata.google.internal') or host.endswith(('.local', '.internal', '.localhost')):
            raise ValueError()
        try:
            literal=ipaddress.ip_address(host)
        except ValueError:literal=None
        if literal is not None and not literal.is_global:raise ValueError()
        if resolver is not None:
            try:addresses = resolver(host, p.port or (443 if p.scheme == 'https' else 80), type=socket.SOCK_STREAM)
            except OSError as exc:raise NetworkError('Nie udało się bezpiecznie rozpoznać DNS',category='dns_error') from exc
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise ValueError()
    except (ValueError, OSError) as exc:
        raise NetworkError('URL odrzucony',category='url_rejected') from exc
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query, ''))


@dataclass
class Response:
    status: int
    headers: dict
    body: bytes
    fetched_at: float
    cached: bool = False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


class PhaseConnection:
    """Instrument actual urllib connections, including the inherited proxy/TLS path."""
    def __init__(self,*args,connect_timeout=8,**kwargs):
        self.read_timeout=kwargs.get('timeout',35)
        kwargs['timeout']=min(self.read_timeout,connect_timeout)
        super().__init__(*args,**kwargs)

    def connect(self):
        try:super().connect()
        except TimeoutError as exc:raise NetworkError('Timeout zestawiania połączenia/proxy/TLS',category='connect_timeout') from exc
        self.sock.settimeout(self.read_timeout)

    def request(self,*args,**kwargs):
        try:return super().request(*args,**kwargs)
        except TimeoutError as exc:raise NetworkError('Timeout wysyłania żądania',category='write_timeout') from exc

    def getresponse(self):
        try:return super().getresponse()
        except TimeoutError as exc:raise NetworkError('Timeout oczekiwania na nagłówki HTTP',category='read_timeout') from exc


class PhaseHTTPConnection(PhaseConnection,http.client.HTTPConnection):pass
class PhaseHTTPSConnection(PhaseConnection,http.client.HTTPSConnection):pass


class PhaseHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self,connect_timeout):super().__init__();self.connect_timeout=connect_timeout
    def http_open(self,req):return self.do_open(partial(PhaseHTTPConnection,connect_timeout=self.connect_timeout),req)


class PhaseHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self,connect_timeout):super().__init__();self.connect_timeout=connect_timeout
    def https_open(self,req):
        return self.do_open(partial(PhaseHTTPSConnection,connect_timeout=self.connect_timeout),req,context=self._context)


def transport(url, method, data, headers, timeout, max_bytes,*,connect_timeout=8):
    # build_opener preserves environment ProxyHandler and system CA/TLS verification.
    opener = urllib.request.build_opener(NoRedirect(),PhaseHTTPHandler(connect_timeout),PhaseHTTPSHandler(connect_timeout))
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        encoding = response.headers.get('Content-Encoding', 'identity').lower()
        if encoding not in ('', 'identity'): raise NetworkError('Nieobsługiwane kodowanie odpowiedzi',category='unsupported_encoding')
        size = response.headers.get('Content-Length')
        if size and int(size) > max_bytes: raise NetworkError('Odpowiedź przekracza limit wielkości',category='response_too_large')
        try:body = response.read(max_bytes + 1)
        except TimeoutError as exc:raise NetworkError('Timeout odczytu treści HTTP',category='read_timeout',http_status=response.status) from exc
        if len(body) > max_bytes: raise NetworkError('Odpowiedź przekracza limit wielkości',category='response_too_large')
        return Response(response.status, {k.lower(): v for k,v in response.headers.items()}, body, time.time())


class HttpClient:
    def __init__(self, cache_path, *, settings=None, wire=transport, clock=time.time, sleep=time.sleep, resolver=socket.getaddrinfo):
        self.cfg = {**config('network'), **(settings or {})}; self.wire = partial(transport,connect_timeout=self.cfg['connect_timeout_seconds']) if wire is transport else wire; self.clock = clock; self.sleep = sleep; self.resolver = resolver
        path = private_path(cache_path); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,status INTEGER,headers TEXT,body BLOB,fetched REAL);
        CREATE TABLE IF NOT EXISTS limits(day TEXT,host TEXT,count INTEGER,bytes INTEGER,next_at REAL,PRIMARY KEY(day,host));
        '''); os.chmod(path,0o600)
        self.requests = 0; self.cache_hits = 0; self.host_delays = {};self.diagnostics=[]

    def _event(self,scope,event,category,**numbers):
        if len(self.diagnostics)<500:self.diagnostics.append({'scope':scope,'event':event,'category':category,**numbers})

    def close(self): self.db.close()

    def defer(self,host,seconds):
        day=dt.datetime.fromtimestamp(self.clock(),dt.timezone.utc).date().isoformat()
        with self.db:self.db.execute('INSERT INTO limits VALUES(?,?,0,0,?) ON CONFLICT(day,host) DO UPDATE SET next_at=MAX(next_at,excluded.next_at)',(day,host,self.clock()+seconds))

    def _reserve(self, host, overpass):
        if self.requests >= self.cfg['max_requests_per_run']: raise BudgetExceeded('Limit zapytań w przebiegu')
        now = self.clock(); day = dt.datetime.fromtimestamp(now, dt.timezone.utc).date().isoformat()
        interval = max(self.cfg['overpass_interval_seconds'] if overpass else self.cfg['min_host_interval_seconds'], self.host_delays.get(host,0))
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT count,next_at FROM limits WHERE day=? AND host=?',(day,host)).fetchone() or (0,0)
            next_at=self.db.execute('SELECT COALESCE(MAX(next_at),0) FROM limits WHERE host=?',(host,)).fetchone()[0]
            overpass_count=row[0]
            if overpass:
                hosts=sorted(set(self.cfg['overpass_hosts'])|{host});marks=','.join('?' for _ in hosts)
                overpass_count=self.db.execute(f'SELECT COALESCE(SUM(count),0) FROM limits WHERE day=? AND host IN ({marks})',(day,*hosts)).fetchone()[0]
                next_at=self.db.execute(f'SELECT COALESCE(MAX(next_at),0) FROM limits WHERE host IN ({marks})',hosts).fetchone()[0]
            total = self.db.execute('SELECT COALESCE(SUM(count),0),COALESCE(SUM(bytes),0) FROM limits WHERE day=?',(day,)).fetchone()
            reserved = self.cfg['overpass_max_body_bytes'] if overpass else self.cfg['max_body_bytes']
            if total[0] >= self.cfg['max_requests_per_day'] or total[1]+reserved > self.cfg['max_download_bytes_per_day'] or overpass and overpass_count >= self.cfg['overpass_requests_per_day']:
                raise BudgetExceeded('Dzienny limit zapytań lub pobierania')
            delay = max(0,next_at-now)
            if delay > self.cfg['max_wait_seconds']: raise BudgetExceeded('Odroczenie dłuższe niż limit oczekiwania')
            self.db.execute('INSERT INTO limits VALUES(?,?,1,?,?) ON CONFLICT(day,host) DO UPDATE SET count=count+1,bytes=bytes+excluded.bytes,next_at=excluded.next_at',(day,host,reserved,max(now,next_at)+interval)); self.db.commit()
        except Exception: self.db.rollback(); raise
        self.requests += 1
        if delay: self.sleep(delay)
        return day,reserved

    def _retry_after(self,response,now):
        value=response.headers.get('retry-after','0')
        try: delay=float(value)
        except ValueError:
            try: delay=email.utils.parsedate_to_datetime(value).timestamp()-now
            except (ValueError,TypeError,OverflowError):delay=0
        return max(0,delay)

    def _retry_delay(self, attempt, response=None):
        delay = 2**attempt + random.uniform(0,0.5)
        if response and response.headers.get('retry-after'):
            delay = max(delay,self._retry_after(response,self.clock()))
        if delay > self.cfg['max_wait_seconds']:
            raise NetworkError('Retry-After przekracza limit; przerwano bez wcześniejszego ponowienia',category='retry_after_deferred')
        self.sleep(delay)

    def request(self, url, *, method='GET', data=None, overpass=False):
        url = public_url(url,None); host = urlsplit(url).hostname
        scope='overpass' if overpass else 'website'
        if host in self.cfg['protected_hosts']: raise NetworkError('Chroniony host produkcyjny pominięty',category='protected_host')
        if method != 'GET' and not (overpass and method == 'POST' and url == self.cfg['overpass_endpoint']):
            raise NetworkError('Dozwolone tylko GET oraz odczytowe POST do skonfigurowanego Overpass',category='method_rejected')
        key = hashlib.sha256(method.encode()+b'\0'+url.encode()+b'\0'+(data or b'')).hexdigest()
        cached = self.db.execute('SELECT status,headers,body,fetched FROM cache WHERE key=?',(key,)).fetchone()
        ttl = self.cfg['overpass_cache_ttl_seconds'] if overpass else self.cfg['cache_ttl_seconds']
        if cached:
            saved=Response(cached[0],json.loads(cached[1]),cached[2],cached[3],True)
            lifetime=max(self.cfg['error_cache_ttl_seconds'],self._retry_after(saved,saved.fetched_at)) if cached[0]>=400 else ttl
            if 0<=self.clock()-cached[3]<lifetime:
                self.cache_hits+=1;self._event(scope,'cache','ok' if saved.status<400 else http_category(saved.status),http_status=saved.status,response_bytes=len(saved.body),attempt=0,elapsed_ms=0);return saved
        try:public_url(url,self.resolver)
        except NetworkError as exc:
            self._event(scope,'error',exc.category,attempt=0,elapsed_ms=0);raise
        for attempt in range(self.cfg['max_attempts']):
            try:day,reserved = self._reserve(host,overpass)
            except BudgetExceeded as exc:
                self._event(scope,'error',exc.category,attempt=attempt+1,elapsed_ms=0);raise
            started=self.clock()
            try:
                response = self.wire(url,method,data,{'User-Agent':self.cfg['user_agent'],'Accept-Encoding':'identity','Accept':'application/json' if overpass else 'text/html,text/plain;q=0.9,*/*;q=0.1','Content-Type':'application/x-www-form-urlencoded' if data else 'text/plain'},self.cfg['overpass_timeout_seconds'] if overpass else self.cfg['timeout_seconds'],self.cfg['overpass_max_body_bytes'] if overpass else self.cfg['max_body_bytes'])
            except (OSError, ValueError, urllib.error.URLError, NetworkError,http.client.HTTPException) as exc:
                category=error_category(exc)
                numbers={'attempt':attempt+1,'elapsed_ms':max(0,int((self.clock()-started)*1000))}
                if getattr(exc,'http_status',None) is not None:numbers['http_status']=exc.http_status
                self._event(scope,'error',category,**numbers)
                if category in ('response_too_large','unsupported_encoding'):raise
                if attempt + 1 < self.cfg['max_attempts']: self._retry_delay(attempt); continue
                raise NetworkError('Błąd połączenia: '+type(exc).__name__,category=category,http_status=getattr(exc,'http_status',None)) from exc
            self._event(scope,'response','ok' if response.status<400 else http_category(response.status),http_status=response.status,attempt=attempt+1,elapsed_ms=max(0,int((self.clock()-started)*1000)),response_bytes=len(response.body))
            with self.db:
                self.db.execute('UPDATE limits SET bytes=bytes+? WHERE day=? AND host=?',(len(response.body)-reserved,day,host))
                self.db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?,?,?)',(key,response.status,json.dumps(response.headers),response.body,response.fetched_at))
            if response.status in (429,503) and response.headers.get('retry-after'):self.defer(host,self._retry_after(response,self.clock()))
            if response.status in (429,500,502,503,504) and attempt + 1 < self.cfg['max_attempts']:
                self._retry_delay(attempt,response); continue
            return response
        raise NetworkError('Nie udało się wykonać zapytania')
