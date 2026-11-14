import datetime as dt
import unittest
from indiepost_guard import eligible, LOST_AUTH

class RecoveryGuardTest(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,15,7,0,tzinfo=dt.timezone.utc)
        self.ledger={'due_sast':'2026-11-15T08:00:00+02:00','posts':{'facebook':{'id':'p1'}},'content':{}}
        self.post={'id':'p1','status':'error','externalLink':None,'error':{'message':next(iter(LOST_AUTH))}}
    def check(self, rows=None): return eligible(self.ledger,'facebook',[self.post] if rows is None else rows,self.now)
    def test_specific_lost_authorization(self): self.assertTrue(self.check())
    def test_unknown_failure_cannot_trigger(self):
        self.post['error']['message']='Unknown error: the post may already be live'
        self.assertFalse(self.check())
    def test_existing_public_link_cannot_trigger(self):
        self.post['externalLink']='https://facebook.com/reel/123'
        self.assertFalse(self.check())
    def test_scheduled_and_wrong_or_ambiguous_posts_cannot_trigger(self):
        self.post['status']='scheduled';self.assertFalse(self.check())
        self.post['status']='error';self.post['id']='different';self.assertFalse(self.check())
        self.post['id']='p1';self.assertFalse(self.check([self.post,self.post]))
    def test_price_evidence_requires_fresh_research(self):
        self.ledger['content']['evidence_product_id']='p';self.assertFalse(self.check())
    def test_too_early(self):
        self.assertFalse(eligible(self.ledger,'facebook',[self.post],dt.datetime(2026,11,15,6,10,tzinfo=dt.timezone.utc)))

if __name__ == '__main__':unittest.main()
