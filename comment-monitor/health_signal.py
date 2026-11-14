"""Publish coarse owner-visible status without comments, names, IDs or metrics."""
import datetime as dt
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

URL='https://api.github.com/repos/hancra09/cwhereucheaper-social-campaign/actions/workflows/monitor-health.yml/dispatches'
INTERVAL=dt.timedelta(hours=6)


def validate(component,flags):
    if not isinstance(flags,dict):raise ValueError('Invalid health flags')
    if component=='selector':
        allowed={'sources':{'available','attention'},'unhandled':{'none','present','unknown'},
                 'stalled':{'none','present','unknown'},'processing':{'ok','attention'}}
    elif component=='native':
        allowed={'slot':None,'youtube':{'none','public_confirmed','pending','unknown'},
                 'tiktok':{'none','found_owned','pending','unknown'},'facebook':{'none','found_owned','pending','unknown'}}
    else:raise ValueError('Invalid health component')
    if set(flags)!=set(allowed):raise ValueError('Invalid health fields')
    for k,choices in allowed.items():
        if choices is None:
            if not isinstance(flags[k],str):raise ValueError('Invalid public slot')
            if flags[k] and not re.fullmatch(r'[0-9]{8}-(early|am|pm)',flags[k]):raise ValueError('Invalid public slot')
        elif flags[k] not in choices:raise ValueError('Invalid health value')
    return flags


def emit(component,flags,state_dir,token,call=None,now=None):
    validate(component,flags)
    if not token:raise ValueError('Missing health credential')
    now=now or dt.datetime.now(dt.timezone.utc);path=Path(state_dir)/('health-'+component+'.json')
    encoded=json.dumps(flags,sort_keys=True,separators=(',',':'));digest=hashlib.sha256(encoded.encode()).hexdigest()
    if path.exists():
        previous=json.loads(path.read_text())
        last=dt.datetime.fromisoformat(previous['sent_at'])
        if previous.get('digest')==digest and dt.timedelta(0)<=now-last<INTERVAL:return False
    payload={'ref':'main','inputs':{'component':component,'payload':encoded,'observed_at':now.isoformat()}}
    if call is None:
        def call(url,data):
            req=urllib.request.Request(url,data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+token,
              'Accept':'application/vnd.github+json','Content-Type':'application/json',
              'X-GitHub-Api-Version':'2022-11-28','User-Agent':'CWUC-coarse-health/1'})
            with urllib.request.urlopen(req,timeout=25) as response:return response.status
    result=call(URL,payload)
    if result not in (200,201,202,204):raise RuntimeError('Health dispatch not accepted')
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps({'digest':digest,'sent_at':now.isoformat()}));os.chmod(tmp,0o600);os.replace(tmp,path)
    return True
