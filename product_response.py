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
HOSTS={'superbhyper.co.za':('superbhyper','Superb Hyper'),'mopani.co.za':('mopani','Mopani'),'animalsfirst.co.za':('animalsfirst','Animals First'),'turfhyper.co.za':('turfhyper','Turf Pet Hyper')}
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
    def __init__(self):super().__init__();self.values={};self.scripts=[];self.script=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag.lower()=='script' and attrs.get('type','').lower()=='application/ld+json':
            self.script=[];return
        if tag.lower()!='meta':return
        key=(attrs.get('property') or attrs.get('name') or '').lower()
        if key in ('og:title','product:price:amount','product:price:currency'):
            self.values.setdefault(key,[]).append(attrs.get('content',''))
    def handle_data(self,data):
        if self.script is not None:self.script.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=='script' and self.script is not None:
            self.scripts.append(''.join(self.script));self.script=None


def structured_price(page,url,product):
    target=urllib.parse.urlsplit(url)
    found=[]
    for raw in page.scripts:
        try: data=json.loads(raw)
        except (ValueError,TypeError): continue
        graph=data.get('@graph',[data]) if isinstance(data,dict) else data
        if not isinstance(graph,list):continue
        for node in graph:
            if not isinstance(node,dict) or node.get('@type')!='Product' or normalize(str(node.get('name','')))!=normalize(product):continue
            ident=urllib.parse.urlsplit(str(node.get('@id','')))
            if ident.hostname!=target.hostname or ident.path.rstrip('/')!=target.path.rstrip('/'):continue
            offers=node.get('offers',[]);offers=offers if isinstance(offers,list) else [offers]
            for offer in offers:
                if not isinstance(offer,dict):continue
                dest=urllib.parse.urlsplit(str(offer.get('url','')))
                if dest.hostname!=target.hostname or dest.path.rstrip('/')!=target.path.rstrip('/'):continue
                if str(offer.get('priceCurrency','')).upper()!='ZAR' or not str(offer.get('availability','')).endswith('/InStock'):continue
                try: found.append(decimal.Decimal(str(offer['price'])))
                except (KeyError,decimal.InvalidOperation):continue
    if len(set(found))!=1:raise ValueError('Missing or ambiguous product offer')
    return found[0]


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urllib.parse.urlsplit(newurl)
        if parsed.scheme!='https' or parsed.hostname not in {h for host in HOSTS for h in (host,'www.'+host)}:
            raise ValueError('Unexpected retailer redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def get(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in {'www.cwhereucheaper.co.za',*(h for host in HOSTS for h in (host,'www.'+host))}:
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
    if parsed.scheme!='https' or parsed.hostname not in {h for host in HOSTS for h in (host,'www.'+host)} or parsed.username or parsed.password:
        raise ValueError('Retailer not supported')
    host=parsed.hostname.removeprefix('www.')
    retailer_code,retailer_display=HOSTS[host]
    if normalize(item.get('retailer',''))!=retailer_code:raise ValueError('Retailer mismatch')
    observed=dt.datetime.fromisoformat(item['observed_at'].replace('Z','+00:00'))
    if observed.tzinfo is None or not dt.timedelta(minutes=-5)<=now-observed<=dt.timedelta(hours=6):
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
    if host in ('animalsfirst.co.za','turfhyper.co.za'):
        actual_price=structured_price(p,item['url'],item.get('product',''))
    else:
        if one('product:price:currency').upper()!='ZAR':raise ValueError('Unexpected currency')
        actual_price=decimal.Decimal(one('product:price:amount'))
    if actual_price!=price:raise ValueError('Retailer price not confirmed')
    title=normalize(one('og:title')); product=normalize(item.get('product',''))
    if not product or not (title==product or title.startswith(product+' ')):
        raise ValueError('Retailer product title not confirmed')
    timestamp=now.astimezone(SAST)
    return {'product_id':str(product_id),'product':item['product'],'retailer':retailer_display,
            'price':format(price,'.2f'),'url':item['url'],'checked_sast':timestamp.isoformat()}


def build(evidence):
    checked=dt.datetime.fromisoformat(evidence['checked_sast'])
    date=checked.strftime('%d %B %Y'); time=checked.strftime('%H:%M')
    product=evidence['product']; retailer=evidence['retailer']; price=evidence['price']
    if len(product)>70:raise ValueError('Product title is too long for a clear video')
    return {'title':'R'+price+': '+product,
      'script':f"On {date}, the {retailer} product page listed {product} at R{price}. That is the item price before delivery or other charges. Prices and availability can change, so check the retailer page before you buy.",
      'caption':f"Price check at {time} SAST on {date}: {retailer} displayed {product} at R{price}. Item price only; delivery and availability may change. Verify before buying: {evidence['url']}",
      'style':'Educational','theme':'shopping-check','growth_hashtags':'#PriceCheck #SmartShopping #SouthAfrica',
      'creative_version':'creative-v2','evidence_checked_sast':evidence['checked_sast'],
      'evidence_product_id':evidence['product_id'],'evidence_price':price,
      'evidence_product':product,'evidence_retailer':retailer,'evidence_url':evidence['url']}
