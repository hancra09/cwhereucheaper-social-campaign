"""Privately select explicit supported requests and dispatch no raw comment text."""
import datetime as dt
import hashlib
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from response import select

REPO='hancra09/cwhereucheaper-social-campaign'
API='https://api.github.com/repos/'+REPO+'/'
SOURCES={name:Path('/var/lib/private/cwhereu-'+name+'-comments/comments.sqlite') for name in ('youtube','tiktok','facebook')}


class Candidates(list):
    def __init__(self):
        super().__init__()
        self.available=set()


def read_candidates(paths=SOURCES):
    """No text is logged. Require recent successful polls and a known non-owner."""
    out=Candidates()
    for source,path in paths.items():
        try:
            with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True,timeout=10) as db:
                columns={row[1] for row in db.execute('PRAGMA table_info(comments)')}
                if 'owner' not in columns:
                    continue
                checked=db.execute('SELECT checked FROM polls WHERE id=1').fetchone()
                if not checked:
                    continue
                last=dt.datetime.fromisoformat(checked[0]).replace(tzinfo=dt.timezone.utc)
                age=dt.datetime.now(dt.timezone.utc)-last
                if age < dt.timedelta(minutes=-5) or age > dt.timedelta(hours=3):
                    continue
                out.available.add(source)
                for cid,body in db.execute('SELECT id,body FROM comments WHERE owner=0'):
                    topic=select(body)
                    if topic:
                        out.append((source,str(cid),hashlib.sha256(body.encode()).hexdigest(),topic))
        except (OSError,sqlite3.Error,ValueError,TypeError):
            out.available.discard(source)
            print('Comment source unavailable:',source,file=sys.stderr)
    return out


def api(path,token,payload=None):
    request=urllib.request.Request(API+path, data=json.dumps(payload).encode() if payload is not None else None,
        headers={**({} if path.startswith('releases/tags/') else {'Authorization':'Bearer '+token}), 'Accept':'application/vnd.github+json',
                 'Content-Type':'application/json','User-Agent':'CWUC-Viewer-Requests/1',
                 'X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(request,timeout=25) as resp:
        raw=resp.read()
        return json.loads(raw) if raw else None


def run(db, token, candidates, call=api):
    db.execute('''CREATE TABLE IF NOT EXISTS requests
        (source TEXT NOT NULL, comment_id TEXT NOT NULL, body_sha TEXT NOT NULL,
         topic TEXT NOT NULL, request_id TEXT NOT NULL, state TEXT NOT NULL,
         attempted_at TEXT, attempt INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
         PRIMARY KEY(source,comment_id,body_sha))''')
    for source,cid,digest,topic in candidates:
        recent=db.execute("SELECT 1 FROM requests WHERE topic=? AND state IN ('pending','dispatching','scheduled') AND datetime(created_at) >= datetime('now','-7 days') LIMIT 1",(topic,)).fetchone()
        if recent:
            continue
        db.execute('INSERT OR IGNORE INTO requests(source,comment_id,body_sha,topic,request_id,state) VALUES(?,?,?,?,?,?)',
                   (source,cid,digest,topic,uuid.uuid4().hex,'pending'))
    db.commit()
    pending=db.execute("SELECT source,comment_id,body_sha,topic,request_id,state,attempted_at,attempt FROM requests WHERE state IN ('pending','dispatching') ORDER BY rowid LIMIT 1").fetchone()
    if not pending:
        print('No supported viewer requests pending.')
        return
    source,cid,digest,topic,rid,state,attempted,attempt=pending
    if state=='dispatching':
        # No blind duplicate while the prior run may still be queued or executing.
        runs=call('actions/workflows/campaign.yml/runs?per_page=100',token)['workflow_runs']
        marker='viewer-'+rid+'-'+str(attempt)
        match=next((x for x in runs if marker in x.get('display_title','')),None)
        if match and match['status']!='completed':
            print('Viewer request workflow still running.')
            return
        try:
            rel=call('releases/tags/viewer-request-'+rid,token)
            result=json.loads(rel.get('body') or '{}')
            if result.get('state')=='scheduled':
                db.execute("UPDATE requests SET state='scheduled' WHERE request_id=?",(rid,)); db.commit()
                print('Viewer response scheduling verified.')
                return
        except urllib.error.HTTPError as exc:
            if exc.code!=404: raise
        # Give uncertain dispatches two hours; repeat with the same durable request ID.
        when=dt.datetime.fromisoformat(attempted)
        if dt.datetime.now(dt.timezone.utc)-when < dt.timedelta(hours=2):
            print('Viewer request awaiting safe reconciliation.')
            return
    if state == 'pending' and source not in getattr(candidates,'available',{source}):
        print('Request source unavailable; retaining request.')
        return
    if state == 'pending' and (source,cid,digest,topic) not in candidates:
        db.execute("UPDATE requests SET state='withdrawn' WHERE request_id=?",(rid,)); db.commit()
        print('Request no longer present; no response dispatched.')
        return
    # Persist before dispatch; only an opaque random ID and an allowed topic leave this host.
    attempt+=1
    stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    db.execute("UPDATE requests SET state='dispatching',attempted_at=?,attempt=? WHERE request_id=?",(stamp,attempt,rid)); db.commit()
    call('actions/workflows/campaign.yml/dispatches',token,{'ref':'main','inputs':{
        'mode':'viewer-response','dispatch_id':'viewer-'+rid+'-'+str(attempt),
        'request_topic':topic,'request_id':rid}})
    print('Supported viewer request dispatched for researched response.')


def main():
    state=Path(os.environ['STATE_DIRECTORY']); state.mkdir(mode=0o700,parents=True,exist_ok=True)
    token=(Path(os.environ['CREDENTIALS_DIRECTORY'])/'github-token').read_text().strip()
    if not token: raise ValueError('Missing credential')
    with sqlite3.connect(state/'requests.sqlite') as db:
        os.chmod(state/'requests.sqlite',0o600)
        run(db,token,read_candidates())

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('Viewer request check failed:',type(exc).__name__,file=sys.stderr)
        sys.exit(1)
