# Independent cloud clock

Runs on the existing Oracle hosting instance, independently of GitHub's scheduled-event delivery. It dispatches only `hancra09/cwhereucheaper-social-campaign` / `campaign.yml`, with a unique correlation marker. The campaign still executes in GitHub Actions; Buffer retains publication timing. No rendering runs in this timer and no Buffer secret moves onto the server.

Hourly at :07 SAST: prime preparation. Audits at 08:20, 12:50, 18:50 SAST. Weekly content review Sunday 19:10 SAST. One initial automatic trigger 45 seconds after activation. Persistent across reboot. Existing GitHub schedules remain redundant triggers; existing active-run, duplicate-post and daily render limits remain in force.

Needs a fine-grained GitHub key restricted to this one public repository: Actions read/write and mandatory Metadata read, with no Contents or Secrets permission. The credential is encrypted on the existing host with systemd-creds and supplied only to the isolated service. Never copy the operator's broader GitHub OAuth login onto the host. No key value belongs in this repository, logs or handovers.

Install `trigger.py` at `/usr/local/lib/cwhereu-social-trigger/trigger.py` and the units under `/etc/systemd/system/`. Encrypted credential path `/etc/cwhereu-social-trigger/github-token.cred`. State receipts `/var/lib/cwhereu-social-trigger/status.json`. Enable only after the restricted credential is authorized and provisioned. `systemctl disable --now cwhereu-social-trigger.timer` pauses future dispatches; it does not cancel already running GitHub jobs or queued Buffer posts.

Acceptance requires an actual timer-fired dispatch, a matching GitHub run observed, and successful cloud execution. Configuration validation alone is not acceptance. Unknown dispatch results are recorded before sending and are not blindly resent in the same minute. An already active campaign run prevents another dispatch.
