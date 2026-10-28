"""Three bounded probes. No prospect import, contacts, website audit or failover."""
from __future__ import annotations
import json
from urllib.parse import urlencode
from finder import config
from live import build_query, region_config
from network import NetworkError, error_category, http_category, safe_diagnostics, instance_settings

PROBES=('availability','minimal_query','industry_small_area')


def diagnostic_settings(instance='overpass-de',accept_terms=False):
    settings=instance_settings(instance,accept_terms)
    d=config('overpass')['diagnostic']
    if d['max_attempts']!=1 or not 1<=d['max_requests_per_run']<=3:raise ValueError('Sondy: maksymalnie trzy próby bez ponowień')
    return {**settings,'max_attempts':d['max_attempts'],'max_requests_per_run':d['max_requests_per_run'],'overpass_timeout_seconds':d['read_timeout_seconds'],'timeout_seconds':d['read_timeout_seconds'],'max_body_bytes':d['max_body_bytes'],'overpass_max_body_bytes':d['max_body_bytes'],'cache_ttl_seconds':d['cache_ttl_seconds'],'overpass_cache_ttl_seconds':d['cache_ttl_seconds']}


def probe_queries(region='poznan',industry='mechanik'):
    d=config('overpass')['diagnostic'];area=dict(region_config(region))
    area['radius_m']=min(2000,area['radius_m'],d['radius_m'])
    small=build_query(area,industry).replace('[timeout:25][maxsize:67108864]',f'[timeout:{d["server_timeout_seconds"]}][maxsize:8388608]').replace('out meta center 1500;','out count;')
    tiny='[out:json][timeout:5][maxsize:8388608];node(1);out count;'
    return tiny,small


def parse_count(response):
    if response.status!=200:raise NetworkError('Błąd HTTP sondy',category=http_category(response.status),http_status=response.status)
    try:payload=json.loads(response.body)
    except (ValueError,UnicodeError) as exc:raise NetworkError('Niepoprawny JSON sondy',category='invalid_json') from exc
    if isinstance(payload,dict) and payload.get('remark'):
        remark=str(payload['remark']).lower()
        category='overpass_timeout' if 'timed out' in remark or 'timeout' in remark else 'overpass_memory_limit' if 'out of memory' in remark or 'memory limit' in remark else 'overpass_runtime_error'
        raise NetworkError('Niepełna odpowiedź sondy',category=category)
    if isinstance(payload,dict) and isinstance(payload.get('elements'),list) and len(payload['elements'])==1:
        element=payload['elements'][0]
        if isinstance(element,dict) and element.get('type')=='count' and isinstance(element.get('tags'),dict):
            value=element['tags'].get('total')
            if isinstance(value,str) and value.isascii() and value.isdecimal() and len(value)<=9:return int(value)
    raise NetworkError('Brak poprawnego wyniku out count',category='invalid_payload')


def safe_probes(raw):
    if not isinstance(raw,list):return []
    rows=[]
    for row in raw[:3]:
        if not isinstance(row,dict) or row.get('name') not in PROBES:continue
        safe={'name':row['name'],'outcome':row.get('outcome') if row.get('outcome') in ('passed','failed','skipped') else 'failed'}
        events=safe_diagnostics({'events':row.get('events',[])})['events']
        safe['events']=events
        category=safe_diagnostics({'failure':row.get('category')})['failure']
        if category:safe['category']=category
        for key,upper in [('matched_osm_objects',999999999),('http_status',599)]:
            value=row.get(key)
            if type(value) is int and 0<=value<=upper:safe[key]=value
        rows.append(safe)
    return rows


def diagnose_run(client,*,instance='overpass-de',region='poznan',industry='mechanik'):
    # Settings/endpoint must be selected once by the caller, never on failure.
    endpoint=config('overpass')['instances'][instance]
    if client.cfg['overpass_endpoint']!=endpoint['endpoint'] or client.cfg['max_attempts']!=1 or client.cfg['max_requests_per_run']>3:raise ValueError('Nieprawidłowy klient diagnostyczny')
    tiny,small=probe_queries(region,industry)
    rows=[];start=len(client.diagnostics);stop=None
    for name,query in zip(PROBES,(None,tiny,small)):
        row={'name':name,'outcome':'failed'};offset=len(client.diagnostics)
        if stop:
            row.update(outcome='skipped',category=stop);rows.append(row);continue
        try:
            response=client.request(endpoint['status_endpoint'] if query is None else endpoint['endpoint'],method='GET' if query is None else 'POST',data=None if query is None else urlencode({'data':query}).encode(),overpass=True)
            row['http_status']=response.status
            if query is None:
                if response.status!=200:raise NetworkError('Status serwera niedostępny',category=http_category(response.status),http_status=response.status)
            else:row['matched_osm_objects']=parse_count(response)
            row['outcome']='passed'
        except NetworkError as exc:
            row['category']=error_category(exc)
            if exc.http_status is not None:row['http_status']=exc.http_status
            if row['category'] in ('http_429','budget_exceeded','retry_after_deferred','proxy_error') or row.get('http_status') in (401,403,451):stop=row['category']
        row['events']=client.diagnostics[offset:];rows.append(row)
    failure=next((r.get('category') for r in rows if r['outcome']=='failed'),None)
    return {'mode':'diagnose','instance':instance,'outcome':'completed' if all(r['outcome']=='passed' for r in rows) else 'blocked_or_failed','probes':safe_probes(rows),'network_requests':client.requests,'cache_hits':client.cache_hits,'diagnostics':safe_diagnostics({'failure':failure,'events':client.diagnostics[start:]}),'limitations':['Diagnostyka nie importuje firm. Liczba obiektów OSM nie jest liczbą klientów.','Status HTTP nie dowodzi działania interpretera; odczyt nie odróżnia kolejki serwera od obliczeń.','Jedna instancja, bez automatycznego failover; obowiązują wspólne budżety i Retry-After.']}
