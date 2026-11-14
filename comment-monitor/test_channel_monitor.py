import json
import tempfile
import unittest
from pathlib import Path
from channel_monitor import CHANNEL, collect, pages, store


def comment(cid, text, parent=None):
    s = {'publishedAt': '2026-11-14T10:00:00Z', 'textDisplay': text}
    if parent is not None:
        s['parentId'] = parent
    return {'id': cid, 'snippet': s}


class ChannelTests(unittest.TestCase):
    def test_reads_threads_and_all_replies_without_exposing_key(self):
        def fetch(req):
            self.assertNotIn('key-value', req.full_url)
            self.assertEqual(req.get_header('X-goog-api-key'), 'key-value')
            if '/commentThreads?' in req.full_url:
                return json.dumps({'items': [{'snippet': {'channelId': CHANNEL, 'videoId': 'v',
                    'topLevelComment': comment('top', 'Question'), 'totalReplyCount': 1}}]}).encode()
            return json.dumps({'items': [comment('reply', 'Check milk', 'top')]}).encode()
        self.assertEqual([r[0] for r in collect('key-value', fetch)], ['top', 'reply'])

    def test_rejects_wrong_channel_and_pagination_overflow(self):
        wrong = {'items': [{'snippet': {'channelId': 'other'}}]}
        with self.assertRaises(ValueError): collect('key', lambda req: json.dumps(wrong).encode())
        with self.assertRaises(RuntimeError):
            pages('comments', {}, 'key', lambda req: b'{"items":[],"nextPageToken":"again"}', limit=1)

    def test_store_marks_changed_comments_unreviewed(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'private' / 'db'
            store(path, [('x','v','','2026-11-14','milk',0)])
            with sqlite3.connect(path) as db: db.execute("UPDATE comments SET state='reviewed'")
            store(path, [('x','v','','2026-11-14','bread',0)])
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('SELECT body,state FROM comments').fetchone(), ('bread','unreviewed'))
            store(path, [])
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM comments').fetchone()[0], 0)


if __name__ == '__main__': unittest.main()

class OwnerTests(unittest.TestCase):
 def test_known_owner_and_unidentified_author(self):
  from channel_monitor import row
  self.assertEqual(row({'id':'a','snippet':{'publishedAt':'x','textDisplay':'x','authorChannelId':{'value':CHANNEL}}},'v','')[-1],1)
  self.assertEqual(row({'id':'b','snippet':{'publishedAt':'x','textDisplay':'x'}},'v','')[-1],-1)
  self.assertEqual(row({'id':'c','snippet':{'publishedAt':'x','textDisplay':'x','authorChannelId':{'value':'other'}}},'v','')[-1],0)
