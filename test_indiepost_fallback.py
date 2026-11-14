import datetime as dt
import unittest
from indiepost_guard import LOST_AUTH
from indiepost_fallback import recover

class SafeRecovery(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,15,7,0,tzinfo=dt.timezone.utc)
        self.ledger={'slot':'20261115-early','due_sast':'2026-11-15T08:00:00+02:00','posts':{'facebook':{'id':'p1','text':'A shopping tip'}},'content':{'title':'Shopping'},'video':'https://github.com/x/y/v.mp4'}
        self.row={'id':'p1','channelId':'fb','status':'error','externalLink':None,'error':{'message':next(iter(LOST_AUTH))},'text':'A shopping tip'}
        self.saved=[]; self.sent=[]
    def save(self,x): self.saved.append(x['indiepost_fallback']['facebook']['phase'])
    def send(self,data,key):
        self.assertEqual(self.saved[-1],'sending');self.sent.append(data);return {'postGroupId':'test'}
    def run_recovery(self,reader=None):return recover(self.ledger,'facebook','fb',reader or (lambda:[self.row]),self.save,self.now,upload=lambda url:'media',send=self.send)
    def test_submits_once_after_guard_and_saves_before_sending(self):
        self.assertEqual(self.run_recovery(),'submitted');self.assertEqual(self.saved,['media_ready','sending','submitted']);self.assertEqual(self.run_recovery(),'submitted');self.assertEqual(len(self.sent),1)
    def test_buffer_status_changed_during_upload(self):
        calls=[0]
        def reader():
            calls[0]+=1
            return [self.row if calls[0]==1 else {**self.row,'status':'sent'}]
        self.assertEqual(self.run_recovery(reader),'not_eligible');self.assertEqual(self.sent,[])
    def test_timeout_after_submit_never_retried(self):
        def fail(data,key):raise TimeoutError()
        with self.assertRaises(TimeoutError):recover(self.ledger,'facebook','fb',lambda:[self.row],self.save,self.now,upload=lambda url:'media',send=fail)
        self.assertEqual(self.run_recovery(),'sending');self.assertEqual(self.sent,[])
    def test_duplicate_buffer_post_blocks_recovery(self):
        duplicate={**self.row,'id':'other','status':'sent'}
        self.assertEqual(self.run_recovery(lambda:[self.row,duplicate]),'not_eligible')
    def test_wrong_channel_not_recovered(self):
        self.row['channelId']='other';self.assertEqual(self.run_recovery(),'not_eligible')

if __name__=='__main__':unittest.main()
