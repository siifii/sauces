# Login screen, web (sample design)

The web version of the `login` sample: the same sign-in screen designed at two widths, a phone frame and a desktop frame. It is the standard input for Sauces web tests and evals (`web-react`, `web-html`). Mobile tests never use this folder; they use `../login/`.

| Frame | Canvas | PNG |
|---|---|---|
| `login@390` | 390 x 844 CSS px at device pixel ratio 2 | 780 x 1688 |
| `login@1440` | 1440 x 900 CSS px at device pixel ratio 1 | 1440 x 900 |

The `@390` frames are byte-for-byte copies of the mobile sample (`../login/login--<state>.png`); see `../login/description.md` for their layout.

## Files

| File | What |
|---|---|
| `login@390--default.png`, `login@390--error.png`, `login@390--loading.png` | Phone frames (copies of the mobile sample) |
| `login@1440--default.png`, `login@1440--error.png`, `login@1440--loading.png` | Desktop frames |
| `src/default.html`, `src/error.html`, `src/loading.html` | Desktop HTML: the mobile markup inside a two-column page |
| `src/desktop.css` | Desktop layer, loaded after `../login/src/login.css` (same tokens, type and fonts) |

## Copy (exact)

- Title: `Welcome back`
- Field labels: `Email`, `Password`
- Link: `Forgot password?`
- Button: `Sign in`
- Error message: `Incorrect email or password`

The field values `alex@example.com` and `••••••••` are placeholder content, not copy. The desktop frame adds no copy.

## Colors

| Role | Hex |
|---|---|
| Brand (brand panel, button, link) | `#3D5AFE` |
| Surface (background, button label, brand mark) | `#FFFFFF` |
| Text (title, field values) | `#1B1B1F` |
| Label and icon (on-surface-variant) | `#49454F` |
| Field border (outline) | `#79747E` |
| Error | `#B3261E` |

Type, field, link, button and state details are the mobile sample's (Inter; see `../login/description.md`).

## Desktop layout (`@1440`, CSS px)

- Two equal columns, 720 each, full height (900).
- Start side: the brand panel, filled with brand color, with a centered 96 x 96 mark (white ring, 8 stroke, radius 40, and a white dot, radius 14). Decorative: it has no text.
- End side: the form, 420 wide, centered horizontally in its column (left edge at 870), top at 300 (the default-state form is 300 high, so it is vertically centered).
- Inside the form, the mobile column without its side padding: title, 32 gap, Email field, 16 gap, Password field, 8 gap, `Forgot password?` end-aligned, 24 gap, `Sign in` button (full form width, 52 high).
- Error state: as on mobile, the error text pushes the link row and button down by 20; the form top stays at 300.
- Loading state: the button shows the static spinner instead of the label.

In a right-to-left locale the columns mirror: the brand panel is on the right and the form on the left.

## Regenerate

```
scripts/dev/render_web_designs.sh
```

Needs Google Chrome (override the path with `CHROME=/path/to/chrome`) and Pillow. The frames in this folder were rendered with headless Chrome 158.0.8127.37 at window 1440 x 1100, DPR 1, then cropped to 1440 x 900. It also re-copies the `@390` frames from `../login/`.
