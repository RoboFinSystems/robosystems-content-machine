# Recording a chat-client demo (ChatGPT, claude.ai, Grok, or our apps)

A second capture mode next to the filings→video pipeline: drive a real AI chat client (or robosystems-app / roboledger-app) through Playwright while it uses RoboSystems over MCP, record the session, and publish it to `content/demos/<slug>/`. First used 2026-08-26 for the ChatGPT plugin-directory submission (`content/demos/chatgpt_plugin/`).

## Prerequisites

- Claude Code with the Playwright MCP plugin (headed browser). The operator signs in to the chat client **by hand in that browser**; the recording context inherits the cookies. Never type credentials through automation.
- The RoboSystems connection already configured in the client (plugin installed / connector authorized) so the take starts at the prompt, not at consent.
- `ffmpeg` on the path. macOS `screencapture -v` is not an option without the Screen Recording permission; Playwright's recorder is the path.

## Recipe

1. **Recording context.** From `browser_run_code_unsafe` (sandbox: no `require`, no `process`, and `globalThis` is not persisted — hang state on `page.__rec`):
   ```js
   const browser = page.context().browser();
   const ctx = await browser.newContext({
     viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2,
     recordVideo: { dir: '<scratch>/takes', size: { width: 1280, height: 800 } },
   });
   await ctx.addCookies(await page.context().cookies());
   const rec = await ctx.newPage(); page.__rec = { ctx, rec };
   ```
2. **Stage the page.** Collapse the sidebar (recent chats are on it), dismiss any upsell banner, start from a fresh conversation.
3. **Invoke the plugin, ChatGPT-specific.** Type `@RoboSystems`, wait for the popup whose header reads **Plugins**, press **Enter**. Do not click the matching text — it hits the chip in an earlier message and opens the plugin page (a spoiled take). Then type the prompt and press Enter.
4. **Wait for completion.** `button[aria-label*="Stop"]` appears, then disappears. Click **Called tool** to expand the tool card before moving on; pause a beat on results.
5. **Finish.** `await page.__rec.ctx.close()` — the `.webm` is only finalized on context close.
6. **Encode.** `ffmpeg -i take.webm -c:v libx264 -pix_fmt yuv420p -movflags +faststart out.mp4`; trim the first seconds if the sidebar was still visible (`-ss`).

## Publish

```
aws s3 cp out.mp4 s3://robosystems-content/content/demos/<slug>/<slug>_<variant>.mp4 \
  --profile robosystems-sso --content-type video/mp4 --cache-control "public, max-age=86400"
aws s3 cp meta.json s3://robosystems-content/content/demos/<slug>/meta.json --profile robosystems-sso
```

`meta.json` follows the existing demos (`slug`, `title`, `status`, `version` or `shipped_at`, `runtime_sec`, `file`, `notes`). Served at `https://assets.robosystems.ai/content/demos/<slug>/<file>`; only `content/*` and `blog/*` are public.

## Rules for a take

- 1280×800 at 2×, under ~3:30, one storyline, no credentials or account e-mail on screen; use the reviewer tenant or a showcase graph, never customer data.
- Nothing baked in that a directory reviewer would read as fabricated: real prompts, real tool calls, real results.
- A take that needs a re-shoot is cheaper than an edit — re-run the recipe.
