# Posting times - the shared slot table

**Date**: 2026-07-26 · Read by `/buffer-draft-li`, `/buffer-draft-blog`, and anything else that schedules through Buffer.

## Why this file exists

**Buffer's built-in posting schedule cannot be changed through the API.** The GraphQL surface exposes `Channel.postingSchedule` as read-only; the only mutations are `createPost` / `editPost` / `deletePost` / `movePostInQueue` / templates / ideas. `managePostingSchedule` appears in `allowedActions` but has no corresponding mutation, so it is a Buffer-UI-only action.

The default slots Buffer generated are bad - LinkedIn at Mon 21:41, Tue 21:12, Sun 22:17 is dead air for a B2B audience.

**So we do not use the queue.** Every scheduled post goes out as `mode: "customScheduled"` with an explicit `dueAt`, computed from the table below. Buffer's slot grid is bypassed entirely, which is strictly better than fixing it: timing becomes a per-post variable we control and can test, rather than a fixed grid.

`mode: "addToQueue"` is now **wrong** for this repo. Do not use it.

## The table

Account timezone is **America/Chicago**. All times CT. Build `dueAt` as ISO 8601 with the CT offset (`-05:00` during CDT, `-06:00` during CST) and confirm it is in the future.

### LinkedIn (Joseph French, personal)

**Revised 2026-07-27 against actual post history (n=8). The 07:00 slot is retired.**

| Day | Slot 1 | Slot 2 | Notes |
|---|---|---|---|
| Mon-Fri | **12:30** | 14:30 | the measured band |
| Sat | 09:30 | - | light, untested |
| Sun | 16:00 | - | light, untested |

**One post per day while the account recovers from dormancy.** Use slot 2 only when there is a reason to run two, and never within three hours of slot 1.

What the history says. Every LinkedIn post with metrics, by send time CT:

| Impressions | Time CT |
|---|---|
| 3,557 | 11:48 |
| 2,273 | 14:57 |
| 1,998 | 13:12 |
| 1,378 | 13:33 |
| 1,374 | 13:16 |
| 1,220 | 08:00 |
| 688 | 23:43 |
| **91** | **07:00** |

Five of the top six land between 11:45 and 15:00. The old 07:00 prior came from "08:00 ET, the morning scroll before the workday" reasoning, and the one post ever sent at 07:00 returned 91 impressions against an account median around 1,300.

**Read this honestly: content is confounded with time here.** The 91 was also the weakest post the account has published (an observation with no argument in it), and it ran after three weeks of dormancy, which LinkedIn punishes on its own. So 07:00 is not proven bad. What is true is that the midday band has five independent successes and 07:00 has zero, so the prior should sit where the evidence is until something separates them.

### X (@JosephTFrench, Premium)

| Day | Slot 1 | Slot 2 | Notes |
|---|---|---|---|
| Mon-Fri | 07:30 | 14:45 | pre-market (08:30 ET) and into the close (15:45 ET) |
| Sat | 09:30 | 13:00 | weekends hold up for finance/AI content |
| Sun | 09:30 | 16:00 | |

Reasoning: a finance audience clusters around the trading day. The existing Buffer defaults bunched everything into 08:00-12:00 CT, which misses the close entirely.

## Confidence, and when to revisit

**LinkedIn times are now fitted to n=8 real posts (revised 2026-07-27). X times are still convention** - the X cuts carry no per-post metrics in Buffer, so `just insights` is the only source there and it has not accumulated enough to separate timing from content.

The LinkedIn fit is weak evidence, not proof: eight posts, unequal content quality, and one long dormancy gap. Re-check after ~3 weeks of the daily cadence, when there are enough posts in each slot to hold content type roughly constant. Update this file with the date and n each time.

**The bigger lever is content register, not timing.** Same account, same audience: posts that open with an argument about the world ("XBRL was supposed to make financial data machine-readable 15 years ago") ran 1,200-3,600. Posts that open with an observation about the author's own work ran 91. That is a larger spread than any slot difference in the table above, so do not spend effort tuning times while the copy is still observational. See the register rules in `/atomize`.

## Plan limits (checked live 2026-07-26)

| Limit | Value | Bites? |
|---|---|---|
| Daily posting, LinkedIn | 50/day | no |
| Daily posting, X | 100/day | no |
| Org `scheduledPosts` | **5000** (paid, re-checked 2026-07-27) | no |

The scheduled cap was 10 on the free tier and was the binding constraint on the volume plan. The upgrade removed it - nothing in Buffer limits the cadence now. **The constraint is supply of good copy, not queue capacity.**
