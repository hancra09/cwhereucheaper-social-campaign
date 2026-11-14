import json
from pathlib import Path
from comparison_response import match_request,research,build
from creative_engine import render_video
fake='Please compare 20kg Ideal Adult Dog Food at Animals First and Turf Hyper?'
subject=match_request(fake,[(14535,'20kg Ideal Adult Dog Food',30273,'IDEAL ADULT DOG FOOD 20KG')]);assert subject=='14535-30273'
evidence=research(subject);item=build(evidence);item['response_request_id']='d'*32
work=Path('synthetic-output');work.mkdir(exist_ok=True)
(work/'SYNTHETIC-TEST.json').write_text(json.dumps({'test_input':fake,'evidence':evidence,'content':item,'published':False},indent=2)+'\n')
render_video(item,'synthetic-comparison-test',work/'synthetic-comparison-response.mp4',work)
