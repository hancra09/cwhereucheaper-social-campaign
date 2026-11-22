import datetime as dt,json,re,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import campaign as c
import creative_engine as e
import media_delivery as m

class CreativeSafety(unittest.TestCase):
 def test_all_original_facts_are_retained_in_generic_narration(self):
  items=json.loads((c.ROOT/'content.json').read_text())+json.loads((c.ROOT/'content-third.json').read_text())
  for i,item in enumerate(items):
   cfg=e.lesson(item,str(i))
   if not cfg['comparison']:
    self.assertEqual(' '.join(cfg['facts']).split()[:len(cfg['core'].split())],cfg['core'].split(), item['title'])
    self.assertEqual(cfg['segments'][1:4],cfg['facts'])
   self.assertEqual(len(cfg['segments']),6)
 def test_retention_first_campaign_has_distinct_art_and_auditable_captions(self):
  day = dt.date(2026, 11, 21)
  items = [c.scheduled_item(day, slot) for slot in c.SLOTS]
  self.assertEqual(len({item['format'] for item in items}), 3)
  self.assertEqual(len({item['asset'] for item in items}), 3)
  for item in items:
   self.assertEqual(item['creative_version'], 'creative-v4')
   self.assertTrue((e.ASSETS / item['asset']).is_file())
   self.assertEqual(item['beats'][-1][0], 'CHECK BEFORE YOU BUY')
   self.assertIn('CWhereUCheaper.co.za', item['beats'][-1][1])
   tag = f"20261121-{item['slot']}"
   caption = c.caption(item, 'tiktok', tag)
   self.assertIn('utm_content=' + tag + '\n', caption)
   self.assertNotIn('Start your next price check', caption)
   self.assertEqual(c.campaign_posts([{'text': caption}]), [{'text': caption}])
  tomorrow = c.scheduled_item(day + dt.timedelta(days=1), 'early')
  self.assertEqual(tomorrow['creative_version'], 'creative-v4')
  self.assertNotEqual(items[0]['script'], tomorrow['script'])

 def test_rand_pronunciation_preserves_currency_amount(self):
  self.assertEqual(e.spoken('R30 for 500 grams and R9.99 delivery.'),'thirty rand for 500 grams and nine rand and ninety-nine cents delivery.')
 def test_hundred_gram_example_has_reviewed_math(self):
  item=next(x for x in json.loads((c.ROOT/'content.json').read_text()) if x['title']=='Price per hundred grams made simple')
  cfg=e.lesson(item,'20261112-am')['comparison']
  self.assertEqual(30/500*100,6);self.assertAlmostEqual(42/600*100,7)
  self.assertEqual((cfg['small_unit'],cfg['large_unit'],cfg['unit_label']),('R6','R7','PER 100 GRAMS'))
 def test_versioned_delivery_does_not_reuse_old_cached_bytes(self):
  tree=[{'path':'20261112-am.mp4','mode':'100644','type':'blob','sha':'old'},{'path':'20261112-am-creative-v2.mp4','mode':'100644','type':'blob','sha':'new'}]
  gh=Mock(side_effect=[{'object':{'sha':'c'}},{'tree':{'sha':'t'}},{'tree':tree}])
  url=m.publish('20261112-am',f'https://github.com/{c.REPO}/releases/download/20261112-am/video-creative-v2.mp4',gh=gh,request=Mock(return_value=b'0000ftyprest'),repo=c.REPO,now=dt.datetime(2026,11,12))
  self.assertTrue(url.endswith('/20261112-am-creative-v2.mp4'))
  self.assertEqual(gh.call_count,3)
 def test_v4_cache_accepts_only_exact_same_slot_archive(self):
  entries=[{'path':'20261122-am-creative-v4.mp4','type':'blob','mode':'100644','sha':'v4'}]
  fake=lambda: Mock(side_effect=[{'object':{'sha':'c'}},{'tree':{'sha':'t'}},{'tree':entries}])
  raw=Mock(return_value=b'0000ftypv4')
  url=f'https://github.com/{c.REPO}/releases/download/20261122-am/video-creative-v4.mp4'
  now=dt.datetime(2026,11,22)
  self.assertTrue(m.publish('20261122-am',url,gh=fake(),request=raw,repo=c.REPO,now=now).endswith('/20261122-am-creative-v4.mp4'))
  with self.assertRaises(ValueError):
   m.publish('20261122-am',url.replace('20261122-am','20261123-am'),gh=fake(),request=raw,repo=c.REPO,now=now)
 def upgrade_fixture(self,status='scheduled'):
  item=c.campaign_item(dt.date(2026,11,12),'early');tag='20261112-early';url='https://public/new.mp4'
  posts=[{'id':s,'channelId':v,'status':status,'text':c.caption(item,s,tag),'dueAt':'2026-11-12T06:00:00Z','assets':[{'source':'old'}]} for s,v in c.CHANNELS.items()]
  ledger={'slot':tag,'content':item,'video':'old-video','posts':dict(zip(c.CHANNELS,posts))};release={'body':json.dumps(ledger),'id':1}
  channels=[{'service':s,'id':v,'serviceId':c.FACEBOOK_PAGE_ID if s=='facebook' else 'existing'} for s,v in c.CHANNELS.items()]
  def api(query,variables):
   if query.startswith('query'):return {'channels':channels}
   p=variables['input'];before=next(x for x in posts if x['id']==p['id'])
   self.assertNotIn('mode',p);self.assertNotIn('dueAt',p)
   return {'editPost':{'post':{**before,'text':p['text'],'assets':[{'source':url}]}}}
  return tag,url,posts,release,api
 def test_upgrade_preserves_three_ids_times_and_never_creates_a_post(self):
  tag,url,posts,release,api=self.upgrade_fixture()
  with patch.object(c,'buffer',side_effect=api) as mutation,patch.object(c,'existing_posts',return_value=posts),patch.object(c,'read_release',side_effect=lambda t:release if t==tag else None),patch.object(c,'creative_asset',return_value=('new',{'voice':'af_heart'})),patch.object(c,'delivery_url',return_value=url),patch.object(c,'save'):
   c.upgrade_creative(dt.datetime(2026,11,12,6,tzinfo=c.SAST))
  self.assertEqual(mutation.call_count,4)
  self.assertTrue(all('createPost' not in x.args[0] for x in mutation.call_args_list))
 def test_upgrade_refuses_already_published_posts(self):
  tag,url,posts,release,api=self.upgrade_fixture('sent')
  with patch.object(c,'buffer',side_effect=api) as mutation,patch.object(c,'existing_posts',return_value=posts),patch.object(c,'read_release',side_effect=lambda t:release if t==tag else None),patch.object(c,'creative_asset') as render:
   c.upgrade_creative(dt.datetime(2026,11,12,6,tzinfo=c.SAST))
   render.assert_not_called();self.assertEqual(mutation.call_count,1)

 def test_three_queue_repairs_have_distinct_product_art_and_facts(self):
  sunday, monday = dt.date(2026,11,22), dt.date(2026,11,23)
  items = [c.scheduled_item(sunday,'am'), c.scheduled_item(monday,'early'), c.scheduled_item(monday,'am')]
  self.assertEqual([item['asset'] for item in items], ['pouches.png','bottles.png','receipt.jpg'])
  self.assertEqual(len({line for item in items for _, line in item['beats'][:-1]}),12)
  self.assertTrue(all(item['beats'][-1][1].endswith('before your next checkout.') for item in items))
  self.assertIn('R54 divided by six is R9 each.',items[2]['script'])
  self.assertIn('R8 in this example',items[2]['script'])
  self.assertNotIn('I came for do the division',items[2]['script'])

 def test_previous_mini_story_caption_stays_reconcilable(self):
  item = {'title':'Old title','caption':'Old caption. What would you check first?',
          'creative_version':'creative-v3','format':'pov'}
  text = c.caption(item, 'tiktok', '20261122-am')
  self.assertIn('utm_campaign=retention_first_story',text)
  self.assertIn('Old caption. What would you check first?',text)

 def test_upgrade_does_not_edit_when_post_started_while_rendering(self):
  tag,url,posts,release,api=self.upgrade_fixture()
  changed=[dict(x,status='sending') for x in posts]
  with patch.object(c,'buffer',side_effect=api) as mutation,patch.object(c,'existing_posts',side_effect=[posts,changed]),patch.object(c,'read_release',side_effect=lambda t:release if t==tag else None),patch.object(c,'creative_asset',return_value=('new',{'voice':'af_heart'})),patch.object(c,'delivery_url',return_value=url),patch.object(c,'save') as persist:
   c.upgrade_creative(dt.datetime(2026,11,12,6,tzinfo=c.SAST),only_slots={tag})
  self.assertEqual(mutation.call_count,1)
  self.assertNotIn('creative_version',persist.call_args.args[1]['content'])

 def test_upgrade_filters_requested_slots(self):
  tag,url,posts,release,api=self.upgrade_fixture()
  with patch.object(c,'buffer',side_effect=api) as mutation,patch.object(c,'existing_posts',return_value=posts),patch.object(c,'read_release') as lookup:
   c.upgrade_creative(dt.datetime(2026,11,12,6,tzinfo=c.SAST),only_slots=set())
  lookup.assert_not_called();self.assertEqual(mutation.call_count,1)

if __name__=='__main__':unittest.main()
