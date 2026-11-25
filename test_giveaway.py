"""January Pro draw episodes (Owner request, 24 Nov 2026)."""

import datetime as dt
import re
import unittest

import campaign as c
import entertainment as e


class Giveaway(unittest.TestCase):
    def setUp(self):
        # These tests cover the draw while its rules page is public; no network in tests.
        from unittest.mock import patch
        patcher = patch.object(c, 'giveaway_rules_live', return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_only_the_evening_slot_from_26_november_to_31_december(self):
        self.assertFalse(c.is_giveaway_slot(dt.date(2026, 11, 25), 'pm'))
        self.assertTrue(c.is_giveaway_slot(dt.date(2026, 11, 26), 'pm'))
        self.assertTrue(c.is_giveaway_slot(dt.date(2026, 12, 31), 'pm'))
        self.assertFalse(c.is_giveaway_slot(dt.date(2027, 1, 1), 'pm'))
        for slot in ('early', 'am'):
            self.assertFalse(c.is_giveaway_slot(dt.date(2026, 12, 10), slot))
        self.assertTrue(c.scheduled_item(dt.date(2026, 12, 10), 'pm').get('giveaway'))
        self.assertFalse(c.scheduled_item(dt.date(2026, 12, 10), 'am').get('giveaway'))

    def test_every_caption_carries_the_cpa_offer_and_platform_lines(self):
        day = e.GIVEAWAY_FROM
        while day <= e.GIVEAWAY_TO:
            item = c.scheduled_item(day, 'pm')
            tag = day.strftime('%Y%m%d') + '-pm'
            for service in c.CHANNELS:
                text = c.caption(item, service, tag)
                for phrase in ('Create and verify a free CWhereUCheaper account by 31 December 2026',  # how to enter, closing date
                               '10 winners at random',  # how results are determined
                               'CWUC Pro for January 2027, free and worth R99',  # benefit
                               'Winners are told by email by 5 January 2027',  # how results are announced
                               'Rules: https://www.cwhereucheaper.co.za/pro/january-draw',  # where the rules are
                               'No purchase needed', 'Not sponsored or run by Facebook, TikTok or YouTube',
                               '#JanuarySavings', 'AI narration'):
                    self.assertIn(phrase, text, (tag, service, phrase))
                self.assertIn('utm_content=' + tag + '\n', text)  # audit matching
                self.assertLessEqual(len(text), 2200)  # TikTok caption limit
            self.assertLessEqual(len(item['title'] + ' #Shorts'), 100)  # YouTube title limit
            day += dt.timedelta(days=1)

    def test_scripts_stay_short_enough_to_narrate_in_time(self):
        for title, _fmt, _asset, beats in (*e.GIVEAWAY_VERSIONS, e.GIVEAWAY_FINAL_WEEK, e.GIVEAWAY_LAST_DAY):
            words = sum(len(line.split()) for _, line in beats) + len(e.GIVEAWAY_CTA[1].split())
            self.assertLessEqual(words, 42, title)
            spoken = ' '.join(line for _, line in beats)
            self.assertRegex(spoken, r'R99', title)  # every version states the prize value
            self.assertRegex(spoken.lower(), r'random', title)
            self.assertTrue(re.search(r'thirty-first of december|today|midnight', spoken.lower()), title)

    def test_neighbouring_slots_never_repeat_a_title_or_hook(self):
        day, previous = e.GIVEAWAY_FROM, None
        while day <= e.GIVEAWAY_TO:
            current = e.fingerprint(c.scheduled_item(day, 'pm'))
            if previous:
                self.assertNotEqual(current[0], previous[0])
                self.assertNotEqual(current[1], previous[1]) if day.day != 31 else None
            previous = current
            day += dt.timedelta(days=1)

    def test_end_card_and_cutaways_render_without_overflow(self):
        import creative_engine as ce
        from PIL import Image, ImageDraw, ImageFont
        ce.Image, ce.ImageDraw, ce.ImageFont = Image, ImageDraw, ImageFont
        for day in (e.GIVEAWAY_FROM + dt.timedelta(days=i) for i in range(len(e.GIVEAWAY_VERSIONS))):
            item = e.giveaway_item(day, 'pm')
            ce.CFG = {**item, 'segments': [line for _, line in item['beats']]}
            ce.NARRATION = {'cuts': [0, 3, 6, 9, 12, 15], 'duration': 15}
            ce.TOTAL = 15
            ce.pair = Image.open(ce.ASSETS / item['asset']).convert('RGB')
            ce.left = ce.right = ce.pair
            ce.web = Image.open(ce.ASSETS / 'website.png').convert('RGB')
            for t in (1, 4, 7, 10, 13):
                self.assertEqual(ce.render_episode(t).size, (1080, 1920))


if __name__ == '__main__':
    unittest.main()


class RulesGate(unittest.TestCase):
    def test_giveaway_post_is_held_before_any_render_while_rules_are_offline(self):
        from unittest.mock import patch
        with patch.object(c, 'giveaway_rules_live', return_value=False), \
                patch.object(c, 'buffer') as api, patch.object(c, 'load_release') as release:
            with self.assertRaisesRegex(RuntimeError, 'rules page is not live'):
                c.run(dt.date(2026, 12, 10), 'pm', now=dt.datetime(2026, 12, 9, 9, tzinfo=c.SAST),
                      request_item=e.giveaway_item(dt.date(2026, 12, 10), 'pm'))
            api.assert_not_called()
            release.assert_not_called()

    def test_held_draw_slot_falls_back_to_a_normal_tip_instead_of_blocking(self):
        from unittest.mock import patch
        day = dt.date(2026, 12, 10)
        with patch.object(c, 'giveaway_rules_live', return_value=False):
            item = c.scheduled_item(day, 'pm')
        self.assertFalse(item.get('giveaway'))
        self.assertEqual(item['creative_version'], e.VERSION)
        with patch.object(c, 'giveaway_rules_live', return_value=True):
            self.assertTrue(c.scheduled_item(day, 'pm').get('giveaway'))

    def test_collapsed_tiktok_caption_still_matches_its_slot(self):
        text = 'Title Body https://x/?utm_content=20261121-am AI narration #SouthAfrica'
        self.assertTrue(c.has_tag(text, '20261121-am'))
        self.assertTrue(c.has_tag('a\nutm_content=20261121-am\nb', '20261121-am'))
        self.assertFalse(c.has_tag(text.replace('-am', '-amx'), '20261121-am'))
        self.assertFalse(c.has_tag(text, '20261121-a'))

    def test_rules_check_needs_the_real_page(self):
        from unittest.mock import patch
        with patch.object(c, 'request', return_value=b'<h1>January Pro draw</h1> closes 31 December 2026'):
            self.assertTrue(c.giveaway_rules_live())
        with patch.object(c, 'request', return_value=b'Not found'):
            self.assertFalse(c.giveaway_rules_live())
        with patch.object(c, 'request', side_effect=OSError('down')):
            self.assertFalse(c.giveaway_rules_live())
