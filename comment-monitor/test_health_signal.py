import datetime as dt,json,tempfile,unittest
from pathlib import Path
import health_signal as h
NOW=dt.datetime(2026,11,14,12,0,tzinfo=dt.timezone.utc)
class HealthSignalTests(unittest.TestCase):
 def test_only_coarse_flags_are_sent_and_repeats_are_throttled(self):
  flags={'sources':'available','unhandled':'none','stalled':'none','processing':'ok'};calls=[]
  def send(url,payload):calls.append(payload);return 204
  with tempfile.TemporaryDirectory() as d:
   self.assertTrue(h.emit('selector',flags,d,'dummy',send,NOW))
   self.assertFalse(h.emit('selector',flags,d,'dummy',send,NOW+dt.timedelta(hours=1)))
   self.assertTrue(h.emit('selector',dict(flags,unhandled='present'),d,'dummy',send,NOW+dt.timedelta(hours=2)))
   self.assertEqual(len(calls),2);self.assertNotIn('comment',json.dumps(calls))
   self.assertEqual((Path(d)/'health-selector.json').stat().st_mode & 0o777,0o600)
 def test_unexpected_payload_cannot_leak(self):
  with self.assertRaises(ValueError):h.validate('selector',{'comment':'private text'})
  with self.assertRaises(ValueError):h.validate('native',{'slot':'https://bad','youtube':'none','tiktok':'none','facebook':'none'})
 def test_failed_dispatch_does_not_mark_sent(self):
  flags={'sources':'attention','unhandled':'unknown','stalled':'none','processing':'attention'}
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RuntimeError):h.emit('selector',flags,d,'dummy',lambda *a:500,NOW)
   self.assertFalse((Path(d)/'health-selector.json').exists())
if __name__=='__main__':unittest.main()
