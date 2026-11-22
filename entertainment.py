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
}

def _topic(item):
    return item['title'].split(':', 1)[-1].strip().rstrip('.')

def _lesson_beats(item):
    # Preserve reviewed facts rather than putting a headline inside a spoken template.
    core = re.sub(
        r'\s*(?:Start your next price check at Cwhereucheaper\.co\.za|'
        r'Visit Cwhereucheaper\.co\.za before your next price check|'
        r'Begin your next shopping comparison at Cwhereucheaper\.co\.za|'
        r'Make Cwhereucheaper\.co\.za your next price-check starting point)\.?\s*$',
        '', item['script'], flags=re.I).strip()
    sentences = re.split(r'(?<=[.!?])\s+', core)
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
    if topic in STORIES:
        fmt, asset, story = STORIES[topic]
    else:
        story = _lesson_beats(item)
    beats = (*story, CTA)
    return {
        **item,
        'date': day.isoformat(),
        'slot': slot,
        'title': topic,
        'caption': item['caption'],
        'asset': asset,
        'format': fmt,
        'beats': beats,
        'style': 'Playful',
        'creative_version': VERSION,
        'script': ' '.join(line for _, line in beats),
        'video_style': 'retention-first shopping mini-story',
    }
