# CWhereUCheaper ongoing cloud video campaign

Owner-authorized promotion for https://www.cwhereucheaper.co.za.

Three distinct videos daily, each published to TikTok @cwhereucheaper.co, YouTube @CwhereUcheaper and the existing CwhereUcheaper Facebook Page. Publication slots: **08:00, 12:30 and 18:30 SAST**, starting 8 November 2026 and continuing until paused. These are trial times, not proven audience peaks. GitHub scheduled runs can be delayed.

## Content

The original 90 scripts, exact 8 November–7 December mapping, captions and tracking links are preserved. From 8 December, monthly JSON plans supply content. The factory combines curated evergreen shopping lessons with varied original hooks, reminders and calls to action. No paid text API is used. These are controlled variations of reviewed educational material; no daily live market research or unconstrained AI writer is claimed. Scripts make no unverified retailer price, stock, discount or savings claim.

Saved monthly plans have three complete slots per calendar day, unique narration, unique monthly titles and a checksum. Earlier planned narration is excluded from new batches. Current and following month are prepared automatically and saved to this repository. Existing plans remain frozen. A missing or corrupt plan stops publication rather than recycling the first 90. Content selected for a slot is also frozen in its release ledger.

## Creation and publishing

The existing Reels creator produces 25-second 1080×1920 videos with Emma narration and original motion graphics. No music, stock media or browser capture is requested. The workflow respects the guest three-per-day allowance, validates video and narration, then supplies intended-public MP4 files to Buffer. Supported AI flags are set for TikTok/YouTube; Facebook uses its native Reel type. Captions retain the disclosure.

Preparation checks run at **06:53, 11:23 and 17:23 SAST**, plus every two hours at minute 13. They fill future slots 2–48 hours ahead rather than relying on a same-day trigger. Publication checks remain **08:20, 12:50 and 18:50 SAST**. Rendering is bounded to 20 minutes and each workflow to 28 minutes. No campaign end-date or automatic end-date disable remains. Service quotas, valid access and provider availability still apply. No laptop or new recurring subscription is required.

## Reconciliation and weekly review

Publishing checks cover the last seven calendar days. API requests are date-filtered so a growing lifetime history does not exhaust the bound. Historical release ledgers remain available. Exact channel identity, late-slot refusal, pending-send duplicate protection and MP4 validation remain enforced. A missed earlier slot is reported without preventing the next distinct video. Uncertain sends stop for reconciliation instead of blind retries.

Every **Sunday at 19:10 SAST**, an optional review reads Buffer post metrics. It ranks only within the same channel and needs at least three comparable posts aged 48 hours, with metric snapshots refreshed within the last 48 hours. Missing or stale metrics are not used for ranking or treated as zero. Buffer metrics are early and may lag or be unavailable; no website-conversion or guaranteed-growth claim is inferred. Unavailable review signals do not stop publishing.

Public review files contain coarse content themes and already-public example titles/links, never raw private metric values. Useful themes influence at most two of every five slots in newly prepared future plans; the remainder retain variety. Existing planned and queued posts are unchanged.

## Access and operation

BUFFER_API_KEY remains an encrypted GitHub Actions secret with only account:read, posts:read, posts:write and insights:read. publishing-access.json records expiry metadata only. The workflow warns during the final 30 days and refuses expired access. Renew before expiry; Buffer also sends expiry notices. No key value, private certificate, browser session or application source belongs in this repository.

Disable the Cloud video campaign workflow to pause creation. Review Buffer separately for posts already queued. Revoking the key ends the integration's access. Manual preflight validates content, channel identity and reconciliation without rendering or creating social posts. prepare prepares plans only; review performs the optional weekly content check. Smoke mode remains restricted to the already-authorized 7 November 2026 proof and should not be rerun.

Native failed-workflow notifications provide failure notices according to the account's settings. Disconnected channels, provider restrictions and credential renewal may require attention. No new paid service is authorized.

## Scheduler-delay recovery

The 08:00 SAST slot on 8 November 2026 was missed: GitHub had not delivered its preparation trigger. Earlier scheduled runs also arrived hours late. GitHub cron is best effort, so publication time must be held in Buffer ahead of time. The ahead preparer fills one future slot per trigger, always at least two hours before publication, with a 48-hour horizon and at most nine pending posts per channel. A durable daily ledger limits the campaign to three new render attempts per SAST day, including failed/uncertain attempts. Existing video reuse does not consume another render. No missed slot is backdated or flooded into the current queue.

Manual prime can prepare up to three future slots within the same daily budget and workflow deadline. Uncertain sends and unresolved renders stay recorded and are not retried blindly; another distinct safe slot can be prepared. Separate publication audits continue to report the missed 08:00 slot until it leaves their seven-day window. Ahead preparation does not turn that historical failure into a pass. Provider scheduling is still best effort, but prepared Buffer posts no longer depend on a trigger arriving just before publication.

### Media delivery repair — 8 November 2026
TikTok and Facebook rejected the release download URL at publication time while YouTube succeeded. A direct Buffer upload of the same validated 30fps H.264/AAC file recovered both existing posts. Scheduled campaign posts now use a redirect-free public-video-cache branch on raw.githubusercontent.com. Originals remain in GitHub Releases. The isolated cache contains only validated dated campaign MP4s, retains ten days plus upcoming videos, and replaces its own parentless cache snapshot to avoid accumulating MP4 Git history. It never writes application/source branches. No additional account, secret or subscription is required. `refresh-media` edits only future live scheduled posts and checks that IDs, captions, channel, status and publication times are preserved; it creates no posts or renders. The first native scheduled delivery using this route remains to be observed.

## Approved creative-v2 rollout — 12 November 2026

Newly prepared slots use the Owner-approved Heart female AI voice at0.97 speed, natural sentence pauses, six narration-timed scenes, original illustrative product photography, readable comparisons/checklists, light shopping humour and an actual website ending. Original shopping facts and arithmetic are preserved; examples remain explicitly illustrative. No music is introduced. The source lesson plans remain intact; creative narration is derived and recorded in each slot's creative-v2.json.

Authoring runs in the existing public GitHub Actions runner using the same open-source voice family as Reels and the reviewed renderer. This replaces the old repetitive Reels cards without changing the application or using a paid text/voice/video API. The three-new-slots-per-SAST-day budget remains enforced. Re-editing already-created scheduled slots creates no extra slots and does not call or bypass the public Reels job quota. Normal publishing times, channel checks, exact-post-ID reconciliation and no-duplicate guards remain.

`upgrade-creative` edits only exact live scheduled posts with at least20minutes lead, over the next48hours. IDs, dueAt and scheduled status must stay identical. Already published/sending/draft posts are never replaced. AI disclosures update alongside the media. Old MP4s remain in Releases; new `video-creative-v2.mp4` files and versioned public URLs prevent stale cached video delivery. Originals/provenance provide rollback evidence. The updater saves results after every channel change, and refuses uncertain render retries. Existing queued content is bound to its prior lesson facts.
