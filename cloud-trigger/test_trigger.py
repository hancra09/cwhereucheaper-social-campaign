import datetime as dt
import unittest
import trigger

class TriggerSafety(unittest.TestCase):
    def test_modes_at_real_sast_times(self):
        for h,m,expected in [(6,20,'audit'),(10,50,'audit'),(16,50,'audit'),(17,10,'review'),(11,7,'prime')]:
            self.assertEqual(trigger.action(dt.datetime(2026,11,8,h,m,tzinfo=dt.timezone.utc)),expected)
    def test_review_is_sunday_only(self):
        self.assertEqual(trigger.action(dt.datetime(2026,11,9,17,10,tzinfo=dt.timezone.utc)), 'prime')
    def test_all_active_states_block_second_dispatch(self):
        for state in ['queued','in_progress','waiting','pending','requested']:
            self.assertTrue(trigger.running([{'status':state}]))
        self.assertFalse(trigger.running([{'status':'completed'}]))

    def test_audits_queue_even_when_preparation_is_running(self):
        runs=[{'status':'in_progress'}]
        self.assertTrue(trigger.defer(runs,'prime'))
        self.assertFalse(trigger.defer(runs,'audit'))
        self.assertFalse(trigger.defer(runs,'review'))

if __name__=='__main__':unittest.main()
