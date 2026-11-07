# Proposed tickets: W1-3 Rebrand and hide out-of-scope features

Each is under one day. Order matters. Format: Title / Context / Acceptance criteria / Files / Tests / Assignee.

## R1. Trade-term translation overrides (Frontend Engineer)
- Context: glossary in `docs/CUSTOMISATION_PLAN.md` section 4.
- Acceptance: [ ] en strings show Company, Site, Job, Task, Status, Team member, Owner, Tags in nav, lists, modals, emails untouched. [ ] No source rename of components or keys. [ ] `i18n-sync-check` passes.
- Files: `packages/i18n` locale `en` (core edit, list in UPSTREAM.md), or an override file if the loader supports it.
- Tests: snapshot/unit test that key terms resolve; manual smoke.

## R2. RopeOps name and logo in web, space and admin (Frontend Engineer)
- Acceptance: [ ] No "Plane" name/logo in page titles, headers, sign-in, onboarding, empty states, `manifest.json`. [ ] AGPL headers and LICENSE untouched. [ ] Placeholder RopeOps logo asset in `**/ropeops/` folder.
- Files: logo components, `apps/web/manifest.json`, titles (list each core file in UPSTREAM.md).
- Tests: grep check `.github/scripts/check_branding.sh` in CI for user-visible "Plane" strings (excluding licence headers).

## R3. Transactional email and API templates branding (Backend Engineer)
- Acceptance: [ ] Emails in `apps/api/templates` say RopeOps, no Plane logo/links. [ ] No external sends in tests (locmem).
- Tests: unit test rendering each template, asserting no "Plane" text.

## R4. Feature-flag helper and hide nav entries (Frontend Engineer)
- Context: hide Cycles, Modules, Analytics, Intake, Views, Time tracking, Importers, Integrations, Webhooks UI, God-mode link. Hide, never delete.
- Acceptance: [ ] One flag module `apps/web/**/ropeops/features.ts` with a single list. [ ] Sidebar/project nav/command palette respect it. [ ] Direct URLs to hidden features redirect home.
- Tests: unit test for the flag helper; QA walkthrough.

## R5. Project defaults for new Sites (Backend Engineer)
- Context: `Project.module_view/cycle_view/intake_view/...` defaults.
- Acceptance: [ ] New Sites are created with hidden features off, via a signal/serializer default in `ropeops_branding`/new app (no edit to `Project` model). [ ] Existing sites untouched.
- Tests: contract test creating a project; isolation tests from the harness.

## R6. QA pass for rebrand (QA Engineer)
- Acceptance: [ ] Checklist run on web, space, admin, emails. [ ] Findings filed as bugs. [ ] Isolation suite green on `preview`.
