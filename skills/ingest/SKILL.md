---
name: ingest
description: This skill should be used when the user asks to "ingest designs", "read this Figma link", "load these screenshots", "parse this PDF flow", "normalize design sources", or runs "/sauces:ingest". Normalizes Figma URLs, PNG/JPG, PDF and SVG inputs into screens, states and tokens in .sauces/manifest.json.
argument-hint: <figma-url | file | folder | glob>...
---

# Ingest

Normalize every source in `$ARGUMENTS` into `.sauces/manifest.json` and one reference PNG per screen/state in `.sauces/references/`. Read Figma links through the Figma MCP tools (`get_design_context`, `get_variable_defs`, `get_screenshot`, `get_metadata`), use images as-is, rasterize PDFs with `${CLAUDE_PLUGIN_ROOT}/scripts/rasterize_pdf.py`, classify SVGs as icons or illustrations, and extract a palette with `${CLAUDE_PLUGIN_ROOT}/scripts/extract_palette.py`. Group inputs into screens and states, and ask the user when grouping is uncertain. If a source can't be read (for example, a Figma link with no MCP connected), say so explicitly. (Stub: implemented in Phase 3.)
