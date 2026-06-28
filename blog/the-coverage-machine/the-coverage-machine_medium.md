
# The Coverage Machine

## How we turn SEC filings into narrated equity research — and why we do it in the open

There's a strange gap in public markets. Thousands of companies file audited financials with the SEC every quarter — real revenue, real margins, real balance sheets — and almost no one writes a word about them. The big names get a dozen analysts each. Everyone else gets nothing: no sell-side coverage, no research notes, no plain-English explanation of what the numbers say. Whole corners of the market — small caps, OTC names, the entire US cannabis sector marooned off the major exchanges — are statistically invisible, despite filing the same disclosures as everyone else.

The data isn't missing. Every one of those filings is public, structured XBRL, sitting in EDGAR. What's missing is anyone turning it into something a human would actually watch or read. That's the gap we decided to fill — not by hiring a floor of analysts, but by building a machine.

We call it the content machine. It takes a ticker, pulls the company's actual SEC filings, runs a structured financial analysis, and produces a narrated video breakdown — plus a written brief, a podcast cut, and the social posts to go with it. It's the primary way we go to market for [RoboSystems](https://robosystems.ai), and it's open source. This post is what it is and how it works, with nothing hidden — because the whole point is that the method is the message.

### The thesis: the data already exists; turn it into coverage

RoboSystems is, underneath everything, structured access to financial data — including an open knowledge graph of SEC XBRL filings for every public company. Revenue, earnings, cash flow, segment breakdowns, the footnotes, the tax detail: all queryable, all traceable back to the original filing.

Once you have that, a question presents itself. If the data is already structured and an AI agent can query it precisely, what stops you from producing real coverage of the companies nobody covers? Not a hot take — actual analysis, grounded in the filing, at a cost per company that rounds to zero. The answer turned out to be: nothing stops you. You just have to build the assembly line.

### How it works, end to end

The machine runs in three stages. We keep them deliberately separate, because each one is good at something the others aren't.

**1. Research.** An AI analyst (Claude, driving the RoboSystems data tools) pulls the company's financials straight from the SEC graph — keyed to the company's permanent SEC identifier, not a ticker that might have changed. It computes the things that actually matter for the name: multi-year revenue and margin trajectory, cash flow versus reported earnings, the debt and maturity picture, the effective tax rate, and a set of "what happens if the situation changes" scenarios. Every number it uses traces to a specific line in a specific filing. The output of this stage is a written brief and a single source-of-truth script — the narration and the on-screen data, locked together.

**2. Craft.** The script becomes an on-brand slide deck and a thumbnail, built in a design tool that already knows our visual system. This is the step we keep human-in-the-loop on purpose. Automated slides look automated; a designed deck looks like someone cared. The script constrains it — every slide maps to a narration beat and shows the exact filing number — but the craft is real.

**3. Production.** Code takes over again: it slices the deck into frames, generates the voiceover ([ElevenLabs](https://try.elevenlabs.io/v9z3wzm97gk3)), assembles the video, normalizes the audio, and emits the final 1080p file plus a podcast extract and the chapter timestamps. One command in, a finished video out.

Research that automates. Craft that doesn't. Production that automates again. That split is the whole design.

### The discipline part

It would be easy to make this fast and wrong. The hard part — the part that makes it coverage instead of content — is the discipline.

Every figure that goes on screen is checked against the source filing; for the first videos of a new campaign we re-verify the headline numbers directly against the XBRL graph, line by line, before anything renders. When we model what a company could be worth under different scenarios, we present it as a *range* under stated assumptions — never a price target, never a buy or sell call. We're not a registered investment adviser and we don't pretend to be one. The job is to show what the filing says and what the math looks like, with the assumptions on the table, and let the viewer decide. The audience can verify everything. That's the entire value proposition.

### What it looks like in practice

The first campaign is US cannabis — an obvious fit, because those multi-state operators are exactly the under-covered, mispriced, regulation-driven names the gap describes.

Take our most recent one: Trulieve. The filings tell a genuinely strange story — a company doing $1.2 billion in revenue at a 60% gross margin, generating record cash flow, that still reports a net loss, purely because a tax rule written for drug traffickers (Section 280E) taxed it at an effective rate of 228%. That's not a typo; it's in the 10-K. We'd covered Trulieve once before, so this one ran as a *coverage update*: in the months since, it became the first US cannabis company to list on the NYSE, and its quarterly tax rate just collapsed from 258% to 87% as a partial federal rescheduling took effect. The hook wrote itself — the tax relief is here; now what does a cash machine like this do with profitability it hasn't had in years? Every number in that video reconciles to the filings to the dollar. We checked.

### What I'm not claiming

I want to be precise about what this is and isn't, because the genre is full of overclaiming and I'd rather not add to it.

It is not a button you press to get a finished film. There's a human in the loop on the craft and on editorial judgment, and there should be. It is not a replacement for analysts who do deep, original, primary-source work on the names that deserve it — it's coverage for the long tail that gets *no* attention at all. And it is not finished. We shipped the first video of the current version days ago; in doing it we found our own bugs — our runtime estimates were off by nearly half, which threw the first set of chapter timestamps out by several seconds until we made the pipeline emit the real ones. We fixed it in the open and wrote it down. That's the honest state of the thing: working, useful, and visibly improving.

### Why it should matter to you

If you build things with AI, the generalizable lesson is about the substrate. The reason this works isn't a clever prompt — it's that the underlying data is *structured and verifiable*, so the model can be precise and we can check it. Point capable models at clean, queryable data with a verification step, and you can manufacture genuinely good analytical work at a scale and cost that didn't exist a couple of years ago. The bottleneck was never the analysis. It was the data being a mess.

If you invest, the takeaway is simpler: a lot of real businesses are priced by a market that has never had the analysis explained to it. Coverage is starting to reach them.

And if you're curious how it's actually done — the data behind every video is the open SEC repository inside RoboSystems, and the content machine itself is open source. You can run the same queries we run. We'd rather show our work than ask you to take it on faith.

---

*We build RoboSystems in the open — structured, verifiable financial data and the AI tools that operate on top of it. The coverage videos are one thing that data makes possible; there are others. If there's a public company you wish someone would actually explain, tell me the ticker — it might be next. More at [robosystems.ai](https://robosystems.ai).*

*Disclosure: the ElevenLabs link above is a referral link.*
