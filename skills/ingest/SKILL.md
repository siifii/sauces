---
name: ingest
description: This skill should be used when the user asks to "ingest designs", "read this Figma link", "load these screenshots", "parse this PDF flow", "normalize design sources", "import the mockups", or runs "/sauces:ingest". Normalizes Figma URLs, PNG/JPG/WebP screenshots, PDFs and SVGs into screens, states, tokens and assets in .sauces/manifest.json, with one reference PNG per screen state.
argument-hint: <figma-url | file | folder | glob>...
---

# Ingest

Turn every design source in `$ARGUMENTS` into `.sauces/manifest.json` plus one reference PNG per screen state in `.sauces/references/`. `verify` scores the built UI against these PNGs, so each must be the best available image of its state, and layouts describe only what the images show.

## Hard rules

- The target project root is the current working directory. Every path written into the manifest under `.sauces/` is relative to it, POSIX style (`.sauces/references/login--default.png`).
- Write only inside `.sauces/` (create it if missing). Never modify, move or delete a design source or any project file. Leave other files in `.sauces/` alone, except stale reference PNGs (step 4).
- Run helpers as `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/<name>"` and quote every path (paths may contain spaces). Exit 3 from any helper, or an `ImportError`/`ModuleNotFoundError` from an inline `python3 -I -c` Pillow command, means Pillow/numpy is missing: stop and give the guidance in `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/python-deps.md`. Never mark a source unreadable for that reason.
- Never skip a source silently. Every source gets a `sources[]` entry with `status: ok` or `status: unreadable` and, when anything is notable (unreadable, duplicate, guessed grouping), a `reason`.
- Never invent content. Text, colors and measurements come from the sources. Use `"unknown"` in a layout when you cannot read something.
- Eval mode: when `.sauces/eval-approve` exists there is no human. Never ask; take the best guess, record it in the source's `reason`, and list it in the summary.

## 0. Preflight

Check the Python dependencies before anything else:

```bash
python3 -I -c "import PIL, numpy"
```

If it fails, stop: read `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/python-deps.md` and give the user that guidance. Do not write a manifest.

## 1. Collect sources

Split `$ARGUMENTS` into items (respect quotes). Expand each item:

- **URL** containing `figma.com/`: one source, `kind: figma`, `ref` = the URL as given.
- **Folder**: walk it recursively and take files ending in `.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`, `.svg` (case-insensitive). Skip folders named `src`, `node_modules`, `build`, `.sauces`, and every hidden folder (name starts with `.`). Ignore all other files (`.md`, `.html`, `.css`, `.ttf`, `.txt`, …): they are not design sources.
- **Glob**: expand it and keep only the extensions above.
- **File**: take it if the extension is supported. A missing file gets a source entry (kind from its extension) with `status: unreadable`, `reason: "File not found"`. An unsupported file type is not a source: mention it in the summary only.

Kinds: `.png/.jpg/.jpeg/.webp` → `image`, `.pdf` → `pdf`, `.svg` → `svg`. Set `ref` to the path relative to the project root when the file is inside the project, otherwise to its absolute path. Order sources as the arguments were given, files within a folder sorted by path. A state's `source` is the index of its entry in this list.

Supplementary context: if a `description.md` (or `README.md`) sits in a design folder you walked, read it for screen names, state names and the spelling of copy. It is never a source: do not take measurements, colors or fonts from it, and never let it override what the images show.

## 2. Read each source

### Images

Use them as-is. Derive a screen id and state from the file name (step 3). Opaque PNG files are copied unchanged to their reference path in step 4. Convert JPG/WebP, and any PNG with transparency, to an opaque PNG while copying (alpha is composited onto white):

```bash
python3 -I -c "import sys; from PIL import Image; im = Image.open(sys.argv[1]); im = im.convert('RGBA') if 'A' in im.getbands() or 'transparency' in im.info else im.convert('RGB'); bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im, mask=im.getchannel('A')) if im.mode == 'RGBA' else bg.paste(im); bg.save(sys.argv[2])" "<src>" ".sauces/references/<screen>--<state>.png"
```

A file Pillow cannot open (decode error, corrupt file) is `unreadable` with the error as `reason`. A missing-module error is a dependency problem, not an unreadable file (hard rules).

### PDFs

Rasterize every page:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/rasterize_pdf.py" "<file.pdf>" --out-dir ".sauces/references/_pdf/<pdf-stem>" --dpi 144
```

It prints `{"version":1,"pages":[...]}`. Exit 4 means `pdftoppm` is missing: mark the source `unreadable` with the install hint from stderr as `reason`, and continue. Treat each page as an image candidate without a file-name state (step 3).

### SVGs

Read the file and classify it:

- `icon`: roughly square (aspect 0.8–1.25), small (the `width`/`height` attributes, when present, have a longer side ≤ 48; without them, judge the viewBox by aspect ratio only, since icon sets use large viewBoxes such as Material Symbols' `0 -960 960 960`), drawn in a single color or `currentColor`, a handful of simple shapes/paths, no embedded `<image>` and no gradients.
- `illustration`: everything else.

Copy it unchanged to `.sauces/assets/<name>.svg`, where `<name>` is the file stem in lowercase kebab-case (add `-2`, `-3` on a clash). Record `assets[] {path: ".sauces/assets/<name>.svg", kind, name}` and a source entry with `status: ok`. SVGs never become screen states.

### Figma

Read `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/figma.md` and follow it. Find the Figma tools by name suffix (`get_design_context`, `get_screenshot`, `get_variable_defs`, `get_metadata`) under any server prefix. If none is available, record the source as:

```json
{"ref": "<url>", "kind": "figma", "status": "unreadable", "reason": "No Figma MCP connected. Add one with `claude mcp add --transport http figma https://mcp.figma.com/mcp` or connect the claude.ai Figma connector, then run again."}
```

Then continue with the other sources and repeat the message in the summary.

## 3. Group into screens and states

State names are the schema enum: `default`, `loading`, `empty`, `error`, `dark`, `other`. Ids are lowercase kebab-case.

Process in two passes so names win over guesses:

- **Pass A**: group every source whose file name follows the convention (rule 1). These create the screens and their reference states.
- **Pass B**: then process nameless candidates (PDF pages, loose screenshots without a state part) one by one against the pass-A references: duplicate check first (below), then rules 2–3. Each candidate added in pass B becomes a reference the later candidates are compared with. During grouping, a state's reference is its current image file (source PNG/JPG or page raster); step 4 writes the final files.

If a pass-B candidate would start a new screen, compare it first with the states of every existing screen; when it is the same screen (same title and structure), add it as a state of that screen instead of creating a second screen under the visible title. Before writing, check that no two screens describe the same UI; merge any that do into the file-named screen.

The rules:

1. **File name convention.** Parse the stem as `<screen>--<state>` (preferred). Also accept `<screen>_<state>` and `<screen>-<state>` when the last word is one of the state names above. The state id is that word and its name is the matching enum value. With `--`, a state word outside the enum (`login--filled`) keeps its id and gets name `other`. A stem with no state part is screen `<stem>`, state `default`.
2. **Visual similarity** for images without a state from the name (PDF pages, loose screenshots). First check for duplicates (below). Otherwise compare the candidate with existing references using `visual_diff.py` (it is a hint, not proof), then look at both images: the same title and structure means the same screen. Choose the state from what is visible (spinner → `loading`, error text or red field → `error`, empty list or placeholder → `empty`, dark background → `dark`). Name new screens from the visible title, in kebab-case.
3. **Ask** the user when the grouping is still uncertain. In eval mode, take the best guess and note it in that source's `reason` (for example `"guessed: page 2 → onboarding error"`).

Distinct file-name states are never merged, even when they look almost identical (a loading state can differ from default only by a spinner).

### Duplicates

Frames of one screen at different widths are not duplicates: follow `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/breakpoints.md` for them and for each source's `viewport`. Light and dark frames of one state are not duplicates either: pair them per `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/dark-mode.md`.

Before adding a state from a candidate image, compare it with every existing state reference, at the reference's size:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/visual_diff.py" "<candidate.png>" "<reference.png>" --out-dir ".sauces/references/_diff" --threshold 97
```

It prints a 0–100 score; exit 1 only means it is under 97. A score ≥ 97 makes the candidate only a **possible** duplicate: the score cannot tell states apart (default and loading can score 99.8). For each state scoring ≥ 97, open both images and compare the state-distinguishing elements: spinner or progress, error text or error-colored borders, empty-state placeholder, dark vs light theme, overlays (dialogs, sheets, toasts), selected/disabled controls. It duplicates only a state where none differ (several qualify: best score, then page order); if every match differs, it is a new state of that screen (rule 2 names it). Once confirmed, keep the higher-resolution image (larger width) as that state's reference, with `source` pointing at whichever source supplied it, and record the duplicate in the candidate's `reason` with `status: ok` (e.g. `"pages 1–3 duplicate login default/error/loading"`). Two files naming the same screen and state are duplicates too: keep the higher-resolution one. Delete `.sauces/references/_diff/` when grouping is done.

## 4. Write references

First delete any `.sauces/references/*.png` left from an earlier run that is not the reference of a current state (do not touch `_pdf/` of current PDFs). Then, for each state, write its reference to `.sauces/references/<screen>--<state-id>.png` (copy PNG, convert others, copy the chosen PDF page). Only these files are references; the `_pdf/` rasters stay as provenance.

## 5. Analyze each state

Read `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/images.md` and follow it. In short: when the Agent/Task tool is available, dispatch the `sauces:design-analyst` agent once per state reference (send them all in one message so they run in parallel). Otherwise analyze each image yourself with the same output contract. Store each returned `layout` object on its state as `layout`.

Then build the optional `design_system` object (component candidates counted across all states, plus signals) per `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/design-system-signals.md`. Never fabricate Figma signals.

## 6. Tokens

Build `tokens` from all sources:

- **colors**: run the palette helper on the current states' reference PNGs, listed explicitly (not a glob):

  ```bash
  python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/extract_palette.py" ".sauces/references/<screen>--<state>.png" ...
  ```

  Add each color as `{hex, coverage, origin: "extracted"}`. Then add any text/border/icon color the analysis reported that is not within ΔE 3 of a palette color (for example a small error-text red), as `{hex, origin: "extracted"}` without coverage. Add `name` only when a role is obvious (`primary` for the button fill, `surface`, `on-surface`, `error`). Figma variables merge in per `figma.md` with `origin: "figma"` (with `source`, `modes` and named spacing/radii); when a Figma color matches an extracted one (ΔE < 3), keep only the Figma entry.
- **typography**: collect the distinct `(size, weight, line_height, family)` styles from the text nodes of all layouts, round size and line height to whole logical px, and merge styles that differ by ≤ 1 px with the same weight. Name each by role: `title`, `headline`, `body`, `label`, `caption`, `button`, `link` (suffix `-2` etc. when a role has several sizes). Omit `family` and `line_height` when unknown.
- **spacing** and **radii**: collect paddings, gaps and corner radii from all layouts, snap each to the 4-pt grid (see `images.md`), de-duplicate and sort ascending. The layouts keep the raw measured values.

## 7. Write and validate

Write `.sauces/manifest.json`:

```json
{"version": 1, "sources": [...], "screens": [{"id": "login", "name": "Login", "states": [{"id": "default", "name": "default", "reference": ".sauces/references/login--default.png", "source": 0, "layout": {...}}]}], "tokens": {"colors": [...], "typography": [...], "spacing": [...], "radii": [...]}, "assets": [...]}
```

Use only schema fields. Then validate:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/check_json.py" "${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/manifest-schema.json" .sauces/manifest.json
```

- Exit 0: valid.
- Exit 1: each `path: message` line is an error. Fix the manifest and validate again. Repeat until it exits 0. Never finish with an invalid manifest.
- Exit 2: schema or usage problem. Check the command and paths, then rerun.

Check also that every `reference` file exists and every `source` index points into `sources`.

## 8. Summarise

End with a short human summary (do not paste the JSON):

- sources: total, how many `ok` and `unreadable`, with the reason for each unreadable one (for Figma, repeat the connect hint; when Figma frames produced no screenshot file, say that `verify` needs PNG exports of those frames);
- screens × states (for example `login: default, error, loading`);
- duplicates dropped;
- token counts: colors, typography styles, spacing values, radii;
- assets by kind;
- every guess made (grouping, state names, DPR assumption) and anything you skipped.
