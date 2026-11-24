# Reading Figma sources

Figma data arrives only through a Figma MCP server the user connected: the plugin's own `figma` server (`.mcp.json`, `https://mcp.figma.com/mcp`) or a claude.ai Figma connector. Sauces never calls the Figma REST API itself and never asks for a token.

## 1. Find the tools

Look through your available tools (including deferred ones you can load by name) for names ending in:

- `get_design_context`: structured design + code hints for a node (primary)
- `get_screenshot`: an image of a node
- `get_variable_defs`: the variables (colors, spacing, type) used by a node
- `get_metadata`: the node tree (ids, names, sizes) of a page or frame

Match the suffix under any server prefix, for example `mcp__figma__get_design_context`, `mcp__plugin_sauces_figma__get_design_context` or `mcp__claude_ai_Figma__get_design_context`. If several servers offer them, prefer the one the user named, else the first that works. If a server's tool list also has `create_session` (current official Figma server), call it first with the fileKey and a one-line task description, and pass the returned id as `sessionId` where tools accept it. If its instructions name a skill to load before `get_design_context`, load it.

If none of the four tools exists, record the source and move on:

```json
{"ref": "<url>", "kind": "figma", "status": "unreadable", "reason": "No Figma MCP connected. Connect the Figma connector or the plugin's figma server."}
```

Use that `reason` exactly. If the tools exist but every call fails (auth error, no access, file not found), use `status: unreadable` with `reason` = `"Figma MCP error: <message>"`.

## 2. Parse the URL

| URL form | fileKey | nodeId |
|---|---|---|
| `figma.com/design/<fileKey>/<name>?node-id=<a>-<b>` | `<fileKey>` | `<a>:<b>` (replace `-` with `:`) |
| `figma.com/file/<fileKey>/<name>?node-id=...` (legacy) | `<fileKey>` | same conversion |
| `figma.com/design/<fileKey>/branch/<branchKey>/<name>` | `<branchKey>` | from `node-id` |
| `figma.com/proto/<fileKey>/<name>?node-id=...` (prototype link) | `<fileKey>` | from `node-id` (the frame shown) |
| `figma.com/spec/<fileKey>/<name>?node-id=...` (Dev Mode spec link) | `<fileKey>` | from `node-id` |
| `figma.com/make/<makeFileKey>/<name>` | `<makeFileKey>` | none |
| `figma.com/board/...` | FigJam. Mark `unreadable` with `reason: "FigJam boards are not UI designs."` |
| `figma.com/slides/...` | Slides. Mark `unreadable` with `reason: "Figma Slides files are not UI designs."` |

The `node-id` query value may be URL-encoded (`1%3A2`); decode it first. Without a node id, call `get_metadata` on the file/page and take its top-level frames.

## 3. Read frames

1. `get_metadata` on the node. If it is a page or section, its direct child frames are the screens; if it is a single frame, that frame is the screen.
2. For each frame: the frame name gives screen and state, using the same naming rules as files (`Login--Error`, `Login / Error`, `Login – error` → screen `login`, state `error`). Frames with the same base name are states of one screen. Variant properties such as `State=Error` also name the state.
3. `get_design_context` on each frame: use its structure, text and styles to build the state's `layout` with the contract in `images.md` (sizes in Figma are already logical px; set `assumed_dpr` to 1 relative to the frame).
4. `get_screenshot` on each frame for the reference PNG. If the result includes a downloadable image URL, fetch it into `.sauces/references/<screen>--<state>.png` with `curl -fsSL`. If it comes back only as an inline image you cannot write to disk, say so: keep the layout, do not create the state (a state needs a reference file), set `reason: "screenshot not saved to disk; export the frame as PNG and ingest it"` with `status: ok`, and tell the user in the summary that `verify` needs PNG exports of those frames. The exact screenshot return format differs between server versions; check what you get rather than assuming.

A PNG export of a frame also given in the arguments is a duplicate (SKILL.md §3): keep the higher-resolution file.

## 4. Variables into tokens

Call `get_variable_defs` on each frame (or the parent node once). It returns names mapped to values. Merge them:

- Color variables (`#RRGGBB`, or `#RRGGBBAA` with alpha `FF`) → `tokens.colors {hex, name: <variable name in kebab-case, e.g. color/primary → primary>, origin: "figma"}`. Drop extracted colors within ΔE 3 of a Figma color.
- Number variables named like spacing/gap/padding → `tokens.spacing`; radius/corner → `tokens.radii`. Figma values are intentional: keep them as they are, do not snap them.
- Text styles (font family, size, weight, line height) → `tokens.typography`, named from the style name (`Title/Large` → `title-large`).

Record the source with `status: ok` and, when only part of it was usable, a `reason` saying which frames were skipped and why.
