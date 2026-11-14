import json
from pathlib import Path
from product_response import match_request,research,build
from creative_engine import render_video
fake='Please check the price of Rhodes Guava Nectar Juice 1lt?'
pid=match_request(fake,[(23895,'Rhodes Guava Nectar Juice 1lt')]);assert pid=='23895'
evidence=research(pid);item=build(evidence);item['response_request_id']='f'*32
work=Path('synthetic-output');work.mkdir(exist_ok=True)
(work/'SYNTHETIC-TEST.json').write_text(json.dumps({'test_input':fake,'evidence':evidence,'content':item,'published':False},indent=2)+'\n')
render_video(item,'synthetic-product-test',work/'synthetic-product-response.mp4',work)
