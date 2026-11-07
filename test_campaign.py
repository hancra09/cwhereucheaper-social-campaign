import datetime as dt
import json
import unittest
from unittest.mock import patch
import campaign as c


class CampaignSafety(unittest.TestCase):
    def setUp(self):
        self.channels = [{'service':s,'id':i} for s,i in c.CHANNELS.items()]
        self.now = dt.datetime(2026,11,8,11,23,tzinfo=c.SAST)
        self.release = {'id':1,'body':'{}','assets':[]}

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


if __name__=='__main__':
    unittest.main()
