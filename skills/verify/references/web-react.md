# Verify web-react

Follow `web-capture.md` in this folder for the runner, seeding order, capture settings, clip rule, RTL pass and keyboard check. This file adds what is specific to React projects.

## Render test
Seed each state through props on the presentational `<Screen>View`: an existing Storybook story first, then an existing fixture route, then a dev-only fixture page (Next.js route that calls `notFound()` outside development; Vite extra HTML entry left out of `build.rollupOptions.input`). Read the view's props and the project's providers (i18n, theme, query client) so the fixture wraps the view exactly as the app does. Give each state a readiness selector (a role or test id only that state shows). A Testing Library or jsdom render is never a capture.

## Run
Start the dev server with the lockfile's package manager (`npm run dev`, `pnpm dev`, …) on a free port and wait until it answers, or use the running Storybook. Capture every state of every `<screen>@<width>` screen with `capture.cjs`, the project's Playwright when installed, else the pinned `npx` command. Stop the server when done. If the app does not start or a fixture page cannot be added under the approved plan, record the reason and use the manual checklist without a score.

## Fix
Apply fixes through the build reference (`skills/build/references/web-react.md`): tokens, logical properties and the project's breakpoints, never inline pixel values to match a frame.
