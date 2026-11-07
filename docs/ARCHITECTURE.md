# RopeOps architecture map

Snapshot of the Plane fork (`yoesk8/ropeops`, branch `preview`, based on upstream `618d0eb7`, 3 Nov 2026). Paths are relative to the repo root. Read this before touching anything in `apps/api/plane/` or `apps/web/`.

## 1. Repository layout

| Path | What it is |
| --- | --- |
| `apps/api` | Django 5.2 + DRF backend, Celery workers. Python 3.12, deps via `uv` (`pyproject.toml`, `uv.lock`). |
| `apps/web` | Main app (React Router + MobX + Vite), port 3000. |
| `apps/space` | Public "spaces" app, port 3002, base path `/spaces`. Anonymous/published views. Basis for the client portal. |
| `apps/admin` | Instance admin ("god mode", port 3001). Not for tenants. Hide from RopeOps users. |
| `apps/live` | Real-time collaboration server (editor), port 3100. |
| `apps/proxy` | Caddy reverse proxy used by `deployments/`. |
| `packages/*` | Shared TS packages: `shared-state` (MobX stores), `types`, `constants`, `i18n`, `editor`, `blocks`, `utils`, `services`, ... |
| `docs/` | Our docs (this folder). |

## 2. Backend (`apps/api/plane`)

Django project `plane`. `plane/urls.py` mounts four API surfaces:

| Prefix | Django app | Auth | Used by |
| --- | --- | --- | --- |
| `/api/` | `plane.app` | Session cookie (`BaseSessionAuthentication`) | Web app. **Our main surface.** |
| `/api/public/` | `plane.space` | Anonymous or session; scoped by deploy-board `anchor` | `apps/space` |
| `/api/v1/` | `plane.api` | `X-Api-Key` (`APIToken`) | External/3rd-party API |
| `/api/instances/` | `plane.license` | Instance admin | God-mode, instance config |
| `/auth/` | `plane.authentication` | n/a | Login, magic link, OAuth |

Other apps: `plane.db` (all models + migrations), `plane.bgtasks` (Celery tasks), `plane.analytics`, `plane.middleware`, `plane.utils`, `plane.web` (static/health), `plane.tests`.

### 2.1 Models (`plane/db/models/`, 86 model classes, one migration app `db`)

All models derive from `BaseModel` (UUID pk, `created_at/updated_at/created_by/updated_by`, **soft delete** via `deleted_at`, `AuditModel`). `created_by` is auto-filled from `crum.get_current_user()` on save.

Tenant hierarchy:

```
User ──< WorkspaceMember >── Workspace ──< Project ──< ProjectMember >── User
                              │              │
                              │              ├─ State, Label, Cycle, Module, Issue (work item), Page, IssueView, Estimate, Intake, ...
                              └─ Team, WorkspaceTheme, WorkspaceUserProperties, WorkspaceMemberInvite, APIToken, Webhook, ...
```

- **Workspace** (`workspace.py`) is the tenant. `slug` is the URL identifier. `owner` FK to User.
- `WorkspaceBaseModel` (abstract): `workspace` FK (CASCADE) + optional `project` FK; `save()` copies `project.workspace`. **Our new tenant-scoped models must inherit this** (or declare a non-null `workspace` FK).
- `ProjectBaseModel` (abstract, `project.py`): `project` + `workspace` FKs, `workspace` auto-set from project.
- `Project`: `identifier` (short key), `network` (0 secret, 2 public), feature toggles `module_view`, `cycle_view`, `issue_views_view`, `page_view`, `intake_view`, `is_time_tracking_enabled`, `is_issue_type_enabled`, `guest_view_all_features`.
- `Issue` (`issue.py`) = "work item". Related: `IssueAssignee`, `IssueLabel`, `IssueComment`, `IssueActivity`, `IssueAttachment` (via `FileAsset`), `IssueRelation`, `IssueLink`, `IssueVote`, `IssueReaction`, `IssueSubscriber`, `IssueVersion`, etc. States: `State` (groups backlog/unstarted/started/completed/cancelled).
- `DeployBoard` / `ProjectDeployBoard` (`deploy_board.py`): public publish of a project/issue board with unguessable `anchor`. Backs `apps/space`.
- `FileAsset` (`asset.py`): all uploads, S3/MinIO. Entity-typed.
- `Instance*` models live in `plane/license/models`.

### 2.2 Roles and permission classes

Roles (ints): **Admin 20, Member 15, Guest 5**, at two levels: `WorkspaceMember.role` and `ProjectMember.role`. `is_active=False` means removed (always filter `is_active=True`).

`plane/app/permissions/`:

- `workspace.py`: `WorkSpaceBasePermission`, `WorkspaceOwnerPermission` (admin), `WorkSpaceAdminPermission` (admin+member), `WorkspaceEntityPermission` (read: any member; write: admin+member), `WorkspaceViewerPermission`/`WorkspaceUserPermission` (any active member), `WorkspaceMemberPermission`.
- `project.py`: `ProjectBasePermission`, `ProjectEntityPermission`, `ProjectMemberPermission`, `ProjectLitePermission`, `ProjectAdminPermission`, `ProjectArchiveUnarchivePermission`.
- `base.py`: `allow_permission([ROLE.ADMIN, ...], level="WORKSPACE"|"PROJECT", creator=False, model=None)` method decorator (the dominant pattern in views; workspace admins who are project members pass project-level checks), `issue_hidden_from_guest()`, `ROLE` enum.
- `page.py`: `ProjectPagePermission`.

Views resolve the tenant from the URL (`<slug>` = workspace slug, `<project_id>`), and **permissions check membership against that slug**. Querysets are expected to filter `workspace__slug=slug` (and project membership where the project is private). This is the main place a cross-tenant leak can happen; hence our isolation harness (`docs/TENANT_ISOLATION_TESTING.md`).

`BaseViewSet`/`BaseAPIView` (`plane/app/views/base.py`) add timezone, pagination and a guard that complains when a mixin-provided action has no real permission class. Default `permission_classes = [IsAuthenticated]` is **not** authorization.

### 2.3 View/URL layout

`plane/app/views/<domain>/` + `plane/app/urls/<domain>.py`, one list per domain (`analytic, asset, cycle, estimate, exporter, external, intake, issue, module, notification, page, project, search, state, timezone, user, views, webhook, workspace, api`). `plane/app/urls/__init__.py` concatenates them. Serializers in `plane/app/serializers/`. The external API (`plane/api/`) mirrors a subset with its own serializers and rate limit (`API_KEY_RATE_LIMIT`).

### 2.4 Background work

Celery (`plane/celery.py`, RabbitMQ broker, Valkey/Redis cache). Tasks in `plane/bgtasks/` (notifications, email, exports, webhooks, issue activity, cleanup). `django_celery_beat` holds periodic schedules: this is where recurring-job generation will hook in.

### 2.5 Settings

`plane/settings/{common,local,production,test,openapi}.py`. `INSTALLED_APPS` is in `common.py` (inhouse apps, then third-party). `test.py` appends `plane.tests`. DB from `DATABASE_URL` or `POSTGRES_*`.

## 3. Public views: `plane/space` + `apps/space`

Published boards are keyed by an unguessable `anchor` on `DeployBoard`. `plane/space/views/*` take `<anchor>` and resolve project/issues from it; `DeployBoardAnchorMixin` rejects an anchor whose project doesn't match. Anonymous requests are allowed; many endpoints also support signed-in members. Frontend: `apps/space/app/issues/[anchor]` + `apps/space/store/*` (`issue-detail`, `issue-filters`, `cycle`, `instance`, plus `store/helpers`). This is the foundation for the client portal (read-only certificates and job status for customers); any new public endpoint must resolve everything from the anchor and never accept a free workspace/project id.

## 4. Frontend

- `apps/web`: React Router (framework mode). Routes are declared in `apps/web/app/routes/core.ts` (upstream) and `apps/web/app/routes/extended.ts` (**empty extension hook; our routes go here**). Pages under `apps/web/app/(all)/[workspaceSlug]/...`. UI in `apps/web/components/<feature>`, hooks in `apps/web/hooks`, services (API clients) in `apps/web/services`.
- **MobX stores**: `apps/web/store/` with `root.store.ts` (`CoreRootStore`) composing `cycle, module, label, member, project, project-view, issue/*, pages/*, inbox/*, notifications/*, estimates/*, workspace/*, user/*, ...`. Accessed through hooks in `apps/web/hooks/store/use-*.ts` (`useProject`, `useWorkspace`, `useMember`, ...). Shared stores in `packages/shared-state`. New stores go in new files under `apps/web/store/ropeops/`; wiring them into `CoreRootStore` is one core edit (listed in UPSTREAM.md), made once in the first frontend ticket.
- `apps/space`: own small store set (above). `apps/admin`: instance admin.
- i18n in `packages/i18n` (translation files per locale; `i18n-sync-check` workflow guards sync). Trade terms ("work item" -> "Job" etc.) are applied through translation overrides, see `CUSTOMISATION_PLAN.md`.
- Primitives from `@makeplane/propel`; composites in `packages/blocks`.

## 5. Existing tests and CI

- `apps/api/plane/tests/{unit,contract/{app,api},smoke}` + `conftest.py` (`workspace`, `session_client`, `api_key_client`, `create_user`) + `factories.py`. About 55 contract tests already assert workspace/project scope for fixed upstream CVEs; copy their style.
- Upstream workflows kept: `pull-request-build-lint-api` (ruff), `pull-request-build-lint-web-apps` (format, lint, types, build), `migration-check`, `copyright-check`, `i18n-sync-check`, `codeql`, `check-version`, `build-branch`, `feature-deployment`, `react-doctor`.
- **Gap found:** upstream CI does not run the Django test suite. We added `.github/workflows/ropeops-api-tests.yml`, see `docs/TENANT_ISOLATION_TESTING.md`.

## 6. Where RopeOps code goes

See `docs/CUSTOMISATION_PLAN.md`. Short version: new Django packages `apps/api/ropeops_*` (label `ropeops_*`), new frontend folders prefixed `ropeops`, with the smallest possible core edits registered in `docs/UPSTREAM.md`.
