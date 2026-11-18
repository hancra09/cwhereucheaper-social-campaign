"""Three original episodes for the first retention trial."""
import datetime as dt

VERSION = 'creative-v3'
TRIAL_DAY = dt.date(2026, 11, 21)

EPISODES = {
    'early': {
        'title': 'That delivery fee arrived with luggage',
        'caption': 'The cheaper item lost at checkout. Which total did you expect to win?',
        'asset': 'receipt.jpg',
        'format': 'receipt',
        'beats': [
            ('HOW DID R200 LOSE?', 'My delivery fee arrived with luggage.'),
            ('R200 + R60 = R260', 'Two hundred rand. Then sixty for delivery.'),
            ('R230 DELIVERED', 'The other one? Two thirty, delivered.'),
            ('THE “CHEAP” ONE LOST.', 'The cheap one owes me thirty bucks.'),
        ],
    },
    'am': {
        'title': 'The bulk pack is on trial',
        'caption': 'The charge is taking up half the cupboard. Would you still buy the bulk pack?',
        'asset': 'court.jpg',
        'format': 'court',
        'beats': [
            ('ORDER IN THE CUPBOARD!', 'Order! The bulk pack is on trial.'),
            ('EXHIBIT A', 'You said buying in bulk would save space?'),
            ('EXHIBIT B', 'Your Honour, the broom now lives outside.'),
            ('VERDICT: MEASURE FIRST.', 'Guilty. Measure the cupboard first.'),
        ],
    },
    'pm': {
        'title': 'My cupboard has receipts',
        'caption': 'What grocery item do you keep buying because you forgot you already have it?',
        'asset': 'cupboard.jpg',
        'format': 'pov',
        'beats': [
            ('I SWEAR WE HAD NO PASTA', 'I swear we had no pasta.'),
            ('PACKET ONE.', 'Oh. One packet.'),
            ('TWO. THREE.', 'Two. Three. This is a franchise.'),
            ('CHECK THE CUPBOARD FIRST.', 'At this point the cupboard can make dinner.'),
        ],
    },
}


def trial_item(day, slot):
    if day != TRIAL_DAY:
        return None
    episode = EPISODES[slot]
    return {
        **episode,
        'date': day.isoformat(),
        'slot': slot,
        'style': 'Playful',
        'creative_version': VERSION,
        'script': ' '.join(line for _, line in episode['beats']),
    }
