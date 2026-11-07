"""Original evergreen shopping education; no live offers or paid text service."""
import calendar
import datetime as dt
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent
VERSION = 1
SLOTS = ('early', 'am', 'pm')
LESSONS = [
    ('unit-price', 'Compare the same quantity', 'Put both products on the same unit before comparing. A price per kilogram cannot be compared directly with a price per hundred grams.'),
    ('unit-price', 'Read the refill quantity', 'A refill and a full bottle can hold different amounts. Compare their usable quantity and total price before deciding which offers better value.'),
    ('unit-price', 'Count what is inside', 'Check both the number of items and the size of each one. Similar looking multipacks can contain very different total quantities.'),
    ('unit-price', 'Check the concentrated version', 'For a concentrate, check the dilution instructions and usable amount. Comparing bottle sizes alone can miss an important difference.'),
    ('unit-price', 'Watch the package size', 'When a familiar item looks cheaper, check its weight or volume again. A smaller package can change the comparison even when the shelf price falls.'),
    ('checkout', 'Compare the final total', 'Add delivery and any checkout charges before choosing a retailer. The lowest item price does not always produce the lowest final total.'),
    ('checkout', 'Price the collection trip', 'Collection can avoid a delivery fee, but travel still takes time and money. Include the trip when comparing your options.'),
    ('checkout', 'Check a delivery threshold', 'Before adding extras to unlock delivery, compare the extra spending with the delivery charge. Only add items you already need.'),
    ('checkout', 'Look at split deliveries', 'A basket split across retailers may involve more than one delivery charge. Compare the combined total with buying from one place.'),
    ('checkout', 'Recheck before payment', 'Review quantities, delivery choices and the final amount before paying. A useful comparison should end with the price you actually agree to pay.'),
    ('planning', 'Check the cupboard first', 'Look through your cupboards before making a shopping list. Finding something you already own can remove an unnecessary purchase altogether.'),
    ('planning', 'Plan the next few meals', 'Build a short meal plan around ingredients already at home. Then compare prices for the missing ingredients rather than starting with sale stickers.'),
    ('planning', 'Separate needs and extras', 'Mark the items you need before browsing offers. Keeping extras separate makes it easier to see what is changing your basket total.'),
    ('planning', 'Keep a useful backup choice', 'Choose an acceptable alternative before shopping. If your first choice is unavailable, compare the substitute instead of buying the first replacement you see.'),
    ('planning', 'Compare a realistic basket', 'Compare the products and quantities your household will actually use. A cheaper basket is only useful when it still meets your needs.'),
    ('waste', 'Buy the amount you will use', 'A large pack only helps when you can use its contents. Consider storage space and likely use before paying for extra quantity.'),
    ('waste', 'Check storage instructions', 'Read storage instructions before choosing a bulk purchase. A product that needs conditions you cannot provide may become an expensive mistake.'),
    ('waste', 'Check the date label', 'Read the date label and storage instructions before buying. Choose an amount you can use appropriately, rather than letting a discount choose the quantity.'),
    ('waste', 'Use the open packet first', 'Check which packets are already open before adding more to your basket. Using existing supplies can reduce both spending and avoidable waste.'),
    ('waste', 'Think about freezer space', 'Before buying extra food for freezing, check available space and the product instructions. A bulk offer needs a practical storage plan.'),
    ('equivalence', 'Match the model number', 'For electronics and appliances, compare the complete model number. Similar names or photographs do not prove that two listings contain the same product.'),
    ('equivalence', 'Check included accessories', 'Read what comes in the box before comparing bundles. One listing may include accessories that another sells separately.'),
    ('equivalence', 'Compare the product variant', 'Match the size, variant and quantity before comparing prices. A different formulation or model can make a lower price a different offer.'),
    ('equivalence', 'Read the power requirements', 'Check the product specifications and intended use before buying an appliance. A cheaper model still needs to do the job you require.'),
    ('equivalence', 'Look beyond the photograph', 'Use the written product description, model and quantity to check a match. A familiar photograph alone is not enough evidence.'),
    ('offers', 'Read the minimum purchase', 'Check whether an offer requires a minimum quantity or basket total. Compare the full amount you must spend, not just the advertised unit price.'),
    ('offers', 'Check who qualifies', 'Read the conditions for a member or promotional price. Make sure you qualify before using that price in your comparison.'),
    ('offers', 'Read a discount carefully', 'A large percentage discount does not establish the best current price. Compare the actual item and final total across your available options.'),
    ('offers', 'Compare bundles with care', 'List the items in a bundle and decide which you need. Extra items only add value when they are useful to you.'),
    ('offers', 'Check the offer period', 'Check the offer dates and any stock conditions before planning a purchase. Reconfirm the price when you are ready to buy.'),
    ('ownership', 'Think beyond purchase day', 'For a reusable product, consider the supplies it needs and how you will use it. The purchase price is only one part of the decision.'),
    ('ownership', 'Check replacement supplies', 'Before buying a device, check the availability and cost of its compatible consumables. A low starting price may leave important future costs unanswered.'),
    ('ownership', 'Read the return terms', 'Review the retailer return terms and product condition before buying. Keep the receipt and product details so you have a useful record.'),
    ('ownership', 'Check the warranty details', 'Read who provides the warranty, what it covers and any stated conditions. Similar products can come with different support arrangements.'),
    ('ownership', 'Compare useful capacity', 'Choose capacity that fits your normal use and available space. Paying for extra size is not automatically a saving.'),
    ('shopping-check', 'Write down the full comparison', 'Record the retailer, product, quantity and final price together. A short note makes it easier to compare the same things later.'),
    ('shopping-check', 'Check availability before travelling', 'Check the retailer listing or contact the store before making a special trip. An advertised product may not be available at every branch.'),
    ('shopping-check', 'Keep alternatives comparable', 'If you change brands, check quantity and intended use again. A replacement should be judged on what you will actually receive.'),
    ('shopping-check', 'Pause before an extra purchase', 'Before adding an unplanned item, decide what you will use it for. A lower price is not a saving on something you did not need.'),
    ('shopping-check', 'Make one clear price check', 'Start with a specific product, size or model rather than a vague category. A clear description makes the comparison more useful.'),
]
HOOKS = [
    ('Before you buy', 'Before your next purchase, try this check.'),
    ('Small shopping check', 'One small check can improve a shopping decision.'),
    ('A clearer comparison', 'Make your next comparison easier to understand.'),
    ('Pause at checkout', 'Pause for a quick check before committing.'),
    ('Check this detail', 'Here is a detail worth checking before buying.'),
    ('Shopping list reminder', 'Keep this reminder beside your shopping list.'),
    ('Look a little closer', 'Look a little closer before choosing a price.'),
    ('Your next price check', 'Give your next price check a clear starting point.'),
    ('Read before choosing', 'Read the details before choosing between offers.'),
    ('A practical buying habit', 'Try this practical habit when comparing products.'),
    ('A useful second look', 'A useful second look starts with the details.'),
    ('Plan then compare', 'Plan the purchase, then compare the options.'),
]
CONTEXT = [
    'Keep the comparison tied to your actual needs.',
    'Check the details again when you are ready to buy.',
    'Let the full comparison guide your choice.',
    'Take a moment to check rather than guess.',
    'Keep a short note of the options you compare.',
    'A clear comparison is more useful than a rushed one.',
]
CTA = [
    'Start your next price check at Cwhereucheaper.co.za.',
    'Visit Cwhereucheaper.co.za before your next price check.',
    'Begin your next shopping comparison at Cwhereucheaper.co.za.',
    'Make Cwhereucheaper.co.za your next price-check starting point.',
]


def theme_for(title):
    value = title.lower()
    for theme, words in [
        ('unit-price', ('unit', 'pack', 'kilogram', 'quantity', 'refill')),
        ('checkout', ('delivery', 'checkout', 'collection', 'total')),
        ('waste', ('waste', 'expiry', 'storage', 'freezer')),
        ('equivalence', ('model', 'variant', 'accessor', 'photograph')),
        ('offers', ('offer', 'discount', 'bundle', 'member', 'two for')),
        ('ownership', ('warranty', 'return', 'consumable', 'capacity')),
        ('planning', ('list', 'cupboard', 'meal', 'plan')),
    ]:
        if any(word in value for word in words):
            return theme
    return 'shopping-check'


def build_month(month, preferred=(), previous=()):
    """Freeze a varied month from vetted material; never repeat a saved script."""
    first = dt.date.fromisoformat(month + '-01')
    rng = random.Random(f'cwuc-evergreen-v{VERSION}-{month}')
    lessons = list(LESSONS)
    rng.shuffle(lessons)
    preferred = set(preferred)
    favourites = [x for x in lessons if x[0] in preferred]
    used = set(previous)
    used_titles = set()
    entries = []
    recent = []
    for day in range(1, calendar.monthrange(first.year, first.month)[1] + 1):
        for slot in SLOTS:
            # At most two of every five slots follow a reviewed theme. Keep variety.
            pool = favourites if favourites and len(entries) % 5 < 2 else lessons
            candidates = [x for x in pool if x[1] not in recent[-3:]] or lessons
            for _ in range(2000):
                theme, title, body = rng.choice(candidates)
                short, hook = rng.choice(HOOKS)
                script = ' '.join((hook, body, rng.choice(CONTEXT), rng.choice(CTA)))
                if script not in used and short + ': ' + title not in used_titles:
                    break
            else:
                raise RuntimeError('Fresh content choices exhausted; extend the vetted library.')
            assert 30 <= len(script.split()) <= 65, 'Narration outside the reviewed duration'
            used.add(script)
            used_titles.add(short + ': ' + title)
            recent.append(title)
            entries.append({
                'date': first.replace(day=day).isoformat(), 'slot': slot,
                'title': short + ': ' + title, 'script': script,
                'caption': body + ' ' + rng.choice(CONTEXT),
                'style': ('Educational', 'Storytelling', 'Playful')[len(entries) % 3],
                'theme': theme,
            })
    content = {'month': month, 'generator_version': VERSION,
               'content_kind': 'Curated evergreen education with varied hooks and wording',
               'preferred_themes': sorted(preferred), 'items': entries}
    content['sha256'] = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    return content


def validate_plan(plan, month):
    expected = calendar.monthrange(*map(int, month.split('-')))[1] * 3
    body = {k: v for k, v in plan.items() if k != 'sha256'}
    assert plan['month'] == month and len(plan['items']) == expected
    assert plan['sha256'] == hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    assert len({x['script'] for x in plan['items']}) == expected
    assert len({(x['date'], x['slot']) for x in plan['items']}) == expected
    for x in plan['items']:
        date = dt.date.fromisoformat(x['date'])
        assert date.strftime('%Y-%m') == month and x['slot'] in SLOTS
        assert all(x.get(k, '').strip() for k in ('title', 'script', 'caption'))
        assert len(x['script'].split()) <= 65
    return plan
