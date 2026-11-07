# CWhereUCheaper cloud video campaign

Owner-authorized promotional campaign for https://www.cwhereucheaper.co.za.

8 November–7 December 2026 inclusive: 90 distinct videos, each submitted to TikTok `@cwhereucheaper.co` and YouTube `@CwhereUcheaper`. Trial publication slots: **08:00, 12:30 and 18:30 SAST**. These are not established audience peaks. GitHub scheduled runs are best effort and can be delayed.

The standard GitHub-hosted runner calls the existing Reels creator as a normal guest, respects its generation limits, validates the resulting MP4 and puts only the intended-public promotional video in a public release. Buffer retrieves that public file and automatically publishes it. The Buffer key is an encrypted repository secret, not source code. No application source, business certificate, browser session, private account document or local machine is required.

The 90 scripts are original shopping education. Arithmetic is explicitly illustrative. The campaign makes no unverified retailer price, savings, stock or cheapest-price claim. All videos disclose AI narration, use the creator's original motion graphics, and set platform AI flags. There is no music or uploaded third-party media.

Cloud preparation runs at 06:53, 11:23 and 17:23 SAST; publication checks run at 08:20, 12:50 and 18:50 SAST. Rendering is bounded to 20 minutes. Failed render or unknown send state stops safely. Slot-specific release ledgers, exact live caption reconciliation, and a single concurrency group prevent ordinary reruns from duplicating posts. An uncertain send with no reconcilable post requires investigation rather than a blind retry. Native GitHub failed-run notifications report failures according to the account's notification settings.

The workflow is bounded by date and disables itself after the final day's audit. The publishing key expires on 6 January 2027; the campaign guard stops publishing after 7 December. Revoke the key in Buffer to terminate access sooner. Disable the workflow in GitHub Actions to pause future creation; posts already in Buffer's queue must be reviewed separately.

Manual actions: `preflight` is read-only, `bootstrap` prepares the first campaign slot, `audit` checks live Buffer state. `smoke` is restricted to 7 November 2026 and publishes a separate test video. This repository is public by owner authorization.
