# Copyright (c) 2026-present RopeOps contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""TEMPLATE: copy this file into your module's tests and replace the URLs/models.

Pattern for every new RopeOps module:
  1. Create "secret" rows in tenant A through your model.
  2. Hit each endpoint of your module with assert_cross_tenant_denied().
  3. Check each list endpoint with assert_list_scoped().
This file exercises the harness against Plane's own project endpoints so it
passes today and proves the helpers detect real isolation.
"""

import pytest

from ropeops.testing import assert_cross_tenant_denied, assert_list_scoped

pytestmark = pytest.mark.contract


def test_other_tenant_cannot_read_or_change_project(tenants):
    a = tenants.a
    base = f"/api/workspaces/{a.slug}/projects/"
    detail = f"{base}{a.project.id}/"
    secrets = [a.project.id, a.project.name, a.project.identifier]
    assert_cross_tenant_denied(tenants, a, "get", base, secrets=secrets)
    assert_cross_tenant_denied(tenants, a, "get", detail, secrets=secrets)
    assert_cross_tenant_denied(tenants, a, "patch", detail, data={"name": "pwned"}, secrets=secrets)
    assert_cross_tenant_denied(tenants, a, "delete", detail, secrets=secrets)
    a.project.refresh_from_db()
    assert a.project.name != "pwned" and a.project.deleted_at is None


def test_project_list_is_scoped_to_own_workspace(tenants):
    a, b = tenants.a, tenants.b
    assert_list_scoped(
        tenants,
        a,
        f"/api/workspaces/{a.slug}/projects/",
        f"/api/workspaces/{b.slug}/projects/",
        secret_ids=[b.project.id, b.project.identifier],
        expected_ids=[a.project.id],
    )


def test_harness_detects_a_leak(tenants):
    """Guard against a vacuous harness: a URL the attacker CAN read must fail the check."""
    b = tenants.b
    with pytest.raises(AssertionError):
        # tenant B's own admin is not an "attacker" of B, but tenant A's users hitting
        # a public endpoint that returns 200 must be flagged. /api/users/me/ is such an endpoint.
        assert_cross_tenant_denied(tenants, b, "get", "/api/users/me/")
