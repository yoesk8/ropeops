# Tenant-isolation testing (mandatory for every module PR)

A workspace is a tenant. No endpoint or queryset may ever return, change or reveal another workspace's data. Every PR that adds or changes a model or endpoint in a `ropeops_*` app ships tests built on `apps/api/ropeops/testing`.

## What the harness gives you

`apps/api/ropeops/conftest.py` provides the `tenants` fixture: two workspaces, A and B, each with an admin, member and guest (all active, all project members) and one project.

| Helper | Use |
| --- | --- |
| `assert_cross_tenant_denied(tenants, victim, method, url, data=None, secrets=[...])` | Every role of the other tenant plus an anonymous caller must get 401/403/404, and no `secrets` (ids, names) may appear in the response. |
| `assert_list_scoped(tenants, owner, own_url, other_url, secret_ids=[...], expected_ids=[...])` | A list endpoint returns the caller's own rows, none of the other tenant's, and the other tenant's URL is denied. |
| `build_tenant(name)` | Make extra tenants/roles when you need them. |
| `tenant.client_for("admin"/"member"/"guest")` | Authenticated `APIClient` for a role. |

`ropeops/tests/test_isolation_template.py` is the template: copy it to `apps/api/ropeops_<module>/tests/test_isolation.py` and replace the URLs. `ropeops/tests/test_model_tenancy.py` automatically fails any `ropeops_*` model without a non-null `workspace` FK to `db.Workspace` (exemptions need a written reason in `EXEMPT`, approved by the CTO).

## Checklist for each new endpoint

- [ ] Create rows in tenant A with the new model; collect their ids/names as `secrets`.
- [ ] Cross-tenant GET/POST/PATCH/DELETE on detail and list URLs via `assert_cross_tenant_denied`.
- [ ] List endpoints via `assert_list_scoped`.
- [ ] Inside one tenant: guest/member/admin permissions match the intended roles (use Plane permission classes or `@allow_permission`).
- [ ] Ids in request bodies (e.g. a `project` or `holder` pointing at tenant B) are rejected, not silently accepted.
- [ ] Public/portal endpoints resolve everything from the deploy-board `anchor` only.

## Running

Same stack as CI (Docker needed once):

```bash
./setup.sh                                   # creates apps/api/.env
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest ropeops
docker compose -f docker-compose-test.yml run --rm api-tests pytest plane/tests ropeops   # full
docker compose -f docker-compose-test.yml down -v
```

CI (`.github/workflows/ropeops-ci.yml`) runs the same two commands on every PR to `preview`, plus the upstream core-edit guard.
