# Viewports and breakpoints

Read this when design sources show the same screen at more than one width (a phone frame and a desktop frame), or when the target platform is `web-react` or `web-html`.

## 1. Fill each source's `viewport`

Give every `ok` source a `viewport`: `{"width": <CSS px>, "dpr": <device pixel ratio>}`.

- **Figma:** the frame's width in the file is already CSS px. Use `dpr: 1` unless the frame is an exported bitmap.
- **PNG/JPG:** CSS width = pixel width ÷ DPR. Take the DPR, in this order, from:
  1. the file name (`@2x`, `@3x`, `-1x`);
  2. a description or README next to the designs that states canvas sizes;
  3. a guess from common widths: 360–430 px (phones at 1×) or 720–1290 px at 2×/3× for phones; 768–834 (tablet); 1280, 1366, 1440, 1536, 1920 (desktop at 1×). Say it is a guess in the source's `reason` (e.g. `"viewport guessed: 1170 px at @3x = 390"`).
- **PDF/SVG:** the page or `viewBox` width in CSS px, `dpr` from the rasterization you chose.

Leave `viewport` out only when you truly cannot tell, and say so in `reason`.

## 2. Same screen, different widths

Frames of the same screen and state at different viewport widths are **not duplicates**: never run the duplicate check between them, never keep "the higher-resolution one". Group them by screen first, then by width. If it is unclear whether two frames are the same screen, use the confirm-with-the-user step from grouping.

Then decide by the target platform. Read it from `.sauces/project-profile.json` (`projects[].platform`), or from the scaffold choice (`--create-platform`, or the platform the user picked to create):

- **`web-react` or `web-html`:** make one screen per width. Its `id` is `<base>@<width>` (e.g. `login@390`, `login@1440`); set `base` to the screen name without `@` and `breakpoint` to the width. State IDs stay `<screen-id>--<state>` (`login@1440--error`), and reference files follow them (`.sauces/references/login@1440--error.png`). A screen designed at one width only still gets the `@<width>` suffix.
- **Every other platform:** keep one frame per state: the one closest to the target device width, which in practice is the **narrowest** frame (phone widths are under 500 CSS px). Never pick the 1440 frame because it has more pixels. Record the frames you dropped in the kept source's `reason` (e.g. `"also designed at 1440; mobile target keeps 390"`). Do not set `base` or `breakpoint`.

**Lite run** (`.sauces/lite` exists): for web platforms too, keep only the narrowest frame per state (still named `<base>@<width>`) and record the dropped widths in the kept source's `reason`; report lists them as not verified.

When no platform is known yet (ingest ran before scan), keep every width as `<base>@<width>` screens and say so; scan and plan settle it, and a later ingest run rewrites the manifest.
