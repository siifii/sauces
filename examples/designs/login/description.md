# Login screen (sample design)

A mobile sign-in screen designed as a Material 3 screen: white background, no status bar or device chrome. It is the standard input for Sauces tests and evals.

Canvas: 390 x 844 logical px at device pixel ratio 2 (PNG 780 x 1688).

## Files

| File | What |
|---|---|
| `login--default.png` | Default state |
| `login--error.png` | Error state |
| `login--loading.png` | Loading state |
| `login-flow.pdf` | The three states, one per page, in the order default, error, loading |
| `icons/eye.svg` | 24 x 24 outline eye icon (stroke `currentColor`, 1.75, round caps) |
| `src/` | HTML and CSS source (`login.css`, `default.html`, `error.html`, `loading.html`, `flow.html`, `fonts/` Inter TTFs and `OFL.txt`) |

## Copy (exact)

- Title: `Welcome back`
- Field labels: `Email`, `Password`
- Link: `Forgot password?`
- Button: `Sign in`
- Error message: `Incorrect email or password`

The field values `alex@example.com` and `••••••••` are placeholder content, not copy.

## Colors

| Role | Hex |
|---|---|
| Brand (button, link) | `#3D5AFE` |
| Surface (background, button label) | `#FFFFFF` |
| Text (title, field values) | `#1B1B1F` |
| Label and icon (on-surface-variant) | `#49454F` |
| Field border (outline) | `#79747E` |
| Error | `#B3261E` |

## Type (Inter)

| Element | Weight | Size / line height | Color |
|---|---|---|---|
| Title | SemiBold 600 | 28 / 36 | text |
| Field label (floating) | Regular 400 | 12 / 16 | `#49454F` |
| Field value | Regular 400 | 16 / 24 | text |
| Forgot password link | Medium 500 | 14 / 20 | brand |
| Button label | SemiBold 600 | 16 / 24 | white |
| Error message | Regular 400 | 12 / 16 | error |

## Layout (logical px)

- Content column with 24 side padding, starting 96 from the top.
- Title, then 32 gap.
- Email field, 16 gap, Password field.
- 8 gap, then `Forgot password?` right-aligned (20 high).
- 24 gap, then the `Sign in` button (full width, 52 high, 12 radius, brand fill).
- Fields: 56 high, 12 radius, 1 border `#79747E`. The label floats on the top border (12 from the left edge, 4 side padding, white background behind it). Value text sits 16 from the left edge.
- Password field: eye icon, 24 x 24, inside the field, 12 from the right edge, vertically centered.

## States

1. **Default**: values `alex@example.com` and `••••••••`, all borders 1 px outline color.
2. **Error**: as default, but the Password field border is 2 px in the error color, its label is error color, and `Incorrect email or password` sits 4 below the field with a 16 left inset. The forgot-password row and button move down by 20 (16 text + 4 offset).
3. **Loading**: as default, but the button shows a centered 24 px circular spinner (white, 2.5 stroke, about 270 degree arc, static) instead of the label.

## Regenerate

```
scripts/dev/render_designs.sh
```

Needs Google Chrome (override the path with `CHROME=/path/to/chrome`). Runs from any directory and rewrites the three PNGs and the PDF in this folder.
