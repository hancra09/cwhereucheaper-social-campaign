import json
from pathlib import Path
from response import select,research,build
from creative_engine import render_video
fake='Please show how to compare unit prices?'
topic=select(fake);assert topic=='unit_price_v1'
evidence=research(topic=topic);item=build(topic,evidence);item['response_request_id']='e'*32
work=Path('synthetic-output/unit');work.mkdir(parents=True,exist_ok=True)
(work/'SYNTHETIC-TEST.json').write_text(json.dumps({'test_input':fake,'evidence':evidence,'content':item,'published':False},indent=2)+'\n')
render_video(item,'synthetic-unit-test',work/'synthetic-unit-response.mp4',work)
