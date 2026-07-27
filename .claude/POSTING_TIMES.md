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

| Day | Slot 1 | Slot 2 | Notes |
|---|---|---|---|
| Mon | 07:00 | 11:30 | |
| Tue | 07:00 | 11:30 | strongest day |
| Wed | 07:00 | 11:30 | strongest day |
| Thu | 07:00 | 11:30 | strong |
| Fri | 07:00 | - | drops after midday |
| Sat | 09:30 | - | light |
| Sun | 16:00 | - | light; evening browse |

Reasoning: the audience is US accountants, controllers and fractional CFOs, weighted to Eastern. 07:00 CT = 08:00 ET, the morning scroll before the workday. 11:30 CT = 12:30 ET, lunch. Tue-Thu outperform Mon/Fri for B2B.

### X (@JosephTFrench, Premium)

| Day | Slot 1 | Slot 2 | Notes |
|---|---|---|---|
| Mon-Fri | 07:30 | 14:45 | pre-market (08:30 ET) and into the close (15:45 ET) |
| Sat | 09:30 | 13:00 | weekends hold up for finance/AI content |
| Sun | 09:30 | 16:00 | |

Reasoning: a finance audience clusters around the trading day. The existing Buffer defaults bunched everything into 08:00-12:00 CT, which misses the close entirely.

## Confidence, and when to revisit

**This table is convention plus audience reasoning, not our data.** LinkedIn has n=2 posts ever, so there is no signal to fit to. X has directional per-post impressions via `just insights`, but not enough to separate a timing effect from a content effect.

Treat it as the starting prior. Once the volume cadence has run ~3 weeks, there will be enough posts at enough times to tune it - hold content type roughly constant and compare slots. Update this file when that happens, and note the date and n.

## Plan limits (checked live 2026-07-26)

| Limit | Value | Bites? |
|---|---|---|
| Daily posting, LinkedIn | 50/day | no |
| Daily posting, X | 100/day | no |
| **Org `scheduledPosts`** | **10** | **yes** |

The 10-post scheduled cap is the Buffer plan limit and it is the binding constraint on a volume cadence. At 1-2 items/day/channel the week needs 14-28 scheduled posts. Free-tier Buffer cannot hold a week of queue. **A paid plan is a prerequisite for the volume plan**, not an optimization. Check headroom with `list_posts(status:["scheduled"])` before any large scheduling run and say so if the selection would exceed it.
