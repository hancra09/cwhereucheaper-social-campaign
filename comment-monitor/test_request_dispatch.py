import json,sqlite3,unittest
from request_dispatch import run

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
   d.run(db,'dummy',original,lambda path,token,payload=None:calls.append((path,payload)))
   rid=db.execute('SELECT request_id FROM requests').fetchone()[0]
   db.execute("UPDATE requests SET attempted_at='2026-11-14T21:55:00+00:00'");db.commit()
   def api(path,token,payload=None):
    calls.append((path,payload))
    if '/runs?' in path:return {'workflow_runs':[{'display_title':'Cloud video campaign viewer-'+rid+'-1','status':'completed','conclusion':'success'}]}
    if path.startswith('releases/tags/'):return {'body':'{}'}
   with patch.object(d.dt,'datetime',Clock):d.run(db,'dummy',original,api)
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
   d.run(db,'dummy',original,lambda path,token,payload=None:calls.append((path,payload)))
   rid=db.execute('SELECT request_id FROM requests').fetchone()[0]
   db.execute("UPDATE requests SET attempted_at='2026-11-14T21:55:00+00:00'");db.commit()
   def api(path,token,payload=None):
    calls.append((path,payload))
    if '/runs?' in path:return {'workflow_runs':[{'display_title':'Cloud video campaign viewer-'+rid+'-1','status':'completed','conclusion':'success'}]}
    if path.startswith('releases/tags/'):return {'body':'{"slot":"20261116-am"}'}
   with patch.object(d.dt,'datetime',Clock):d.run(db,'dummy',original,api)
   self.assertEqual(sum('dispatches' in path for path,_ in calls),1)
