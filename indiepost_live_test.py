"""One-shot delivery-fee campaign post with simulated failover. Never run twice."""
import datetime as dt, json, time
import campaign
from indiepost_guard import LOST_AUTH
from indiepost_fallback import recover, call

TAG='indiepost-delivery-video-20261114'
release=campaign.read_release(TAG)
if not release:raise RuntimeError('Test release is missing')
try: old=json.loads(release.get('body') or '{}')
except ValueError: old={}
if old.get('test_started'):raise RuntimeError('Test already started; reconcile existing state')
state={'test_started':True,'simulated_failure':True,'platforms':{}}
def save_state():
    campaign.gh('releases/'+str(release['id']), {'body':json.dumps(state,sort_keys=True)}, 'PATCH')
save_state()
now=dt.datetime.now(dt.timezone.utc)
video='https://github.com/hancra09/cwhereucheaper-social-campaign/releases/download/'+TAG+'/humour-sample.mp4'
message=next(iter(LOST_AUTH))
for service in ('youtube','tiktok','facebook'):
    channel=campaign.CHANNELS[service]
    caption=('Found the cheapest price? Delivery says: hold my receipt 😂 🛒\n\n'
             'A lower sticker price can cost more by the time it reaches your door. '
             'These numbers are an illustration, not current offers.\n\n'
             'What is your biggest checkout surprise? Tell us below.\n'
             'Compare before checkout: https://www.cwhereucheaper.co.za\n'
             'AI narration and illustrative visuals. #ShoppingTips #SouthAfrica #OnlineShopping #CWhereUCheaper')
    item={'title':'Delivery fee plot twist'}
    row={'id':'simulated-'+service,'channelId':channel,'status':'error','error':{'message':message},'externalLink':'','text':caption}
    ledger={'slot':TAG,'due_sast':(now-dt.timedelta(minutes=21)).isoformat(),'posts':{service:{'id':row['id'],'text':caption}},'content':item,'video':video}
    state['platforms'][service]=ledger
    save_state()
    def save(_):save_state()
    result=recover(ledger,service,channel,lambda:[row],save,now)
    print(json.dumps({'platform':service,'result':result,'group':ledger.get('indiepost_fallback',{}).get(service,{}).get('post_group_id')}),flush=True)
    if result!='submitted':raise RuntimeError('Test did not reach submitted state')
    ident=ledger['indiepost_fallback'][service]['post_group_id']
    for _ in range(12):
        details=call('posts/'+ident)
        statuses=[{'platform':p.get('platform'),'status':p.get('status'),'externalPostId':p.get('externalPostId')} for p in details.get('posts',[])]
        state['platforms'][service]['provider_status']={'status':details.get('status'),'posts':statuses}
        save_state()
        if statuses and all(p.get('status') in ('posted','failed','error') for p in statuses):break
        time.sleep(10)
    print(json.dumps({'platform':service,'provider':state['platforms'][service]['provider_status']}),flush=True)
