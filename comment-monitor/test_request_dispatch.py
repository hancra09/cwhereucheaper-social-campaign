import json,sqlite3,unittest
from request_dispatch import run as real_run

def run(db,token,candidates,call):
 return real_run(db,token,candidates,call,guard_active=False)

class DispatchTests(unittest.TestCase):
 def test_synthetic_request_dispatch_excludes_comment_and_reconciles(self):
  calls=[]
  def api(path,token,payload=None):
   calls.append((path,payload))
   if '/runs?' in path:return {'workflow_runs':[{'display_title':'viewer-'+rid+'-1','status':'completed'}]}
   if path.startswith('releases/tags/'):return {'body':json.dumps({'state':'scheduled'})}
  with sqlite3.connect(':memory:') as db:
   run(db,'test',[('facebook','fake-comment-id','digest','delivery_total_v1','')],api)
   rid=db.execute('SELECT request_id FROM requests').fetchone()[0]
   payload=calls[0][1]
   self.assertNotIn('fake-comment-id',json.dumps(payload))
   self.assertEqual(payload['inputs']['request_topic'],'delivery_total_v1')
   run(db,'test',[],api)
   self.assertEqual(db.execute('SELECT state FROM requests').fetchone()[0],'scheduled')
   self.assertEqual(sum('dispatches' in path for path,_ in calls),1)
 def test_unfinished_workflow_never_dispatches_again(self):
  calls=[]
  def api(path,token,payload=None):
   calls.append(path)
   if '/runs?' in path:return {'workflow_runs':[{'display_title':'viewer-'+rid+'-1','status':'in_progress'}]}
  with sqlite3.connect(':memory:') as db:
   run(db,'test',[('tiktok','id','digest','delivery_total_v1','')],api)
   rid=db.execute('SELECT request_id FROM requests').fetchone()[0]
   run(db,'test',[],api)
   self.assertEqual(sum('dispatches' in p for p in calls),1)

if __name__=='__main__':unittest.main()

class IntakeTests(unittest.TestCase):
 def test_synthetic_request_is_detected_from_private_store(self):
  import tempfile,datetime
  from pathlib import Path
  from request_dispatch import read_candidates
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'comments.sqlite'
   with sqlite3.connect(path) as db:
    db.execute('CREATE TABLE polls (id INTEGER,checked TEXT)')
    db.execute('INSERT INTO polls VALUES (1,CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE comments (id TEXT,body TEXT,owner INTEGER)')
    db.execute('INSERT INTO comments VALUES (?,?,?)',('fake','Please show how delivery fees can change which basket is cheaper?',0))
    db.execute('INSERT INTO comments VALUES (?,?,?)',('owner','Can you compare delivery fees?',1))
   rows=read_candidates({'facebook':path})
   self.assertEqual(len(rows),1)
   self.assertEqual((rows[0][0],rows[0][1],rows[0][3]),('facebook','fake','delivery_total_v1'))
   self.assertNotIn('Please show',repr(rows))

class ProductIntakeTests(unittest.TestCase):
 def test_synthetic_named_product_stays_private(self):
  import tempfile
  from pathlib import Path
  from request_dispatch import read_candidates
  body='Please check the price of Rhodes Guava Nectar Juice 1lt?'
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'comments.sqlite'
   with sqlite3.connect(p) as db:
    db.execute('CREATE TABLE polls(id INTEGER,checked TEXT)');db.execute('INSERT INTO polls VALUES(1,CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE comments(id TEXT,body TEXT,owner INTEGER)');db.execute('INSERT INTO comments VALUES(?,?,0)',('fake-comment',body))
   rows=read_candidates({'facebook':p},[(23895,'Rhodes Guava Nectar Juice 1lt')])
   self.assertEqual(len(rows),1);self.assertEqual(rows[0][3:],('product_price_v1','23895'))
   sent=[]
   with sqlite3.connect(':memory:') as state:
    run(state,'dummy',rows,lambda path,token,payload=None:sent.append(payload))
   self.assertEqual(sent[0]['inputs']['request_subject'],'23895')
   self.assertNotIn(body,json.dumps(sent));self.assertNotIn('fake-comment',json.dumps(sent))

class UnhandledTests(unittest.TestCase):
 def test_unsupported_question_recorded_privately(self):
  import tempfile
  from pathlib import Path
  from request_dispatch import read_candidates
  question='Where is Clover milk cheapest?'
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'c.sqlite'
   with sqlite3.connect(p) as db:
    db.execute('CREATE TABLE polls(id INTEGER,checked TEXT)');db.execute('INSERT INTO polls VALUES(1,CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE comments(id TEXT,body TEXT,owner INTEGER)');db.execute('INSERT INTO comments VALUES(?,?,0)',('q',question))
   candidates=read_candidates({'facebook':p},[])
   self.assertEqual(len(candidates),0);self.assertEqual(len(candidates.unhandled),1)
   with sqlite3.connect(':memory:') as state:
    run(state,'dummy',candidates,lambda *args: self.fail('must not dispatch'))
    saved=state.execute('SELECT source,comment_id,body_sha FROM unhandled').fetchall()
    self.assertEqual(len(saved),1);self.assertNotIn(question,repr(saved))

class MigrationTests(unittest.TestCase):
 def test_existing_live_selector_state_is_preserved(self):
  with sqlite3.connect(':memory:') as db:
   db.execute('''CREATE TABLE requests(source TEXT,comment_id TEXT,body_sha TEXT,topic TEXT,request_id TEXT,state TEXT,attempted_at TEXT,attempt INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(source,comment_id,body_sha))''')
   db.execute("INSERT INTO requests(source,comment_id,body_sha,topic,request_id,state) VALUES('facebook','x','h','delivery_total_v1','a','scheduled')")
   run(db,'dummy',[],lambda *args:self.fail('must not dispatch'))
   self.assertEqual(db.execute('select topic,subject,state from requests').fetchone(),('delivery_total_v1','','scheduled'))

class WithdrawalTests(unittest.TestCase):
 def test_deleted_comment_is_not_dispatched_again_after_failure(self):
  from request_dispatch import Candidates
  import datetime
  with sqlite3.connect(':memory:') as db:
   original=[('facebook','q','digest','delivery_total_v1','')]
   run(db,'dummy',original,lambda *args:None)
   db.execute("UPDATE requests SET attempted_at=?",((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=3)).isoformat(),));db.commit()
   fresh=Candidates();fresh.available.add('facebook')
   def api(path,token,payload=None):
    if '/runs?' in path:return {'workflow_runs':[]}
    if path.startswith('releases/tags/'):
     import urllib.error
     raise urllib.error.HTTPError('https://example.invalid',404,'missing',{},None)
    self.fail('withdrawn request must not dispatch')
   run(db,'dummy',fresh,api)
   self.assertEqual(db.execute('SELECT state FROM requests').fetchone()[0],'withdrawn')

class ComparisonIntakeTests(unittest.TestCase):
 def test_comparison_request_sends_only_public_product_ids(self):
  import tempfile
  from pathlib import Path
  from request_dispatch import read_candidates
  body='Please compare 20kg Ideal Adult Dog Food at Animals First and Turf Hyper?'
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'comments.sqlite'
   with sqlite3.connect(p) as db:
    db.execute('CREATE TABLE polls(id INTEGER,checked TEXT)');db.execute('INSERT INTO polls VALUES(1,CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE comments(id TEXT,body TEXT,owner INTEGER)');db.execute('INSERT INTO comments VALUES(?,?,0)',('fake-comparison',body))
   rows=read_candidates({'facebook':p},[],[(14535,'20kg Ideal Adult Dog Food',30273,'IDEAL ADULT DOG FOOD 20KG')])
   self.assertEqual(rows[0][3:],('product_compare_v1','14535-30273'))
   sent=[]
   with sqlite3.connect(':memory:') as db:run(db,'dummy',rows,lambda path,token,payload=None:sent.append(payload))
   self.assertEqual(sent[0]['inputs']['request_subject'],'14535-30273')
   self.assertNotIn(body,json.dumps(sent));self.assertNotIn('fake-comparison',json.dumps(sent))

class DailyPriorityTests(unittest.TestCase):
 def test_completed_slot_free_attempt_can_retry_after_sast_midnight(self):
  import datetime
  from unittest.mock import patch
  import request_dispatch as d
  class Clock(datetime.datetime):
   @classmethod
   def now(cls,tz=None):
    value=cls(2026,11,14,22,1,tzinfo=datetime.timezone.utc)
    return value.astimezone(tz) if tz else value.replace(tzinfo=None)
  original=[('facebook','q','digest','delivery_total_v1','')];calls=[]
  with sqlite3.connect(':memory:') as db:
   d.run(db,'dummy',original,lambda path,token,payload=None:calls.append((path,payload)),guard_active=False)
   rid=db.execute('SELECT request_id FROM requests').fetchone()[0]
   db.execute("UPDATE requests SET attempted_at='2026-11-14T21:55:00+00:00'");db.commit()
   def api(path,token,payload=None):
    calls.append((path,payload))
    if '/runs?' in path:return {'workflow_runs':[{'display_title':'Cloud video campaign viewer-'+rid+'-1','status':'completed','conclusion':'success'}]}
    if path.startswith('releases/tags/'):return {'body':'{}'}
   with patch.object(d.dt,'datetime',Clock):d.run(db,'dummy',original,api,guard_active=False)
   self.assertEqual(sum('dispatches' in path for path,_ in calls),2)
   self.assertEqual(db.execute('select attempt from requests').fetchone()[0],2)

 def test_partial_reservation_keeps_waiting_after_midnight(self):
  import datetime
  from unittest.mock import patch
  import request_dispatch as d
  class Clock(datetime.datetime):
   @classmethod
   def now(cls,tz=None):
    value=cls(2026,11,14,22,1,tzinfo=datetime.timezone.utc)
    return value.astimezone(tz) if tz else value.replace(tzinfo=None)
  original=[('facebook','q','digest','delivery_total_v1','')];calls=[]
  with sqlite3.connect(':memory:') as db:
   d.run(db,'dummy',original,lambda path,token,payload=None:calls.append((path,payload)),guard_active=False)
   rid=db.execute('SELECT request_id FROM requests').fetchone()[0]
   db.execute("UPDATE requests SET attempted_at='2026-11-14T21:55:00+00:00'");db.commit()
   def api(path,token,payload=None):
    calls.append((path,payload))
    if '/runs?' in path:return {'workflow_runs':[{'display_title':'Cloud video campaign viewer-'+rid+'-1','status':'completed','conclusion':'success'}]}
    if path.startswith('releases/tags/'):return {'body':'{"slot":"20261116-am"}'}
   with patch.object(d.dt,'datetime',Clock):d.run(db,'dummy',original,api,guard_active=False)
   self.assertEqual(sum('dispatches' in path for path,_ in calls),1)

class SyntheticManifestTests(unittest.TestCase):
 def test_only_active_approved_test_dispatches_with_label(self):
  import datetime,tempfile
  from pathlib import Path
  from request_dispatch import Candidates,include_approved_synthetic
  start=datetime.datetime(2026,11,14,22,1,tzinfo=datetime.timezone.utc)
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'approved-synthetic-test.json'
   p.write_text(json.dumps({'id':'f'*32,'body':'Please show how to compare unit prices?','not_before':start.isoformat(),'expires':(start+datetime.timedelta(days=2)).isoformat()}))
   early=Candidates();include_approved_synthetic(early,tmp,start-datetime.timedelta(seconds=1));self.assertEqual(len(early),0)
   active=Candidates();include_approved_synthetic(active,tmp,start);self.assertEqual(len(active),1)
   calls=[]
   with sqlite3.connect(':memory:') as db:run(db,'dummy',active,lambda path,token,payload=None:calls.append(payload))
   self.assertEqual(calls[0]['inputs']['request_origin'],'synthetic')
   self.assertNotIn('Please show',json.dumps(calls))
   late=Candidates();include_approved_synthetic(late,tmp,start+datetime.timedelta(days=2));self.assertEqual(len(late),0);self.assertIn('synthetic',late.available)
 def test_unapproved_manifest_fails_closed(self):
  import tempfile
  from pathlib import Path
  from request_dispatch import Candidates,include_approved_synthetic
  with tempfile.TemporaryDirectory() as tmp:
   (Path(tmp)/'approved-synthetic-test.json').write_text(json.dumps({'id':'f'*32,'body':'Fake other suggestion'}))
   with self.assertRaises(ValueError):include_approved_synthetic(Candidates(),tmp)

class SyntheticPriorityTests(unittest.TestCase):
 def test_real_request_wins_and_test_does_not_suppress_it(self):
  candidates=[('synthetic','fake','hash1','unit_price_v1',''),('youtube','real','hash2','unit_price_v1','')]
  calls=[]
  with sqlite3.connect(':memory:') as db:
   run(db,'dummy',candidates,lambda path,token,payload=None:calls.append(payload))
   self.assertEqual(db.execute('select count(*) from requests').fetchone()[0],2)
   self.assertEqual(calls[0]['inputs']['request_origin'],'')
   self.assertEqual(db.execute("select state from requests where source='synthetic'").fetchone()[0],'pending')

class RequestConcurrencyTests(unittest.TestCase):
 def test_inflight_synthetic_is_reconciled_before_new_real_dispatch(self):
  fake=('synthetic','fake','hash1','unit_price_v1','');real=('youtube','real','hash2','unit_price_v1','');calls=[]
  with sqlite3.connect(':memory:') as db:
   run(db,'dummy',[fake],lambda path,token,payload=None:calls.append((path,payload)))
   rid=db.execute('select request_id from requests').fetchone()[0]
   def api(path,token,payload=None):
    calls.append((path,payload))
    if '/runs?' in path:return {'workflow_runs':[{'display_title':'Cloud video campaign viewer-'+rid+'-1','status':'in_progress'}]}
   run(db,'dummy',[fake,real],api)
   self.assertEqual(sum('dispatches' in path for path,_ in calls),1)
   self.assertEqual(db.execute("select state from requests where source='youtube'").fetchone()[0],'pending')

class RecoveryAndQueueTests(unittest.TestCase):
 def test_stalled_request_does_not_block_a_different_request(self):
  first=('facebook','one','hash1','delivery_total_v1','');second=('youtube','two','hash2','bulk_buying_v1','');calls=[]
  with sqlite3.connect(':memory:') as db:
   real_run(db,'dummy',[first],lambda path,token,payload=None:calls.append((path,payload)),guard_active=False)
   rid=db.execute('select request_id from requests').fetchone()[0]
   def api(path,token,payload=None):
    calls.append((path,payload))
    if '/runs?' in path:return {'workflow_runs':[{'display_title':'Cloud video campaign viewer-'+rid+'-1','status':'completed','conclusion':'failure'}]}
    if path.startswith('releases/tags/'):return {'body':'{}'}
   real_run(db,'dummy',[first,second],api,guard_active=False)
   sends=[payload for path,payload in calls if 'dispatches' in path]
   self.assertEqual(len(sends),2);self.assertEqual(sends[-1]['inputs']['request_topic'],'bulk_buying_v1')
 def test_existing_campaign_run_prevents_new_dispatch(self):
  calls=[]
  def api(path,token,payload=None):
   calls.append(path)
   if '/runs?' in path:return {'workflow_runs':[{'status':'in_progress','display_title':'Cloud video campaign prime'}]}
  with sqlite3.connect(':memory:') as db:
   real_run(db,'dummy',[('youtube','real','hash','unit_price_v1','')],api)
   self.assertEqual(db.execute('select state from requests').fetchone()[0],'pending')
   self.assertFalse(any('dispatches' in p for p in calls))

class CoarseHealthTests(unittest.TestCase):
 def test_missing_sources_are_unknown_and_unhandled_has_no_details(self):
  from request_dispatch import Candidates,health_flags
  candidates=Candidates();candidates.available.update(('youtube','tiktok'))
  with sqlite3.connect(':memory:') as db:
   db.execute('CREATE TABLE requests(state TEXT,created_at TEXT)')
   flags=health_flags(candidates,db,True)
   self.assertEqual(flags,{'sources':'attention','unhandled':'unknown','stalled':'none','processing':'ok'})
   candidates.unhandled.append(('facebook','private-id','private-hash'))
   flags=health_flags(candidates,db,True)
   self.assertEqual(flags['unhandled'],'present');self.assertNotIn('private-id',str(flags))
 def test_old_pending_request_is_marked_without_counts(self):
  from request_dispatch import Candidates,health_flags
  candidates=Candidates();candidates.available.update(('youtube','tiktok','facebook'))
  with sqlite3.connect(':memory:') as db:
   db.execute('CREATE TABLE requests(state TEXT,created_at TEXT)');db.execute("INSERT INTO requests VALUES('pending','2000-01-01 00:00:00')")
   flags=health_flags(candidates,db,True);self.assertEqual(flags['stalled'],'present');self.assertEqual(flags['sources'],'available')

class CoarseHealthUnknownTests(unittest.TestCase):
 def test_missing_state_does_not_claim_no_stalled_requests(self):
  from request_dispatch import Candidates,health_flags
  c=Candidates();c.available.update(('youtube','tiktok','facebook'))
  with sqlite3.connect(':memory:') as db:
   flags=health_flags(c,db,True)
  self.assertEqual(flags['stalled'],'unknown');self.assertEqual(flags['processing'],'attention')
