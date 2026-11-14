"""Research an exact public product-page price with fail-closed evidence checks."""
import datetime as dt
import decimal
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ORIGIN='https://www.cwhereucheaper.co.za'
ALLOWED_HOST='superbhyper.co.za'
SAST=dt.timezone(dt.timedelta(hours=2))


def normalize(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    return ' '.join(re.findall('[a-z0-9]+',s))


def match_request(body, catalog):
    """Require exact, unique public product title and a request for a price.

    Do not silently answer requests for comparisons, cheapest sellers, stock,
    availability, delivery or other claims with one observed product price.
    """
    if not isinstance(body,str) or len(body)>500 or re.search(r'https?://|@|[<>`{}\[\]]',body):
        return None
    text=normalize(body)
    if not re.search(r'\b(price|cost|costs|priced|much)\b',text):
        return None
    if not ('?' in body or re.search(r'\b(please|check|what|how|show|find|tell|can|could)\b',text)):
        return None
    if re.search(r'\b(no|not|never|dont|do not)\b',text):
        return None
    if re.search(r'\b(compare|comparison|versus|vs|cheapest|cheaper|lowest|best|between|stock|available|availability|delivery|deliver|delivered|saving|savings|discount|deal|deals)\b',text):
        return None
    matches=[]
    for product_id,name in catalog:
        canonical=normalize(name)
        if len(canonical)<12 or len(canonical.split())<3:
            continue
        if re.search(r'(?<![a-z0-9])'+re.escape(canonical)+r'(?![a-z0-9])',text):
            matches.append((len(canonical),str(product_id),canonical))
    if not matches:
        return None
    longest=max(x[0] for x in matches)
    ids={x[1] for x in matches if x[0]==longest}
    return next(iter(ids)) if len(ids)==1 else None


class Meta(HTMLParser):
    def __init__(self):super().__init__();self.values={}
    def handle_starttag(self,tag,attrs):
        if tag.lower()!='meta':return
        attrs=dict(attrs); key=(attrs.get('property') or attrs.get('name') or '').lower()
        if key in ('og:title','product:price:amount','product:price:currency'):
            self.values.setdefault(key,[]).append(attrs.get('content',''))


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urllib.parse.urlsplit(newurl)
        if parsed.scheme!='https' or parsed.hostname not in (ALLOWED_HOST,'www.'+ALLOWED_HOST):
            raise ValueError('Unexpected retailer redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def get(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in ('www.cwhereucheaper.co.za',ALLOWED_HOST,'www.'+ALLOWED_HOST):
        raise ValueError('Unexpected source domain')
    opener=urllib.request.build_opener(SafeRedirect())
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; CWhereUCheaper research)'})
    with opener.open(req,timeout=25) as r:
        if r.status!=200:raise ValueError('Unavailable source')
        data=r.read(2_000_001)
    if len(data)>2_000_000:raise ValueError('Source too large')
    return data


def research(product_id, fetch=None, now=None):
    if not re.fullmatch(r'[1-9][0-9]{0,9}',str(product_id)):
        raise ValueError('Invalid public product id')
    fetch=fetch or get; now=now or dt.datetime.now(dt.timezone.utc)
    data=json.loads(fetch(ORIGIN+'/reels/api/shopping-opportunities?product_id='+str(product_id)))
    rows=data.get('opportunities')
    if not isinstance(rows,list) or len(rows)!=1:raise ValueError('Product evidence unavailable')
    item=rows[0]
    if str(item.get('product_id'))!=str(product_id):raise ValueError('Product mismatch')
    parsed=urllib.parse.urlsplit(item.get('url',''))
    if parsed.scheme!='https' or parsed.hostname not in (ALLOWED_HOST,'www.'+ALLOWED_HOST) or parsed.username or parsed.password:
        raise ValueError('Retailer not supported')
    if normalize(item.get('retailer',''))!='superbhyper':raise ValueError('Retailer mismatch')
    observed=dt.datetime.fromisoformat(item['observed_at'].replace('Z','+00:00'))
    if observed.tzinfo is None or not dt.timedelta(minutes=-5)<=now-observed<=dt.timedelta(hours=2):
        raise ValueError('Catalogue observation stale')
    price=decimal.Decimal(str(item['price']))
    if not price.is_finite() or price<=0 or price>100000 or price.as_tuple().exponent < -2:
        raise ValueError('Invalid price')
    p=Meta();p.feed(fetch(item['url']).decode('utf-8',errors='replace'))
    vals=p.values
    def one(key):
        v=vals.get(key,[])
        if len(set(v))!=1:raise ValueError('Missing or ambiguous product metadata')
        return v[0]
    if one('product:price:currency').upper()!='ZAR' or decimal.Decimal(one('product:price:amount'))!=price:
        raise ValueError('Retailer price not confirmed')
    title=normalize(one('og:title')); product=normalize(item.get('product',''))
    if not product or not title.startswith(product+' '):
        raise ValueError('Retailer product title not confirmed')
    timestamp=now.astimezone(SAST)
    return {'product_id':str(product_id),'product':item['product'],'retailer':'Superb Hyper',
            'price':format(price,'.2f'),'url':item['url'],'checked_sast':timestamp.isoformat()}


def build(evidence):
    checked=dt.datetime.fromisoformat(evidence['checked_sast'])
    date=checked.strftime('%d %B %Y'); time=checked.strftime('%H:%M')
    product=evidence['product']; retailer=evidence['retailer']; price=evidence['price']
    return {'title':'Price check: '+product,
      'script':f"On {date}, at {time}, the {retailer} product page listed {product} at R{price}. That is the item price before delivery or other charges. Prices and availability can change, so check the retailer page before you buy.",
      'caption':f"Price check at {time} SAST on {date}: {retailer} displayed {product} at R{price}. Item price only; delivery and availability may change. Verify before buying: {evidence['url']}",
      'style':'Educational','theme':'shopping-check','growth_hashtags':'#PriceCheck #SmartShopping #SouthAfrica',
      'creative_version':'creative-v2','evidence_checked_sast':evidence['checked_sast']}
