# RoboSystems Content Machine

Automated video content pipeline for SEC filing analysis. Uses [Claude Desktop Cowork](https://claude.ai) to generate written assets (report, script, charts), then a production pipeline to turn them into a finished video.

## How It Works

There are two phases:

1. **Content generation (Claude Cowork)** — Claude analyzes a company's SEC filing via the [RoboSystems](https://robosystems.ai) MCP tools and produces a video script, chart HTMLs, stock report, social post, and thumbnail.
2. **Video production (pipeline)** — A series of Python scripts screenshot the charts, generate avatar video segments (HeyGen), synthesize voiceover audio (ElevenLabs), upload assets to S3, and assemble the final video (Shotstack).

## Prerequisites

**CLI tools:**

- [uv](https://docs.astral.sh/uv/) — Python package manager (handles all Python deps)
- [just](https://github.com/casey/just) — command runner
- [Google Chrome](https://www.google.com/chrome/) — used headlessly for chart screenshots
- [ffmpeg / ffprobe](https://ffmpeg.org/) — media duration detection
- [AWS CLI](https://aws.amazon.com/cli/) — S3 uploads (with SSO or credentials configured)

**API accounts:**

- [HeyGen](https://www.heygen.com/) — avatar video generation
- [ElevenLabs](https://elevenlabs.io/) — voice synthesis
- [Shotstack](https://shotstack.io/) — cloud video assembly

**For the Cowork phase:**

- [Claude Desktop](https://claude.ai/download) with the RoboSystems MCP server configured

## Setup

```bash
git clone https://github.com/RoboFinSystems/robosystems-content-machine.git
cd robosystems-content-machine
```

The first time you run any `just` command, `.env` is auto-created from `.env.example`. Open it and fill in your API keys:

### HeyGen (avatar video segments)

Sign up at [heygen.com](https://www.heygen.com/). Then:

- **`HEYGEN_API_KEY`** — Settings → API Keys
- **`HEYGEN_AVATAR_ID`** — Create or pick an avatar, copy its ID from the avatar editor URL
- **`HEYGEN_VOICE_ID`** — Pick a voice in the avatar editor, copy its ID from the API or voice library

### ElevenLabs (voiceover audio)

Sign up at [elevenlabs.io](https://elevenlabs.io/). Then:

- **`ELEVEN_LABS_API_KEY`** — Profile → API Keys
- **`ELEVEN_LABS_VOICE_ID`** — Voice Library → select a voice → copy the Voice ID

### Shotstack (video assembly)

Sign up at [shotstack.io](https://shotstack.io/). Then:

- **`SHOTSTACK_API_KEY`** — Dashboard → API Keys (use the **Stage** key for testing)
- **`SHOTSTACK_OWNER_ID`** — shown on the same Dashboard page

### AWS (S3 uploads)

The assemble step uploads assets to S3 (so Shotstack can access them via presigned URLs). You need a bucket created beforehand.

- **`AWS_PROFILE`** — your AWS CLI profile name. Run `aws sso login --profile <name>` before the pipeline if using SSO
- **`S3_BUCKET`** — the bucket name for asset uploads (must already exist, your profile needs `s3:PutObject` and `s3:GetObject`)
- **`S3_REGION`** — bucket region (default: `us-east-1`)

## Usage

### 1. Scaffold a new project

```bash
just new NVDA 10-K 2025
```

This copies the template into `projects/NVDA_2025_10_K/` with the folder structure and instructions Claude needs.

### 2. Generate content with Claude Cowork

Open Claude Desktop and start a Cowork session pointed at the new project folder. Claude reads `COWORK_INSTRUCTIONS.md` and produces:

- `reports/{TICKER}_report.html` — investor-grade HTML report
- `scripts/{TICKER}_script.json` — structured video script
- `charts/html/*.html` — one chart per visual segment
- `social/{TICKER}_x_post.txt` — X post
- `charts/html/{TICKER}_thumbnail.html` — YouTube thumbnail

### 3. Run the production pipeline

```bash
just pipeline NVDA_2025_10_K
```

This runs all steps end-to-end. The final video opens automatically when done.

## Pipeline Steps

| Step | What it does |
|------|-------------|
| **Validate** | Checks that all Cowork outputs exist and the script JSON matches the expected schema. Auto-fixes common issues. |
| **Screenshots** | Opens each chart HTML in headless Chrome and captures a 1920x1080 PNG. |
| **Avatar** | Sends avatar segment narration to the HeyGen API, polls until videos are ready, downloads them. |
| **Voiceover** | Sends visual segment narration to ElevenLabs TTS, downloads the audio files. |
| **Assemble** | Uploads all assets to S3, builds a Shotstack timeline, submits the render, and downloads the final MP4. |

## Running Steps Individually

```bash
just validate NVDA_2025_10_K      # Validate cowork outputs
just validate-fix NVDA_2025_10_K  # Validate and auto-fix
just screenshots NVDA_2025_10_K   # Screenshot charts to PNG
just avatar NVDA_2025_10_K        # Generate HeyGen avatar segments
just avatar-poll NVDA_2025_10_K   # Resume polling (if interrupted)
just voiceover NVDA_2025_10_K     # Generate ElevenLabs voiceovers
just assemble NVDA_2025_10_K      # Assemble final video via Shotstack
```

**Utilities:**

```bash
just projects                     # List all projects
just play NVDA_2025_10_K          # Play the final video
just durations NVDA_2025_10_K     # Show media durations via ffprobe
just clean NVDA_2025_10_K         # Remove generated assets (keeps source files)
```

## Project Structure

```
.
├── justfile                        # All commands
├── .env.example                    # Environment variable template
├── template/                       # Project template (copied by `just new`)
│   ├── COWORK_INSTRUCTIONS.md      # Prompt for Claude Cowork
│   ├── assets/                     # Brand assets (logo)
│   └── charts/html/                # Chart template + examples
│       ├── CHART_TEMPLATE.html
│       ├── EXAMPLE_bar_chart.html
│       ├── EXAMPLE_data_table.html
│       ├── EXAMPLE_line_chart.html
│       ├── EXAMPLE_metric_cards.html
│       ├── INTRO_SLIDE.html
│       └── OUTRO_SLIDE.html
├── tools/                          # Pipeline scripts
│   ├── run_pipeline.sh             # Full pipeline runner
│   ├── new_project.sh              # Project scaffolding
│   ├── validate_project.py         # Schema validation
│   ├── screenshot_charts.py        # Headless Chrome screenshots
│   ├── generate_avatar_segments.py # HeyGen API
│   ├── generate_voiceover_audio.py # ElevenLabs API
│   └── assemble_video.py           # S3 upload + Shotstack render
└── projects/                       # Generated projects (gitignored)
    └── NVDA_2025_10_K/
        ├── COWORK_INSTRUCTIONS.md
        ├── scripts/
        ├── charts/html/
        ├── charts/png/
        ├── reports/
        ├── social/
        └── videos/
```

## Links

- [robosystems.ai](https://robosystems.ai) — RoboSystems platform
