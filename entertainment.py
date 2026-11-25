"""Topic-specific CWUC stories with a shared site ending and rotating visuals."""
import re

VERSION = 'creative-v5'
FORMATS = (('receipt', 'receipt.jpg'), ('court', 'court.jpg'), ('pov', 'cupboard.jpg'))
CTA = ('FREE ACCOUNT · LINK IN BIO', 'Search it free on CWhereUCheaper.co.za. Link in bio.')
BRIDGE_LINE = 'Compare it across shops on CWhereUCheaper.co.za. Cheapest match first.'

# creative-v5 (25 November 2026, Owner request): every story is hook -> problem ->
# reveal -> CWUC bridge -> free-account CTA. Hooks talk to the viewer in under eight
# words. Bridge lines only describe features the free site offers (same product
# across shops, basket comparison, watching a basket). Illustrative scenarios, not
# current price, stock or retailer claims.
STORIES = {
    'Do the division before the decision': ('receipt', 'receipt.jpg', (
        ('6 FOR R54. DEAL?', 'Six for R54. Sounds like a deal, right?'),
        ('DO THE MATHS', 'R54 divided by six is R9 each.'),
        ('R9 vs R8', 'The single one is R8 in this example. That bundle just cost you more.'),
        ('SAME PRODUCT. SIDE BY SIDE.', 'CWhereUCheaper shows the same product across shops, side by side. Cheapest match first.'),
    )),
    'The R15 delivery difference': ('receipt', 'receipt.jpg', (
        ('R90 OR R100?', 'R90 or R100. Same item. Which one is cheaper?'),
        ('ADD DELIVERY', 'The R90 one adds R30 delivery. That is R120.'),
        ('R120 vs R105', 'The R100 one adds R5. R105. In this example, the pricier sticker wins.'),
        ('COMPARE SHOPS FIRST', 'Compare shops on CWhereUCheaper, then check the checkout total. Cheapest match first.'),
    )),
    'Cheaper per unit can still cost more today': ('court', 'pouches.png', (
        ('THE BIG BAG LIED', 'The big bag is cheaper per scoop. So why are you broke at the till?'),
        ('YOU PAY FOR ALL OF IT', 'Because you pay for the whole bag today, not one scoop.'),
        ('BUDGET FIRST', 'If it busts the budget or goes off, the small bag wins.'),
        ('SEE BOTH SIZES', 'Compare both sizes across shops on CWhereUCheaper. Cheapest match first.'),
    )),
    'Watch for a different product strength': ('pov', 'bottles.png', (
        ('LOOK IDENTICAL?', 'These two bottles look identical. They are not.'),
        ('FLIP IT OVER', 'One is concentrated. Check how many washes it says.'),
        ('COUNT THE WASHES', 'Same size bottle does not mean the same number of washes.'),
        ('COMPARE BEFORE YOU GO', 'Check prices for both on CWhereUCheaper before you leave home. Cheapest match first.'),
    )),
    'A bigger bottle may be different strength': ('pov', 'bottles.png', (
        ('BIGGER = CHEAPER?', 'Bigger bottle, better deal? Not so fast.'),
        ('READ THE BACK', 'Check how much each one says to use per wash.'),
        ('WASHES, NOT LITRES', 'Different strengths make size a bad shortcut.'),
        ('LINE THEM UP', 'Line them up across shops on CWhereUCheaper. Cheapest match first.'),
    )),
    'Choose a basket before choosing an offer': ('court', 'basket.png', (
        ('SPECIALS ARE COSTING YOU', 'You came for dinner. You left with five specials.'),
        ('LIST FIRST', 'Decide what you need before you look at promotions.'),
        ('3 BARGAINS = MORE SPEND', 'Three bargains you did not need still cost more.'),
        ('PRICE YOUR LIST', 'Build your basket on CWhereUCheaper and compare it across shops. Cheapest match first.'),
    )),
    'Before you tap reorder': ('pov', 'cupboard.jpg', (
        ("DON'T TAP REORDER", 'Wait. Do not tap reorder yet.'),
        ('CHECK THE CUPBOARD', 'Three packs of pasta already in the cupboard. Take them out.'),
        ('PRICES MOVED', 'Prices and delivery change. Read the new total.'),
        ('WATCH YOUR BASKET FREE', 'Or save your basket on CWhereUCheaper and watch it for free. Cheapest match first.'),
    )),
    'A marketplace seller matters': ('receipt', 'receipt.jpg', (
        ('WRONG SELLER?', 'Same product page. Different seller. Did you check?'),
        ("WHO'S SELLING?", 'Look at the actual seller, not just the product.'),
        ('DELIVERY. RETURNS.', 'Delivery and returns can change with the seller.'),
        ('COMPARE EXACT OFFERS', 'Compare offers for the same product on CWhereUCheaper. Cheapest match first.'),
    )),
    'Check the product variant': ('court', 'pouches.png', (
        ('WRONG ONE AGAIN?', 'The picture said your flavour. The dropdown said surprise.'),
        ('SIZE. COLOUR. FLAVOUR.', 'Same product family is not the same product.'),
        ('RECHECK THE PRICE', 'Pick the exact version, then check the price again.'),
        ('MATCH IT EXACTLY', 'Search the exact product on CWhereUCheaper. Cheapest match first.'),
    )),
    'A good price on the wrong item': ('court', 'court.jpg', (
        ('CHEAP. AND USELESS.', 'A cheap spare part is expensive if it does not fit.'),
        ('CHECK THE MODEL', 'Confirm the exact model and size first.'),
        ('THEN COMPARE', 'Only compare prices on parts that actually fit.'),
        ('SEARCH THE EXACT ONE', 'Then search that exact item on CWhereUCheaper. Cheapest match first.'),
    )),
    'Thirty seconds before checkout': ('receipt', 'receipt.jpg', (
        ('FREE DELIVERY TRAP', 'You added stuff just to get free delivery, didn\'t you?'),
        ('TAKE IT OUT', 'Remove anything you only added to reach the threshold.'),
        ('COMPARE BOTH TOTALS', 'Compare both totals. Sometimes paying delivery is cheaper.'),
        ('CHECK SHOPS FIRST', 'Check prices across shops on CWhereUCheaper first. Cheapest match first.'),
    )),
    'Compare usable quantity': ('pov', 'pouches.png', (
        ('BULK BUY REGRET', 'Your bulk buy looked brilliant. Then the leftovers moved in.'),
        ('WILL YOU USE IT?', 'A low unit price only helps if you use it in time.'),
        ('SMALL CAN WIN', 'Sometimes the smaller pack is the better buy.'),
        ('COMPARE SIZES', 'Compare pack sizes across shops on CWhereUCheaper. Cheapest match first.'),
    )),
}

# Live CWUC search recorded for the bridge beat (site_capture.py). Real public
# grocery searches that returned several matches on 25 November 2026.
SITE_QUERY = {
    'Do the division before the decision': 'colgate 75ml',
    'The R15 delivery difference': 'nescafe classic 200g',
    'Cheaper per unit can still cost more today': 'omo washing powder 2kg',
    'Watch for a different product strength': 'sunlight dishwashing liquid',
    'A bigger bottle may be different strength': 'sunlight dishwashing liquid',
    'Choose a basket before choosing an offer': 'cooking oil 2l',
    'Before you tap reorder': 'jacobs coffee',
    'A marketplace seller matters': 'nescafe classic 200g',
    'Check the product variant': 'colgate 75ml',
    'A good price on the wrong item': 'skip auto washing powder',
    'Thirty seconds before checkout': 'jacobs coffee',
    'Compare usable quantity': 'cooking oil 2l',
}
# Searches whose top results showed two or more shops on 25 November 2026. The
# recorder re-checks this live and moves down the list, because the bridge line
# says "across shops" and the footage must show it.
SITE_QUERY_ROTATION = ('colgate 75ml', 'omo washing powder 2kg', 'jacobs coffee', 'cooking oil 2l',
                       'skip auto washing powder', 'sunlight dishwashing liquid', 'nescafe classic 200g')

# Animated comparison card for the reveal beat: (label, value) pairs, winner index.
COMPARE = {
    'Do the division before the decision': ((('BUNDLE', 'R9 each'), ('SINGLE', 'R8 each')), 1),
    'The R15 delivery difference': ((('R90 + R30 delivery', 'R120'), ('R100 + R5 delivery', 'R105')), 1),
}

def _topic(item):
    if item.get('response_request_id'):
        return item['title'].strip().rstrip('.')
    return item['title'].split(':', 1)[-1].strip().rstrip('.')


def creative_key(value):
    return ' '.join(re.findall(r'\w+', value.casefold()))


def topic_key(item):
    if item.get('evidence_product'):
        return creative_key(item['evidence_product'])
    value = creative_key(_topic(item))
    if value in {'watch for a different product strength', 'a bigger bottle may be different strength'}:
        return 'compare bottle strength'
    return value


def fingerprint(item):
    beats = item.get('beats') or []
    body = ' '.join(line for _, line in beats[:-1]) if beats else item['script']
    hook = beats[0][1] if beats else re.split(r'(?<=[.!?])\s+', body, maxsplit=1)[0]
    return topic_key(item), creative_key(hook), creative_key(body)


def select_opening(item, used_assets):
    if item['asset'] not in used_assets:
        return item
    for fmt, asset in item['visual_options']:
        if asset not in used_assets:
            return {**item, 'format': fmt, 'asset': asset}
    return None


def _visuals(item, topic, first):
    space = creative_key(' '.join((topic, item.get('theme', ''))))
    if item.get('evidence_product_id') or item.get('evidence_comparison_subject'):
        choices = [('receipt', 'receipt.jpg'), ('pov', 'basket.png'), ('court', 'court.jpg')]
    elif re.search(r'\b(bottle|dosage|concentration|strength)\b', space):
        choices = [('pov', 'bottles.png'), ('court', 'court.jpg'), ('pov', 'basket.png')]
    elif re.search(r'\b(unit|kilogram|gram|pack|bulk|bundle|variant|quantity)\b', space):
        choices = [('court', 'pouches.png'), ('pov', 'basket.png'), ('receipt', 'receipt.jpg')]
    elif re.search(r'\b(delivery|checkout|voucher|seller|discount|cost|total)\b', space):
        choices = [('receipt', 'receipt.jpg'), ('court', 'court.jpg'), ('pov', 'basket.png')]
    else:
        choices = [('pov', 'cupboard.jpg'), ('pov', 'basket.png'), ('court', 'court.jpg')]
    return list(dict.fromkeys([first, *choices]))

# Match each frozen plan label to a different, neutral shopping scenario.
# These add context, not prices, savings, stock, or retailer claims.
PLAN_SCENARIOS = (
    'Picture this on a quick top-up shop.',
    'Try it with one item from your regular list.',
    'Use it when two listings are open on your phone.',
    'Run the check before you confirm the basket.',
    'Think about the next thing you are replacing.',
    'Try it while writing the list for your next shop.',
    'Use it when the packaging makes two choices look alike.',
    'Try it before deciding which retailer to visit.',
    'Use it on an offer you would actually buy.',
    'Try this when an unfamiliar alternative catches your eye.',
    'Run it on the item you are least sure about.',
    'Try it while planning the weekly shop.',
)


def _lesson_beats(item):
    # Preserve reviewed facts rather than putting a headline inside a spoken template.
    core = re.sub(
        r'\s*(?:Start your next price check at Cwhereucheaper\.co\.za|'
        r'Visit Cwhereucheaper\.co\.za before your next price check|'
        r'Begin your next shopping comparison at Cwhereucheaper\.co\.za|'
        r'Make Cwhereucheaper\.co\.za your next price-check starting point)\.?\s*$',
        '', item['script'], flags=re.I).strip()
    sentences = re.split(r'(?<=[.!?])\s+', core)
    if not item.get('response_request_id'):
        from content_factory import HOOKS
        for (label, hook), scenario in zip(HOOKS, PLAN_SCENARIOS):
            if item['title'].startswith(label+': ') and core.startswith(hook + ' '):
                sentences = re.split(r'(?<=[.!?])\s+', core[len(hook):].lstrip())
                sentences.insert(1,scenario)
                break
    if len(sentences) >= 4:
        a, b, c = (len(sentences) * i // 4 for i in (1, 2, 3))
        segments = [' '.join(group) for group in
                    (sentences[:a], sentences[a:b], sentences[b:c], sentences[c:])]
    else:
        segments = sentences
    if len(segments) == 4 and len(' '.join(segments).split()) <= 48:
        segments = [segments[0], segments[1], ' '.join(segments[2:])]
    labels = (_topic(item).upper(), 'LOOK CLOSER', 'CHECK THE DETAILS', 'BEFORE YOU BUY')
    beats = tuple(zip(labels, segments))
    if len(beats) <= 3 and len(' '.join(segments).split()) <= 48:
        beats = (*beats, ('COMPARE ON CWUC', BRIDGE_LINE))
    return beats

def episode_item(item, day, slot):
    offset = (day.toordinal() + ('early', 'am', 'pm').index(slot)) % len(FORMATS)
    fmt, asset = FORMATS[offset]
    topic = _topic(item)
    if topic in STORIES and not item.get('response_request_id'):
        fmt, asset, story = STORIES[topic]
        options = _visuals(item, topic, (fmt, asset))
    else:
        story = _lesson_beats(item)
        options = _visuals(item, topic, (fmt, asset))
        if item.get('response_request_id') or day.isoformat() >= '2026-11-24':
            fmt, asset = options[1] if len(options) > 1 else options[0]
    beats = (*story, CTA)
    return {
        **item,
        'date': day.isoformat(),
        'slot': slot,
        'title': topic,
        'caption': item['caption'],
        'asset': asset,
        'format': fmt,
        'visual_options': options,
        'scene_cuts': True,
        'is_price_evidence': bool(item.get('evidence_product_id') or item.get('evidence_comparison_subject')),
        'is_example': bool(re.search(r'illustrative|made-up|in this example', item['caption'], re.I)),
        'creative_policy': 'hook-bridge-cta-20261125',
        'beats': beats,
        'compare': COMPARE.get(topic) if not item.get('response_request_id') else None,
        'site_query': SITE_QUERY.get(topic) or SITE_QUERY_ROTATION[day.toordinal() % len(SITE_QUERY_ROTATION)],
        'style': 'Playful',
        'creative_version': VERSION,
        'script': ' '.join(line for _, line in beats),
        'video_style': 'kinetic captions + CWUC bridge',
    }


# --------------------------------------------------------------------------- #
# January Pro draw (Owner request, 24 November 2026). The evening slot promotes
# the draw from 26 November to 31 December 2026; the other slots stay tips.
# Every version states the benefit, how to enter, the random draw and the
# closing date; the caption adds how results are announced and where the rules
# are (Consumer Protection Act s36(5)). Rules: /pro/january-draw.
# --------------------------------------------------------------------------- #
import datetime as _dt

GIVEAWAY_FROM = _dt.date(2026, 11, 26)
GIVEAWAY_TO = _dt.date(2026, 12, 31)
GIVEAWAY_SLOT = 'pm'
GIVEAWAY_POLICY = 'january-pro-draw-20261124'
GIVEAWAY_RULES_URL = 'https://www.cwhereucheaper.co.za/pro/january-draw'
GIVEAWAY_HASHTAGS = '#CWhereUCheaper #JanuarySavings #SmartShoppingSA'
GIVEAWAY_CTA = ('JOIN FREE BY 31 DEC', 'Join free at CWhereUCheaper.co.za. Rules on the site.')
GIVEAWAY_CAPTION = (
    "December had its fun. January wants to see the receipts. 🧾🇿🇦\n\n"
    "Create and verify a free CWhereUCheaper account by 31 December 2026 to enter the draw. "
    "We'll pick 10 winners at random on 2 January 2027, and each gets CWUC Pro for January 2027, "
    "free and worth R99. Winners are told by email by 5 January 2027. No purchase needed.\n\n"
    f"Rules: {GIVEAWAY_RULES_URL}\n"
    "Not sponsored or run by Facebook, TikTok or YouTube.\n\n"
    "Make that January budget stretch. Sign up at cwhereucheaper.co.za."
)

# (title, format, asset, beats). Spoken text stays short: Buffer-ready videos must
# narrate in 8-24 seconds, so each version is at most 44 spoken words with the ending.
GIVEAWAY_VERSIONS = (
    ('January wants to see the receipts', 'receipt', 'receipt.jpg', (
        ('DECEMBER HAD ITS FUN', 'December had its fun. January wants the receipts.'),
        ('10 WINNERS, AT RANDOM', 'Ten random winners get January Pro.'),
        ('WORTH R99 EACH', 'Worth R99 each. No purchase needed.'),
        ('VERIFY BY 31 DEC', 'Create and verify a free account by the thirty-first of December.'),
    )),
    ('Your January budget called', 'pov', 'cupboard.jpg', (
        ('YOUR BUDGET CALLED', 'Your January budget called. It sounded nervous.'),
        ('WE HAVE BACKUP', 'Ten random winners get January Pro, worth R99 each.'),
        ('FREE TO ENTER', 'Create and verify a free account by the thirty-first of December.'),
        ('NOTHING TO BUY', 'No purchase needed.'),
    )),
    ('Januworry has a plan B', 'court', 'court.jpg', (
        ('JANUWORRY IS COMING', 'Januworry is coming. We have a plan B.'),
        ('10 MONTHS OF PRO', 'Ten random winners get January Pro, worth R99 each.'),
        ('ENTRY IS FREE', 'Verify a free account by the thirty-first of December.'),
        ('NOTHING TO BUY', 'No purchase needed.'),
    )),
    ('The court of January is in session', 'court', 'court.jpg', (
        ('ORDER IN THE COURT', 'Order in the court of January. Receipts on trial.'),
        ('THE VERDICT', 'Ten people get January Pro, worth R99 each.'),
        ('THE EVIDENCE', 'A free account, verified by the thirty-first of December.'),
        ('THE JURY IS RANDOM', 'Winners picked at random. Nothing to buy.'),
    )),
    ('POV: it is the second of January', 'pov', 'cupboard.jpg', (
        ('POV: 2 JANUARY', 'It is the second of January. The cupboard is judging you.'),
        ('10 WIN JANUARY PRO', 'Ten random winners get January Pro, worth R99 each.'),
        ('FREE ENTRY', 'Verify a free account by the thirty-first of December.'),
        ('NOTHING TO BUY', 'No purchase needed.'),
    )),
    ('Already a member? You are in', 'pov', 'basket.png', (
        ('ALREADY A MEMBER?', 'Got a verified CWUC account?'),
        ("YOU'RE ALREADY IN", "You're already in the January Pro draw."),
        ('10 RANDOM WINNERS', 'Ten random winners, worth R99 each.'),
        ('NEW HERE?', 'New here? Verify by the thirty-first of December.'),
    )),
    ('Two steps to enter', 'receipt', 'receipt.jpg', (
        ('TWO STEPS, TOPS', 'Two steps. Your January self says thanks.'),
        ('STEP ONE', 'Create a free account.'),
        ('STEP TWO', 'Verify your email by the thirty-first of December.'),
        ('10 WIN JANUARY PRO', 'Ten random winners get January Pro, worth R99 each.'),
    )),
    ('The festive receipt is long', 'receipt', 'receipt.jpg', (
        ('THE FESTIVE RECEIPT', 'The festive receipt is long. January reads every line.'),
        ('A LITTLE HELP', 'Ten random winners get January Pro, worth R99 each.'),
        ('FREE TO ENTER', 'Verify a free account by the thirty-first of December.'),
        ('NOTHING TO BUY', 'No purchase needed.'),
    )),
    ('What does Pro actually do?', 'pov', 'basket.png', (
        ('WHAT DOES PRO DO?', 'Pro watches prices on your list and says when to buy.'),
        ('WIN JANUARY FREE', 'Ten random winners get January Pro, worth R99 each.'),
        ('HOW TO ENTER', 'Verify a free account by the thirty-first of December.'),
        ('NOTHING TO BUY', 'No purchase needed.'),
    )),
    ('Make January stretch', 'court', 'court.jpg', (
        ('MAKE JANUARY STRETCH', 'January is long. Your budget needs backup.'),
        ('A MONTH OF PRO', 'Ten random winners get January Pro, worth R99 each.'),
        ('ENTER BY 31 DEC', 'Verify a free account by the thirty-first of December.'),
        ('NOTHING TO BUY', 'No purchase needed.'),
    )),
)
GIVEAWAY_FINAL_WEEK = ('One week left to enter', 'receipt', 'receipt.jpg', (
    ('ONE WEEK LEFT', 'Less than a week left to enter the January Pro draw.'),
    ('10 RANDOM WINNERS', 'Ten random winners, worth R99 each.'),
    ('FREE TO ENTER', 'Verify a free account by the thirty-first of December.'),
    ('NOTHING TO BUY', 'No purchase needed.'),
))
GIVEAWAY_LAST_DAY = ('Last day to enter', 'receipt', 'receipt.jpg', (
    ('LAST DAY TO ENTER', 'Last day to enter the January Pro draw.'),
    ('CLOSES 23:59 TONIGHT', 'Entries close one minute before midnight.'),
    ('FREE • VERIFY TODAY', 'Verify a free account today.'),
    ('10 RANDOM WINNERS', 'Ten random winners, worth R99 each.'),
))


def is_giveaway_slot(day, slot):
    return slot == GIVEAWAY_SLOT and GIVEAWAY_FROM <= day <= GIVEAWAY_TO


def giveaway_version(day):
    if day == GIVEAWAY_TO:
        return GIVEAWAY_LAST_DAY
    if day >= GIVEAWAY_TO - _dt.timedelta(days=6):
        return GIVEAWAY_FINAL_WEEK
    return GIVEAWAY_VERSIONS[(day - GIVEAWAY_FROM).days % len(GIVEAWAY_VERSIONS)]


def giveaway_item(day, slot):
    title, fmt, asset, story = giveaway_version(day)
    if title == GIVEAWAY_FINAL_WEEK[0]:
        # A countdown keeps each final-week day distinct for the repeat check.
        left = (GIVEAWAY_TO - day).days
        words = ('one', 'two', 'three', 'four', 'five', 'six')[left - 1]
        plural = 'day' if left == 1 else 'days'
        title = f'{words.capitalize()} {plural} left to enter'
        story = ((f'{left} {plural.upper()} LEFT', f'{words.capitalize()} {plural} left to enter the January Pro draw.'),
                 *story[1:])
    beats = (*story, GIVEAWAY_CTA)
    options = list(dict.fromkeys([(fmt, asset), ('receipt', 'receipt.jpg'), ('court', 'court.jpg'),
                                  ('pov', 'cupboard.jpg'), ('pov', 'basket.png')]))
    return {
        'date': day.isoformat(),
        'slot': slot,
        'title': title,
        'caption': GIVEAWAY_CAPTION,
        'theme': 'giveaway',
        'asset': asset,
        'format': fmt,
        'visual_options': options,
        'scene_cuts': True,
        'is_price_evidence': False,
        'is_example': False,
        'giveaway': True,
        'growth_hashtags': GIVEAWAY_HASHTAGS,
        'creative_policy': 'hook-bridge-cta-20261125',
        'giveaway_policy': GIVEAWAY_POLICY,
        'beats': beats,
        'style': 'Playful',
        'creative_version': VERSION,
        'script': ' '.join(line for _, line in beats),
        'video_style': 'kinetic captions + CWUC bridge',
    }
