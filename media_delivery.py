"""Small disposable public-video cache; permanent originals remain in Releases."""
import base64
import datetime as dt
import re
import subprocess
import time
import urllib.error

BRANCH = 'public-video-cache'
TAG = re.compile(r'^20\d{6}-(early|am|pm)$')
CACHE_FILE = re.compile(r'^20\d{6}-(early|am|pm)(-creative-v2)?\.mp4$')


def retained(entries, now):
    cutoff = (now.date() - dt.timedelta(days=10)).strftime('%Y%m%d')
    # Never copy arbitrary repository paths, documents, or application source.
    return [e for e in entries if e.get('type') == 'blob'
            and e.get('path', '').endswith('.mp4')
            and CACHE_FILE.fullmatch(e['path']) and e['path'][:8] >= cutoff]


def publish(tag, source, *, gh, request, repo, now):
    if not TAG.fullmatch(tag):
        raise ValueError('Only dated intended-public campaign videos can enter media cache')
    entries = []
    exists = False
    try:
        ref = gh('git/ref/heads/' + BRANCH)
        commit = gh('git/commits/' + ref['object']['sha'])
        entries = gh('git/trees/' + commit['tree']['sha'])['tree']
        exists = True
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    entries = retained(entries, now)
    allowed = {f'https://github.com/{repo}/releases/download/{tag}/video.mp4': ('video.mp4', tag+'.mp4'),
        f'https://github.com/{repo}/releases/download/{tag}/video-creative-v2.mp4': ('video-creative-v2.mp4', tag+'-creative-v2.mp4')}
    if source not in allowed:
        raise ValueError('Only the exact archived campaign video may be cached')
    filename, path = allowed[source]
    if not any(e['path'] == path for e in entries):
        # The public release redirect itself has timed out remotely. Use the
        # authenticated official CLI to retrieve the durable archived original.
        video = subprocess.check_output(['gh', 'release', 'download', tag, '--repo', repo,
            '--pattern', filename, '--output', '-'], stderr=subprocess.PIPE, timeout=90)
        if video[4:8] != b'ftyp' or len(video) > 50_000_000:
            raise ValueError('Cache requires a validated campaign MP4 below 50MB')
        blob = gh('git/blobs', {'content': base64.b64encode(video).decode(), 'encoding': 'base64'}, 'POST')
        entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
        if len(entries) > 48:
            raise RuntimeError('Public delivery cache is unexpectedly full')
        tree = gh('git/trees', {'tree': [{k: e[k] for k in ('path', 'mode', 'type', 'sha')} for e in entries]}, 'POST')
        # Parentless cache snapshots prevent MP4 history accumulating forever.
        # The fixed disposable cache ref is the ONLY ref ever replaced here.
        commit = gh('git/commits', {'message': 'Refresh disposable public video delivery cache',
            'tree': tree['sha'], 'parents': []}, 'POST')
        if exists:
            gh('git/refs/heads/' + BRANCH, {'sha': commit['sha'], 'force': True}, 'PATCH')
        else:
            gh('git/refs', {'ref': 'refs/heads/' + BRANCH, 'sha': commit['sha']}, 'POST')
    url = f'https://raw.githubusercontent.com/{repo}/refs/heads/{BRANCH}/{path}'
    # Check public delivery without credentials, not merely Git API access.
    for attempt in range(6):
        try:
            data = request(url)
            if data[4:8] != b'ftyp':
                raise RuntimeError('Public delivery URL did not return MP4')
            return url
        except urllib.error.HTTPError as error:
            if error.code != 404 or attempt == 5:
                raise
            time.sleep(5)
