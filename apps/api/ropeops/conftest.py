# Copyright (c) 2026-present RopeOps contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from ropeops.testing.isolation import TwoTenants, build_tenant


@pytest.fixture
def tenants(db) -> TwoTenants:
    """Two isolated workspaces (A and B), each with admin/member/guest users and a project."""
    return TwoTenants(a=build_tenant("a"), b=build_tenant("b"))
