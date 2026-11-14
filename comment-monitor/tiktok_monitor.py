"""Read public TikTok comments via TikTok Social MCP; never posts or modifies content."""
import json
import os
import sqlite3
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SERVER = 'https://business-api.tiktok.com/open_mcp/tt-ads-mcp-organic-social'


def save_token(path, key, token):
    nonce = os.urandom(12)
    ciphertext = nonce + AESGCM(key).encrypt(nonce, json.dumps(token).encode(), b'cwuc-tiktok-v1')
    fd, name = tempfile.mkstemp(prefix='.token-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(ciphertext)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def access_token(credentials, state, fetch=None, now=None):
    fetch = fetch or (lambda req: urllib.request.urlopen(req, timeout=30).read())
    now = time.time() if now is None else now
    key = (credentials / 'tiktok-envelope').read_bytes()
    if len(key) != 32:
        raise ValueError('Invalid envelope key')
    path = state / 'token.enc'
    if path.exists():
        raw = path.read_bytes()
        token = json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], b'cwuc-tiktok-v1'))
    else:
        token = json.loads((credentials / 'tiktok-social').read_text())
        # Bootstrap credentials may have been issued before this service first starts.
        token['expires_at'] = now + max(0, int(token['expires_in']) - 7200)
        save_token(path, key, token)
    if now >= token['expires_at']:
        body = urllib.parse.urlencode({'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token'], 'client_id': token['client_id']}).encode()
        response = json.loads(fetch(urllib.request.Request(SERVER + '/oauth/tiktok/token', data=body)))
        if not response.get('access_token') or not response.get('refresh_token'):
            raise ValueError('Token refresh failed')
        response['client_id'] = token['client_id']
        response['expires_at'] = now + int(response['expires_in']) - 600
        save_token(path, key, response)
        token = response
    return token['access_token']


def call(name, arguments, token, fetch=None):
    fetch = fetch or (lambda req: urllib.request.urlopen(req, timeout=30).read())
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
               'params': {'name': name, 'arguments': arguments}}
    request = urllib.request.Request(SERVER, data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    outer = json.loads(fetch(request))
    if outer.get('error') or outer.get('result', {}).get('isError'):
        raise ValueError('TikTok tool failure')
    response = json.loads(outer['result']['content'][0]['text'])
    if response.get('code') != 0 or not isinstance(response.get('data'), dict):
        raise ValueError('TikTok provider failure')
    return response['data']


def all_pages(name, args, key, token, fetch=None, max_pages=100):
    args = dict(args)
    results, seen = [], set()
    for _ in range(max_pages):
        page = call(name, args, token, fetch)
        values = page.get(key) or []
        if not isinstance(values, list) or not isinstance(page.get('has_more'), bool):
            raise ValueError('Incomplete TikTok response')
        results.extend(values)
        if not page['has_more']:
            return results
        cursor = str(page['cursor'])
        if cursor in seen:
            raise ValueError('Repeated TikTok cursor')
        seen.add(cursor)
        # TikTok's MCP server converts large integer video cursors to scientific notation.
        args['cursor'] = cursor if name == 'account_user_post_list_get' else int(cursor)
    raise RuntimeError('TikTok pagination limit reached')


def collect(token, fetch=None, posts_out=None):
    posts = all_pages('account_user_post_list_get', {'fields': ['item_id', 'create_time'],
                      'max_count': 20}, 'videos', token, fetch, max_pages=50)
    if posts_out is not None:
        posts_out.extend(str(post['item_id']) for post in posts)
    rows = []
    for post in posts:
        video = str(post['item_id'])
        args = {'video_id': video, 'status': 'PUBLIC', 'max_count': 30,
                'sort_field': 'create_time', 'sort_order': 'desc'}
        comments = all_pages('account_user_comment_list_get', args, 'comments', token, fetch)
        for comment in comments:
            rows.append(row(comment, video, ''))
            if int(comment.get('replies', 0)):
                opts = dict(args, comment_id=str(comment['comment_id']))
                for reply in all_pages('account_user_comment_reply_list_get', opts, 'comments', token, fetch):
                    rows.append(row(reply, video, str(comment['comment_id'])))
    return rows, len(posts)


def row(comment, video, parent):
    if str(comment['video_id']) != video:
        raise ValueError('Unexpected TikTok video')
    return (str(comment['comment_id']), video, parent, str(comment['create_time']),
            str(comment['text']), int(bool(comment.get('owner', False))))


def store(path, rows, posts=None):
    db = sqlite3.connect(path)
    os.chmod(path, 0o600)
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS comments
            (id TEXT PRIMARY KEY, video TEXT NOT NULL, parent TEXT NOT NULL, published TEXT NOT NULL,
             body TEXT NOT NULL, owner INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'unreviewed')''')
        db.execute('CREATE TABLE IF NOT EXISTS polls (id INTEGER PRIMARY KEY CHECK(id=1), checked TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS published_posts (id TEXT PRIMARY KEY)')
        with db:
            db.execute('CREATE TEMP TABLE seen_ids (id TEXT PRIMARY KEY)')
            db.executemany('INSERT OR IGNORE INTO seen_ids(id) VALUES(?)', [(r[0],) for r in rows])
            db.executemany('''INSERT INTO comments(id,video,parent,published,body,owner) VALUES(?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET body=excluded.body, owner=excluded.owner,
                state=CASE WHEN comments.body != excluded.body THEN 'unreviewed' ELSE comments.state END''', rows)
            db.execute('DELETE FROM comments WHERE id NOT IN (SELECT id FROM seen_ids)')
            if posts is not None:
                db.execute('DELETE FROM published_posts')
                db.executemany('INSERT OR IGNORE INTO published_posts(id) VALUES(?)',[(p,) for p in posts])
            db.execute('''INSERT INTO polls(id,checked) VALUES(1,CURRENT_TIMESTAMP)
                       ON CONFLICT(id) DO UPDATE SET checked=CURRENT_TIMESTAMP''')
    finally:
        db.close()


def main():
    credentials = Path(os.environ['CREDENTIALS_DIRECTORY'])
    state = Path(os.environ['STATE_DIRECTORY'])
    token = access_token(credentials, state)
    post_ids=[]
    rows, videos = collect(token,posts_out=post_ids)
    store(state / 'comments.sqlite', rows,post_ids)
    print('TikTok public comment poll succeeded; videos:', videos, 'comments:', len(rows))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('TikTok public comment poll failed:', type(exc).__name__, file=sys.stderr)
        sys.exit(1)
