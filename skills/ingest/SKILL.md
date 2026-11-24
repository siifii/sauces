---
name: ingest
description: This skill should be used when the user asks to "ingest designs", "read this Figma link", "load these screenshots", "parse this PDF flow", "normalize design sources", "import the mockups", or runs "/sauces:ingest". Normalizes Figma URLs, PNG/JPG/WebP screenshots, PDFs and SVGs into screens, states, tokens and assets in .sauces/manifest.json, with one reference PNG per screen state.
argument-hint: <figma-url | file | folder | glob>...
---

# Ingest

Turn every design source in `$ARGUMENTS` into `.sauces/manifest.json` plus one normalized reference PNG per screen state in `.sauces/references/`. `plan`, `build` and `verify` consume this manifest, and `verify` scores the built UI against these reference PNGs, so the references must be the best available image of each state and the layout must describe only what the images show.

## Hard rules

- The target project root is the current working directory. Every path written into the manifest under `.sauces/` is relative to it, POSIX style (`.sauces/references/login--default.png`).
- Write only inside `.sauces/` (create it if missing). Never modify, move or delete a design source or any project file. Leave other files in `.sauces/` alone.
- Run helpers as `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/<name>"` and quote every path (paths may contain spaces). Exit 3 from any helper means Pillow/numpy is missing: stop and tell the user to run the install command the helper printed.
- Never skip a source silently. Every source gets a `sources[]` entry with `status: ok` or `status: unreadable` and, when anything is notable (unreadable, duplicate, guessed grouping), a `reason`.
- Never invent content. Text, colors and measurements come from the sources. Use `"unknown"` in a layout when you cannot read something.
- Eval mode: when `.sauces/eval-approve` exists there is no human. Never ask; take the best guess, record it in the source's `reason`, and list it in the summary.

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

Use them as-is. Derive a screen id and state from the file name (step 3). PNG files are copied unchanged to their reference path in step 4. Convert JPG/WebP to PNG while copying:

```bash
python3 -I -c "import sys; from PIL import Image; Image.open(sys.argv[1]).convert('RGB').save(sys.argv[2])" "<src>" ".sauces/references/<screen>--<state>.png"
```

A file Pillow cannot open is `unreadable` with the error as `reason`.

### PDFs

Rasterize every page:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/rasterize_pdf.py" "<file.pdf>" --out-dir ".sauces/references/_pdf/<pdf-stem>" --dpi 144
```

It prints `{"version":1,"pages":[...]}`. Exit 4 means `pdftoppm` is missing: mark the source `unreadable` with the install hint from stderr as `reason`, and continue. Treat each page as an image candidate without a file-name state (step 3). If the PDF has selectable text, `pdftotext` (when installed) may help confirm copy.

### SVGs

Read the file and classify it:

- `icon`: viewBox (or width/height) roughly square (aspect 0.8–1.25) with the longer side ≤ 48, drawn in a single color or `currentColor`, a handful of simple shapes/paths, no embedded `<image>` and no gradients.
- `illustration`: everything else.

Copy it unchanged to `.sauces/assets/<name>.svg`, where `<name>` is the file stem in lowercase kebab-case (add `-2`, `-3` on a clash). Record `assets[] {path: ".sauces/assets/<name>.svg", kind, name}` and a source entry with `status: ok`. SVGs never become screen states.

### Figma

Read `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/figma.md` and follow it. Find the Figma tools by name suffix (`get_design_context`, `get_screenshot`, `get_variable_defs`, `get_metadata`) under any server prefix. If none is available, record the source as:

```json
{"ref": "<url>", "kind": "figma", "status": "unreadable", "reason": "No Figma MCP connected. Connect the Figma connector or the plugin's figma server."}
```

Then keep going with the other sources and repeat the message in the summary. Never stop the whole ingest because Figma is unreadable.

## 3. Group into screens and states

State names are the schema enum: `default`, `loading`, `empty`, `error`, `dark`, `other`. Ids are lowercase kebab-case.

Apply these rules in order:

1. **File name convention.** Parse the stem as `<screen>--<state>` (preferred). Also accept `<screen>_<state>` and `<screen>-<state>` when the last word is one of the state names above. The state id is that word and its name is the matching enum value. With `--`, a state word outside the enum (`login--filled`) keeps its id and gets name `other`. A stem with no state part is screen `<stem>`, state `default`.
2. **Visual similarity** for images without a state from the name (PDF pages, loose screenshots). First check for duplicates (below). Otherwise compare the candidate with existing references using `visual_diff.py` (it is a hint, not proof), then look at both images: the same title and structure means the same screen. Choose the state from what is visible (spinner → `loading`, error text or red field → `error`, empty list or placeholder → `empty`, dark background → `dark`). Name new screens from the visible title, in kebab-case.
3. **Ask** the user when the grouping is still uncertain. In eval mode, take the best guess and note it in that source's `reason` (for example `"guessed: page 2 → onboarding error"`).

Distinct file-name states are never merged, even when they look almost identical (a loading state can differ from default only by a spinner).

### Duplicates

Before adding a state from a candidate image, compare it with every existing state reference, at the reference's size:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/visual_diff.py" "<candidate.png>" "<reference.png>" --out-dir ".sauces/references/_diff" --threshold 97
```

It prints a 0–100 score; exit 1 only means the score is under 97. A score ≥ 97 against any existing state makes the candidate a duplicate: do not create a state. If it matches several states, pick the best score, and break near-ties (within 0.5) by looking at the images and the page order. Keep the higher-resolution image (larger width) as that state's reference and point the state's `source` at whichever source supplied it. Record the duplicate in the candidate source's `reason` with `status: ok`, for example `"pages 1–3 duplicate login default/error/loading"`. Two files whose names give the same screen and state are duplicates too: keep the higher-resolution one the same way. Delete `.sauces/references/_diff/` when grouping is done.

## 4. Write references

For each state, write its reference to `.sauces/references/<screen>--<state-id>.png` (copy PNG, convert others, copy the chosen PDF page). Only these files are references; the `_pdf/` rasters stay as provenance.

## 5. Analyze each state

Read `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/images.md` and follow it. In short: when the Agent/Task tool is available, dispatch the `sauces:design-analyst` agent once per state reference (send them all in one message so they run in parallel). Otherwise analyze each image yourself with the same output contract. Store each returned `layout` object on its state as `layout`.

## 6. Tokens

Build `tokens` from all sources:

- **colors**: run the palette helper on every reference PNG:

  ```bash
  python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/extract_palette.py" .sauces/references/*.png
  ```

  Add each color as `{hex, coverage, origin: "extracted"}`. Then add any text/border/icon color the analysis reported that is not within ΔE 3 of a palette color (for example a small error-text red), as `{hex, origin: "extracted"}` without coverage. Add `name` only when a role is obvious (`primary` for the button fill, `surface`, `on-surface`, `error`). Figma variables merge in per `figma.md` with `origin: "figma"`; when a Figma color matches an extracted one (ΔE < 3), keep only the Figma entry.
- **typography**: collect the distinct `(size, weight, line_height, family)` styles from the text nodes of all layouts, round size and line height to whole logical px, and merge styles that differ by ≤ 1 px with the same weight. Name each by role: `title`, `headline`, `body`, `label`, `caption`, `button`, `link` (suffix `-2` etc. when a role has several sizes). Omit `family` and `line_height` when unknown.
- **spacing** and **radii**: collect paddings, gaps and corner radii from all layouts, snap each to the 4-pt grid (see `images.md`), de-duplicate and sort ascending. The layouts keep the raw measured values.

## 7. Write and validate

Write `.sauces/manifest.json`:

```json
{"version": 1, "sources": [...], "screens": [{"id": "login", "name": "Login", "states": [{"id": "default", "name": "default", "reference": ".sauces/references/login--default.png", "source": 0, "layout": {...}}]}], "tokens": {"colors": [...], "typography": [...], "spacing": [...], "radii": [...]}, "assets": [...]}
```

Use only schema fields (`additionalProperties` is false at the top level). Then validate:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/check_json.py" "${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/manifest-schema.json" .sauces/manifest.json
```

- Exit 0: valid.
- Exit 1: each `path: message` line is an error. Fix the manifest and validate again. Repeat until it exits 0. Never finish with an invalid manifest.
- Exit 2: schema or usage problem. Check the command and paths, then rerun.

Check also that every `reference` file exists and every `source` index points into `sources`.

## 8. Summarise

End with a short human summary (do not paste the JSON):

- sources: total, how many `ok` and `unreadable`, with the reason for each unreadable one (for Figma, repeat the connect hint);
- screens × states (for example `login: default, error, loading`);
- duplicates dropped;
- token counts: colors, typography styles, spacing values, radii;
- assets by kind;
- every guess made (grouping, state names, DPR assumption) and anything you skipped.
