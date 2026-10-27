"""Bounded read-only HTTP transport. Cache and rate ledger stay outside the repository."""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import random
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from dataclasses import dataclass

from finder import config, private_path


class NetworkError(Exception): pass
class BudgetExceeded(NetworkError): pass


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
            addresses = resolver(host, p.port or (443 if p.scheme == 'https' else 80), type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise ValueError()
    except (ValueError, OSError) as exc:
        raise NetworkError('URL odrzucony lub brak bezpiecznego rozpoznania DNS') from exc
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


def transport(url, method, data, headers, timeout, max_bytes):
    # build_opener preserves environment ProxyHandler and system CA/TLS verification.
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        encoding = response.headers.get('Content-Encoding', 'identity').lower()
        if encoding not in ('', 'identity'): raise NetworkError('Nieobsługiwane kodowanie odpowiedzi')
        size = response.headers.get('Content-Length')
        if size and int(size) > max_bytes: raise NetworkError('Odpowiedź przekracza limit wielkości')
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes: raise NetworkError('Odpowiedź przekracza limit wielkości')
        return Response(response.status, {k.lower(): v for k,v in response.headers.items()}, body, time.time())


class HttpClient:
    def __init__(self, cache_path, *, settings=None, wire=transport, clock=time.time, sleep=time.sleep, resolver=socket.getaddrinfo):
        self.cfg = {**config('network'), **(settings or {})}; self.wire = wire; self.clock = clock; self.sleep = sleep; self.resolver = resolver
        path = private_path(cache_path); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,status INTEGER,headers TEXT,body BLOB,fetched REAL);
        CREATE TABLE IF NOT EXISTS limits(day TEXT,host TEXT,count INTEGER,bytes INTEGER,next_at REAL,PRIMARY KEY(day,host));
        '''); os.chmod(path,0o600)
        self.requests = 0; self.cache_hits = 0; self.host_delays = {}

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
            total = self.db.execute('SELECT COALESCE(SUM(count),0),COALESCE(SUM(bytes),0) FROM limits WHERE day=?',(day,)).fetchone()
            reserved = self.cfg['overpass_max_body_bytes'] if overpass else self.cfg['max_body_bytes']
            if total[0] >= self.cfg['max_requests_per_day'] or total[1]+reserved > self.cfg['max_download_bytes_per_day'] or overpass and row[0] >= self.cfg['overpass_requests_per_day']:
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
            raise NetworkError('Retry-After przekracza limit; przerwano bez wcześniejszego ponowienia')
        self.sleep(delay)

    def request(self, url, *, method='GET', data=None, overpass=False):
        url = public_url(url,None); host = urlsplit(url).hostname
        if host in self.cfg['protected_hosts']: raise NetworkError('Chroniony host produkcyjny pominięty')
        if method != 'GET' and not (overpass and method == 'POST' and url == self.cfg['overpass_endpoint']):
            raise NetworkError('Dozwolone tylko GET oraz odczytowe POST do skonfigurowanego Overpass')
        key = hashlib.sha256(method.encode()+b'\0'+url.encode()+b'\0'+(data or b'')).hexdigest()
        cached = self.db.execute('SELECT status,headers,body,fetched FROM cache WHERE key=?',(key,)).fetchone()
        ttl = self.cfg['overpass_cache_ttl_seconds'] if overpass else self.cfg['cache_ttl_seconds']
        if cached:
            saved=Response(cached[0],json.loads(cached[1]),cached[2],cached[3],True)
            lifetime=max(self.cfg['error_cache_ttl_seconds'],self._retry_after(saved,saved.fetched_at)) if cached[0]>=400 else ttl
            if 0<=self.clock()-cached[3]<lifetime:self.cache_hits+=1;return saved
        public_url(url,self.resolver)
        for attempt in range(self.cfg['max_attempts']):
            day,reserved = self._reserve(host,overpass)
            try:
                response = self.wire(url,method,data,{'User-Agent':self.cfg['user_agent'],'Accept-Encoding':'identity','Accept':'application/json' if overpass else 'text/html,text/plain;q=0.9,*/*;q=0.1','Content-Type':'application/x-www-form-urlencoded' if data else 'text/plain'},self.cfg['overpass_timeout_seconds'] if overpass else self.cfg['timeout_seconds'],self.cfg['overpass_max_body_bytes'] if overpass else self.cfg['max_body_bytes'])
            except (OSError, ValueError, urllib.error.URLError, NetworkError) as exc:
                if attempt + 1 < self.cfg['max_attempts']: self._retry_delay(attempt); continue
                raise NetworkError('Błąd połączenia (proxy/DNS/TLS/timeout/limit treści): '+type(exc).__name__) from exc
            with self.db:
                self.db.execute('UPDATE limits SET bytes=bytes+? WHERE day=? AND host=?',(len(response.body)-reserved,day,host))
                self.db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?,?,?)',(key,response.status,json.dumps(response.headers),response.body,response.fetched_at))
            if response.status in (429,503) and response.headers.get('retry-after'):self.defer(host,self._retry_after(response,self.clock()))
            if response.status in (429,500,502,503,504) and attempt + 1 < self.cfg['max_attempts']:
                self._retry_delay(attempt,response); continue
            return response
        raise NetworkError('Nie udało się wykonać zapytania')
