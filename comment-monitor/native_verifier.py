"""Verify response publication against native accounts; never posts or sends messages."""
import datetime as dt
import json
import os
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from contextlib import closing
from pathlib import Path

GITHUB='https://api.github.com/repos/hancra09/cwhereucheaper-social-campaign/releases'
YOUTUBE='https://www.googleapis.com/youtube/v3/videos'
CHANNEL='UCRZrhWYIMqPVITDfWq8piUg'
SAST=dt.timezone(dt.timedelta(hours=2))
SLOTS={'early':dt.time(8),'am':dt.time(12,30),'pm':dt.time(18,30)}
TIKTOK=Path('/var/lib/private/cwhereu-tiktok-comments/comments.sqlite')
FACEBOOK=Path('/var/lib/private/cwhereu-facebook-comments/comments.sqlite')


def get_json(url,headers=None):
    req=urllib.request.Request(url,headers={'User-Agent':'CWUC-native-response-verifier/1',**(headers or {})})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)


def records(fetch=get_json,now=None):
    now=now or dt.datetime.now(dt.timezone.utc);cutoff=now-dt.timedelta(days=8);out=[]
    for page in range(1,11):
        data=fetch(GITHUB+'?per_page=100&page='+str(page),{'Accept':'application/vnd.github+json'})
        if not isinstance(data,list):raise ValueError('Invalid release list')
        for release in data:
            if str(release.get('tag_name','')).startswith('response-native-'):
                published=dt.datetime.fromisoformat(release['published_at'].replace('Z','+00:00'))
                if published>=cutoff:
                    body=json.loads(release.get('body') or '{}')
                    out.append(body)
        if len(data)<100:return out
    raise RuntimeError('Incomplete release inventory')


def identify(service,url):
    if not isinstance(url,str):return None
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.username or u.password:return None
    host=(u.hostname or '').lower()
    if service=='youtube' and host=='www.youtube.com':pat=r'/shorts/([A-Za-z0-9_-]{11})/?'
    elif service=='tiktok' and host=='www.tiktok.com':pat=r'/@cwhereucheaper\.co/video/([0-9]+)/?'
    elif service=='facebook' and host=='www.facebook.com':pat=r'/reel/([0-9]+)/?'
    else:return None
    m=re.fullmatch(pat,u.path,re.I)
    return m.group(1) if m else None


def due_time(slot):
    m=re.fullmatch(r'([0-9]{8})-(early|am|pm)',str(slot))
    if not m:raise ValueError('Invalid slot')
    day=dt.datetime.strptime(m.group(1),'%Y%m%d').date()
    return dt.datetime.combine(day,SLOTS[m.group(2)],SAST).astimezone(dt.timezone.utc)


def inventory(path,service,due,now):
    try:
        with closing(sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True,timeout=10)) as db:
            row=db.execute('SELECT checked FROM polls WHERE id=1').fetchone()
            if not row:return None
            checked=dt.datetime.fromisoformat(row[0]).replace(tzinfo=dt.timezone.utc)
            if checked<due or not dt.timedelta(minutes=-5)<=now-checked<=dt.timedelta(hours=2):return None
            if service=='tiktok':return {str(r[0]) for r in db.execute('SELECT id FROM published_posts')}
            refs=set()
            for (url,) in db.execute('SELECT permalink FROM published_posts'):
                u=urllib.parse.urlsplit(url or '')
                if (u.hostname or '').lower() not in ('facebook.com','www.facebook.com','m.facebook.com'):continue
                m=re.fullmatch(r'/reel/([0-9]+)/?',u.path)
                if m:refs.add(m.group(1))
            return refs
    except (OSError,sqlite3.Error,ValueError,TypeError):return None


def youtube(id,key,fetch=get_json,due=None,now=None):
    if not key or not re.fullmatch(r'[A-Za-z0-9_-]{11}',id):return 'unknown'
    try:
        params=urllib.parse.urlencode({'part':'snippet,status','id':id})
        data=fetch(YOUTUBE+'?'+params,{'X-Goog-Api-Key':key})
        rows=data.get('items',[])
        if len(rows)!=1 or rows[0].get('id')!=id:return 'unknown'
        snippet=rows[0].get('snippet',{})
        if snippet.get('channelId')!=CHANNEL:return 'unknown'
        if due is not None:
            published=dt.datetime.fromisoformat(snippet['publishedAt'].replace('Z','+00:00'))
            now=now or dt.datetime.now(dt.timezone.utc)
            if published.tzinfo is None or not due-dt.timedelta(minutes=15)<=published<=now+dt.timedelta(minutes=5):return 'unknown'
        return 'public_confirmed' if rows[0].get('status',{}).get('privacyStatus')=='public' else 'unknown'
    except Exception:return 'unknown'


def verify(record,key,now=None,fetch=get_json,tiktok=TIKTOK,facebook=FACEBOOK):
    now=now or dt.datetime.now(dt.timezone.utc)
    tag=record['slot'];due=due_time(tag)
    if not re.fullmatch(r'[a-f0-9]{32}',str(record.get('request_id',''))):raise ValueError('Invalid request ID')
    result={}
    for service in ('youtube','tiktok','facebook'):
        row=record.get('posts',{}).get(service,{})
        if row.get('status')!='sent':result[service]='pending' if row.get('status') in ('scheduled','sending') else 'unknown';continue
        ident=identify(service,row.get('url'))
        if not ident:result[service]='unknown';continue
        if service=='youtube':result[service]=youtube(ident,key,fetch,due,now)
        else:
            source=inventory(tiktok if service=='tiktok' else facebook,service,due,now)
            result[service]='found_owned' if source is not None and ident in source else 'unknown'
    return result


def store(path,record,result,now=None):
    now=now or dt.datetime.now(dt.timezone.utc);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with closing(sqlite3.connect(path)) as db:
        os.chmod(path,0o600)
        db.execute('''CREATE TABLE IF NOT EXISTS checks(slot TEXT PRIMARY KEY,request_id TEXT NOT NULL,
            checked_utc TEXT NOT NULL, youtube TEXT NOT NULL,tiktok TEXT NOT NULL,facebook TEXT NOT NULL)''')
        with db:
            db.execute('''INSERT INTO checks VALUES(?,?,?,?,?,?) ON CONFLICT(slot) DO UPDATE SET
                request_id=excluded.request_id,checked_utc=excluded.checked_utc,youtube=excluded.youtube,
                tiktok=excluded.tiktok,facebook=excluded.facebook''',
                (record['slot'],record['request_id'],now.isoformat(),result['youtube'],result['tiktok'],result['facebook']))


def main():
    key=(Path(os.environ['CREDENTIALS_DIRECTORY'])/'youtube-api-key').read_text().strip()
    path=Path(os.environ['STATE_DIRECTORY'])/'verification.sqlite'
    rows=records();counts={'public_confirmed':0,'found_owned':0,'pending':0,'unknown':0};latest=None
    for record in rows:
        result=verify(record,key);store(path,record,result)
        if latest is None or due_time(record['slot'])>due_time(latest[0]['slot']):latest=(record,result)
        for status in result.values():counts[status]+=1
    print('Native response checks:',len(rows),'responses;',counts)
    try:
        from health_signal import emit
        flags={'slot':'','youtube':'none','tiktok':'none','facebook':'none'} if latest is None else {'slot':latest[0]['slot'],**latest[1]}
        token=(Path(os.environ['CREDENTIALS_DIRECTORY'])/'github-token').read_text().strip()
        emit('native',flags,Path(os.environ['STATE_DIRECTORY']),token)
    except Exception as exc:
        print('Coarse native status unavailable:',type(exc).__name__,file=sys.stderr)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Native response verification failed:',type(exc).__name__,file=sys.stderr);sys.exit(1)
