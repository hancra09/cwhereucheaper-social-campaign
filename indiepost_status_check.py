import campaign,json
from indiepost_fallback import call
r=campaign.read_release('indiepost-delivery-video-20261114');state=json.loads(r['body'])
for service in ('tiktok','facebook'):
    row=state['platforms'].get(service,{})
    ident=row.get('indiepost_fallback',{}).get(service,{}).get('post_group_id')
    if not ident:print(service,'no group');continue
    details=call('posts/'+ident)
    print(json.dumps({'platform':service,'status':details.get('status'),'posts':details.get('posts',[])},ensure_ascii=False))
