# RoboSystems Content Machine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automated content pipeline for financial analysis. Turns a company's SEC filings into a narrated **video**, a vertical **teaser short**, a two-voice **Q&A podcast**, and **social posts** — one analysis, multiple formats.

- **Campaign-Driven** — reusable campaign templates define the editorial angle, analytical framework, and output specs; apply them to any ticker.
- **AI Content Generation** — [Claude Cowork](https://claude.ai) analyzes filings via [RoboSystems](https://robosystems.ai) MCP tools and writes the brief, video script, Q&A script, and social posts.
- **On-Brand Decks** — slides are composed in [Claude Design](https://claude.ai/design) from the `@robosystems/core` design system (no hand-authored HTML).
- **Automated Production** — the pipeline slices the deck, synthesizes voiceover, assembles the video, and produces the short + podcast.

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

Three stages: **research** and **production** automate; the **design** step in the middle is human-in-the-loop (the craft step).

### 1. Scaffold a Project

Every project starts from the base `template/` (folder structure + stage instructions + assets). Projects are company-centric — sources accumulate over time, each run produces a new set of outputs.

```bash
just new TICKER                      # base template
just campaign TICKER campaign_name   # with a campaign overlay
just campaigns                       # list available campaigns
```

#### Campaigns

Campaigns add an editorial layer for thematic coverage across many companies — the voice, analytical framework, target tickers, and shared reference data.

```
campaigns/
  my_campaign/
    CAMPAIGN_BRIEF.md        # Editorial strategy and analytical framework
    AUTHORING_INSTRUCTIONS.md   # Production instructions (overrides base)
    tickers.md               # Target companies and production calendar
    sources/                 # Third-party research and reference data (gitignored)
    overrides/               # File replacements (custom assets/instructions)
```

The base template is applied first, then the campaign overlays its instructions, brief, and shared sources on top.

### 2. Content Generation (Claude Cowork)

Point a Cowork session at the scaffolded project folder. Claude reads the instructions (`AUTHORING_INSTRUCTIONS.md` + `PRODUCTION_CONTRACT.md`) and produces:

- **Narrative brief** — the written analysis (Markdown), authored first.
- **Video script** (`scripts/{TICKER}_script.json`) — the source of truth: ordered segments with narration + per-slide content, the `thumbnail` block, and a `short` block (the teaser).
- **Q&A script** (`scripts/{TICKER}_qa.json`) — a two-voice interviewer/analyst conversation for the podcast.
- **Social posts** — X post + YouTube description.

Cowork authors **no HTML** — slides and the thumbnail are specced in the script and built in Claude Design.

### 3. Design (Claude Design)

Generate the hand-off brief, then compose the deck + thumbnail on-brand:

```bash
just deck-brief TICKER   # render the Claude Design hand-off from the script
```

Paste the brief into [claude.ai/design](https://claude.ai/design) (on `@robosystems/core`), compose a 16:9 deck and thumbnail, then export **both as PDF** (Claude Design exports PDF only) → `deck/{TICKER}_deck.pdf` and `deck/{TICKER}_thumbnail.pdf`. The `slice` step rasterizes the thumbnail PDF to `charts/png/{TICKER}_thumbnail.png` automatically.

### 4. Production Pipeline

```bash
just pipeline PROJECT       # validate -> slice -> voiceover -> assemble (long-form video)
just short PROJECT          # 9:16 teaser short (b-roll + music + VO + caption cards)
just podcast-qa PROJECT     # two-voice Q&A podcast (MP3 for Spotify + MP4 for YouTube)
just podcast PROJECT        # extract podcast MP3 from the long-form video
just publish PROJECT        # upload final deliverables to the public S3 artifact store
just postpack PROJECT       # assemble the per-platform publish pack (paste-ready copy + S3 links)
```

| Step | Command | What it does |
|------|---------|-------------|
| **Validate** | `just validate PROJECT` | Checks Cowork outputs exist and the script matches the deck contract |
| **Slice** | `just slice PROJECT` | Slices the exported deck PDF into per-slide 1920×1080 PNGs (pdftoppm) |
| **Voiceover** | `just voiceover PROJECT` | Sends narration to ElevenLabs TTS (idempotent; `--force` to regen) |
| **Assemble** | `just assemble PROJECT` | Uploads assets to S3, builds the Shotstack timeline, renders the MP4 (`--production` for 1080p) |
| **Short** | `just short PROJECT` | Renders a 9:16 teaser locally with ffmpeg |
| **Podcast (Q&A)** | `just podcast-qa PROJECT` | Synthesizes the two-voice conversation → MP3 + MP4 |

Assembly writes `videos/{TICKER}_timestamps.txt` with the actual YouTube chapter times.

### Publishing (S3 artifact store)

`just publish {TICKER}` uploads the final deliverables (long-form, short, podcast MP3/MP4,
thumbnail, brief, social copy) to `s3://$AWS_S3_BUCKET/content/{TICKER}/` and prints public URLs
(served via `$AWS_CDN_DOMAIN_URL` when set, else `https://$AWS_S3_BUCKET.s3.amazonaws.com/content/{TICKER}/…`)
— a durable artifact store, separate from posting to YouTube / Spotify / X. The bucket policy grants
public read on the **`content/*` + `blog/*` prefixes only** (no user data — the store is public by
design); Shotstack staging assets elsewhere stay private. The bucket + CloudFront CDN are managed by
`cloudformation/content.yaml` (`just infra-deploy` — see Infrastructure below).

### Blog pipeline

A lighter sibling of the research pipeline for markdown essays. A post is one file —
`blog/<slug>/post.md` (YAML frontmatter + body), authored and **git-versioned in this repo**.
Narration, cover image, and social copy are all optional and additive; a post with just
`post.md` publishes cleanly.

```bash
just blog-new <slug>        # scaffold blog/<slug>/post.md from the template
just blog-publish <slug>    # auto-narrate (default-on) + upload blog/<slug>/* to S3 + reindex
just blog-narrate <slug>    # (re)generate narration on its own; --force to redo
just blog-social <slug>     # optional: paste-ready distribution pack (uses <slug>_x_post.txt if present)
just blog-reindex           # rebuild blog/index.json (the catalog the app's /blog routes read)
```

**Every post ships with a "Listen to this story" narration** — `blog-publish` auto-narrates any
post that has no audio yet (pass `--no-audio` to skip), so the feature stays consistent across
the whole catalog. Narration reuses the same ElevenLabs path as the research voiceover + Q&A
podcast (one brand voice; body stripped of code/tables, chunked for TTS, concatenated with
ffmpeg). `blog-publish` also writes a self-describing `meta.json` and refreshes `blog/index.json`
— a versioned contract (`version: 1`) with absolute CDN asset URLs, the same consumption shape
the `/research` catalog uses. The app consumes it via SSG/ISR; publishing or editing a post no
longer needs an app redeploy.

### Shared Media Libraries

The short pulls from reusable, mood/tag-tagged libraries that compound across every ticker:

```bash
just broll          # show the b-roll library + coverage by category
just broll-sync     # register new clips dropped into assets/broll/
just music-sync     # register new tracks dropped into assets/music/
just music "<prompt>"   # generate a music bed via the ElevenLabs Music API
```

Cowork selects clips/tracks by theme: a `broll_theme` / `music_mood` (tags) or an explicit list. Manifests are tracked; the heavy `.mp4`/`.mp3` binaries are gitignored (local-only).

### Batch Operations

```bash
just projects              # List all projects
just play PROJECT          # Play the final video
just durations PROJECT     # Show media durations via ffprobe
just clean PROJECT         # Remove generated assets (keeps source files)
```

## Setup

### Required Tools

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [just](https://github.com/casey/just) — command runner
- [ffmpeg / ffprobe](https://ffmpeg.org/) — media processing (short, podcast, slicing)
- [poppler](https://poppler.freedesktop.org/) — `pdftoppm` for slicing the deck PDF + rasterizing the thumbnail
- [AWS CLI](https://aws.amazon.com/cli/) — S3 uploads for Shotstack

### API Keys

Configure in `.env` after first run:

| Service | Keys | Purpose |
|---------|------|---------|
| [ElevenLabs](https://try.elevenlabs.io/v9z3wzm97gk3) | `ELEVEN_LABS_API_KEY`, `ELEVEN_LABS_VOICE_ID`, `ELEVEN_LABS_INTERVIEWER_VOICE_ID` | Voiceover (narrator) + Q&A interviewer voice + Music API |
| [Shotstack](https://shotstack.io/) | `SHOTSTACK_API_KEY`, `SHOTSTACK_OWNER_ID` (+ sandbox keys) | Cloud video assembly |
| AWS | `AWS_PROFILE`, `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_CDN_DOMAIN_URL` (optional), `AWS_ROUTE53_HOSTED_ZONE_ID` (optional, auto-resolved) | Asset uploads + CloudFront CDN |

<sub>The ElevenLabs link above is a referral link.</sub>

### Claude Cowork + Claude Design

Content generation uses [Claude Desktop](https://claude.ai/download) with the [RoboSystems MCP server](https://github.com/RoboFinSystems/robosystems-mcp-client) configured; the deck is composed in [claude.ai/design](https://claude.ai/design) on the `@robosystems/core` design system.

## Infrastructure

The content bucket + CloudFront CDN are defined in `cloudformation/content.yaml` and deployed
**locally via the AWS CLI** (no GitHub Actions), mirroring the platform repo's `just bootstrap` flow.
Config comes from `.env` (`AWS_PROFILE`, `AWS_S3_BUCKET`, optional `AWS_CDN_DOMAIN_URL`;
`AWS_ROUTE53_HOSTED_ZONE_ID` is auto-resolved from the CDN domain).

```bash
just infra-validate    # validate the template
just infra-deploy      # create the bucket + CDN stack (+ wait, + print outputs)
just content-migrate   # copy existing content from the legacy bucket into the new one
just reindex           # rebuild content/index.json on the new bucket (CDN urls)
just infra-outputs     # show bucket / CDN url / distribution id
```

`infra-deploy` creates a **new** bucket (default `robosystems-content`); the legacy
`robosystems-marketing-assets` bucket is left untouched. After migrating + reindexing, point the apps
at the CDN (`assets.robosystems.ai`) and retire the old bucket when ready.

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

Backed by an **[ElevenLabs Grant](https://elevenlabs.io/startup-grants)** — the credits power the voiceover, Q&A interviewer voice, and music generation behind every video this pipeline produces.

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
