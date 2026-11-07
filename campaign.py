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
import urllib.error
import urllib.parse
import urllib.request
from content_factory import build_month, theme_for, validate_plan

SAST = dt.timezone(dt.timedelta(hours=2))
START = dt.date(2026, 11, 8)
LEGACY_END = dt.date(2026, 12, 7)
ORIGIN = 'https://www.cwhereucheaper.co.za'
REPO = 'hancra09/cwhereucheaper-social-campaign'
ORG = '6aeef1646c3957c58fdd3b19'
CHANNELS = {'youtube': '6aeef238e29c69a171916d83', 'tiktok': '6aeef202e29c69a171916c16',
    'facebook': '6aeef981e29c69a17191b79b'}
FACEBOOK_PAGE_ID = '1265683793295341'  # Public URL redirects to profile 61592840593333.
POST_FIELDS = 'id channelId status text dueAt externalLink error { message }'
SLOTS = {'early': dt.time(8), 'am': dt.time(12, 30), 'pm': dt.time(18, 30)}
ROOT = Path(__file__).parent
AUDIT_DAYS = 7


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
    return item['title'] + '\n\n' + item['caption'] + '\nStart your next price check: ' + link + '\nAI narration and original motion graphics. #SouthAfrica #ShoppingTips #CwhereUcheaper' + (' #Shorts' if service == 'youtube' else '')


def run(day, slot, *, now, immediate=False, preflight=False):
    item = campaign_item(day, slot)
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
    ledger['content'] = item
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


def campaign_posts(posts):
    return [p for p in posts if any('utm_campaign=' + name in p['text']
        for name in ('30_day_shopping_tips', 'evergreen_shopping_tips'))]


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
    p.add_argument('--mode', choices=['scheduled', 'preflight', 'bootstrap', 'smoke', 'audit', 'review', 'prepare'], default='scheduled')
    args = p.parse_args()
    now = dt.datetime.now(SAST)
    check_access_expiry(now)
    ensure_plans(now.date())
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
    prior_failure = None
    try:
        audit()
    except RuntimeError as error:
        # A missed/failed earlier slot must not prevent the next distinct video.
        prior_failure = str(error)
    run(now.date(), scheduled_slot(now), now=now)
    if prior_failure:
        raise RuntimeError(prior_failure)


if __name__ == '__main__':
    main()
