import datetime as dt
import json
import unittest
from unittest.mock import patch
import campaign as c

class ResponseScheduleTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,14,6,tzinfo=c.SAST)
        self.request_id='a'*32
        self.releases={}
    def load(self,tag):
        return self.releases.setdefault(tag,{'id':tag,'body':'{}','assets':[]})
    def read(self,tag): return self.releases.get(tag)
    def save(self,release,ledger): release['body']=json.dumps(ledger)
    def test_selects_only_unoccupied_slot_and_uses_existing_channels(self):
        old='20261114-early'
        self.releases[old]={'id':old,'body':json.dumps({'content':{'title':'preserve'}}),'assets':[]}
        def run(day,slot,*,now,request_item):
            tag=day.strftime('%Y%m%d')+'-'+slot
            rel=self.read(tag); ledger=json.loads(rel['body']); ledger.update({'state':'scheduled','posts':{x:{'status':'scheduled'} for x in c.CHANNELS}});self.save(rel,ledger)
        with patch.object(c,'load_release',side_effect=self.load),patch.object(c,'read_release',side_effect=self.read),patch.object(c,'save',side_effect=self.save),patch.object(c,'existing_posts',return_value=[]),patch.object(c,'render_budget',return_value=[]),patch.object(c,'run',side_effect=run),patch('response.research',return_value={'url':'https://clicks.co.za/onlineshopping'}):
            self.assertTrue(c.prepare_request(self.now,'delivery_total_v1',self.request_id))
            self.assertTrue(c.prepare_request(self.now,'delivery_total_v1',self.request_id))
        self.assertEqual(json.loads(self.releases[old]['body'])['content']['title'],'preserve')
        self.assertEqual(json.loads(self.releases['viewer-request-'+self.request_id]['body'])['slot'],'20261114-am')
    def test_queue_full_does_not_select_or_research(self):
        posts=[{'channelId':next(iter(c.CHANNELS.values())),'status':'scheduled'} for _ in range(9)]
        with patch.object(c,'load_release',side_effect=self.load),patch.object(c,'existing_posts',return_value=posts),patch('response.research') as research:
            self.assertFalse(c.prepare_request(self.now,'delivery_total_v1',self.request_id));research.assert_not_called()
    def test_invalid_topic_never_creates_release(self):
        with patch.object(c,'load_release') as load:
            with self.assertRaises(ValueError): c.prepare_request(self.now,'unknown',self.request_id)
            load.assert_not_called()

if __name__=='__main__':unittest.main()

class SyntheticPipelineTests(unittest.TestCase):
 def test_private_comment_to_simulated_schedule(self):
  import sys,tempfile,sqlite3
  from pathlib import Path
  sys.path.insert(0,str(c.ROOT/'comment-monitor'))
  import request_dispatch as d
  fake='Please show how delivery fees can change which basket is cheaper?'
  now=dt.datetime(2026,11,14,6,tzinfo=c.SAST)
  releases={}; calls=[]
  def load(tag):return releases.setdefault(tag,{'id':tag,'body':'{}','assets':[]})
  def read(tag):return releases.get(tag)
  def save(rel,ledger):rel['body']=json.dumps(ledger)
  def create_posts(day,slot,*,now,request_item):
   tag=day.strftime('%Y%m%d')+'-'+slot; rel=read(tag); ledger=json.loads(rel['body'])
   self.assertIn('R100 plus R40',request_item['script'])
   ledger.update({'state':'scheduled','posts':{x:{'status':'scheduled'} for x in c.CHANNELS}});save(rel,ledger)
  def api(path,token,payload=None):
   calls.append((path,payload))
   if path.endswith('dispatches'):
    inputs=payload['inputs']
    c.prepare_request(now,inputs['request_topic'],inputs['request_id'],inputs.get('request_subject',''),inputs.get('request_origin',''))
   elif '/runs?' in path:
    return {'workflow_runs':[{'display_title':calls[0][1]['inputs']['dispatch_id'],'status':'completed'}]}
   elif path.startswith('releases/tags/'):
    return releases[path.split('/')[-1]]
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'source.sqlite'
   with sqlite3.connect(path) as source:
    source.execute('CREATE TABLE polls(id INTEGER,checked TEXT)');source.execute('INSERT INTO polls VALUES(1,CURRENT_TIMESTAMP)')
    source.execute('CREATE TABLE comments(id TEXT,body TEXT,owner INTEGER)');source.execute('INSERT INTO comments VALUES(?,?,?)',('synthetic',fake,0))
   candidates=d.read_candidates({'facebook':path})
   with sqlite3.connect(':memory:') as state,patch.object(c,'load_release',side_effect=load),patch.object(c,'read_release',side_effect=read),patch.object(c,'save',side_effect=save),patch.object(c,'existing_posts',return_value=[]),patch.object(c,'render_budget',return_value=[]),patch.object(c,'run',side_effect=create_posts),patch('response.research',return_value={'url':'https://clicks.co.za/onlineshopping'}):
    d.run(state,'test',candidates,api,guard_active=False)
    d.run(state,'test',candidates,api,guard_active=False)
    self.assertEqual(state.execute('SELECT state FROM requests').fetchone()[0],'scheduled')
   self.assertNotIn(fake,json.dumps(calls))
   self.assertEqual(sum('dispatches' in path for path,_ in calls),1)

class ProductResponseScheduleTests(unittest.TestCase):
 def test_verified_product_uses_vacant_slot_without_touching_occupied_slot(self):
  now=dt.datetime.now(c.SAST); slot_time=now+dt.timedelta(hours=4)
  # Select a deterministic future slot by replacing the slot generator and times.
  day=now.date()+dt.timedelta(days=1); releases={}
  def load(tag): return releases.setdefault(tag,{'id':tag,'body':'{}','assets':[]})
  def read(tag): return releases.get(tag)
  def save(rel,ledger): rel['body']=json.dumps(ledger)
  e={'product_id':'23895','product':'Rhodes Guava Nectar Juice 1lt','retailer':'Superb Hyper','price':'9.99','url':'https://superbhyper.co.za/product/a/','checked_sast':now.isoformat()}
  def run(day,slot,*,now,request_item):
   self.assertIn('R9.99',request_item['script'])
   tag=day.strftime('%Y%m%d')+'-'+slot; rel=read(tag); led=json.loads(rel['body'])
   led.update({'state':'scheduled','posts':{name:{'status':'scheduled'} for name in c.CHANNELS}});save(rel,led)
  request_id='b'*32
  with patch.object(c,'future_slots',return_value=[(day,'early')]),patch.object(c,'load_release',side_effect=load),patch.object(c,'read_release',side_effect=read),patch.object(c,'save',side_effect=save),patch.object(c,'existing_posts',return_value=[]),patch.object(c,'render_budget',return_value=[]),patch.object(c,'run',side_effect=run),patch('product_response.research',return_value=e):
   self.assertTrue(c.prepare_request(now,'product_price_v1',request_id,'23895'))
   self.assertTrue(c.prepare_request(now,'product_price_v1',request_id,'23895'))
   with self.assertRaises(ValueError): c.prepare_request(now,'product_price_v1',request_id,'999')
  self.assertEqual(json.loads(releases['viewer-request-'+request_id]['body'])['state'],'scheduled')

class PriceFreshnessTests(unittest.TestCase):
 def test_changed_price_does_not_send_to_buffer(self):
  from product_response import build
  now=dt.datetime.now(c.SAST);day=now.date()+dt.timedelta(days=1)
  e={'product_id':'23895','product':'Rhodes Guava Nectar Juice 1lt','retailer':'Superb Hyper','price':'9.99','url':'https://superbhyper.co.za/product/a/','checked_sast':now.isoformat()}
  item=build(e);item['response_request_id']='c'*32
  release={'id':1,'body':json.dumps({'content':item}),'assets':[]}
  channels=[{'service':s,'id':v,'serviceId':c.FACEBOOK_PAGE_ID if s=='facebook' else 'other'} for s,v in c.CHANNELS.items()]
  with patch.object(c,'buffer',return_value={'channels':channels}) as api,patch.object(c,'existing_posts',return_value=[]),patch.object(c,'load_release',return_value=release),patch.object(c,'generate',return_value='https://example.com/video.mp4'),patch('product_response.research',return_value=dict(e,price='10.99')):
   with self.assertRaisesRegex(RuntimeError,'expired or changed'):c.run(day,'early',now=now,request_item=item)
   self.assertEqual(api.call_count,1)

class ComparisonGuardTests(unittest.TestCase):
 def test_changed_comparison_does_not_send_to_buffer(self):
  from comparison_response import build,signature
  now=dt.datetime.now(c.SAST);day=now.date()+dt.timedelta(days=1)
  one={'product_id':'14535','product':'20kg Ideal Adult Dog Food','retailer':'Animals First','price':'540.00','url':'https://animalsfirst.co.za/product/a/','checked_sast':now.isoformat()}
  two={'product_id':'30273','product':'IDEAL ADULT DOG FOOD 20KG','retailer':'Turf Pet Hyper','price':'450.00','url':'https://turfhyper.co.za/product/a/','checked_sast':now.isoformat()}
  e={'items':[one,two],'subject':'14535-30273','checked_sast':now.isoformat(),'signature':signature([one,two])}
  item=build(e);item['response_request_id']='d'*32
  release={'id':1,'body':json.dumps({'content':item}),'assets':[]}
  channels=[{'service':s,'id':v,'serviceId':c.FACEBOOK_PAGE_ID if s=='facebook' else 'other'} for s,v in c.CHANNELS.items()]
  with patch.object(c,'buffer',return_value={'channels':channels}) as api,patch.object(c,'existing_posts',return_value=[]),patch.object(c,'load_release',return_value=release),patch.object(c,'generate',return_value='https://example.com/video.mp4'),patch('comparison_response.research',return_value=dict(e,signature='changed')):
   with self.assertRaisesRegex(RuntimeError,'expired or changed'):c.run(day,'early',now=now,request_item=item)
   self.assertEqual(api.call_count,1)

class ComparisonSchedulingTests(unittest.TestCase):
 def test_researched_comparison_uses_one_vacant_slot_once(self):
  from comparison_response import signature
  now=dt.datetime.now(c.SAST);day=now.date()+dt.timedelta(days=1);releases={}
  def load(tag):return releases.setdefault(tag,{'id':tag,'body':'{}','assets':[]})
  def save(rel,ledger):rel['body']=json.dumps(ledger)
  a={'product_id':'14535','product':'20kg Ideal Adult Dog Food','retailer':'Animals First','price':'540.00','url':'https://animalsfirst.co.za/product/a/','checked_sast':now.isoformat()}
  b={'product_id':'30273','product':'IDEAL ADULT DOG FOOD 20KG','retailer':'Turf Pet Hyper','price':'450.00','url':'https://turfhyper.co.za/product/b/','checked_sast':now.isoformat()}
  evidence={'items':[a,b],'subject':'14535-30273','checked_sast':now.isoformat(),'signature':signature([a,b])}
  def simulated_run(day,slot,*,now,request_item):
   self.assertIn('two stores before delivery',request_item['script'])
   tag=day.strftime('%Y%m%d')+'-'+slot;rel=releases[tag];ledger=json.loads(rel['body']);ledger.update({'state':'scheduled','posts':{s:{'status':'scheduled'} for s in c.CHANNELS}});save(rel,ledger)
  with patch.object(c,'future_slots',return_value=[(day,'early')]),patch.object(c,'load_release',side_effect=load),patch.object(c,'read_release',side_effect=lambda tag:releases.get(tag)),patch.object(c,'save',side_effect=save),patch.object(c,'existing_posts',return_value=[]),patch.object(c,'render_budget',return_value=[]),patch.object(c,'run',side_effect=simulated_run) as run,patch('comparison_response.research',return_value=evidence):
   self.assertTrue(c.prepare_request(now,'product_compare_v1','d'*32,'14535-30273'))
   self.assertTrue(c.prepare_request(now,'product_compare_v1','d'*32,'14535-30273'))
   self.assertEqual(run.call_count,1)

class LabelledSyntheticScheduleTests(unittest.TestCase):
 def test_synthetic_video_is_labelled_and_slots_preserved(self):
  import creative_engine
  now=dt.datetime.now(c.SAST);day=now.date()+dt.timedelta(days=1);releases={}
  def load(tag):return releases.setdefault(tag,{'id':tag,'body':'{}','assets':[]})
  def save(rel,ledger):rel['body']=json.dumps(ledger)
  def fake_run(day,slot,*,now,request_item):
   self.assertTrue(request_item['synthetic_test'])
   self.assertIn('simulated viewer request',request_item['caption'])
   self.assertTrue(creative_engine.lesson(request_item,'test')['synthetic_test'])
   tag=day.strftime('%Y%m%d')+'-'+slot;rel=releases[tag];ledger=json.loads(rel['body'])
   ledger.update({'state':'scheduled','posts':{s:{'status':'scheduled'} for s in c.CHANNELS}});save(rel,ledger)
  with patch.object(c,'future_slots',return_value=[(day,'early')]),patch.object(c,'load_release',side_effect=load),patch.object(c,'read_release',side_effect=lambda tag:releases.get(tag)),patch.object(c,'save',side_effect=save),patch.object(c,'existing_posts',return_value=[]),patch.object(c,'render_budget',return_value=[]),patch.object(c,'run',side_effect=fake_run),patch('response.research',return_value={'url':'https://www.health.gov.za/wp-content/uploads/2020/11/tri-fold_pamphlet.pdf'}):
   self.assertTrue(c.prepare_request(now,'unit_price_v1','e'*32,'','synthetic'))
   self.assertEqual(json.loads(releases['viewer-request-'+'e'*32]['body'])['origin'],'synthetic')
   with self.assertRaises(ValueError):c.prepare_request(now,'product_price_v1','d'*32,'23895','synthetic')
