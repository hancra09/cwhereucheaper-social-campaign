import json, os, urllib.request
req=urllib.request.Request("https://www.indiepost.app/api/v1/accounts",headers={"Authorization":"Bearer "+os.environ["INDIEPOST_API_KEY"]})
with urllib.request.urlopen(req,timeout=20) as r: data=json.load(r)
accounts=[a for w in data.get("workspaces",[]) for a in w.get("accounts",[])]
print(json.dumps({p: any(a.get("platform")==p and a.get("connected") is True for a in accounts) for p in ("tiktok","youtube","facebook")}))
# Exercise media transfer only. Never create a post in this check.
url='https://github.com/hancra09/cwhereucheaper-social-campaign/releases/download/20261115-am/video-creative-v2.mp4'
with urllib.request.urlopen(url, timeout=45) as r: content=r.read(10_000_001)
if len(content)>10_000_000 or len(content)<1000: raise RuntimeError('Unexpected test media size')
def post(path, body):
    req=urllib.request.Request('https://www.indiepost.app/api/v1/'+path,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+os.environ['INDIEPOST_API_KEY'],'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=45) as r: return json.load(r)
info=post('media',{'filename':'cwuc-backup-transfer-test.mp4','mimeType':'video/mp4','size':len(content)})
u=info['upload']['url']
if not u.startswith('https://'):raise RuntimeError('Non-HTTPS upload refused')
req=urllib.request.Request(u,data=content,headers={'Content-Type':'video/mp4'},method='PUT')
with urllib.request.urlopen(req,timeout=60) as r:
    if r.status not in (200,201,204):raise RuntimeError('Media upload rejected')
post('media/confirm',{'mediaId':info['mediaId']})
print('Video transfer confirmed; no post created')
