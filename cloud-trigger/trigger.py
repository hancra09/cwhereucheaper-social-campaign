#!/usr/bin/env python3
"""Independent cloud clock. Credential restricted to campaign Actions only."""
import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.request

REPO = 'hancra09/cwhereucheaper-social-campaign'
WORKFLOW = 'campaign.yml'
SAST = dt.timezone(dt.timedelta(hours=2))
STATE = Path('/var/lib/cwhereu-social-trigger/status.json')


def action(now):
    local = now.astimezone(SAST)
    hm = (local.hour, local.minute)
    if hm in ((8, 20), (12, 50), (18, 50)):
        return 'audit'
    if local.weekday() == 6 and hm == (19, 10):
        return 'review'
    return 'prime'


def running(runs):
    return any(r['status'] in ('queued', 'in_progress', 'waiting', 'pending', 'requested') for r in runs)


def defer(runs, mode):
    # Preparation can wait; delivery audits/reviews must queue behind active work.
    return mode == 'prime' and running(runs)


def api(path, token, payload=None):
    req = urllib.request.Request('https://api.github.com/repos/' + REPO + '/actions/' + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json', 'User-Agent': 'CWUC-Independent-Cloud-Clock/1',
            'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read()
        return json.loads(data) if data else None


def main():
    now = dt.datetime.now(dt.timezone.utc)
    mode = action(now)
    stamp = now.strftime('%Y%m%dT%H%M')
    marker = 'oracle-' + stamp
    token = (Path(os.environ['CREDENTIALS_DIRECTORY']) / 'github-token').read_text().strip()
    if not token:
        raise RuntimeError('Missing restricted trigger credential')
    prior = json.loads(STATE.read_text()) if STATE.exists() else {}
    if prior.get('marker') == marker:
        print('Already attempted this minute; no duplicate dispatch.')
        return
    runs = api('workflows/' + WORKFLOW + '/runs?per_page=20', token)['workflow_runs']
    if defer(runs, mode):
        print('Campaign already active; no overlapping dispatch.')
        return
    record = {'marker': marker, 'mode': mode, 'attempted_at_utc': now.isoformat(),
        'state': 'dispatch_result_unknown'}
    # Persist before sending. A network timeout must not cause blind duplication.
    STATE.write_text(json.dumps(record, indent=2) + '\n')
    api('workflows/' + WORKFLOW + '/dispatches', token,
        {'ref': 'main', 'inputs': {'mode': mode, 'dispatch_id': marker}})
    record['state'] = 'accepted'
    STATE.write_text(json.dumps(record, indent=2) + '\n')
    for _ in range(6):
        runs = api('workflows/' + WORKFLOW + '/runs?event=workflow_dispatch&per_page=10', token)['workflow_runs']
        match = next((r for r in runs if marker in r['display_title']), None)
        if match:
            record.update({'state': 'run_observed', 'run_id': match['id'], 'run_url': match['html_url']})
            STATE.write_text(json.dumps(record, indent=2) + '\n')
            print(json.dumps(record))
            return
        time.sleep(5)
    print(json.dumps(record))


if __name__ == '__main__':
    main()
