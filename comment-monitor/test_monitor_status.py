import datetime as dt,json,unittest
import monitor_status as m
NOW=dt.datetime(2026,11,14,12,0,tzinfo=dt.timezone.utc)
SEL={'sources':'available','unhandled':'none','stalled':'none','processing':'ok'}
class MonitorStatusTests(unittest.TestCase):
 def test_renders_only_coarse_states_in_sast(self):
  calls=[]
  def api(path,token,body=None,method=None):
   calls.append((path,body,method))
   if path.startswith('releases/tags/'):
    import urllib.error
    raise urllib.error.HTTPError('https://example.invalid',404,'missing',{},None)
   return {'id':1}
  self.assertTrue(m.update('selector',SEL,NOW.isoformat(),'dummy',api,NOW))
  content=calls[-1][1]['body'];self.assertIn('2026-11-14T14:00:00+02:00',content)
  self.assertIn('viewer comments',content.lower());self.assertNotIn('count:',content)
  self.assertEqual(m.decode(content)['selector']['flags'],SEL)
 def test_bad_input_and_unexpected_existing_content_rejected(self):
  with self.assertRaises(ValueError):m.update('selector',dict(SEL,comment='secret'),NOW.isoformat(),'dummy',lambda *a:None,NOW)
  with self.assertRaises(ValueError):m.decode('unexpected public text')
 def test_old_arrival_cannot_replace_new_state(self):
  recent={'selector':{'flags':SEL,'checked_at_sast':'2026-11-14T14:30:00+02:00'}}
  calls=[]
  def api(path,token,body=None,method=None):calls.append(path);return {'id':1,'body':m.render(recent)}
  self.assertFalse(m.update('selector',SEL,NOW.isoformat(),'dummy',api,NOW));self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main()

class NativeStatusTests(unittest.TestCase):
 def test_platform_scope_is_explained_and_selector_state_preserved(self):
  native={'slot':'20261114-am','youtube':'public_confirmed','tiktok':'found_owned','facebook':'unknown'}
  initial={'selector':{'flags':SEL,'checked_at_sast':'2026-11-14T13:30:00+02:00'}};calls=[]
  def api(path,token,body=None,method=None):
   calls.append((path,body,method))
   if path.startswith('releases/tags/'):return {'id':1,'body':m.render(initial)}
   return {'id':1}
  self.assertTrue(m.update('native',native,NOW.isoformat(),'dummy',api,NOW))
  body=calls[-1][1]['body'];state=m.decode(body)
  self.assertIn('public confirmed',body);self.assertIn('found in account',body)
  self.assertIn('does not confirm',body);self.assertEqual(state['selector']['flags'],SEL)
  self.assertIn('response-native-20261114-am',body)
