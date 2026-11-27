# Pseudo-locale pass (optional)

Run this only when `.sauces/config.json` has `"pseudo_locale": true`, after the RTL pass. It is a check, not a fidelity score: it never changes `score`, `passed` or `iterations`.

## What it shows

A pseudo-locale renders every translated string accented, about 30% longer and in brackets: `Sign in` → `[Šîĝñ îñ~~~]`. In the capture:

- text without brackets is **hard-coded** (it did not come from the catalog);
- a missing closing bracket or an ellipsis means the text is **clipped**;
- overlapping or overflowing elements mean the layout cannot take longer translations.

## Make the pseudo catalog

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/pseudo_locale.py" "<source catalog>" --out ".sauces/verify/pseudo/<file>" --locale en-XA
```

It handles JSON catalogs (i18next, next-intl, `locales/*.json`), Flutter ARB and Android `strings.xml`, keeping placeholders and ICU plurals intact. Use the project's source-locale catalog from the profile's `localization.location`.

## Render it, per platform

Render the **default state of each screen once**, at the narrowest designed width, in the pseudo-locale. Never leave a pseudo catalog or locale in the user's project: load it in memory, or add it in a temporary copy, or delete it right after the capture and say so.

- **web-react:** in the dev fixture page, load `.sauces/verify/pseudo/<file>` as an extra in-memory bundle (i18next `addResourceBundle("en-XA", …)` + `changeLanguage("en-XA")`; next-intl: pass it as `messages` to the provider for that render).
- **web-html:** write it to `locales/en-XA.json` in the served site, capture `?lang=en-XA`, then delete that file.
- **react-native:** the same in-memory bundle as web-react, in the existing capture harness.
- **flutter:** in a temporary copy of the project, add `app_en_XA.arb` (from `pseudo_locale.py`) next to the source ARB, run `flutter gen-l10n`, and pump the screen with `locale: Locale('en', 'XA')`. Delete the copy afterwards.
- **android-compose / kmp-cmp:** Android has built-in pseudolocales (`en-XA` accented and longer, `ar-XB` right-to-left) when the debug build type enables them (`isPseudoLocalesEnabled = true`). That is a build change: use it only if the approved plan includes it. Otherwise write the pseudo `strings.xml` to a temporary `values-en-rXA/` folder, render with the test's configuration locale set to `en-XA`, and delete the folder.
- **ios-swiftui:** Xcode has Accented and Double-Length pseudolanguages (the scheme's or test plan's App Language). Use them for the UI test run when the installed Xcode exposes them from the command line (check `xcodebuild -help` for `-testLanguage`); if it does not, skip the pass and say so. Do not edit String Catalogs for it.

## Record

Save the capture as `.sauces/verify/<id>/pseudo.png` and write each problem as one sentence in that state's `pseudo_issues` (for example "'Forgot password?' shows without brackets: hard-coded" or "Button label clipped at 390 px"). Report it, do not fix it in verify: hard-coded text found here is a build bug to fix through the build reference, so list it in the summary as the first next step.
