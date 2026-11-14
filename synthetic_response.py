import json
from pathlib import Path
import response
from creative_engine import render_video

fake='Please show how delivery fees can change which basket is cheaper?'
topic=response.select(fake)
assert topic, 'Synthetic request was not recognised'
evidence=response.research()
item=response.build(topic,evidence)
work=Path('synthetic-output');work.mkdir(exist_ok=True)
(work/'SYNTHETIC-TEST.json').write_text(json.dumps({'test_input':fake,'topic':topic,'evidence':evidence,'content':item,'published':False},indent=2)+'\n')
render_video(item,'synthetic-delivery-test',work/'synthetic-response.mp4',work)
