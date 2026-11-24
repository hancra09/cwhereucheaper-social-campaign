"""Topic-specific CWUC stories with a shared site ending and rotating visuals."""
import re

VERSION = 'creative-v4'
FORMATS = (('receipt', 'receipt.jpg'), ('court', 'court.jpg'), ('pov', 'cupboard.jpg'))
CTA = ('CHECK BEFORE YOU BUY', 'Visit CWhereUCheaper.co.za before your next checkout.')

# Illustrative scenarios, not current price, stock or retailer claims.
STORIES = {
    'Cheaper per unit can still cost more today': ('court', 'pouches.png', (
        ('BULK BAG ON TRIAL', 'The big bag is cheaper per scoop. My wallet would like to buy just the scoop, please.'),
        ('AT THE TILL', 'The till has bad news. I have to pay for the whole bag.'),
        ('TWO DIFFERENT NUMBERS', 'Check the cost per scoop and the cash you need today.'),
        ('SMALL BAG WINS', 'If the big bag busts the budget or goes to waste, the small one wins this round.'),
    )),
    'Watch for a different product strength': ('pov', 'bottles.png', (
        ('BOTTLE TWINS?', 'These laundry bottles could be twins. Until you turn them around.'),
        ('FLIP THE LABELS', 'One is concentrated. The labels give different directions.'),
        ('COUNT THE WASHES', 'Same size bottle does not tell me how many washes I am buying.'),
        ('CHECK THE DIRECTIONS', 'I am checking the dosage and the stated washes before I pick.'),
    )),
    'Do the division before the decision': ('receipt', 'receipt.jpg', (
        ('ILLUSTRATIVE EXAMPLE', 'Six for R54 sounds like a special. My calculator would like a word.'),
        ('R54 ÷ 6 = R9 EACH', 'R54 divided by six is R9 each.'),
        ('SINGLE ITEM: R8', 'The single costs R8 in this example.'),
        ('THE BUNDLE LOSES', 'The bundle loses. Never let a sticker do your maths.'),
    )),
    "The R15 delivery difference": ("receipt", "receipt.jpg", (
        ("CHEAP UNTIL CHECKOUT", "Two identical items. One is R90. The other is R100. Easy, right?"),
        ("DELIVERY JOINS IN", "The R90 item adds R30 delivery. Total: R120."),
        ("PLOT TWIST", "The R100 item adds just R5. Total: R105."),
        ("R15 LESS IN THIS EXAMPLE", "The higher sticker price wins by R15. Compare the checkout totals."),
    )),
    "A bigger bottle may be different strength": ("pov", "bottles.png", (
        ("BIGGER ISN’T ALWAYS BETTER", "The bigger bottle has entered the chat. So has the tiny dosage label."),
        ("READ THE BACK", "Check how much each bottle says to use."),
        ("COMPARE EQUIVALENT USES", "Different strengths can make volume a bad shortcut."),
        ("DON’T GUESS BY SIZE", "Compare equivalent washes only when the labels give you enough information."),
    )),
    "Choose a basket before choosing an offer": ("court", "basket.png", (
        ("THE TROLLEY HAS A LAWYER", "I came for dinner. My trolley wants to plead special offer."),
        ("START WITH THE PLAN", "Decide what you actually need before looking at the promotions."),
        ("COMPARE THAT BASKET", "Find a good price on your own list, not a list built by discounts."),
        ("EXHIBIT: THREE UNPLANNED EXTRAS", "An individual bargain can still leave you spending more."),
    )),
    "Before you tap reorder": ("pov", "cupboard.jpg", (
        ("REORDER IS NOT REPLAY", "My reorder button remembers everything except what changed since last time."),
        ("CHECK QUANTITIES", "Review the quantities. Take out what is already in the cupboard."),
        ("CHECK SUBSTITUTIONS", "Look for unavailable items or changed substitutions."),
        ("CHECK THE CURRENT TOTAL", "Prices and delivery can change. Read the new total before confirming."),
    )),
    "A marketplace seller matters": ("receipt", "receipt.jpg", (
        ("SAME PAGE, DIFFERENT SELLER", "Ever recognised the product and missed the name on the till slip?"),
        ("CHECK WHO’S SELLING", "Look at the actual marketplace seller, not just the product page."),
        ("CHECK DELIVERY AND RETURNS", "Availability, delivery and returns can change with the seller."),
        ("COMPARE THE EXACT OFFER", "Match the item and check the final total before you pay."),
    )),
    "Check the product variant": ("court", "pouches.png", (
        ("THE PRODUCT HAS AN ALIBI", "The picture says favourite flavour. The dropdown says surprise."),
        ("SIZE, COLOUR, FLAVOUR", "Same product family does not mean the same version."),
        ("MATCH THE SELECTION", "Check the exact variant and specifications you want."),
        ("RECHECK THE PRICE", "The price you saw before picking a version might not be the price you pay."),
    )),
    "A good price on the wrong item": ("court", "court.jpg", (
        ("A DEAL THAT DOESN’T FIT", "A cheap spare part is expensive when it fits everything except your machine."),
        ("CHECK THE FIT", "Confirm the dimensions, compatibility or exact model."),
        ("COMPARE SUITABLE OPTIONS", "Rule out the wrong items before comparing prices."),
        ("THEN CHECK THE TOTAL", "Compare the complete cost of the items that actually work for you."),
    )),
    "Thirty seconds before checkout": ("receipt", "receipt.jpg", (
        ("THE EXTRA ITEM TEST", "I added an extra item to save on shipping. My calculator has questions."),
        ("TAKE A SHORT PAUSE", "Remove anything you only added to reach the threshold."),
        ("COMPARE BOTH TOTALS", "Recalculate delivery and put the two payable totals side by side."),
        ("BUY WHAT YOU NEED", "Keep the version that makes sense for what you actually wanted."),
    )),
    "Compare usable quantity": ("pov", "pouches.png", (
        ("THE FRIDGE CAN’T KEEP SECRETS", "My bulk buy looked brilliant until the leftovers started applying for residency."),
        ("COUNT WHAT YOU CAN USE", "A low unit price helps only if you can use the food in time."),
        ("CHECK SAFE STORAGE", "Look at the space you have and how you’ll store it safely."),
        ("SMALL CAN MAKE SENSE", "A smaller pack can be better for your household even with a higher unit price."),
    )),
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
    labels = (_topic(item).upper(), 'LOOK CLOSER', 'CHECK THE DETAILS', 'BEFORE YOU BUY')
    return tuple(zip(labels, segments))

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
        'creative_policy': 'fresh-stories-20261122',
        'beats': beats,
        'style': 'Playful',
        'creative_version': VERSION,
        'script': ' '.join(line for _, line in beats),
        'video_style': 'retention-first shopping mini-story',
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
        'creative_policy': 'fresh-stories-20261122',
        'giveaway_policy': GIVEAWAY_POLICY,
        'beats': beats,
        'style': 'Playful',
        'creative_version': VERSION,
        'script': ' '.join(line for _, line in beats),
        'video_style': 'retention-first shopping mini-story',
    }
