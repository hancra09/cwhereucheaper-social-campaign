"""Buffer's per-day channel cap must not freeze a slot (incident of 22-24 Nov 2026)."""

import datetime as dt
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import campaign as c

LIMIT = ('You have already scheduled the maximum number of posts YouTube allows in a day (2). '
         'Please consider scheduling this post for another day.')


class DailyLimit(unittest.TestCase):
    def test_youtube_skips_the_early_slot_from_the_cutover(self):
        before = (c.YOUTUBE_TWO_A_DAY_FROM - dt.timedelta(days=1)).strftime('%Y%m%d')
        after = c.YOUTUBE_TWO_A_DAY_FROM.strftime('%Y%m%d')
        self.assertIn('youtube', c.slot_channels(before + '-early'))
        self.assertEqual(set(c.slot_channels(after + '-early')), {'tiktok', 'facebook'})
        for slot in ('am', 'pm'):
            self.assertEqual(set(c.slot_channels(after + '-' + slot)), set(c.CHANNELS))
        self.assertEqual(c.slot_channels('viewer-request-x'), dict(c.CHANNELS))

    def test_only_a_recorded_daily_cap_refusal_counts(self):
        self.assertTrue(c.daily_limit_refused({'refused': {'youtube': LIMIT}}, 'youtube'))
        self.assertTrue(c.daily_limit_refused(
            {'refused': {'youtube': 'The daily posting limit for this channel has been reached!'}}, 'youtube'))
        self.assertFalse(c.daily_limit_refused({'refused': {'youtube': 'Invalid video'}}, 'youtube'))
        self.assertFalse(c.daily_limit_refused({'pending_service': 'youtube'}, 'youtube'))

    def test_audit_accepts_a_recorded_daily_cap_refusal_but_nothing_else(self):
        now = dt.datetime.now(c.SAST)
        cutoff = now - dt.timedelta(minutes=15)
        day = max(c.START, cutoff.date() - dt.timedelta(days=c.AUDIT_DAYS - 1))
        posts, tags = [], []
        while day <= cutoff.date():
            for slot, when in c.SLOTS.items():
                if dt.datetime.combine(day, when, c.SAST) > cutoff:
                    continue
                tag = day.strftime('%Y%m%d') + '-' + slot
                tags.append(tag)
                for service, channel in c.slot_channels(tag).items():
                    posts.append({'id': tag + service, 'channelId': channel, 'status': 'sent',
                                  'text': 'x\nutm_content=' + tag + '\nAI'})
            day += dt.timedelta(days=1)
        gap = tags[-1]
        posts = [p for p in posts if p['id'] != gap + 'youtube']

        def run(ledger):
            release = {'body': json.dumps(ledger)}
            with tempfile.TemporaryDirectory() as tmp, patch.object(c, 'existing_posts', return_value=posts), \
                    patch.object(c, 'campaign_posts', side_effect=lambda p: p), \
                    patch.object(c, 'publish_response_evidence'), \
                    patch.object(c, 'read_release', return_value=release):
                cwd = os.getcwd()
                os.chdir(tmp)
                try:
                    c.audit()
                finally:
                    os.chdir(cwd)

        if 'youtube' in c.slot_channels(gap):
            run({'refused': {'youtube': LIMIT}})  # accepted
            with self.assertRaisesRegex(RuntimeError, 'Expected one sent post'):
                run({'pending_service': 'youtube'})


if __name__ == '__main__':
    unittest.main()


class Reconcile(unittest.TestCase):
    def test_youtube_day_full_counts_only_other_live_youtube_posts_that_day(self):
        day = dt.date(2026, 11, 25)
        yt, tt = c.CHANNELS['youtube'], c.CHANNELS['tiktok']
        posts = [
            {'channelId': yt, 'status': 'scheduled', 'dueAt': '2026-11-25T06:00:00.000Z', 'text': 'a\nutm_content=20261125-early\n'},
            {'channelId': yt, 'status': 'scheduled', 'dueAt': '2026-11-25T10:30:00.000Z', 'text': 'b\nutm_content=20261125-am\n'},
            {'channelId': tt, 'status': 'scheduled', 'dueAt': '2026-11-25T16:30:00.000Z', 'text': 'c\nutm_content=20261125-pm\n'},
        ]
        self.assertTrue(c.youtube_day_full(posts, day, '20261125-pm'))
        self.assertFalse(c.youtube_day_full(posts[:1], day, '20261125-pm'))
        posts[1]['status'] = 'error'
        self.assertFalse(c.youtube_day_full(posts, day, '20261125-pm'))
        # 22:30 UTC on the 24th is already the 25th in SAST
        late = [{'channelId': yt, 'status': 'sent', 'dueAt': '2026-11-24T22:30:00Z', 'text': 'x'}] * 2
        self.assertTrue(c.youtube_day_full(late, day, '20261125-pm'))
