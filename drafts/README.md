# drafts/ — WIP staging for content

The work-in-progress home for content before it's published. The **WIP content here is untracked**
(gitignored like `projects/`) because it churns and a draft can become a blog post *or other content* —
only this README is committed, so the folder and its purpose live in the repo. It's **part of the pipeline**
(the tooling operates on it); nothing here is live until it's promoted/posted. This is the "drafting →
queued" half of the queue; `blog/` and the platforms are "published."

See `local/specs/unified-content-pipeline.md` for the full two-type model. Short version:

## Two ways out of `drafts/`

**1. Technical essay → publish via the blog pipeline (canonical).**
A draft that should live at `robosystems.ai/blog/<slug>` (the canonical home, for SEO ownership):

```
# when the draft is ready, scaffold the publishable post and move the prose in
just blog-new <slug>            # creates blog/<slug>/post.md from the template
#   → move the essay into blog/<slug>/post.md, fill the frontmatter
#   → optional companions: blog/<slug>/<slug>_medium.md, _linkedin.md, _x_post.txt
just blog-social <slug>         # paste-ready pack: Medium (canonical→blog) + LinkedIn + X
just blog-publish <slug>        # → s3://…/blog/<slug>/ + blog/index.json (auto-narrates)
```

Medium is **syndication**, not a peer: set its canonical URL to the blog post on import so we never
cannibalize our own SEO. LinkedIn/X are native short derivatives (no canonical, no in-body link).

**2. Standalone social post → post natively from the draft (no blog).**
Some pieces are deliberately single-platform and never become a blog post — e.g. `linkedin.md` (a queue of
short LinkedIn posts) or the launch X/Reddit/HN posts in `archive/`. Draft them here, post them natively.
Don't force a blog canonical onto these.

## Draft campaigns (`campaigns/`)

`drafts/campaigns/<vertical>.md` holds **draft research-coverage plans** (the verticals — ai-capex,
glp1-obesity, oil-gas, …). They graduate to an active `campaigns/<vertical>/` folder when you commit to
running that vertical — the research-lane parallel to a technical draft graduating to `blog/`. Engineering
specs are NOT here: those stay in `local/specs/` (they're about the machine, not content).

## Conventions

- **One idea, sibling cuts:** `medium-<topic>.md` / `linkedin-<topic>.md` / `x-<topic>.md` are platform-native
  cuts of the same piece (the `*-content-machine.*` trio is the model). Drafts carry a light frontmatter
  header: `platform / status / bucket / audience / suggested_tags / hook`.
- **`BACKLOG.md`** is the flat queue — one line per idea, `idea → drafting → queued → published`. It is the
  whole planning apparatus; do **not** build a planner around it.
- **`archive/`** = previously posted or old unposted drafts (launch-era LinkedIn/X/Medium/Reddit/HN + the
  prior `TECH_POSTS_SPEC.md`). Historical reference, not active work — mine it for proven copy, don't treat
  it as the queue.
- **Don't publish directly from `drafts/`** — it's pre-canonical. Promote to `blog/<slug>/` (path 1) or post
  natively (path 2).

## What's here

- `medium-provenance.md` · `medium-graph-native-close.md` · `medium-real-data-dogfood.md` — standalone essays (WIP).
- `linkedin.md` — 6 copy-paste short LinkedIn posts (standalone queue).
- `BACKLOG.md` — the living queue.
- `campaigns/` — draft coverage plans (7 verticals) → graduate to `campaigns/{name}/`.
- `archive/` — prior posted/unposted pieces (historical reference).

_The Coverage Machine trio that seeded `drafts/` graduated to `blog/the-coverage-machine/` and published
2026-06-28; its source drafts were deleted (git is the archive)._
