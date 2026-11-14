"""Read Facebook Page comments through a restricted SocialAPI key."""
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = 'https://api.social-api.ai/v1/'
ACCOUNT = 'acc_01M7CTNY8J7N2NCND671P65ETF'


def pages(path, key, fetch=None, limit=100):
    if not key:
        raise ValueError('Missing credential')
    fetch = fetch or (lambda req: urllib.request.urlopen(req, timeout=30).read())
    cursor, seen, rows = '', set(), []
    for _ in range(limit):
        query = {'account_id': ACCOUNT, 'limit': 100}
        if cursor:
            query['cursor'] = cursor
        req = urllib.request.Request(API + path + '?' + urllib.parse.urlencode(query),
                                     headers={'Authorization': 'Bearer ' + key})
        data = json.loads(fetch(req))
        if not isinstance(data, dict) or not isinstance(data.get('data'), list) or not isinstance(data.get('pagination'), dict):
            raise ValueError('Invalid response')
        rows.extend(data['data'])
        pg = data['pagination']
        cursor = pg.get('next_cursor') or ''
        if not pg.get('has_more') and not cursor:
            return rows
        if not cursor or cursor in seen:
            raise ValueError('Incomplete or repeated cursor')
        seen.add(cursor)
    raise RuntimeError('Page limit reached')


def collect(key, fetch=None, posts_out=None):
    posts = pages('inbox/comments', key, fetch)
    rows = []
    for post in posts:
        if post.get('account_id') != ACCOUNT or post.get('platform') != 'facebook':
            raise ValueError('Unexpected account or platform')
        post_id = str(post['id'])
        if posts_out is not None:posts_out.append((post_id,str(post.get('permalink') or '')))
        path = 'inbox/comments/' + urllib.parse.quote(post_id, safe='')
        for comment in pages(path, key, fetch):
            rows.append(row(comment, post_id, ''))
            if comment.get('has_replies'):
                reply_path = path + '/' + urllib.parse.quote(str(comment['id']), safe='') + '/replies'
                for reply in pages(reply_path, key, fetch):
                    rows.append(row(reply, post_id, str(comment['id'])))
    return len(posts), rows


def row(comment, post, parent):
    if comment.get('platform') != 'facebook':
        raise ValueError('Unexpected platform')
    return (str(comment['id']), post, parent, str(comment['created_at']),
            str(comment['text']), int(bool(comment.get('is_owner', False))))


def store(path, rows, posts=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(path)
    os.chmod(path, 0o600)
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS comments
            (id TEXT PRIMARY KEY, video TEXT NOT NULL, parent TEXT NOT NULL, published TEXT NOT NULL,
             body TEXT NOT NULL, owner INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'unreviewed')''')
        db.execute('CREATE TABLE IF NOT EXISTS polls (id INTEGER PRIMARY KEY CHECK(id=1), checked TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS published_posts (id TEXT PRIMARY KEY,permalink TEXT NOT NULL)')
        with db:
            db.execute('CREATE TEMP TABLE seen_ids (id TEXT PRIMARY KEY)')
            db.executemany('INSERT OR IGNORE INTO seen_ids(id) VALUES(?)', [(r[0],) for r in rows])
            db.executemany('''INSERT INTO comments(id,video,parent,published,body,owner) VALUES(?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET body=excluded.body, owner=excluded.owner,
                state=CASE WHEN comments.body != excluded.body THEN 'unreviewed' ELSE comments.state END''', rows)
            db.execute('DELETE FROM comments WHERE id NOT IN (SELECT id FROM seen_ids)')
            if posts is not None:
                db.execute('DELETE FROM published_posts')
                db.executemany('INSERT OR REPLACE INTO published_posts(id,permalink) VALUES(?,?)',posts)
            db.execute('''INSERT INTO polls(id,checked) VALUES(1,CURRENT_TIMESTAMP)
                       ON CONFLICT(id) DO UPDATE SET checked=CURRENT_TIMESTAMP''')
    finally:
        db.close()


def main():
    key = (Path(os.environ['CREDENTIALS_DIRECTORY']) / 'socialapi-key').read_text().strip()
    post_refs=[]
    posts, rows = collect(key,posts_out=post_refs)
    store(Path(os.environ['STATE_DIRECTORY']) / 'comments.sqlite', rows,post_refs)
    print('Facebook comment poll succeeded; posts:', posts, 'comments:', len(rows))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Facebook comment poll failed:', type(exc).__name__, file=sys.stderr)
        sys.exit(1)
