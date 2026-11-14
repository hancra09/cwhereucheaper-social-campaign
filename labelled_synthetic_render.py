import json
from pathlib import Path
from response import select,research,build
from creative_engine import render_video
fake='Please show how to compare unit prices?'
topic=select(fake);assert topic=='unit_price_v1'
evidence=research(topic=topic);item=build(topic,evidence)
item.update({'response_request_id':'e'*32,'synthetic_test':True})
item['caption']='TEST VIDEO: Based on a simulated viewer request. '+item['caption']
work=Path('synthetic-output');work.mkdir(exist_ok=True)
(work/'SYNTHETIC-TEST.json').write_text(json.dumps({'test_input':fake,'content':item,'published':False},indent=2)+'\n')
render_video(item,'labelled-synthetic-test',work/'labelled-synthetic-response.mp4',work)
