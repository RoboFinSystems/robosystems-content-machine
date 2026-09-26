# motion

The RoboLedger video templates: a standard intro, a standard end card, and a data-driven
"slide" for motion shots between live footage. They reuse the roboledger-app landing demos'
kit (`public/demos/kit.js`), fonts and logo, which the renderer mounts at `/demos/`, `/fonts/`
and `/images/`, so the videos and the landing page share one look and one runtime.

```bash
just motion-template intro  open    '{"kicker":"For finance leads","title":"Why is cash down in a profitable year?"}' out/
just motion-template slide  ar      '{"kind":"number","eyebrow":"Receivables","from":{"value":17333,"label":"a year ago"},"value":153333,"prefix":"$","label":"owed at year end"}' out/
just motion-template outro  end     '{"note":"Driftline Coffee Roasters is a demo company."}' out/
```

Each call writes `out/<name>.mp4` (silent, 1920x1080, 30fps). Add `--stills 1,3` for QA frames
instead. `$ROBOLEDGER_PUBLIC` points at a different roboledger-app checkout.

## Templates

| Template | Data | Default length |
| --- | --- | --- |
| `intro` | `kicker`, `title`, `sub?` | 4.8s |
| `outro` | `line?`, `cta?`, `note?` | 5.5s |
| `slide` `title` | `eyebrow?`, `headline`, `sub?` | 4.5s |
| `slide` `number` | `eyebrow?`, `value`, `prefix?`, `suffix?`, `decimals?`, `label`, `from?: {value, label}` | 4.5s |
| `slide` `compare` | `eyebrow?`, `left: {title, items[]}`, `right: {title, items[]}` | 4.5s |
| `slide` `flow` | `eyebrow?`, `nodes[]`, `caption?` | 4.5s |

Every template takes `duration` (seconds). Once the narration exists, set it from the voice so
the picture follows the voice, not the reverse.

## Rules the templates keep

They follow `tools/motion/README.md`:

- One idea per shot, centred.
- Headlines blur in word by word.
- A slow push runs under every shot.
- Content fades into the shared backdrop at both ends, so cuts between templates and live
  footage never dip to black.
- No glows, no drop shadows, no text parked at the top of the frame.
- Put on screen only what the narration says at that moment.

Run `just motion-pops` on anything assembled from them. A count-up (`number`) changes digits
every frame by design, so expect flags inside its first two seconds and nowhere else.
