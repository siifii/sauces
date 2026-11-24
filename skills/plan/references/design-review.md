# Design review (plan step 7)

Review the design itself and suggest improvements ("the design would be better if…"), beside the code recommendations. Every suggestion rests on a measured fact from `design_audit.py` or on a cited principle. Never write a taste-only suggestion ("make it pop", "use a more modern font", "add more whitespace") with no guideline and no number behind it.

The user decides per suggestion at the gate: `keep` (default, build the design as drawn) or `apply` (build the improved version; verify records it as an intentional deviation, not an error to fix back). Eval mode keeps every suggestion.

## 1. Measure

Run the audit from the target root:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/design_audit.py" --manifest .sauces/manifest.json
```

It writes `.sauces/design-audit.json`: `{version, about, grid, summary, findings[]}`. Each finding is `{id: audit-<category>-<n>, category, severity, screen, state?, also_in?, region?, detail, measured, guideline}`. Exit 0 means it ran, findings or not. Exit 2 means the manifest could not be read: say so in the summary, skip the measured part and still do the judgement checks (section 3).

The report reads the same file later, so never edit it.

To compute a number the audit does not give you (the contrast of a replacement color, a ΔE), call the same functions instead of estimating:

```bash
python3 -I -c 'import importlib.util as u,sys;s=u.spec_from_file_location("a",sys.argv[1]);m=u.module_from_spec(s);s.loader.exec_module(m);print(round(m.contrast_ratio(sys.argv[2],sys.argv[3]),2), round(m.delta_e76(sys.argv[2],sys.argv[3]),2))' "${CLAUDE_PLUGIN_ROOT}/scripts/design_audit.py" "#49454F" "#FFFFFF"
```

It prints the contrast ratio, then ΔE76.

## 2. Turn audit findings into suggestions

One suggestion per root cause, not per finding: the same small caption in three states, or three off-grid gaps, is one suggestion listing all the evidence. Copy `severity` and `guideline` from the finding (you may lower a severity with a stated reason, never raise it). Set `audit_id` to the first finding's id.

| Finding (`measured` keys) | Concrete `change` |
|---|---|
| Text contrast (`contrast_ratio`, `required`, `color`, `background`) | The replacement color and its new ratio. Prefer an existing design color or theme role that passes (for example `#49454F` on `#FFFFFF`, 9.34:1); otherwise darken (light background) or lighten (dark background) the same hue until it passes with a 0.2 margin. Compute the ratio, never estimate it. |
| Border contrast (`border`, `contrast_ratio`) | A border color with ≥ 3:1 against the background, with its ratio (Material's outline role `#79747E` is 4.55:1 on white). |
| Touch target (`kind`, `height`, `width`, `minimum`, `wcag_spacing`) | Keep the visual size and extend the hit area to 48 × 48 (Flutter: `minimumSize: Size(48, 48)` or `MaterialTapTargetSize.padded` on the button style; Compose: `Modifier.minimumInteractiveComponentSize()`; SwiftUI: `.frame(minWidth: 44, minHeight: 44)` plus `.contentShape(Rectangle())`), or raise the visual height (`button height 36 → 48 px`) when the control itself is too small. Say which; a hit-area-only change has no visual deviation. Inline links inside a sentence are exempt from WCAG 2.5.8: skip them. Severity is `high` only when the target is under 24 px and `wcag_spacing` is `fails` (too close to an adjacent target); otherwise it meets 2.5.8, at least by its spacing exception, and misses only Material 48 dp / HIG 44 pt, so say that in `why`. The audit also checks icons inside a text field (a password toggle). |
| Small text (`size`, `minimum`) | `raise <element> from 11 to 12 px (line height 16)`, naming the platform type role (Material `body small` 12/16; HIG `caption 1` 12 pt). State that it is a legibility recommendation, not a WCAG requirement. Material `label small` (11) is a legitimate role for short non-essential labels (badges, overlines): lower to `low` there, or drop it. |
| Near-duplicate colors (`color_a`, `color_b`, `delta_e`, `uses_a`, `uses_b`) | `replace <rarer> with <more used or token color> (ΔE 0.9)`. For colors extracted from images, a color used once with ΔE < 1.5 is usually anti-aliasing or compression noise: drop it instead of suggesting. |
| Off-grid value (`value`, `nearest_on_grid`, `kinds`) | One suggestion for all off-grid values: `gap 14 → 16 px, padding 13 → 12 px`. A value from an image layout with a `raw_note` may be measurement noise: say "measured from the image" in the evidence and keep severity `low`. |
| Mixed radii (`radii`, `count`, `maximum`) | Map each radius to the nearest Material 3 shape-scale step the design already uses (`radius 10 → 12 px, 20 → 16 px`), leaving at most 3. Pills are already excluded. |
| Type-scale sprawl (`styles`, `count`, `off_scale_sizes`) | Map each style to a platform type role with its size (`15/500 → title small 14/500`, `18/400 → body large 16/400`), so the screen uses at most 6 styles and no off-scale sizes. On iOS map to Dynamic Type styles (body 17, subheadline 15, footnote 13). |
| Missing states (`missing`, `present`) | What each missing state shows, in values: `loading: Sign in button shows a 20 px circular progress indicator in place of its label, fields and link disabled; error: error text 12/16 #B3261E under the password field`. Use the design's own colors and the project's component variants. Applying it means build adds the state without a reference image; verify reports it as unscored. |

Evidence is `<screen>/<state>: <region> — <measured values>` (add `also in login/error, login/loading` from `also_in`), for example `login/default: column > link "Forgot password?" — height 20 px (from line height), minimum 48`.

## 3. Judgement checks

The script cannot measure these. Look at the layouts and the reference images. Write a suggestion only when it applies, and cite the principle in `guideline`; leave `audit_id` out.

- **Primary-action hierarchy (ux).** Count high-emphasis buttons (`filled`) per screen state. More than one, or a destructive action styled as primary, is a suggestion: keep one filled button for the main action and make the others `tonal`, `outlined` or `text`. Guideline (paraphrased): Material 3 Buttons (filled is the highest-emphasis style, for the most important or final action) and Apple HIG Buttons (give the most likely action a prominent style).
- **Error copy (ux).** Error text must say what went wrong and how to fix it (WCAG 2.2 SC 3.3.1 Error Identification, SC 3.3.3 Error Suggestion). A field error like `Invalid input` → `Enter an email like name@example.com`. Exception: a sign-in failure such as `Incorrect email or password` is deliberately generic so it does not reveal which accounts exist (OWASP Authentication Cheat Sheet, authentication responses). It is fine: never suggest naming the wrong field. An error shown only as a red border or red text with no message fails WCAG 2.2 SC 1.4.1 Use of Color: suggest message text, optionally an error icon.
- **Password visibility (ux).** A password field without a show/hide control: suggest a trailing visibility toggle (NIST SP 800-63B: verifiers should offer an option to display the secret as it is typed; Material 3 text fields: trailing icon). When the toggle exists as an `icon` inside the field, the audit already measures its touch target (section 2).
- **Text expansion (localization).** A label in a fixed-width element (a `width` number on a button, chip or tab, or several labels sharing one row) with less than about 40% spare room will clip when translated: German and similar languages run about 30–40% longer than English, and short strings (under 10 characters) can double (W3C Internationalization, "Text size in translation"). Change: let the element grow (`min width 120 px` instead of `width 120 px`) or allow the label to wrap to two lines. Mention the project's locales from the profile.
- **RTL mirroring (localization).** Directional icons (back and forward arrows, chevrons, progress that moves left to right) must mirror in right-to-left locales; non-directional ones (eye, search, checkmark, media playback) must not. Text alignment is start/end, never left/right. Guideline: Material Design bidirectionality guidance and Apple HIG Right to left. Raise it to `medium` when the profile's `localization.rtl` is true or a locale is RTL (ar, he, fa, ur); otherwise `low`, and only when a directional icon is present.
- **Text baked into images (localization).** Text inside an `image` or illustration node cannot be translated or scaled: suggest real text over the image (WCAG 2.2 SC 1.4.5 Images of Text).
- **Platform conventions (platform).** Compare the design with the target platform's idiom: Android and Compose follow Material 3 (system back and predictive back, top app bar, Material switch); iOS and SwiftUI follow Apple HIG (navigation bar with a back button and swipe-back, safe areas around the notch and home indicator, iOS toggle). Flutter and CMP follow the project's design language (Material unless the project uses Cupertino widgets). A control drawn in the other platform's style, or content placed under the status bar or home indicator, is a suggestion. A missing `dark` state is a product decision, never a defect: at most one `low` platform suggestion, and only when the project theme already defines a dark theme (both platforms let users choose a system-wide dark appearance).

Do not suggest what build does anyway (keyboard types, autofill hints, semantic labels, min-height instead of fixed height so text scales). Put those in the item `notes` instead.

## 4. Rank, cap and write

1. Merge duplicates: one suggestion per root cause, with every screen and state in `evidence`.
2. Sort by severity (high, medium, low), then category in this order: accessibility, ux, states, localization, platform, consistency. `design-audit.json` uses the same order.
3. Keep at most 8. Never drop a `high` one to make room. When more remain, say in `plan.md` how many lower-severity findings were left out and that `.sauces/design-audit.json` lists them all.
4. Number them `sug-1`, `sug-2`, … in that order.

Each `design_suggestions[]` entry in `plan.json`:

- `id`, `audit_id` (when from the audit), `category`, `severity`.
- `title`: the change in a few words (`Give "Forgot password?" a 48 dp touch target`).
- `evidence`: screen, state, region and the measured values (section 2).
- `change`: concrete enough to build, values not adjectives (`raise caption from 11 to 12 px`, never "make it bigger").
- `why`: the effect on users, in one or two sentences.
- `guideline`: the cited rule (WCAG SC number and name, Material 3 or HIG page, or the source named in section 3).
- `choice`: `keep`.

In `plan.md`, `## Design suggestions` opens with one line: "Every suggestion defaults to keep (the design is built as drawn). Choose apply to build the improved version; verify records it as an intentional deviation." Then one block per suggestion:

```
### sug-1 · medium · accessibility · Give "Forgot password?" a 48 dp touch target
- Evidence: login/default: column > link "Forgot password?" — height 20 px (from line height), minimum 48; WCAG 2.5.8 spacing passes (gap 8 px)
- Change: keep the 20 px text, extend the hit area to 48 × 48 dp
- Why: small targets are hard to hit, especially for users with motor impairments; it meets WCAG 2.5.8 by spacing but misses the platform minimums
- Guideline: Material 3 touch targets 48 × 48 dp; HIG 44 × 44 pt; WCAG 2.2 SC 2.5.8 (spacing exception)
- Choice: keep
```

## 5. At the gate and after

In the approval message, list each suggestion on one line (`sug-1 (medium, accessibility): <title>: <change>`), say they all default to `keep`, and that the user can reply `sug-1: apply` or `apply all suggestions`.

When the user applies a suggestion: set its `choice` to `apply`, and add `design suggestion sug-<n> applied: <change>` to the `notes` of every item it affects. If the change needs a value the plan does not have yet (a new color, a new string for an added state), add the token item or `strings[]` entry too. Applying never changes an existing theme value: if it would, say so and offer the matching `rec-design-theme-<n>` option instead.
