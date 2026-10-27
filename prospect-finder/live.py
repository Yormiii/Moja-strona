"""OpenStreetMap discovery and conservative, robots-aware homepage checks."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from uuid import uuid4
import datetime as dt
from html.parser import HTMLParser
import json
import math
import re
import os
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from finder import config, industries, validate_record, url, matches, private_path, export_records
from network import HttpClient, NetworkError, BudgetExceeded

ATTRIBUTION = '© OpenStreetMap contributors — ODbL 1.0'
COPYRIGHT = 'https://www.openstreetmap.org/copyright'


def region_config(key):
    region = config('osm')['regions'].get(key)
    if not region: raise ValueError('Nieznany region OSM')
    if not -90 <= region['lat'] <= 90 or not -180 <= region['lon'] <= 180 or not 1 <= region['radius_m'] <= 50000: raise ValueError('Nieprawidłowy region/promień')
    return region


def tag_matches(tags, condition):
    value = str(tags.get(condition['key'], ''))
    if 'contains' in condition: return condition['contains'].casefold() in value.casefold()
    return value in condition['values']


def classify(tags, rules=None):
    # Specific barber/beauty/agritourism rules precede broader alternatives.
    rules = rules or config('osm')['rules']
    order = ['barber','stylistka','agroturystyka'] + [k for k in rules if k not in ('barber','stylistka','agroturystyka')]
    for key in order:
        if any(all(tag_matches(tags,c) for c in group) for group in rules[key]): return key
    return None


def build_query(region, industry=None):
    rules = config('osm')['rules']
    if set(rules) != set(industries()): raise ValueError('Reguły OSM muszą pokrywać wszystkie skonfigurowane branże')
    if industry and industry not in rules: raise ValueError('Nieznana branża')
    clauses = set()
    for key in ([industry] if industry else rules):
        for group in rules[key]:
            filters = '["name"]'
            for c in group:
                tag = json.dumps(c['key'])
                if 'contains' in c:
                    filters += f'[{tag}~{json.dumps(re.escape(c["contains"]))},i]'
                elif len(c['values']) == 1:
                    filters += f'[{tag}={json.dumps(c["values"][0])}]'
                else:
                    pattern = '^('+'|'.join(re.escape(v) for v in c['values'])+')$'
                    filters += f'[{tag}~{json.dumps(pattern)}]'
            clauses.add(f'nwr(around:{region["radius_m"]},{region["lat"]},{region["lon"]}){filters};')
    return '[out:json][timeout:25][maxsize:67108864];(\n'+'\n'.join(sorted(clauses))+'\n);out meta center 1500;'


def distance(lat, lon, region):
    a,b,c,d = map(math.radians,[lat,lon,region['lat'],region['lon']])
    return 6371000 * 2 * math.asin(min(1,math.sqrt(math.sin((a-c)/2)**2 + math.cos(a)*math.cos(c)*math.sin((b-d)/2)**2)))


def element_record(element, region, observed_day):
    if not isinstance(element,dict):return None
    tags = element.get('tags', {})
    if not isinstance(tags,dict) or not tags.get('name') or tags.get('access') == 'private': return None
    if any(tags.get(key) not in (None,'no','false','0') for key in ('disused','abandoned','demolished','closed')) or any(k.startswith(('disused:','abandoned:','demolished:')) for k in tags): return None
    industry = classify(tags)
    if not industry or element.get('type') not in ('node','way','relation') or type(element.get('id')) is not int: return None
    center = element.get('center',element)
    if not isinstance(center,dict):return None
    lat,lon = center.get('lat'),center.get('lon')
    if type(lat) not in (int,float) or type(lon) not in (int,float) or not math.isfinite(lat+lon) or distance(lat,lon,region)>region['radius_m']: return None
    source = f'https://www.openstreetmap.org/{element["type"]}/{element["id"]}'
    website = None
    for field in ('contact:website','website'):
        candidate = str(tags.get(field,'')).strip()
        if candidate and candidate.casefold() not in ('no','none','unknown','yes'):
            if '://' not in candidate: candidate = 'https://'+candidate
            try: website = url(candidate,'website'); break
            except ValueError: pass
    fact = {'value':'present' if website else 'unknown','source_url':source,'verified_at':observed_day,'note':'OSM podaje adres WWW; dostępność wymaga osobnego sprawdzenia.' if website else 'OSM nie podaje obsługiwanego adresu WWW. To nie potwierdza braku strony.'}
    contacts = []
    for kind,fields in [('email',['contact:email','email']),('phone',['contact:phone','phone'])]:
        for field in fields:
            for value in str(tags.get(field,'')).split(';'):
                value = value.strip().removeprefix('mailto:').removeprefix('tel:')
                if not value: continue
                if kind == 'email' and not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",value): continue
                if kind == 'phone' and (not re.fullmatch(r'\+?[0-9 ()-]{7,30}',value) or not 7<=len(re.sub(r'\D','',value))<=15): continue
                item={'kind':kind,'value':value,'source_url':source,'verified_at':observed_day}
                if item not in contacts: contacts.append(item)
    city = tags.get('addr:city') or tags.get('addr:place') or 'Nieustalona miejscowość (OSM)'
    address = ' '.join(str(tags[k]) for k in ('addr:street','addr:housenumber','addr:postcode') if tags.get(k))
    if str(tags.get('addr:country','PL')).upper() != 'PL': return None
    raw = {'name':tags['name'],'industry':industry,'city':city,'voivodeship':region['voivodeship'],'country':'PL','address':address,'website':website,'contacts':contacts,'source':{'provider':'openstreetmap','id':f'{element["type"]}/{element["id"]}','url':source},'last_verified_at':observed_day,'activity_signs':[],'facts':{'website_status':fact},'services':[],'description':'','fictional':False,'geo':{'lat':lat,'lon':lon},'source_metadata':{'license':'ODbL-1.0','attribution':ATTRIBUTION,'copyright_url':COPYRIGHT,'osm_timestamp':str(element.get('timestamp','nieustalony')),'classification_note':config('osm')['classification_note']}}
    try: return validate_record(raw)
    except (ValueError,TypeError): return None


class OverpassSource:
    def __init__(self, client, region='poznan'):
        self.client = client; self.region = region_config(region); self.diagnostics = {}

    def search(self, *, limit=25, industry=None, **filters):
        if not 1 <= limit <= 30: raise ValueError('Limit przebiegu: 1–30 firm')
        query = build_query(self.region,industry)
        response = self.client.request(self.client.cfg['overpass_endpoint'],method='POST',data=urlencode({'data':query}).encode(),overpass=True)
        if response.status != 200: raise NetworkError(f'Overpass HTTP {response.status}')
        try: payload = json.loads(response.body)
        except (ValueError,UnicodeError) as exc: raise NetworkError('Overpass nie zwrócił JSON') from exc
        if not isinstance(payload,dict) or payload.get('remark') or not isinstance(payload.get('elements'),list): raise NetworkError('Overpass zwrócił niepełne dane/błąd; przerwano import')
        day = dt.datetime.fromtimestamp(response.fetched_at,dt.timezone.utc).date().isoformat()
        records = {}; seen_businesses=set()
        for element in payload['elements']:
            record = element_record(element,self.region,day)
            if record and matches(record,industry=industry,**filters): records[record['source']['id']] = record
        groups = defaultdict(list)
        for r in records.values(): groups[r['industry']].append(r)
        for rows in groups.values(): rows.sort(key=lambda r:(distance(r['geo']['lat'],r['geo']['lon'],self.region),r['source']['id']))
        selected=[]
        while len(selected)<limit and any(groups.values()):
            for key in sorted(groups):
                if not groups[key]: continue
                r=groups[key].pop(0)
                # Node + building duplicates with identical business/location are sampled once.
                identity=(r['name'].casefold(),r['city'].casefold(),r['address'].casefold())
                if identity in seen_businesses: continue
                seen_businesses.add(identity);selected.append(r)
                if len(selected)==limit: break
        self.diagnostics={'source_objects':len(payload['elements']),'source_may_be_truncated':len(payload['elements'])>=1500,'mapped_candidates':len(records),'selected':len(selected),'cached_source':response.cached,'attribution':ATTRIBUTION,'copyright_url':COPYRIGHT}
        return selected


class PageSignals(HTMLParser):
    def __init__(self):
        super().__init__(); self.viewport=False; self.legacy=False; self.http_assets=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='meta' and a.get('name','').lower()=='viewport' and 'width=device-width' in a.get('content','').replace(' ','').lower(): self.viewport=True
        if tag=='frameset' or tag in ('embed','object') and ('shockwave-flash' in a.get('type','').lower() or re.search(r'\.swf(?:[?#]|$)',a.get('src',a.get('data','')).lower())): self.legacy=True
        if tag in ('img','script','iframe','link') and a.get('src',a.get('href','')).lower().startswith('http://'): self.http_assets=True


def clean_final_url(value):
    p=urlsplit(value)
    return urlunsplit((p.scheme,p.netloc,p.path or '/','',''))


class SiteAuditor:
    def __init__(self,client): self.client=client;self.robots={}

    def allowed(self,target):
        p=urlsplit(target);origin=f'{p.scheme}://{p.netloc}'
        if origin not in self.robots:
            current=origin+'/robots.txt'; response=None
            for _ in range(self.client.cfg['max_redirects']+1):
                response=self.client.request(current)
                if response.status not in (301,302,303,307,308):break
                nxt=urljoin(current,response.headers.get('location',''))
                q=urlsplit(nxt)
                if q.hostname.removeprefix('www.') != p.hostname.removeprefix('www.') or q.path!='/robots.txt':raise NetworkError('Nieobsługiwane przekierowanie robots.txt')
                current=nxt
            if response.status==404: self.robots[origin]=None
            elif response.status==200:
                rp=RobotFileParser();rp.parse(response.body.decode('utf8',errors='replace').splitlines())
                delay=rp.crawl_delay('WebForgeProspectFinder') or rp.crawl_delay('*') or 0
                if delay>self.client.cfg['max_wait_seconds']:raise NetworkError('Crawl-delay przekracza limit; stronę pominięto')
                host=p.hostname;self.client.host_delays[host]=max(self.client.host_delays.get(host,0),delay)
                if delay:self.client.defer(host,delay)
                self.robots[origin]=rp
            else:raise NetworkError('robots.txt niedostępny/odmawia dostępu; brak oceny strony')
        rp=self.robots[origin]
        return rp is None or rp.can_fetch('WebForgeProspectFinder',target)

    def audit(self,record):
        if not record['website']:
            record['site_check']={'checked_at':dt.date.today().isoformat(),'outcome':'no_url','http_status':None,'final_url':None,'signals':[{'code':'unknown_website','detail':'Brak adresu w źródle — nie potwierdzono braku strony.'}]};return record
        current=record['website'];seen=set();response=None
        report={'checked_at':dt.date.today().isoformat(),'outcome':'unknown','http_status':None,'final_url':None,'signals':[]}
        try:
            for _ in range(self.client.cfg['max_redirects']+1):
                if current in seen:raise NetworkError('Pętla przekierowań')
                seen.add(current)
                if not self.allowed(current): report['outcome']='robots_disallowed';break
                response=self.client.request(current);report['http_status']=response.status;report['final_url']=clean_final_url(current)
                report['checked_at']=dt.datetime.fromtimestamp(response.fetched_at,dt.timezone.utc).date().isoformat()
                if response.status in (301,302,303,307,308):
                    target=urljoin(current,response.headers.get('location',''))
                    if not response.headers.get('location'):raise NetworkError('Przekierowanie bez Location')
                    current=target;continue
                break
            else:raise NetworkError('Przekroczono limit przekierowań')
            if report['outcome']=='robots_disallowed':
                report['signals'].append({'code':'robots_disallowed','detail':'Nie oceniono strony: robots.txt nie zezwala na pobranie.'})
            elif response:
                status=response.status
                if status in (401,403,407,429,451): report['outcome']='access_limited'
                elif status>=400:
                    report['outcome']='http_error'
                    if status in (404,410) or status>=500:
                        record['facts']['technical_issues']={'value':True,'source_url':record['website'],'verified_at':report['checked_at'],'note':f'Kontrolowane żądanie strony głównej zwróciło HTTP {status}; pojedynczy pomiar, możliwa awaria przejściowa.'}
                    else:report['signals'].append({'code':'unclassified_http','detail':f'HTTP {status}; bez przypisania punktów jakości na podstawie niejednoznacznej odpowiedzi.'})
                elif 200<=status<300:
                    report['outcome']='reachable'
                    if 'html' in response.headers.get('content-type','').lower():
                        parser=PageSignals();parser.feed(response.body.decode('utf8',errors='replace'))
                        if parser.legacy:
                            record['facts']['outdated']={'value':True,'source_url':record['website'],'verified_at':report['checked_at'],'note':'Wykryto frameset lub element Flash — oznaka starej technologii, nie ocena wyglądu ani wieku domeny.'}
                            report['signals'].append({'code':'legacy_markup','detail':'Wykryto Flash/frameset; wymaga ręcznej oceny zakresu modernizacji.'})
                        if not parser.viewport:report['signals'].append({'code':'viewport_not_detected','detail':'Nie wykryto responsywnego meta viewport. To wskazówka do weryfikacji, nie potwierdzony błąd mobilny.'})
                        if urlsplit(current).scheme=='https' and parser.http_assets:
                            report['signals'].append({'code':'http_assets','detail':'W HTML znaleziono adresy zasobów HTTP przy HTTPS; bez pobierania zasobów nie potwierdzono awarii.'})
                    else:report['signals'].append({'code':'not_html','detail':'Odpowiedź nie jest deklarowana jako HTML; brak analizy układu.'})
        except BudgetExceeded as exc: report['outcome']='budget_exceeded';report['signals'].append({'code':'budget','detail':str(exc)})
        except (NetworkError,ValueError,TypeError,AttributeError) as exc:
            report['outcome']='network_error';report['signals'].append({'code':'unverified','detail':str(exc)[:500]})
        record['site_check']=report
        return validate_record(record)


def discover_run(store, *, region='poznan', limit=25, workdir=None, industry=None, category='wszystkie', client=None):
    if not 1<=limit<=30:raise ValueError('Limit przebiegu: 1–30 firm')
    region_config(region)
    if industry and industry not in industries():raise ValueError('Nieznana branża')
    if category not in ('wszystkie','modernizacja'):raise ValueError('Nieznana kategoria')
    cfg=config('sources')
    if not cfg['network_fetch_enabled'] or not cfg['adapters'].get('osm-overpass',{}).get('enabled'):raise ValueError('Źródło sieciowe wyłączone')
    folder=private_path(workdir or store.path.parent/'live');folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(folder,0o700)
    owned=client is None;client=client or HttpClient(folder/'network-cache.sqlite3')
    run_id=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:8]
    report={'version':2,'run_id':run_id,'source':'osm-overpass','region':region,'requested_limit':limit,'category':category,'outcome':'completed','real_companies_found':0,'stored_unique_records':0,'exported_records':0,'attribution':ATTRIBUTION,'license_url':COPYRIGHT,'limitations':['Dane OSM mogą być niepełne/nieaktualne. Klasyfikacja branży wymaga weryfikacji.','Brak WWW w OSM nie potwierdza braku strony. Edycja OSM i działające WWW nie potwierdzają aktywności firmy.']}
    try:
        source=OverpassSource(client,region);records=source.search(limit=limit,industry=industry)
        report['source_diagnostics']=source.diagnostics;report['real_companies_found']=len(records)
        auditor=SiteAuditor(client)
        records=[auditor.audit(record) for record in records]
        ids=list(dict.fromkeys(store.ingest(records))) if records else []
        report['stored_unique_records']=len(ids)
        rows=[store.get(i) for i in ids];rows=[r for r in rows if matches(r,category=category)]
        report['exported_records']=len(rows);report['outcomes']={k:sum(r.get('site_check',{}).get('outcome')==k for r in rows) for k in sorted({r.get('site_check',{}).get('outcome','unknown') for r in rows})}
        report['json_export']=str(export_records(rows,folder/f'{run_id}.json'))
        report['csv_export']=str(export_records(rows,folder/f'{run_id}.csv','csv'))
    except (NetworkError,ValueError,TypeError,json.JSONDecodeError) as exc:
        report['outcome']='blocked_or_failed';report['error']=str(exc)[:500]
    finally:
        report['network_requests']=client.requests;report['cache_hits']=client.cache_hits
        if owned:client.close()
    path=folder/f'{run_id}-report.json'
    with path.open('x',encoding='utf8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    os.chmod(path,0o600);report['report_path']=str(path)
    return report
