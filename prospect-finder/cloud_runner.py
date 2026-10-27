"""GitHub Actions wrapper. Never prints companies, raw errors, credentials or SQL."""
from __future__ import annotations
import argparse
import base64
from contextlib import redirect_stdout, redirect_stderr
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
from urllib.parse import quote

from finder import Store, config, industries, private_path
from live import discover_run, region_config

SOURCE_REPO='Yormiii/Moja-strona'
STATE_PATH='state/prospect-state.tar.gpg'
MAX_ENCRYPTED=20*1024*1024
MAX_EXPANDED=150*1024*1024


def key_from_env():
    key=os.environ.get('PROSPECT_DATA_KEY','')
    if not re.fullmatch(r'[a-fA-F0-9]{64}',key):raise ValueError('PROSPECT_DATA_KEY: wymagany losowy klucz 64 hex')
    return key


def crypt(source,destination,key,decrypt=False):
    source=private_path(source);destination=private_path(destination)
    if destination.exists():raise FileExistsError('Plik wyjściowy istnieje')
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not re.fullmatch(r'[a-fA-F0-9]{64}',key):raise ValueError('Nieprawidłowy klucz')
    # Secret is passed through an inherited pipe, not command line or a file.
    with tempfile.TemporaryDirectory(prefix='webforge-gpg-',dir=destination.parent) as home:
        os.chmod(home,0o700);read_fd,write_fd=os.pipe()
        try:
            os.write(write_fd,(key+'\n').encode());os.close(write_fd);write_fd=None
            cmd=['gpg','--homedir',home,'--batch','--yes','--no-autostart','--no-symkey-cache','--pinentry-mode','loopback','--passphrase-fd',str(read_fd),'--output',str(destination)]
            cmd+=['--decrypt'] if decrypt else ['--symmetric','--cipher-algo','AES256','--s2k-mode','3','--s2k-count','65011712','--compress-algo','none']
            cmd+=[str(source)]
            result=subprocess.run(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(read_fd,),timeout=120)
            if result.returncode:
                destination.unlink(missing_ok=True);raise ValueError('Szyfrowanie/odszyfrowanie nie powiodło się')
            os.chmod(destination,0o600)
        finally:
            os.close(read_fd)
            if write_fd is not None:os.close(write_fd)


def archive_tree(source,destination,*,state_only=False):
    source=private_path(source);destination=private_path(destination)
    state_names=['prospects.sqlite3','live/network-cache.sqlite3']
    candidates=[source/name for name in state_names] if state_only else sorted(source.rglob('*'))
    with tarfile.open(destination,'w:gz') as archive:
        for path in candidates:
            if not path.exists():continue
            if path.is_symlink():raise ValueError('Symlink w archiwum')
            if not path.is_file():continue
            name=path.relative_to(source).as_posix()
            if path.suffix=='.sqlite3':
                # Consistent backup includes committed WAL data without leaking journals.
                with tempfile.TemporaryDirectory(prefix='webforge-db-',dir=destination.parent) as tmp:
                    backup=Path(tmp)/'copy.sqlite3';a=sqlite3.connect(f'file:{path}?mode=ro',uri=True);b=sqlite3.connect(backup)
                    try:a.backup(b)
                    finally:a.close();b.close()
                    archive.add(backup,arcname=name,recursive=False)
            elif not name.endswith(('-wal','-shm','-journal')):
                archive.add(path,arcname=name,recursive=False)
    os.chmod(destination,0o600)


def restore_state(archive,destination):
    destination=private_path(destination);destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    allowed={'prospects.sqlite3','live/network-cache.sqlite3'}
    with tarfile.open(archive,'r:gz') as stream:
        members=stream.getmembers()
        if len({m.name for m in members})!=len(members) or any(not m.isfile() or m.name not in allowed for m in members) or sum(m.size for m in members)>MAX_EXPANDED:
            raise ValueError('Nieprawidłowe archiwum stanu')
        if not any(m.name=='prospects.sqlite3' for m in members):raise ValueError('Brak bazy w archiwum')
        for member in members:
            target=private_path(destination/member.name)
            if destination not in target.parents or target.exists():raise ValueError('Niebezpieczna ścieżka odtwarzania')
            target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            body=stream.extractfile(member)
            with target.open('xb') as output:shutil.copyfileobj(body,output)
            os.chmod(target,0o600)
            db=sqlite3.connect(f'file:{target}?mode=ro',uri=True)
            try:
                if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Uszkodzona baza')
            finally:db.close()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None


def github_api(path,token,method='GET',payload=None):
    # Token can only be sent to api.github.com, with no redirect following.
    if not token or not path.startswith('/repos/'):raise ValueError('Brak autoryzacji stanu')
    req=urllib.request.Request('https://api.github.com'+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'WebForgeProspectFinder/0.3'},method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as response:
            raw=response.read(30*1024*1024+1)
            if len(raw)>30*1024*1024:raise ValueError('Za duża odpowiedź stanu')
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        if exc.code==404:return None
        raise ValueError('Operacja API stanu nie powiodła się') from None


class PrivateRepositoryState:
    def __init__(self,name,token,api=github_api):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',name or '') or name.casefold()==SOURCE_REPO.casefold():raise ValueError('Wymagane osobne prywatne repozytorium stanu')
        self.name=name;self.token=token;self.api=api;self.sha=None
        info=api('/repos/'+name,token)
        if not info or info.get('private') is not True or not info.get('default_branch'):raise ValueError('Repozytorium stanu musi być prywatne i zainicjowane')
        self.branch=info['default_branch']

    def load(self,destination):
        metadata=self.api(f'/repos/{self.name}/contents/{STATE_PATH}?ref={quote(self.branch,safe="")}',self.token)
        if metadata is None:return False
        if metadata.get('type')!='file' or not 0<metadata.get('size',0)<=MAX_ENCRYPTED:raise ValueError('Nieprawidłowy rozmiar stanu')
        self.sha=metadata['sha'];blob=self.api(f'/repos/{self.name}/git/blobs/{self.sha}',self.token)
        if not blob or blob.get('encoding')!='base64':raise ValueError('Nieprawidłowy plik stanu')
        data=base64.b64decode(blob['content'])
        if len(data)!=metadata['size'] or len(data)>MAX_ENCRYPTED:raise ValueError('Nieprawidłowa zawartość stanu')
        with Path(destination).open('xb') as stream:stream.write(data)
        os.chmod(destination,0o600);return True

    def save(self,source):
        # Verify privacy again; never overwrite a newer state with an old lease.
        info=self.api('/repos/'+self.name,self.token)
        if not info or info.get('private') is not True:raise ValueError('Repozytorium stanu nie jest już prywatne')
        data=Path(source).read_bytes()
        if len(data)>MAX_ENCRYPTED:raise ValueError('Stan przekracza limit 20 MiB')
        payload={'message':'Update encrypted Prospect Finder state','content':base64.b64encode(data).decode(),'branch':self.branch}
        if self.sha:payload['sha']=self.sha
        result=self.api(f'/repos/{self.name}/contents/{STATE_PATH}',self.token,'PUT',payload)
        if not result:raise ValueError('Nie zapisano stanu')


def public_summary(report,storage,restored,errors):
    fields=['real_companies_found','new_records','duplicate_records','with_website','potential_modernizations','network_requests','cache_hits']
    counts={k:report.get(k) if type(report.get(k)) is int and report[k]>=0 else None for k in fields}
    top=[{'score':r['score'],'coverage_percent':r['coverage_percent']} for r in report.get('top_scores',[]) if type(r.get('score')) is int and 0<=r['score']<=100 and type(r.get('coverage_percent')) is int and 0<=r['coverage_percent']<=100]
    outcomes={k:v for k,v in report.get('outcomes',{}).items() if k in ('no_url','unknown','reachable','http_error','access_limited','robots_disallowed','network_error','budget_exceeded') and type(v) is int and v>=0}
    allowed_errors={'preflight_failed','state_restore_failed','discovery_failed','packaging_failed','state_save_failed','discovery_blocked_or_failed'}
    safe_errors=[e if e in allowed_errors else 'runner_failed' for e in errors]
    return {'version':3,'outcome':report.get('outcome') if report.get('outcome') in ('completed','blocked_or_failed') else 'not_started','storage':storage if storage in ('temporary','private-repository') else 'invalid','state_restored':bool(restored),**counts,'top_scores':top,'website_outcomes':outcomes,'errors':safe_errors,'limitations':['Próbka OSM wymaga weryfikacji; brak WWW nie potwierdza braku strony.','Pełne rekordy i błędy są tylko w zaszyfrowanej paczce.','Artefakty są tymczasowe; ciągłość deduplikacji wymaga trybu private-repository.']}


def markdown(summary):
    labels={'real_companies_found':'Znalezione firmy','new_records':'Nowe','duplicate_records':'Zduplikowane / już znane','with_website':'Z podanym adresem WWW','potential_modernizations':'Potencjalne modernizacje','network_requests':'Żądania HTTP','cache_hits':'Odczyty z cache'}
    lines=['# WebForge Prospect Finder v0.3','',f"Stan: `{summary['outcome']}`",f"Magazyn: `{summary['storage']}`; odtworzono stan: `{summary['state_restored']}`",'','| Miara | Liczba |','|---|---:|']
    for key,label in labels.items():lines.append(f"| {label} | {summary[key] if summary[key] is not None else 'nieustalono'} |")
    lines+=['','Najwyższe wyniki (bez danych firm): '+(', '.join(str(x['score'])+'/100' for x in summary['top_scores']) or 'brak danych'),'','Wyniki kontroli WWW: '+(', '.join(f'{k}: {v}' for k,v in summary['website_outcomes'].items()) or 'nieustalono'),'', 'Błędy: '+(', '.join(summary['errors']) or 'brak zgłoszonych'),'',*['- '+x for x in summary['limitations']]]
    return '\n'.join(lines)+'\n'


def run_cloud(args,discover=discover_run):
    report={};errors=[];restored=False;store=None;state=None;stage='preflight';success=False
    output=private_path(args.output);work=private_path(args.workdir)
    output.mkdir(parents=True,exist_ok=True,mode=0o700);work.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(work,0o700);os.chmod(output,0o700)
    try:
        key=key_from_env();region_config(args.region)
        if not shutil.which('gpg'):raise ValueError('Wymagany GnuPG')
        industry=None if args.industry=='all' else args.industry
        if industry and industry not in industries() or not 1<=args.limit<=30:raise ValueError('Nieprawidłowe parametry')
        if args.storage not in ('temporary','private-repository'):raise ValueError('Nieprawidłowy magazyn')
        if any(work.iterdir()) or (output/'results.tar.gpg').exists():raise ValueError('Wymagane puste katalogi przebiegu')
        stage='state_restore'
        if args.storage=='private-repository':
            state=PrivateRepositoryState(args.state_repository,os.environ.get('PROSPECT_STATE_TOKEN',''))
            encrypted=output/'restored.tar.gpg'
            if state.load(encrypted):
                plain=output/'restored.tar.gz';crypt(encrypted,plain,key,decrypt=True)
                try:restore_state(plain,work);restored=True
                finally:plain.unlink(missing_ok=True);encrypted.unlink(missing_ok=True)
        stage='discovery';store=Store(work/'prospects.sqlite3')
        # A future discovery implementation must not leak raw stdout to public logs.
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            report=discover(store,region=args.region,limit=args.limit,industry=industry,category=args.category,workdir=work/'live')
        store.close();store=None
        if report['outcome']!='completed':errors.append('discovery_blocked_or_failed')
        stage='packaging'
        with tempfile.TemporaryDirectory(prefix='webforge-bundle-',dir=output) as temp:
            plain=Path(temp)/'results.tar.gz';archive_tree(work,plain);crypt(plain,output/'results.tar.gpg',key)
            if state:
                state_plain=Path(temp)/'state.tar.gz';state_encrypted=Path(temp)/'state.tar.gpg'
                archive_tree(work,state_plain,state_only=True);crypt(state_plain,state_encrypted,key)
                stage='state_save';state.save(state_encrypted)
        success=report.get('outcome')=='completed'
    except Exception:
        # Never log exception details: they can contain a URL, token or record.
        errors.append(stage+'_failed')
    finally:
        if store:store.close()
    summary=public_summary(report,args.storage,restored,errors)
    if errors:summary['outcome']='failed'
    safe=markdown(summary)
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'summary.md').write_text(safe,encoding='utf8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf8') as stream:stream.write(safe)
    print(safe)
    return 0 if success and not errors else 1


def main(argv=None):
    parser=argparse.ArgumentParser(description='Cloud wrapper: szyfrowane wyniki, bez publicznych rekordów')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--region',default='poznan');run.add_argument('--industry',default='all');run.add_argument('--limit',type=int,default=25);run.add_argument('--category',choices=['wszystkie','modernizacja'],default='wszystkie');run.add_argument('--storage',choices=['temporary','private-repository'],default='temporary');run.add_argument('--state-repository',default='');run.add_argument('--workdir',required=True);run.add_argument('--output',required=True)
    decrypt=sub.add_parser('decrypt');decrypt.add_argument('--input',required=True);decrypt.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    if args.command=='run':return run_cloud(args)
    crypt(args.input,args.output,key_from_env(),decrypt=True);print('Odszyfrowano prywatne archiwum TAR.GZ. Nie kopiuj go do repozytorium.');return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError):print('Nie wykonano operacji. Sprawdź parametry, prywatne ścieżki i konfigurację sekretów.',file=__import__('sys').stderr);raise SystemExit(1)
