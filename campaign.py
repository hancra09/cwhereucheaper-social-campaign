"""Ongoing CWUC campaign. Standard library only; credentials never enter the ledger."""
import argparse
import base64
import datetime as dt
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import time
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from content_factory import build_month, theme_for, validate_plan
from media_delivery import publish as publish_delivery

SAST = dt.timezone(dt.timedelta(hours=2))
START = dt.date(2026, 11, 8)
LEGACY_END = dt.date(2026, 12, 7)
ORIGIN = 'https://www.cwhereucheaper.co.za'
REPO = 'hancra09/cwhereucheaper-social-campaign'
ORG = '6aeef1646c3957c58fdd3b19'
CHANNELS = {'youtube': '6aeef238e29c69a171916d83', 'tiktok': '6aeef202e29c69a171916c16',
    'facebook': '6aeef981e29c69a17191b79b'}
FACEBOOK_PAGE_ID = '1265683793295341'  # Public URL redirects to profile 61592840593333.
POST_FIELDS = 'id channelId status text dueAt externalLink error { message } assets { source }'
SLOTS = {'early': dt.time(8), 'am': dt.time(12, 30), 'pm': dt.time(18, 30)}
ROOT = Path(__file__).parent
AUDIT_DAYS = 7
DAILY_RENDER_LIMIT = 3
PREPARE_HOURS = 48
MIN_LEAD_HOURS = 2


def campaign_item(day, slot):
    items = json.loads(Path(__file__).with_name('content.json').read_text())
    third = json.loads(Path(__file__).with_name('content-third.json').read_text())
    assert len(items) == 60 and len(third) == 30
    assert len({i['title'] for i in items + third}) == 90
    assert START <= day, 'Before campaign start'
    assert slot in SLOTS, 'Unknown campaign slot'
    if day > LEGACY_END:
        month = day.strftime('%Y-%m')
        path = ROOT / 'plans' / (month + '.json')
        assert path.is_file(), 'Monthly content plan missing; no automatic recycling'
        plan = validate_plan(json.loads(path.read_text()), month)
        return next(x for x in plan['items'] if x['date'] == day.isoformat() and x['slot'] == slot)
    offset = (day - START).days
    # Preserve the original am/pm mapping and all previously queued captions.
    return third[offset] if slot == 'early' else items[offset * 2 + (slot == 'pm')]


def scheduled_slot(now):
    return 'early' if now.hour < 10 else 'am' if now.hour < 15 else 'pm'


def request(url, *, body=None, headers=None, method=None, opener=None):
    h = {'User-Agent': 'CWUC-Campaign/1.0', **(headers or {})}
    if isinstance(body, dict):
        body = json.dumps(body).encode()
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with (opener.open if opener else urllib.request.urlopen)(req, timeout=120) as r:
        return r.read()


def buffer(query, variables=None):
    result = json.loads(request('https://api.buffer.com', body={'query': query, 'variables': variables or {}},
        headers={'Authorization': 'Bearer ' + os.environ['BUFFER_API_KEY'].strip()}))
    if result.get('errors'):
        raise RuntimeError('Buffer: ' + json.dumps(result['errors']))
    return result['data']


def gh(path, body=None, method=None):
    return json.loads(request('https://api.github.com/repos/' + REPO + '/' + path,
        body=body, method=method, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}))


def write_public_json(path, data, message, *, replace=False):
    """Write only intended-public scripts or coarse content choices, never raw metrics."""
    prior = None
    try:
        prior = gh('contents/' + path)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    if prior and not replace:
        return json.loads(base64.b64decode(prior['content']))
    payload = {'message': message, 'content': base64.b64encode(
        (json.dumps(data, indent=2) + '\n').encode()).decode(), 'branch': 'main'}
    if prior:
        payload['sha'] = prior['sha']
    gh('contents/' + path, payload, 'PUT')
    return data


def ensure_plans(day):
    first = max(day, LEGACY_END + dt.timedelta(days=1)).replace(day=1)
    following = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    policy = ROOT / 'content-policy.json'
    preferred = json.loads(policy.read_text()).get('preferred_themes', []) if policy.exists() else []
    previous = {i['script'] for name in ('content.json', 'content-third.json')
                for i in json.loads((ROOT / name).read_text())}
    for existing in sorted((ROOT / 'plans').glob('*.json')):
        previous.update(i['script'] for i in json.loads(existing.read_text())['items'])
    for date in (first, following):
        month = date.strftime('%Y-%m')
        path = ROOT / 'plans' / (month + '.json')
        if path.exists():
            validate_plan(json.loads(path.read_text()), month)
            continue
        if not path.exists():
            plan = write_public_json('plans/' + month + '.json',
                build_month(month, preferred, previous), 'Prepare original shopping scripts for ' + month)
            validate_plan(plan, month)
            assert not ({i['script'] for i in plan['items']} & previous), 'Duplicate prior narration'
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(plan, indent=2) + '\n')
            previous.update(i['script'] for i in plan['items'])


def check_access_expiry(now):
    config = json.loads((ROOT / 'publishing-access.json').read_text())
    remaining = (dt.date.fromisoformat(config['expires']) - now.date()).days
    if remaining <= 30:
        print('::warning::Publishing access expires in ' + str(remaining)
              + ' days. Renew the restricted Buffer key and encrypted GitHub secret.')
    if remaining < 0:
        raise RuntimeError('Publishing credential has expired; renewal required.')


def load_release(tag):
    try:
        return gh('releases/tags/' + tag)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return gh('releases', {'tag_name': tag, 'name': tag, 'body': '{}', 'draft': False, 'prerelease': True})


def read_release(tag):
    try:
        return gh('releases/tags/' + tag)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def render_budget(now):
    release = read_release('render-budget-' + now.strftime('%Y%m%d'))
    return (json.loads(release['body'] or '{}').get('slots', []) if release else [])


def reserve_render(tag, now):
    release = load_release('render-budget-' + now.strftime('%Y%m%d'))
    ledger = json.loads(release['body'] or '{}')
    slots = ledger.setdefault('slots', [])
    if tag not in slots:
        if len(slots) >= DAILY_RENDER_LIMIT:
            raise RuntimeError('Daily three-render budget already reserved; no extra render.')
        slots.append(tag)
        save(release, ledger)


def save(release, ledger):
    # Durable before/after each publishing mutation; failed ambiguous sends reconcile first.
    gh('releases/' + str(release['id']), {'body': json.dumps(ledger, indent=2)}, 'PATCH')
    Path('last-run.json').write_text(json.dumps(ledger, indent=2))


def generate(item, release, ledger):
    existing = next((a for a in release['assets'] if a['name'] == 'video.mp4'), None)
    if existing:
        return existing['browser_download_url']
    if item.get('creative_version') == 'creative-v2':
        return creative_asset(item, release, ledger, new_slot=True)[0]
    if ledger.get('render_attempted'):
        raise RuntimeError('Previous render attempt has no stored media. Review before retrying; no duplicate quota use.')
    reserve_render(ledger['slot'], dt.datetime.now(SAST))
    ledger['render_attempted'] = True
    save(release, ledger)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    session = json.loads(request(ORIGIN + '/reels/api/session', opener=opener))
    voices = session['voices']
    voice = next((v['id'] for v in voices if 'emma' in json.dumps(v).lower()), None)
    if not voice:
        raise RuntimeError('Approved Emma voice unavailable; refusing to substitute silently.')
    payload = {'topic': item['title'] + '. Original South African shopping education. Use clear original motion graphics. '
        'Any arithmetic is illustrative, never a current retailer offer.', 'script': item['script'],
        'duration': 25, 'style': item.get('style', 'Educational'), 'voice': voice, 'assets': [],
        'stock': False, 'capture': False, 'music': False, 'music_track': '', 'rights_confirmed': True}
    job = json.loads(request(ORIGIN + '/reels/api/jobs', body=payload,
        headers={'Origin': ORIGIN, 'X-Reel-CSRF': session['csrf']}, opener=opener))
    job_id = job['id']
    ledger['render_job'] = job_id
    save(release, ledger)
    deadline = time.monotonic() + 1200
    while time.monotonic() < deadline:
        state = json.loads(request(ORIGIN + '/reels/api/jobs/' + job_id, opener=opener))
        if state['state'] == 'complete':
            break
        if state['state'] in ('failed', 'error', 'expired'):
            raise RuntimeError('Reels render failed: ' + str(state.get('error')))
        time.sleep(12)
    else:
        raise RuntimeError('Render did not complete within 20 minutes; no posts created.')
    data = request(ORIGIN + '/reels/media/' + job_id + '.mp4?download=1', opener=opener)
    if len(data) < 10000 or data[4:8] != b'ftyp':
        raise RuntimeError('Render download is not a valid MP4.')
    Path('video.mp4').write_bytes(data)
    # Fail closed on corrupt streams, missing sound or unexpected vertical dimensions.
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', 'video.mp4']))
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    assert (video['width'], video['height']) == (1080, 1920), 'Unexpected video dimensions'
    assert any(s['codec_type'] == 'audio' for s in info['streams']), 'Missing narration stream'
    assert 20 <= float(info['format']['duration']) <= 35, 'Unexpected duration'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', 'video.mp4', '-f', 'null', '-'], check=True)
    url = release['upload_url'].split('{')[0] + '?name=video.mp4'
    asset = json.loads(request(url, body=data, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Content-Type': 'video/mp4', 'Accept': 'application/vnd.github+json'}))
    # Verify intended-public media works without credentials before handing it to Buffer.
    with urllib.request.urlopen(asset['browser_download_url'], timeout=120) as r:
        assert r.read(12)[4:8] == b'ftyp', 'Public media not reachable'
    ledger['video'] = asset['browser_download_url']
    ledger['render_result'] = state.get('result')
    save(release, ledger)
    return asset['browser_download_url']



def upload_creative_file(release, name, data, mime):
    url = release['upload_url'].split('{')[0] + '?name=' + name
    return json.loads(request(url, body=data, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Content-Type': mime, 'Accept': 'application/vnd.github+json'}))


def creative_asset(item, release, ledger, *, new_slot=False):
    filename = 'video-creative-v2.mp4'
    existing = next((a for a in release.get('assets', []) if a['name'] == filename), None)
    if existing:
        metadata_asset = next((a for a in release['assets'] if a['name'] == 'creative-v2.json'), None)
        if not metadata_asset:
            raise RuntimeError('Creative video lacks reviewed provenance; refusing to publish.')
        metadata = json.loads(subprocess.check_output(['gh','release','download',ledger['slot'],'--repo',REPO,
            '--pattern','creative-v2.json','--output','-'], stderr=subprocess.PIPE, timeout=60))
        if existing.get('digest') and existing['digest'] != 'sha256:'+metadata.get('sha256',''):
            raise RuntimeError('Creative video checksum differs from reviewed provenance')
        if metadata.get('voice') != 'af_heart' or metadata.get('creative_version') != 'creative-v2':
            raise RuntimeError('Creative provenance does not match approved voice/style')
        return existing['browser_download_url'], metadata
    if ledger.get('creative_attempted'):
        raise RuntimeError('Previous creative edit has no stored result; review rather than looping renders.')
    if new_slot:
        reserve_render(ledger['slot'], dt.datetime.now(SAST))
        ledger['render_attempted'] = True
    # Editing an existing scheduled slot adds no new slot or Reels-service job.
    ledger['creative_attempted'] = True
    save(release, ledger)
    from creative_engine import render_video
    with tempfile.TemporaryDirectory(prefix='cwuc-creative-') as directory:
        work = Path(directory); video = work / filename
        metadata = render_video(item, ledger['slot'], video, work)
        asset = upload_creative_file(release, filename, video.read_bytes(), 'video/mp4')
        upload_creative_file(release, 'creative-v2.json', json.dumps(metadata, indent=2).encode(), 'application/json')
        upload_creative_file(release, 'creative-v2-contact-sheet.jpg', (work/'contact-sheet.jpg').read_bytes(), 'image/jpeg')
    ledger['creative_video'] = asset['browser_download_url']
    ledger['creative_result'] = metadata
    if new_slot:
        ledger['video'] = asset['browser_download_url']; ledger['render_result'] = metadata
    save(release, ledger)
    return asset['browser_download_url'], metadata


def native_metadata(service, item):
    if service == 'facebook':
        return {'facebook': {'type': 'reel'}}
    if service == 'tiktok':
        return {'tiktok': {'isAiGenerated': True}}
    return {'youtube': {'isAiGenerated': True, 'title': item['title'] + ' #Shorts',
        'categoryId': '27', 'privacy': 'public', 'madeForKids': False, 'notifySubscribers': True}}


def upgrade_creative(now):
    channels = buffer('query($id:OrganizationId!){channels(input:{organizationId:$id}){id name service serviceId}}', {'id': ORG})['channels']
    assert {c['service']:c['id'] for c in channels} == CHANNELS, 'Connected channel identity changed'
    assert next(c['serviceId'] for c in channels if c['service']=='facebook') == FACEBOOK_PAGE_ID, 'Facebook Page identity changed'
    posts = existing_posts(now=now)
    latest = now + dt.timedelta(hours=48)
    day = now.date()
    changed = []
    while day <= latest.date():
        for slot, when in SLOTS.items():
            due = dt.datetime.combine(day, when, SAST)
            if not now+dt.timedelta(minutes=20) <= due <= latest:
                continue
            tag = day.strftime('%Y%m%d')+'-'+slot
            release = read_release(tag)
            ledger = json.loads(release['body'] or '{}') if release else {}
            if not ledger.get('posts'):
                continue
            current = {}
            for service, channel in CHANNELS.items():
                recorded = ledger['posts'].get(service)
                matches = [p for p in posts if recorded and p['id']==recorded['id'] and p['channelId']==channel]
                if len(matches)!=1 or matches[0]['status']!='scheduled':
                    raise RuntimeError('Upgrade requires exact live scheduled post: '+tag+'/'+service)
                current[service]=matches[0]
            item = {**ledger['content'], 'creative_version':'creative-v2'}
            source, metadata = creative_asset(item, release, ledger)
            url = delivery_url(tag, source, now)
            ledger.setdefault('creative_previous', {'content': ledger['content'], 'video':ledger.get('video'), 'delivery_video':ledger.get('delivery_video')})
            ledger['content']=item
            ledger['creative_video']=source; ledger['creative_result']=metadata
            ledger['creative_version']='creative-v2'
            save(release, ledger)
            for service, before in current.items():
                expected_text=caption(item, service, tag)
                if before['text']==expected_text and any(a.get('source')==url for a in before.get('assets', [])):
                    continue
                result=buffer('mutation($input:EditPostInput!){editPost(input:$input){... on PostActionSuccess{post{'+POST_FIELDS+'}} ... on MutationError{message}}}',
                    {'input':{'id':before['id'],'text':expected_text,'assets':[{'video':{'url':url}}], 'metadata':native_metadata(service,item)}})['editPost']
                after=result.get('post')
                if not after:raise RuntimeError('Creative edit refused: '+str(result.get('message')))
                if any(after[k]!=before[k] for k in ('id','channelId','dueAt','status')):
                    raise RuntimeError('Creative edit changed publishing identity/schedule: '+tag+'/'+service)
                if after['text']!=expected_text or not any(a.get('source')==url for a in after.get('assets', [])):
                    raise RuntimeError('Creative attachment/text not retained: '+tag+'/'+service)
                ledger['posts'][service]=after;save(release,ledger)
                print('CREATIVE UPGRADE scheduled: '+tag+'/'+service+'/'+after['id'], flush=True)
                changed.append({'slot':tag,'service':service,'id':after['id'],'dueAt':after['dueAt']})
            ledger['delivery_video']=url
            save(release,ledger)
        day+=dt.timedelta(days=1)
    print(json.dumps({'creative_version':'creative-v2','updated_posts':changed},indent=2))



def apply_growth_test(now):
    """One approved controlled test; preserve post identities and recovery evidence."""
    import hashlib
    media = 'https://raw.githubusercontent.com/hancra09/cwhereucheaper-social-campaign/refs/heads/growth-test-media-20261114/'
    tests = [
      ('20261115-early', 'quiz.mp4', '79a7468cc1204996ef1de8d70c6c1018401e005408821d2f17bae59efe0e5262',
       'Which pack is cheaper per 100g?', 'Illustrative example: R30 for 500g is R6 per 100g; R42 for 600g is R7 per 100g. Did you pick the bigger pack?', '#UnitPrice #ShoppingTips #SouthAfrica #CwhereUcheaper'),
      ('20261115-am', 'delivery.mp4', '0e16deb09b9d77b833f25b080bc2b3ce4d5f756868b81526a2f831e07072c4e5',
       'The delivery-fee plot twist', 'Illustrative example: R200 plus R60 delivery is R260; R230 with free delivery is R230. Compare the delivered total. Has this caught you out?', '#DeliveryFees #OnlineShopping #ShoppingTips #SouthAfrica'),
    ]
    channels=buffer('query($id:OrganizationId!){channels(input:{organizationId:$id}){id name service serviceId}}', {'id':ORG})['channels']
    assert {c['service']:c['id'] for c in channels} == CHANNELS, 'Connected channel identity changed'
    assert next(c['serviceId'] for c in channels if c['service']=='facebook') == FACEBOOK_PAGE_ID, 'Facebook Page identity changed'
    posts=existing_posts(now=now)
    prepared=[]
    for tag, name, digest, title, body, hashtags in tests:
        due=dt.datetime.combine(dt.datetime.strptime(tag[:8], '%Y%m%d').date(), SLOTS[tag.split('-')[1]], SAST)
        if not now+dt.timedelta(hours=2) < due: raise RuntimeError('Insufficient lead time: '+tag)
        data=request(media+name)
        if data[4:8] != b'ftyp' or hashlib.sha256(data).hexdigest()!=digest: raise RuntimeError('Media verification failed: '+tag)
        release=read_release(tag)
        if not release: raise RuntimeError('Missing release: '+tag)
        ledger=json.loads(release['body'] or '{}')
        if ledger.get('growth_test_pending'): raise RuntimeError('Uncertain previous test edit; reconcile before retry: '+tag)
        current={}
        for service, channel in CHANNELS.items():
            recorded=ledger.get('posts',{}).get(service,{}).get('id')
            found=[p for p in posts if p['id']==recorded and p['channelId']==channel and p['status']=='scheduled']
            if len(found)!=1 or found[0]['dueAt'] != ledger['posts'][service]['dueAt']:
                raise RuntimeError('Exact scheduled post not verified: '+tag+'/'+service)
            current[service]=found[0]
        item={'title':title,'script':title,'caption':body,'style':'Playful','creative_version':'creative-v2','growth_hashtags':hashtags}
        prepared.append((tag,media+name,digest,release,ledger,current,item))
    for tag,url,digest,release,ledger,current,item in prepared:
        ledger['growth_original']=json.loads(json.dumps({k:ledger.get(k) for k in ('content','title','posts','video','delivery_video','creative_video','creative_result')}))
        ledger['growth_test_pending']={'url':url,'sha256':digest,'item':item,'completed':[]}
        save(release,ledger)
        for service,before in current.items():
            expected=caption(item,service,tag)
            result=buffer('mutation($input:EditPostInput!){editPost(input:$input){... on PostActionSuccess{post{'+POST_FIELDS+'}} ... on MutationError{message}}}',
              {'input':{'id':before['id'],'text':expected,'assets':[{'video':{'url':url}}], 'metadata':native_metadata(service,item)}})['editPost']
            after=result.get('post')
            if not after: raise RuntimeError('Edit refused: '+tag+'/'+service+': '+str(result.get('message')))
            if any(after[k]!=before[k] for k in ('id','channelId','dueAt','status')) or after['text']!=expected or not any(a.get('source')==url for a in after.get('assets',[])):
                raise RuntimeError('Edit verification failed: '+tag+'/'+service)
            ledger['posts'][service]=after
            ledger['growth_test_pending']['completed'].append(service)
            save(release,ledger)
            print('VERIFIED '+tag+' '+service+' '+after['id'],flush=True)
        ledger['content']=item; ledger['title']=item['title']; ledger['video']=url; ledger['delivery_video']=url
        ledger['growth_test']={'sha256':digest,'url':url,'kind':'illustrative control','voice':'af_heart'}
        ledger.pop('growth_test_pending',None)
        save(release,ledger)
        print('TEST READY '+tag,flush=True)

def existing_posts(*, now=None, metrics=False):
    now = now or dt.datetime.now(SAST)
    start = dt.datetime.combine(now.date() - dt.timedelta(days=AUDIT_DAYS), dt.time(), SAST)
    fields = POST_FIELDS + (' metrics{type value unit} metricsUpdatedAt' if metrics else '')
    result, after = [], None
    for _ in range(5):
        data = buffer('query($input:PostsInput!,$after:String){posts(input:$input,first:100,after:$after){edges{node{' + fields + '}} pageInfo{hasNextPage endCursor}}}',
            {'input': {'organizationId': ORG, 'filter': {'channelIds': list(CHANNELS.values()),
                'dueAt': {'start': start.astimezone(dt.timezone.utc).isoformat()}},
                'sort': [{'field': 'dueAt', 'direction': 'desc'}]}, 'after': after})['posts']
        result.extend(e['node'] for e in data['edges'])
        if not data['pageInfo']['hasNextPage']:
            return result
        after = data['pageInfo']['endCursor']
    raise RuntimeError('Post history exceeds reconciliation bound; stop safely.')


def caption(item, service, tag):
    campaign = 'evergreen_shopping_tips' if item.get('date', '') > LEGACY_END.isoformat() else '30_day_shopping_tips'
    link = ORIGIN + '/?utm_source=' + service + '&utm_medium=organic_social&utm_campaign=' + campaign + '&utm_content=' + tag
    disclosure = 'AI narration and illustrative AI product visuals.' if item.get('creative_version') == 'creative-v2' else 'AI narration and original motion graphics.'
    return item['title'] + '\n\n' + item['caption'] + '\nStart your next price check: ' + link + '\n' + disclosure + ' ' + item.get('growth_hashtags', '#SouthAfrica #ShoppingTips #CwhereUcheaper') + (' #Shorts' if service == 'youtube' else '')


def run(day, slot, *, now, immediate=False, preflight=False, request_item=None):
    item = request_item or campaign_item(day, slot)
    due = dt.datetime.combine(day, SLOTS[slot], SAST)
    if immediate:
        assert os.environ.get('ALLOW_SMOKE') == '1' and day == START and slot == 'am' and now.date() == dt.date(2026, 11, 7)
        tag = 'smoke-20261107'
        item = json.loads(Path(__file__).with_name('smoke.json').read_text())
    else:
        tag = day.strftime('%Y%m%d') + '-' + slot
        if not preflight and now >= due - dt.timedelta(minutes=5):
            raise RuntimeError('Too late to schedule this slot safely; no catch-up flood.')
    # Read-only preflight validates authentication and channel identity, never creates a release/render/post.
    channels = buffer('query($id:OrganizationId!){channels(input:{organizationId:$id}){id name service serviceId}}', {'id': ORG})['channels']
    assert {c['service']:c['id'] for c in channels} == CHANNELS, 'Connected channel identity changed'
    assert next(c['serviceId'] for c in channels if c['service'] == 'facebook') == FACEBOOK_PAGE_ID, 'Facebook Page identity changed'
    posts = existing_posts(now=now)
    if preflight:
        print('Preflight PASS: original 90 preserved, ongoing monthly plans, three daily slots, authenticated intended channels, rolling reconciliation.')
        return
    release = load_release(tag)
    ledger = json.loads(release['body'] or '{}')
    # Bind later retries to the content first selected for this slot.
    item = ledger.get('content', item)
    if not ledger.get('video') and not ledger.get('render_attempted') and not ledger.get('posts'):
        item = {**item, 'creative_version': 'creative-v2'}
    ledger['content'] = item
    ledger.update({'slot': tag, 'title': item['title'], 'due_sast': due.isoformat() if not immediate else now.isoformat(), 'posts': ledger.get('posts', {})})
    video = ledger.get('video') or generate(item, release, ledger)
    if item.get('evidence_product_id'):
        from product_response import research as product_research
        fresh=product_research(item['evidence_product_id'])
        checked=dt.datetime.fromisoformat(item['evidence_checked_sast'])
        age=dt.datetime.now(dt.timezone.utc)-checked.astimezone(dt.timezone.utc)
        if age>dt.timedelta(minutes=30) or age<dt.timedelta(minutes=-5) or any(fresh[k]!=item['evidence_'+k] for k in ('price','product','retailer','url')):
            raise RuntimeError('Product evidence expired or changed; no new post created.')
    if item.get('evidence_comparison_subject'):
        from comparison_response import research as comparison_research
        fresh=comparison_research(item['evidence_comparison_subject'])
        checked=dt.datetime.fromisoformat(item['evidence_checked_sast'])
        age=dt.datetime.now(dt.timezone.utc)-checked.astimezone(dt.timezone.utc)
        if age>dt.timedelta(minutes=30) or age<dt.timedelta(minutes=-5) or fresh['signature']!=item['evidence_comparison_signature']:
            raise RuntimeError('Comparison evidence expired or changed; no new post created.')
    for service, channel in CHANNELS.items():
        text = caption(item, service, tag)
        matches = [p for p in posts if p['channelId'] == channel and p['text'] == text]
        if len(matches) > 1:
            raise RuntimeError('Multiple existing matching posts; manual review required.')
        if matches:
            post = matches[0]
        elif service in ledger['posts']:
            raise RuntimeError('Recorded post missing from live Buffer history; refusing duplicate.')
        elif ledger.get('pending_service') == service:
            raise RuntimeError('Previous send has an uncertain result; refusing to retry without reconciliation.')
        else:
            if not immediate:
                video = ledger.get('delivery_video') or delivery_url(tag, ledger['video'], now)
                ledger['delivery_video'] = video
            ledger['pending_service'] = service
            save(release, ledger)
            # Facebook requires its native Reel type and does not accept the
            # TikTok/YouTube isAiGenerated input. AI narration is disclosed in text.
            meta = {'facebook': {'type': 'reel'}} if service == 'facebook' else {service: {'isAiGenerated': True}}
            if service == 'youtube':
                meta[service].update({'title': item['title'] + ' #Shorts', 'categoryId': '27',
                    'privacy': 'public', 'madeForKids': False, 'notifySubscribers': True})
            inp = {'channelId': channel, 'text': text, 'assets': [{'video': {'url': video}}],
                'metadata': meta, 'schedulingType': 'automatic', 'mode': 'shareNow' if immediate else 'customScheduled',
                'needsApproval': False, 'aiAssisted': True}
            if not immediate:
                inp['dueAt'] = due.astimezone(dt.timezone.utc).isoformat()
            result = buffer('mutation($input:CreatePostInput!){createPost(input:$input){... on PostActionSuccess{post{' + POST_FIELDS + '}} ... on MutationError{message}}}', {'input': inp})['createPost']
            if 'post' not in result:
                raise RuntimeError('Buffer refused ' + service + ': ' + str(result.get('message')))
            post = result['post']
        ledger['posts'][service] = post
        ledger.pop('pending_service', None)
        save(release, ledger)
        if post['status'] in ('error', 'needs_approval', 'draft'):
            raise RuntimeError('Post requires attention: ' + json.dumps(post))
    ledger['state'] = 'submitted' if immediate else 'scheduled'
    save(release, ledger)
    print(json.dumps({'slot': tag, 'posts': ledger['posts']}, indent=2))


def delivery_url(tag, original, now):
    return publish_delivery(tag, original, gh=gh, request=request, repo=REPO, now=now)


def refresh_media(now):
    """Edit only future scheduled campaign posts, keeping IDs/text/schedules intact."""
    posts = campaign_posts(existing_posts(now=now))
    for day, slot in future_slots(now):
        tag = day.strftime('%Y%m%d') + '-' + slot
        release = read_release(tag)
        ledger = json.loads(release['body'] or '{}') if release else {}
        if not ledger.get('video'):
            continue
        url = delivery_url(tag, ledger['video'], now)
        for service, recorded in ledger.get('posts', {}).items():
            if service == 'youtube':
                continue  # Its existing attachment published successfully; leave it intact.
            matches = [p for p in posts if p['id'] == recorded['id']]
            if len(matches) != 1 or matches[0]['status'] != 'scheduled':
                raise RuntimeError('Media edit requires the exact live scheduled post: ' + tag + '/' + service)
            before = matches[0]
            result = buffer('mutation($input:EditPostInput!){editPost(input:$input){... on PostActionSuccess{post{' + POST_FIELDS + '}} ... on MutationError{message}}}',
                {'input': {'id': before['id'], 'assets': [{'video': {'url': url}}],
                    'metadata': {'facebook': {'type': 'reel'}} if service == 'facebook' else {'tiktok': {'isAiGenerated': True}}}})['editPost']
            after = result.get('post')
            if not after:
                raise RuntimeError('Buffer media edit refused: ' + str(result.get('message')))
            if any(after[k] != before[k] for k in ('id', 'channelId', 'text', 'dueAt', 'status')):
                raise RuntimeError('Media edit changed scheduling/content unexpectedly: ' + tag)
            ledger['posts'][service] = after
            save(release, ledger)
            print('Refreshed media only: ' + tag + '/' + service + '/' + after['id'])
        ledger['delivery_video'] = url
        save(release, ledger)


def campaign_posts(posts):
    return [p for p in posts if any('utm_campaign=' + name in p['text']
        for name in ('30_day_shopping_tips', 'evergreen_shopping_tips'))]


def future_slots(now):
    earliest = now + dt.timedelta(hours=MIN_LEAD_HOURS)
    latest = now + dt.timedelta(hours=PREPARE_HOURS)
    day = max(START, now.date())
    while day <= latest.date():
        for slot, when in SLOTS.items():
            due = dt.datetime.combine(day, when, SAST)
            if earliest <= due <= latest:
                yield day, slot
        day += dt.timedelta(days=1)


def prepare_ahead(now):
    """Fill one future slot. Never catch up a missed slot or exceed daily generation."""
    posts = existing_posts(now=now)
    # Leave room for an Owner-added post within Buffer Free's 10-per-channel queue.
    if any(sum(p['channelId'] == channel and p['status'] in ('scheduled', 'sending')
               for p in posts) >= 9 for channel in CHANNELS.values()):
        print('Ahead preparation paused: a channel queue has nine pending posts.')
        return False
    budget = render_budget(now)
    for day, slot in future_slots(now):
        tag = day.strftime('%Y%m%d') + '-' + slot
        release = read_release(tag)
        ledger = json.loads(release['body'] or '{}') if release else {}
        item = ledger.get('content') or campaign_item(day, slot)
        matches = {service: [p for p in posts if p['channelId'] == channel
                   and p['text'] == caption(item, service, tag)]
                   for service, channel in CHANNELS.items()}
        if any(len(values) > 1 for values in matches.values()):
            raise RuntimeError('Duplicate live slot posts need review: ' + tag)
        if all(values and values[0]['status'] in ('scheduled', 'sending', 'sent')
               for values in matches.values()):
            continue
        video_ready = bool(ledger.get('video') or (release and
            any(a['name'] == 'video.mp4' for a in release.get('assets', []))))
        pending = ledger.get('pending_service')
        if pending and not matches.get(pending):
            print('::warning::Uncertain send retained for review; no resend: ' + tag)
            continue
        if ledger.get('render_attempted') and not video_ready:
            print('::warning::Unresolved render retained for review; no repeat: ' + tag)
            continue
        if not video_ready and tag not in budget and len(budget) >= DAILY_RENDER_LIMIT:
            continue
        run(day, slot, now=now)
        return True
    print('No safe future slot needs preparation within the current budget/horizon.')
    return False



def prepare_request(now, topic, request_id, subject="", origin=""):
    """Reserve only a vacant normal slot; keep existing queues untouched."""
    import re
    from response import research, build
    if not re.fullmatch(r'[a-f0-9]{32}',request_id or ''):
        raise ValueError('Invalid request identifier')
    if not ((topic in ('delivery_total_v1','unit_price_v1','bulk_buying_v1','shopping_plan_v1') and not subject) or (topic=='product_price_v1' and re.fullmatch(r'[1-9][0-9]{0,9}',subject or '')) or (topic=='product_compare_v1' and re.fullmatch(r'[1-9][0-9]{0,9}-[1-9][0-9]{0,9}',subject or ''))):
        raise ValueError('Unsupported request or subject')
    if origin not in ('','synthetic') or (origin=='synthetic' and (topic!='unit_price_v1' or subject)):
        raise ValueError('Invalid synthetic test request')
    request_release = load_release('viewer-request-' + request_id)
    request_ledger = json.loads(request_release['body'] or '{}')
    if request_ledger.get('topic') not in (None,topic) or request_ledger.get('subject') not in (None,subject) or request_ledger.get('origin') not in (None,origin):
        raise ValueError('Request identifier reused')
    if request_ledger.get('state') == 'scheduled':
        return True
    posts = existing_posts(now=now)
    if any(sum(p['channelId'] == channel and p['status'] in ('scheduled','sending') for p in posts) >= 9 for channel in CHANNELS.values()):
        print('Request deferred: campaign queue is full.')
        return False
    selected = request_ledger.get('slot')
    if not selected:
        if len(render_budget(now)) >= DAILY_RENDER_LIMIT:
            print('Request deferred: daily render budget exhausted.')
            return False
        if topic in ('delivery_total_v1','unit_price_v1','bulk_buying_v1','shopping_plan_v1'):
            item=build(topic,research(topic=topic))
        elif topic=='product_price_v1':
            from product_response import research as product_research, build as product_build
            item=product_build(product_research(subject))
        else:
            from comparison_response import research as comparison_research, build as comparison_build
            item=comparison_build(comparison_research(subject))
        item['response_request_id'] = request_id
        if origin=='synthetic':
            item['synthetic_test']=True
            item['caption']='TEST VIDEO: Based on a simulated viewer request. '+item['caption']
        for day, slot in future_slots(now):
            tag = day.strftime('%Y%m%d')+'-'+slot
            if any('utm_content='+tag+'\n' in p.get('text','') for p in posts) or read_release(tag):
                continue
            request_ledger.update({'topic':topic,'subject':subject,'origin':origin,'slot':tag,'state':'reserving'})
            save(request_release,request_ledger)
            slot_release = load_release(tag)
            slot_ledger = json.loads(slot_release['body'] or '{}')
            if slot_ledger:
                raise RuntimeError('Slot became occupied; refusing overwrite')
            slot_ledger.update({'slot':tag,'content':item,'response_request_id':request_id})
            save(slot_release,slot_ledger)
            selected=tag
            break
        if not selected:
            print('Request deferred: no vacant slot in horizon.')
            return False
    day_text, slot = selected.split('-',1)
    day = dt.datetime.strptime(day_text,'%Y%m%d').date()
    if now > dt.datetime.combine(day,SLOTS[slot],SAST) - dt.timedelta(hours=MIN_LEAD_HOURS):
        raise RuntimeError('Reserved response slot too close; no post created.')
    if topic in ('delivery_total_v1','unit_price_v1','bulk_buying_v1','shopping_plan_v1'):
        research(topic=topic)  # Reconfirm source before scheduling.
    slot_release = read_release(selected)
    if not slot_release:
        raise RuntimeError('Reserved response slot missing; review required.')
    ledger = json.loads(slot_release['body'] or '{}')
    if ledger.get('response_request_id') != request_id:
        raise RuntimeError('Response slot belongs to another request.')
    if topic in ('product_price_v1','product_compare_v1'):
        checked=dt.datetime.fromisoformat(ledger['content']['evidence_checked_sast'])
        age=dt.datetime.now(dt.timezone.utc)-checked.astimezone(dt.timezone.utc)
        if age>dt.timedelta(minutes=30) or age<dt.timedelta(minutes=-5):
            raise RuntimeError('Product evidence expired; no post created.')
    run(day,slot,now=now,request_item=ledger['content'])
    confirmed = json.loads(read_release(selected)['body'] or '{}')
    if confirmed.get('state') != 'scheduled' or set(confirmed.get('posts',{})) != set(CHANNELS):
        raise RuntimeError('Response delivery not fully confirmed.')
    request_ledger.update({'topic':topic,'subject':subject,'origin':origin,'slot':selected,'state':'scheduled'})
    save(request_release,request_ledger)
    print('Viewer response scheduled in campaign slot:',selected)
    return True


def audit():
    now = dt.datetime.now(SAST)
    posts = existing_posts(now=now)
    relevant = campaign_posts(posts)
    failed = [p for p in relevant if p['status'] in ('error', 'needs_approval', 'draft')]
    cutoff = now - dt.timedelta(minutes=15)
    day = max(START, cutoff.date() - dt.timedelta(days=AUDIT_DAYS - 1))
    while day <= cutoff.date():
        for slot, publish_time in SLOTS.items():
            if dt.datetime.combine(day, publish_time, SAST) > cutoff:
                continue
            tag = day.strftime('%Y%m%d') + '-' + slot
            for service, channel in CHANNELS.items():
                matches = [p for p in relevant if p['channelId'] == channel and 'utm_content=' + tag + '\n' in p['text']]
                if len(matches) != 1 or matches[0]['status'] != 'sent':
                    failed.append({'slot': tag, 'service': service, 'problem': 'Expected one sent post', 'found': matches})
        day += dt.timedelta(days=1)
    Path('audit.json').write_text(json.dumps(relevant, indent=2))
    print(json.dumps({s: sum(p['status'] == s for p in relevant) for s in {p['status'] for p in relevant}}))
    if failed:
        raise RuntimeError('Campaign publishing failure: ' + json.dumps(failed))


def review():
    """Optional within-channel signals; no raw private analytics are published."""
    now = dt.datetime.now(SAST)
    report = {'week_ending': now.date().isoformat(), 'preferred_themes': [], 'examples': [],
        'basis': 'Within-channel post metrics, not measured website conversions',
        'notes': 'Early Buffer metrics can lag or be unavailable. Preserve variety; no raw metrics stored.'}
    try:
        posts = campaign_posts(existing_posts(now=now, metrics=True))
        def recent_snapshot(post):
            try:
                updated = dt.datetime.fromisoformat(post['metricsUpdatedAt'].replace('Z', '+00:00'))
                return now - dt.timedelta(hours=48) <= updated <= now + dt.timedelta(minutes=5)
            except (KeyError, TypeError, ValueError, AttributeError):
                return False
        for service, channel in CHANNELS.items():
            eligible = [p for p in posts if p['channelId'] == channel and p['status'] == 'sent'
                and recent_snapshot(p)
                and p.get('dueAt') and dt.datetime.fromisoformat(p['dueAt'].replace('Z', '+00:00'))
                <= now - dt.timedelta(hours=48)]
            for kind in ('views', 'impressions', 'reach'):
                scored = [(next((m['value'] for m in p.get('metrics') or []
                    if m['type'] == kind and m['unit'] == 'count'), None), p) for p in eligible]
                scored = [(value, p) for value, p in scored if value is not None]
                if len(scored) < 3 or max(value for value, _ in scored) <= 0:
                    continue
                for _, post in sorted(scored, key=lambda x: x[0], reverse=True)[:2]:
                    title = post['text'].splitlines()[0]
                    theme = theme_for(title)
                    report['preferred_themes'].append(theme)
                    report['examples'].append({'channel': service, 'title': title,
                        'public_post': post.get('externalLink'), 'theme': theme})
                break
        report['preferred_themes'] = sorted(set(report['preferred_themes']))
        report['status'] = 'signals_available' if report['preferred_themes'] else 'insufficient_data'
    except (RuntimeError, urllib.error.URLError, KeyError, TypeError, ValueError):
        # Experimental metrics must never stop scheduled publishing or invent results.
        report['status'] = 'metrics_unavailable'
    write_public_json('reviews/' + now.date().isoformat() + '.json', report,
        'Review public campaign content choices', replace=True)
    if report['preferred_themes']:
        write_public_json('content-policy.json', {
            'review_date': report['week_ending'], 'preferred_themes': report['preferred_themes'],
            'rule': 'Use reviewed themes for at most two of five future slots; freeze existing plans.'},
            'Update future content emphasis from weekly review', replace=True)
    print('Weekly content review: ' + report['status'] + '. Raw metrics were not written to public storage.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['scheduled', 'preflight', 'bootstrap', 'smoke', 'audit', 'review', 'prepare', 'prime', 'refresh-media', 'upgrade-creative', 'growth-test', 'viewer-response'], default='scheduled')
    p.add_argument('--request-topic', default='')
    p.add_argument('--request-id', default='')
    p.add_argument('--request-subject', default='')
    p.add_argument('--request-origin', default='')
    args = p.parse_args()
    now = dt.datetime.now(SAST)
    check_access_expiry(now)
    ensure_plans(now.date())
    if args.mode == 'viewer-response':
        prepare_request(now,args.request_topic,args.request_id,args.request_subject,args.request_origin)
        return
    if args.mode == 'growth-test':
        apply_growth_test(now)
        return
    if args.mode == 'upgrade-creative':
        upgrade_creative(now)
        return
    if args.mode == 'refresh-media':
        refresh_media(now)
        return
    if args.mode == 'prepare':
        print('Current and next monthly content plans are ready. No render or publish.')
        return
    if args.mode == 'review':
        review()
        return
    if args.mode == 'audit':
        audit()
        return
    if args.mode in ('bootstrap', 'preflight', 'smoke'):
        if args.mode == 'bootstrap':
            assert now.date() <= START, 'Bootstrap cannot run after campaign start'
        day = max(START, now.date()) if args.mode == 'preflight' else START
        run(day, scheduled_slot(now) if args.mode == 'preflight' else 'am', now=now,
            immediate=args.mode == 'smoke', preflight=args.mode == 'preflight')
        return
    if now.date() < START:
        print('Campaign inactive before 8 Nov 2026 SAST. No render or publish.')
        return
    # Preparation is independent of publication-time audit. A missed historical
    # slot still fails the separate audits but does not block future preparation.
    deadline = time.monotonic() + 24 * 60
    for _ in range(3 if args.mode == 'prime' else 1):
        if deadline - time.monotonic() < 20 * 60:
            break  # Reserve room for one existing bounded renderer.
        if not prepare_ahead(dt.datetime.now(SAST)):
            break


if __name__ == '__main__':
    main()
