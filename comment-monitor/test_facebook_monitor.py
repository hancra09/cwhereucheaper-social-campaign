import json
import tempfile
import unittest
from pathlib import Path
import facebook_monitor as m


class FacebookMonitorTests(unittest.TestCase):
    def test_comments_and_replies(self):
        post = {'id':'p1','account_id':m.ACCOUNT,'platform':'facebook'}
        parent = {'id':'c1','platform':'facebook','text':'what is cheaper?', 'created_at':'2026-11-14', 'has_replies':True}
        reply = {'id':'c2','platform':'facebook','text':'please check milk', 'created_at':'2026-11-14'}
        batches = iter([{'data':[post],'pagination':{'has_more':False}}, {'data':[parent],'pagination':{'has_more':False}}, {'data':[reply],'pagination':{'has_more':False}}])
        count, rows = m.collect('key', lambda req: json.dumps(next(batches)).encode())
        self.assertEqual((count,len(rows),rows[1][2]), (1,2,'c1'))

    def test_incomplete_pagination_fails(self):
        with self.assertRaises(ValueError):
            m.pages('inbox/comments','key',lambda req: b'{"data":[],"pagination":{"has_more":true}}')

    def test_failed_scan_does_not_erase_stored_comments(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'comments.sqlite'
            m.store(path,[('c','p','','2026-11-14','question',0)])
            with self.assertRaises(ValueError):
                m.collect('key',lambda req: b'{"error":"failed"}')
            import sqlite3
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('select count(*) from comments').fetchone()[0],1)


if __name__ == '__main__': unittest.main()
