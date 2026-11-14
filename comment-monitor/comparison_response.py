"""Compare two explicitly requested retailers only when both product pages agree."""
import datetime as dt
import hashlib
import json
import re
from product_response import normalize, research as product_research

SAST=dt.timezone(dt.timedelta(hours=2))


def same_product(a,b):
    left=normalize(a).split(); right=normalize(b).split()
    return len(left)>=4 and sorted(left)==sorted(right)


def match_request(body,pairs):
    if not isinstance(body,str) or len(body)>500 or re.search(r'https?://|@|[<>`{}\[\]]',body):return None
    text=normalize(body)
    if not re.search(r'\b(compare|comparison|versus|vs|cheaper)\b',text):return None
    if not re.search(r'\banimals\s*first\b',text) or not re.search(r'\bturf\s*(?:pet\s*)?hyper\b',text):return None
    if re.search(r'\b(no|not|never|dont|delivery|delivered|stock|availability|discount|saving|savings)\b',text):return None
    found=[]
    for left_id,left_name,right_id,right_name in pairs:
        if not same_product(left_name,right_name):continue
        names={normalize(left_name),normalize(right_name)}
        if any(re.search(r'(?<![a-z0-9])'+re.escape(n)+r'(?![a-z0-9])',text) for n in names):
            found.append((max(map(len,names)),str(left_id)+'-'+str(right_id)))
    if not found:return None
    longest=max(x[0] for x in found);matches={x[1] for x in found if x[0]==longest}
    return next(iter(matches)) if len(matches)==1 else None


def signature(items):
    values=[{k:item[k] for k in ('product_id','product','retailer','price','url')} for item in items]
    return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def research(subject,fetch=None,now=None):
    if not re.fullmatch(r'[1-9][0-9]{0,9}-[1-9][0-9]{0,9}',subject or ''):
        raise ValueError('Invalid comparison subject')
    first,second=subject.split('-')
    items=[product_research(first,fetch,now),product_research(second,fetch,now)]
    if [x['retailer'] for x in items]!=['Animals First','Turf Pet Hyper']:
        raise ValueError('Unexpected retailers')
    if not same_product(items[0]['product'],items[1]['product']):
        raise ValueError('Product identity does not match')
    return {'subject':subject,'items':items,'checked_sast':max(x['checked_sast'] for x in items),'signature':signature(items)}


def build(evidence):
    a,b=evidence['items'];when=dt.datetime.fromisoformat(evidence['checked_sast']); date=when.strftime('%d %B %Y');time=when.strftime('%H:%M')
    name=a['product'];
    if len(name)>65:raise ValueError('Product name too long')
    return {'title':'R'+a['price']+' vs R'+b['price']+': '+name,
      'script':f"On {date}, Animals First listed {name} for R{a['price']}. Turf Pet Hyper listed the same item for R{b['price']}. These are item prices at those two stores before delivery. Prices and availability can change, so check both pages before buying.",
      'caption':f"Two-store check at {time} SAST on {date}: {name}. Animals First: R{a['price']}; Turf Pet Hyper: R{b['price']}. Item prices only; delivery and availability may change. Sources: {a['url']} {b['url']}",
      'style':'Educational','theme':'shopping-check','growth_hashtags':'#PriceComparison #SmartShopping #SouthAfrica','creative_version':'creative-v2',
      'evidence_checked_sast':evidence['checked_sast'],'evidence_comparison_subject':evidence['subject'],'evidence_comparison_signature':evidence['signature']}
