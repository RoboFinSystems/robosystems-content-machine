---
description: Shoot one MCP chat-demo episode from a JSON spec (headed Playwright, real Claude/ChatGPT/Grok).
argument-hint: '[path-to-episode.json]'
---

Shoot one live MCP chat-demo episode. **Claude Max or Grok Build only. Marketing watches, does not drive Playwright.** Playbook: `showcase/mcp_series/playbook.md`. Recipe: `showcase/mcp_series/recording.md`. Spec: `$ARGUMENTS`. Two Playwright browsers. `just demo-up` first. Stop for Joey to OAuth MCP.

## Non-negotiables

- Never type credentials. If claude.ai / ChatGPT / Grok / the apps are not already signed in in the headed browser, stop and tell the operator to sign in by hand.
- Preflight is human: `showcase/mcp_series/preflight.md`. Prod graph from demo-integration, OAuth into the client, app open on the same `graph_id`. If OAuth, connector consent, or a graph picker appears, stop. Do not complete it. If chat and the app are on different graphs, stop.
- Claude takes: Team seat A only, never Joey's Max. ChatGPT: one Plus, sidebar collapsed, no second seat. Grok: existing login only. If a name or email is readable, spoil the take. A ChatGPT Plus badge is fine.
- Showcase graph only. Never customer data. App login is the showcase tenant.
- Real prompts, real tool calls, real results. Nothing baked in.
- No em dashes in notes, commit messages, or meta.json.
- Do not Buffer, do not post social, do not `just publish` unless the episode `"publish": true` AND the operator just said ship.
- Re-shoot is cheaper than a fancy edit.

## Steps

1. Read `showcase/mcp_series/recording.md` and the episode JSON.
2. Confirm headed Playwright MCP is available. Confirm the client in `episode.client` is signed in and the RoboSystems connector is already authorized.
3. Open a recording context (1280x800, deviceScaleFactor 2). Copy cookies. Fresh conversation. Collapse the sidebar.
4. Run `episode.prompts` in order. For each: type the prompt, wait until Stop disappears, expand the tool card, pause on the result. `expect_tools` and `pass` are the quality gate. If a prompt fails the pass check, stop and re-shoot that prompt. Do not stitch a miss.
5. If `mode` is `flip` or `dual-surface`, open the app page in the same context and capture the outcome / grid move as specified in `cuts`.
6. Close the recording context (webm finalizes on close). ffmpeg encode to `content/demos/<slug>/<slug>.mp4` as in the recipe. If dual-surface alongside, hstack to 2560x800 as a `_alongside` variant. Default social cut is 1280x800 flip.
7. Write `content/demos/<slug>/meta.json` with slug, title, status `draft`, runtime_sec, file, notes. Do not upload unless publish is explicitly on.
