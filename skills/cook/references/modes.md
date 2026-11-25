# Modes

Cook picks the mode from `.sauces/project-profile.json` `mode` right after scan-project (design §5.1). Eval mode is `.sauces/eval-approve` existing: no human is present, so take the stated eval action and say so in the summary.

| Profile `mode` | Sauces mode | What cook does | Eval mode |
|---|---|---|---|
| `existing` | **follow** (+ advise) | Continue to plan. New code follows the project's architecture and conventions; scan's findings become the plan's recommendations (default: keep as is). | Same. |
| `empty` | **create** | Offer to create a project: "There's no app project here yet. I can create one and build the design into it." Run the scaffold skill, which asks the platform(s) with the defaults marked (Recommended), lets the user override them, creates `<root>/<platform>/` and rescans. Then continue to plan in follow mode on the new project. If the user declines, stop: nothing to build into. | Scaffold with every default (Flutter). |
| `ambiguous` | **ask** | Scan already asked which project to target (an unsupported app beside a supported one, several platforms side by side, or unclassifiable code). Continue with the project the user picked; never guess. If the user hasn't picked, ask again and wait. | Scan picked the first project in platform order (`flutter`, `ios-swiftui`, `android-compose`, `kmp-cmp`, `react-native`); continue with it. |

Notes:

- A supported project in a child folder (`flutter/`, `ios/`, …) is follow mode with that project's `root`, not create mode.
- Backend, tooling or script folders never change the mode.
- When scaffold creates several projects, select one for the current plan using scan’s ambiguous-mode rules.
- Create mode needs an empty folder (README, licences, dotfiles, docs and design files are fine). Scaffold refuses anything else unless the user confirms, and always refuses in eval mode.
