# Upstream sync (makeplane/plane)

Remote: `upstream` = `https://github.com/makeplane/plane.git`, branch `preview`.
Fork point: upstream commit `618d0eb7` (3 Nov 2026).

```bash
git remote add upstream https://github.com/makeplane/plane.git   # once
git fetch upstream preview
```

## Monthly sync (first week of the month, CTO owns)

1. `git checkout preview && git pull && git checkout -b upstream-sync/YYYY-MM`
2. `git merge upstream/preview` (merge, not rebase, so history stays shared).
3. Conflicts: only files in the table below should conflict. Rule: take upstream's version, then re-apply our one-line edit. If something else conflicts, a rule was broken: fix the cause and note it here.
4. Check upstream's new migrations in `apps/api/plane/db/migrations`; our `ropeops_*` migrations depend on `db` only by an explicit older migration, so no renumbering is needed.
5. Run the full CI (lint, types, build, Django tests, isolation tests, migration check) and a manual smoke test.
6. QA passes, then merge. A **major** merge (auth, billing, stack, large schema change) needs Board approval first.
7. Record the new fork point below.

## Core files we have touched

CI fails a PR that edits a file under `apps/api/plane/` (excluding `plane/tests/`), `apps/web/`, `apps/space/`, `packages/` or other upstream paths unless the file is in this list (`scripts/check_core_edits.py`). Add a row in the same PR with the reason.

<!-- core-files:start -->
| File | Why | Added in |
| --- | --- | --- |
| `.github/workflows/ropeops-api-tests.yml` | New file (CI) | ROP-3 |
| `docs/*` | Our docs | ROP-3 |
<!-- core-files:end -->

Paths owned entirely by RopeOps (no upstream equivalent, never listed): `apps/api/ropeops*/`, `scripts/`, `docs/`, `**/ropeops/**`, `.github/workflows/ropeops-*.yml`.

## Sync log

| Date | Upstream commit | Notes |
| --- | --- | --- |
| 2026-11-03 | `618d0eb7` | Fork point |
