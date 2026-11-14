"""Conservative, deterministic first slice of viewer-request handling.

Only a generic delivery-cost question is handled. Specific retailers, prices,
products and other requests remain unhandled until independently researched.
Never pass viewer text into a public script or executable instruction.
"""
import re
import urllib.request
from html.parser import HTMLParser

SOURCE = 'https://clicks.co.za/onlineshopping'


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
    vocabulary = set('a about add affect affects an and are as at basket baskets be before buy buying can changes check compare comparing cost costs could delivery difference do does fee fees for get how i in is it make me next of on online order orders please price prices see share show shopping should tell than the to video want we what when which why will with would you your cheaper cheapest expensive more less final total totals change'.split())
    words = re.findall(r"[a-z]+", s)
    if not words or any(word not in vocabulary for word in words):
        return None
    if not re.search(r'\b(delivery)\b', s) or not re.search(r'\b(fee|fees|cost|costs|total|totals|price|prices)\b', s):
        return None
    if not ('?' in s or re.search(r'\b(please|show|tell|compare|video|how|what|why|which|could|can)\b', s)):
        return None
    return 'delivery_total_v1'


def research(fetch=None):
    """Check a retailer's live public delivery information; do not extract prices."""
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
    if topic != 'delivery_total_v1' or evidence.get('url') != SOURCE:
        raise ValueError('Unsupported or unverified topic')
    return {'title':'Can delivery change the cheaper basket?',
      'script':('Delivery fees have entered the chat. Compare the same items and quantities at each shop. '
                'Add delivery and any other checkout charges to each basket. '
                'Then compare the final totals before you buy.'),
      'caption':('A lower item price may not mean a lower checkout total. Compare the same basket and include delivery and other charges. '
                 'Retailer delivery details: https://clicks.co.za/onlineshopping'),
      'style':'Educational','theme':'checkout',
      'growth_hashtags':'#DeliveryFees #SmartShopping #SouthAfrica',
      'creative_version':'creative-v2'}
