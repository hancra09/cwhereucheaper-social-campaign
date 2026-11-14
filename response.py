"""Conservative, deterministic first slice of viewer-request handling.

Only explicitly supported generic shopping questions are handled here.
Named products and other requests require separate verified research.
Never pass viewer text into a public script or executable instruction.
"""
import re
import hashlib
import urllib.request
from html.parser import HTMLParser

SOURCE = 'https://clicks.co.za/onlineshopping'
UNIT_SOURCE = 'https://www.health.gov.za/wp-content/uploads/2020/11/tri-fold_pamphlet.pdf'
UNIT_SOURCE_SHA256 = '343ef7aaa938515d5ec17bde83ca3587708c89c923dbac08b74823760b811f7a'


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.hidden:
            self.hidden -= 1
    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def select(body):
    """Accept a narrow generic question; reject injected text and specific claims."""
    if not isinstance(body, str) or len(body) > 350:
        return None
    s = re.sub(r'\s+', ' ', body.lower()).strip()
    if re.search(r'https?://|@|#|\d|[<>`{}\[\]]', s):
        return None
    vocabulary = set('a about add affect affects an and are as at basket baskets be before buy buying can changes check compare comparing cost costs could delivery difference do does fee fees for get how i in is it make me next of on online order orders please price prices see share show shopping should tell than the to video want we what when which why will with would you your cheaper cheapest expensive more less final total totals change unit units gram grams kilogram kilogramme kilograms kilo kilos per litre liter litres liters pack packs size sizes smaller bigger larger calculate calculating calculation work works out means mean explain math maths differences different bulk expiry dates date store storing storage waste food use using amount amounts space cupboard list lists meal meals planning plan needs need save savings money household household help understand understanding explaining explanation explain example examples groceries grocery shopping shoppers ways way advice tip tips question questions using works figuring figure find finding me my our lets lets s d'.split())
    words = re.findall(r"[a-z]+", s)
    if not words or any(word not in vocabulary for word in words):
        return None
    if not ('?' in s or re.search(r'\b(please|show|tell|compare|video|how|what|why|which|could|can|explain)\b', s)):
        return None
    if re.search(r'\bdelivery\b',s) and re.search(r'\b(fee|fees|cost|costs|total|totals|price|prices)\b',s):
        return 'delivery_total_v1'
    if re.search(r'\bunit\b',s) and re.search(r'\b(price|prices|cost|costs)\b',s):
        return 'unit_price_v1'
    if re.search(r'\bper\b',s) and re.search(r'\b(gram|grams|kilogram|kilograms|kilo|litre|litres|liter|liters)\b',s) and re.search(r'\b(compare|comparing|price|prices|cost|costs)\b',s):
        return 'unit_price_v1'
    if re.search(r'\bbulk\b',s):
        return 'bulk_buying_v1'
    if re.search(r'\b(list|lists|meal|meals|planning|plan)\b',s) and re.search(r'\b(shopping|meal|meals|list|lists)\b',s):
        return 'shopping_plan_v1'
    return None


def research(fetch=None,topic='delivery_total_v1'):
    """Check a live authoritative source. Unit-price guide is pinned after review."""
    if topic in ('unit_price_v1','bulk_buying_v1','shopping_plan_v1'):
        def get_pdf(url):
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 CWUC video research'})
            with urllib.request.urlopen(req,timeout=25) as response:
                if response.status!=200 or not response.geturl().startswith('https://www.health.gov.za/'):
                    raise ValueError('Unexpected unit-price source')
                return response.read(2_000_001)
        data=(fetch or get_pdf)(UNIT_SOURCE)
        if len(data)>2_000_000 or hashlib.sha256(data).hexdigest()!=UNIT_SOURCE_SHA256:
            raise ValueError('Unit-price source unavailable or changed')
        return {'url':UNIT_SOURCE,'finding':'The South African health department offers budget shopping guidance.'}
    if topic!='delivery_total_v1':raise ValueError('Unsupported topic')
    def default(url):
        req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 CWUC video research'})
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status != 200 or not response.geturl().startswith('https://clicks.co.za/'):
                raise ValueError('Unexpected research source')
            return response.read(1_000_001)
    data = (fetch or default)(SOURCE)
    if len(data) > 1_000_000:
        raise ValueError('Research page too large')
    p=Text(); p.feed(data.decode('utf-8',errors='replace'))
    body=' '.join(' '.join(p.parts).lower().split())
    if 'delivery' not in body or not re.search(r'\b(fee|fees|cost|costs)\b', body):
        raise ValueError('Delivery information not verified')
    return {'url':SOURCE,'finding':'The retailer publishes delivery options and costs; check the current checkout.'}


def build(topic, evidence):
    if topic=='bulk_buying_v1' and evidence.get('url')==UNIT_SOURCE:
        return {'title':'Is bulk buying worth it?',
          'script':('Bigger is not always a bargain. Compare the unit price and buy an amount you will use. '
                    'Check storage space and the date label before buying more. Your fridge has opinions too.'),
          'caption':'Compare the unit price, storage and date labels before a bulk purchase. Source: '+UNIT_SOURCE,
          'style':'Educational','theme':'waste','growth_hashtags':'#BulkBuying #SmartShopping #SouthAfrica','creative_version':'creative-v2'}
    if topic=='shopping_plan_v1' and evidence.get('url')==UNIT_SOURCE:
        return {'title':'A shopping list that helps',
          'script':('Before you shop, check what you already have at home. Plan your meals and write a shopping list. '
                    'Compare the same quantities and keep extras separate. Your cupboard might surprise you.'),
          'caption':'Check your cupboards, plan meals and take a list when you shop. Source: '+UNIT_SOURCE,
          'style':'Educational','theme':'planning','growth_hashtags':'#ShoppingList #SmartShopping #SouthAfrica','creative_version':'creative-v2'}
    if topic=='unit_price_v1' and evidence.get('url')==UNIT_SOURCE:
        return {'title':'Price per hundred grams made simple',
          'script':('In this example, a 500 gram pack costs R30. A 600 gram pack costs R42. '
                    'That is R6 per 100 grams versus R7 per 100 grams. The smaller pack costs less per 100 grams.'),
          'caption':('Illustrative maths, not retailer prices: R30 for 500 grams is R6 per 100 grams; R42 for 600 grams is R7 per 100 grams. ' 
                     'Compare the same product and unit. Source: '+UNIT_SOURCE),
          'style':'Educational','theme':'unit-price','growth_hashtags':'#UnitPrice #SmartShopping #SouthAfrica','creative_version':'creative-v2'}
    if topic != 'delivery_total_v1' or evidence.get('url') != SOURCE:
        raise ValueError('Unsupported or unverified topic')
    return {'title':'Can delivery change the cheaper basket?',
      'script':('In this made-up example, basket A costs R100 plus R40 delivery, for R140 total. '
                'Basket B costs R120 with free delivery, so its total is R120. '
                'The cheaper items cost more at checkout. Compare the same items and all final charges.'),
      'caption':('Illustrative example, not current retailer prices: R100 plus R40 delivery is R140; R120 with free delivery is R120. Compare the same basket and final charges. '
                 'Retailer delivery details: https://clicks.co.za/onlineshopping'),
      'style':'Educational','theme':'checkout',
      'growth_hashtags':'#DeliveryFees #SmartShopping #SouthAfrica',
      'creative_version':'creative-v2'}
