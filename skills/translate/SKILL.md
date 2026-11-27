---
name: translate
description: This skill should be used when the user asks to "translate the strings", "fill the translations", "translate to Arabic", "finish the TODO translations", or runs "/sauces:translate". Fills the translation TODOs Sauces left in the project's real string catalogs for the chosen locales, keeps every placeholder and plural intact, and marks each machine translation for human review.
argument-hint: "[locale ...] [--all]"
---

# Translate

Fill the strings Sauces added but could not translate (other locales got the source text and a translate TODO). Machine translation is a draft: every string you write is marked for review, and nothing a person already translated is touched.

## Hard rules

- The target root is the current working directory. Change only the target-locale catalogs the plan names, `.sauces/todos.json` and `.sauces/translations.json`.
- Translate only **candidates** (section 2). Never change the source locale, a key that is not a candidate, a value that already differs from the source text, or a non-translatable entry (Android `translatable="false"`, product and brand names, URLs, code).
- Keep every placeholder, ICU argument, plural and select structure, HTML tag and escape exactly as in the source. Use the target language's plural categories (Arabic: zero, one, two, few, many, other).
- Show the plan and wait for approval before writing. In eval mode (`.sauces/eval-approve` exists) approve it yourself and say so.

## 1. Load

1. Read `.sauces/project-profile.json` (`localization.system`, `location`, `locales`) and `.sauces/plan.json` (`platform`, `strings[]`). If the profile is missing or `localization.system` is `none`, say there is no catalog to fill (suggest `/sauces:plan` to adopt one) and stop.
2. Locales: the arguments, else every locale in `localization.locales` except the source locale (the template/source catalog). `--all` also includes keys Sauces did not add (section 2). Reject a locale the project does not have; adding a locale is a plan decision.
3. Read the platform's build reference `${CLAUDE_PLUGIN_ROOT}/skills/build/references/<platform>.md` (`## Strings`): it names the catalog files and their format.

## 2. Find candidates

A key is a candidate for a locale when all hold:

- it is in `plan.strings[]` without `"existing": true` (a key Sauces added), or `--all` was given;
- its value in the target catalog is missing, equals the source-locale value, or is marked with a translate TODO (ARB `@key.description` "TODO(sauces): translate", a `.sauces/todos.json` translate entry for that file, an Android/iOS translate comment Sauces left);
- it is translatable (hard rules).

List them per locale: key, source text, where it appears (`plan.strings[].screen`).

## 3. Plan and approve

Draft each translation, natural for the screen it appears on (a button label is short and imperative; an error message is a sentence). Keep the tone of strings the project already translated in that locale; read a few first. Show a table per locale: key, source, proposed translation. Ask the user to approve, edit or drop rows. Write only approved rows.

## 4. Write

Write each approved translation in the catalog's own format and mark it for review:

| System | Where | Review mark |
|---|---|---|
| Flutter ARB | `app_<locale>.arb` value | `"@key": {"description": …, "x-sauces-review": "machine translation"}` (keep any existing `@key` fields) |
| Android `strings.xml` | `values-<locale>/strings.xml` | `<!-- sauces: machine translation, review -->` on the line above |
| iOS String Catalog | `.xcstrings` localization for the locale | `"state": "needs_review"` |
| iOS `.strings` | `<locale>.lproj/*.strings` | `/* sauces: machine translation, review */` above the entry |
| JSON (i18next, next-intl, `locales/*.json`) | the locale's file | no comment syntax: listed in `.sauces/translations.json` only |
| Compose Multiplatform | `composeResources/values-<locale>/strings.xml` | as Android |

Keep the file's formatting and key order; insert new keys next to their neighbours, as build does.

## 5. Check

1. For JSON, ARB and Android XML catalogs, run per locale and fix every problem before continuing:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/i18n_check.py" "<source catalog>" "<target catalog>"
   ```

   Exit 0 is clean; exit 1 lists keys whose placeholders differ (fix the translation, never the source).
2. Run the platform's string tooling from the build reference (`flutter gen-l10n`, the Android resource build, the project's i18n type check or tests) and fix what you wrote.

## 6. Record and report

- Write `.sauces/translations.json`: `{"version": 1, "entries": [{"locale", "file", "key", "source", "translation", "status": "needs_review"}]}` (append to an existing file; update an entry with the same locale, file and key).
- In `.sauces/todos.json`, replace each filled "translate N strings" entry with `{"file": "<catalog>", "line": 1, "text": "review N machine translations (<locale>)"}`.
- Reply in a few lines: strings translated per locale, the review marks used, and that a native speaker should review them before release. Suggest running verify again to see the right-to-left screens with real text.
