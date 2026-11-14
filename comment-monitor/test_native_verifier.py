import datetime as dt,json,sqlite3,tempfile,unittest
from pathlib import Path
import native_verifier as v

NOW=dt.datetime(2026,11,14,11,30,tzinfo=dt.timezone.utc)
RECORD={'slot':'20261114-am','request_id':'a'*32,'posts':{
 'youtube':{'status':'sent','url':'https://www.youtube.com/shorts/6EsKNU-E2CQ'},
 'tiktok':{'status':'sent','url':'https://www.tiktok.com/@cwhereucheaper.co/video/12345'},
 'facebook':{'status':'sent','url':'https://www.facebook.com/reel/67890/'}}}

def fixture(path,service,checked):
 with sqlite3.connect(path) as db:
  db.execute('CREATE TABLE polls(id INTEGER,checked TEXT)');db.execute('INSERT INTO polls VALUES(1,?)',(checked,))
  if service=='tiktok':
   db.execute('CREATE TABLE published_posts(id TEXT PRIMARY KEY)');db.execute("INSERT INTO published_posts VALUES('12345')")
  else:
   db.execute('CREATE TABLE published_posts(id TEXT PRIMARY KEY,permalink TEXT)');db.execute("INSERT INTO published_posts VALUES('page_1','https://www.facebook.com/reel/67890/')")

def fetch(url,headers):
 assert 'key' not in url
 assert headers['X-Goog-Api-Key']=='secret'
 return {'items':[{'id':'6EsKNU-E2CQ','snippet':{'channelId':v.CHANNEL,'publishedAt':'2026-11-14T10:30:48Z'},'status':{'privacyStatus':'public'}}]}

class NativeVerifierTests(unittest.TestCase):
 def test_all_native_paths_and_publication_scope(self):
  with tempfile.TemporaryDirectory() as d:
   t=Path(d)/'t.sqlite';f=Path(d)/'f.sqlite'
   fixture(t,'tiktok','2026-11-14 11:00:00');fixture(f,'facebook','2026-11-14 11:00:00')
   self.assertEqual(v.verify(RECORD,'secret',NOW,fetch,t,f),{'youtube':'public_confirmed','tiktok':'found_owned','facebook':'found_owned'})
 def test_old_youtube_video_cannot_verify_a_new_slot(self):
  old=lambda u,h:{'items':[{'id':'6EsKNU-E2CQ','snippet':{'channelId':v.CHANNEL,'publishedAt':'2026-11-13T10:30:00Z'},'status':{'privacyStatus':'public'}}]}
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(v.verify(RECORD,'secret',NOW,old,Path(d)/'missing',Path(d)/'missing')['youtube'],'unknown')
 def test_stale_and_missing_inventory_are_unknown_not_failed(self):
  with tempfile.TemporaryDirectory() as d:
   t=Path(d)/'t.sqlite';fixture(t,'tiktok','2026-11-14 09:00:00')
   out=v.verify(RECORD,'secret',NOW,fetch,t,Path(d)/'missing')
   self.assertEqual(out['tiktok'],'unknown');self.assertEqual(out['facebook'],'unknown')
 def test_wrong_channel_and_untrusted_links_fail_closed(self):
  self.assertEqual(v.identify('tiktok','https://tiktok.com/@other/video/12345'),None)
  self.assertEqual(v.identify('youtube','https://evil.example/shorts/6EsKNU-E2CQ'),None)
  self.assertEqual(v.youtube('6EsKNU-E2CQ','secret',lambda u,h:{'items':[{'id':'6EsKNU-E2CQ','snippet':{'channelId':'other'},'status':{'privacyStatus':'public'}}]}),'unknown')
 def test_partial_page_or_invalid_record_does_not_become_success(self):
  with self.assertRaises(ValueError):v.records(lambda *a:{},NOW)
  with self.assertRaises(ValueError):v.verify({'slot':'invalid','request_id':'a'*32},'secret',NOW,fetch)
 def test_status_records_are_private(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'status.sqlite';v.store(p,RECORD,{'youtube':'public_confirmed','tiktok':'unknown','facebook':'pending'},NOW)
   with sqlite3.connect(p) as db:self.assertEqual(db.execute('select youtube,tiktok,facebook from checks').fetchone(),('public_confirmed','unknown','pending'))
   self.assertEqual(p.stat().st_mode & 0o777,0o600)
if __name__=='__main__':unittest.main()

class ReleasePaginationTests(unittest.TestCase):
 def test_old_first_page_does_not_hide_a_newer_verification_release(self):
  old={'tag_name':'old','published_at':'2026-10-01T00:00:00Z'}
  recent={'tag_name':'response-native-20261114-am','published_at':'2026-11-14T11:00:00Z','body':json.dumps(RECORD)}
  calls=[]
  def fetch(url,headers):
   calls.append(url)
   return [old]*100 if url.endswith('&page=1') else [recent]
  rows=v.records(fetch,NOW)
  self.assertEqual(len(calls),2);self.assertEqual(rows[0]['slot'],'20261114-am')
