"""Backup publisher for definite Buffer authorization failures.

This module is not installed into the campaign workflow until live media and
provider publishing behaviour have been verified. An unknown result is held
for reconciliation; it is never blindly repeated.
"""
import hashlib
import json
import os
import urllib.parse
import urllib.request
from indiepost_guard import eligible

BASE='https://www.indiepost.app/api/v1/'
MAX_VIDEO=100_000_000

def call(path, data=None):
    headers={'Authorization':'Bearer '+os.environ['INDIEPOST_API_KEY'].strip()}
    if data is not None: headers['Content-Type']='application/json'
    req=urllib.request.Request(BASE+path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)

def upload_video(url):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ('github.com','raw.githubusercontent.com'):
        raise ValueError('Untrusted campaign video URL')
    with urllib.request.urlopen(url,timeout=90) as r: video=r.read(MAX_VIDEO+1)
    if not 1000<=len(video)<=MAX_VIDEO: raise ValueError('Video size invalid')
    media=call('media',{'filename':'cwhereucheaper-recovery.mp4','mimeType':'video/mp4','size':len(video)})
    target=media['upload']['url']
    if urllib.parse.urlparse(target).scheme!='https': raise ValueError('Non-HTTPS upload refused')
    req=urllib.request.Request(target,data=video,headers={'Content-Type':'video/mp4'},method='PUT')
    with urllib.request.urlopen(req,timeout=90) as r:
        if r.status not in (200,201,204):raise RuntimeError('Upload failed')
    call('media/confirm',{'mediaId':media['mediaId']})
    return media['mediaId']

def payload(ledger, service, row, media_id):
    text=row['text']; title=ledger['content']['title']
    data={'mediaIds':[media_id], 'platforms':[service], 'caption':text, 'when':'now'}
    if service=='youtube':data['youtube']={'title':title+' #Shorts','format':'short','aiGenerated':True}
    if service=='tiktok':data['tiktok']={'privacyLevel':'PUBLIC_TO_EVERYONE','commercialYourBrand':True,'aiGenerated':True}
    if service=='facebook':data['facebook']={'format':'reel','aiGenerated':True}
    return data

def key_for(slot,service):
    return 'cwuc-recovery-'+hashlib.sha256((slot+'/'+service).encode()).hexdigest()

def submit(data,key):
    request=urllib.request.Request(BASE+'posts',data=json.dumps(data).encode(),method='POST',headers={
        'Authorization':'Bearer '+os.environ['INDIEPOST_API_KEY'].strip(),
        'Content-Type':'application/json','Idempotency-Key':key})
    with urllib.request.urlopen(request,timeout=90) as response:return json.load(response)

def recover(ledger, service, channel_id, fetch_rows, save_ledger, now, upload=upload_video, send=submit):
    """Recover only a definitely rejected exact post, without touching Buffer.

    Callbacks allow a live re-read immediately before submission. Persisting
    'sending' before the call means a timeout or crash requires reconciliation.
    """
    def current():
        expected=((ledger.get('posts') or {}).get(service) or {})
        ident=expected.get('id')
        text=expected.get('text')
        all_rows=fetch_rows()
        if not ident or not text:return []
        matches=[r for r in all_rows if r.get('channelId')==channel_id and r.get('text')==text]
        if len(matches)!=1 or matches[0].get('id')!=ident:return []
        return matches
    rows=current()
    if not eligible(ledger,service,rows,now):return 'not_eligible'
    item=ledger.get('content') or {}
    if not isinstance(rows[0].get('text'),str) or not item.get('title') or not ledger.get('video'):
        return 'not_eligible'
    states=ledger.setdefault('indiepost_fallback',{})
    state=states.setdefault(service,{})
    if state.get('phase') in ('sending','submitted','confirmed'):
        return state['phase']
    if state.get('phase') not in (None,'media_ready'):
        return 'unknown'
    if not state.get('media_id'):
        state['media_id']=upload(ledger.get('delivery_video') or ledger['video'])
        state['phase']='media_ready'
        save_ledger(ledger)
    rows=current()
    if not eligible(ledger,service,rows,now):return 'not_eligible'
    data=payload(ledger,service,rows[0],state['media_id'])
    state['phase']='sending'
    state['request_digest']=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    save_ledger(ledger)
    result=send(data,key_for(ledger['slot'],service))
    post_id=result.get('postGroupId')
    if not isinstance(post_id,str) or not post_id:raise RuntimeError('Uncertain provider response; do not retry')
    state['post_group_id']=post_id
    state['phase']='submitted'
    save_ledger(ledger)
    return 'submitted'
