import datetime as dt
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import campaign as c
from content_factory import build_month, validate_plan


class CampaignSafety(unittest.TestCase):
    def setUp(self):
        self.channels = [{'service':s,'id':i,'serviceId':c.FACEBOOK_PAGE_ID if s=='facebook' else 'existing'} for s,i in c.CHANNELS.items()]
        self.now = dt.datetime(2026,11,8,11,23,tzinfo=c.SAST)
        self.release = {'id':1,'body':'{}','assets':[]}

    def test_growth_tags_are_opt_in_and_keep_tracking(self):
        item={'title':'Quiz','caption':'Illustrative example', 'creative_version':'creative-v2', 'growth_hashtags':'#UnitPrice #SouthAfrica'}
        text=c.caption(item,'youtube','20261115-early')
        self.assertIn('#UnitPrice #SouthAfrica #Shorts',text)
        self.assertIn('utm_content=20261115-early',text)
        self.assertIn('AI narration and illustrative AI product visuals.',text)

    def test_growth_test_stops_on_channel_identity_before_mutation(self):
        with patch.object(c,'buffer',return_value={'channels':[]}) as api, patch.object(c,'save') as save:
            with self.assertRaisesRegex(AssertionError,'identity'):
                c.apply_growth_test(self.now)
            self.assertEqual(api.call_count,1)
            save.assert_not_called()

    def test_growth_test_replaces_six_posts_preserving_schedule_and_backups(self):
        from types import SimpleNamespace
        now=dt.datetime(2026,11,14,10,tzinfo=c.SAST)
        releases={}; posts=[]; saved={}
        for tag, due in [('20261115-early','2026-11-15T06:00:00Z'),('20261115-am','2026-11-15T10:30:00Z')]:
            group={}
            for service,channel in c.CHANNELS.items():
                post={'id':tag+service,'channelId':channel,'status':'scheduled','dueAt':due,'text':'old','assets':[{'source':'old-url'}]}
                group[service]=post.copy(); posts.append(post.copy())
            ledger={'content':{'title':'old'},'posts':group,'video':'old-video'}
            releases[tag]={'id':tag,'body':json.dumps(ledger)}
        def api(query, variables=None):
            if 'channels(input' in query: return {'channels':self.channels}
            inp=variables['input']; before=next(p for p in posts if p['id']==inp['id'])
            after={**before,'text':inp['text'],'assets':[{'source':inp['assets'][0]['video']['url']}]}
            return {'editPost':{'post':after}}
        def save(release,ledger): saved[release['id']]=json.loads(json.dumps(ledger))
        def sha(data):
            return SimpleNamespace(hexdigest=lambda: '79a7468cc1204996ef1de8d70c6c1018401e005408821d2f17bae59efe0e5262' if data.endswith(b'quiz') else '0e16deb09b9d77b833f25b080bc2b3ce4d5f756868b81526a2f831e07072c4e5')
        with patch.object(c,'buffer',side_effect=api), patch.object(c,'existing_posts',return_value=posts), patch.object(c,'read_release',side_effect=lambda tag: releases[tag]), patch.object(c,'save',side_effect=save), patch.object(c,'request',side_effect=lambda url: b'1234ftyp'+(b'quiz' if url.endswith('quiz.mp4') else b'delivery')), patch('hashlib.sha256',side_effect=sha):
            c.apply_growth_test(now)
        self.assertEqual(len(saved),2)
        for ledger in saved.values():
            self.assertNotIn('growth_test_pending',ledger)
            self.assertEqual(ledger['growth_original']['content']['title'],'old')
            self.assertTrue(all(p['text']=='old' for p in ledger['growth_original']['posts'].values()))
            self.assertTrue(all(p['status']=='scheduled' and p['text']!='old' for p in ledger['posts'].values()))

    def test_outside_date_and_late_slot_never_calls_services(self):
        with patch.object(c,'buffer') as api:
            with self.assertRaises(AssertionError):
                c.run(c.START-dt.timedelta(days=1),'am',now=self.now)
            with self.assertRaises(RuntimeError):
                c.run(c.START,'am',now=self.now.replace(hour=13))
            api.assert_not_called()

    def test_uncertain_send_does_not_repeat_mutation(self):
        self.release['body']=json.dumps({'video':'https://example.com/public.mp4','pending_service':'youtube'})
        with patch.object(c,'buffer',return_value={'channels':self.channels}) as api, patch.object(c,'existing_posts',return_value=[]), patch.object(c,'load_release',return_value=self.release):
            with self.assertRaisesRegex(RuntimeError,'uncertain'):
                c.run(c.START,'am',now=self.now)
            self.assertEqual(api.call_count,1)

    def test_reconciles_both_posts_without_creating_duplicates(self):
        self.release['body']=json.dumps({'video':'https://example.com/public.mp4'})
        item=json.loads(c.Path(c.__file__).with_name('content.json').read_text())[0]
        posts=[{'id':s,'channelId':i,'status':'scheduled','text':c.caption(item,s,'20261108-am')} for s,i in c.CHANNELS.items()]
        with patch.object(c,'buffer',return_value={'channels':self.channels}) as api, patch.object(c,'existing_posts',return_value=posts), patch.object(c,'load_release',return_value=self.release), patch.object(c,'save') as save:
            c.run(c.START,'am',now=self.now)
            self.assertEqual(api.call_count,1)
            self.assertEqual(save.call_args[0][1]['state'],'scheduled')

    def test_render_attempt_without_asset_cannot_use_more_quota(self):
        with self.assertRaisesRegex(RuntimeError,'Previous render'):
            c.generate({},self.release,{'render_attempted':True})

    def test_changed_channel_identity_fails_before_mutations(self):
        with patch.object(c,'buffer',return_value={'channels':[]}), patch.object(c,'load_release') as release:
            with self.assertRaises(AssertionError):
                c.run(c.START,'am',now=self.now)
            release.assert_not_called()

    def test_third_slot_keeps_all_previously_planned_items_stable(self):
        original=json.loads(c.Path(c.__file__).with_name('content.json').read_text())
        seen=[]
        for offset in range(30):
            day=c.START+dt.timedelta(days=offset)
            self.assertEqual(c.campaign_item(day,'am'),original[offset*2])
            self.assertEqual(c.campaign_item(day,'pm'),original[offset*2+1])
            for slot in c.SLOTS:
                seen.append(c.campaign_item(day,slot)['title'])
        self.assertEqual(len(set(seen)),90)

    def test_actual_cloud_trigger_times_select_correct_sast_slot(self):
        for hour,minute,slot in [(6,53,'early'),(11,23,'am'),(17,23,'pm')]:
            now=self.now.replace(hour=hour,minute=minute)
            selected=c.scheduled_slot(now)
            self.assertEqual(selected,slot)
            self.assertGreater(dt.datetime.combine(now.date(),c.SLOTS[selected],c.SAST),now)

    def test_wrong_facebook_page_blocks_all_publishing(self):
        self.channels[-1]['serviceId']='wrong-page'
        with patch.object(c,'buffer',return_value={'channels':self.channels}), patch.object(c,'load_release') as release:
            with self.assertRaisesRegex(AssertionError,'Facebook Page identity'):
                c.run(c.START,'am',now=self.now)
            release.assert_not_called()

    def test_future_plans_have_full_unique_coverage_without_recycling_originals(self):
        originals = [json.loads(c.Path(c.__file__).with_name(name).read_text())
                     for name in ('content.json', 'content-third.json')]
        previous = {x['script'] for group in originals for x in group}
        for month, days in [('2026-12',31), ('2027-01',31), ('2027-02',28), ('2028-02',29)]:
            plan = validate_plan(build_month(month, ['unit-price'], previous), month)
            scripts = {x['script'] for x in plan['items']}
            self.assertEqual(len(scripts), days * 3)
            self.assertFalse(scripts & previous)
            self.assertEqual(len({x['title'] for x in plan['items']}), days * 3)
            for day in range(1, days + 1):
                slots = [x['slot'] for x in plan['items'] if x['date'] == f'{month}-{day:02d}']
                self.assertEqual(set(slots), set(c.SLOTS))
            previous.update(scripts)

    def test_next_year_uses_saved_plan_and_missing_plan_stops_before_services(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(c, 'ROOT', Path(directory)):
            day = dt.date(2027, 1, 15)
            with patch.object(c, 'buffer') as api:
                with self.assertRaisesRegex(AssertionError, 'Monthly content plan missing'):
                    c.run(day, 'am', now=dt.datetime(2027,1,15,11,tzinfo=c.SAST))
                api.assert_not_called()
            path = c.ROOT / 'plans'; path.mkdir()
            plan = build_month('2027-01')
            (path/'2027-01.json').write_text(json.dumps(plan))
            item = c.campaign_item(day, 'am')
            self.assertEqual(item['date'], '2027-01-15')
            self.assertIn('utm_campaign=evergreen_shopping_tips', c.caption(item,'youtube','20270115-am'))

    def test_reconciliation_filters_recent_history_at_api_not_by_total_account_age(self):
        response = {'posts': {'edges': [], 'pageInfo': {'hasNextPage': False}}}
        now = dt.datetime(2028,1,15,11,tzinfo=c.SAST)
        with patch.object(c, 'buffer', return_value=response) as api:
            self.assertEqual(c.existing_posts(now=now), [])
            inp = api.call_args[0][1]['input']
            self.assertEqual(inp['filter']['dueAt']['start'], '2028-01-07T22:00:00+00:00')
            self.assertEqual(inp['filter']['channelIds'], list(c.CHANNELS.values()))

    def test_preflight_is_safe_even_after_last_daily_slot(self):
        with patch.object(c,'buffer',return_value={'channels':self.channels}), \
                patch.object(c,'existing_posts',return_value=[]), patch.object(c,'load_release') as release:
            c.run(c.START,'pm',now=self.now.replace(hour=23),preflight=True)
            release.assert_not_called()

    def test_review_unavailable_metrics_does_not_invent_scores_or_policy(self):
        with patch.object(c,'existing_posts',side_effect=RuntimeError('Unavailable')), \
                patch.object(c,'write_public_json') as write:
            c.review()
            self.assertEqual(write.call_count,1)
            report=write.call_args[0][1]
            self.assertEqual(report['status'],'metrics_unavailable')
            self.assertEqual(report['preferred_themes'],[])

    def test_weekly_review_publishes_content_choices_without_raw_metrics(self):
        now=dt.datetime.now(c.SAST)
        posts=[{'id':str(i),'channelId':c.CHANNELS['youtube'],'status':'sent',
            'dueAt':(now-dt.timedelta(days=3)).isoformat(),
            'text':'Unit price check\nutm_campaign=evergreen_shopping_tips',
            'externalLink':'https://www.youtube.com/shorts/example'+str(i),
            'metricsUpdatedAt':now.isoformat(),
            'metrics':[{'type':'views','value':100+i,'unit':'count'}]} for i in range(3)]
        with patch.object(c,'existing_posts',return_value=posts), patch.object(c,'write_public_json') as write:
            c.review()
            report=write.call_args_list[0][0][1]
            self.assertEqual(report['status'],'signals_available')
            self.assertEqual(report['preferred_themes'],['unit-price'])
            self.assertNotIn('metrics',report)
            self.assertNotIn('value',json.dumps(report))
            self.assertEqual(write.call_count,2)
        for post in posts:
            post['metricsUpdatedAt']=(now-dt.timedelta(days=4)).isoformat()
        with patch.object(c,'existing_posts',return_value=posts), patch.object(c,'write_public_json') as write:
            c.review()
            self.assertEqual(write.call_count,1)
            self.assertEqual(write.call_args[0][1]['status'],'insufficient_data')

    def test_rolling_audit_does_not_require_old_buffer_history(self):
        real_datetime = dt.datetime
        now = real_datetime(2027,1,15,20,tzinfo=c.SAST)
        class Frozen(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return now
        posts=[]
        for offset in range(7):
            day=now.date()-dt.timedelta(days=offset)
            for slot in c.SLOTS:
                tag=day.strftime('%Y%m%d')+'-'+slot
                for service,channel in c.CHANNELS.items():
                    posts.append({'channelId':channel,'status':'sent',
                        'text':'utm_campaign=evergreen_shopping_tips\nutm_content='+tag+'\n'})
        with tempfile.TemporaryDirectory() as directory, patch.object(c.dt,'datetime',Frozen), \
                patch.object(c,'existing_posts',return_value=posts), patch.object(c,'publish_response_evidence'), patch.object(c,'Path') as path:
            c.audit()
            self.assertEqual(len(posts),63)
            with patch.object(c,'existing_posts',return_value=posts[:-1]):
                with self.assertRaisesRegex(RuntimeError,'publishing failure'):
                    c.audit()

    def test_retry_uses_frozen_content_instead_of_new_wording(self):
        old=c.campaign_item(c.START,'am')
        self.release['body']=json.dumps({'video':'https://example.com/public.mp4','content':old})
        posts=[{'id':s,'channelId':i,'status':'scheduled','text':c.caption(old,s,'20261108-am')}
               for s,i in c.CHANNELS.items()]
        with patch.object(c,'campaign_item',return_value={**old,'caption':'Changed later'}), \
                patch.object(c,'buffer',return_value={'channels':self.channels}) as api, \
                patch.object(c,'existing_posts',return_value=posts), \
                patch.object(c,'load_release',return_value=self.release),patch.object(c,'save'):
            c.run(c.START,'am',now=self.now)
            self.assertEqual(api.call_count,1)

    def test_delayed_trigger_prepares_future_slots_without_catchup(self):
        now=dt.datetime(2026,11,8,10,30,tzinfo=c.SAST)
        future=list(c.future_slots(now))
        self.assertEqual(future[0],(dt.date(2026,11,8),'am'))
        self.assertNotIn((dt.date(2026,11,8),'early'),future)
        for day,slot in future:
            due=dt.datetime.combine(day,c.SLOTS[slot],c.SAST)
            self.assertGreaterEqual(due,now+dt.timedelta(hours=2))
            self.assertLessEqual(due,now+dt.timedelta(hours=48))

    def test_ahead_preparation_skips_already_queued_slot(self):
        now=dt.datetime(2026,11,8,10,tzinfo=c.SAST)
        item=c.campaign_item(c.START,'am')
        posts=[{'id':s,'channelId':i,'status':'scheduled',
                'text':c.caption(item,s,'20261108-am')} for s,i in c.CHANNELS.items()]
        with patch.object(c,'existing_posts',return_value=posts), \
                patch.object(c,'render_budget',return_value=[]), \
                patch.object(c,'read_release',return_value=None),patch.object(c,'run') as run:
            self.assertTrue(c.prepare_ahead(now))
            self.assertEqual(run.call_args[0],(c.START,'pm'))

    def test_daily_budget_blocks_extra_render_but_allows_existing_video_to_schedule(self):
        now=dt.datetime(2026,11,8,10,tzinfo=c.SAST)
        with patch.object(c,'existing_posts',return_value=[]), \
                patch.object(c,'render_budget',return_value=['a','b','c']), \
                patch.object(c,'read_release',return_value=None),patch.object(c,'run') as run:
            self.assertFalse(c.prepare_ahead(now))
            run.assert_not_called()
        with patch.object(c,'existing_posts',return_value=[]), \
                patch.object(c,'render_budget',return_value=['a','b','c']), \
                patch.object(c,'read_release',return_value={'body':json.dumps({'video':'public.mp4'}),'assets':[]}), \
                patch.object(c,'run') as run:
            self.assertTrue(c.prepare_ahead(now))
            run.assert_called_once()

    def test_reservation_is_persistent_and_never_exceeds_three(self):
        now=dt.datetime(2026,11,8,10,tzinfo=c.SAST)
        release={'body':json.dumps({'slots':['one','two','three']})}
        with patch.object(c,'load_release',return_value=release),patch.object(c,'save') as save:
            with self.assertRaisesRegex(RuntimeError,'three-render budget'):
                c.reserve_render('four',now)
            c.reserve_render('two',now)
            save.assert_not_called()

    def test_blocked_or_unknown_send_is_not_retried_by_ahead_preparer(self):
        now=dt.datetime(2026,11,8,10,tzinfo=c.SAST)
        for ledger in ({'pending_service':'youtube'}, {'render_attempted':True}):
            with patch.object(c,'existing_posts',return_value=[]), \
                    patch.object(c,'render_budget',return_value=[]), \
                    patch.object(c,'read_release',return_value={'body':json.dumps(ledger),'assets':[]}), \
                    patch.object(c,'run') as run:
                self.assertFalse(c.prepare_ahead(now))
                run.assert_not_called()


if __name__=='__main__':
    unittest.main()


class MediaDeliverySafety(unittest.TestCase):
    def test_cache_never_accepts_document_or_arbitrary_path(self):
        import media_delivery as m
        from unittest.mock import Mock
        gh = Mock()
        with self.assertRaises(ValueError):
            m.publish('COR14.3.pdf', 'private', gh=gh, request=Mock(), repo=c.REPO, now=dt.datetime.now(c.SAST))
        gh.assert_not_called()

    def test_cache_retention_excludes_private_paths_and_keeps_future_video(self):
        import media_delivery as m
        entries = [{'type':'blob','path':p} for p in ['20261109-am.mp4','20261001-pm.mp4','TaxNumber.pdf','main.py','20261108-../../secret.mp4']]
        self.assertEqual([e['path'] for e in m.retained(entries, dt.datetime(2026,11,8))], ['20261109-am.mp4'])

    def test_existing_cached_video_never_reuploads_or_rewrites_any_ref(self):
        import media_delivery as m
        from unittest.mock import Mock
        gh = Mock(side_effect=[{'object':{'sha':'commit'}},{'tree':{'sha':'tree'}}, {'tree':[{'path':'20261109-am.mp4','mode':'100644','type':'blob','sha':'blob'}]}])
        request=Mock(return_value=b'0000ftyprest')
        url=m.publish('20261109-am','https://github.com/'+c.REPO+'/releases/download/20261109-am/video.mp4',gh=gh,request=request,repo=c.REPO,now=dt.datetime(2026,11,8))
        self.assertTrue(url.endswith('/public-video-cache/20261109-am.mp4'))
        self.assertTrue(all(len(call.args)==1 for call in gh.call_args_list))

    def test_refresh_edits_media_on_same_scheduled_post_and_preserves_content(self):
        now=dt.datetime(2026,11,8,12,40,tzinfo=c.SAST)
        before={'id':'same','channelId':c.CHANNELS['tiktok'],'status':'scheduled','text':'utm_campaign=30_day_shopping_tips','dueAt':'2026-11-08T16:30:00Z'}
        release={'body':json.dumps({'video':'release-url','posts':{'tiktok':before}})}
        with patch.object(c,'existing_posts',return_value=[before]), patch.object(c,'future_slots',return_value=[(c.START,'pm')]), patch.object(c,'read_release',return_value=release), patch.object(c,'delivery_url',return_value='https://public/video.mp4'), patch.object(c,'buffer',return_value={'editPost':{'post':before}}) as api, patch.object(c,'save'):
            c.refresh_media(now)
        payload=api.call_args.args[1]['input']
        self.assertEqual(payload,{'id':'same','assets':[{'video':{'url':'https://public/video.mp4'}}], 'metadata': {'tiktok': {'isAiGenerated': True}}})
        self.assertNotIn('createPost',api.call_args.args[0])

class NativeLinkEvidenceTests(unittest.TestCase):
 def test_link_hosts_and_owned_tiktok_are_strict(self):
  self.assertEqual(c.public_post_link('youtube','https://www.youtube.com/shorts/6EsKNU-E2CQ?feature=share'),'https://www.youtube.com/shorts/6EsKNU-E2CQ')
  self.assertEqual(c.public_post_link('tiktok','https://tiktok.com/@cwhereucheaper.co/video/12345'),'https://www.tiktok.com/@cwhereucheaper.co/video/12345')
  self.assertEqual(c.public_post_link('facebook','https://www.facebook.com/reel/12345/'),'https://www.facebook.com/reel/12345/')
  for url in ('https://evil.example/reel/12345','http://facebook.com/reel/12345/','https://user:pass@facebook.com/reel/12345/'):
   self.assertEqual(c.public_post_link('facebook',url),'')
  self.assertEqual(c.public_post_link('tiktok','https://tiktok.com/@other/video/12345'),'')

class ResponseEvidenceTests(unittest.TestCase):
 def test_only_exact_recorded_post_ids_produce_public_evidence(self):
  now=dt.datetime(2026,11,14,14,0,tzinfo=c.SAST)
  tag='20261114-am';ids={s:'id-'+s for s in c.CHANNELS}
  ledger={'response_request_id':'a'*32,'content':{'synthetic_test':True},'posts':{s:{'id':ids[s]} for s in ids}}
  posts=[{'id':ids['youtube'],'channelId':c.CHANNELS['youtube'],'status':'sent','externalLink':'https://www.youtube.com/shorts/6EsKNU-E2CQ'},
         {'id':'different','channelId':c.CHANNELS['tiktok'],'status':'sent','externalLink':'https://www.tiktok.com/@cwhereucheaper.co/video/123'},
         {'id':ids['facebook'],'channelId':c.CHANNELS['facebook'],'status':'sending','externalLink':'https://www.facebook.com/reel/123/'}]
  def read(name):return {'id':1,'body':json.dumps(ledger)} if name==tag else None
  with patch.object(c,'read_release',side_effect=read),patch.object(c,'load_release',return_value={'id':2,'body':'{}'}),patch.object(c,'save') as save:
   c.publish_response_evidence(now,posts)
  evidence=save.call_args.args[1]
  self.assertEqual(evidence['posts']['youtube']['status'],'sent')
  self.assertEqual(evidence['posts']['tiktok'],{'status':'unknown','url':''})
  self.assertEqual(evidence['posts']['facebook'],{'status':'sending','url':''})
  self.assertTrue(evidence['synthetic'])
