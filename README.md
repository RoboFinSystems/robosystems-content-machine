# RoboSystems Content Machine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automated equity-research content pipeline. Turns a company's SEC filings into a narrated
**16:9 video**, a purpose-built **9:16 short**, and a written **brief** that publishes as-is -
one analysis, every surface.

- **Campaign-Driven** - reusable campaign templates define the editorial angle, analytical framework, and output specs; apply them to any ticker.
- **Authored in Claude Code** - one session reads the filings via [RoboSystems](https://robosystems.ai) MCP tools and writes the brief, the video script, the short, and the social copy. No hand-off to another app.
- **Rendered locally** - the deck is HTML built from the script, shot frame-by-frame in headless Chrome, and muxed with ffmpeg. No cloud render service, no per-render cost.
- **No hand-authored slides** - you write numbers into `script.json`; the renderer draws every slide.

> 🎙️ **Voiceover & music run on [ElevenLabs](https://try.elevenlabs.io/v9z3wzm97gk3).** Setting this up? Signing up through our **referral link** costs you nothing extra and directly supports the project. <sub>Affiliate link.</sub>

## Quick Start

```bash
git clone https://github.com/RoboFinSystems/robosystems-content-machine.git
cd robosystems-content-machine

# Scaffold a project from a campaign
just campaign TICKER campaign_name

# Or scaffold from the base template (no campaign)
just new TICKER
```

The first `just` command auto-creates `.env` from `.env.example`. Fill in your API keys (see [Setup](#setup)).

## How It Works

Three stages: **scaffold**, **author**, **render**. Authoring happens in a Claude Code session
against a written contract; everything on either side of it is a `just` recipe.

### 1. Scaffold a Project

Every project starts from the base `template/` (folder structure + the authoring contract + assets).
Projects are company-centric - sources accumulate over time, each run produces a new set of outputs.

```bash
just new TICKER                      # base template
just campaign TICKER campaign_name   # with a campaign overlay
just campaigns                       # list available campaigns
just recover TICKER campaign_name    # re-cover for a new quarter (archives prior outputs)
```

#### Campaigns

Campaigns add an editorial layer for thematic coverage across many companies - the voice, analytical framework, target tickers, and shared reference data.

```
campaigns/
  my_campaign/
    CAMPAIGN_BRIEF.md           # Editorial strategy and analytical framework
    AUTHORING_INSTRUCTIONS.md   # Authoring instructions (overrides base)
    tickers.md                  # Target companies and production calendar
    sources/                    # Third-party research and reference data (gitignored)
    overrides/                  # File replacements (custom assets/instructions)
```

The base template is applied first, then the campaign overlays its instructions, brief, and shared sources on top.

### 2. Author (Claude Code)

Point a Claude Code session at the repo. The scaffolded project carries its own contract:
`AUTHORING_INSTRUCTIONS.md` (the editorial brief) and `PRODUCTION_CONTRACT.md` (the schema,
slide kinds, layout capacity limits, and spoken-form TTS rules). The session reads those plus
everything in `sources/`, verifies every number against the SEC graph over MCP, and writes:

- **Narrative brief** (`reports/{TICKER}_brief.md`) - the written analysis, authored first. Ships verbatim as a native X Article.
- **Video script** (`scripts/{TICKER}_script.json`) - the source of truth: ordered segments carrying narration plus the exact numbers each slide draws.
- **Short script** (`scripts/{TICKER}_short_script.json`) - 5-6 beats for the vertical cut, targeting ~45s.
- **Social copy** (`social/`) - X post, YouTube description, and `publish.json` (the titles and links the publish step reads).

The repo ships the research-lane skills that drive this - `/scout`, `/collect`, `/author`,
`/review`, `/status`, `/batch`, `/refresh` - as `.claude/commands/*.md`. They are conveniences
around the contract, not a dependency: the contract is the spec, and a session that reads
`AUTHORING_INSTRUCTIONS.md` + `PRODUCTION_CONTRACT.md` produces the same artifacts without them.

```bash
just validate TICKER    # gate the authored output against the contract before rendering
```

`validate` is schema-level. It catches missing fields, capacity overruns and duplicate refs; it
cannot see that a chart is visually wrong, so check the rendered frames too.

### 3. Render

```bash
just webdeck-pipeline TICKER         # long-form 16:9 -> videos/{TICKER}_final.mp4
just webdeck-short-pipeline TICKER   # 9:16 short    -> videos/{TICKER}_short.mp4
```

| Step | Command | What it does |
|------|---------|-------------|
| **Everything** | `just webdeck-pipeline TICKER` | Runs the five steps below end to end |
| **Validate** | `just validate TICKER` | Checks the authored output against the production contract |
| **Voiceover** | `just voiceover TICKER` | Sends narration to ElevenLabs TTS (idempotent; `--force` to regen) |
| **Build** | `just webdeck TICKER` | Builds the animated HTML deck from `script.json` + VO durations |
| **Render** | `just webdeck-render TICKER` | Renders the deck to frames via headless Chrome (puppeteer-core) |
| **Mux** | `just webdeck-mux TICKER` | Muxes narration, and narration + ducked music, with ffmpeg |

The 9:16 short runs the same engine at 1080x1920. It is **purpose-built vertical, not a crop**:
its own beat kinds (hook / stat / cards / points / cta), burned-in kinetic captions, a progress
bar and a `$TICKER` chip. One asset serves both X native video and YouTube Shorts.

Rendering is **entirely local** - puppeteer-core drives headless Chrome, ffmpeg does the mux.
There is no cloud render service and no per-render cost, so a re-render costs only wall clock.
The mux writes `videos/{TICKER}_timestamps.txt` with the authoritative YouTube chapter times.

Two pre-render inspection recipes save a full render when the layout is in question:

```bash
just webdeck-stills TICKER "3,17,42"        # single frames at given seconds
just webdeck-short-stills TICKER "1,12,30"
```

### 4. Thumbnails, publish, post

```bash
just thumbnails TICKER   # 3 platform thumbnails, generated from the brief via OpenAI
just publish TICKER      # upload deliverables to the S3 artifact store + reindex the catalog
just postpack TICKER     # assemble the per-platform publish pack (paste-ready copy + S3 links)
```

Posting is per-surface, each asset in its best format:

```bash
just yt-upload TICKER   && just yt-publish TICKER         # long-form (uploads private, then flips)
just yt-short TICKER    && just yt-short-publish TICKER   # the Short (auto-links the long-form)
just x-article TICKER                                     # the brief as a native X Article (draft)
just x-article TICKER --publish
just x-short TICKER                                       # the 9:16 as X native video
just x-post TICKER                                        # the text post
just sync-youtube                                         # capture published URLs into the catalog
just analytics [tickers] · just insights                  # per-post rollup · channel-level reach
```

`just yt-auth` and `just x-auth` do the one-time OAuth for the YouTube and X APIs.

### Publishing (S3 artifact store)

`just publish {TICKER}` uploads the final deliverables (long-form, short, thumbnail, brief,
social copy) to `s3://$AWS_S3_BUCKET/content/{TICKER}/` and prints public URLs
(served via `$AWS_CDN_DOMAIN_URL` when set, else `https://$AWS_S3_BUCKET.s3.amazonaws.com/content/{TICKER}/…`)
- a durable artifact store, separate from posting to YouTube / X. The bucket policy grants
public read on the **`content/*` + `blog/*` prefixes only** (no user data - the store is public by
design); everything else in the bucket stays private. The bucket + CloudFront CDN are managed by
`cloudformation/content.yaml` (`just infra-deploy` - see Infrastructure below).

### Blog pipeline

A lighter sibling of the research pipeline for markdown essays. A post is one file -
`blog/<slug>/post.md` (YAML frontmatter + body), authored and **git-versioned in this repo**.
Narration, cover image, and social copy are all optional and additive; a post with just
`post.md` publishes cleanly.

One catalog feeds two sites. The frontmatter `site` field (`robosystems`, the default, or
`roboledger`) says which app renders the post: robosystems-app lists the graph and platform
essays, roboledger-app lists the buyer posts. Moving a post is one frontmatter line plus a
reindex; `canonicalUrl` must sit on the same domain (publish refuses a mismatch).

```bash
just blog-new <slug> [site] # scaffold blog/<slug>/post.md from the template (site: robosystems | roboledger)
just blog-publish <slug>    # auto-narrate (default-on) + upload blog/<slug>/* to S3 + reindex
just blog-narrate <slug>    # (re)generate narration on its own; --force to redo
just blog-social <slug>     # optional: paste-ready distribution pack (uses <slug>_x_post.txt if present)
just blog-x-article <slug>  # publish the essay as a native X Article
just blog-reindex           # rebuild blog/index.json (the catalog the app's /blog routes read)
```

**Every post ships with a "Listen to this story" narration** - `blog-publish` auto-narrates any
post that has no audio yet (pass `--no-audio` to skip), so the feature stays consistent across
the whole catalog. Narration reuses the same ElevenLabs path as the research voiceover (one brand
voice; body stripped of code/tables, chunked for TTS, concatenated with ffmpeg). `blog-publish`
also writes a self-describing `meta.json` and refreshes `blog/index.json` - a versioned contract
(`version: 1`) with absolute CDN asset URLs, the same consumption shape the `/research` catalog
uses. The app consumes it via SSG/ISR; publishing or editing a post no longer needs an app redeploy.

### Shared Media Libraries

The short pulls from reusable, mood/tag-tagged libraries that compound across every ticker:

```bash
just broll          # show the b-roll library + coverage by category
just broll-sync     # register new clips dropped into assets/broll/
just music-sync     # register new tracks dropped into assets/music/
just music "<prompt>"   # generate a music bed via the ElevenLabs Music API
```

Clips and tracks are selected by theme - a `broll_theme` / `music_mood` (tags) or an explicit
list. Manifests are tracked; the heavy `.mp4`/`.mp3` binaries are gitignored (local-only).

### Product demo capture

A second, separate capture track records the **live product** rather than a deck: a headless
browser drives the real UI, a drawn cursor travels and clicks, and the page responds. It shares
this repo's audio and mux stages but none of its deck code. See
[`renderer/README.md`](renderer/README.md) for `just render-setup`, `render-capture`,
`demo-probe`, and `demo-pipeline`.

### Batch Operations

```bash
just projects              # List all projects
just play PROJECT          # Play the final video
just durations PROJECT     # Show media durations via ffprobe
just clean PROJECT         # Remove generated assets (keeps source files)
```

## Setup

### Required Tools

- [uv](https://docs.astral.sh/uv/) - Python package manager
- [just](https://github.com/casey/just) - command runner
- [ffmpeg / ffprobe](https://ffmpeg.org/) - media processing (render mux, shorts, probing)
- [Node.js](https://nodejs.org/) - the webdeck renderer (puppeteer-core) and `renderer/`
- [AWS CLI](https://aws.amazon.com/cli/) - S3 uploads for publishing + the CloudFront CDN

### API Keys

Configure in `.env` after first run:

| Service | Keys | Purpose |
|---------|------|---------|
| [ElevenLabs](https://try.elevenlabs.io/v9z3wzm97gk3) | `ELEVEN_LABS_API_KEY`, `ELEVEN_LABS_VOICE_ID` | Voiceover + the Music API |
| OpenAI | `OPENAI_API_KEY` | Thumbnail generation (`just thumbnails`) |
| AWS | `AWS_PROFILE`, `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_CDN_DOMAIN_URL`, `AWS_CLOUDFRONT_DISTRIBUTION_ID` | Asset uploads + CloudFront CDN |
| YouTube | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, `YT_CHANNEL_ID` | Uploads + analytics (`just yt-auth` writes the refresh token into `.env`) |
| X | `X_CONSUMER_KEY`, `X_SECRET_KEY`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`, `X_HANDLE` | Articles, posts, native video (`just x-auth` verifies) |

<sub>The ElevenLabs link above is a referral link.</sub>

### Filing data (RoboSystems MCP)

Authoring verifies numbers against SEC XBRL filings through the
[RoboSystems MCP server](https://github.com/RoboFinSystems/robosystems-mcp-client). Configure it
in your Claude Code session; the `sec` graph is the read-only shared repository the research lane
queries. `SEC_RAW_BUCKET` (optional) points `/collect` at a store of raw filing archives; without
it, fetch filings from EDGAR by hand.

## Infrastructure

The content bucket + CloudFront CDN are defined in `cloudformation/content.yaml` and deployed
**locally via the AWS CLI** (no GitHub Actions), mirroring the platform repo's `just bootstrap` flow.
Config comes from `.env` (`AWS_PROFILE`, `AWS_S3_BUCKET`, optional `AWS_CDN_DOMAIN_URL`;
`AWS_ROUTE53_HOSTED_ZONE_ID` is auto-resolved from the CDN domain).

```bash
just infra-validate    # validate the template
just infra-deploy      # create the bucket + CDN stack (+ wait, + print outputs)
just reindex           # rebuild content/index.json (CDN urls)
just infra-outputs     # show bucket / CDN url / distribution id
```

## Resources

- [RoboSystems Platform](https://robosystems.ai)
- [GitHub Repository](https://github.com/RoboFinSystems/robosystems)
- [MCP Client](https://github.com/RoboFinSystems/robosystems-mcp-client)
- [Python Client](https://github.com/RoboFinSystems/robosystems-python-client)

## Support

- [Issues](https://github.com/RoboFinSystems/robosystems-content-machine/issues)
- [Wiki](https://github.com/RoboFinSystems/robosystems/wiki)
- [Projects](https://github.com/orgs/RoboFinSystems/projects)
- [Discussions](https://github.com/orgs/RoboFinSystems/discussions)

## Acknowledgements

Backed by an **[ElevenLabs Grant](https://elevenlabs.io/startup-grants)** - the credits power the voiceover and music generation behind every video this pipeline produces.

<a href="https://elevenlabs.io/startup-grants">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://eleven-public-cdn.elevenlabs.io/payloadcms/cy7rxce8uki-IIElevenLabsGrants%201.webp">
    <img alt="ElevenLabs Grants" src="https://eleven-public-cdn.elevenlabs.io/payloadcms/pwsc4vchsqt-ElevenLabsGrants.webp" width="250">
  </picture>
</a>

<sub>Using ElevenLabs yourself? Our [referral link](https://try.elevenlabs.io/v9z3wzm97gk3) costs you nothing extra and supports the project.</sub>

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

MIT © 2026 RFS LLC
