import json, os, urllib.request
req=urllib.request.Request("https://www.indiepost.app/api/v1/accounts",headers={"Authorization":"Bearer "+os.environ["INDIEPOST_API_KEY"]})
with urllib.request.urlopen(req,timeout=20) as r: data=json.load(r)
accounts=[a for w in data.get("workspaces",[]) for a in w.get("accounts",[])]
print(json.dumps({p: any(a.get("platform")==p and a.get("connected") is True for a in accounts) for p in ("tiktok","youtube","facebook")}))
