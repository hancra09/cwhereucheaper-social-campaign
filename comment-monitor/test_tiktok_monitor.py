import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tiktok_monitor import access_token, collect, store


def result(data):
    return json.dumps({'result': {'content': [{'text': json.dumps({'code': 0, 'data': data})}]}}).encode()


class TikTokMonitorTests(unittest.TestCase):
    def test_paginated_posts_comments_and_replies(self):
        def fetch(request):
            payload = json.loads(request.data)
            name = payload['params']['name']; args = payload['params']['arguments']
            self.assertNotIn('test-token', request.full_url)
            if name == 'account_user_post_list_get':
                if 'cursor' not in args:
                    return result({'videos': [{'item_id': 'v1'}], 'has_more': True, 'cursor': 1794045181316})
                self.assertEqual(args['cursor'], '1794045181316')
                return result({'videos': [{'item_id': 'v2'}], 'has_more': False})
            if name == 'account_user_comment_list_get':
                comments = [] if args['video_id'] == 'v2' else [{'comment_id': 'c1', 'video_id': 'v1',
                    'create_time': '123', 'text': 'Check milk', 'owner': False, 'replies': 1}]
                return result({'comments': comments, 'has_more': False})
            self.assertEqual(args['comment_id'], 'c1')
            return result({'comments': [{'comment_id': 'r1', 'video_id': 'v1', 'create_time': '124',
                'text': 'Please do', 'owner': False}], 'has_more': False})
        rows, count = collect('test-token', fetch)
        self.assertEqual(count, 2)
        self.assertEqual([(x[0], x[2]) for x in rows], [('c1', ''), ('r1', 'c1')])

    def test_refresh_token_is_rotated_into_encrypted_state(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); credentials = p / 'credentials'; state = p / 'state'
            credentials.mkdir(); state.mkdir()
            (credentials / 'tiktok-envelope').write_bytes(b'x' * 32)
            (credentials / 'tiktok-social').write_text(json.dumps({'client_id': 'id',
                'access_token': 'old-secret', 'refresh_token': 'old-refresh', 'expires_in': 7201}))
            self.assertEqual(access_token(credentials, state, now=100), 'old-secret')
            def refresh(req):
                self.assertNotIn('old-refresh', req.full_url)
                return json.dumps({'access_token': 'new-secret', 'refresh_token': 'new-refresh',
                                   'expires_in': 86400}).encode()
            self.assertEqual(access_token(credentials, state, fetch=refresh, now=102), 'new-secret')
            self.assertNotIn(b'new-secret', (state / 'token.enc').read_bytes())
            self.assertEqual(access_token(credentials, state, now=103), 'new-secret')

    def test_store_reconciles_and_requeues_edited_comments(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'comments.sqlite'
            store(db, [('a','v','','1','milk',0), ('b','v','','2','bread',0)])
            with sqlite3.connect(db) as con: con.execute("UPDATE comments SET state='reviewed'")
            store(db, [('a','v','','1','tea',0)])
            with sqlite3.connect(db) as con:
                self.assertEqual(con.execute('SELECT id,body,state FROM comments').fetchall(), [('a','tea','unreviewed')])

    def test_provider_error_fails_closed(self):
        def fetch(req):
            return json.dumps({'result': {'content': [{'text': json.dumps({'code': 999, 'data': {}})}]}}).encode()
        with self.assertRaises(ValueError): collect('test-token', fetch)


if __name__ == '__main__': unittest.main()
