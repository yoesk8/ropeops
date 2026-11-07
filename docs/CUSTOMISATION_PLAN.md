# Customisation plan

Goal: ship the RopeOps MVP (rope access and window-cleaning ops) on the Plane fork while keeping monthly upstream merges nearly conflict-free.

## 1. Rules that keep merges clean

1. **New code lives in new places.** Backend: new Django packages `apps/api/ropeops_<name>/` (app label `ropeops_<name>`, own models, migrations, serializers, views, urls, tests). Frontend: `apps/web/**/ropeops/` folders and `apps/web/app/routes/extended.ts` (upstream's empty extension hook), `apps/web/store/ropeops/`.
2. **Core edits are tiny and listed.** Allowed one-liners: `INSTALLED_APPS` in `plane/settings/common.py`, `include()` in `plane/urls.py`, route/store registration, flag checks. Every core file we edit goes in `docs/UPSTREAM.md` (CI enforces this, see `.github/scripts/check_core_edits.py`).
3. **Never edit existing migrations.** Our models get their own migration chain (`ropeops_*` apps). If we must depend on `db`, depend on its latest migration at the time, never alter `db` models.
4. **Do not subclass-patch Plane models with new fields.** Use a new model with a `OneToOne`/FK to the Plane model (e.g. `ropeops_certificates.Certificate` -> `db.Workspace`, `db.User`) instead of adding columns to `Issue`, `Project`, etc.
5. **Every tenant-scoped model inherits `WorkspaceBaseModel`** (non-null `workspace` FK), every view uses Plane's permission classes / `@allow_permission`, every queryset filters by the URL workspace slug. Proof: tests built on `ropeops.testing` (see `docs/TENANT_ISOLATION_TESTING.md`). `ropeops/tests/test_model_tenancy.py` fails CI for any `ropeops_*` model without a workspace FK.
6. **Hide, don't delete.** Out-of-scope Plane features are switched off behind flags/config, so upstream code stays intact.
7. **Branding by config/translation, not by search-and-replace of source.** Name, logo and trade terms go through i18n overrides, env/instance settings and a `ropeops` theme; AGPL headers and licence files stay untouched.
8. **Backend tests required for each new endpoint and model**; no merge without QA pass.

## 2. Decision per MVP item

The MVP list is in ROP-2. Decisions below; items are ordered as in the plan.

| Item | Decision | Notes |
| --- | --- | --- |
| Workspace / multi-tenancy, members, roles | **Extend (use as is)** | Admin/Member/Guest map to Owner/Supervisor/Technician-or-Client later via `company_role` text and our own labels. |
| Jobs (work items) with status, assignee, dates | **Extend** | Plane work item = RopeOps "Job". Rename through i18n. Custom fields via work-item types/properties (already in Plane) where possible; else a side model keyed to `Issue`. |
| Sites / clients | **Extend + small new module** | Sites = Plane Projects (rename "Site"). Client contact details: new model `ropeops_clients.Client` (workspace-scoped), Site links to it. |
| Recurring jobs | **New module** `ropeops_recurring` | Model `RecurringJob` (template + RRULE-style schedule). Celery beat task generates Issues. |
| Certificates (IRATA/SPRAT, equipment, inspections) | **New module** `ropeops_certificates` | CTO scaffolds models/permissions in W4, Yoel builds W5-W8. Expiry reminders via Celery. |
| Client portal | **Extend `apps/space`** | Read-only anchor-scoped views; new endpoints under `plane/space`-style routes in our own app. Needs Board sign-off on what clients see (UK GDPR). |
| Branding | **New module** `ropeops_branding` + config | `WorkspaceBranding` model (logo asset, colours, display name) per workspace; RopeOps defaults. |
| Subscriptions / billing | **New module** `ropeops_billing` | `WorkspaceSubscription` model only (plan, status, seats). **Any payment provider integration needs Board approval.** |
| Cycles, Modules, Analytics, Pages, Intake, Views, Estimates, Time tracking, Issue types UI, Webhooks UI, Integrations/Importers, God-mode link | **Hide** | Per-feature flags (`Project.*_view` already defaults several off); hide nav entries via one flag helper. Not deleted. |
| Auth (email+password, magic link) | **Extend (config only)** | Changes to auth configuration need Board approval. |
| Plane name/logo/links in UI and emails | **Replace via config** | i18n override + asset swap + email templates in `apps/api/templates` (core edit, listed). Licence notices stay. |

## 3. New models (all in new apps, all inherit `WorkspaceBaseModel` unless noted)

```
ropeops_clients.Client            workspace, name, contact_name, email, phone, address, notes
ropeops_clients.Site              workspace, client FK, project OneToOne -> db.Project (nullable), access_notes, hazards
ropeops_certificates.Certificate  workspace, holder (FK db.User) | equipment (FK Equipment), type (choices), number, issuer,
                                  issued_on, expires_on, file (FK db.FileAsset), status, reminder_days
ropeops_certificates.Equipment    workspace, name, serial, category, next_inspection_on
ropeops_recurring.RecurringJob    workspace, project FK, title, description, assignee(s), schedule (rrule text), next_run_at,
                                  last_run_at, is_active, template fields
ropeops_billing.WorkspaceSubscription  workspace OneToOne, plan, status, seats, current_period_end, external_customer_id (nullable)
ropeops_branding.WorkspaceBranding     workspace OneToOne, display_name, logo (FK db.FileAsset), primary_colour, portal_welcome_text
```

Field lists are a starting point; the owning ticket may refine them but may not drop the `workspace` FK. Personal data (holder names, certificate files) is UK GDPR relevant: store the minimum, support export and erase per workspace, never log values.

## 4. Glossary of trade terms (UI strings)

| Plane term | RopeOps UI term |
| --- | --- |
| Workspace | Company |
| Project | Site |
| Work item / Issue | Job |
| Sub-work item | Task |
| State | Status |
| Member | Team member |
| Guest | Client / Viewer (portal) |
| Admin | Owner |
| Cycle | (hidden) |
| Module | (hidden) |
| Intake | (hidden) |
| Labels | Tags (e.g. "Rope access", "Window cleaning") |
| (new) Certificate | Certificate (IRATA, SPRAT, PASMA, first aid...) |
| (new) Recurring job | Recurring job |

Implemented in the Rebrand work (W1-3) via `packages/i18n` override keys; role numbers in the database do not change.

## 5. Monthly upstream sync

Process lives in `docs/UPSTREAM.md`. In short: first week of each month, branch `upstream-sync/YYYY-MM`, merge `upstream/preview`, resolve conflicts (only possible in files listed in UPSTREAM.md), run full CI, QA pass, then merge. Major upstream changes (auth, billing, stack, big migrations) need Board approval.

## 6. Build order and who

W1 docs/CI/harness (CTO) -> W1-3 Rebrand and hiding (Frontend, Backend) -> clients/sites -> recurring jobs -> W4 certificates scaffold (CTO) -> W5-W8 certificates (Yoel) -> portal -> branding/subscriptions. Tickets of under one day each are written per feature at the start of that phase.
