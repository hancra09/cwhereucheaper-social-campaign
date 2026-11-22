"""Retention-first CWUC mini-stories, derived from the frozen daily lesson plan."""
VERSION = 'creative-v3'

FORMATS = (
    ('receipt', 'receipt.jpg'),
    ('court', 'court.jpg'),
    ('pov', 'cupboard.jpg'),
)


def _topic(item):
    return item['title'].split(':', 1)[-1].strip().rstrip('.')


def _beats(fmt, topic):
    """Short, original comedy beats; the frozen lesson remains in the caption."""
    scripts = {
        'receipt': (
            ('THE RECEIPT OBJECTS', f'I came for {topic.lower()}. The receipt came with a plot twist.'),
            ('ITEM PRICE', 'It looked cheap until checkout joined the meeting.'),
            ('THE ACTUAL TOTAL', 'Now we compare the full total, not the opening scene.'),
            ('VERDICT', 'Your wallet would like the facts, please.'),
        ),
        'court': (
            ('ORDER IN THE TROLLEY!', f"Today's case: {topic}."),
            ('EXHIBIT A', 'The label made a very confident promise.'),
            ('EXHIBIT B', 'The details are giving the side-eye.'),
            ('VERDICT', 'Check the whole story before the trolley wins.'),
        ),
        'pov': (
            ('POV: YOU ARE SHOPPING', f'I only wanted to {topic.lower()}.'),
            ('ONE TINY DETAIL', 'Then the fine print started doing cardio.'),
            ('THE PLOT THICKENS', 'Apparently the trolley had its own budget.'),
            ('SAVE THE DRAMA', 'Pause. Check. Then let the facts win.'),
        ),
    }
    return scripts[fmt] + (
        ('CHECK BEFORE YOU BUY', 'Visit CWhereUCheaper.co.za before your next checkout.'),
    )


def episode_item(item, day, slot):
    """Keep all future slots in the proven video format without replaying one trial."""
    offset = (day.toordinal() + ('early', 'am', 'pm').index(slot)) % len(FORMATS)
    fmt, asset = FORMATS[offset]
    topic = _topic(item)
    beats = _beats(fmt, topic)
    return {
        **item,
        'date': day.isoformat(),
        'slot': slot,
        'title': topic,
        'caption': item['caption'] + ' What would you check first?',
        'asset': asset,
        'format': fmt,
        'beats': beats,
        'style': 'Playful',
        'creative_version': VERSION,
        'script': ' '.join(line for _, line in beats),
        'video_style': 'retention-first shopping mini-story',
    }
