"""Record a real CWhereUCheaper search for the creative-v5 bridge beat (Owner request,
25 November 2026).

A headless phone-sized browser opens the live public site, types the query into the
search box, submits it and scrolls the results. Frames are saved as 1080x1920 JPEGs with
their capture times. Prices shown are the site's own live results with the site's own
"checked" times on screen; the renderer labels the footage as live prices with the
capture date. Any failure returns None so the renderer falls back to the homepage
capture. No sign-in, cookies or form other than the public search are used.
"""
import datetime as dt
import json
import re
import time
from pathlib import Path

SITE = 'https://www.cwhereucheaper.co.za/'
VIEW = {'width': 360, 'height': 640}
SCALE = 3
SAST = dt.timezone(dt.timedelta(hours=2))


def shops_in(text, top=6):
    found = re.findall(r' at ([A-Z][\w\.&\' ]+?) · checked', re.sub(r'\s+', ' ', text))
    return list(dict.fromkeys(found[:top]))


def capture(queries, out_dir, timeout_s=75):
    """Record the first query whose top results show at least two shops."""
    if isinstance(queries, str):
        queries = [queries]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('frame-*.jpg'):
        old.unlink()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    frames = []
    started = time.monotonic()

    def snap(page, hold=0.0):
        path = out / f'frame-{len(frames):03d}.jpg'
        page.screenshot(path=str(path), type='jpeg', quality=88)
        frames.append({'file': path.name, 'hold': hold})
        if time.monotonic() - started > timeout_s:
            raise TimeoutError('Site capture exceeded its time budget')

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport=VIEW, device_scale_factor=SCALE, is_mobile=True,
                                      has_touch=True, locale='en-ZA',
                                      user_agent=('Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
                                                  '(KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36 '
                                                  'CWUC-campaign-capture'))
            query = None
            for candidate in queries:
                html = ctx.request.get(SITE + 'search?q=' + candidate.replace(' ', '+'), timeout=20000).text()
                text = re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S))
                found = re.search(r'(\d+) of (\d+) matching prices', text)
                if found and int(found.group(1)) >= 3 and len(shops_in(text)) >= 2:
                    query = candidate
                    break
            if not query:
                browser.close()
                return None
            page = ctx.new_page()
            page.goto(SITE, wait_until='networkidle', timeout=30000)
            # Hide the mascot and its bubbles so they never cover the search box.
            page.add_style_tag(content='.pc,.pc-say,.pc-pop,.pc-menu,.pc-z{display:none!important}')
            box = page.locator('#q')
            box.scroll_into_view_if_needed()
            page.evaluate('window.scrollBy(0, -200)')
            snap(page, .5)
            box.click()
            for ch in query:
                box.type(ch)
                snap(page, .07)
            snap(page, .3)
            box.press('Enter')
            page.wait_for_load_state('networkidle', timeout=30000)
            body = page.inner_text('body')
            match = re.search(r'(\d+) of (\d+) matching prices', body)
            if not match or int(match.group(1)) < 3 or len(shops_in(body)) < 2:
                browser.close()
                return None
            snap(page, .6)
            for _ in range(22):
                page.mouse.wheel(0, 34)
                page.wait_for_timeout(30)
                snap(page, .06)
            snap(page, .5)
            browser.close()
    except Exception:
        return None
    manifest = {
        'query': query,
        'url': SITE + 'search?q=' + query.replace(' ', '+'),
        'captured_sast': dt.datetime.now(SAST).isoformat(timespec='minutes'),
        'matches': int(match.group(1)),
        'shops_shown': shops_in(body),
        'frames': frames,
    }
    (out / 'capture.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    import sys
    print(json.dumps(capture(sys.argv[1].split(','), sys.argv[2]), indent=2))
