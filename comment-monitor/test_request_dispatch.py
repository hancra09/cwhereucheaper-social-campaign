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
