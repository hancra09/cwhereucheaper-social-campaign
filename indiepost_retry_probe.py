import campaign,json,hashlib,urllib.error
from indiepost_fallback import payload,submit,key_for
TAG='indiepost-delivery-video-20261114'
r=campaign.read_release(TAG);state=json.loads(r['body']);ledger=state['platforms']['youtube'];s=ledger['indiepost_fallback']['youtube']
if s.get('phase')!='sending':raise RuntimeError('Unexpected submission state; stop')
row={'text':ledger['posts']['youtube']['text']};data=payload(ledger,'youtube',row,s['media_id'])
if hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()!=s['request_digest']:raise RuntimeError('Request differs; stop')
try:result=submit(data,key_for(TAG,'youtube'))
except urllib.error.HTTPError as e:
    print(json.dumps({'http':e.code,'retry_after':e.headers.get('Retry-After'),'body':e.read(2000).decode('utf-8','replace')}),flush=True)
    raise
print('Provider response:',json.dumps(result),flush=True)
if not result.get('postGroupId'):raise RuntimeError('No group id; stop')
s.update({'phase':'submitted','post_group_id':result['postGroupId']})
campaign.gh('releases/'+str(r['id']),{'body':json.dumps(state,sort_keys=True)},'PATCH')
