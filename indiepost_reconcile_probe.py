import json
from indiepost_fallback import call
result=call('posts')
print('Provider response shape:', list(result) if isinstance(result,dict) else type(result).__name__)
rows=result.get('posts',[]) if isinstance(result,dict) else result
for row in rows:
    print(json.dumps({k:row.get(k) for k in ('id','postGroupId','caption','status','createdAt','platforms')},ensure_ascii=False))
