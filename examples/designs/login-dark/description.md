# Login screen with dark appearance (sample design)

The `login` sample, each state in a light and a dark frame. It is the input for testing dark mode: ingest pairs `login--<state>.png` with `login--<state>-dark.png`, plan maps the dark colors onto the project's dark theme, verify renders both.

Canvas: 390 x 844 logical px at device pixel ratio 2 (PNG 780 x 1688). Copy and layout are identical to `../login/description.md`.

## Files

| File | What |
|---|---|
| `login--default.png`, `login--error.png`, `login--loading.png` | Light frames (copied from `../login`) |
| `login--default-dark.png`, `login--error-dark.png`, `login--loading-dark.png` | Dark frames |
| `src/` | HTML for the dark frames and `dark.css` (overrides `../login/src/login.css`) |

Regenerate the dark frames with `scripts/dev/render_dark_designs.sh` (headless Chrome).

## Colors (dark)

| Role | Light | Dark |
|---|---|---|
| Brand (button, link) | `#3D5AFE` | `#B9C3FF` |
| Surface (background) | `#FFFFFF` | `#1B1B1F` |
| Text | `#1B1B1F` | `#E4E1E6` |
| Label and icon | `#49454F` | `#C8C5D0` |
| Field border | `#79747E` | `#928F99` |
| Error | `#B3261E` | `#F2B8B5` |
| Button label | `#FFFFFF` | `#0A1F8F` |
