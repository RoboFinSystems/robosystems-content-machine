# RoboSystems Content Machine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automated video content pipeline for financial analysis. Combines AI-generated content with production automation to turn SEC filings into narrated videos, podcasts, and social posts.

- **Campaign-Driven**: Reusable campaign templates define the editorial angle, slide designs, and output specs — apply them to any ticker
- **AI Content Generation**: [Claude Cowork](https://claude.ai) analyzes filings via [RoboSystems](https://robosystems.ai) MCP tools and produces narrative briefs, video scripts, charts, and social posts
- **Automated Production**: Pipeline screenshots charts, synthesizes voiceover, assembles video, and extracts podcast audio
- **Two Production Modes**: Slides-only (voiceover + charts) or mixed (avatar segments + charts) — auto-detected from script

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

### 1. Scaffold a Project

Every project starts from the base `template/`, which provides the folder structure, chart types, slide examples, and pipeline assets. Scaffold one for any ticker:

```bash
just new TICKER
```

#### Campaigns

For thematic coverage across multiple companies, campaigns add an editorial layer on top of the base template. A campaign defines the voice, analytical framework, slide designs, and target tickers for a class of companies.

```
campaigns/
  my_campaign/
    CAMPAIGN_BRIEF.md        # Editorial strategy and analytical framework
    COWORK_INSTRUCTIONS.md   # Claude's production instructions (overrides base)
    tickers.md               # Target companies and production calendar
    sources/                 # Third-party research and reference data (gitignored)
    overrides/               # File replacements (custom slide templates, assets)
```

When you scaffold with a campaign, the base template is applied first, then the campaign overlays its instructions, briefs, and templates on top.

```bash
just campaigns                       # List available campaigns
just campaign TICKER campaign_name   # Scaffold with campaign overlay
```

### 2. Content Generation (Claude Cowork)

Open Claude Desktop and start a Cowork session pointed at the scaffolded project folder. Claude reads the instructions and produces:

- **Narrative brief** — written analysis (Markdown)
- **Video script** — structured JSON with segment timing and narration
- **Charts and slides** — one HTML file per visual segment
- **Social posts** — platform-specific copy (X, StockTwits)
- **Thumbnail** — YouTube thumbnail HTML

### 3. Production Pipeline

```bash
just pipeline PROJECT   # Run all steps end-to-end
```

| Step | Command | What it does |
|------|---------|-------------|
| **Validate** | `just validate PROJECT` | Checks Cowork outputs exist and script JSON matches schema |
| **Screenshots** | `just screenshots PROJECT` | Opens each chart HTML in headless Chrome, captures 1920x1080 PNGs |
| **Avatar** | `just avatar PROJECT` | Sends avatar narration to HeyGen API (mixed mode only) |
| **Voiceover** | `just voiceover PROJECT` | Sends visual narration to ElevenLabs TTS |
| **Assemble** | `just assemble PROJECT` | Uploads assets to S3, builds Shotstack timeline, renders final MP4 |
| **Podcast** | `just podcast PROJECT` | Extracts podcast audio (MP3) from final video |

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
- [Google Chrome](https://www.google.com/chrome/) — headless chart screenshots
- [ffmpeg / ffprobe](https://ffmpeg.org/) — media processing
- [AWS CLI](https://aws.amazon.com/cli/) — S3 uploads

### API Keys

Configure in `.env` after first run:

| Service | Keys | Purpose |
|---------|------|---------|
| [ElevenLabs](https://elevenlabs.io/) | `ELEVEN_LABS_API_KEY`, `ELEVEN_LABS_VOICE_ID` | Voice synthesis |
| [Shotstack](https://shotstack.io/) | `SHOTSTACK_API_KEY`, `SHOTSTACK_OWNER_ID` | Cloud video assembly |
| [HeyGen](https://www.heygen.com/) | `HEYGEN_API_KEY`, `HEYGEN_AVATAR_ID`, `HEYGEN_VOICE_ID` | Avatar video (mixed mode only) |
| AWS | `AWS_PROFILE`, `S3_BUCKET`, `S3_REGION` | Asset uploads for Shotstack |

### Claude Cowork

The content generation phase requires [Claude Desktop](https://claude.ai/download) with the [RoboSystems MCP server](https://github.com/RoboFinSystems/robosystems-mcp-client) configured.

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

MIT © 2026 RFS LLC
