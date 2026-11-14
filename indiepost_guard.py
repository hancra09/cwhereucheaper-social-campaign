"""Conservative eligibility for an automatic secondary publisher.

A Buffer error alone is not proof that a post failed to publish. Only the
specific lost-authorization errors documented by Buffer qualify. Unknown
states and mismatched records must never trigger a backup post.
"""
import datetime as dt

LOST_AUTH = {
    "it looks like buffer has lost authorization to post on your behalf. no need to worry, though! here are the steps to re-authorize buffer.",
    "it looks like buffer has lost the authorization to post to this account. please reauthorize and try again. if the issue persists, please get in touch! here are the steps to refresh your connection.",
    "it looks like buffer has lost authorization to post to this social account. please reauthorize and try again. if the issue persists, please get in touch!",
}

def eligible(ledger, service, rows, now):
    if service not in ('tiktok', 'youtube', 'facebook') or now.tzinfo is None:
        return False
    content = ledger.get('content') or {}
    if content.get('evidence_product_id') or content.get('evidence_comparison_subject'):
        return False
    try:
        due = dt.datetime.fromisoformat(ledger['due_sast'])
        recorded = ledger['posts'][service]['id']
    except (TypeError, KeyError, ValueError):
        return False
    if due.tzinfo is None or not recorded or now < due + dt.timedelta(minutes=20):
        return False
    if not isinstance(rows, list) or len(rows) != 1:
        return False
    row = rows[0]
    message = (row.get('error') or {}).get('message')
    if not isinstance(message, str):
        return False
    return (row.get('id') == recorded and row.get('status') == 'error'
            and not row.get('externalLink') and message.strip().casefold() in LOST_AUTH)
