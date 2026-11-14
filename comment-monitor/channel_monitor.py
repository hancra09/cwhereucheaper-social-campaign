"""Experimental public YouTube comment reader; no publishing or network scheduler."""
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = 'https://www.googleapis.com/youtube/v3/'
CHANNEL = 'UCRZrhWYIMqPVITDfWq8piUg'


def pages(resource, params, key, fetch=None, limit=20):
    if not key:
        raise ValueError('Missing credential')
    fetch = fetch or (lambda request: urllib.request.urlopen(request, timeout=30).read())
    params = dict(params, maxResults=100, textFormat='plainText')
    result = []
    for _ in range(limit):
        req = urllib.request.Request(API + resource + '?' + urllib.parse.urlencode(params),
                                     headers={'X-Goog-Api-Key': key})
        data = json.loads(fetch(req))
        if not isinstance(data, dict) or not isinstance(data.get('items'), list):
            raise ValueError('Invalid YouTube response')
        result.extend(data['items'])
        token = data.get('nextPageToken')
        if not token:
            return result
        params['pageToken'] = token
    raise RuntimeError('Incomplete response: page limit reached')


def collect(key, fetch=None):
    threads = pages('commentThreads', {'part': 'snippet', 'allThreadsRelatedToChannelId': CHANNEL,
                                      'order': 'time'}, key, fetch)
    rows = []
    for thread in threads:
        s = thread['snippet']
        if s['channelId'] != CHANNEL:
            raise ValueError('Unexpected channel')
        parent = s['topLevelComment']
        video = s.get('videoId', '')
        rows.append(row(parent, video, ''))
        if s['totalReplyCount']:
            replies = pages('comments', {'part': 'snippet', 'parentId': parent['id']}, key, fetch)
            for reply in replies:
                if reply['snippet']['parentId'] != parent['id']:
                    raise ValueError('Unexpected reply parent')
                rows.append(row(reply, video, parent['id']))
    return rows


def row(comment, video, parent):
    snippet = comment['snippet']
    return (comment['id'], video, parent, snippet['publishedAt'], snippet['textDisplay'])


def store(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(path)
    os.chmod(path, 0o600)
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS comments
                   (id TEXT PRIMARY KEY, video TEXT NOT NULL, parent TEXT NOT NULL,
                    published TEXT NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'unreviewed')''')
        db.execute('CREATE TABLE IF NOT EXISTS polls (id INTEGER PRIMARY KEY CHECK(id=1), checked TEXT NOT NULL)')
        with db:
            db.execute('CREATE TEMP TABLE seen_ids (id TEXT PRIMARY KEY)')
            db.executemany('INSERT OR IGNORE INTO seen_ids(id) VALUES(?)', [(r[0],) for r in rows])
            db.executemany('''INSERT INTO comments(id,video,parent,published,body) VALUES(?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET body=excluded.body,
                state=CASE WHEN comments.body != excluded.body THEN 'unreviewed' ELSE comments.state END''', rows)
            db.execute('DELETE FROM comments WHERE id NOT IN (SELECT id FROM seen_ids)')
            db.execute('''INSERT INTO polls(id,checked) VALUES(1,CURRENT_TIMESTAMP)
                       ON CONFLICT(id) DO UPDATE SET checked=CURRENT_TIMESTAMP''')
    finally:
        db.close()


def main():
    credential_dir = os.environ.get('CREDENTIALS_DIRECTORY')
    state_dir = os.environ.get('STATE_DIRECTORY')
    if not credential_dir or not state_dir:
        raise ValueError('Missing service credential or state directory')
    key = (Path(credential_dir) / 'youtube-api-key').read_text().strip()
    rows = collect(key)
    store(Path(state_dir) / 'comments.sqlite', rows)
    print('YouTube public comment poll succeeded; count:', len(rows))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('YouTube public comment poll failed:', type(exc).__name__, file=sys.stderr)
        sys.exit(1)
