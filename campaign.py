"""Bounded CWUC campaign. Standard library only; credentials never enter the ledger."""
import argparse
import datetime as dt
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

SAST = dt.timezone(dt.timedelta(hours=2))
START = dt.date(2026, 11, 8)
END = dt.date(2026, 12, 7)
ORIGIN = 'https://www.cwhereucheaper.co.za'
REPO = 'hancra09/cwhereucheaper-social-campaign'
ORG = '6aeef1646c3957c58fdd3b19'
CHANNELS = {'youtube': '6aeef238e29c69a171916d83', 'tiktok': '6aeef202e29c69a171916c16'}
POST_FIELDS = 'id channelId status text dueAt externalLink error { message }'


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


def load_release(tag):
    try:
        return gh('releases/tags/' + tag)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return gh('releases', {'tag_name': tag, 'name': tag, 'body': '{}', 'draft': False, 'prerelease': True})


def save(release, ledger):
    # Durable before/after each publishing mutation; failed ambiguous sends reconcile first.
    gh('releases/' + str(release['id']), {'body': json.dumps(ledger, indent=2)}, 'PATCH')
    Path('last-run.json').write_text(json.dumps(ledger, indent=2))


def generate(item, release, ledger):
    existing = next((a for a in release['assets'] if a['name'] == 'video.mp4'), None)
    if existing:
        return existing['browser_download_url']
    if ledger.get('render_attempted'):
        raise RuntimeError('Previous render attempt has no stored media. Review before retrying; no duplicate quota use.')
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
        'duration': 25, 'style': 'Educational', 'voice': voice, 'assets': [],
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


def existing_posts():
    result, after = [], None
    for _ in range(5):
        data = buffer('query($input:PostsInput!,$after:String){posts(input:$input,first:100,after:$after){edges{node{' + POST_FIELDS + '}} pageInfo{hasNextPage endCursor}}}',
            {'input': {'organizationId': ORG, 'filter': {'channelIds': list(CHANNELS.values())}}, 'after': after})['posts']
        result.extend(e['node'] for e in data['edges'])
        if not data['pageInfo']['hasNextPage']:
            return result
        after = data['pageInfo']['endCursor']
    raise RuntimeError('Post history exceeds reconciliation bound; stop safely.')


def caption(item, service, tag):
    link = ORIGIN + '/?utm_source=' + service + '&utm_medium=organic_social&utm_campaign=30_day_shopping_tips&utm_content=' + tag
    return item['title'] + '\n\n' + item['caption'] + '\nStart your next price check: ' + link + '\nAI narration and original motion graphics. #SouthAfrica #ShoppingTips #CwhereUcheaper' + (' #Shorts' if service == 'youtube' else '')


def run(day, slot, *, now, immediate=False, preflight=False):
    items = json.loads(Path(__file__).with_name('content.json').read_text())
    assert len(items) == 60 and len({i['title'] for i in items}) == 60
    assert START <= day <= END, 'Outside campaign dates'
    index = (day - START).days * 2 + (slot == 'pm')
    item = items[index]
    due = dt.datetime.combine(day, dt.time(12 if slot == 'am' else 18, 30), SAST)
    if immediate:
        assert os.environ.get('ALLOW_SMOKE') == '1' and day == START and slot == 'am' and now.date() == dt.date(2026, 11, 7)
        tag = 'smoke-20261107'
        item = json.loads(Path(__file__).with_name('smoke.json').read_text())
    else:
        tag = day.strftime('%Y%m%d') + '-' + slot
        if now >= due - dt.timedelta(minutes=5):
            raise RuntimeError('Too late to schedule this slot safely; no catch-up flood.')
    # Read-only preflight validates authentication and channel identity, never creates a release/render/post.
    channels = buffer('query($id:OrganizationId!){channels(input:{organizationId:$id}){id name service}}', {'id': ORG})['channels']
    assert {c['service']:c['id'] for c in channels} == CHANNELS, 'Connected channel identity changed'
    posts = existing_posts()
    if preflight:
        print('Preflight PASS: 60 scripts, campaign bounds, authenticated intended channels, post reconciliation.')
        return
    release = load_release(tag)
    ledger = json.loads(release['body'] or '{}')
    ledger.update({'slot': tag, 'title': item['title'], 'due_sast': due.isoformat() if not immediate else now.isoformat(), 'posts': ledger.get('posts', {})})
    video = ledger.get('video') or generate(item, release, ledger)
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
            ledger['pending_service'] = service
            save(release, ledger)
            meta = {service: {'isAiGenerated': True}}
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


def audit():
    posts = existing_posts()
    relevant = [p for p in posts if 'utm_campaign=30_day_shopping_tips' in p['text']]
    failed = [p for p in relevant if p['status'] in ('error', 'needs_approval', 'draft')]
    cutoff = dt.datetime.now(SAST) - dt.timedelta(minutes=15)
    day = START
    while day <= min(cutoff.date(), END):
        for slot, hour in [('am', 12), ('pm', 18)]:
            if dt.datetime.combine(day, dt.time(hour, 30), SAST) > cutoff:
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['scheduled', 'preflight', 'bootstrap', 'smoke', 'audit'], default='scheduled')
    args = p.parse_args()
    now = dt.datetime.now(SAST)
    if args.mode == 'audit':
        audit()
        return
    if args.mode in ('bootstrap', 'preflight', 'smoke'):
        if args.mode == 'bootstrap':
            assert now.date() <= START, 'Bootstrap cannot run after campaign start'
        run(START, 'am', now=now, immediate=args.mode == 'smoke', preflight=args.mode == 'preflight')
        return
    if not START <= now.date() <= END:
        print('Campaign inactive outside 8 Nov–7 Dec 2026 SAST. No render or publish.')
        return
    prior_failure = None
    try:
        audit()
    except RuntimeError as error:
        # A missed/failed earlier slot must not prevent the next distinct video.
        prior_failure = str(error)
    run(now.date(), 'am' if now.hour < 15 else 'pm', now=now)
    if prior_failure:
        raise RuntimeError(prior_failure)


if __name__ == '__main__':
    main()
