"""Render and update a coarse public status page; accepts no user content."""
import base64
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from health_signal import validate

API='https://api.github.com/repos/hancra09/cwhereucheaper-social-campaign/'
TAG='viewer-response-health'
SAST=dt.timezone(dt.timedelta(hours=2))
MARKER=re.compile(r'^<!-- CWUC_HEALTH ([A-Za-z0-9+/=]+) -->')


def render(state):
    encoded=base64.b64encode(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).decode()
    lines=['<!-- CWUC_HEALTH '+encoded+' -->','# Viewer response monitor','',
       'Only general status appears here. Viewer comments, names and counts are not published.','']
    selector=state.get('selector')
    lines+=['## Request handling','']
    if selector:
        f=selector['flags'];when=selector['checked_at_sast']
        lines += ['Checked: '+when, '',
          '- Comment sources: '+('available' if f['sources']=='available' else 'need attention'),
          '- Requests outside supported scope: '+{'none':'none observed','present':'need review','unknown':'unknown'}[f['unhandled']],
          '- Requests waiting unusually long: '+{'present':'need review','none':'none observed','unknown':'unknown'}[f['stalled']],
          '- Processing: '+('working' if f['processing']=='ok' else 'needs attention'),'']
    else:lines+=['Not checked yet.','']
    native=state.get('native');lines+=['## Latest response publication','']
    if native and native['flags']['slot']:
        f=native['flags'];lines+=['Checked: '+native['checked_at_sast'],'',
          '- YouTube: '+{'public_confirmed':'public confirmed','pending':'pending','unknown':'unknown','none':'not checked'}[f['youtube']],
          '- TikTok: '+{'found_owned':'found in account','pending':'pending','unknown':'unknown','none':'not checked'}[f['tiktok']],
          '- Facebook: '+{'found_owned':'found in account','pending':'pending','unknown':'unknown','none':'not checked'}[f['facebook']],
          '', 'Account presence does not confirm TikTok or Facebook public visibility or recommendation eligibility.',
          '', '[View public post links](https://github.com/hancra09/cwhereucheaper-social-campaign/releases/tag/response-native-'+f['slot']+')','']
    else:lines+=['No response publication has been checked yet.','']
    return '\n'.join(lines)+'\n'


def decode(body):
    if not body:return {}
    m=MARKER.match(body)
    if not m:raise ValueError('Unexpected existing health page')
    state=json.loads(base64.b64decode(m.group(1),validate=True))
    if not isinstance(state,dict) or set(state)-{'selector','native'}:raise ValueError('Invalid health page state')
    for component,value in state.items():validate(component,value['flags'])
    return state


def api(path,token,body=None,method=None):
    req=urllib.request.Request(API+path,data=json.dumps(body).encode() if body is not None else None,method=method,
      headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json',
               'X-GitHub-Api-Version':'2022-11-28','User-Agent':'CWUC-coarse-health/1'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)


def update(component,flags,observed,token,call=api,now=None):
    validate(component,flags)
    instant=dt.datetime.fromisoformat(observed.replace('Z','+00:00'));now=now or dt.datetime.now(dt.timezone.utc)
    if instant.tzinfo is None or not dt.timedelta(minutes=-5)<=now-instant<=dt.timedelta(hours=2):raise ValueError('Stale health observation')
    try:release=call('releases/tags/'+TAG,token)
    except urllib.error.HTTPError as exc:
        if exc.code!=404:raise
        release=None
    state=decode(release.get('body','') if release else '')
    previous=state.get(component)
    # A delayed job cannot overwrite a more recent observation.
    if previous and dt.datetime.fromisoformat(previous['checked_at_sast'])>instant:return False
    state[component]={'flags':flags,'checked_at_sast':instant.astimezone(SAST).isoformat(timespec='seconds')}
    content=render(state)
    if release:call('releases/'+str(release['id']),token,{'body':content},'PATCH')
    else:call('releases',token,{'tag_name':TAG,'name':'Viewer response health','body':content,'draft':False,'prerelease':True},'POST')
    return True


def main():
    update(os.environ['HEALTH_COMPONENT'],json.loads(os.environ['HEALTH_PAYLOAD']),os.environ['HEALTH_OBSERVED_AT'],os.environ['GH_TOKEN'])
    print('Coarse public health page updated; no comments, names or counts included.')

if __name__=='__main__':main()
